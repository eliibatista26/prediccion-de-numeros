from datetime import date

from lottery_predictor.models import LotteryResult
from lottery_predictor.storage import discard_republished_results, merge_results


def test_discard_republished_results_keeps_original_date_when_numbers_are_reused():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (16, 40, 34), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (16, 40, 34), "new"),
    ]

    assert discard_republished_results(existing, scraped) == []
    merged = merge_results(existing, scraped)

    assert len(merged) == 1
    assert merged[0].draw_date == date(2026, 6, 5)


def test_discard_republished_results_keeps_changed_numbers_for_new_date():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (16, 40, 34), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (5, 74, 93), "new"),
    ]

    filtered = discard_republished_results(existing, scraped)

    assert filtered == scraped

