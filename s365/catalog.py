"""Загрузка каталога программ.

Каталог — это JSON-выгрузка со списком программ: список объектов либо объект
с полем ``items``/``results``/``programs``. Как её получить — см. README;
инструмент ничего сам никуда не запрашивает и работает с локальным файлом.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load(path: str | Path) -> list[dict[str, Any]]:
    """Прочитать каталог и вернуть список программ."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if isinstance(data, dict):
        for key in ("items", "results", "programs", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # словарь вида {slug: program}
            data = list(data.values())

    if not isinstance(data, list):
        raise ValueError("не удалось разобрать каталог: ожидался список программ")

    return [p for p in data if isinstance(p, dict)]


def active(programs: list[dict[str, Any]], exclude: set[str] | None = None) -> list[dict[str, Any]]:
    """Оставить только опубликованные и незавершённые программы."""
    exclude = exclude or set()
    out = []
    for p in programs:
        if p.get("status") != "published" or p.get("finished"):
            continue
        if p.get("slug") in exclude:
            continue
        out.append(p)
    return out
