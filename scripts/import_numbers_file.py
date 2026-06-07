#!/usr/bin/env python3
"""
Importa datos del archivo Apple Numbers a data/results.json.

Archivo fuente: NACIONAL Y GANAMAS 1999 AL 2026.numbers
Sorteos que importa:
  - NACIONAL  → Lotería Nacional / Lotería Nacional
  - GANA MAS  → Lotería Nacional / Gana Más

Reglas de deduplicación:
  - Si ya existe un registro para la misma fecha + sorteo en conectate.com.do,
    se respeta el de conectate (más fiable).
  - Si solo existe en la planilla, se añade con source='numbers_spreadsheet'.
  - 100 → 00 (normalización estándar de la lotería).

Uso:
    python scripts/import_numbers_file.py
    python scripts/import_numbers_file.py --dry-run   # solo cuenta, no guarda
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from numbers_parser import Document

from lottery_predictor.models import LotteryResult
from lottery_predictor.storage import load_results, save_results

NUMBERS_FILE = Path("NACIONAL Y GANAMAS 1999 AL 2026.numbers")
DATA_PATH = Path("data/results.json")
TODAY = datetime.date.today()

# Mapping de nombre en planilla → (lottery canónico, draw canónico)
DRAW_MAP = {
    "NACIONAL": ("Lotería Nacional", "Lotería Nacional"),
    "GANA MAS": ("Lotería Nacional", "Gana Más"),
}

SOURCE = "numbers_spreadsheet"


def _normalize_num(val) -> int | None:
    """Convierte valor de celda a número 0-99. 100 → 0."""
    try:
        n = int(float(val))
        if n == 100:
            n = 0
        if 0 <= n <= 99:
            return n
    except (TypeError, ValueError):
        pass
    return None


def read_numbers_file(path: Path) -> list[LotteryResult]:
    """Lee el archivo .numbers y devuelve LotteryResults válidos."""
    print(f"Abriendo {path} ...")
    doc = Document(str(path))
    sheets = list(doc.sheets)

    # Las 3 primeras hojas son idénticas; usamos solo Hoja 1
    table = list(sheets[0].tables)[0]
    rows = list(table.iter_rows())
    print(f"  Filas en Hoja 1: {len(rows)}")

    results: list[LotteryResult] = []
    skipped = 0

    for row in rows:
        vals = [cell.value for cell in row]
        if len(vals) < 6:
            skipped += 1
            continue

        raw_date = vals[1]
        draw_name = str(vals[5]).strip().upper() if vals[5] is not None else ""

        # Solo fechas datetime válidas (no texto, no futuro)
        if not isinstance(raw_date, datetime.datetime):
            skipped += 1
            continue
        d = raw_date.date()
        if d > TODAY or d.year < 1990:
            skipped += 1
            continue

        # Solo los sorteos que queremos
        canonical = DRAW_MAP.get(draw_name)
        if canonical is None:
            skipped += 1
            continue

        lottery, draw = canonical

        # Números en posiciones 2, 3, 4
        nums = []
        for col_idx in (2, 3, 4):
            n = _normalize_num(vals[col_idx]) if col_idx < len(vals) else None
            if n is None:
                break
            nums.append(n)

        if len(nums) < 3:
            skipped += 1
            continue

        results.append(LotteryResult(
            lottery=lottery,
            draw=draw,
            draw_date=d,
            numbers=tuple(nums),
            source=SOURCE,
        ))

    print(f"  Registros válidos leídos: {len(results)} | Omitidos: {skipped}")
    return results


def merge_with_priority(
    existing: list[LotteryResult],
    spreadsheet: list[LotteryResult],
) -> tuple[list[LotteryResult], int, int]:
    """
    Fusiona conservando conectate.com.do como fuente preferida.
    Retorna (merged_list, added, skipped_due_to_conflict).
    """
    # Clave única por fecha + sorteo
    existing_keys: dict[str, LotteryResult] = {}
    for r in existing:
        key = f"{r.draw_date.isoformat()}|{r.lottery}|{r.draw}"
        existing_keys[key] = r

    added = 0
    skipped_conflict = 0

    for r in spreadsheet:
        key = f"{r.draw_date.isoformat()}|{r.lottery}|{r.draw}"
        if key in existing_keys:
            # Ya existe → solo reemplazar si existente viene de planilla
            existing_source = existing_keys[key].source
            if existing_source == SOURCE:
                existing_keys[key] = r  # actualiza planilla con planilla (no cambia nada)
            else:
                skipped_conflict += 1  # respeta conectate / otra fuente
        else:
            existing_keys[key] = r
            added += 1

    merged = sorted(existing_keys.values(), key=lambda x: (x.draw_date, x.lottery, x.draw))
    return merged, added, skipped_conflict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo cuenta, no guarda")
    parser.add_argument("--file", type=Path, default=NUMBERS_FILE)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: No se encontró {args.file}")
        sys.exit(1)

    # Leer planilla
    spreadsheet_results = read_numbers_file(args.file)

    # Cargar datos existentes
    print(f"\nCargando {args.data} ...")
    existing = load_results(args.data)
    print(f"  Registros existentes: {len(existing)}")

    # Fusionar
    print("\nFusionando ...")
    merged, added, conflicts = merge_with_priority(existing, spreadsheet_results)

    # Estadísticas de fecha
    from_dates = [r.draw_date for r in merged]
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Resultado:")
    print(f"  Nuevos registros añadidos de la planilla: {added}")
    print(f"  Omitidos (ya existen en conectate):       {conflicts}")
    print(f"  Total tras fusión:                        {len(merged)}")
    if from_dates:
        print(f"  Rango de fechas: {min(from_dates)} → {max(from_dates)}")

    # Desglose por sorteo de lo añadido
    new_only = [r for r in merged if r.source == SOURCE]
    by_draw: dict[str, int] = {}
    for r in new_only:
        k = f"{r.lottery} / {r.draw}"
        by_draw[k] = by_draw.get(k, 0) + 1
    print("\n  Registros con source='numbers_spreadsheet' en el JSON final:")
    for k, v in sorted(by_draw.items()):
        print(f"    {k}: {v}")

    if not args.dry_run:
        save_results(args.data, merged)
        print(f"\n✅ Guardado en {args.data}")
    else:
        print("\n[DRY RUN] No se guardó nada.")


if __name__ == "__main__":
    main()
