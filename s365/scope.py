"""Разбор скоупа из человекочитаемого описания программы.

Описания пишут текстом: «в области действия», «не принимаем», «вне области» идут вперемешку.
Парсер режет описание на секции по заголовкам, определяет знак каждой секции и каждой строки
по негативным маркерам и раскладывает найденные домены на два списка.

Это помощник, а не замена чтению правил программы.
"""

from __future__ import annotations

import re

TLDS = (
    "ru|com|net|org|io|dev|tech|online|site|store|cloud|app|me|su|biz|info|pro|team|"
    "digital|space|life|shop|agency|systems|ai|games|group"
)

DOMAIN = re.compile(
    r"(?<![\w/.-])(\*\.)?((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:" + TLDS + r"))(?![\w-])",
    re.I,
)

NEGATIVE = re.compile(
    r"(не принима|не рассматрива|вне области|out of scope|исключ|не распространя|"
    r"не оплачива|информацион|не вознагражда|запрещ|не в scope|не входят)",
    re.I,
)

POSITIVE = re.compile(
    r"(область действия|в scope|in scope|где искать|какие.*ресурс|перечень|"
    r"наши.*ресурс|поддомен|тестиров\w+ разреш|scope)",
    re.I,
)

HEADING = re.compile(r"^\s{0,3}(#{1,6}\s|\*\*[^*]{3,80}\*\*\s*$)")

# домены площадок, магазинов приложений и общеизвестных сайтов — не часть скоупа
NOISE = {
    "standoff365.com", "bugbounty.standoff365.com", "apps.apple.com", "play.google.com",
    "github.com", "google.com", "youtube.com", "t.me", "telegram.org", "w3.org",
    "owasp.org", "portswigger.net", "example.com", "cve.mitre.org", "nvd.nist.gov",
    "sentry.io", "dadata.ru",
}


def _sections(markdown: str) -> list[tuple[str, str]]:
    """Разбить текст на (заголовок, тело)."""
    out: list[tuple[str, list[str]]] = []
    head, body = "", []
    for line in markdown.split("\n"):
        if HEADING.match(line):
            out.append((head, body))
            head, body = line.strip("# *").strip(), []
        else:
            body.append(line)
    out.append((head, body))
    return [(h, "\n".join(b)) for h, b in out if h or any(b)]


def parse(description: str) -> tuple[list[str], list[str]]:
    """Вернуть (в скоупе, вне скоупа) — два отсортированных списка доменов."""
    inside: set[str] = set()
    outside: set[str] = set()

    for head, body in _sections(description or ""):
        # секция негативная, если это сказано в заголовке, либо если заголовок
        # ничего не утверждает, а тело начинается с отрицания
        section_negative = bool(NEGATIVE.search(head)) or (
            not POSITIVE.search(head) and bool(NEGATIVE.search(body[:200]))
        )

        for line in (head + "\n" + body).split("\n"):
            line_negative = section_negative or bool(NEGATIVE.search(line))
            for m in DOMAIN.finditer(line):
                if m.group(2).lower() in NOISE:
                    continue
                domain = (("*." if m.group(1) else "") + m.group(2)).lower()
                (outside if line_negative else inside).add(domain)

    return sorted(inside - outside), sorted(outside)
