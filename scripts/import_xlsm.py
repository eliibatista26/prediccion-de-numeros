#!/usr/bin/env python3
"""
Importa histórico de quinielas desde la planilla Excel.

Archivo fuente: TODAS LAS LOTERIAS 1999 AL 2015 2.xlsm (pese al nombre, varias
hojas llegan a 2024).

Cada hoja mezcla varias series en la columna LOTERIA, y hay que elegirlas a mano
porque los nombres no son fiables:
  - LOTEKA contiene 'LOTEKA' (la quiniela nocturna, que es la que analizamos) y
    'LOTEKA DIA', que es un sorteo distinto.
  - REAL contiene 'REAL' y 'REAL NOCHE', que resultaron ser el MISMO sorteo
    duplicado: coinciden 1.846 de 1.846 fechas de 2011 en adelante y solo
    difieren en 71 fechas de 2010, el arranque de la serie. Se usan las dos,
    con 'REAL' mandando en los choques por ser la que llega hasta 2024.

Por qué hace falta: la API de conéctate retiene unos meses (en septiembre de
2026 alcanzaba abril de 2026), así que los días anteriores a eso que el scraper
no capturó en su momento solo pueden venir de aquí.

Reglas:
  - NUNCA pisa un registro existente; solo añade fechas que faltan. Al cruzar
    planilla y datos guardados discrepan en torno al 5%, y sin una tercera
    fuente no se puede saber cuál acierta.
  - 100 → 00 (normalización estándar de la lotería).
  - Fechas fuera de 1999-2026 se descartan: la planilla tiene erratas de tecleo
    con años como 2998 o 1900.
  - source='xlsm_spreadsheet', por debajo de conéctate en _source_rank.

Uso:
    python3 scripts/import_xlsm.py --sorteo todos --dry-run
    python3 scripts/import_xlsm.py --sorteo real
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl

from lottery_predictor.models import LotteryResult
from lottery_predictor.storage import load_results, save_results

XLSM_FILE = Path("TODAS LAS LOTERIAS 1999 AL 2015 2.xlsm")
DATA_PATH = Path("data/results.json")
SOURCE = "xlsm_spreadsheet"
AÑOS_VALIDOS = range(1999, 2027)

# sorteo -> (hoja, series en orden de prioridad, lotería, nombre canónico)
SORTEOS = {
    "loteka": ("LOTEKA", ["LOTEKA"], "Loteka", "Quiniela Loteka"),
    "real": ("REAL", ["REAL", "REAL NOCHE"], "Lotería Real", "Quiniela Real"),
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}


def _normalizar(texto: object) -> str:
    plano = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", plano).strip().lower()


def parse_fecha(valor: object) -> date | None:
    """Lee '30 de julio de 2009', '20 de agosto del 2009' y '24-Ago-2023'."""
    if isinstance(valor, date):
        return valor if valor.year in AÑOS_VALIDOS else None
    texto = _normalizar(valor)
    match = (
        re.search(r"(\d{1,2})\s+de\s+([a-z]+)\s+del?\s+(\d{4})", texto)
        or re.search(r"(\d{1,2})-([a-z]{3,})-(\d{4})", texto)
    )
    if not match:
        return None
    mes = MESES.get(match.group(2))
    if not mes:
        return None
    try:
        fecha = date(int(match.group(3)), mes, int(match.group(1)))
    except ValueError:
        return None
    return fecha if fecha.year in AÑOS_VALIDOS else None


def parse_numero(valor: object) -> int | None:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        return None
    if numero == 100:
        numero = 0
    return numero if 0 <= numero <= 99 else None


def leer_hoja(libro, hoja: str, series: list[str]) -> tuple[dict[date, tuple[int, ...]], Counter]:
    filas = libro[hoja].iter_rows(min_row=2, max_col=6, values_only=True)
    # Una serie solo rellena lo que la anterior no trajo: la primera manda.
    por_serie: dict[str, dict[date, tuple[int, ...]]] = {serie: {} for serie in series}
    descartes: Counter = Counter()

    for fila in filas:
        _, cruda, n1, n2, n3, etiqueta = fila[:6]
        serie = str(etiqueta).strip().upper()
        if serie not in por_serie:
            descartes["otra serie"] += 1
            continue
        fecha = parse_fecha(cruda)
        if fecha is None:
            descartes["fecha ilegible o absurda"] += 1
            continue
        numeros = [parse_numero(valor) for valor in (n1, n2, n3)]
        if any(numero is None for numero in numeros):
            descartes["números inválidos"] += 1
            continue
        por_serie[serie].setdefault(fecha, tuple(numeros))

    sorteos: dict[date, tuple[int, ...]] = {}
    for serie in reversed(series):          # la primera de la lista se aplica al final
        sorteos.update(por_serie[serie])
    return sorteos, descartes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sorteo", choices=[*SORTEOS, "todos"], default="todos")
    parser.add_argument("--dry-run", action="store_true", help="Solo informa, no guarda.")
    args = parser.parse_args()

    if not XLSM_FILE.exists():
        print(f"No se encontró {XLSM_FILE}")
        return 1

    libro = openpyxl.load_workbook(XLSM_FILE, read_only=True, data_only=True)
    guardados = load_results(DATA_PATH)
    nuevos: list[LotteryResult] = []

    elegidos = list(SORTEOS) if args.sorteo == "todos" else [args.sorteo]
    for clave in elegidos:
        hoja, series, lottery, draw = SORTEOS[clave]
        planilla, descartes = leer_hoja(libro, hoja, series)
        ya_tenemos = {
            resultado.draw_date
            for resultado in guardados
            if resultado.lottery == lottery and resultado.draw == draw
        }
        faltantes = sorted(set(planilla) - ya_tenemos)

        print(f"\n=== {draw} (hoja {hoja}, series {series}) ===")
        print(f"  planilla: {len(planilla)} fechas legibles ({min(planilla)} .. {max(planilla)})")
        for motivo, cuantos in descartes.most_common():
            print(f"    descartadas por {motivo}: {cuantos}")
        print(f"  ya guardadas: {len(ya_tenemos)}")
        print(f"  aporta:       {len(faltantes)}")
        if faltantes:
            por_año = Counter(fecha.year for fecha in faltantes)
            print("    por año:", dict(sorted(por_año.items())))

        nuevos.extend(
            LotteryResult(lottery, draw, fecha, planilla[fecha], SOURCE)
            for fecha in faltantes
        )

    if args.dry_run:
        print(f"\n--dry-run: se habrían añadido {len(nuevos)} registros.")
        return 0
    if not nuevos:
        print("\nNada que importar.")
        return 0

    save_results(DATA_PATH, guardados + nuevos)
    print(f"\nGuardado. Registros en {DATA_PATH}: {len(guardados) + len(nuevos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
