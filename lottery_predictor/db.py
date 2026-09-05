from __future__ import annotations

import os

import psycopg2
import psycopg2.extensions
import psycopg2.extras

from .models import LotteryResult
from .scraper import CONNECTATE_LOTERIAS_URL

# Literal SQL de la fuente primaria: solo conéctate puede corregir un
# resultado ya guardado que tenga el mismo número de bolas.
_PRIMARY_SOURCE = psycopg2.extensions.adapt(CONNECTATE_LOTERIAS_URL).getquoted().decode()

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS lottery_results (
    id          BIGSERIAL PRIMARY KEY,
    result_key  TEXT UNIQUE NOT NULL,
    lottery     TEXT NOT NULL,
    draw        TEXT NOT NULL,
    draw_date   DATE NOT NULL,
    numbers     INTEGER[] NOT NULL,
    source      TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lr_draw_date ON lottery_results (draw_date DESC);
CREATE INDEX IF NOT EXISTS idx_lr_lottery   ON lottery_results (lottery);
"""


def is_available() -> bool:
    return bool(DATABASE_URL)


def _connect():
    # client_encoding explícito: si no, psycopg2 hereda el locale del sistema y
    # los nombres con tilde ("Lotería Nacional") fallan al codificar.
    return psycopg2.connect(DATABASE_URL, connect_timeout=30, client_encoding="UTF8")


def setup() -> None:
    print(f"Conectando a Neon... (URL: {'SET' if DATABASE_URL else 'NOT SET'}, longitud: {len(DATABASE_URL)})")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
        conn.commit()
    print("Tabla lottery_results lista.")


def truncate() -> None:
    """Borra todos los registros de la tabla (para empezar de cero)."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE lottery_results RESTART IDENTITY;")
        conn.commit()
    print("Tabla lottery_results vaciada.")


def load_results() -> list[LotteryResult]:
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT lottery, draw, draw_date, numbers, source "
                "FROM lottery_results ORDER BY draw_date DESC, lottery, draw"
            )
            rows = cur.fetchall()
    return [
        LotteryResult(
            lottery=row["lottery"],
            draw=row["draw"],
            draw_date=row["draw_date"],
            numbers=tuple(row["numbers"]),
            source=row["source"],
        )
        for row in rows
    ]


def save_results(results: list[LotteryResult]) -> int:
    if not results:
        return 0
    # Postgres rechaza un ON CONFLICT DO UPDATE que toque la misma fila dos
    # veces, así que un lote no puede traer la clave repetida. Ante el choque,
    # nos quedamos con el resultado más completo.
    unique: dict[str, LotteryResult] = {}
    for result in results:
        current = unique.get(result.key)
        if current is None or len(result.numbers) > len(current.numbers):
            unique[result.key] = result
    rows = [
        (r.key, r.lottery, r.draw, r.draw_date, list(r.numbers), r.source)
        for r in unique.values()
    ]
    BATCH = 500
    total_written = 0
    with _connect() as conn:
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            with conn.cursor() as cur:
                # Se pisa el sorteo guardado en dos casos: cuando el nuevo trae
                # más números (captura a medias que se completa) y cuando la
                # fuente primaria publica una corrección con las mismas bolas.
                # Nunca con menos números ni desde una planilla.
                psycopg2.extras.execute_values(
                    cur,
                    f"""
                    INSERT INTO lottery_results (result_key, lottery, draw, draw_date, numbers, source)
                    VALUES %s
                    ON CONFLICT (result_key) DO UPDATE
                        SET numbers = EXCLUDED.numbers,
                            source  = EXCLUDED.source
                        WHERE cardinality(EXCLUDED.numbers)
                              > cardinality(lottery_results.numbers)
                           OR (
                                cardinality(EXCLUDED.numbers)
                                  = cardinality(lottery_results.numbers)
                                AND EXCLUDED.numbers
                                    IS DISTINCT FROM lottery_results.numbers
                                AND EXCLUDED.source = {_PRIMARY_SOURCE}
                              )
                    """,
                    batch,
                    page_size=len(batch),
                )
                total_written += cur.rowcount
            conn.commit()
            if (i // BATCH) % 10 == 0:
                print(f"  Procesados {i + len(batch)}/{len(rows)} registros...")
    return total_written
