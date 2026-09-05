from datetime import date

from lottery_predictor.analysis import (
    analyze_base_10,
    backtest_draw,
    build_predictions,
    is_base_visible_draw,
    suggest_numbers,
)
from lottery_predictor.models import LotteryResult


def test_suggest_numbers_prefers_frequent_recent_numbers():
    results = [
        LotteryResult("Leidsa", "Noche", date(2026, 6, 4), (12, 48, 73), "test"),
        LotteryResult("Leidsa", "Noche", date(2026, 6, 3), (9, 31, 48), "test"),
        LotteryResult("Leidsa", "Noche", date(2026, 6, 2), (48, 20, 1), "test"),
    ]

    suggestions = suggest_numbers(results, limit=3)

    assert suggestions[0].number == 48
    assert len(suggestions) == 3


def test_backtest_draw_returns_hit_rates_with_enough_history():
    results = [
        LotteryResult("Leidsa", "Quiniela", date(2026, 1, day), (12, day % 100, 48), "test")
        for day in range(1, 32)
    ]
    results.extend(
        [
            LotteryResult("Leidsa", "Quiniela", date(2026, 2, 1), (12, 40, 41), "test"),
            LotteryResult("Leidsa", "Quiniela", date(2026, 2, 2), (99, 88, 77), "test"),
        ]
    )

    report = backtest_draw(results, limit=5, window_days=10, min_history=30)

    assert report["status"] == "ok"
    assert report["tested_draws"] == 3
    assert report["top5_any_hit_rate"] > 0


def test_base_visible_draw_filter_excludes_loto_and_kino():
    assert is_base_visible_draw("Leidsa", "Quiniela Leidsa")
    assert is_base_visible_draw("Lotería Nacional", "Quiniela Nacional")
    assert not is_base_visible_draw("Leidsa", "Super Kino TV")
    assert not is_base_visible_draw("Loteka", "MegaLotto")
    assert is_base_visible_draw("Lotería Nacional", "Gana Más")
    # Fuera del alcance: solo las quinielas de ANALYSIS_DRAWS entran al análisis.
    assert not is_base_visible_draw("Lotería Nacional", "Juega + Pega +")
    assert not is_base_visible_draw("La Primera", "La Primera Día")


def test_analyze_base_10_uses_only_visible_base_draws():
    results = [
        LotteryResult("Loteka", "MegaLotto", date(2010, 8, 1), (1, 2, 3), "test"),
        LotteryResult("Loteka", "MegaLotto", date(2010, 8, 2), (1, 2, 3), "test"),
        LotteryResult("Loteka", "MegaLotto", date(2010, 8, 3), (1, 2, 3), "test"),
        LotteryResult("Loteka", "Quiniela Loteka", date(2010, 8, 1), (88, 89, 90), "test"),
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 5, 2), (88, 91, 92), "test"),
    ]

    report = analyze_base_10(results)
    top_numbers = {item["number"] for item in report["top_10_repeated"]}

    assert report["window"]["from"] == "2010-08-01"
    assert report["window"]["to"] == "2026-05-02"
    assert "88" in top_numbers
    assert "01" not in top_numbers


def test_build_predictions_ignores_non_quiniela_draws():
    """Super Kino TV (20 bolas 01-80) sesgaba las frecuencias hacia números bajos."""
    results = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, day), (91, 92, 93), "test")
        for day in range(1, 11)
    ]
    results.extend(
        LotteryResult("Leidsa", "Super Kino TV", date(2026, 6, day), tuple(range(1, 21)), "test")
        for day in range(1, 11)
    )

    predictions = build_predictions(results)
    leidsa = predictions["lotteries"]["Leidsa"]

    assert set(leidsa["draws"]) == {"Quiniela Leidsa"}
    assert leidsa["total_results"] == 10
    frequency = {item["number"]: item["frequency"] for item in leidsa["suggestions"]}
    assert frequency["91"] == 10
    # 01 sale 10 veces en Super Kino TV; si contara, su frecuencia no sería 0.
    assert frequency.get("01", 0) == 0


def test_build_predictions_drops_truncated_results():
    """Un resultado capturado a medias (2 de 3 bolas) no debe contar."""
    results = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 6, 1), (11, 22, 33), "test"),
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 6, 2), (44, 55), "test"),
    ]

    predictions = build_predictions(results)

    assert predictions["lotteries"]["Loteka"]["total_results"] == 1


def test_analyze_base_10_prefers_recent_momentum_over_historical_frequency():
    results = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 1, day), (25, day % 100, 1), "test")
        for day in range(1, 25)
    ]
    results.extend(
        [
            LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 1), (41, 64, 31), "test"),
            LotteryResult("Lotería Nacional", "Lotería Nacional", date(2026, 6, 2), (41, 49, 16), "test"),
            LotteryResult("Loteka", "Quiniela Loteka", date(2026, 6, 3), (41, 38, 70), "test"),
        ]
    )

    report = analyze_base_10(results)

    assert report["elite_group"][0]["number"] == "41"
    assert report["top_10_repeated"][0]["number"] == "41"
