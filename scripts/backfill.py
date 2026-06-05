from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lottery_predictor.analysis import build_predictions
from lottery_predictor.scraper import scrape_conectate_range, scrape_yelu_history
from lottery_predictor.site import build_site
from lottery_predictor.storage import load_results, merge_results, save_results


DATA_PATH = Path("data/results.json")
DOCS_PATH = Path("docs")


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga histórico disponible desde el año indicado.")
    parser.add_argument("--from", dest="from_date", default="2010-01-01")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=DOCS_PATH)
    args = parser.parse_args()

    start_year = datetime.strptime(args.from_date, "%Y-%m-%d").date().year
    start_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    today = datetime.today().date()
    existing = load_results(args.data)
    historical = scrape_conectate_range(start_date=start_date, end_date=today)
    historical.extend(scrape_yelu_history(start_year=start_year))
    merged = merge_results(existing, historical)
    save_results(args.data, merged)
    build_site(build_predictions(merged, requested_from_date=args.from_date), args.output)

    print(f"Fecha objetivo: {args.from_date}")
    print(f"Resultados existentes: {len(existing)}")
    print(f"Resultados históricos descargados: {len(historical)}")
    print(f"Resultados totales: {len(merged)}")
    if merged:
        print(f"Fecha real más antigua: {min(result.draw_date for result in merged)}")
        print(f"Fecha real más reciente: {max(result.draw_date for result in merged)}")


if __name__ == "__main__":
    main()
