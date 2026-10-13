"""Ранжирование программ.

Сортировка по максимальной выплате — худший доступный критерий: максимум платят за то, чего
в программе нет, а реальный исход определяют доля принятых отчётов, ширина скоупа и то,
жива ли программа вообще.

Веса подобраны руками и спорны по построению. Меняй под себя — это и есть смысл того,
что они собраны в одном месте.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any

from . import scope as _scope

WEIGHTS = {
    "max_reward": 1 / 100_000,   # за каждые 100k максимальной выплаты — 1 балл
    "accept_rate": 1 / 20,       # 100% принятых — 5 баллов
    "wildcard": 1.5,             # за каждый wildcard-домен, не больше 8 штук
    "domains": 1 / 6,            # за каждый домен, не больше 30 штук
    "rating": 1 / 2,             # рейтинг программы
    "recent_bonus": 3.0,         # есть принятый отчёт за последние полгода
    "fast_response_bonus": 2.0,  # первый ответ быстрее 48 часов
}

RECENT_DAYS = 180
FAST_RESPONSE_HOURS = 48


@dataclass
class Program:
    slug: str
    name: str
    terms: str
    max_reward: int | None = None
    avg_reward: int = 0
    accepted: int = 0
    total: int = 0
    rating: float | None = None
    response_hours: float | None = None
    last_accepted: str = ""
    in_scope: list[str] = field(default_factory=list)
    out_scope: list[str] = field(default_factory=list)

    @property
    def accept_rate(self) -> int | None:
        return round(100 * self.accepted / self.total) if self.total else None

    @property
    def wildcards(self) -> list[str]:
        return [d for d in self.in_scope if d.startswith("*.")]

    @property
    def score(self) -> float:
        w = WEIGHTS
        s = 0.0
        s += (self.max_reward or 0) * w["max_reward"]
        s += (self.accept_rate or 0) * w["accept_rate"]
        s += min(len(self.wildcards), 8) * w["wildcard"]
        s += min(len(self.in_scope), 30) * w["domains"]
        s += (self.rating or 0) * w["rating"]
        if self._is_recent():
            s += w["recent_bonus"]
        if self.response_hours is not None and self.response_hours < FAST_RESPONSE_HOURS:
            s += w["fast_response_bonus"]
        return round(s, 2)

    def _is_recent(self) -> bool:
        if not self.last_accepted:
            return False
        try:
            seen = _dt.date.fromisoformat(self.last_accepted[:10])
        except ValueError:
            return False
        return (_dt.date.today() - seen).days <= RECENT_DAYS


def _hours(seconds: Any) -> float | None:
    return round(seconds / 3600, 1) if seconds else None


def build(raw: dict[str, Any]) -> Program:
    """Собрать Program из записи каталога."""
    stats = raw.get("statistics") or {}
    rewards = ((stats.get("rewards") or {}).get("rub") or {})
    inside, outside = _scope.parse(raw.get("description") or "")

    return Program(
        slug=raw.get("slug", "?"),
        name=raw.get("name", "?"),
        terms=raw.get("terms", ""),
        max_reward=rewards.get("max"),
        avg_reward=round(rewards.get("averageBounty") or 0),
        accepted=stats.get("reportsAccepted") or 0,
        total=stats.get("reportsTotal") or 0,
        rating=(raw.get("rating") or {}).get("value"),
        response_hours=_hours(stats.get("avgFirstResponseSeconds")),
        last_accepted=(stats.get("lastAcceptedReportDate") or "")[:10],
        in_scope=inside,
        out_scope=outside,
    )


def rank(programs: list[dict[str, Any]]) -> list[Program]:
    return sorted((build(p) for p in programs), key=lambda p: -p.score)
