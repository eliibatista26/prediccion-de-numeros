import json

from lottery_predictor.cli import preserve_existing_base_10


def test_preserve_existing_base_10_reuses_previous_predictions(tmp_path):
    output = tmp_path / "docs"
    output.mkdir()
    previous_base_10 = {
        "elite_group": [{"number": "41"}],
        "window": {"to": "2026-06-05"},
    }
    (output / "predictions.json").write_text(
        json.dumps({"base_10": previous_base_10}),
        encoding="utf-8",
    )
    predictions = {
        "base_10": {
            "elite_group": [{"number": "99"}],
            "window": {"to": "2026-06-06"},
        },
    }

    preserved = preserve_existing_base_10(predictions, output)

    assert preserved is True
    assert predictions["base_10"] == previous_base_10
