from datetime import date

from lottery_predictor.analysis import analyze_base_10, backtest_draw, is_base_visible_draw, suggest_numbers
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
    assert is_base_visible_draw("La Primera", "Lotería La Primera 12PM")
    assert not is_base_visible_draw("Leidsa", "Super Kino TV")
    assert not is_base_visible_draw("La Primera", "Loto 5")


def test_analyze_base_10_uses_only_visible_base_draws():
    results = [
        LotteryResult("La Primera", "Loto 5", date(2010, 8, 1), (1, 2, 3), "test"),
        LotteryResult("La Primera", "Loto 5", date(2010, 8, 2), (1, 2, 3), "test"),
        LotteryResult("La Primera", "Loto 5", date(2010, 8, 3), (1, 2, 3), "test"),
        LotteryResult("La Primera", "La Primera Día", date(2010, 8, 1), (88, 89, 90), "test"),
        LotteryResult("La Primera", "La Primera Día", date(2026, 5, 2), (88, 91, 92), "test"),
    ]

    report = analyze_base_10(results)
    top_numbers = {item["number"] for item in report["top_10_repeated"]}

    assert report["window"]["from"] == "2010-08-01"
    assert report["window"]["to"] == "2026-05-02"
    assert "88" in top_numbers
    assert "01" not in top_numbers
