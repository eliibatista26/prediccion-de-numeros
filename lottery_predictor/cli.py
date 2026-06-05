from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import build_predictions
from . import db
from .scraper import scrape_all_sources
from .site import build_site
from .storage import load_results, merge_results, save_results


DATA_PATH = Path("data/results.json")
DOCS_PATH = Path("docs")


def _migrate_json_to_db(json_path: Path) -> None:
    if not json_path.exists():
        return
    historical = load_results(json_path)
    if not historical:
        return
    print(f"Primera ejecución con DB: migrando {len(historical)} resultados del JSON histórico...")
    inserted = db.save_results(historical)
    print(f"Migración completada: {inserted} filas insertadas en Neon.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza resultados y genera la página estática.")
    parser.add_argument("--skip-scrape", action="store_true", help="Solo genera la página con los datos existentes.")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=DOCS_PATH)
    args = parser.parse_args()

    using_db = db.is_available()

    if using_db:
        print("Modo: base de datos PostgreSQL (Neon)")
        db.setup()
        existing = db.load_results()
        if not existing:
            _migrate_json_to_db(args.data)
            existing = db.load_results()
    else:
        print("Modo: archivo JSON local")
        existing = load_results(args.data)

    new_results = [] if args.skip_scrape else scrape_all_sources()

    if using_db:
        if new_results:
            inserted = db.save_results(new_results)
            print(f"Resultados nuevos insertados en DB: {inserted}")
        all_results = db.load_results()
    else:
        all_results = merge_results(existing, new_results)
        save_results(args.data, all_results)

    build_site(build_predictions(all_results), args.output)
    print(f"Resultados existentes: {len(existing)}")
    print(f"Resultados nuevos del scraper: {len(new_results)}")
    print(f"Resultados totales: {len(all_results)}")
    print(f"Página generada en: {args.output}")


if __name__ == "__main__":
    main()
