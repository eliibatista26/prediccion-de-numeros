from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import build_predictions
from .scraper import scrape_all_sources
from .site import build_site
from .storage import load_results, merge_results, save_results


DATA_PATH = Path("data/results.json")
DOCS_PATH = Path("docs")


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza resultados y genera la página estática.")
    parser.add_argument("--skip-scrape", action="store_true", help="Solo genera la página con los datos existentes.")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=DOCS_PATH)
    args = parser.parse_args()

    existing = load_results(args.data)
    new_results = [] if args.skip_scrape else scrape_all_sources()
    merged = merge_results(existing, new_results)
    save_results(args.data, merged)
    build_site(build_predictions(merged), args.output)
    print(f"Resultados existentes: {len(existing)}")
    print(f"Resultados nuevos: {len(new_results)}")
    print(f"Resultados totales: {len(merged)}")
    print(f"Página generada en: {args.output}")


if __name__ == "__main__":
    main()
