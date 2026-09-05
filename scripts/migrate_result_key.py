"""Migra result_key al formato sin números.

Antes la clave incluía los números sorteados, así que un mismo sorteo capturado
a medias (2 de 3 bolas) y luego completo quedaba como dos filas distintas y la
versión rota nunca se corregía. La clave nueva identifica el sorteo
(fecha|lotería|sorteo), de modo que el UPSERT de db.save_results puede pisar el
resultado incompleto.

El script deja una fila por sorteo, quedándose siempre con la más completa.
Es idempotente: correrlo dos veces no cambia nada la segunda vez.

    DATABASE_URL='postgres://...' python3 scripts/migrate_result_key.py --dry-run
    DATABASE_URL='postgres://...' python3 scripts/migrate_result_key.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lottery_predictor import db
from lottery_predictor.analysis import ANALYSIS_DRAWS, ANALYSIS_NUMBERS

NEW_KEY_SQL = "draw_date::text || '|' || lottery || '|' || draw"

# De cada grupo (fecha, lotería, sorteo) borra todas menos la mejor: primero la
# que tenga más números, y a igualdad la de id más bajo (la primera guardada).
DELETE_DUPLICATES = """
DELETE FROM lottery_results a
USING lottery_results b
WHERE a.draw_date = b.draw_date
  AND a.lottery   = b.lottery
  AND a.draw      = b.draw
  AND (
        cardinality(a.numbers) < cardinality(b.numbers)
     OR (cardinality(a.numbers) = cardinality(b.numbers) AND a.id > b.id)
  )
"""

COUNT_DUPLICATES = """
SELECT COALESCE(SUM(copias - 1), 0) FROM (
    SELECT COUNT(*) AS copias
    FROM lottery_results
    GROUP BY draw_date, lottery, draw
    HAVING COUNT(*) > 1
) AS grupos
"""

COUNT_STALE_KEYS = f"SELECT COUNT(*) FROM lottery_results WHERE result_key <> {NEW_KEY_SQL}"

REWRITE_KEYS = f"""
UPDATE lottery_results
SET result_key = {NEW_KEY_SQL}
WHERE result_key <> {NEW_KEY_SQL}
"""

TRUNCATED_QUINIELAS = """
SELECT draw_date, lottery, draw, numbers
FROM lottery_results
WHERE lottery = ANY(%s)
  AND draw = ANY(%s)
  AND cardinality(numbers) < %s
  -- Si existe una copia más completa del mismo sorteo, la migración se queda
  -- con ella; solo interesan los que se quedan cortos de verdad.
  AND NOT EXISTS (
      SELECT 1 FROM lottery_results mejor
      WHERE mejor.draw_date = lottery_results.draw_date
        AND mejor.lottery   = lottery_results.lottery
        AND mejor.draw      = lottery_results.draw
        AND cardinality(mejor.numbers) > cardinality(lottery_results.numbers)
  )
ORDER BY draw_date DESC
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo informa, no modifica nada.")
    args = parser.parse_args()

    if not db.is_available():
        print("DATABASE_URL no está definida. Exporta la cadena de Neon y vuelve a correr.")
        return 1

    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM lottery_results")
            total_before = cur.fetchone()[0]
            cur.execute(COUNT_DUPLICATES)
            duplicates = cur.fetchone()[0]
            cur.execute(COUNT_STALE_KEYS)
            stale_keys = cur.fetchone()[0]

            print(f"Filas actuales:            {total_before}")
            print(f"Duplicados a eliminar:     {duplicates}")
            print(f"Claves a reescribir:       {stale_keys}")

            cur.execute(
                TRUNCATED_QUINIELAS,
                (
                    sorted(ANALYSIS_DRAWS),
                    sorted({draw for draws in ANALYSIS_DRAWS.values() for draw in draws}),
                    ANALYSIS_NUMBERS,
                ),
            )
            truncated = cur.fetchall()
            if truncated:
                print(f"\nQuinielas incompletas que quedarán en la tabla ({len(truncated)}):")
                for draw_date, lottery, draw, numbers in truncated:
                    print(f"  {draw_date} {lottery} | {draw} -> {numbers}")
                print("El scraper las completará sola la próxima vez que las publique conéctate.")

            if args.dry_run:
                print("\n--dry-run: no se modificó nada.")
                return 0

            if not duplicates and not stale_keys:
                print("\nNada que migrar, la tabla ya está en el formato nuevo.")
                return 0

            cur.execute(DELETE_DUPLICATES)
            deleted = cur.rowcount
            cur.execute(REWRITE_KEYS)
            rewritten = cur.rowcount
            cur.execute("SELECT COUNT(*) FROM lottery_results")
            total_after = cur.fetchone()[0]
        conn.commit()

    print(f"\nFilas eliminadas:          {deleted}")
    print(f"Claves reescritas:         {rewritten}")
    print(f"Filas finales:             {total_after}")
    print("Migración completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
