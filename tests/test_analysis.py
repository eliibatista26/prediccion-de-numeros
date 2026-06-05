from datetime import date

from lottery_predictor.analysis import suggest_numbers
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

