from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import LotteryResult
from .scraper import _source_rank, is_better_result


def load_results(path: Path) -> list[LotteryResult]:
    if not path.exists():
        return []
    raw_results = json.loads(path.read_text(encoding="utf-8"))
    return [LotteryResult.from_dict(item) for item in raw_results]


def save_results(path: Path, results: list[LotteryResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(results, key=lambda item: (item.draw_date, item.lottery, item.draw), reverse=True)
    payload = [item.to_dict() for item in ordered]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remove_future_republished_results(
    existing: list[LotteryResult],
    authoritative_results: list[LotteryResult],
) -> list[LotteryResult]:
    authoritative_dates: dict[tuple[str, str, tuple[int, ...]], date] = {}
    for result in authoritative_results:
        key = (result.lottery, result.draw, result.numbers)
        if key not in authoritative_dates or result.draw_date > authoritative_dates[key]:
            authoritative_dates[key] = result.draw_date

    return [
        result
        for result in existing
        if result.draw_date <= authoritative_dates.get((result.lottery, result.draw, result.numbers), result.draw_date)
    ]


def supersedes_stored(fresh: LotteryResult, stored: LotteryResult) -> bool:
    """Decide si una captura recién hecha sustituye a lo ya guardado.

    Conéctate corrige resultados después de publicarlos, y esas correcciones
    llegan con las mismas 3 bolas, así que "gana el más completo" no basta: sin
    esto, el dato viejo y erróneo se queda para siempre aunque la ventana de
    scraping vuelva a traer el bueno cada día.

    No sustituye si trae menos bolas (sería una captura a medias) ni si viene de
    una fuente menos fiable (una planilla no pisa a conéctate).
    """
    if len(fresh.numbers) < len(stored.numbers):
        return False
    return _source_rank(fresh.source) <= _source_rank(stored.source)


def merge_results(existing: list[LotteryResult], new_results: list[LotteryResult]) -> list[LotteryResult]:
    best: dict[str, LotteryResult] = {}
    existing = remove_future_republished_results(existing, new_results)
    for result in existing:
        current = best.get(result.key)
        if current is None or is_better_result(result, current):
            best[result.key] = result
    # Las capturas nuevas van después y pueden corregir lo guardado.
    for result in new_results:
        current = best.get(result.key)
        if current is None or supersedes_stored(result, current):
            best[result.key] = result
    return list(best.values())
