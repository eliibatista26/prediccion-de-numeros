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

# The 10 canonical draws shown in the "Today's Results" section, in display order
DRAW_LABELS = {
    ("Lotería Nacional", "Gana Más"): "Nacional Día",
    ("Lotería Nacional", "Lotería Gana Más"): "Nacional Día",
    ("Lotería Nacional", "Lotería Nacional"): "Nacional Noche",
    ("Lotería Nacional", "Nacional Noche"): "Nacional Noche",
    ("Lotería Nacional", "Quiniela Nacional"): "Nacional Noche",
    ("Leidsa", "Quiniela Leidsa"): "Leidsa",
    ("Lotería Real", "Quiniela Real"): "Real",
    ("Loteka", "Quiniela Loteka"): "Loteka",
    ("La Primera", "La Primera Día"): "La Primera Día",
    ("La Primera", "Lotería La Primera 12PM"): "La Primera Día",
    ("La Primera", "La Primera Noche"): "La Primera Noche",
    ("La Primera", "Lotería La Primera Noche 8PM"): "La Primera Noche",
    ("La Primera", "Primera Noche"): "La Primera Noche",
    ("La Suerte Dominicana", "La Suerte MD"): "La Suerte MD",
    ("La Suerte Dominicana", "La Suerte 12:30"): "La Suerte MD",
    ("La Suerte Dominicana", "La Suerte 6PM"): "La Suerte 6PM",
    ("La Suerte Dominicana", "La Suerte 18:00"): "La Suerte 6PM",
    ("Lotedom", "LoteDom"): "Lotedom",
    ("Lotedom", "Quiniela LoteDom"): "Lotedom",
    ("Lotedom", "Quiniela Lotedom"): "Lotedom",
}

TODAY_DRAW_ORDER = [
    "Nacional Día",
    "Nacional Noche",
    "Leidsa",
    "Real",
    "Loteka",
    "La Primera Día",
    "La Primera Noche",
    "La Suerte MD",
    "La Suerte 6PM",
    "Lotedom",
]

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
    actual_from_date = escape(str(predictions.get("actual_from_date") or ""))
    actual_to_date = escape(str(predictions.get("actual_to_date") or ""))

    base_10 = predictions.get("base_10", {})
    base_10_panel = _render_base_10_panel(base_10 if isinstance(base_10, dict) else {})
    today_results = _render_today_results(lottery_items)
    compare_panel = _render_compare_panel(lottery_items, actual_to_date)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Predicción Loterías RD</title>
  <meta name="description" content="Predicción estadística de números para Leidsa, Lotería Nacional, Loteka, Lotería Real, La Primera, La Suerte y Lotedom. Actualización automática con datos reales.">
  <meta name="robots" content="index, follow">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Predicción Loterías RD">
  <meta property="og:description" content="Análisis estadístico de Leidsa, Nacional, Loteka, Real, La Primera y más. Datos reales desde 2010, actualización automática.">
  <meta property="og:locale" content="es_DO">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Predicción Loterías RD">
  <meta name="twitter:description" content="Estadísticas y sugerencias para loterías dominicanas. Actualización automática.">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="app-header">
    <div class="header-brand">
      <span class="header-logo">RD</span>
      <span class="header-title">Predicción Loterías RD</span>
    </div>
    <p class="update-line">Última actualización: {generated_at} · {generated_timezone}</p>
    <div class="header-actions">
      <button type="button" id="btn-update" data-open-update>⟳ Actualizar</button>
      <button type="button" data-open-help>Cómo usar</button>
    </div>
  </header>

  <main>
    {today_results}
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
        <h3>1. Resultados de hoy</h3>
        <p>La sección principal muestra los últimos resultados de cada sorteo como bolas grandes con posición (1RO, 2DO, 3RO).</p>
      </section>
      <section>
        <h3>2. Las 10 Base</h3>
        <p>El análisis completo muestra el Grupo Élite, Número Líder, y todos los indicadores estadísticos para elegir números.</p>
      </section>
      <section>
        <h3>3. Las 4 condiciones</h3>
        <p>Un número que cumple las 4 condiciones (repetición reciente, atraso útil, coincidencias históricas y arrastre) tiene mayor probabilidad estadística.</p>
      </section>
      <section>
        <h3>4. Atrasados por posición</h3>
        <p>Muestra qué números llevan más días sin aparecer en 1ra, 2da y 3ra posición para cada lotería.</p>
      </section>
      <section>
        <h3>5. Cobertura desde 2010</h3>
        <p>Usamos histórico real desde {actual_from_date} hasta {actual_to_date}. No es el año 2010 completo; empieza en la primera fecha confirmada.</p>
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

  <dialog class="update-modal" id="update-modal" aria-labelledby="update-modal-title">
    <div class="modal-head">
      <div>
        <p class="eyebrow">GitHub Actions</p>
        <h2 id="update-modal-title">Actualizar ahora</h2>
      </div>
      <button type="button" id="close-update-modal" aria-label="Cerrar">Cerrar</button>
    </div>
    <div class="modal-body">
      <p id="update-status-msg">Para disparar la actualización necesitas un token de GitHub con permiso <code>workflow</code>. Se guarda solo en tu navegador.</p>
      <div id="update-token-section">
        <label style="display:block;margin-bottom:8px;font-size:13px;font-weight:700;">
          GitHub Personal Access Token (PAT)
        </label>
        <input type="password" id="gh-token-input" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
          style="width:100%;padding:10px;border-radius:8px;border:1px solid #fed7aa;font-size:14px;box-sizing:border-box;background:#fff7ed;">
        <p style="font-size:11px;color:#9ba3b8;margin-top:6px;">
          Crea el token en GitHub → Settings → Developer settings → Personal access tokens → Fine-grained → permiso <strong>Actions: Write</strong> en este repo.
        </p>
      </div>
      <div id="update-action-row" style="display:flex;gap:10px;margin-top:16px;align-items:center;flex-wrap:wrap;">
        <button type="button" id="btn-trigger-update" style="background:#ea580c;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-weight:700;cursor:pointer;font-size:14px;">
          Disparar actualización
        </button>
        <button type="button" id="btn-clear-token" style="background:transparent;color:#9ba3b8;border:1px solid #e5e7eb;padding:10px 16px;border-radius:8px;font-size:13px;cursor:pointer;">
          Borrar token guardado
        </button>
        <span id="update-feedback" style="font-size:13px;font-weight:600;"></span>
      </div>
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
    // Help modal
    const helpModal = document.querySelector('.help-modal');
    document.querySelector('[data-open-help]').addEventListener('click', () => helpModal.showModal());
    document.querySelector('[data-close-help]').addEventListener('click', () => helpModal.close());
    helpModal.addEventListener('click', (event) => {{
      if (event.target === helpModal) helpModal.close();
    }});

    // Update modal
    const updateModal = document.getElementById('update-modal');
    const ghTokenInput = document.getElementById('gh-token-input');
    const updateFeedback = document.getElementById('update-feedback');
    const REPO = 'eliibatista26/prediccion-de-numeros';
    const WORKFLOW = 'update-site.yml';
    const TOKEN_KEY = 'gh_update_token';

    function loadToken() {{
      const saved = localStorage.getItem(TOKEN_KEY) || '';
      if (saved) ghTokenInput.value = saved;
    }}

    document.querySelector('[data-open-update]').addEventListener('click', () => {{
      loadToken();
      updateFeedback.textContent = '';
      updateModal.showModal();
    }});
    document.getElementById('close-update-modal').addEventListener('click', () => updateModal.close());
    updateModal.addEventListener('click', (e) => {{ if (e.target === updateModal) updateModal.close(); }});

    document.getElementById('btn-clear-token').addEventListener('click', () => {{
      localStorage.removeItem(TOKEN_KEY);
      ghTokenInput.value = '';
      updateFeedback.textContent = 'Token borrado.';
      updateFeedback.style.color = '#9ba3b8';
    }});

    document.getElementById('btn-trigger-update').addEventListener('click', async () => {{
      const token = ghTokenInput.value.trim();
      if (!token) {{
        updateFeedback.textContent = '⚠ Introduce el token primero.';
        updateFeedback.style.color = '#ea580c';
        return;
      }}
      localStorage.setItem(TOKEN_KEY, token);
      updateFeedback.textContent = 'Enviando…';
      updateFeedback.style.color = '#9ba3b8';
      try {{
        const res = await fetch(
          `https://api.github.com/repos/${{REPO}}/actions/workflows/${{WORKFLOW}}/dispatches`,
          {{
            method: 'POST',
            headers: {{
              'Authorization': `Bearer ${{token}}`,
              'Accept': 'application/vnd.github+json',
              'X-GitHub-Api-Version': '2022-11-28',
              'Content-Type': 'application/json',
            }},
            body: JSON.stringify({{ ref: 'main' }}),
          }}
        );
        if (res.status === 204) {{
          updateFeedback.textContent = '✅ Actualización en marcha (~2 min)';
          updateFeedback.style.color = '#16a34a';
          setTimeout(() => updateModal.close(), 2500);
        }} else if (res.status === 401) {{
          updateFeedback.textContent = '❌ Token inválido o sin permisos.';
          updateFeedback.style.color = '#dc2626';
        }} else {{
          const body = await res.json().catch(() => ({{}}));
          updateFeedback.textContent = `❌ Error ${{res.status}}: ${{body.message || 'desconocido'}}`;
          updateFeedback.style.color = '#dc2626';
        }}
      }} catch (err) {{
        updateFeedback.textContent = `❌ ${{err.message}}`;
        updateFeedback.style.color = '#dc2626';
      }}
    }});

    // ── Compare panel ──────────────────────────────────────────────────────
    const compareToggle = document.querySelector('[data-compare-toggle]');
    const compareWrap = document.querySelector('[data-compare-wrap]');
    const comparePanel = document.querySelector('[data-compare-month]');
    compareToggle.addEventListener('click', () => {{
      const open = !compareWrap.hidden;
      compareWrap.hidden = open;
      compareToggle.setAttribute('aria-expanded', String(!open));
      compareToggle.querySelector('.compare-toggle-arrow').textContent = open ? '▼' : '▲';
      if (!open) renderCompare();
    }});

    const compareData = JSON.parse(document.getElementById('compare-data').textContent);
    const firstSelect  = document.querySelector('[data-compare-first]');
    const secondSelect = document.querySelector('[data-compare-second]');
    const compareMode  = document.querySelector('[data-compare-mode]');
    const compareFrom  = document.querySelector('[data-compare-from]');
    const compareTo    = document.querySelector('[data-compare-to]');
    const compareDay   = document.querySelector('[data-compare-day]');
    const compareDateFields      = document.querySelectorAll('[data-compare-date-field]');
    const compareHistoricalFields = document.querySelectorAll('[data-compare-historical-field]');
    const compareOutput = document.querySelector('[data-compare-output]');
    const currentCompareMonth = comparePanel ? comparePanel.dataset.compareMonth : '';

    // ── helpers ────────────────────────────────────────────────────────────
    const cmpBall = (n, cls='') =>
      `<span class="b10-ball${{cls ? ' ' + cls : ''}}">${{n}}</span>`;

    /** Aggregate months data for a lottery within a date range.
        Returns {{counts, p1, p2, p3}} each as {{num: totalCount}} */
    function aggregateMonths(payload, from, to) {{
      const months = payload.months || {{}};
      const c={{}}, p1={{}}, p2={{}}, p3={{}};
      Object.entries(months).forEach(([month, data]) => {{
        if (from && month < from) return;
        if (to   && month > to)   return;
        Object.entries(data.c  ||{{}}).forEach(([n,v])=>{{ c[n]  = (c[n]  ||0)+v; }});
        Object.entries(data.p1 ||{{}}).forEach(([n,v])=>{{ p1[n] = (p1[n] ||0)+v; }});
        Object.entries(data.p2 ||{{}}).forEach(([n,v])=>{{ p2[n] = (p2[n] ||0)+v; }});
        Object.entries(data.p3 ||{{}}).forEach(([n,v])=>{{ p3[n] = (p3[n] ||0)+v; }});
      }});
      return {{c, p1, p2, p3}};
    }}

    /** Sort descending by count, return top N as array of {{number, count}} */
    function topN(obj, n=10) {{
      return Object.entries(obj)
        .map(([number, count]) => ({{number, count}}))
        .sort((a,b) => b.count - a.count || a.number.localeCompare(b.number))
        .slice(0, n);
    }}

    /** Sort ascending by count (= most delayed = least seen in position), top N */
    function delayedN(obj, n=3) {{
      const entries = Object.entries(obj)
        .map(([number, count]) => ({{number, count}}))
        .sort((a,b) => a.count - b.count || a.number.localeCompare(b.number))
        .slice(0, n);
      return entries;
    }}

    /** Get per-lottery data for current mode */
    function getLotteryStats(name) {{
      const payload = compareData[name] || {{}};
      const mode = compareMode.value;
      if (mode === 'date') {{
        const from = compareFrom.value ? compareFrom.value.slice(0,7) : '';
        const to   = compareTo.value   ? compareTo.value.slice(0,7)   : '';
        if (!from && !to) return null; // require at least one date
        return aggregateMonths(payload, from, to);
      }}
      if (mode === 'historical' && compareDay.value && currentCompareMonth) {{
        const dayMonth = `${{currentCompareMonth}}-${{compareDay.value}}`;
        const items = ((payload.dayMonth || {{}})[dayMonth] || []);
        const c={{}};
        items.forEach(i => {{ c[i.number] = (c[i.number]||0) + i.count; }});
        return {{c, p1:{{}}, p2:{{}}, p3:{{}}}};
      }}
      // "current" — use pre-computed suggestions as frequency proxy
      const c={{}};
      (payload.suggestions||[]).forEach(s => {{ c[s.number] = s.frequency || s.score || 1; }});
      return {{c, p1:{{}}, p2:{{}}, p3:{{}}}};
    }}

    /** Check 4 conditions for a number given aggregated stats from both lotteries */
    function fourConditions(num, statsA, statsB, top10A, top10B, top10BothSet) {{
      const top10ASet = new Set(top10A.map(x=>x.number));
      // 1. Repetición reciente: in top 10 of lotería A
      const cond1 = top10ASet.has(num);
      // 2. Atraso útil: NOT in top 3 of A (has some delay), but appeared at least once
      const top3A = top10A.slice(0,3).map(x=>x.number);
      const cond2 = (statsA.c[num]||0) > 0 && !top3A.includes(num);
      // 3. Coincidencias históricas: appears in top 20 of lotería B
      const top20B = topN(statsB.c, 20).map(x=>x.number);
      const cond3 = top20B.includes(num);
      // 4. Arrastre: in top 10 of BOTH lotteries
      const cond4 = top10BothSet.has(num);
      return [cond1, cond2, cond3, cond4];
    }}

    // ── render ─────────────────────────────────────────────────────────────
    function updateCompareFields() {{
      const dateMode = compareMode.value === 'date';
      const histMode = compareMode.value === 'historical';
      compareDateFields.forEach(f => {{ f.hidden = !dateMode; }});
      compareHistoricalFields.forEach(f => {{ f.hidden = !histMode; }});
    }}

    function renderCompare() {{
      updateCompareFields();
      const nameA = firstSelect.value;
      const nameB = secondSelect.value;
      const statsA = getLotteryStats(nameA);
      const statsB = getLotteryStats(nameB);

      if (!statsA || !statsB) {{
        compareOutput.innerHTML = '<p class="cmp-hint">Selecciona un rango de fechas para comparar.</p>';
        return;
      }}

      const top10A = topN(statsA.c, 10);
      const top10B = topN(statsB.c, 10);
      const top10ASet = new Set(top10A.map(x=>x.number));
      const top10BSet = new Set(top10B.map(x=>x.number));
      const top10BothSet = new Set([...top10ASet].filter(n=>top10BSet.has(n)));
      const coincidencias = [...top10BothSet];

      // Delayed by position (top 3 least seen per position = most delayed)
      const del1A = delayedN(statsA.p1, 3);
      const del2A = delayedN(statsA.p2, 3);
      const del3A = delayedN(statsA.p3, 3);
      const del1B = delayedN(statsB.p1, 3);
      const del2B = delayedN(statsB.p2, 3);
      const del3B = delayedN(statsB.p3, 3);

      // 4 conditions: find numbers that meet all 4 (check union of both top 20)
      const candidates = [...new Set([
        ...topN(statsA.c, 20).map(x=>x.number),
        ...topN(statsB.c, 20).map(x=>x.number),
      ])];
      const fourCondNums = [];
      candidates.forEach(num => {{
        const conds = fourConditions(num, statsA, statsB, top10A, top10B, top10BothSet);
        if (conds.every(Boolean)) fourCondNums.push(num);
      }});

      // ── HTML rendering — usa exactamente las mismas clases que b10-panel ──
      const condNames = ['Repetición reciente','Atraso útil','Coincidencias históricas','Arrastre'];

      // Top 10: usa b10-numlist + b10-ball igual que el resto de la página
      const renderTop10 = (items, otherSet) => `<ol class="b10-numlist b10-inline">
        ${{items.length
          ? items.map(item => `<li style="${{otherSet.has(item.number)?'border:1px solid #f97316;':''}}">
              ${{cmpBall(item.number, otherSet.has(item.number)?'b10-elite':'')}}
              <b>${{item.count}} veces</b>
              ${{otherSet.has(item.number)?'<span class="cmp-badge-shared">✓</span>':''}}
            </li>`).join('')
          : '<li class="b10-empty">Sin datos</li>'}}
      </ol>`;

      // Atrasados: usa b10-numlist estilo rank
      const renderDelayed = (items) => `<ol class="b10-numlist">
        ${{items.length
          ? items.map((item,i) => `<li>
              <span class="b10-rank">#${{i+1}}</span>
              ${{cmpBall(item.number)}}
              <b>${{item.count}} veces</b>
            </li>`).join('')
          : '<li class="b10-empty">—</li>'}}
      </ol>`;

      // 4 condiciones: usa four-cond-item igual que b10-panel
      const renderFour = (conds, num) => `
        <div class="four-cond-item">
          ${{cmpBall(num, 'b10-elite')}}
          <div class="four-cond-badges">
            ${{condNames.map((n,i) => `<span class="cond-badge ${{conds[i]?'cond-ok':'cond-no'}}">${{n}}</span>`).join('')}}
          </div>
        </div>`;

      // Build 4-conditions with top candidates sorted by conditions met
      const allCandidatesFor4 = [...new Set([
        ...topN(statsA.c, 15).map(x=>x.number),
        ...topN(statsB.c, 15).map(x=>x.number),
      ])];
      const fourCondDetails = allCandidatesFor4.map(num => {{
        const conds = fourConditions(num, statsA, statsB, top10A, top10B, top10BothSet);
        return {{num, conds, total: conds.filter(Boolean).length}};
      }}).sort((a,b) => b.total - a.total || a.num.localeCompare(b.num)).slice(0, 6);

      // b10-card helper: same card style as rest of page
      const card = (title, body) =>
        `<article class="b10-card"><h3>${{title}}</h3>${{body}}</article>`;

      compareOutput.innerHTML = `
        <!-- 4 condiciones — igual que en Las 10 Base -->
        <div class="b10-card b10-four-cond">
          <h3>Las 4 condiciones — ${{nameA}} vs ${{nameB}}</h3>
          <p class="b10-four-desc">Repetición reciente · Atraso útil · Coincidencias históricas · Arrastre entre loterías</p>
          <div class="b10-four-list">
            ${{fourCondDetails.length
              ? fourCondDetails.map(d => renderFour(d.conds, d.num)).join('')
              : '<p class="b10-empty">Sin datos suficientes en el rango seleccionado.</p>'}}
          </div>
        </div>

        <!-- Coincidencias -->
        ${{coincidencias.length ? `
        <article class="b10-card">
          <h3>Coincidencias top 10 — ${{coincidencias.length}} número${{coincidencias.length!==1?'s':''}} en ambas loterías</h3>
          <div class="b10-elite-balls">
            ${{coincidencias.map(n=>cmpBall(n,'b10-elite')).join('')}}
          </div>
        </article>` : ''}}

        <!-- Análisis lado a lado usando b10-analysis-grid de 2 columnas -->
        <div class="cmp-dual-grid">
          <div class="b10-col-1">
            <p class="eyebrow" style="padding:4px 0 8px">${{nameA}}</p>
            ${{card('Top 10 más repetidos', renderTop10(top10A, top10BSet))}}
            ${{card('3 más atrasados — 1ra posición', renderDelayed(del1A))}}
            ${{card('3 más atrasados — 2da posición', renderDelayed(del2A))}}
            ${{card('3 más atrasados — 3ra posición', renderDelayed(del3A))}}
          </div>
          <div class="b10-col-2">
            <p class="eyebrow" style="padding:4px 0 8px">${{nameB}}</p>
            ${{card('Top 10 más repetidos', renderTop10(top10B, top10ASet))}}
            ${{card('3 más atrasados — 1ra posición', renderDelayed(del1B))}}
            ${{card('3 más atrasados — 2da posición', renderDelayed(del2B))}}
            ${{card('3 más atrasados — 3ra posición', renderDelayed(del3B))}}
          </div>
        </div>
      `;
    }}

    firstSelect.addEventListener('change', renderCompare);
    secondSelect.addEventListener('change', renderCompare);
    compareMode.addEventListener('change', renderCompare);
    compareDay.addEventListener('change', renderCompare);
    // "Por fechas": auto-fire when both dates filled; button also works
    const cmpRunBtn = document.querySelector('[data-compare-run]');
    if (cmpRunBtn) cmpRunBtn.addEventListener('click', renderCompare);
    compareFrom.addEventListener('change', () => {{ if (compareTo.value) renderCompare(); }});
    compareTo.addEventListener('change', () => {{ if (compareFrom.value) renderCompare(); }});
    renderCompare();

    // Draw modal
    const drawDataEl = document.getElementById('draw-data');
    const drawData = drawDataEl ? JSON.parse(drawDataEl.textContent) : {{}};
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


def _render_today_results(lottery_items: dict[str, object]) -> str:
    """Render the top section with today's (most recent) results for the 10 draws."""
    # Collect most recent result for each of the 10 canonical draws
    draw_results: dict[str, dict] = {}
    prev_results: dict[str, list[str]] = {}  # previous draw numbers for "repite" badges

    # Reverse map: label → suggestions list (top 5 numbers)
    label_suggestions: dict[str, list[str]] = {}
    # Build reverse DRAW_LABELS: label → (lottery_name, canonical_draw)
    label_to_draw: dict[str, tuple[str, str]] = {}
    for (lot, drw), lbl in DRAW_LABELS.items():
        if lbl not in label_to_draw:
            label_to_draw[lbl] = (lot, drw)

    for label, (lot, drw) in label_to_draw.items():
        lot_data = lottery_items.get(lot)
        if not isinstance(lot_data, dict):
            continue
        draws = lot_data.get("draws", {}) if isinstance(lot_data.get("draws"), dict) else {}
        draw_data = draws.get(drw, {}) if isinstance(draws.get(drw), dict) else {}
        suggs = draw_data.get("suggestions", [])
        nums = [f"{int(float(s['number'])):02d}" for s in suggs[:5] if isinstance(s, dict) and "number" in s]
        if nums:
            label_suggestions[label] = nums

    for lottery_name, data in lottery_items.items():
        if not isinstance(data, dict):
            continue
        results = [item for item in data.get("last_results", []) if isinstance(item, dict)]
        canonical_seen: dict[str, list] = {}
        for result in results:
            raw_draw = str(result.get("draw", ""))
            if not _is_visible_draw(lottery_name, raw_draw):
                continue
            label = DRAW_LABELS.get((lottery_name, raw_draw))
            if not label:
                alias = DRAW_ALIASES.get(normalize_text(raw_draw))
                if alias:
                    label = DRAW_LABELS.get((lottery_name, alias))
            if not label:
                continue
            nums = [f"{int(n):02d}" for n in result.get("numbers", [])[:3]]
            draw_date = str(result.get("draw_date", ""))
            if label not in canonical_seen:
                canonical_seen[label] = []
            canonical_seen[label].append((draw_date, nums))

        for label, entries in canonical_seen.items():
            entries.sort(key=lambda e: e[0], reverse=True)
            if entries and label not in draw_results:
                draw_results[label] = {"date": entries[0][0], "numbers": entries[0][1]}
            if len(entries) >= 2 and label not in prev_results:
                prev_results[label] = entries[1][1]

    def result_card(label: str) -> str:
        info = draw_results.get(label)
        date_str = ""
        numbers = ["--", "--", "--"]
        if info:
            numbers = info.get("numbers", ["--", "--", "--"])
            while len(numbers) < 3:
                numbers.append("--")
            date_str = _short_date(info.get("date", ""))
        prev = prev_results.get(label, [])
        prev_set = set(prev)

        def ball_html(num: str, pos_label: str) -> str:
            repite = num in prev_set and num != "--"
            badge = '<span class="repite-badge">repite</span>' if repite else ""
            return f"""<div class="today-ball-wrap">
              <span class="today-ball">{escape(num)}</span>
              {badge}
              <small>{escape(pos_label)}</small>
            </div>"""

        balls_html = (
            ball_html(numbers[0], "1RO")
            + ball_html(numbers[1], "2DO")
            + ball_html(numbers[2], "3RO")
        )

        # Suggestions row
        sugg_nums = label_suggestions.get(label, [])
        if sugg_nums:
            sugg_balls = "".join(
                f'<span class="sugg-ball">{escape(n)}</span>' for n in sugg_nums
            )
            sugg_html = f"""<div class="today-suggestions">
    <span class="sugg-label">Sugeridos</span>
    <div class="sugg-balls">{sugg_balls}</div>
  </div>"""
        else:
            sugg_html = ""

        return f"""<article class="today-card">
  <div class="today-card-head">
    <span class="today-lottery-name">{escape(label)}</span>
    <span class="today-date">{escape(date_str)}</span>
  </div>
  <div class="today-balls">{balls_html}</div>
  {sugg_html}
</article>"""

    cards_html = "\n".join(result_card(label) for label in TODAY_DRAW_ORDER)

    return f"""<section class="results-today">
  <div class="results-today-head">
    <p class="eyebrow">Resultados de hoy</p>
    <h2>Últimos sorteos</h2>
  </div>
  <div class="today-grid">
    {cards_html}
  </div>
</section>"""


def _render_base_10_panel(base_10: dict[str, object]) -> str:
    if not base_10:
        return ""
    window = base_10.get("window", {}) if isinstance(base_10.get("window"), dict) else {}
    strength = base_10.get("strength_ranking", []) if isinstance(base_10.get("strength_ranking"), list) else []
    top_hist = base_10.get("top_10_historical", []) if isinstance(base_10.get("top_10_historical"), list) else []
    top_recent = base_10.get("top_10_repeated", []) if isinstance(base_10.get("top_10_repeated"), list) else []
    delayed_pos = base_10.get("delayed_by_position", {}) if isinstance(base_10.get("delayed_by_position"), dict) else {}
    delayed_by_lot = base_10.get("delayed_by_lottery", {}) if isinstance(base_10.get("delayed_by_lottery"), dict) else {}
    coincidences = base_10.get("coincidences", []) if isinstance(base_10.get("coincidences"), list) else []
    drags = base_10.get("drags", []) if isinstance(base_10.get("drags"), list) else []
    active_mirrors = base_10.get("active_mirrors", []) if isinstance(base_10.get("active_mirrors"), list) else []
    moving_numbers = base_10.get("moving_numbers", []) if isinstance(base_10.get("moving_numbers"), list) else []
    frequent_pairs = base_10.get("frequent_pairs", []) if isinstance(base_10.get("frequent_pairs"), list) else []
    elite = base_10.get("elite_group", []) if isinstance(base_10.get("elite_group"), list) else []
    leader = base_10.get("leader") if isinstance(base_10.get("leader"), dict) else {}
    bullet_pair = base_10.get("bullet_pair") if isinstance(base_10.get("bullet_pair"), dict) else {}
    pair_nums = bullet_pair.get("pair", []) if isinstance(bullet_pair, dict) else []

    def ball(num, cls=""):
        return f'<span class="b10-ball{" " + cls if cls else ""}">{escape(str(num))}</span>'

    def num_row(item, val_key="count", suffix=""):
        n = escape(str(item.get("number", "")))
        v = escape(str(item.get(val_key, "")))
        return f'<li>{ball(n)}<b>{v}{" " + escape(suffix) if suffix else ""}</b></li>'

    # ── Hero: Elite + Leader ───────────────────────────────────────────────
    elite_balls_html = "".join(
        f'<span class="b10-ball b10-elite">{escape(str(e.get("number","")))} </span>'
        for e in elite[:5]
    )
    leader_num = escape(str(leader.get("number", "N/D"))) if leader else "N/D"
    leader_score = escape(str(round(float(leader.get("score", 0)), 1))) if leader else "N/D"
    pair_str = "-".join(escape(str(x)) for x in pair_nums) if pair_nums else "N/D"
    results_count = escape(str(window.get("results", 0)))
    date_from = escape(str(window.get("from", "")))
    date_to = escape(str(window.get("to", "")))

    # ── 4-condition analysis ───────────────────────────────────────────────
    # Build sets for condition checking
    recent_set = {str(item.get("number", "")) for item in top_recent[:10]}
    coinc_map = {str(item.get("number", "")): int(item.get("count", 0)) for item in coincidences}
    drag_map = {str(item.get("number", "")): int(item.get("count", 0)) for item in drags}

    four_cond_html = ""
    four_cond_count = 0
    for item in strength[:10]:
        num = str(item.get("number", ""))
        delay = float(item.get("delay_days", 0) or 0)
        cond_recent = num in recent_set
        cond_delay = 3 <= delay <= 45
        cond_coinc = coinc_map.get(num, 0) > 50
        cond_drag = drag_map.get(num, 0) > 100
        if cond_recent and cond_delay and cond_coinc and cond_drag:
            badges = ""
            badges += '<span class="cond-badge cond-ok">Repetición reciente</span>'
            badges += '<span class="cond-badge cond-ok">Atraso útil</span>'
            badges += '<span class="cond-badge cond-ok">Coincidencias hist.</span>'
            badges += '<span class="cond-badge cond-ok">Arrastre</span>'
            four_cond_html += f'''<div class="four-cond-item">
              {ball(num, "elite")}
              <div class="four-cond-badges">{badges}</div>
            </div>'''
            four_cond_count += 1
            if four_cond_count >= 5:
                break

    if not four_cond_html:
        # Show top 3 that meet the most conditions
        scored = []
        for item in strength[:10]:
            num = str(item.get("number", ""))
            delay = float(item.get("delay_days", 0) or 0)
            conds = [
                num in recent_set,
                3 <= delay <= 45,
                coinc_map.get(num, 0) > 50,
                drag_map.get(num, 0) > 100,
            ]
            scored.append((sum(conds), num, conds, item))
        scored.sort(key=lambda x: -x[0])
        for total, num, conds, item in scored[:3]:
            cond_names = ["Repetición reciente", "Atraso útil", "Coincidencias hist.", "Arrastre"]
            badges = "".join(
                f'<span class="cond-badge {"cond-ok" if c else "cond-no"}">{escape(n)}</span>'
                for c, n in zip(conds, cond_names)
            )
            four_cond_html += f'''<div class="four-cond-item">
              {ball(num, "elite")}
              <div class="four-cond-badges">{badges}</div>
            </div>'''

    # ── Strength ranking rows ──────────────────────────────────────────────
    def strength_row(item, rank):
        n = escape(str(item.get("number", "")))
        sc = escape(str(round(float(item.get("score", 0)), 1)))
        rec = escape(str(item.get("recent_30", item.get("recent", 0))))
        coinc = escape(str(item.get("coincidences", 0)))
        drg = escape(str(item.get("drags", 0)))
        freq = escape(str(item.get("frequency", 0)))
        return f'''<tr class="b10-tr">
          <td class="b10-rank">#{rank}</td>
          <td>{ball(n)}</td>
          <td class="b10-sc">{sc}</td>
          <td class="b10-meta">{rec}<small>rec.</small></td>
          <td class="b10-meta">{coinc}<small>coinc.</small></td>
          <td class="b10-meta">{drg}<small>arr.</small></td>
          <td class="b10-meta">{freq}<small>hist.</small></td>
        </tr>'''

    strength_rows_html = "".join(strength_row(item, i+1) for i, item in enumerate(strength[:10]))

    def simple_rank_rows(items, val_key="count", suffix=""):
        return "".join(num_row(item, val_key, suffix) for item in (items or [])[:10])

    def delay_rows(items):
        rows = []
        for item in (items if isinstance(items, list) else [])[:3]:
            if isinstance(item, dict):
                n = escape(str(item.get("number", "")))
                d = escape(str(item.get("delay_days", "")))
                rows.append(f'<li>{ball(n)}<b>{d}d</b></li>')
        return "".join(rows)

    # Mirror rows
    mirror_rows = ""
    for m in (active_mirrors or [])[:8]:
        a = escape(str(m.get("number", "")))
        b_m = escape(str(m.get("mirror", "")))
        diff = escape(str(m.get("diff_days", "")))
        aa = escape(str(m.get("days_ago_a", "")))
        ab = escape(str(m.get("days_ago_b", "")))
        mirror_rows += f'<li><span class="mirror-pair">{ball(a)} <i>↔</i> {ball(b_m)}</span><small>{diff}d dif · {a}:{aa}d, {b_m}:{ab}d</small></li>'

    # Moving numbers rows
    moving_rows = ""
    for mv in (moving_numbers or [])[:6]:
        if not isinstance(mv, dict):
            continue
        num = escape(str(mv.get("number", "")))
        lots = mv.get("lotteries", [])
        if not isinstance(lots, list):
            lots = []
        lot_tags = " ".join(f'<span class="lot-tag">{escape(str(l))}</span>' for l in lots[:3])
        moving_rows += f'<li>{ball(num)}{lot_tags}</li>'

    # Pair rows
    pair_rows = ""
    for p in (frequent_pairs or [])[:8]:
        pair = p.get("pair", [])
        cnt = p.get("count", 0)
        if len(pair) >= 2:
            pair_rows += f'<li><span class="pale-pair">{ball(escape(str(pair[0])))} <i>-</i> {ball(escape(str(pair[1])))}</span><b>{escape(str(cnt))}x</b></li>'

    # Coincidences and drags rows
    coinc_rows = "".join(f'<li>{ball(escape(str(c.get("number",""))))}<b>{escape(str(c.get("count",0)))}x</b></li>' for c in (coincidences or [])[:8])
    drag_rows = "".join(f'<li>{ball(escape(str(d.get("number",""))))}<b>{escape(str(d.get("count",0)))}x</b></li>' for d in (drags or [])[:8])

    # Delayed by lottery table
    LOTTERY_ORDER = ["Gana Más", "Nacional Noche", "Leidsa", "Real", "Loteka", "La Primera Día", "La Primera Noche", "La Suerte MD", "La Suerte 6PM", "Lotedom"]
    lot_table_rows = ""
    for lot_label in LOTTERY_ORDER:
        positions = delayed_by_lot.get(lot_label, {})
        if not positions:
            continue
        def pos_cells(pos_key):
            items = positions.get(pos_key, [])[:3]
            if not items:
                return "<td>—</td>"
            cells = " ".join(f'{ball(escape(str(it.get("number",""))))}<small>{escape(str(it.get("delay_days","")))}</small>' for it in items)
            return f"<td><div class='lot-pos-nums'>{cells}</div></td>"
        lot_table_rows += f'''<tr>
          <td class="lot-name">{escape(lot_label)}</td>
          {pos_cells("1")}
          {pos_cells("2")}
          {pos_cells("3")}
        </tr>'''

    return f"""<section class="b10-panel">
  <div class="b10-header">
    <div>
      <p class="eyebrow">LAS 10 BASE</p>
      <h2>Análisis completo</h2>
      <p class="b10-meta-line">{results_count} sorteos · {date_from} → {date_to}</p>
    </div>
  </div>

  <!-- Hero: Elite & Leader -->
  <div class="b10-hero">
    <div class="b10-elite-box">
      <p class="b10-section-label">Grupo Élite</p>
      <div class="b10-elite-balls">{elite_balls_html}</div>
    </div>
    <div class="b10-leader-box">
      <p class="b10-section-label">Número Líder</p>
      <span class="b10-leader-ball">{leader_num}</span>
      <p class="b10-leader-sub">Score: <strong>{leader_score}</strong></p>
    </div>
    <div class="b10-bala-box">
      <p class="b10-section-label">Palé Bala</p>
      <span class="b10-bala-nums">{pair_str}</span>
    </div>
  </div>

  <!-- 4-condition analysis -->
  <div class="b10-card b10-four-cond">
    <h3>Las 4 condiciones — números que cumplen todo</h3>
    <p class="b10-four-desc">Repetición reciente · Atraso útil (3–45 días) · Coincidencias históricas · Arrastre entre loterías</p>
    <div class="b10-four-list">{four_cond_html}</div>
  </div>

  <!-- Analysis grid: 3 balanced columns -->
  <div class="b10-analysis-grid">
    <div class="b10-col-1">
      <article class="b10-card b10-strength">
        <h3>Ranking de fuerza</h3>
        <table class="b10-table">
          <thead><tr><th></th><th>Núm.</th><th>Score</th><th>Rec.</th><th>Coinc.</th><th>Arr.</th><th>Hist.</th></tr></thead>
          <tbody>{strength_rows_html}</tbody>
        </table>
      </article>
      <article class="b10-card">
        <h3>Top 10 histórico</h3>
        <ol class="b10-numlist b10-inline">{simple_rank_rows(top_hist, "count", "veces")}</ol>
      </article>
      <article class="b10-card">
        <h3>Repetición reciente <small>(últimos 30 días)</small></h3>
        <ol class="b10-numlist b10-inline">{simple_rank_rows(top_recent, "count", "veces")}</ol>
      </article>
    </div>

    <div class="b10-col-2">
      <article class="b10-card">
        <h3>Atrasados 1ra posición</h3>
        <ol class="b10-numlist">{delay_rows(delayed_pos.get("1", []))}</ol>
      </article>
      <article class="b10-card">
        <h3>Atrasados 2da posición</h3>
        <ol class="b10-numlist">{delay_rows(delayed_pos.get("2", []))}</ol>
      </article>
      <article class="b10-card">
        <h3>Atrasados 3ra posición</h3>
        <ol class="b10-numlist">{delay_rows(delayed_pos.get("3", []))}</ol>
      </article>
      <article class="b10-card">
        <h3>Coincidencias <small>entre loterías</small></h3>
        <ol class="b10-numlist b10-inline">{coinc_rows}</ol>
      </article>
      <article class="b10-card">
        <h3>Arrastres <small>día siguiente</small></h3>
        <ol class="b10-numlist b10-inline">{drag_rows}</ol>
      </article>
    </div>

    <div class="b10-col-3">
      <article class="b10-card">
        <h3>Espejos activos <small>≤14 días</small></h3>
        <ul class="b10-mirror-list">{mirror_rows if mirror_rows else "<li class='b10-empty'>Sin espejos activos</li>"}</ul>
      </article>
      <article class="b10-card">
        <h3>Palés frecuentes</h3>
        <ul class="b10-pale-list">{pair_rows if pair_rows else "<li class='b10-empty'>Sin datos</li>"}</ul>
      </article>
      <article class="b10-card">
        <h3>Números que cambian de lotería</h3>
        <ul class="b10-numlist b10-moving">{moving_rows if moving_rows else "<li class='b10-empty'>Sin datos</li>"}</ul>
      </article>
    </div>
  </div>

  <!-- Per-lottery delayed table -->
  <article class="b10-card b10-lottery-table-wrap">
    <h3>Atrasados por lotería — top 3 en cada posición</h3>
    <div class="b10-table-scroll">
      <table class="b10-lot-table">
        <thead>
          <tr>
            <th>Lotería</th>
            <th>1ra posición</th>
            <th>2da posición</th>
            <th>3ra posición</th>
          </tr>
        </thead>
        <tbody>{lot_table_rows}</tbody>
      </table>
    </div>
  </article>
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
                {"number": str(item.get("number")), "score": item.get("score"), "frequency": item.get("frequency")}
                for item in data.get("suggestions", [])[:10]
                if isinstance(item, dict)
            ],
            "months": _compare_month_data(data.get("compare_results", [])),
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
      <div class="cmp-row-selects">
        <label class="cmp-label">Lotería A <select data-compare-first>{options}</select></label>
        <label class="cmp-label">Lotería B <select data-compare-second>{second_options}</select></label>
        <label class="cmp-label">Consulta
          <select data-compare-mode>
            <option value="current">Actual</option>
            <option value="date">Por fechas</option>
            <option value="historical">Día histórico</option>
          </select>
        </label>
      </div>
      <div class="cmp-row-dates" data-compare-date-field hidden>
        <label class="cmp-label">Desde <input type="date" data-compare-from></label>
        <label class="cmp-label">Hasta <input type="date" data-compare-to></label>
        <button type="button" class="cmp-run-btn" data-compare-run>Comparar</button>
      </div>
      <div class="cmp-row-dates" data-compare-historical-field hidden>
        <label class="cmp-label">Día del mes
          <select data-compare-day><option value="">Selecciona día</option>{day_options}</select>
        </label>
      </div>
    </div>
    <div class="compare-body" data-compare-output></div>
  </div>
  <script type="application/json" id="compare-data">{json_data}</script>
</section>"""


def _compare_month_data(results: object) -> dict[str, object]:
    """Agrega resultados por año-mes con desglose por posición (1ra, 2da, 3ra).
    Permite calcular: top repetidos, atrasados por posición y las 4 condiciones en JS."""
    if not isinstance(results, list):
        return {}
    by_month: dict[str, list[Counter]] = {}  # month → [all, pos1, pos2, pos3]
    for result in results:
        if not isinstance(result, dict):
            continue
        draw_date = str(result.get("draw_date") or "")
        if len(draw_date) < 7:
            continue
        month_key = draw_date[:7]
        if month_key not in by_month:
            by_month[month_key] = [Counter(), Counter(), Counter(), Counter()]
        nums = result.get("numbers", [])[:3]
        for n in nums:
            try:
                by_month[month_key][0][int(n)] += 1
            except (TypeError, ValueError):
                pass
        for i in range(min(3, len(nums))):
            try:
                by_month[month_key][i + 1][int(nums[i])] += 1
            except (TypeError, ValueError):
                pass

    out = {}
    for month_key, (all_c, p1, p2, p3) in sorted(by_month.items()):
        out[month_key] = {
            "c":  {f"{n:02d}": v for n, v in all_c.most_common()},
            "p1": {f"{n:02d}": v for n, v in p1.most_common()},
            "p2": {f"{n:02d}": v for n, v in p2.most_common()},
            "p3": {f"{n:02d}": v for n, v in p3.most_common()},
        }
    return out


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
      <p class="eyebrow">Historial y predicciones</p>
      <h2>Sorteos recientes con predicción</h2>
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
        "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic",
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


def _render_lottery_image(name: str, class_name: str = "lottery-photo") -> str:
    safe_name = escape(clean_text(name))
    return f"""<img class="{class_name}" src="{_logo_path(name)}" alt="{safe_name}" loading="lazy">"""


def _logo_path(name: str) -> str:
    return f"assets/logos/{LOGO_FILES.get(name, 'loteria-nacional.svg')}"


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

h1, h2, h3, p {
  margin: 0;
}

h1 { font-size: 32px; line-height: 1.1; }
h2 { font-size: 28px; line-height: 1.1; }

/* ── Header ──────────────────────────────────────────────────────────── */
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px clamp(16px, 4vw, 56px);
  border-bottom: 1px solid #fed7aa;
  background: rgba(255, 247, 237, 0.96);
  backdrop-filter: blur(10px);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-logo {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  background: #f97316;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
  flex-shrink: 0;
}

.header-title {
  font-size: 17px;
  font-weight: 900;
  color: #9a3412;
  white-space: nowrap;
}

.update-line {
  color: #697087;
  font-size: 13px;
  font-weight: 700;
  flex: 1;
  text-align: center;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.header-actions button {
  color: #ffffff;
  border-color: #f97316;
  background: #f97316;
  font-weight: 900;
}

.eyebrow {
  margin: 0 0 4px;
  color: #9a3412;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

main {
  width: min(1400px, 100%);
  margin: 0 auto;
  padding: 16px clamp(12px, 3vw, 36px) 40px;
  display: grid;
  gap: 16px;
}

/* ── Today's Results ─────────────────────────────────────────────────── */
.results-today {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(154, 52, 18, 0.08);
}

.results-today-head {
  margin-bottom: 18px;
}

.results-today-head h2 {
  color: #9a3412;
  font-size: 26px;
}

.today-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.today-card {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.today-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.today-lottery-name {
  font-size: 15px;
  font-weight: 900;
  color: #9a3412;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.today-date {
  font-size: 12px;
  font-weight: 700;
  color: #9ba3b8;
}

.today-balls {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.today-ball-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  position: relative;
}

.today-ball {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: #ffffff;
  font-size: 22px;
  font-weight: 950;
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.35);
}

.today-ball-wrap small {
  font-size: 11px;
  font-weight: 900;
  color: #9ba3b8;
  letter-spacing: 0.08em;
}

.repite-badge {
  position: absolute;
  top: -6px;
  right: -8px;
  background: #22c55e;
  color: #ffffff;
  font-size: 9px;
  font-weight: 900;
  padding: 2px 5px;
  border-radius: 999px;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* ── Suggested numbers row ───────────────────────────────────────────── */
.today-suggestions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid #fde8d4;
  flex-wrap: wrap;
}

.sugg-label {
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #9ba3b8;
  white-space: nowrap;
}

.sugg-balls {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.sugg-ball {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #fff7ed;
  border: 2px solid #fed7aa;
  color: #ea580c;
  font-size: 11px;
  font-weight: 900;
}

/* ── Las 10 Base ─────────────────────────────────────────────────────── */
.b10-panel {
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(154, 52, 18, 0.08);
}

.b10-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #fed7aa;
}

.b10-header h2 {
  color: #9a3412;
  margin: 4px 0 6px;
}

.b10-meta-line {
  color: #9ba3b8;
  font-size: 13px;
  font-weight: 700;
}

.b10-section-label {
  font-size: 11px;
  font-weight: 900;
  color: #9ba3b8;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin: 0 0 8px;
}

/* Hero row */
.b10-hero {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
  padding: 18px 20px;
  background: linear-gradient(135deg, #fff7ed, #ffedd5);
  border: 1px solid #fed7aa;
  border-radius: 12px;
}

.b10-elite-balls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.b10-ball {
  display: inline-grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: #f97316;
  font-weight: 950;
  font-size: 14px;
  flex-shrink: 0;
}

.b10-ball.elite {
  width: 46px;
  height: 46px;
  font-size: 17px;
  background: linear-gradient(135deg, #f97316, #c2410c);
  box-shadow: 0 4px 14px rgba(249, 115, 22, 0.4);
}

.b10-leader-box {
  text-align: center;
  padding: 12px 20px;
  border-left: 2px solid #fed7aa;
  border-right: 2px solid #fed7aa;
}

.b10-leader-ball {
  display: inline-grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #c2410c);
  color: #ffffff;
  font-size: 30px;
  font-weight: 950;
  box-shadow: 0 6px 20px rgba(249, 115, 22, 0.45);
}

.b10-leader-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #697087;
}

.b10-leader-sub strong {
  color: #f97316;
}

.b10-bala-box {
  text-align: center;
  padding: 12px 16px;
}

.b10-bala-nums {
  display: block;
  font-size: 28px;
  font-weight: 950;
  color: #9a3412;
  letter-spacing: 0.05em;
}

/* 4-condition */
.b10-four-cond {
  margin-bottom: 20px;
}

.b10-four-cond h3 {
  font-size: 14px;
  font-weight: 900;
  color: #374151;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.b10-four-desc {
  font-size: 12px;
  color: #9ba3b8;
  font-weight: 700;
  margin-bottom: 14px;
}

.b10-four-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.four-cond-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  flex: 1;
  min-width: 200px;
}

.four-cond-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.cond-badge {
  font-size: 10px;
  font-weight: 900;
  padding: 3px 8px;
  border-radius: 999px;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.cond-ok {
  background: #dcfce7;
  color: #166534;
}

.cond-no {
  background: #f1f5f9;
  color: #9ba3b8;
}

/* Analysis grid — 3 columns */
.b10-analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
  margin-bottom: 20px;
  align-items: start;
}

.b10-col-1,
.b10-col-2,
.b10-col-3 {
  display: grid;
  gap: 14px;
}

/* Cards */
.b10-card {
  padding: 16px;
  border: 1px solid #e5e8ef;
  border-radius: 10px;
  background: #f8fafc;
}

.b10-card h3 {
  font-size: 12px;
  font-weight: 900;
  color: #374151;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.b10-card h3 small {
  font-size: 10px;
  color: #9ba3b8;
  text-transform: none;
  letter-spacing: 0;
  font-weight: 700;
  display: block;
  margin-top: 2px;
}

.b10-empty {
  color: #9ba3b8;
  font-size: 13px;
  padding: 8px 10px;
}

/* Numlists */
.b10-numlist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.b10-numlist li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 8px;
  background: #ffffff;
}

.b10-numlist b {
  color: #6b7280;
  font-size: 12px;
  margin-left: auto;
}

.b10-numlist.b10-inline {
  grid-template-columns: repeat(2, 1fr);
}

/* Moving numbers */
.b10-moving li {
  flex-wrap: wrap;
  gap: 6px;
}

.lot-tag {
  font-size: 10px;
  font-weight: 900;
  padding: 2px 6px;
  border-radius: 999px;
  background: #ffedd5;
  color: #9a3412;
}

/* Strength table */
.b10-strength { overflow: hidden; }

.b10-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.b10-table th {
  padding: 7px 6px;
  background: #f0f2f7;
  color: #5f6680;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: left;
  border-bottom: 1px solid #e5e8ef;
}

.b10-tr td {
  padding: 6px;
  border-bottom: 1px solid #f0f2f7;
  vertical-align: middle;
}

.b10-tr:last-child td { border-bottom: 0; }

.b10-rank {
  color: #9ba3b8;
  font-weight: 900;
  font-size: 10px;
  width: 22px;
}

.b10-sc {
  font-weight: 900;
  color: #f97316;
  font-size: 12px;
}

.b10-meta {
  color: #6b7280;
  font-size: 11px;
}

.b10-meta small {
  display: block;
  font-size: 9px;
  color: #9ba3b8;
  font-weight: 700;
}

/* Mirror & pale lists */
.b10-mirror-list,
.b10-pale-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.b10-mirror-list li,
.b10-pale-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: #ffffff;
  flex-wrap: wrap;
}

.mirror-pair,
.pale-pair {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mirror-pair i,
.pale-pair i {
  color: #9ba3b8;
  font-style: normal;
  font-weight: 900;
  font-size: 12px;
}

.b10-mirror-list small {
  color: #9ba3b8;
  font-size: 10px;
  font-weight: 700;
  margin-left: auto;
}

.b10-pale-list b {
  color: #6b7280;
  font-size: 12px;
  margin-left: auto;
}

/* Lottery table */
.b10-lottery-table-wrap { overflow: hidden; }

.b10-table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.b10-lot-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 600px;
}

.b10-lot-table th {
  padding: 9px 12px;
  background: #f0f2f7;
  color: #5f6680;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: left;
  border-bottom: 1px solid #e5e8ef;
}

.b10-lot-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f2f7;
  vertical-align: middle;
}

.b10-lot-table tr:last-child td { border-bottom: 0; }

.lot-name {
  font-weight: 900;
  color: #374151;
  white-space: nowrap;
  min-width: 130px;
}

.lot-pos-nums {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.lot-pos-nums small {
  font-size: 10px;
  color: #9ba3b8;
  font-weight: 700;
}

/* ── Compare Panel ────────────────────────────────────────────────────── */
.compare-panel {
  background: #ffffff;
  border: 1px solid #d8dce8;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 4px 16px rgba(26, 35, 65, 0.06);
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

.compare-toggle:hover { color: #f97316; }

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

.compare-toggle:hover .compare-toggle-arrow { color: #f97316; }

.compare-body-wrap {
  padding-top: 16px;
  border-top: 1px solid #e5e8ef;
}

/* ── Compare controls ─────────────────────────────── */
.compare-controls { margin-bottom: 16px; }

.cmp-row-selects {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.cmp-row-dates {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}

.cmp-label {
  display: grid;
  gap: 4px;
  color: #5f6680;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.cmp-label input,
.cmp-label select {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid #d8dce8;
  border-radius: 8px;
  background: #ffffff;
  color: #17202a;
  font: inherit;
  font-size: 14px;
  letter-spacing: 0;
  text-transform: none;
}

.cmp-run-btn {
  height: 40px;
  padding: 0 18px;
  background: #ea580c;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}
.cmp-run-btn:hover { background: #c2410c; }

.cmp-hint {
  padding: 20px;
  color: #9ba3b8;
  font-size: 14px;
  text-align: center;
}

/* Dual grid — same gap as b10-analysis-grid */
.cmp-dual-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: start;
}

/* Shared badge inside b10-numlist li */
.cmp-badge-shared {
  margin-left: auto;
  padding: 2px 6px;
  border-radius: 999px;
  background: #f97316;
  color: #ffffff;
  font-size: 10px;
  font-weight: 900;
  white-space: nowrap;
}

/* ── Draws Panel (historical/predictions) ────────────────────────────── */
.draws-panel {
  background: #fffaf5;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  padding: 22px;
}

.draws-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.draws-head h2 { font-size: 24px; }

.draws-head > span {
  color: #5f6680;
  font-weight: 900;
  font-size: 13px;
}

.lottery-draw-group { margin-bottom: 24px; }
.lottery-draw-group:last-of-type { margin-bottom: 0; }

.lottery-group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 3px solid var(--brand, #f97316);
  color: var(--brand, #f97316);
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.draw-card-list {
  display: grid;
  gap: 14px;
}

.draw-card {
  display: grid;
  grid-template-columns: minmax(200px, 0.9fr) minmax(200px, 0.7fr) minmax(240px, 0.8fr);
  align-items: center;
  gap: 16px;
  min-height: 130px;
  padding: 16px 20px;
  border: 1px solid #fed7aa;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 22px rgba(154, 52, 18, 0.08);
}

.draw-identity {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.draw-logo {
  width: 72px;
  height: 52px;
  overflow: hidden;
  border-radius: 8px;
  background: #fff7ed;
  box-shadow: inset 0 0 0 1px #fed7aa;
  flex-shrink: 0;
}

.draw-logo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.draw-identity h3 {
  color: #202638;
  font-size: 20px;
  line-height: 1.1;
}

.draw-identity p {
  margin-top: 6px;
  color: #172033;
  font-size: 15px;
  font-weight: 950;
}

.confidence-badge {
  display: inline-flex;
  margin-top: 7px;
  padding: 5px 8px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  color: #9a3412;
  background: #fff7ed;
  font-size: 11px;
  font-weight: 950;
}

.draw-numbers {
  display: flex;
  justify-content: center;
  gap: 18px;
}

.draw-numbers span {
  display: grid;
  min-width: 48px;
  justify-items: center;
  color: #59636a;
  font-size: 38px;
  font-weight: 500;
  line-height: 0.95;
}

.draw-numbers .first {
  color: #9a3412;
  font-weight: 950;
}

.draw-numbers small {
  margin-top: 7px;
  color: #a1a8b1;
  font-size: 15px;
  font-weight: 800;
}

.draw-numbers .first small {
  position: relative;
  color: #9a3412;
}

.draw-numbers .first small::before {
  position: absolute;
  top: -6px;
  left: 50%;
  width: 34px;
  height: 3px;
  border-radius: 999px;
  background: #fb923c;
  content: "";
  transform: translateX(-50%);
}

.draw-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.draw-actions button {
  min-width: 110px;
  min-height: 44px;
  border-radius: 8px;
  font-size: 14px;
}

.draw-actions button:last-child {
  color: #9a3412;
  border-color: #fed7aa;
  background: #fff7ed;
}

/* ── Modals ───────────────────────────────────────────────────────────── */
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
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.94), rgba(194, 65, 12, 0.82));
}

.modal-head .eyebrow { color: #fde8d4; }
.modal-head h2 { font-size: 26px; }

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

.draw-modal-head h2 { font-size: 26px; }

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
.modal-result-row span { display: block; }

.modal-result-row span,
.modal-prediction p { color: #697087; }

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

.modal-prediction p { margin-bottom: 12px; }

.backtest-box {
  display: grid;
  gap: 4px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fff7ed;
}

.backtest-box strong { color: #9a3412; }
.backtest-box span { color: #697087; font-weight: 800; }

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

/* ── Responsive ───────────────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .b10-analysis-grid {
    grid-template-columns: 1fr 1fr;
  }
  .b10-col-3 {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 820px) {
  .app-header {
    flex-wrap: wrap;
    gap: 10px;
  }

  .update-line {
    order: 3;
    width: 100%;
    text-align: left;
  }

  .today-grid {
    grid-template-columns: 1fr;
  }

  .b10-hero {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .b10-leader-box {
    border-left: 0;
    border-right: 0;
    border-top: 2px solid #fed7aa;
    border-bottom: 2px solid #fed7aa;
    padding: 14px 0;
    text-align: left;
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .b10-analysis-grid {
    grid-template-columns: 1fr;
  }

  .b10-col-3 {
    grid-column: auto;
    grid-template-columns: 1fr;
  }

  .draw-card {
    grid-template-columns: 1fr;
  }

  .draw-numbers,
  .draw-actions {
    justify-content: flex-start;
  }

  .cmp-dual-grid {
    grid-template-columns: 1fr;
  }

  .modal-body {
    grid-template-columns: 1fr;
  }

  .draws-head {
    display: grid;
  }
}

@media (max-width: 520px) {
  .header-title { display: none; }

  .today-ball { width: 46px; height: 46px; font-size: 18px; }

  .b10-numlist.b10-inline {
    grid-template-columns: 1fr;
  }

  .draw-card { padding: 14px; }

  .draw-identity h3 { font-size: 18px; }

  .draw-numbers span { font-size: 32px; }

  .draw-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .modal-result-row { display: grid; }
}

/* ── Dark mode ────────────────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  :root { color-scheme: dark; }

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
    border-bottom-color: #3d2208;
    background: rgba(14, 16, 20, 0.96);
  }

  .header-title { color: #fb923c; }
  .update-line { color: #6b7280; }

  .header-actions button {
    color: #ffffff;
    border-color: #ea580c;
    background: #ea580c;
  }

  .results-today {
    background: #14161f;
    border-color: #3d2208;
  }

  .results-today-head h2 { color: #fb923c; }

  .today-card {
    background: #1a1108;
    border-color: #3d2208;
  }

  .today-lottery-name { color: #fb923c; }

  .today-suggestions { border-top-color: #3d2208; }
  .sugg-ball { background: #14161f; border-color: #3d2208; color: #fb923c; }

  .b10-panel {
    border-color: #3d2208;
    background: #14161f;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4);
  }

  .b10-header {
    border-bottom-color: #3d2208;
  }

  .b10-header h2 { color: #fb923c; }

  .b10-hero {
    background: linear-gradient(135deg, #1a1108, #1c1205);
    border-color: #3d2208;
  }

  .b10-card {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .b10-card h3 { color: #9ba3b8; }

  .b10-numlist li { background: #0e1014; }

  .b10-mirror-list li,
  .b10-pale-list li { background: #0e1014; }

  .b10-table th,
  .b10-lot-table th {
    background: #1e2130;
    color: #9ba3b8;
    border-bottom-color: #2e3140;
  }

  .b10-tr td,
  .b10-lot-table td { border-bottom-color: #1e2130; }

  .b10-lot-table tr:last-child td,
  .b10-tr:last-child td { border-bottom: 0; }

  .b10-rank { color: #6b7280; }
  .b10-meta-line { color: #6b7280; }

  .four-cond-item {
    background: #1a1108;
    border-color: #3d2208;
  }

  .cond-ok { background: #14532d; color: #86efac; }
  .cond-no { background: #1e2130; color: #6b7280; }

  .compare-panel {
    border-color: #1e2130;
    background: #14161f;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  }

  .compare-toggle { color: #e2e4ed; }
  .compare-body-wrap { border-top-color: #1e2130; }

  .cmp-label input,
  .cmp-label select { background: #1a1d27; border-color: #1e2130; color: #e2e4ed; }

  .draws-panel {
    border-color: #3d2208;
    background: #100c06;
  }

  .draw-card {
    border-color: #3d2208;
    background: #14161f;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.5);
  }

  .draw-identity h3 { color: #e2e4ed; }
  .draw-identity p { color: #c8cadc; }

  .confidence-badge {
    border-color: #3d2208;
    background: #1a1108;
    color: #fb923c;
  }

  .draw-numbers span { color: #6b7280; }

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

  .draw-modal-head { border-bottom-color: #1e2130; }
  .draw-modal-head span { color: #6b7280; }

  .modal-result-row,
  .modal-prediction {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .backtest-box {
    border-color: #3d2208;
    background: #1a1108;
  }

  .backtest-box span { color: #6b7280; }
  .modal-prediction li { background: #0e1014; }

  .modal-body section {
    border-color: #1e2130;
    background: #1a1d27;
  }

  .modal-body h3 { color: #e2e4ed; }
  .modal-body p { color: #6b7280; }

  .modal-note {
    background: #1a1108;
    color: #9ba3b8;
  }

  .lottery-group-title {
    border-bottom-color: color-mix(in srgb, var(--brand) 60%, #1e2130);
  }

  .lot-tag { background: #3d2208; color: #fb923c; }
}
"""
