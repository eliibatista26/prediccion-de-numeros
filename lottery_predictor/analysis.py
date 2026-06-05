from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .models import LotteryResult


@dataclass(frozen=True)
class NumberSuggestion:
    number: int
    score: float
    frequency: int
    delay_days: int | None
    recent_frequency: int


def build_predictions(
    results: list[LotteryResult],
    limit: int = 10,
    requested_from_date: str = "2010-08-01",
) -> dict[str, object]:
    generated_at = datetime.now(ZoneInfo("Europe/Madrid"))
    grouped: dict[str, list[LotteryResult]] = defaultdict(list)
    for result in results:
        grouped[result.lottery].append(result)

    lotteries = {}
    for lottery, lottery_results in sorted(grouped.items()):
        suggestions = suggest_numbers(lottery_results, limit=limit)
        lotteries[lottery] = {
            "suggestions": [
                {
                    "number": f"{item.number:02d}",
                    "score": round(item.score, 2),
                    "frequency": item.frequency,
                    "delay_days": item.delay_days,
                    "recent_frequency": item.recent_frequency,
                }
                for item in suggestions
            ],
            "last_results": [result.to_dict() for result in sorted(lottery_results, key=lambda item: item.draw_date, reverse=True)[:8]],
            "total_results": len(lottery_results),
        }

    return {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "generated_at_display": generated_at.strftime("%d/%m/%Y %H:%M"),
        "generated_timezone": "Europe/Madrid",
        "requested_from_date": requested_from_date,
        "actual_from_date": min((result.draw_date for result in results), default=None).isoformat() if results else None,
        "actual_to_date": max((result.draw_date for result in results), default=None).isoformat() if results else None,
        "disclaimer": "Estas sugerencias son estadísticas y no garantizan resultados.",
        "lotteries": lotteries,
    }


def suggest_numbers(results: list[LotteryResult], limit: int = 10) -> list[NumberSuggestion]:
    if not results:
        return []

    all_counts: Counter[int] = Counter()
    recent_counts: Counter[int] = Counter()
    last_seen: dict[int, date] = {}
    ordered = sorted(results, key=lambda item: item.draw_date, reverse=True)

    for index, result in enumerate(ordered):
        for number in result.numbers:
            all_counts[number] += 1
            if index < 30:
                recent_counts[number] += 1
            last_seen.setdefault(number, result.draw_date)

    today = date.today()
    suggestions: list[NumberSuggestion] = []
    for number in range(100):
        frequency = all_counts[number]
        recent_frequency = recent_counts[number]
        delay_days = (today - last_seen[number]).days if number in last_seen else None
        delay_score = min(delay_days or 365, 365) / 365
        score = frequency * 1.0 + recent_frequency * 1.8 + delay_score * 3.0
        if frequency == 0 and recent_frequency == 0:
            score *= 0.25
        suggestions.append(
            NumberSuggestion(
                number=number,
                score=score,
                frequency=frequency,
                delay_days=delay_days,
                recent_frequency=recent_frequency,
            )
        )

    return sorted(suggestions, key=lambda item: (item.score, item.frequency, item.recent_frequency), reverse=True)[:limit]
