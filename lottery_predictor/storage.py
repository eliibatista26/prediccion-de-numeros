from __future__ import annotations

import json
from pathlib import Path

from .models import LotteryResult


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


def merge_results(existing: list[LotteryResult], new_results: list[LotteryResult]) -> list[LotteryResult]:
    merged = {result.key: result for result in existing}
    for result in new_results:
        merged[result.key] = result
    return list(merged.values())

