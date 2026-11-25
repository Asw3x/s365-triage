"""Тесты парсера скоупа, скоринга и CLI."""

from __future__ import annotations

import io
import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from s365 import cli, scope, score


class ScopeParseTests(unittest.TestCase):
    def test_splits_in_and_out_of_scope_sections(self) -> None:
        desc = textwrap.dedent(
            """
            ## Область действия
            - *.shop.ru
            - api.shop.ru
            - okko.tv

            ## Вне области действия
            - legacy.shop.ru
            - dev.shop.kz
            """
        )
        inside, outside = scope.parse(desc)
        self.assertEqual(inside, ["*.shop.ru", "api.shop.ru", "okko.tv"])
        self.assertEqual(outside, ["dev.shop.kz", "legacy.shop.ru"])

    def test_out_of_scope_wins_over_in_scope(self) -> None:
        desc = textwrap.dedent(
            """
            ## В scope
            - pay.example-bank.ru
            - admin.example-bank.ru (не принимаем)
            """
        )
        inside, outside = scope.parse(desc)
        self.assertEqual(inside, ["pay.example-bank.ru"])
        self.assertEqual(outside, ["admin.example-bank.ru"])

    def test_filters_noise_domains(self) -> None:
        desc = textwrap.dedent(
            """
            ## В scope
            Скачать приложение можно на play.google.com и apps.apple.com.
            Основной домен: portal.company.by. Писать в t.me.
            """
        )
        inside, outside = scope.parse(desc)
        self.assertEqual(inside, ["portal.company.by"])
        self.assertEqual(outside, [])

    def test_empty_description(self) -> None:
        self.assertEqual(scope.parse(""), ([], []))


class ScoreAndCliTests(unittest.TestCase):
    def test_rank_prefers_active_program_with_scope(self) -> None:
        raw = [
            {
                "slug": "dead",
                "name": "Dead",
                "status": "published",
                "finished": False,
                "terms": "only_vuln",
                "description": "## В scope\napp.dead.ru",
                "statistics": {
                    "reportsAccepted": 0,
                    "reportsTotal": 20,
                    "rewards": {"rub": {"max": 500_000}},
                },
            },
            {
                "slug": "alive",
                "name": "Alive",
                "status": "published",
                "finished": False,
                "terms": "only_vuln",
                "description": "## В scope\n*.alive.ru\napi.alive.ru",
                "rating": {"value": 4.8},
                "statistics": {
                    "reportsAccepted": 40,
                    "reportsTotal": 50,
                    "avgFirstResponseSeconds": 18_000,
                    "lastAcceptedReportDate": "2026-11-01",
                    "rewards": {"rub": {"max": 300_000, "averageBounty": 35_000}},
                },
            },
        ]
        ranked = score.rank(raw)
        self.assertEqual([p.slug for p in ranked], ["alive", "dead"])

    def test_cli_scope_finds_risks_program_without_terms_flag(self) -> None:
        catalog = [
            {
                "slug": "risk-target",
                "name": "Risk Target",
                "status": "published",
                "finished": False,
                "terms": "only_risks",
                "description": "## В scope\napp.risk-target.ru",
                "statistics": {},
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main([str(path), "--scope", "risk-target"])
            self.assertEqual(rc, 0)
            self.assertIn("app.risk-target.ru", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
