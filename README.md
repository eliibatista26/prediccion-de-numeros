# Predicción de números

Proyecto para publicar gratis una página con sugerencias estadísticas de números para loterías dominicanas.

La idea es no mantener un servidor FastAPI encendido todo el día. En su lugar:

- GitHub Actions ejecuta el scraper varias veces al día.
- Los resultados se guardan en `data/results.json`.
- El análisis genera `docs/index.html` y `docs/predictions.json`.
- GitHub Pages publica la carpeta `docs/` como página web gratis.

Importante: las sugerencias son estadísticas y no garantizan resultados.

## Ejecutar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m lottery_predictor.cli --skip-scrape
```

Abre `docs/index.html` en el navegador.

Para intentar actualizar datos desde internet:

```bash
python -m lottery_predictor.cli
```

## Publicar en GitHub Pages

1. Sube este repo a GitHub.
2. En GitHub, ve a `Settings > Pages`.
3. En `Build and deployment`, elige:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/docs`
4. Guarda los cambios.

La página quedará en una URL parecida a:

```text
https://TU_USUARIO.github.io/prediccion-de-numeros/
```

## Automatización

El workflow `.github/workflows/update-site.yml` corre tres veces al día y también se puede ejecutar manualmente desde `Actions > Update lottery predictions > Run workflow`.

## Backfill histórico

El objetivo del proyecto es usar histórico desde `2010-08-01`, que es la primera fecha que Conectate responde con resultados en `https://www.conectate.com.do/loterias/?date=01-08-2010`.

Para cargar histórico disponible:

```bash
python3 scripts/backfill.py --from 2010-08-01
```

Nota: el script no inventa resultados. Si una fuente pública solo ofrece datos desde una fecha posterior, la página muestra la cobertura real cargada.

## Próximos pasos recomendados

- Ajustar el scraper si la fuente cambia su HTML.
- Añadir backfill histórico desde una fuente con archivo por fecha.
- Añadir más loterías o filtrar por lotería favorita.
- Cambiar los datos de ejemplo por resultados reales.
