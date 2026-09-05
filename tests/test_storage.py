from datetime import date

from lottery_predictor.models import LotteryResult
from lottery_predictor.storage import merge_results, remove_future_republished_results


def test_merge_results_keeps_repeated_numbers_on_different_dates():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (16, 40, 34), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (16, 40, 34), "new"),
    ]

    merged = merge_results(existing, scraped)

    assert len(merged) == 2
    assert {result.draw_date for result in merged} == {date(2026, 6, 5), date(2026, 6, 6)}


def test_merge_results_keeps_changed_numbers_for_new_date():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (16, 40, 34), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (5, 74, 93), "new"),
    ]

    merged = merge_results(existing, scraped)

    assert len(merged) == 2


def test_merge_results_removes_future_copy_when_source_reports_older_date():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (5, 74, 93), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (5, 74, 93), "new"),
    ]

    merged = merge_results(existing, scraped)

    assert len(merged) == 1
    assert merged[0].draw_date == date(2026, 6, 5)


def test_remove_future_republished_results_keeps_unrelated_future_results():
    existing = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 6), (5, 74, 93), "old"),
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 6, 6), (22, 37, 40), "old"),
    ]
    scraped = [
        LotteryResult("Leidsa", "Quiniela Leidsa", date(2026, 6, 5), (5, 74, 93), "new"),
    ]

    cleaned = remove_future_republished_results(existing, scraped)

    assert len(cleaned) == 1
    assert cleaned[0].draw == "Quiniela Loteka"


CONECTATE = "https://www.conectate.com.do/loterias/"


def test_merge_applies_source_correction_with_same_ball_count():
    """Conéctate corrige resultados ya publicados manteniendo las 3 bolas."""
    existing = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (4, 19, 76), CONECTATE),
    ]
    scraped = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (3, 10, 71), CONECTATE),
    ]

    merged = merge_results(existing, scraped)

    assert len(merged) == 1
    assert merged[0].numbers == (3, 10, 71)


def test_merge_never_replaces_with_a_truncated_result():
    existing = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (3, 10, 71), CONECTATE),
    ]
    scraped = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (3, 10), CONECTATE),
    ]

    merged = merge_results(existing, scraped)

    assert merged[0].numbers == (3, 10, 71)


def test_merge_does_not_let_a_spreadsheet_overwrite_conectate():
    existing = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (3, 10, 71), CONECTATE),
    ]
    planilla = [
        LotteryResult("Loteka", "Quiniela Loteka", date(2026, 9, 4), (1, 2, 3), "xlsm_spreadsheet"),
    ]

    merged = merge_results(existing, planilla)

    assert merged[0].numbers == (3, 10, 71)
