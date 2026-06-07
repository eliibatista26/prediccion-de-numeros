from __future__ import annotations

import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from .utils import clean_text, normalize_text


BRAND_COLORS = {
    "Anguila": "#f97316",
    "Florida": "#ea580c",
    "King Lottery": "#d97706",
    "La Primera": "#f97316",
    "La Suerte Dominicana": "#fb923c",
    "Leidsa": "#ea580c",
    "Lotedom": "#c2410c",
    "Loteka": "#f59e0b",
    "Lotería Nacional": "#f97316",
    "Lotería Real": "#d97706",
    "Mega Millions": "#fb923c",
    "New York": "#ea580c",
    "Powerball": "#c2410c",
}

DISPLAY_LOTTERIES = (
    "Lotería Nacional",
    "Leidsa",
    "Lotería Real",
    "Loteka",
    "La Primera",
    "La Suerte Dominicana",
    "Lotedom",
)

LOGO_FILES = {
    "La Primera": "la-primera.svg",
    "La Suerte Dominicana": "la-suerte-dominicana.svg",
    "Leidsa": "leidsa.svg",
    "Lotedom": "lotedom.svg",
    "Loteka": "loteka.svg",
    "Lotería Nacional": "loteria-nacional.svg",
    "Lotería Real": "loteria-real.svg",
}

VISIBLE_DRAWS = {
    "Lotería Nacional": {
        "Gana Más",
        "Lotería Gana Más",
        "Lotería Nacional",
        "Nacional Noche",
        "Quiniela Nacional",
    },
    "Leidsa": {
        "Quiniela Leidsa",
    },
    "Lotería Real": {
        "Quiniela Real",
    },
    "Loteka": {
        "Quiniela Loteka",
    },
    "La Primera": {
        "La Primera Día",
        "La Primera Noche",
        "Lotería La Primera 12PM",
        "Lotería La Primera Noche 8PM",
        "Primera Noche",
    },
    "La Suerte Dominicana": {
        "La Suerte 12:30",
        "La Suerte 18:00",
        "La Suerte 6PM",
        "La Suerte MD",
    },
    "Lotedom": {
        "LoteDom",
        "Quiniela LoteDom",
        "Quiniela Lotedom",
    },
}

DRAW_ALIASES = {
    "loteria gana mas": "Gana Más",
    "loteria la primera 12pm": "La Primera Día",
    "loteria la primera noche 8pm": "La Primera Noche",
    "nacional noche": "Lotería Nacional",
    "quiniela nacional": "Lotería Nacional",
    "primera noche": "La Primera Noche",
    "quiniela lotedom": "LoteDom",
    "la suerte 12:30": "La Suerte MD",
    "la suerte 18:00": "La Suerte 6PM",
}


_FAVICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <circle cx="16" cy="16" r="16" fill="#f97316"/>
  <circle cx="10" cy="10" r="4" fill="white" opacity="0.35"/>
  <text x="16" y="21" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="900" fill="white">RD</text>
</svg>
"""


def build_site(predictions: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_logo_assets(output_dir)
    (output_dir / "favicon.svg").write_text(_FAVICON_SVG, encoding="utf-8")
    (output_dir / "predictions.json").write_text(
        json.dumps(_public_predictions(predictions), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(_render_html(predictions), encoding="utf-8")
    (output_dir / "styles.css").write_text(_render_css(), encoding="utf-8")


def _write_logo_assets(output_dir: Path) -> None:
    logo_dir = output_dir / "assets" / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    for name in DISPLAY_LOTTERIES:
        filename = LOGO_FILES[name]
        color = BRAND_COLORS.get(name, "#f97316")
        (logo_dir / filename).write_text(_logo_svg(name, color), encoding="utf-8")


def _logo_svg(name: str, color: str) -> str:
    initials = _initials(name)
    safe_name = escape(name)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="190" viewBox="0 0 320 190" role="img" aria-label="{safe_name}">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#fff7ed"/>
      <stop offset="1" stop-color="#fed7aa"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#9a3412" flood-opacity=".18"/>
    </filter>
  </defs>
  <rect width="320" height="190" rx="28" fill="url(#bg)"/>
  <circle cx="72" cy="76" r="44" fill="{color}" opacity=".95" filter="url(#shadow)"/>
  <circle cx="96" cy="58" r="16" fill="#ffffff" opacity=".58"/>
  <path d="M42 124 C92 92, 140 94, 192 128" fill="none" stroke="#9a3412" stroke-width="10" stroke-linecap="round" opacity=".9"/>
  <text x="72" y="88" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="32" font-weight="900" fill="#ffffff">{initials}</text>
  <text x="136" y="82" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="900" fill="#431407">{safe_name}</text>
  <text x="136" y="112" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="800" fill="#9a3412">Predicción estadística</text>
</svg>
"""


def _public_predictions(predictions: dict[str, object]) -> dict[str, object]:
    public = dict(predictions)
    lotteries = predictions.get("lotteries", {})
    if isinstance(lotteries, dict):
        public["lotteries"] = {
            name: _public_lottery_payload(name, lotteries[name])
            for name in DISPLAY_LOTTERIES
            if name in lotteries
        }
    return public


def _public_lottery_payload(name: str, payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    public = dict(payload)
    public.pop("compare_results", None)
    public.pop("compare_day_month", None)
    last_results = payload.get("last_results", [])
    if isinstance(last_results, list):
        public["last_results"] = [
            item
            for item in last_results
            if isinstance(item, dict) and _is_visible_draw(name, str(item.get("draw", "")))
        ]
    draws = payload.get("draws", {})
    if isinstance(draws, dict):
        public["draws"] = {
            draw: draw_payload
            for draw, draw_payload in draws.items()
            if _is_visible_draw(name, draw)
        }
    return public


def _render_html(predictions: dict[str, object]) -> str:
    lotteries = predictions.get("lotteries", {})
    all_lottery_items = lotteries if isinstance(lotteries, dict) else {}
    lottery_items = {
        name: all_lottery_items[name]
        for name in DISPLAY_LOTTERIES
        if name in all_lottery_items
    }
    generated_at = escape(str(predictions.get("generated_at_display") or predictions.get("generated_at") or ""))
    generated_timezone = escape(str(predictions.get("generated_timezone") or ""))
    requested_from_date = escape(str(predictions.get("requested_from_date") or ""))
    actual_from_date = escape(str(predictions.get("actual_from_date") or ""))
    actual_to_date = escape(str(predictions.get("actual_to_date") or ""))
    disclaimer = escape(str(predictions.get("disclaimer", "")))
    result_count = sum(
        int(data.get("total_results", 0))
        for data in lottery_items.values()
        if isinstance(data, dict)
    )
    chips = "\n".join(_render_chip(name) for name in lottery_items)
    base_10 = predictions.get("base_10", {})
    base_10_panel = _render_base_10_panel(base_10 if isinstance(base_10, dict) else {})
    compare_panel = _render_compare_panel(lottery_items, actual_to_date)
    draws_panel = _render_draws_panel(lottery_items)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Predicción de números · Loterías dominicanas</title>
  <meta name="description" content="Predicción estadística de números para Leidsa, Lotería Nacional, Loteka, Lotería Real, La Primera, La Suerte y Lotedom. Actualización automática con datos reales.">
  <meta name="robots" content="index, follow">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Predicción de números · Loterías dominicanas">
  <meta property="og:description" content="Análisis estadístico de Leidsa, Nacional, Loteka, Real, La Primera y más. Datos reales desde 2010, actualización automática.">
  <meta property="og:locale" content="es_DO">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Predicción de números · Loterías dominicanas">
  <meta name="twitter:description" content="Estadísticas y sugerencias para loterías dominicanas. Actualización automática.">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="app-header">
    <p class="update-line">Última actualización: {generated_at} · {generated_timezone}</p>
    <div class="header-actions">
      <button type="button" data-open-help>Cómo usar la predicción</button>
    </div>
  </header>

  <main>
    <section class="title-row">
      <div>
        <p class="eyebrow">Predicción estadística</p>
        <h1>Números sugeridos por lotería</h1>
      </div>
      <div class="meta">
        <span>{result_count:,} resultados</span>
        <span>Cobertura real: {actual_from_date} a {actual_to_date}</span>
      </div>
    </section>

    <section class="filter-panel">
      <p>Filtrar por operador</p>
      <div class="chips">
        <button class="chip active" type="button" data-filter="all">Todas</button>
        {chips}
      </div>
      <div class="schedule">
        <strong>Actualización</strong>
        <span>Última generación: {generated_at} ({generated_timezone}). Automática por GitHub Actions.</span>
      </div>
      <div class="coverage-note">
        <strong>Cobertura verificada</strong>
        <span>Usamos datos reales desde {actual_from_date}. No es todo el año 2010 completo: empieza en {actual_from_date}, que es la primera fecha que Conectate devuelve con resultados.</span>
      </div>
    </section>

    <section class="explain">
      <div class="score-grid">
        <div><b>Frecuencia</b><span>Datos válidos desde {actual_from_date}.</span></div>
        <div><b>Tendencia</b><span>Más próximo a los sorteos recientes.</span></div>
        <div><b>Atraso</b><span>Extra si lleva días sin aparecer.</span></div>
      </div>
    </section>

    {draws_panel}
    {base_10_panel}
    {compare_panel}
  </main>
  <dialog class="help-modal" aria-labelledby="help-title">
    <div class="modal-head">
      <div>
        <p class="eyebrow">Explicación</p>
        <h2 id="help-title">Cómo usar esta pantalla</h2>
      </div>
      <button type="button" data-close-help aria-label="Cerrar">Cerrar</button>
    </div>
    <div class="modal-body">
      <section>
        <h3>1. Elige una lotería</h3>
        <p>Usa los filtros de arriba para ver solo Leidsa, Nacional, Loteka, Real u otra. El botón “Todas” vuelve a mostrar todos los operadores.</p>
      </section>
      <section>
        <h3>2. Lee primero los círculos grandes</h3>
        <p>Los primeros tres números son la recomendación principal. Los círculos pequeños son alternativas cercanas que también tienen buena puntuación.</p>
      </section>
      <section>
        <h3>3. Revisa los parámetros</h3>
        <p>Frecuencia indica cuántas veces apareció. Tendencia reciente favorece datos cercanos. Atraso suma cuando un número lleva tiempo sin salir.</p>
      </section>
      <section>
        <h3>4. Compara con resultados recientes</h3>
        <p>La columna de la derecha muestra los últimos sorteos guardados. Sirve para evitar jugar a ciegas y ver si un número sugerido acaba de aparecer.</p>
      </section>
      <section>
        <h3>5. Cobertura desde 2010</h3>
        <p>Estamos usando histórico real desde {actual_from_date} hasta {actual_to_date}. No es el año 2010 completo; empieza en la primera fecha confirmada por Conectate.</p>
      </section>
      <section>
        <h3>6. Actualización automática</h3>
        <p>Última actualización: {generated_at} ({generated_timezone}). GitHub Actions recalcula la predicción y publica la página automáticamente.</p>
      </section>
    </div>
    <div class="modal-note">
      <strong>Importante:</strong> esto es análisis estadístico, no una promesa de resultado.
    </div>
  </dialog>
  <dialog class="draw-modal" aria-labelledby="draw-modal-title">
    <div class="draw-modal-head">
      <div>
        <p class="eyebrow" data-draw-modal-kicker>Sorteo</p>
        <h2 id="draw-modal-title"></h2>
        <span data-draw-modal-meta></span>
      </div>
      <button type="button" data-close-draw aria-label="Cerrar">Cerrar</button>
    </div>
    <div class="draw-modal-body" data-draw-modal-body></div>
  </dialog>
  <script>
    const helpModal = document.querySelector('.help-modal');
    document.querySelector('[data-open-help]').addEventListener('click', () => helpModal.showModal());
    document.querySelector('[data-close-help]').addEventListener('click', () => helpModal.close());
    helpModal.addEventListener('click', (event) => {{
      if (event.target === helpModal) helpModal.close();
    }});
    function normalizeFilterValue(value) {{
      return String(value || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .toLowerCase();
    }}
    document.querySelectorAll('[data-filter]').forEach((button) => {{
      button.addEventListener('click', () => {{
        const selected = button.dataset.filter;
        const selectedKey = normalizeFilterValue(selected);
        document.querySelectorAll('[data-filter]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        document.querySelectorAll('[data-lottery]').forEach((section) => {{
          section.hidden = selected !== 'all' && normalizeFilterValue(section.dataset.lottery) !== selectedKey;
        }});
      }});
    }});
    const compareToggle = document.querySelector('[data-compare-toggle]');
    const comparePanel = document.querySelector('[data-compare-month]');
    const compareWrap = document.querySelector('[data-compare-wrap]');
    compareToggle.addEventListener('click', () => {{
      const open = !compareWrap.hidden;
      compareWrap.hidden = open;
      compareToggle.setAttribute('aria-expanded', String(!open));
      compareToggle.querySelector('.compare-toggle-arrow').textContent = open ? '▼' : '▲';
      if (!open) renderCompare();
    }});
    const compareData = JSON.parse(document.getElementById('compare-data').textContent);
    const firstSelect = document.querySelector('[data-compare-first]');
    const secondSelect = document.querySelector('[data-compare-second]');
    const compareMode = document.querySelector('[data-compare-mode]');
    const compareFrom = document.querySelector('[data-compare-from]');
    const compareTo = document.querySelector('[data-compare-to]');
    const compareDay = document.querySelector('[data-compare-day]');
    const compareDateFields = document.querySelectorAll('[data-compare-date-field]');
    const compareHistoricalFields = document.querySelectorAll('[data-compare-historical-field]');
    const compareOutput = document.querySelector('[data-compare-output]');
    const currentCompareMonth = comparePanel ? comparePanel.dataset.compareMonth : '';
    function countDateItems(payload) {{
      const dates = payload.dates || {{}};
      const from = compareFrom.value || '';
      const to = compareTo.value || '';
      const counts = {{}};
      Object.entries(dates).forEach(([date, items]) => {{
        if (from && date < from) return;
        if (to && date > to) return;
        items.forEach((item) => {{
          counts[item.number] = (counts[item.number] || 0) + Number(item.count || 0);
        }});
      }});
      return Object.entries(counts)
        .map(([number, count]) => ({{ number, score: count, frequency: count, metric: count === 1 ? 'vez' : 'veces' }}))
        .sort((a, b) => b.score - a.score || a.number.localeCompare(b.number))
        .slice(0, 10);
    }}
    function compareItems(name) {{
      const payload = compareData[name] || {{}};
      if (compareMode.value === 'date') {{
        return countDateItems(payload);
      }}
      if (compareMode.value === 'historical' && compareDay.value && currentCompareMonth) {{
        const dayMonth = `${{currentCompareMonth}}-${{compareDay.value}}`;
        return ((payload.dayMonth || {{}})[dayMonth] || [])
          .map((item) => ({{ number: item.number, score: item.count, frequency: item.count, metric: item.count === 1 ? 'vez' : 'veces' }}))
          .slice(0, 10);
      }}
      return payload.suggestions || [];
    }}
    function updateCompareFields() {{
      const dateMode = compareMode.value === 'date';
      const historicalMode = compareMode.value === 'historical';
      compareDateFields.forEach((field) => {{ field.hidden = !dateMode; }});
      compareHistoricalFields.forEach((field) => {{ field.hidden = !historicalMode; }});
      if (!dateMode) {{
        compareFrom.value = '';
        compareTo.value = '';
      }}
      if (!historicalMode) compareDay.value = '';
    }}
    function renderCompare() {{
      updateCompareFields();
      const first = compareItems(firstSelect.value);
      const second = compareItems(secondSelect.value);
      const secondSet = new Set(second.map((item) => item.number));
      const firstSet = new Set(first.map((item) => item.number));
      const sharedCount = [...firstSet].filter((n) => secondSet.has(n)).length;
      const renderCol = (items, otherSet, title) => `
        <div class="cmp-col">
          <p class="cmp-col-title">${{title}}</p>
          ${{items.length ? items.map((item) => `
            <div class="cmp-row${{otherSet.has(item.number) ? ' is-shared' : ''}}">
              <span class="cmp-num">${{item.number}}</span>
              <span class="cmp-score">${{item.score}} ${{item.metric || 'pts'}}</span>
              ${{otherSet.has(item.number) ? '<span class="cmp-badge">coincide</span>' : ''}}
            </div>
          `).join('') : '<div class="cmp-empty">Sin datos en ese rango</div>'}}
        </div>`;
      compareOutput.innerHTML = `
        <div class="cmp-cols">
          ${{renderCol(first, secondSet, firstSelect.options[firstSelect.selectedIndex].text)}}
          ${{renderCol(second, firstSet, secondSelect.options[secondSelect.selectedIndex].text)}}
        </div>
        <p class="cmp-summary">${{sharedCount > 0
          ? `<strong>${{sharedCount}}</strong> número${{sharedCount !== 1 ? 's' : ''}} coinciden en ambas loterías`
          : 'Ningún número coincide en el top 10 de ambas loterías'}}</p>`;
    }}
    firstSelect.addEventListener('change', renderCompare);
    secondSelect.addEventListener('change', renderCompare);
    compareMode.addEventListener('change', renderCompare);
    compareFrom.addEventListener('change', renderCompare);
    compareTo.addEventListener('change', renderCompare);
    compareDay.addEventListener('change', renderCompare);
    renderCompare();
    const drawData = JSON.parse(document.getElementById('draw-data').textContent);
    const drawModal = document.querySelector('.draw-modal');
    const drawTitle = document.querySelector('[data-draw-modal-title], #draw-modal-title');
    const drawKicker = document.querySelector('[data-draw-modal-kicker]');
    const drawMeta = document.querySelector('[data-draw-modal-meta]');
    const drawBody = document.querySelector('[data-draw-modal-body]');
    function ballList(numbers) {{
      return `<div class="modal-balls">${{numbers.map((number) => `<span>${{number}}</span>`).join('')}}</div>`;
    }}
    function renderDrawModal(id, mode) {{
      const item = drawData[id];
      if (!item) return;
      drawTitle.textContent = item.draw;
      drawKicker.textContent = mode === 'history' ? 'Historial' : 'Predicciones';
      drawMeta.textContent = `${{item.date}} · ${{item.lottery}}`;
      if (mode === 'history') {{
        drawBody.innerHTML = item.history.map((entry) => `
          <article class="modal-result-row">
            <div><strong>${{entry.draw}}</strong><span>${{entry.date}}</span></div>
            ${{ballList(entry.numbers)}}
          </article>
        `).join('');
      }} else {{
        const backtest = item.backtest || {{}};
        const rate = typeof backtest.top5_any_hit_rate === 'number'
          ? `${{Math.round(backtest.top5_any_hit_rate * 100)}}%`
          : 'N/D';
        drawBody.innerHTML = `
          <article class="modal-prediction">
            <p>Predicción calculada solo con el historial de este sorteo. Base: ${{item.total_results}} resultados.</p>
            <div class="backtest-box">
              <strong>Validación histórica: ${{backtest.confidence_label || 'Sin validar'}}</strong>
              <span>Acierto top 5: ${{rate}} · Pruebas: ${{backtest.tested_draws || 0}}</span>
            </div>
            ${{item.predictions.length ? ballList(item.predictions.slice(0, 5).map((entry) => entry.number)) : '<em>No hay histórico suficiente para este sorteo.</em>'}}
            <ol>${{item.predictions.slice(0, 5).map((entry) => `<li><span>${{entry.number}}</span><b>${{entry.score}} pts</b></li>`).join('')}}</ol>
          </article>
        `;
      }}
      drawModal.showModal();
    }}
    document.querySelectorAll('[data-open-draw]').forEach((button) => {{
      button.addEventListener('click', () => renderDrawModal(button.dataset.drawId, button.dataset.openDraw));
    }});
    document.querySelector('[data-close-draw]').addEventListener('click', () => drawModal.close());
    drawModal.addEventListener('click', (event) => {{
      if (event.target === drawModal) drawModal.close();
    }});
  </script>
</body>
</html>
"""


def _render_chip(name: str) -> str:
    color = BRAND_COLORS.get(name, "#334155")
    safe_name = escape(name)
    return f"""<button class="chip" type="button" data-filter="{safe_name}" style="--brand: {color}"><i></i>{safe_name}</button>"""


def _logo_path(name: str) -> str:
    return f"assets/logos/{LOGO_FILES.get(name, 'loteria-nacional.svg')}"


def _render_lottery_image(name: str, class_name: str = "lottery-photo") -> str:
    safe_name = escape(clean_text(name))
    return f"""<img class="{class_name}" src="{_logo_path(name)}" alt="{safe_name}" loading="lazy">"""


def _render_base_10_panel(base_10: dict[str, object]) -> str:
    window = base_10.get("window", {}) if isinstance(base_10.get("window"), dict) else {}
    top_rows = _render_simple_rank(base_10.get("top_10_repeated", []), "count")
    strength_rows = _render_strength_rows(base_10.get("strength_ranking", []))
    delayed_first = _render_delay_rows(base_10.get("delayed_by_position", {}).get("1", []) if isinstance(base_10.get("delayed_by_position"), dict) else [])
    delayed_second = _render_delay_rows(base_10.get("delayed_by_position", {}).get("2", []) if isinstance(base_10.get("delayed_by_position"), dict) else [])
    delayed_third = _render_delay_rows(base_10.get("delayed_by_position", {}).get("3", []) if isinstance(base_10.get("delayed_by_position"), dict) else [])
    elite = " ".join(f"""<span>{escape(str(item.get("number")))}</span>""" for item in base_10.get("elite_group", []) if isinstance(item, dict))
    leader = base_10.get("leader") if isinstance(base_10.get("leader"), dict) else {}
    bullet_pair = base_10.get("bullet_pair") if isinstance(base_10.get("bullet_pair"), dict) else {}
    pair = bullet_pair.get("pair") if isinstance(bullet_pair.get("pair"), list) else []
    return f"""<section class="base-panel">
  <div class="base-head">
    <div>
      <p class="eyebrow">LAS 10 BASE</p>
      <h2>Análisis completo</h2>
    </div>
    <div class="meta">
      <span>{escape(str(window.get("results", 0)))} resultados</span>
      <span>{escape(str(window.get("from", "")))} a {escape(str(window.get("to", "")))}</span>
    </div>
  </div>
  <div class="base-grid">
    <article>
      <h3>Top 10 repetidos</h3>
      <ol>{top_rows}</ol>
    </article>
    <article>
      <h3>Ranking de fuerza</h3>
      <ol>{strength_rows}</ol>
    </article>
    <article class="elite-box">
      <h3>Grupo Élite</h3>
      <div>{elite}</div>
      <p>Líder: <strong>{escape(str(leader.get("number", "N/D")))}</strong> · Palé bala: <strong>{"-".join(escape(str(item)) for item in pair) or "N/D"}</strong></p>
    </article>
  </div>
  <div class="delay-grid">
    <article><h3>Atrasados 1ra posición</h3><ol>{delayed_first}</ol></article>
    <article><h3>Atrasados 2da posición</h3><ol>{delayed_second}</ol></article>
    <article><h3>Atrasados 3ra posición</h3><ol>{delayed_third}</ol></article>
  </div>
</section>"""


def _render_compare_panel(lottery_items: dict[str, object], actual_to_date: str) -> str:
    names = list(lottery_items)
    options = "\n".join(f"""<option value="{escape(name)}">{escape(name)}</option>""" for name in names)
    second_options = "\n".join(
        f"""<option value="{escape(name)}"{" selected" if index == 1 else ""}>{escape(name)}</option>"""
        for index, name in enumerate(names)
    )
    day_options = "\n".join(f"""<option value="{day:02d}">{day}</option>""" for day in range(1, 32))
    compare_data = {}
    for name, data in lottery_items.items():
        if not isinstance(data, dict):
            continue
        compare_data[name] = {
            "suggestions": [
                {"number": str(item.get("number")), "score": item.get("score"), "frequency": item.get("frequency"), "metric": "pts"}
                for item in data.get("suggestions", [])[:10]
                if isinstance(item, dict)
            ],
            "dates": _compare_date_counts(data.get("compare_results", [])),
            "dayMonth": data.get("compare_day_month", {}),
        }
    json_data = json.dumps(compare_data, ensure_ascii=False).replace("</", "<\\/")
    current_month = actual_to_date[5:7] if len(actual_to_date) >= 7 else ""
    return f"""<section class="compare-panel" data-compare-month="{escape(current_month)}">
  <button class="compare-toggle" type="button" data-compare-toggle aria-expanded="false">
    <span class="compare-toggle-label">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
      Comparar dos loterías
    </span>
    <span class="compare-toggle-arrow" aria-hidden="true">▼</span>
  </button>
  <div class="compare-body-wrap" data-compare-wrap hidden>
    <div class="compare-controls">
      <select data-compare-first>{options}</select>
      <select data-compare-second>{second_options}</select>
      <label class="compare-date-field">Consulta <select data-compare-mode><option value="current">Actual</option><option value="date">Fechas</option><option value="historical">Día histórico</option></select></label>
      <label class="compare-date-field" data-compare-date-field hidden>Desde <input type="date" data-compare-from></label>
      <label class="compare-date-field" data-compare-date-field hidden>Hasta <input type="date" data-compare-to></label>
      <label class="compare-date-field" data-compare-historical-field hidden>Día histórico <select data-compare-day><option value="">Selecciona</option>{day_options}</select></label>
    </div>
    <div class="compare-body" data-compare-output></div>
  </div>
  <script type="application/json" id="compare-data">{json_data}</script>
</section>"""


def _compare_date_counts(results: object) -> dict[str, list[dict[str, object]]]:
    by_date: dict[str, Counter[int]] = defaultdict(Counter)
    if not isinstance(results, list):
        return {}
    for result in results:
        if not isinstance(result, dict):
            continue
        draw_date = str(result.get("draw_date") or "")
        if not draw_date:
            continue
        for number in result.get("numbers", [])[:3]:
            try:
                by_date[draw_date][int(number)] += 1
            except (TypeError, ValueError):
                continue
    return {
        draw_date: [
            {"number": f"{number:02d}", "count": count}
            for number, count in counter.most_common()
        ]
        for draw_date, counter in sorted(by_date.items())
    }


def _render_draws_panel(lottery_items: dict[str, object]) -> str:
    items = _draw_items(lottery_items)
    json_data = json.dumps({str(index): item for index, item in enumerate(items)}, ensure_ascii=False).replace("</", "<\\/")

    by_lottery: dict[str, list[tuple[int, dict[str, object]]]] = {}
    for index, item in enumerate(items):
        name = str(item.get("lottery", ""))
        by_lottery.setdefault(name, []).append((index, item))

    sections = ""
    for lottery_name, lottery_cards in by_lottery.items():
        color = BRAND_COLORS.get(lottery_name, "#9a3412")
        cards = "\n".join(_render_draw_card(item, index) for index, item in lottery_cards)
        sections += f"""<section class="lottery-draw-group" data-lottery="{escape(lottery_name)}" style="--brand: {color}">
  <h3 class="lottery-group-title">{escape(lottery_name)}</h3>
  <div class="draw-card-list">{cards}</div>
</section>
"""

    return f"""<section class="draws-panel">
  <div class="draws-head">
    <div>
      <p class="eyebrow">Sorteos recientes</p>
      <h2>Resultados con historial y predicción</h2>
    </div>
    <span>{len(items)} sorteos visibles</span>
  </div>
  {sections}
  <script type="application/json" id="draw-data">{json_data}</script>
</section>"""


def _draw_items(lottery_items: dict[str, object]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for lottery_name, data in lottery_items.items():
        if not isinstance(data, dict):
            continue
        draw_payloads = data.get("draws", {}) if isinstance(data.get("draws"), dict) else {}
        results = [item for item in data.get("last_results", []) if isinstance(item, dict)]
        seen_draws: set[str] = set()
        seen_numbers: set[str] = set()
        selected_results = []
        for result in results:
            raw_draw = str(result.get("draw", ""))
            if not _is_visible_draw(lottery_name, raw_draw):
                continue
            draw_key = _canonical_draw_label(lottery_name, raw_draw).strip().lower()
            if draw_key in seen_draws:
                continue
            numbers_key = f"{result.get('draw_date')}|{'-'.join(str(n) for n in result.get('numbers', [])[:3])}"
            if numbers_key in seen_numbers:
                continue
            seen_draws.add(draw_key)
            seen_numbers.add(numbers_key)
            selected_results.append(result)
            if len(selected_results) == 3:
                break
        for result in selected_results:
            draw = _canonical_draw_label(lottery_name, str(result.get("draw", "")))
            draw_payload = draw_payloads.get(str(result.get("draw", "")))
            draw_data = draw_payload if isinstance(draw_payload, dict) else {}
            backtest = draw_data.get("backtest", {}) if isinstance(draw_data.get("backtest"), dict) else {}
            draw_results = [item for item in draw_data.get("last_results", []) if isinstance(item, dict)]
            suggestions = [
                {
                    "number": str(item.get("number")),
                    "score": item.get("score"),
                    "frequency": item.get("frequency"),
                    "delay_days": item.get("delay_days"),
                }
                for item in draw_data.get("suggestions", [])[:10]
                if isinstance(item, dict)
            ]
            history = [
                {
                    "draw": clean_text(str(history_item.get("draw", ""))),
                    "date": str(history_item.get("draw_date", "")),
                    "numbers": [f"{int(number):02d}" for number in history_item.get("numbers", [])[:3]],
                }
                for history_item in (draw_results or results)
                if _canonical_draw_label(lottery_name, str(history_item.get("draw", ""))) == draw
            ][:5]
            items.append(
                {
                    "lottery": clean_text(lottery_name),
                    "draw": draw,
                    "date": _short_date(str(result.get("draw_date", ""))),
                    "raw_date": str(result.get("draw_date", "")),
                    "numbers": [f"{int(number):02d}" for number in result.get("numbers", [])[:3]],
                    "predictions": suggestions,
                    "prediction_scope": "Sorteo específico",
                    "total_results": draw_data.get("total_results", 0),
                    "backtest": backtest,
                    "history": history,
                }
            )
    items.sort(key=lambda item: str(item.get("raw_date", "")), reverse=True)
    return items[:21]


def _render_draw_card(item: dict[str, object], index: int) -> str:
    lottery = escape(clean_text(str(item.get("lottery", ""))))
    draw = escape(clean_text(str(item.get("draw", ""))))
    date = escape(str(item.get("date", "")))
    numbers = [escape(str(number)) for number in item.get("numbers", [])[:3]]
    while len(numbers) < 3:
        numbers.append("--")
    color = BRAND_COLORS.get(str(item.get("lottery", "")), "#9a3412")
    backtest = item.get("backtest", {}) if isinstance(item.get("backtest"), dict) else {}
    confidence = escape(str(backtest.get("confidence_label") or "Sin validar"))
    hit_rate = backtest.get("top5_any_hit_rate")
    hit_text = f"{round(float(hit_rate) * 100)}%" if isinstance(hit_rate, (float, int)) else "N/D"
    return f"""<article class="draw-card" data-draw-lottery="{lottery}" style="--brand: {color}">
  <div class="draw-identity">
    <div class="draw-logo">{_render_lottery_image(str(item.get("lottery", "")), "draw-logo-img")}</div>
    <div>
      <h3>{draw}</h3>
      <p>{date}</p>
      <span class="confidence-badge">Backtest {confidence} · {hit_text}</span>
    </div>
  </div>
  <div class="draw-numbers">
    <span class="first">{numbers[0]}<small>1RO</small></span>
    <span>{numbers[1]}<small>2DO</small></span>
    <span>{numbers[2]}<small>3RO</small></span>
  </div>
  <div class="draw-actions">
    <button type="button" data-open-draw="history" data-draw-id="{index}">Historial</button>
    <button type="button" data-open-draw="prediction" data-draw-id="{index}">Predicciones</button>
  </div>
</article>"""


def _short_date(value: str) -> str:
    month_names = {
        "01": "Ene",
        "02": "Feb",
        "03": "Mar",
        "04": "Abr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Ago",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dic",
    }
    parts = value.split("-")
    if len(parts) != 3:
        return value
    return f"{parts[2]} {month_names.get(parts[1], parts[1])}"


def _canonical_draw_label(lottery_name: str, draw: str) -> str:
    normalized = normalize_text(draw)
    return DRAW_ALIASES.get(normalized, clean_text(draw))


def _is_visible_draw(lottery_name: str, draw: str) -> bool:
    visible = VISIBLE_DRAWS.get(lottery_name, set())
    if not visible:
        return False
    draw_key = normalize_text(draw)
    visible_keys = {normalize_text(item) for item in visible}
    alias = DRAW_ALIASES.get(draw_key)
    return draw_key in visible_keys or bool(alias and normalize_text(alias) in visible_keys)


def _render_simple_rank(items: object, value_key: str) -> str:
    rows = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            rows.append(f"""<li><span>{escape(str(item.get("number")))}</span><b>{escape(str(item.get(value_key)))}</b></li>""")
    return "\n".join(rows)


def _render_strength_rows(items: object) -> str:
    rows = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            rows.append(f"""<li><span>{escape(str(item.get("number")))}</span><b>{escape(str(item.get("score")))} pts</b></li>""")
    return "\n".join(rows)


def _render_delay_rows(items: object) -> str:
    rows = []
    for item in (items if isinstance(items, list) else [])[:3]:
        if isinstance(item, dict):
            rows.append(f"""<li><span>{escape(str(item.get("number")))}</span><b>{escape(str(item.get("delay_days")))} días</b></li>""")
    return "\n".join(rows)


def _initials(name: str) -> str:
    words = [word for word in name.replace("Lotería", "").split() if word]
    return escape("".join(word[0] for word in words[:2]).upper() or "RD")


def _render_css() -> str:
    return """:root {
  color-scheme: light;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: #161b2d;
  background: #fff7ed;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid #d9dce5;
  border-radius: 999px;
  color: #15204a;
  background: #ffffff;
  font-weight: 800;
  cursor: pointer;
}

select {
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid #d9dce5;
  border-radius: 8px;
  color: #15204a;
  background: #ffffff;
  font: inherit;
  font-weight: 800;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.header-actions button:first-child {
  color: #ffffff;
  border-color: #f97316;
  background: #f97316;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px clamp(16px, 4vw, 56px);
  border-bottom: 1px solid #e1e3ea;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(10px);
}

.update-line {
  color: #697087;
  font-size: 14px;
  font-weight: 800;
}

main {
  width: min(1280px, 100%);
  margin: 0 auto;
  padding: 22px clamp(14px, 4vw, 42px) 56px;
}

.title-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #6d7288;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 32px;
  line-height: 1.1;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.meta span,
.section-count {
  padding: 8px 11px;
  border: 1px solid #e1e3ea;
  border-radius: 999px;
  color: #5f6680;
  background: #ffffff;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.filter-panel,
.explain {
  margin-bottom: 22px;
  padding: 18px;
  border: 1px solid #e1e3ea;
  border-radius: 8px;
  background: #ffffff;
}

.filter-panel p {
  margin-bottom: 12px;
  color: #6d7288;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 14px;
  border: 2px solid var(--brand, #1f2937);
  border-radius: 999px;
  color: #1d2437;
  background: #ffffff;
  font-weight: 900;
  font-family: inherit;
}

.chip.active {
  color: #ffffff;
  border-color: #151927;
  background: #151927;
}

.chip i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand, #1f2937);
}

.schedule {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e6e8ee;
  color: #5f6680;
}

.schedule strong {
  color: #17202a;
}

.coverage-note {
  display: grid;
  gap: 4px;
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
}

.coverage-note strong {
  color: #f97316;
}

.coverage-note span {
  color: #4f5b75;
  line-height: 1.4;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.score-grid div {
  min-height: 112px;
  padding: 18px;
  border: 1px solid #e6e8ee;
  border-radius: 12px;
  background: #f8fafc;
}

.score-grid b,
.score-grid span {
  display: block;
}

.score-grid b {
  margin-bottom: 8px;
  color: #141a2e;
  font-size: 19px;
}

.score-grid span {
  color: #667089;
  font-size: 16px;
  line-height: 1.35;
}

.base-panel,
.compare-panel {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #d8dce8;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(26, 35, 65, 0.06);
}

.base-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.base-head h2 {
  font-size: 27px;
}

.base-grid,
.delay-grid {
  display: grid;
  gap: 14px;
}

.base-grid {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(260px, 0.75fr);
  margin-bottom: 14px;
}

.delay-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.base-grid article,
.delay-grid article {
  padding: 16px;
  border: 1px solid #e5e8ef;
  border-radius: 8px;
  background: #f8fafc;
}

.base-grid h3,
.delay-grid h3 {
  margin-bottom: 10px;
  color: #17202a;
  font-size: 15px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.base-grid ol,
.delay-grid ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.base-grid li,
.delay-grid li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  border-radius: 8px;
  background: #ffffff;
}

.base-grid li span,
.delay-grid li span,
.elite-box div span,
.compare-result span {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: #f97316;
  font-weight: 950;
}

.base-grid li b,
.delay-grid li b {
  color: #5f6680;
}

.elite-box div {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 14px;
}

.elite-box p {
  color: #5f6680;
  line-height: 1.45;
}

.elite-box strong {
  color: #f97316;
}

.compare-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 52px;
  padding: 0 6px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #17202a;
  font-size: 17px;
  font-weight: 900;
  cursor: pointer;
}

.compare-toggle:hover {
  color: #f97316;
}

.compare-toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.compare-toggle-arrow {
  color: #9ba3b8;
  font-size: 13px;
  transition: color 0.15s;
}

.compare-toggle:hover .compare-toggle-arrow {
  color: #f97316;
}

.compare-body-wrap {
  padding-top: 16px;
  border-top: 1px solid #e5e8ef;
}

.compare-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.compare-date-field {
  display: grid;
  gap: 4px;
  color: #5f6680;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.compare-date-field input,
.compare-date-field select {
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid #d8dce8;
  border-radius: 8px;
  background: #ffffff;
  color: #17202a;
  font: inherit;
  letter-spacing: 0;
  text-transform: none;
}

.compare-body {
  margin-top: 4px;
}

.cmp-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.cmp-col {
  border: 1px solid #e5e8ef;
  border-radius: 10px;
  overflow: hidden;
}

.cmp-col-title {
  margin: 0;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e8ef;
  color: #17202a;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.cmp-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-bottom: 1px solid #f0f2f7;
  transition: background 0.15s;
}

.cmp-row:last-child {
  border-bottom: 0;
}

.cmp-row.is-shared {
  background: #fff7ed;
}

.cmp-num {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: #f97316;
  font-weight: 950;
  font-size: 15px;
  flex-shrink: 0;
}

.cmp-row.is-shared .cmp-num {
  background: #ea580c;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.25);
}

.cmp-score {
  color: #6b7280;
  font-size: 13px;
  font-weight: 700;
  flex: 1;
}

.cmp-empty {
  padding: 14px;
  color: #6b7280;
  font-size: 14px;
  font-weight: 700;
}

.cmp-badge {
  padding: 3px 8px;
  border-radius: 999px;
  background: #f97316;
  color: #ffffff;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.cmp-summary {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 14px;
  font-weight: 700;
}

.cmp-summary strong {
  font-size: 18px;
  font-weight: 950;
}

.draws-panel {
  margin-bottom: 26px;
  padding: 20px;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fffaf5;
}

.draws-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.draws-head h2 {
  font-size: 27px;
}

.draws-head > span {
  color: #5f6680;
  font-weight: 900;
}

.lottery-draw-group {
  margin-bottom: 24px;
}

.lottery-draw-group:last-of-type {
  margin-bottom: 0;
}

.lottery-group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 3px solid var(--brand, #f97316);
  color: var(--brand, #f97316);
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.draw-card-list {
  display: grid;
  gap: 16px;
}

.draw-card {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(220px, 0.7fr) minmax(270px, 0.8fr);
  align-items: center;
  gap: 18px;
  min-height: 148px;
  padding: 18px 22px;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(154, 52, 18, 0.1);
}

.draw-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.draw-logo {
  width: 78px;
  height: 58px;
  overflow: hidden;
  border-radius: 10px;
  background: #fff7ed;
  box-shadow: inset 0 0 0 1px #fed7aa;
}

.draw-logo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.draw-identity h3 {
  color: #202638;
  font-size: 24px;
  line-height: 1.1;
}

.draw-identity p {
  margin-top: 8px;
  color: #172033;
  font-size: 18px;
  font-weight: 950;
}

.confidence-badge {
  display: inline-flex;
  margin-top: 9px;
  padding: 6px 9px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  color: #9a3412;
  background: #fff7ed;
  font-size: 12px;
  font-weight: 950;
}

.draw-numbers {
  display: flex;
  justify-content: center;
  gap: 22px;
}

.draw-numbers span {
  display: grid;
  min-width: 54px;
  justify-items: center;
  color: #59636a;
  font-size: 42px;
  font-weight: 500;
  line-height: 0.95;
}

.draw-numbers .first {
  color: #9a3412;
  font-weight: 950;
}

.draw-numbers small {
  margin-top: 8px;
  color: #a1a8b1;
  font-size: 18px;
  font-weight: 800;
}

.draw-numbers .first small {
  position: relative;
  color: #9a3412;
}

.draw-numbers .first small::before {
  position: absolute;
  top: -7px;
  left: 50%;
  width: 38px;
  height: 4px;
  border-radius: 999px;
  background: #fb923c;
  content: "";
  transform: translateX(-50%);
}

.draw-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.draw-actions button {
  min-width: 124px;
  min-height: 50px;
  border-radius: 10px;
  font-size: 15px;
}

.draw-actions button:last-child {
  color: #9a3412;
  border-color: #fed7aa;
  background: #fff7ed;
}

.draw-modal {
  width: min(680px, calc(100% - 28px));
  padding: 0;
  border: 0;
  border-radius: 12px;
  color: #161b2d;
  background: #ffffff;
  box-shadow: 0 24px 80px rgba(16, 24, 48, 0.28);
}

.draw-modal::backdrop {
  background: rgba(13, 18, 32, 0.54);
  backdrop-filter: blur(4px);
}

.draw-modal-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  padding: 22px;
  border-bottom: 1px solid #e5e8ef;
}

.draw-modal-head h2 {
  font-size: 28px;
}

.draw-modal-head span {
  display: block;
  margin-top: 6px;
  color: #697087;
  font-weight: 800;
}

.draw-modal-body {
  display: grid;
  gap: 12px;
  padding: 18px;
}

.modal-result-row,
.modal-prediction {
  padding: 14px;
  border: 1px solid #e5e8ef;
  border-radius: 10px;
  background: #f8fafc;
}

.modal-result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.modal-result-row strong,
.modal-result-row span {
  display: block;
}

.modal-result-row span,
.modal-prediction p {
  color: #697087;
}

.modal-balls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.modal-balls span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: #f97316;
  font-weight: 950;
}

.modal-prediction p {
  margin-bottom: 12px;
}

.backtest-box {
  display: grid;
  gap: 4px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fff7ed;
}

.backtest-box strong {
  color: #9a3412;
}

.backtest-box span {
  color: #697087;
  font-weight: 800;
}

.modal-prediction ol {
  display: grid;
  gap: 8px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.modal-prediction li {
  display: flex;
  justify-content: space-between;
  padding: 9px 10px;
  border-radius: 8px;
  background: #ffffff;
}

.lottery-section {
  margin-top: 0;
  padding-top: 18px;
  border-top: 3px solid var(--brand);
}

.lottery-section + .lottery-section {
  margin-top: 28px;
}

.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2 {
  color: var(--brand);
  font-size: 34px;
}

.section-head span {
  color: #6d7288;
  font-weight: 800;
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  align-items: start;
  gap: 16px;
}

.result-card {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 16px;
  min-height: 210px;
  padding: 18px;
  border: 1px solid #dadde7;
  border-left: 6px solid var(--brand);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(26, 35, 65, 0.08);
}

.side-results {
  display: grid;
  gap: 12px;
}

.side-results > h3 {
  color: #687087;
  font-size: 13px;
  font-weight: 950;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.compact {
  grid-template-columns: 1fr;
  min-height: 0;
  padding: 14px;
  border-left-width: 4px;
}

.logo-box {
  display: grid;
  width: 104px;
  height: 104px;
  place-items: center;
  align-self: start;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  color: var(--brand);
  background: #ffffff;
  font-size: 34px;
  font-weight: 950;
  box-shadow: inset 0 0 0 1px #f5f6fa;
}

.card-main {
  min-width: 0;
}

.card-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.card-title h3 {
  color: var(--brand);
  font-size: 25px;
}

.card-title p {
  color: #646b80;
  font-size: 18px;
}

.compact .card-title {
  margin-bottom: 12px;
}

.compact .card-title p {
  color: #202638;
  font-size: 15px;
  font-weight: 850;
}

.compact .ball-row {
  gap: 8px;
}

.compact .ball {
  width: 42px;
  height: 42px;
  font-size: 17px;
}

.card-title strong {
  color: #6d7288;
  font-size: 13px;
  font-weight: 950;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  white-space: nowrap;
}

.ball-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.ball {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 50%;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 14%, white);
  font-size: 24px;
  font-weight: 950;
  box-shadow: 0 3px 8px rgba(26, 35, 65, 0.08);
}

.prediction-ball:first-child {
  width: 76px;
  height: 76px;
  color: #ffffff;
  background: var(--brand);
  font-size: 30px;
}

.score-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
}

.score-list li {
  padding: 8px;
  border-radius: 8px;
  background: #f8f9fc;
}

.score-list span,
.score-list b {
  display: block;
}

.score-list span {
  color: var(--brand);
  font-weight: 950;
}

.score-list b {
  color: #6d7288;
  font-size: 11px;
}

.help-modal {
  width: min(760px, calc(100% - 28px));
  padding: 0;
  border: 0;
  border-radius: 12px;
  color: #161b2d;
  background: #ffffff;
  box-shadow: 0 24px 80px rgba(16, 24, 48, 0.28);
}

.help-modal::backdrop {
  background: rgba(13, 18, 32, 0.54);
  backdrop-filter: blur(4px);
}

.modal-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  padding: 22px;
  color: #ffffff;
  background:
    linear-gradient(135deg, rgba(249, 115, 22, 0.94), rgba(194, 65, 12, 0.82));
}

.modal-head .eyebrow {
  color: #dfe7ff;
}

.modal-head h2 {
  font-size: 28px;
}

.modal-head button {
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.36);
  background: rgba(255, 255, 255, 0.16);
}

.modal-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 18px;
}

.modal-body section {
  padding: 14px;
  border: 1px solid #e5e8ef;
  border-radius: 8px;
  background: #fbfbfd;
}

.modal-body h3 {
  margin-bottom: 8px;
  color: #17202a;
}

.modal-body p {
  color: #626a80;
  line-height: 1.45;
}

.modal-note {
  margin: 0 18px 18px;
  padding: 13px 14px;
  border-left: 4px solid #ea580c;
  border-radius: 8px;
  background: #fff7ed;
  color: #4d5568;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(340px, 0.85fr);
  gap: 22px;
  align-items: start;
  margin-bottom: 28px;
}

.content-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 0.38fr);
  gap: 24px;
  align-items: start;
}

.lottery-list {
  min-width: 0;
}

.global-latest {
  position: sticky;
  top: 88px;
}

.featured-panel,
.latest-panel {
  border: 1px solid #d8dce8;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(26, 35, 65, 0.08);
}

.featured-panel {
  min-height: 420px;
  padding: 28px;
  border-left: 5px solid var(--brand);
  background: linear-gradient(180deg, #ffffff 0%, #fffaf5 100%);
}

.featured-head,
.latest-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.featured-title {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.lottery-photo {
  width: 112px;
  height: 74px;
  flex: 0 0 auto;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  object-fit: cover;
  background: #fff7ed;
  box-shadow: 0 8px 18px rgba(154, 52, 18, 0.1);
}

.featured-head h2 {
  color: var(--brand);
  font-size: 30px;
}

.featured-head p {
  margin-top: 4px;
  color: #616a80;
}

.featured-head > span {
  padding: 7px 12px;
  border-radius: 8px;
  color: #f97316;
  background: #ffedd5;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}

.featured-balls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
  margin: 36px 0;
}

.hero-ball {
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: var(--brand);
  font-size: 24px;
  font-weight: 950;
  box-shadow: 0 10px 18px color-mix(in srgb, var(--brand) 28%, transparent);
}

.mini-balls {
  display: flex;
  gap: 10px;
  margin-left: 18px;
}

.mini-ball {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 3px solid var(--brand);
  border-radius: 50%;
  color: var(--brand);
  background: #ffffff;
  font-weight: 950;
}

.metric-table {
  overflow: hidden;
  border: 1px solid #e1e4eb;
  border-radius: 8px;
}

.metric-header,
.metric-row {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 0.6fr;
  gap: 12px;
  padding: 12px 14px;
}

.metric-header {
  color: #4f566b;
  background: #f0f2f5;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.08em;
}

.metric-row {
  border-top: 1px solid #e7e9ef;
}

.metric-row strong {
  color: #f97316;
}

.latest-panel {
  padding: 20px;
}

.latest-head {
  margin-bottom: 14px;
}

.latest-head h2 {
  font-size: 21px;
}

.latest-head a,
.latest-head span {
  color: #f97316;
  font-size: 12px;
  font-weight: 950;
  text-decoration: none;
  text-transform: uppercase;
}

.latest-list {
  display: grid;
  gap: 12px;
}

.latest-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border: 1px solid #d8dce8;
  border-radius: 10px;
  background: #ffffff;
}

.latest-card h3 {
  color: #f97316;
  font-size: 13px;
  text-transform: uppercase;
}

.latest-card p {
  margin: 2px 0 10px;
  color: #5f6678;
  font-size: 12px;
}

.latest-card div div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.latest-card div div span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 50%;
  color: #f97316;
  background: #ffedd5;
  font-size: 12px;
  font-weight: 950;
}

.latest-card > b {
  align-self: center;
  color: #a1a8b8;
  font-size: 28px;
}

.weekly-box {
  margin-top: 16px;
  padding: 14px;
  border-radius: 10px;
  background: #eef0f3;
}

.weekly-box span {
  display: block;
  color: #555e73;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.weekly-box strong {
  color: #f97316;
  font-size: 32px;
}

.weekly-box p {
  display: inline;
  color: #4f566b;
}

@media (max-width: 820px) {
  .title-row,
  .section-head,
  .app-header {
    align-items: start;
  }

  .title-row,
  .draws-head,
  .app-header,
  .section-head {
    display: grid;
  }

  .header-actions {
    justify-content: start;
  }

  .meta {
    justify-content: start;
  }

  .dashboard-grid,
  .content-layout,
  .explain,
  .score-grid,
  .base-grid,
  .delay-grid,
  .result-grid,
  .modal-body {
    grid-template-columns: 1fr;
  }

  .compare-panel {
    display: grid;
  }

  .cmp-cols {
    grid-template-columns: 1fr;
  }

  .draw-card {
    grid-template-columns: 1fr;
  }

  .draw-numbers,
  .draw-actions {
    justify-content: flex-start;
  }

  .compare-result {
    justify-content: start;
  }

  .global-latest {
    position: static;
  }

  .result-card {
    grid-template-columns: 1fr;
  }

  .logo-box {
    width: 84px;
    height: 84px;
    font-size: 28px;
  }
}

@media (max-width: 520px) {
  h1 {
    font-size: 27px;
  }

  .section-head h2 {
    font-size: 28px;
  }

  .card-title {
    display: grid;
  }

  .ball {
    width: 50px;
    height: 50px;
    font-size: 20px;
  }

  .score-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .draw-card {
    padding: 16px;
  }

  .draw-identity {
    align-items: flex-start;
  }

  .draw-logo {
    width: 58px;
    height: 50px;
    font-size: 18px;
  }

  .draw-identity h3 {
    font-size: 22px;
  }

  .draw-numbers {
    gap: 16px;
  }

  .draw-numbers span {
    font-size: 36px;
  }

  .draw-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .modal-result-row {
    display: grid;
  }
}

@media (max-width: 820px) {
  .chips {
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 4px;
  }

  .chips::-webkit-scrollbar {
    display: none;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
  }

  body {
    color: #e2e4ed;
    background: #0e1014;
  }

  button {
    color: #c8cadc;
    border-color: #2e3140;
    background: #1a1d27;
  }

  select {
    color: #c8cadc;
    border-color: #2e3140;
    background: #1a1d27;
  }

  .app-header {
    border-bottom-color: #1e2130;
    background: rgba(14, 16, 20, 0.94);
  }

  .update-line {
    color: #6b7280;
  }

  .filter-panel,
  .explain {
    border-color: #1e2130;
    background: #14161f;
  }

  .filter-panel p {
    color: #6b7280;
  }

  .chip {
    color: #c8cadc;
    border-color: color-mix(in srgb, var(--brand) 50%, #2e3140);
    background: #1a1d27;
  }

  .chip.active {
    color: #ffffff;
    border-color: #e2e4ed;
    background: #1e2236;
  }

  .schedule {
    border-top-color: #1e2130;
    color: #6b7280;
  }

  .schedule strong {
    color: #c8cadc;
  }

  .coverage-note {
    border-color: #3d2208;
    background: #1a1108;
  }

  .coverage-note span {
    color: #8b9299;
  }

  .score-grid div {
    border-color: #1e2130;
    background: #14161f;
  }

  .score-grid b {
    color: #e2e4ed;
  }

  .score-grid span {
    color: #6b7280;
  }

  .base-panel,
  .compare-panel {
    border-color: #1e2130;
    background: #14161f;
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.4);
  }

  .base-grid article,
  .delay-grid article {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .base-grid h3,
  .delay-grid h3 {
    color: #9ba3b8;
  }

  .base-grid li,
  .delay-grid li {
    background: #0e1014;
  }

  .base-grid li b,
  .delay-grid li b {
    color: #6b7280;
  }

  .elite-box p {
    color: #6b7280;
  }

  .draws-panel {
    border-color: #3d2208;
    background: #100c06;
  }

  .draw-card {
    border-color: #3d2208;
    background: #14161f;
    box-shadow: 0 14px 30px rgba(0, 0, 0, 0.5);
  }

  .draw-identity h3 {
    color: #e2e4ed;
  }

  .draw-identity p {
    color: #c8cadc;
  }

  .confidence-badge {
    border-color: #3d2208;
    background: #1a1108;
    color: #fb923c;
  }

  .draw-numbers span {
    color: #6b7280;
  }

  .draw-actions button:last-child {
    color: #fb923c;
    border-color: #3d2208;
    background: #1a1108;
  }

  .draw-logo {
    background: #1a1108;
    box-shadow: inset 0 0 0 1px #3d2208;
  }

  .draw-modal,
  .help-modal {
    background: #14161f;
    color: #e2e4ed;
  }

  .draw-modal-head {
    border-bottom-color: #1e2130;
  }

  .draw-modal-head span {
    color: #6b7280;
  }

  .modal-result-row,
  .modal-prediction {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .backtest-box {
    border-color: #3d2208;
    background: #1a1108;
  }

  .backtest-box span {
    color: #6b7280;
  }

  .modal-prediction li {
    background: #0e1014;
  }

  .modal-body section {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .modal-body h3 {
    color: #e2e4ed;
  }

  .modal-body p {
    color: #6b7280;
  }

  .modal-note {
    background: #1a1108;
    color: #9ba3b8;
  }

  .meta span,
  .section-count {
    border-color: #1e2130;
    background: #14161f;
    color: #6b7280;
  }

  .compare-toggle {
    color: #e2e4ed;
  }

  .compare-body-wrap {
    border-top-color: #1e2130;
  }

  .cmp-col {
    border-color: #1e2130;
  }

  .cmp-col-title {
    background: #1a1d27;
    color: #9ba3b8;
    border-bottom-color: #1e2130;
  }

  .cmp-row {
    border-bottom-color: #1e2130;
  }

  .cmp-row.is-shared {
    background: #1a1108;
  }

  .cmp-score {
    color: #6b7280;
  }

  .cmp-summary {
    border-color: #3d2208;
    background: #1a1108;
    color: #fb923c;
  }

  .lottery-group-title {
    border-bottom-color: color-mix(in srgb, var(--brand) 60%, #1e2130);
  }
}
"""
