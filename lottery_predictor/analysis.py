from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

from .models import LotteryResult
from .utils import clean_text, normalize_text

BASE_LOTTERIES = {
    "La Primera",
    "La Suerte Dominicana",
    "Leidsa",
    "Lotedom",
    "Loteka",
    "Lotería Nacional",
    "Lotería Real",
}

BASE_VISIBLE_DRAWS = {
    "Lotería Nacional": {
        "Gana Más",
        "Lotería Gana Más",
        "Lotería Nacional",
        "Nacional Noche",
        "Quiniela Nacional",
    },
    "Leidsa": {
        "Quiniela Leidsa",
    },
    "Lotería Real": {
        "Quiniela Real",
    },
    "Loteka": {
        "Quiniela Loteka",
    },
    "La Primera": {
        "La Primera Día",
        "La Primera Noche",
        "Lotería La Primera 12PM",
        "Lotería La Primera Noche 8PM",
        "Primera Noche",
    },
    "La Suerte Dominicana": {
        "La Suerte 12:30",
        "La Suerte 18:00",
        "La Suerte 6PM",
        "La Suerte MD",
    },
    "Lotedom": {
        "LoteDom",
        "Quiniela LoteDom",
        "Quiniela Lotedom",
    },
}

BASE_DRAW_ALIASES = {
    "la suerte 12:30": "La Suerte MD",
    "la suerte 18:00": "La Suerte 6PM",
    "loteria gana mas": "Gana Más",
    "loteria la primera 12pm": "La Primera Día",
    "loteria la primera noche 8pm": "La Primera Noche",
    "nacional noche": "Lotería Nacional",
    "quiniela nacional": "Lotería Nacional",
    "primera noche": "La Primera Noche",
    "quiniela lotedom": "LoteDom",
}

BASE_ANALYSIS_FROM = date(2010, 8, 1)
COMPARE_RESULTS_LIMIT = 99999  # all history — aggregated by month in site.py
MIRRORS = {number: int(f"{number:02d}"[::-1]) for number in range(100)}


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
    generated_at = datetime.now(ZoneInfo("America/Santo_Domingo"))
    grouped: dict[str, list[LotteryResult]] = defaultdict(list)
    for result in results:
        grouped[result.lottery].append(result)

    lotteries = {}
    for lottery, lottery_results in sorted(grouped.items()):
        suggestions = suggest_numbers(lottery_results, limit=limit)
        draw_groups: dict[str, list[LotteryResult]] = defaultdict(list)
        for result in lottery_results:
            draw_groups[result.draw].append(result)
        lotteries[lottery] = {
            "suggestions": _serialize_suggestions(suggestions),
            "last_results": [result.to_dict() for result in sorted(lottery_results, key=lambda item: item.draw_date, reverse=True)[:8]],
            "compare_daily": _compare_daily_results(lottery_results),
            "compare_results": [
                result.to_dict()
                for result in sorted(lottery_results, key=lambda item: item.draw_date, reverse=True)[:COMPARE_RESULTS_LIMIT]
            ],
            "total_results": len(lottery_results),
            "draws": {
                draw: {
                    "suggestions": _serialize_suggestions(suggest_numbers(draw_results, limit=limit)),
                    "last_results": [result.to_dict() for result in sorted(draw_results, key=lambda item: item.draw_date, reverse=True)[:8]],
                    "total_results": len(draw_results),
                    "backtest": backtest_draw(draw_results, limit=limit),
                }
                for draw, draw_results in sorted(draw_groups.items())
            },
        }

    return {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "generated_at_display": generated_at.strftime("%d/%m/%Y %H:%M"),
        "generated_timezone": "America/Santo_Domingo",
        "requested_from_date": requested_from_date,
        "actual_from_date": min((result.draw_date for result in results), default=None).isoformat() if results else None,
        "actual_to_date": max((result.draw_date for result in results), default=None).isoformat() if results else None,
        "disclaimer": "Estas sugerencias son estadísticas y no garantizan resultados.",
        "base_10": analyze_base_10(results),
        "lotteries": lotteries,
    }


def _serialize_suggestions(suggestions: list[NumberSuggestion]) -> list[dict[str, object]]:
    return [
        {
            "number": f"{item.number:02d}",
            "score": round(item.score, 2),
            "frequency": item.frequency,
            "delay_days": item.delay_days,
            "recent_frequency": item.recent_frequency,
        }
        for item in suggestions
    ]


def _compare_daily_results(results: list[LotteryResult]) -> list[list[object]]:
    """Lista compacta [fecha YYYYMMDD, n1, n2, n3] por sorteo.
    Permite filtrar en JS por día del mes, día de la semana y rango de fechas,
    conservando el orden de posiciones (1ra, 2da, 3ra)."""
    rows: list[list[object]] = []
    for result in sorted(results, key=lambda item: item.draw_date):
        nums = [int(n) for n in result.numbers[:3]]
        if not nums:
            continue
        rows.append([result.draw_date.strftime("%Y%m%d"), *nums])
    return rows


def suggest_numbers(
    results: list[LotteryResult],
    limit: int = 10,
    reference_date: date | None = None,
) -> list[NumberSuggestion]:
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

    today = reference_date or date.today()
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


def backtest_draw(
    results: list[LotteryResult],
    limit: int = 10,
    window_days: int = 60,
    min_history: int = 30,
) -> dict[str, object]:
    ordered = sorted(results, key=lambda item: item.draw_date)
    if len(ordered) <= min_history:
        return {
            "status": "insufficient",
            "window_days": window_days,
            "tested_draws": 0,
            "message": f"Necesita al menos {min_history + 1} resultados para validar.",
        }

    max_date = ordered[-1].draw_date
    cutoff = date.fromordinal(max_date.toordinal() - window_days)
    targets = [result for result in ordered if result.draw_date >= cutoff]

    tested = 0
    top3_any_hits = 0
    top5_any_hits = 0
    first_position_hits = 0
    total_hits_top5 = 0
    evaluated_rows: list[dict[str, object]] = []

    for target in targets:
        prior = [result for result in ordered if result.draw_date < target.draw_date]
        if len(prior) < min_history:
            continue
        predictions = suggest_numbers(prior, limit=limit, reference_date=target.draw_date)
        predicted_top3 = {item.number for item in predictions[:3]}
        predicted_top5 = {item.number for item in predictions[:5]}
        actual_numbers = set(target.numbers[:3])
        hits_top5 = sorted(actual_numbers & predicted_top5)
        tested += 1
        top3_any_hits += int(bool(actual_numbers & predicted_top3))
        top5_any_hits += int(bool(hits_top5))
        first_position_hits += int(bool(target.numbers and target.numbers[0] in predicted_top5))
        total_hits_top5 += len(hits_top5)
        evaluated_rows.append(
            {
                "date": target.draw_date.isoformat(),
                "actual": [f"{number:02d}" for number in target.numbers[:3]],
                "predicted": [f"{item.number:02d}" for item in predictions[:5]],
                "hits": [f"{number:02d}" for number in hits_top5],
            }
        )

    if tested == 0:
        return {
            "status": "insufficient",
            "window_days": window_days,
            "tested_draws": 0,
            "message": "No hay suficientes resultados recientes con histórico previo.",
        }

    top5_rate = top5_any_hits / tested
    if tested < 20:
        label = "Muestra baja"
    elif top5_rate >= 0.35:
        label = "Alta"
    elif top5_rate >= 0.18:
        label = "Media"
    else:
        label = "Baja"

    return {
        "status": "ok",
        "window_days": window_days,
        "tested_draws": tested,
        "top3_any_hit_rate": round(top3_any_hits / tested, 3),
        "top5_any_hit_rate": round(top5_rate, 3),
        "first_position_hit_rate": round(first_position_hits / tested, 3),
        "average_hits_top5": round(total_hits_top5 / tested, 2),
        "confidence_label": label,
        "recent_evaluations": evaluated_rows[-5:],
    }


def analyze_base_10(results: list[LotteryResult]) -> dict[str, object]:
    base_results = [
        result
        for result in results
        if result.lottery in BASE_LOTTERIES
        and is_base_visible_draw(result.lottery, result.draw)
        and result.draw_date >= BASE_ANALYSIS_FROM
        and len(result.numbers) >= 3
    ]
    analysis_to = max((result.draw_date for result in base_results), default=BASE_ANALYSIS_FROM)
    recent_7_from = analysis_to - timedelta(days=6)
    recent_30_from = analysis_to - timedelta(days=29)
    ordered = sorted(base_results, key=lambda item: (item.draw_date, item.lottery, item.draw))
    latest_first = list(reversed(ordered))
    total_counts: Counter[int] = Counter()
    recent_7_counts: Counter[int] = Counter()
    recent_30_counts: Counter[int] = Counter()
    position_counts = [Counter(), Counter(), Counter()]
    last_seen_position: list[dict[int, date]] = [dict(), dict(), dict()]
    by_day: dict[date, list[LotteryResult]] = defaultdict(list)
    by_lottery: dict[str, list[LotteryResult]] = defaultdict(list)
    pair_counts: Counter[tuple[int, int]] = Counter()
    recent_pair_counts: Counter[tuple[int, int]] = Counter()

    for result in ordered:
        by_day[result.draw_date].append(result)
        by_lottery[result.lottery].append(result)
        for number in result.numbers[:3]:
            total_counts[number] += 1
            if result.draw_date >= recent_30_from:
                recent_30_counts[number] += 1
            if result.draw_date >= recent_7_from:
                recent_7_counts[number] += 1
        for index, number in enumerate(result.numbers[:3]):
            position_counts[index][number] += 1
            last_seen_position[index][number] = result.draw_date
        for pair in combinations(sorted(set(result.numbers[:3])), 2):
            pair_counts[pair] += 1
            if result.draw_date >= recent_30_from:
                recent_pair_counts[pair] += 1

    recent_counts: Counter[int] = Counter()
    for result in latest_first[:80]:
        if result.draw_date >= recent_30_from:
            recent_counts.update(result.numbers[:3])

    coincidences: Counter[int] = Counter()
    recent_coincidences: Counter[int] = Counter()
    for day_results in by_day.values():
        day_map: dict[int, set[str]] = defaultdict(set)
        for result in day_results:
            for number in result.numbers[:3]:
                day_map[number].add(result.lottery)
        for number, lotteries in day_map.items():
            if len(lotteries) > 1:
                coincidences[number] += len(lotteries)
                if day_results[0].draw_date >= recent_30_from:
                    recent_coincidences[number] += len(lotteries)

    drags: Counter[int] = Counter()
    recent_drags: Counter[int] = Counter()
    previous_numbers: set[int] = set()
    previous_date: date | None = None
    for result in ordered:
        current_numbers = set(result.numbers[:3])
        if previous_date is not None and (result.draw_date - previous_date).days <= 1:
            for number in current_numbers & previous_numbers:
                drags[number] += 1
                if result.draw_date >= recent_30_from:
                    recent_drags[number] += 1
        previous_numbers = current_numbers
        previous_date = result.draw_date

    moves: Counter[int] = Counter()
    recent_moves: Counter[int] = Counter()
    for number in range(100):
        lotteries_with_number = {
            result.lottery
            for result in base_results
            if number in result.numbers[:3]
        }
        if len(lotteries_with_number) > 1:
            moves[number] = len(lotteries_with_number)
        recent_lotteries_with_number = {
            result.lottery
            for result in base_results
            if result.draw_date >= recent_30_from and number in result.numbers[:3]
        }
        if len(recent_lotteries_with_number) > 1:
            recent_moves[number] = len(recent_lotteries_with_number)

    mirror_counts: Counter[int] = Counter()
    recent_mirror_counts: Counter[int] = Counter()
    for number, count in total_counts.items():
        mirror = MIRRORS[number]
        if mirror != number and total_counts[mirror] > 0:
            mirror_counts[number] = count + total_counts[mirror]
        if mirror != number and recent_30_counts[mirror] > 0:
            recent_mirror_counts[number] = recent_30_counts[number] + recent_30_counts[mirror]

    strength_rows = []
    for number in range(100):
        frequency = total_counts[number]
        if frequency == 0:
            continue
        score = (
            frequency * 0.08
            + recent_counts[number] * 3.0
            + recent_30_counts[number] * 7.0
            + recent_7_counts[number] * 10.0
            + recent_coincidences[number] * 4.0
            + recent_drags[number] * 3.5
            + recent_mirror_counts[number] * 1.0
            + recent_moves[number] * 4.0
            + coincidences[number] * 0.15
            + drags[number] * 0.15
            + mirror_counts[number] * 0.03
            + moves[number] * 0.5
        )
        strength_rows.append(
            {
                "number": f"{number:02d}",
                "score": round(score, 2),
                "frequency": frequency,
                "recent": recent_counts[number],
                "recent_7": recent_7_counts[number],
                "recent_30": recent_30_counts[number],
                "coincidences": coincidences[number],
                "drags": drags[number],
                "mirror": f"{MIRRORS[number]:02d}",
                "moves": moves[number],
            }
        )
    strength_rows.sort(key=lambda item: (item["score"], item["recent_7"], item["recent_30"], item["frequency"]), reverse=True)

    top_counter = recent_30_counts if recent_30_counts else total_counts
    top_10 = [{"number": f"{number:02d}", "count": count} for number, count in top_counter.most_common(10)]
    delayed_by_position = {
        str(index + 1): _delayed_rows(last_seen_position[index], analysis_to, position_counts[index])
        for index in range(3)
    }
    elite = strength_rows[:5]
    leader = strength_rows[0] if strength_rows else None
    bullet_pair = (recent_pair_counts or pair_counts).most_common(1)

    DRAW_CANONICAL = {
        "Lotería Nacional": {"Gana Más": "Gana Más", "Lotería Nacional": "Nacional Noche"},
        "Leidsa": {"Quiniela Leidsa": "Leidsa"},
        "Lotería Real": {"Quiniela Real": "Real"},
        "Loteka": {"Quiniela Loteka": "Loteka"},
        "La Primera": {"La Primera Día": "La Primera Día", "La Primera Noche": "La Primera Noche",
                       "Primera Noche": "La Primera Noche", "Lotería La Primera 12PM": "La Primera Día",
                       "Lotería La Primera Noche 8PM": "La Primera Noche"},
        "La Suerte Dominicana": {"La Suerte MD": "La Suerte MD", "La Suerte 6PM": "La Suerte 6PM",
                                  "La Suerte 12:30": "La Suerte MD", "La Suerte 18:00": "La Suerte 6PM"},
        "Lotedom": {"LoteDom": "Lotedom", "Quiniela LoteDom": "Lotedom", "Quiniela Lotedom": "Lotedom"},
    }

    delayed_by_lottery: dict[str, dict[str, list[dict[str, object]]]] = {}
    by_draw_label: dict[str, list[LotteryResult]] = defaultdict(list)
    for result in base_results:
        draw_map = DRAW_CANONICAL.get(result.lottery, {})
        label = draw_map.get(result.draw)
        if label:
            by_draw_label[label].append(result)

    for label, draw_results in sorted(by_draw_label.items()):
        pos_last_seen: list[dict[int, date]] = [dict(), dict(), dict()]
        pos_counts: list[Counter] = [Counter(), Counter(), Counter()]
        for r in sorted(draw_results, key=lambda x: x.draw_date):
            for idx, n in enumerate(r.numbers[:3]):
                pos_last_seen[idx][n] = r.draw_date
                pos_counts[idx][n] += 1
        positions = {}
        for idx in range(3):
            rows = sorted(
                [{"number": f"{n:02d}", "delay_days": (analysis_to - d).days, "frequency": pos_counts[idx][n]}
                 for n, d in pos_last_seen[idx].items()],
                key=lambda x: (-x["delay_days"], -x["frequency"])
            )[:3]
            positions[str(idx + 1)] = rows
        delayed_by_lottery[label] = positions

    return {
        "window": {
            "from": BASE_ANALYSIS_FROM.isoformat(),
            "to": analysis_to.isoformat(),
            "results": len(base_results),
        },
        "top_10_repeated": top_10,
        "top_10_historical": [{"number": f"{number:02d}", "count": count} for number, count in total_counts.most_common(10)],
        "delayed_by_position": delayed_by_position,
        "delayed_by_lottery": delayed_by_lottery,
        "coincidences": [{"number": f"{number:02d}", "count": count} for number, count in coincidences.most_common(10)],
        "drags": [{"number": f"{number:02d}", "count": count} for number, count in drags.most_common(10)],
        "active_mirrors": _active_mirror_pairs(base_results, analysis_to),
        "moving_numbers": [{"number": f"{number:02d}", "lotteries": count} for number, count in moves.most_common(10)],
        "frequent_pairs": [{"pair": [f"{a:02d}", f"{b:02d}"], "count": count} for (a, b), count in pair_counts.most_common(10)],
        "strength_ranking": strength_rows[:10],
        "elite_group": elite,
        "leader": leader,
        "bullet_pair": {"pair": [f"{bullet_pair[0][0][0]:02d}", f"{bullet_pair[0][0][1]:02d}"], "count": bullet_pair[0][1]} if bullet_pair else None,
    }


def _active_mirror_pairs(results: list[LotteryResult], reference_date: date) -> list[dict[str, object]]:
    cutoff = reference_date - timedelta(days=14)
    last_seen: dict[int, date] = {}
    for r in sorted(results, key=lambda x: x.draw_date):
        for n in r.numbers[:3]:
            last_seen[n] = r.draw_date
    pairs = []
    seen = set()
    for n in range(100):
        m = MIRRORS[n]
        if m == n or (m, n) in seen:
            continue
        seen.add((n, m))
        d1 = last_seen.get(n)
        d2 = last_seen.get(m)
        if d1 and d2 and d1 >= cutoff and d2 >= cutoff:
            diff = abs((d1 - d2).days)
            pairs.append({
                "number": f"{n:02d}",
                "mirror": f"{m:02d}",
                "diff_days": diff,
                "days_ago_a": (reference_date - d1).days,
                "days_ago_b": (reference_date - d2).days,
            })
    return sorted(pairs, key=lambda x: (x["diff_days"], x["days_ago_a"]))[:12]


def _delayed_rows(last_seen: dict[int, date], reference_date: date, counts: Counter[int]) -> list[dict[str, object]]:
    rows = []
    for number, seen in last_seen.items():
        delay = (reference_date - seen).days
        rows.append(
            {
                "number": f"{number:02d}",
                "delay_days": delay,
                "last_seen": seen.isoformat(),
                "frequency": counts[number],
            }
        )
    return sorted(rows, key=lambda item: (item["delay_days"], item["frequency"]), reverse=True)[:10]


def is_base_visible_draw(lottery_name: str, draw: str) -> bool:
    visible = BASE_VISIBLE_DRAWS.get(lottery_name, set())
    if not visible:
        return False
    draw_key = normalize_text(draw)
    visible_keys = {normalize_text(item) for item in visible}
    alias = BASE_DRAW_ALIASES.get(draw_key)
    return draw_key in visible_keys or bool(alias and normalize_text(alias) in visible_keys)
