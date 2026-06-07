from __future__ import annotations

import argparse
import json
import os
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
        print("No se encontró data/results.json para migrar.")
        return
    historical = load_results(json_path)
    if not historical:
        print("El JSON está vacío, nada que migrar.")
        return
    print(f"Primera ejecución con DB: migrando {len(historical)} resultados del JSON histórico...")
    inserted = db.save_results(historical)
    print(f"Migración completada: {inserted} filas insertadas en Neon.")


def preserve_existing_base_10(predictions: dict[str, object], output_path: Path) -> bool:
    predictions_path = output_path / "predictions.json"
    if not predictions_path.exists():
        return False
    try:
        previous = json.loads(predictions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    previous_base_10 = previous.get("base_10") if isinstance(previous, dict) else None
    if not isinstance(previous_base_10, dict):
        return False
    predictions["base_10"] = previous_base_10
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza resultados y genera la página estática.")
    parser.add_argument("--skip-scrape", action="store_true", help="Solo genera la página con los datos existentes.")
    parser.add_argument(
        "--preserve-base-10",
        action="store_true",
        help="Actualiza resultados visibles sin recalcular Las 10 Base.",
    )
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, default=DOCS_PATH)
    args = parser.parse_args()

    # Diagnóstico del entorno
    raw_url = os.environ.get("DATABASE_URL", "")
    print(f"DATABASE_URL presente en entorno: {'SÍ' if raw_url else 'NO'} (longitud: {len(raw_url)})")

    using_db = db.is_available()

    # Siempre cargamos JSON como base histórica
    json_results = load_results(args.data)
    print(f"Registros en JSON: {len(json_results)}")

    if using_db:
        print("Modo: base de datos PostgreSQL (Neon) + JSON histórico")
        try:
            db.setup()
            db_count = len(db.load_results())
            print(f"Registros en DB: {db_count}")
        except Exception as exc:
            print(f"ERROR conectando a Neon: {exc}")
            print("Continuando solo con JSON local...")
            using_db = False
    else:
        print("Modo: archivo JSON local")

    new_results = [] if args.skip_scrape else scrape_all_sources()

    if using_db:
        # Guardar nuevos resultados en DB (solo acumula nuevos scraping diarios)
        if new_results:
            try:
                inserted = db.save_results(new_results)
                print(f"Resultados nuevos insertados en DB: {inserted}")
            except Exception as exc:
                print(f"ERROR guardando en DB: {exc}")
        # Para el análisis usamos JSON histórico + nuevos resultados de hoy
        all_results = merge_results(json_results, new_results)
        save_results(args.data, all_results)
    else:
        all_results = merge_results(json_results, new_results)
        save_results(args.data, all_results)

    predictions = build_predictions(all_results)
    if args.preserve_base_10:
        preserved = preserve_existing_base_10(predictions, args.output)
        print(f"Base 10 preservada: {'SÍ' if preserved else 'NO'}")
    build_site(predictions, args.output)
    print(f"Registros históricos (JSON): {len(json_results)}")
    print(f"Resultados nuevos del scraper: {len(new_results)}")
    print(f"Resultados totales: {len(all_results)}")
    print(f"Página generada en: {args.output}")


if __name__ == "__main__":
    main()
