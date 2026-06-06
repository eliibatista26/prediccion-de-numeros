from datetime import date

from lottery_predictor.scraper import _parse_conectate_results, parse_result_text, scrape_loterias_do, scrape_loterias_rd


def test_parse_result_text_extracts_known_lottery_result():
    text = "Resultados | Leidsa Noche 04/06/2026 12 48 73 | Otra sección"

    results = parse_result_text(text, source="test")

    assert len(results) == 1
    assert results[0].lottery == "Leidsa"
    assert results[0].draw == "Noche"
    assert results[0].numbers == (12, 48, 73)


def test_scrape_loterias_do_parses_static_html(monkeypatch):
    html = """
    <h3><a href='leidsa/quiniela-pale/' rel='bookmark'>Quiniela Palé</a></h3>
    <p><span class='bolo-sorteo'>16</span><span class='bolo-sorteo'>40</span><span class='bolo-sorteo'>34</span></p>
    <span class='lotdate'>04-06-2026</span>
    """
    monkeypatch.setattr("lottery_predictor.scraper.fetch_html", lambda url: html)

    results = scrape_loterias_do()

    assert len(results) == 1
    assert results[0].lottery == "Leidsa"
    assert results[0].draw == "Quiniela Palé"
    assert results[0].numbers == (16, 40, 34)


def test_scrape_loterias_rd_parses_data_attributes(monkeypatch):
    html = """
    <a href="/loteria/loteria-nacional/quiniela"
       data-loteria-nombre="Lotería Nacional"
       data-loteria-fecha="04 de junio de 2026"
       data-loteria-numeros="74, 26, 22">
    </a>
    """
    monkeypatch.setattr("lottery_predictor.scraper.fetch_html", lambda url: html)

    results = scrape_loterias_rd()

    assert len(results) == 1
    assert results[0].lottery == "Lotería Nacional"
    assert results[0].draw == "Lotería Nacional"
    assert results[0].numbers == (74, 26, 22)


def test_parse_conectate_results_extracts_main_page_blocks():
    html = """
    <div class="game-block company-block-15 past">
      <div class="game-info">
        <div class="game-details">
          <a class="game-title" href="/loterias/nacional/quiniela">
            <span>Lotería Nacional</span>
          </a>
        </div>
        <div class="game-scores ball-mode">
          <span class="score ">26</span>
          <span class="score ">20</span>
          <span class="score ">04</span>
        </div>
      </div>
    </div>
    """

    results = _parse_conectate_results(html, draw_date=date(2010, 8, 1))

    assert len(results) == 1
    assert results[0].lottery == "Lotería Nacional"
    assert results[0].draw_date == date(2010, 8, 1)
    assert results[0].numbers == (26, 20, 4)


def test_parse_conectate_results_uses_block_date_when_present():
    html = """
    <div class="game-block company-block-15 past">
      <div class="game-info">
        <div class="game-details">
          <span class="session-date">05-06</span>
          <a class="game-title" href="/loterias/nacional/quiniela">
            <span>Lotería Nacional</span>
          </a>
        </div>
        <div class="game-scores ball-mode">
          <span class="score ">97</span>
          <span class="score ">57</span>
          <span class="score ">53</span>
        </div>
      </div>
    </div>
    """

    results = _parse_conectate_results(html, draw_date=date(2026, 6, 6))

    assert len(results) == 1
    assert results[0].draw_date == date(2026, 6, 5)
