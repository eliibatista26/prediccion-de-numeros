#!/usr/bin/env python3
"""
Repasa un rango de fechas contra conéctate y corrige lo que haya guardado mal.

Para qué sirve: conéctate corrige resultados después de publicarlos. La corrida
diaria solo mira los últimos días (SCRAPE_WINDOW_DAYS), así que una corrección
que llegue más tarde no se aplica nunca. Este script repasa un rango amplio.

Cuánto alcanza: la API retiene varios meses, no solo días. Comprobado el 6 de
septiembre de 2026: responde desde abril de 2026 y devuelve vacío en marzo y
antes. El límite se mueve con el tiempo, así que conviene ejecutarlo de vez en
cuando en vez de esperar a necesitarlo.

Usa la misma regla de merge que el pipeline: un resultado recién capturado
sustituye al guardado salvo que traiga menos bolas, y una planilla nunca pisa a
conéctate.

Uso:
    python3 scripts/reparar_desde_api.py --desde 2026-04-01
    python3 scripts/reparar_desde_api.py --desde 2026-04-01 --hasta 2026-06-30
    python3 scripts/reparar_desde_api.py --desde 2026-04-01 --dry-run
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lottery_predictor.scraper import scrape_conectate_range
from lottery_predictor.storage import load_results, merge_results, save_results

DATA_PATH = Path("data/results.json")


def fecha(texto: str) -> date:
    return datetime.strptime(texto, "%Y-%m-%d").date()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", type=fecha, required=True, help="AAAA-MM-DD")
    parser.add_argument("--hasta", type=fecha, default=date.today(), help="AAAA-MM-DD (por defecto hoy)")
    parser.add_argument("--dry-run", action="store_true", help="Solo informa, no guarda.")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if args.desde > args.hasta:
        print("El rango está invertido.")
        return 1

    guardados = load_results(DATA_PATH)
    previo = {resultado.key: resultado.numbers for resultado in guardados}

    print(f"Consultando conéctate de {args.desde} a {args.hasta}...")
    frescos = scrape_conectate_range(args.desde, args.hasta, workers=args.workers)
    print(f"Resultados devueltos: {len(frescos)}")
    if not frescos:
        print("La API no devolvió nada; probablemente el rango queda fuera de su retención.")
        return 0

    fusionado = merge_results(guardados, frescos)
    ahora = {resultado.key: resultado.numbers for resultado in fusionado}

    corregidos = [clave for clave, valor in ahora.items() if clave in previo and previo[clave] != valor]
    nuevos = set(ahora) - set(previo)

    print(f"\nRegistros corregidos: {len(corregidos)}")
    print(f"Registros nuevos:     {len(nuevos)}")
    print(f"Total: {len(guardados)} -> {len(fusionado)}")

    if corregidos:
        por_año = Counter(clave.split("|")[0][:4] for clave in corregidos)
        print("  corregidos por año:", dict(sorted(por_año.items())))
        print("  ejemplos:")
        for clave in sorted(corregidos)[:5]:
            print(f"    {clave}: {list(previo[clave])} -> {list(ahora[clave])}")

    if args.dry_run:
        print("\n--dry-run: no se guardó nada.")
        return 0

    save_results(DATA_PATH, fusionado)
    print(f"\nGuardado en {DATA_PATH}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
