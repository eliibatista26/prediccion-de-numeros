#!/usr/bin/env python3
"""
Importa el histórico de Quiniela Loteka desde la planilla Excel.

Archivo fuente: TODAS LAS LOTERIAS 1999 AL 2015 2.xlsm, hoja LOTEKA.
La hoja mezcla dos series en la columna LOTERIA: 'LOTEKA' (la quiniela nocturna,
que es la que analizamos) y 'LOTEKA DIA' (un sorteo diurno distinto). Solo se
importa la primera.

Por qué hace falta: la API de conéctate no sirve histórico —una fecha de hace un
año devuelve cero sesiones— así que los días que el scraper no capturó en su
momento no se pueden recuperar desde ahí.

Reglas:
  - NUNCA pisa un registro existente. Solo añade fechas que faltan.
    Al cruzar ambas fuentes en las 1.670 fechas comunes discrepan 77 (4,6%),
    y sin una tercera fuente no se puede saber cuál acierta, así que ante la
    duda se conserva lo que ya había.
  - 100 → 00 (normalización estándar de la lotería).
  - source='xlsm_spreadsheet', por debajo de conéctate en _source_rank: si algún
    día llega el dato bueno para esa fecha, gana el de conéctate.

Uso:
    python3 scripts/import_loteka_xlsm.py --dry-run
    python3 scripts/import_loteka_xlsm.py
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
SHEET = "LOTEKA"
SERIE = "LOTEKA"          # excluye 'LOTEKA DIA'
LOTTERY, DRAW = "Loteka", "Quiniela Loteka"
SOURCE = "xlsm_spreadsheet"

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
    """Lee los formatos de la planilla: '30 de julio de 2009', '20 de agosto
    del 2009' y '24-Ago-2023'."""
    if isinstance(valor, date):
        return valor
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
        return date(int(match.group(3)), mes, int(match.group(1)))
    except ValueError:
        return None


def parse_numero(valor: object) -> int | None:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        return None
    if numero == 100:
        numero = 0
    return numero if 0 <= numero <= 99 else None


def leer_planilla(path: Path) -> tuple[dict[date, tuple[int, ...]], Counter]:
    libro = openpyxl.load_workbook(path, read_only=True, data_only=True)
    filas = libro[SHEET].iter_rows(min_row=2, max_col=6, values_only=True)
    sorteos: dict[date, tuple[int, ...]] = {}
    descartes: Counter = Counter()

    for _, cruda, n1, n2, n3, serie in filas:
        if str(serie).strip().upper() != SERIE:
            descartes["otra serie"] += 1
            continue
        fecha = parse_fecha(cruda)
        if fecha is None:
            descartes["fecha ilegible"] += 1
            continue
        numeros = [parse_numero(valor) for valor in (n1, n2, n3)]
        if any(numero is None for numero in numeros):
            descartes["números inválidos"] += 1
            continue
        if fecha in sorteos and sorteos[fecha] != tuple(numeros):
            descartes["fecha repetida en la planilla"] += 1
            continue
        sorteos[fecha] = tuple(numeros)

    return sorteos, descartes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo informa, no guarda.")
    args = parser.parse_args()

    if not XLSM_FILE.exists():
        print(f"No se encontró {XLSM_FILE}")
        return 1

    planilla, descartes = leer_planilla(XLSM_FILE)
    print(f"Planilla: {len(planilla)} sorteos legibles ({min(planilla)} .. {max(planilla)})")
    for motivo, cuantos in descartes.most_common():
        print(f"  descartadas por {motivo}: {cuantos}")

    existentes = load_results(DATA_PATH)
    ya_tenemos = {
        resultado.draw_date
        for resultado in existentes
        if resultado.lottery == LOTTERY and resultado.draw == DRAW
    }

    faltantes = sorted(set(planilla) - ya_tenemos)
    nuevos = [
        LotteryResult(LOTTERY, DRAW, fecha, planilla[fecha], SOURCE)
        for fecha in faltantes
    ]

    print(f"\nQuiniela Loteka en data/results.json: {len(ya_tenemos)} fechas")
    print(f"Fechas que aporta la planilla:        {len(nuevos)}")
    por_año = Counter(fecha.year for fecha in faltantes)
    for año in sorted(por_año):
        print(f"    {año}: {por_año[año]}")

    if args.dry_run:
        print("\n--dry-run: no se guardó nada.")
        return 0
    if not nuevos:
        print("\nNada que importar.")
        return 0

    save_results(DATA_PATH, existentes + nuevos)
    print(f"\nGuardado. Registros en {DATA_PATH}: {len(existentes) + len(nuevos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
