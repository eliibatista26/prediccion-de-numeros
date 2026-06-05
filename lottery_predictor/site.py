from __future__ import annotations

import json
from html import escape
from pathlib import Path


BRAND_COLORS = {
    "Anguila": "#263b8f",
    "Florida": "#168a76",
    "King Lottery": "#d99a00",
    "La Primera": "#ef233c",
    "La Suerte Dominicana": "#e83e75",
    "Leidsa": "#ec1f2e",
    "Lotedom": "#2026d2",
    "Loteka": "#15a8d8",
    "Lotería Nacional": "#159653",
    "Lotería Real": "#3158b7",
    "Mega Millions": "#24559e",
    "New York": "#1372b8",
    "Powerball": "#df202d",
}


def build_site(predictions: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "predictions.json").write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(_render_html(predictions), encoding="utf-8")
    (output_dir / "styles.css").write_text(_render_css(), encoding="utf-8")


def _render_html(predictions: dict[str, object]) -> str:
    lotteries = predictions.get("lotteries", {})
    lottery_items = lotteries if isinstance(lotteries, dict) else {}
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
    sections = "\n".join(_render_lottery_section(name, data) for name, data in lottery_items.items())

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Predicción de números</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="app-header">
    <div class="brand">
      <strong>Predicción<span>.RD</span></strong>
      <p>Última actualización: {generated_at} · {generated_timezone}</p>
    </div>
    <div class="header-actions">
      <button type="button" data-open-help>Guía rápida</button>
      <button type="button" onclick="window.location.reload()">Actualizar vista</button>
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
      <div>
        <h2>Cómo se calcula la puntuación</h2>
        <p>{disclaimer}</p>
      </div>
      <div class="score-grid">
        <div><b>Frecuencia</b><span>Cuántas veces salió desde {actual_from_date}.</span></div>
        <div><b>Tendencia</b><span>Más peso a los sorteos recientes.</span></div>
        <div><b>Atraso</b><span>Extra si lleva días sin aparecer.</span></div>
      </div>
    </section>

    <section class="lottery-list" id="detalle">
      {sections or '<p>No hay resultados cargados todavía.</p>'}
    </section>
  </main>
  <dialog class="help-modal" aria-labelledby="help-title">
    <div class="modal-head">
      <div>
        <p class="eyebrow">Guía rápida</p>
        <h2 id="help-title">Cómo leer esta predicción</h2>
      </div>
      <button type="button" data-close-help aria-label="Cerrar">Cerrar</button>
    </div>
    <div class="modal-body">
      <section>
        <h3>1. Mira el bloque principal</h3>
        <p>La tarjeta grande de cada lotería muestra los números sugeridos para jugar. El primer círculo es el número con mayor puntuación dentro de esa lotería.</p>
      </section>
      <section>
        <h3>2. Usa la puntuación como prioridad</h3>
        <p>Más puntos no significa garantía. Significa que el número combina mejor frecuencia histórica, tendencia reciente y atraso.</p>
      </section>
      <section>
        <h3>3. Compara con los últimos resultados</h3>
        <p>La columna derecha enseña sorteos recientes para que puedas ver si un número sugerido acaba de salir o lleva tiempo sin aparecer.</p>
      </section>
      <section>
        <h3>4. Actualización automática</h3>
        <p>Última actualización: {generated_at} ({generated_timezone}). GitHub Actions recalcula la página según el horario configurado. El botón “Actualizar vista” solo recarga lo último publicado.</p>
      </section>
      <section>
        <h3>5. Cobertura desde 2010</h3>
        <p>Sí estamos usando histórico de 2010, pero desde {actual_from_date}. No hay datos anteriores guardados porque la primera fecha confirmada por Conectate es {actual_from_date}.</p>
      </section>
    </div>
    <div class="modal-note">
      <strong>Importante:</strong> esto es análisis estadístico, no una promesa de resultado.
    </div>
  </dialog>
  <script>
    const helpModal = document.querySelector('.help-modal');
    document.querySelector('[data-open-help]').addEventListener('click', () => helpModal.showModal());
    document.querySelector('[data-close-help]').addEventListener('click', () => helpModal.close());
    helpModal.addEventListener('click', (event) => {{
      if (event.target === helpModal) helpModal.close();
    }});
    document.querySelectorAll('[data-filter]').forEach((button) => {{
      button.addEventListener('click', () => {{
        const selected = button.dataset.filter;
        document.querySelectorAll('[data-filter]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        document.querySelectorAll('[data-lottery]').forEach((section) => {{
          section.hidden = selected !== 'all' && section.dataset.lottery !== selected;
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def _render_chip(name: str) -> str:
    color = BRAND_COLORS.get(name, "#334155")
    safe_name = escape(name)
    return f"""<button class="chip" type="button" data-filter="{safe_name}" style="--brand: {color}"><i></i>{safe_name}</button>"""


def _render_featured_panel(name: str, data: object) -> str:
    payload = data if isinstance(data, dict) else {}
    suggestions = [item for item in payload.get("suggestions", []) if isinstance(item, dict)]
    color = BRAND_COLORS.get(name, "#1738b8")
    main_balls = "".join(
        f"""<span class="hero-ball">{escape(str(item.get("number")))}</span>"""
        for item in suggestions[:3]
    )
    small_balls = "".join(
        f"""<span class="mini-ball">{escape(str(item.get("number")))}</span>"""
        for item in suggestions[3:5]
    )
    rows = "\n".join(
        _render_metric_row(label, suggestions[index] if index < len(suggestions) else None)
        for index, label in enumerate(("Tendencia histórica", "Ciclo de aparición", "Convergencia algorítmica"))
    )
    return f"""<article class="featured-panel" style="--brand: {color}">
  <div class="featured-head">
    <div>
      <h2>{escape(name)}</h2>
      <p>Predicción recomendada · Hoy</p>
    </div>
    <span>Alta probabilidad</span>
  </div>
  <div class="featured-balls">
    {main_balls}
    <div class="mini-balls">{small_balls}</div>
  </div>
  <div class="metric-table">
    <div class="metric-header"><span>Parámetro</span><span>Frecuencia</span><span>Score</span></div>
    {rows}
  </div>
</article>"""


def _render_metric_row(label: str, suggestion: dict[str, object] | None) -> str:
    if not suggestion:
        return ""
    frequency = escape(str(suggestion.get("frequency", "0")))
    score = escape(str(suggestion.get("score", "0")))
    return f"""<div class="metric-row"><span>{escape(label)}</span><b>{frequency}</b><strong>↑ {score}</strong></div>"""


def _render_lottery_latest_panel(name: str, results: list[dict[str, object]]) -> str:
    cards = "\n".join(_render_latest_card(dict(item, lottery_name=name)) for item in results[:4])
    return f"""<aside class="latest-panel">
  <div class="latest-head">
    <h2>Últimos resultados</h2>
    <span>{len(results)} visibles</span>
  </div>
  <div class="latest-list">{cards}</div>
  <div class="weekly-box">
    <span>Resumen histórico</span>
    <strong>{len(results)}</strong>
    <p>resultados recientes mostrados</p>
  </div>
</aside>"""


def _render_latest_card(item: dict[str, object]) -> str:
    numbers = "".join(f"""<span>{int(number):02d}</span>""" for number in item.get("numbers", [])[:6])
    return f"""<article class="latest-card">
  <div>
    <h3>{escape(str(item.get("draw", "")))}</h3>
    <p>{escape(str(item.get("draw_date", "")))} · {escape(str(item.get("lottery_name", "")))}</p>
    <div>{numbers}</div>
  </div>
  <b>›</b>
</article>"""


def _render_lottery_section(name: str, data: object) -> str:
    payload = data if isinstance(data, dict) else {}
    suggestions = [item for item in payload.get("suggestions", []) if isinstance(item, dict)]
    last_results = [item for item in payload.get("last_results", []) if isinstance(item, dict)]
    total_results = escape(str(payload.get("total_results", 0)))
    color = BRAND_COLORS.get(name, "#123c69")
    return f"""<section class="lottery-section" data-lottery="{escape(name)}" style="--brand: {color}">
  <div class="section-head">
    <div>
      <h2>{escape(name)}</h2>
      <span>{total_results} resultados históricos</span>
    </div>
    <span class="section-count">{len(suggestions)} sugeridos</span>
  </div>
  <div class="dashboard-grid">
    {_render_featured_panel(name, payload)}
    {_render_lottery_latest_panel(name, last_results)}
  </div>
</section>"""


def _render_prediction_card(name: str, suggestions: list[dict[str, object]], color: str) -> str:
    top = suggestions[:10]
    balls = "\n".join(
        f"""<span class="ball prediction-ball">{escape(str(item.get("number")))}</span>"""
        for item in top
    )
    score_rows = "\n".join(
        f"""<li><span>{escape(str(item.get("number")))}</span><b>{escape(str(item.get("score")))} pts</b></li>"""
        for item in top[:5]
    )
    return f"""<article class="result-card prediction-card">
  <div class="logo-box">{_initials(name)}</div>
  <div class="card-main">
    <div class="card-title">
      <div>
        <h3>{escape(name)}</h3>
        <p>Predicción recomendada</p>
      </div>
      <strong>Hoy</strong>
    </div>
    <div class="ball-row">{balls}</div>
    <ol class="score-list">{score_rows}</ol>
  </div>
</article>"""


def _render_result_card(name: str, item: dict[str, object], color: str) -> str:
    numbers = "".join(f"""<span class="ball">{int(number):02d}</span>""" for number in item.get("numbers", []))
    return f"""<article class="result-card compact">
  <div class="card-main">
    <div class="card-title">
      <div>
        <p>{escape(str(item.get("draw", "")))}</p>
      </div>
      <strong>{escape(str(item.get("draw_date", "")))}</strong>
    </div>
    <div class="ball-row">{numbers}</div>
  </div>
</article>"""


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
  background: #f7f7f9;
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

.header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.header-actions button:first-child {
  color: #ffffff;
  border-color: #1738b8;
  background: #1738b8;
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

.brand strong {
  color: #1738b8;
  font-size: 24px;
  letter-spacing: 0;
}

.brand span {
  color: #161b2d;
}

.brand p {
  margin: 2px 0 0;
  color: #697087;
  font-size: 13px;
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
  border: 1px solid #dbe3f4;
  border-radius: 8px;
  background: #f5f8ff;
}

.coverage-note strong {
  color: #1738b8;
}

.coverage-note span {
  color: #4f5b75;
  line-height: 1.4;
}

.explain {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 2fr);
  gap: 16px;
}

.explain h2 {
  margin-bottom: 8px;
}

.explain p,
.score-grid span {
  color: #656d84;
  line-height: 1.45;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.score-grid div {
  padding: 12px;
  border: 1px solid #e6e8ee;
  border-radius: 8px;
  background: #fbfbfd;
}

.score-grid b,
.score-grid span {
  display: block;
}

.score-grid b {
  margin-bottom: 4px;
}

.score-grid span {
  font-size: 13px;
}

.lottery-section {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 3px solid var(--brand);
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
    linear-gradient(135deg, rgba(23, 56, 184, 0.94), rgba(236, 31, 46, 0.82));
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
  border-left: 4px solid #ec1f2e;
  border-radius: 8px;
  background: #fff5f6;
  color: #4d5568;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(340px, 0.85fr);
  gap: 22px;
  align-items: start;
  margin-bottom: 28px;
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
}

.featured-head,
.latest-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
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
  color: #1738b8;
  background: #dfe5ff;
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
  color: #1738b8;
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
  color: #1738b8;
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
  color: #1738b8;
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
  color: #1738b8;
  background: #e5e9f2;
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
  color: #1738b8;
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
  .explain,
  .score-grid,
  .result-grid,
  .modal-body {
    grid-template-columns: 1fr;
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
}
"""
