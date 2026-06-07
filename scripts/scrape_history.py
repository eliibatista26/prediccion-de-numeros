#!/usr/bin/env python3
"""
Scraping histórico de conectate.com.do desde 2010-08-01 hasta hoy.

Sorteos objetivo (los 10 que le interesan al cliente):
  1. Lotería Nacional  - Gana Más
  2. Lotería Nacional  - Lotería Nacional (noche)
  3. Leidsa            - Quiniela Leidsa
  4. Lotería Real      - Quiniela Real
  5. Loteka            - Quiniela Loteka
  6. La Primera        - La Primera Día
  7. La Primera        - La Primera Noche
  8. La Suerte Dom.    - La Suerte MD
  9. La Suerte Dom.    - La Suerte 6PM
 10. Lotedom           - LoteDom

Uso:
    python scripts/scrape_history.py
    python scripts/scrape_history.py --start 2015-01-01   # desde fecha específica
    python scripts/scrape_history.py --workers 4           # más lento, menos riesgo de bloqueo
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lottery_predictor.models import LotteryResult
from lottery_predictor.scraper import scrape_conectate_date
from lottery_predictor.storage import load_results, save_results
from lottery_predictor.utils import normalize_text

# ── Loterías y sorteos que queremos ──────────────────────────────────────────
# Clave: (lottery normalizada, draw normalizada)   Valor: (lottery canónica, draw canónica)
WANTED: dict[tuple[str, str], tuple[str, str]] = {
    # Lotería Nacional
    ("loteria nacional", "gana mas"):                ("Lotería Nacional", "Gana Más"),
    ("loteria nacional", "loteria gana mas"):        ("Lotería Nacional", "Gana Más"),
    ("loteria nacional", "loteria nacional"):        ("Lotería Nacional", "Lotería Nacional"),
    ("loteria nacional", "nacional noche"):          ("Lotería Nacional", "Lotería Nacional"),
    ("loteria nacional", "quiniela nacional"):       ("Lotería Nacional", "Lotería Nacional"),
    # Leidsa
    ("leidsa", "quiniela leidsa"):                   ("Leidsa", "Quiniela Leidsa"),
    # Lotería Real
    ("loteria real", "quiniela real"):               ("Lotería Real", "Quiniela Real"),
    # Loteka
    ("loteka", "quiniela loteka"):                   ("Loteka", "Quiniela Loteka"),
    # La Primera
    ("la primera", "la primera dia"):                ("La Primera", "La Primera Día"),
    ("la primera", "loteria la primera 12pm"):       ("La Primera", "La Primera Día"),
    ("la primera", "la primera noche"):              ("La Primera", "La Primera Noche"),
    ("la primera", "primera noche"):                 ("La Primera", "La Primera Noche"),
    ("la primera", "loteria la primera noche 8pm"):  ("La Primera", "La Primera Noche"),
    # La Suerte Dominicana
    ("la suerte dominicana", "la suerte md"):        ("La Suerte Dominicana", "La Suerte MD"),
    ("la suerte dominicana", "la suerte 12:30"):     ("La Suerte Dominicana", "La Suerte MD"),
    ("la suerte dominicana", "la suerte 6pm"):       ("La Suerte Dominicana", "La Suerte 6PM"),
    ("la suerte dominicana", "la suerte 18:00"):     ("La Suerte Dominicana", "La Suerte 6PM"),
    # Lotedom
    ("lotedom", "lotedom"):                          ("Lotedom", "LoteDom"),
    ("lotedom", "quiniela lotedom"):                 ("Lotedom", "LoteDom"),
    ("lotedom", "quiniela loteDom"):                 ("Lotedom", "LoteDom"),
}

DATA_PATH = Path("data/results.json")
START_DATE = date(2010, 8, 1)


def _wanted(result: LotteryResult) -> tuple[str, str] | None:
    """Devuelve (lottery, draw) canónico si el resultado es de los 10 sorteos objetivo."""
    lottery_key = normalize_text(result.lottery)
    draw_key = normalize_text(result.draw)
    return WANTED.get((lottery_key, draw_key))


def _normalize_result(result: LotteryResult) -> LotteryResult | None:
    """Devuelve un LotteryResult con nombres canónicos, o None si no interesa."""
    canonical = _wanted(result)
    if canonical is None:
        return None
    lottery, draw = canonical
    return LotteryResult(
        lottery=lottery,
        draw=draw,
        draw_date=result.draw_date,
        numbers=result.numbers,
        source=result.source,
    )


def scrape_day(d: date) -> list[LotteryResult]:
    """Scrape un día y devuelve solo los sorteos objetivo."""
    try:
        raw = scrape_conectate_date(d)
        normalized = [_normalize_result(r) for r in raw]
        return [r for r in normalized if r is not None]
    except Exception as exc:
        print(f"  ⚠  {d}: {exc}")
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraping histórico de conectate.com.do")
    parser.add_argument("--start", default=str(START_DATE), help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--end", default=str(date.today()), help="Fecha fin YYYY-MM-DD")
    parser.add_argument("--workers", type=int, default=6, help="Hilos paralelos (default 6)")
    parser.add_argument("--batch", type=int, default=60, help="Días por lote antes de guardar")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    # ── Cargar datos existentes y filtrar solo los 10 sorteos objetivo ────────
    print("Cargando datos existentes...")
    existing_raw = load_results(DATA_PATH)

    # Normalizar y filtrar: solo los 10 sorteos que queremos
    best: dict[str, LotteryResult] = {}
    for r in existing_raw:
        normalized = _normalize_result(r)
        if normalized is not None:
            key = f"{normalized.draw_date.isoformat()}|{normalized.lottery}|{normalized.draw}"
            best[key] = normalized

    print(f"Datos existentes (filtrados): {len(best)} registros")

    # Fechas que ya están cubiertas (tienen al menos Nacional o Leidsa ese día)
    covered_dates: set[date] = set()
    for r in best.values():
        if normalize_text(r.lottery) in ("loteria nacional", "leidsa"):
            covered_dates.add(r.draw_date)

    # Todas las fechas a procesar
    all_dates = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)) not in covered_dates
    ]

    if not all_dates:
        print("✅ No hay fechas nuevas que procesar. El historial ya está completo.")
        return

    print(f"Fechas a procesar: {len(all_dates)} "
          f"(desde {all_dates[0]} hasta {all_dates[-1]})")
    print(f"Trabajadores: {args.workers} | Lote: {args.batch} días")
    print()

    total_new = 0
    batch_dates = [
        all_dates[i : i + args.batch]
        for i in range(0, len(all_dates), args.batch)
    ]

    for batch_num, batch in enumerate(batch_dates, 1):
        batch_new = 0
        t0 = time.time()
        print(f"Lote {batch_num}/{len(batch_dates)}: {batch[0]} → {batch[-1]} ...", end=" ", flush=True)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(scrape_day, d): d for d in batch}
            for future in as_completed(futures):
                results = future.result()
                for r in results:
                    key = f"{r.draw_date.isoformat()}|{r.lottery}|{r.draw}"
                    if key not in best:
                        best[key] = r
                        batch_new += 1
                    # Prefer same-day results over off-day results
                    elif r.draw_date == futures[future] and best[key].draw_date != futures[future]:
                        best[key] = r
                        batch_new += 1

        elapsed = time.time() - t0
        total_new += batch_new
        print(f"{batch_new} nuevos | {elapsed:.1f}s")

        # Guardar después de cada lote
        all_results = list(best.values())
        save_results(DATA_PATH, all_results)
        print(f"  💾 Guardado: {len(all_results)} registros totales (acumulado nuevo: {total_new})")

    print()
    print(f"✅ Scraping completado: {total_new} registros nuevos añadidos.")
    print(f"   Total en data/results.json: {len(best)}")


if __name__ == "__main__":
    main()
