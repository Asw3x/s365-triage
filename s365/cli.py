"""Командный интерфейс."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from . import __version__, catalog, score

TERMS = {"vuln": "only_vuln", "risks": "only_risks"}

HEADER = (
    f"{'slug':26}{'max':>10}{'avg':>9}{'acc/tot':>10}{'%':>5}"
    f"{'рейт':>6}{'ответ,ч':>9}{'посл.принят':>13}{'wld':>5}{'dom':>5}{'балл':>7}"
)


def _row(p: score.Program) -> str:
    return (
        f"{p.slug[:25]:26}"
        f"{(p.max_reward or 0):>10}"
        f"{p.avg_reward:>9}"
        f"{f'{p.accepted}/{p.total}':>10}"
        f"{(p.accept_rate if p.accept_rate is not None else '-'):>5}"
        f"{(p.rating if p.rating is not None else '-'):>6}"
        f"{(p.response_hours if p.response_hours is not None else '-'):>9}"
        f"{(p.last_accepted or '-'):>13}"
        f"{len(p.wildcards):>5}"
        f"{len(p.in_scope):>5}"
        f"{p.score:>7}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="s365-triage",
        description="Разбор скоупа и ранжирование программ bug bounty по локальному каталогу.",
        epilog="Инструмент не ходит в сеть и не трогает цели: он читает JSON-файл с каталогом.",
    )
    ap.add_argument("catalog", help="путь к JSON-файлу каталога программ")
    ap.add_argument("-t", "--terms", choices=["vuln", "risks", "all"], default="vuln",
                    help="условия программы: только уязвимости, только риски, или все (по умолчанию vuln)")
    ap.add_argument("-n", "--limit", type=int, default=25, help="сколько строк показать (0 — все)")
    ap.add_argument("-x", "--exclude", metavar="SLUG", action="append", default=[],
                    help="исключить программу по slug; можно повторять")
    ap.add_argument("--exclude-file", metavar="PATH",
                    help="файл со списком slug'ов для исключения, по одному на строку")
    ap.add_argument("--scope", metavar="SLUG",
                    help="вместо таблицы показать разобранный скоуп одной программы")
    ap.add_argument("--json", action="store_true", help="выдать результат в JSON")
    ap.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    excluded = set(args.exclude)
    if args.exclude_file:
        with open(args.exclude_file, encoding="utf-8") as fh:
            excluded |= {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}

    try:
        programs = catalog.active(catalog.load(args.catalog), excluded)
    except (OSError, ValueError) as exc:
        print(f"не удалось прочитать каталог: {exc}", file=sys.stderr)
        return 1

    ranked = score.rank(programs)
    if args.terms != "all":
        ranked = [p for p in ranked if p.terms == TERMS[args.terms]]

    if args.scope:
        found = next((p for p in ranked if p.slug == args.scope), None)
        if not found:
            print(f"программа {args.scope!r} не найдена среди активных", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(dataclasses.asdict(found), ensure_ascii=False, indent=1))
        else:
            print(f"{found.name} ({found.slug})\n")
            print("в скоупе:")
            for d in found.in_scope:
                print(f"  {d}")
            print("\nвне скоупа:")
            for d in found.out_scope:
                print(f"  {d}")
            print("\nСкоуп разобран автоматически из текста описания. Сверь с правилами программы.")
        return 0

    shown = ranked if args.limit == 0 else ranked[: args.limit]

    if args.json:
        print(json.dumps([dataclasses.asdict(p) for p in shown], ensure_ascii=False, indent=1))
        return 0

    print(f"=== {args.terms}: {len(ranked)} активных программ ===")
    print(HEADER)
    print("-" * len(HEADER))
    for p in shown:
        print(_row(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
