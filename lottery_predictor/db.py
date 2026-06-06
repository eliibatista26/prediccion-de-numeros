from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from .models import LotteryResult

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
    return psycopg2.connect(DATABASE_URL, connect_timeout=30)


def setup() -> None:
    print(f"Conectando a Neon... (URL: {'SET' if DATABASE_URL else 'NOT SET'}, longitud: {len(DATABASE_URL)})")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
        conn.commit()
    print("Tabla lottery_results lista.")


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
    rows = [
        (r.key, r.lottery, r.draw, r.draw_date, list(r.numbers), r.source)
        for r in results
    ]
    BATCH = 500
    total_inserted = 0
    with _connect() as conn:
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO lottery_results (result_key, lottery, draw, draw_date, numbers, source)
                    VALUES %s
                    ON CONFLICT (result_key) DO NOTHING
                    """,
                    batch,
                )
                total_inserted += cur.rowcount
            conn.commit()
            if (i // BATCH) % 10 == 0:
                print(f"  Insertados {i + len(batch)}/{len(rows)} registros...")
    return total_inserted
