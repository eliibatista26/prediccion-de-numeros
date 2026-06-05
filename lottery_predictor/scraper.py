from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Any

import requests

from .models import LotteryResult


RESULTS_DO_URL = "https://resultados.do/"
LOTERIAS_DO_URL = "https://loterias.do/"
LOTERIAS_RD_URL = "https://www.loteriasrd.com.do/"
YELU_BASE_URL = "https://www.yelu.do"
CONNECTATE_LOTERIAS_URL = "https://www.conectate.com.do/loterias/"
RESULTS_DO_SUPABASE_URL = "https://zfqtqdhyodsivygnvnfh.supabase.co/rest/v1/resultados"
RESULTS_DO_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmcXRxZGh5b2RzaXZ5Z252bmZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ5MjI2MzYsImV4cCI6MjA5MDQ5ODYzNn0."
    "t-at7hevbGLDYz_sUoQv1CeJ27FMa8R-18h6N2gNHqY"
)
DATE_PATTERNS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
)
SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
LOTTERY_SLUGS = {
    "nacional": "Lotería Nacional",
    "loteria-nacional": "Lotería Nacional",
    "leidsa": "Leidsa",
    "loteka": "Loteka",
    "real": "Lotería Real",
    "loto-real": "Lotería Real",
    "loteria-real": "Lotería Real",
    "primera": "La Primera",
    "la-primera": "La Primera",
    "suerte": "La Suerte Dominicana",
    "la-suerte": "La Suerte Dominicana",
    "la-suerte-dominicana": "La Suerte Dominicana",
    "lotedom": "Lotedom",
    "king": "King Lottery",
    "king-lottery": "King Lottery",
    "anguila": "Anguila",
    "anguilla": "Anguila",
    "new-york": "New York",
    "florida": "Florida",
    "powerball": "Powerball",
    "power-ball": "Powerball",
    "mega-millions": "Mega Millions",
    "megamillions": "Mega Millions",
}
YELU_HISTORY_ENDPOINTS = (
    ("/lottery/results/history", "Lotería Nacional"),
    ("/leidsa/results/history", "Leidsa"),
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)


def fetch_html(url: str = RESULTS_DO_URL, timeout: int = 20) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 lottery-predictor-bot/1.0",
            "Accept-Language": "es-DO,es;q=0.9,en;q=0.6",
        },
    )
    response.raise_for_status()
    if not response.encoding:
        response.encoding = "utf-8"
    return response.text


def parse_results_do(html: str, source: str = RESULTS_DO_URL) -> list[LotteryResult]:
    extractor = TextExtractor()
    extractor.feed(html)
    text = " | ".join(extractor.parts)
    return parse_result_text(text, source=source)


def parse_result_text(text: str, source: str) -> list[LotteryResult]:
    today = date.today()
    current_date = _find_date(text) or today
    candidates = []
    known_lotteries = (
        "Leidsa",
        "Lotería Nacional",
        "Loteria Nacional",
        "Loteka",
        "Lotería Real",
        "Loteria Real",
        "La Primera",
        "La Suerte",
        "LoteDom",
        "Anguila",
        "King Lottery",
        "New York",
        "Florida",
    )

    chunks = [chunk.strip() for chunk in text.split("|") if chunk.strip()]
    for index, chunk in enumerate(chunks):
        lottery = next((name for name in known_lotteries if name.lower() in chunk.lower()), None)
        if not lottery:
            continue

        window = " ".join(chunks[index : index + 5])
        numbers = _extract_numbers(window)
        if len(numbers) < 2:
            continue

        draw_date = _find_date(window) or current_date
        draw = _guess_draw(window)
        candidates.append(
            LotteryResult(
                lottery=lottery.replace("Loteria", "Lotería"),
                draw=draw,
                draw_date=draw_date,
                numbers=tuple(numbers[:6]),
                source=source,
            )
        )

    return _dedupe(candidates)


def scrape_results_do() -> list[LotteryResult]:
    try:
        return fetch_results_do_api()
    except requests.RequestException:
        return parse_results_do(fetch_html())


def scrape_loterias_do() -> list[LotteryResult]:
    html = fetch_html(LOTERIAS_DO_URL)
    results: list[LotteryResult] = []
    pattern = re.compile(
        r"<h3><a href='(?P<href>[^']+)'.*?>(?P<draw>.*?)</a></h3>\s*"
        r"<p>(?P<numbers>.*?)</p>.*?"
        r"<span class='lotdate'>(?P<date>.*?)</span>",
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        numbers = tuple(_extract_numbers(_strip_tags(match.group("numbers"))))
        if len(numbers) < 2:
            continue
        draw_date = _parse_date(match.group("date"))
        if not draw_date:
            continue
        results.append(
            LotteryResult(
                lottery=_lottery_from_path_or_draw(match.group("href"), match.group("draw")),
                draw=_clean_text(match.group("draw")),
                draw_date=draw_date,
                numbers=numbers,
                source=LOTERIAS_DO_URL,
            )
        )
    return _dedupe(results)


def scrape_loterias_rd() -> list[LotteryResult]:
    html = fetch_html(LOTERIAS_RD_URL)
    results: list[LotteryResult] = []
    pattern = re.compile(
        r"<a\s+href=\"(?P<href>[^\"]+)\"[^>]*?"
        r"data-loteria-nombre=\"(?P<draw>[^\"]+)\"[^>]*?"
        r"data-loteria-fecha=\"(?P<date>[^\"]+)\"[^>]*?"
        r"data-loteria-numeros=\"(?P<numbers>[^\"]+)\"",
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        numbers = tuple(_extract_numbers(match.group("numbers")))
        if len(numbers) < 2:
            continue
        draw_date = _parse_date(match.group("date"))
        if not draw_date:
            continue
        results.append(
            LotteryResult(
                lottery=_lottery_from_path_or_draw(match.group("href"), match.group("draw")),
                draw=_clean_text(match.group("draw")),
                draw_date=draw_date,
                numbers=numbers,
                source=LOTERIAS_RD_URL,
            )
        )
    return _dedupe(results)


def scrape_all_sources() -> list[LotteryResult]:
    try:
        results = scrape_conectate_date(date.today())
        print(f"Conectate: {len(results)} resultados")
        return results
    except requests.RequestException as exc:
        print(f"No se pudo actualizar Conectate: {exc}")
        return []


def scrape_yelu_history(start_year: int = 2010) -> list[LotteryResult]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 lottery-predictor-bot/1.0",
            "Accept-Language": "es-DO,es;q=0.9,en;q=0.6",
        }
    )
    results: list[LotteryResult] = []
    for endpoint, lottery in YELU_HISTORY_ENDPOINTS:
        url = f"{YELU_BASE_URL}{endpoint}"
        response = session.get(url, timeout=20)
        response.raise_for_status()
        months = _extract_yelu_months(response.text, start_year=start_year)
        for month in months:
            page = session.post(
                url,
                data={
                    "_method": "POST",
                    "data[Lottery][name]": "",
                    "data[Lottery][date]": month,
                },
                timeout=20,
            )
            page.raise_for_status()
            results.extend(_parse_yelu_history(page.text, lottery=lottery, source=url))
    return _dedupe(results)


def scrape_conectate_date(draw_date: date, session: requests.Session | None = None) -> list[LotteryResult]:
    http = session or requests.Session()
    response = http.get(
        CONNECTATE_LOTERIAS_URL,
        params={"date": draw_date.strftime("%d-%m-%Y")},
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 lottery-predictor-bot/1.0",
            "Accept-Language": "es-DO,es;q=0.9,en;q=0.6",
        },
    )
    response.raise_for_status()
    return _parse_conectate_results(response.text, draw_date=draw_date)


def scrape_conectate_range(start_date: date, end_date: date, workers: int = 8) -> list[LotteryResult]:
    dates = list(_date_range(start_date, end_date))
    results: list[LotteryResult] = []

    def fetch(day: date) -> list[LotteryResult]:
        session = requests.Session()
        return scrape_conectate_date(day, session=session)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch, day): day for day in dates}
        for future in as_completed(futures):
            day = futures[future]
            try:
                results.extend(future.result())
            except requests.RequestException as exc:
                print(f"No se pudo cargar Conectate {day.isoformat()}: {exc}")
    return _dedupe(results)


def fetch_results_do_api(page_size: int = 1000) -> list[LotteryResult]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = requests.get(
            RESULTS_DO_SUPABASE_URL,
            params={
                "select": "loteria,juego,fecha,turno,numeros",
                "juego": "neq.Chance Express",
                "order": "fecha.asc,created_at.asc",
            },
            headers={
                "apikey": RESULTS_DO_SUPABASE_KEY,
                "Authorization": f"Bearer {RESULTS_DO_SUPABASE_KEY}",
                "Accept": "application/json",
                "Range": f"{offset}-{offset + page_size - 1}",
            },
            timeout=20,
        )
        response.raise_for_status()
        page = response.json()
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return _rows_to_results(rows)


def _rows_to_results(rows: list[dict[str, Any]]) -> list[LotteryResult]:
    results: list[LotteryResult] = []
    for row in rows:
        numbers = tuple(int(number) for number in row.get("numeros") or [] if str(number).isdigit())
        if len(numbers) < 2:
            continue
        raw_date = row.get("fecha")
        if not raw_date:
            continue
        results.append(
            LotteryResult(
                lottery=str(row.get("loteria") or "Sin nombre"),
                draw=str(row.get("juego") or row.get("turno") or "General"),
                draw_date=datetime.strptime(str(raw_date), "%Y-%m-%d").date(),
                numbers=numbers,
                source=RESULTS_DO_URL,
            )
        )
    return _dedupe(results)


def _extract_numbers(text: str) -> list[int]:
    text = re.sub(r"(?<!\d)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})(?!\d)", " ", text)
    numbers: list[int] = []
    for match in re.finditer(r"(?<!\d)(\d{1,2})(?!\d)", text):
        value = int(match.group(1))
        if 0 <= value <= 99:
            numbers.append(value)
    return numbers


def _find_date(text: str) -> date | None:
    for raw in re.findall(r"(?<!\d)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})(?!\d)", text):
        normalized = raw
        if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2}$", raw):
            normalized = raw[:-2] + "20" + raw[-2:]
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(normalized, pattern).date()
            except ValueError:
                continue
    return None


def _parse_date(text: str) -> date | None:
    cleaned = _clean_text(text).lower()
    parsed = _find_date(cleaned)
    if parsed:
        return parsed
    match = re.search(r"(?<!\d)(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(?:de\s+)?(\d{4})(?!\d)", cleaned)
    if not match:
        return None
    month = SPANISH_MONTHS.get(match.group(2))
    if not month:
        return None
    return date(int(match.group(3)), month, int(match.group(1)))


def _extract_yelu_months(html: str, start_year: int) -> list[str]:
    months = sorted(
        {
            match.group(1)
            for match in re.finditer(r'<option value="(\d{4}-\d{2})"', html)
            if int(match.group(1)[:4]) >= start_year
        }
    )
    return months


def _parse_yelu_history(html: str, lottery: str, source: str) -> list[LotteryResult]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    results: list[LotteryResult] = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 3:
            continue
        draw_date = _parse_date(_clean_text(cells[0]))
        draw = _clean_text(cells[1])
        numbers = tuple(_extract_numbers(_strip_tags(cells[2])))
        if not draw_date or len(numbers) < 2:
            continue
        results.append(
            LotteryResult(
                lottery=_normalize_yelu_lottery(lottery, draw),
                draw=draw,
                draw_date=draw_date,
                numbers=numbers,
                source=source,
            )
        )
    return _dedupe(results)


def _parse_conectate_results(html: str, draw_date: date) -> list[LotteryResult]:
    blocks = re.findall(
        r'<div class="game-block[^"]*.*?</div>\s*</div>\s*</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    results: list[LotteryResult] = []
    for block in blocks:
        title_match = re.search(r'<a class="game-title" href="(?P<href>[^"]+)">\s*(?P<title>.*?)</a>', block, re.DOTALL | re.IGNORECASE)
        if not title_match:
            continue
        numbers = tuple(_extract_numbers(" ".join(re.findall(r'<span class="score[^"]*">\s*([^<]+)\s*</span>', block))))
        if len(numbers) < 2:
            continue
        title = _clean_text(title_match.group("title"))
        results.append(
            LotteryResult(
                lottery=_lottery_from_path_or_draw(title_match.group("href"), title),
                draw=title,
                draw_date=draw_date,
                numbers=numbers,
                source=CONNECTATE_LOTERIAS_URL,
            )
        )
    return _dedupe(results)


def _normalize_yelu_lottery(default_lottery: str, draw: str) -> str:
    lowered = draw.lower()
    if "primera" in lowered:
        return "La Primera"
    if "suerte" in lowered:
        return "La Suerte Dominicana"
    if "leidsa" in lowered or default_lottery == "Leidsa":
        return "Leidsa"
    return default_lottery


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _guess_draw(text: str) -> str:
    lower = text.lower()
    if "noche" in lower:
        return "Noche"
    if "tarde" in lower:
        return "Tarde"
    if "mañana" in lower or "matut" in lower:
        return "Mañana"
    if "medio" in lower:
        return "Mediodía"
    return "General"


_SOURCE_PRIORITY: dict[str, int] = {
    CONNECTATE_LOTERIAS_URL: 0,       # más confiable
    LOTERIAS_RD_URL: 1,
    LOTERIAS_DO_URL: 2,
    RESULTS_DO_URL: 3,
    RESULTS_DO_SUPABASE_URL: 3,
}


def _source_rank(source: str) -> int:
    for prefix, rank in _SOURCE_PRIORITY.items():
        if source.startswith(prefix):
            return rank
    return 99


def _dedupe(results: list[LotteryResult]) -> list[LotteryResult]:
    # Un solo resultado por (lotería, sorteo, fecha): gana la fuente de mayor prioridad.
    best: dict[str, LotteryResult] = {}
    for result in results:
        group = f"{result.draw_date.isoformat()}|{result.lottery}|{result.draw}"
        if group not in best or _source_rank(result.source) < _source_rank(best[group].source):
            best[group] = result
    return list(best.values())


def _clean_text(text: str) -> str:
    stripped = " ".join(_strip_tags(text).split())
    if "Ã" not in stripped and "Â" not in stripped:
        return stripped
    try:
        return stripped.encode("latin1").decode("utf-8")
    except UnicodeError:
        return stripped


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _lottery_from_path(path: str) -> str:
    parts = [part for part in re.split(r"[/?#]+", path.lower()) if part]
    for part in parts:
        if part in LOTTERY_SLUGS:
            return LOTTERY_SLUGS[part]
    for slug, lottery in LOTTERY_SLUGS.items():
        if slug in path.lower():
            return lottery
    return "Sin nombre"


def _lottery_from_path_or_draw(path: str, draw: str) -> str:
    lottery = _lottery_from_path(path)
    if lottery != "Sin nombre":
        return lottery
    cleaned_draw = _clean_text(draw).lower().replace(" ", "-")
    return LOTTERY_SLUGS.get(cleaned_draw, _clean_text(draw))
