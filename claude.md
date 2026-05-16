```markdown
# Proyecto: Buscador P2P Cross-Border Europeo (MVP)

## Qué es
Sistema multiagente que recibe una búsqueda de producto en lenguaje natural (en
español), busca en varias plataformas europeas de compraventa de segunda mano,
traduce y normaliza los resultados, y los devuelve como tarjetas con foto, datos
clave-valor y enlace al anuncio original.

Es un proyecto académico (capstone de máster en IA generativa). La prioridad
absoluta es que FUNCIONE de punta a punta. No optimizar coste, no pulir la UI,
no escalar. Esas fases vienen después.

## Alcance del MVP (construir AHORA)
- Agente extractor de filtros desde lenguaje natural (LLM).
- Planificador simple (Python, sin LLM): decide en qué plataformas buscar.
- Scrapers de 3 plataformas para empezar (ampliable después).
- Scraping en paralelo con asyncio.
- Normalizador (Python): unifica todos los resultados a un esquema común.
- Agente traductor (LLM): traduce título y descripción al español en lote.
- Salida: lista de tarjetas (thumbnail + campos clave-valor + enlace).
- Orquestación con un grafo LangGraph.
- Interfaz mínima en Streamlit.
- Tracing con LangSmith.

## Diferido (NO construir todavía, ni proponerlo)
- Agente supervisor de scraping y reformulación multi-idioma.
- Auto-healing de selectores.
- Ranking con embeddings (en el MVP se ordena por precio ascendente).
- Agente presentador con LLM (en el MVP la salida es la lista cruda ordenada).
- Plataformas más allá de las 3-5 iniciales.
- Proxies, resolución de captchas.

## Arquitectura (grafo LangGraph)
Flujo lineal de nodos sobre un estado compartido:

[Query del usuario]
  -> Extractor de filtros        (LLM Opus, structured output)
  -> Planificador                (Python, reglas)
  -> Scraping en paralelo        (Python + httpx/Playwright, asyncio.gather)
  -> Normalizador                (Python puro)
  -> Traductor                   (LLM Haiku, en lote)
  -> Ordenar por precio asc.     (Python)
  -> Salida: lista de tarjetas

Solo hay dos llamadas a LLM en el flujo: extractor (entender la query) y
traductor (idiomas). Todo lo demás es código determinista.

## Stack técnico
- Lenguaje: Python 3.11+
- Framework de agentes: LangGraph + LangChain
- LLMs (proveedor: Anthropic):
  - Extractor de filtros: Claude Opus  -> modelo "claude-opus-4-7"
  - Traductor:            Claude Haiku -> modelo "claude-haiku-4-5-20251001"
- Salida estructurada: Pydantic v2
- Scraping ligero (Tier 1): httpx (async) + selectolax
- Scraping con navegador (Tier 2/3): Playwright (async, headless)
- Interfaz: Streamlit
- Observabilidad: LangSmith
- Cache local: SQLite (o ficheros JSON) para modo demo offline
- Gestión de entorno: venv + requirements.txt
- Variables de entorno: archivo .env (python-dotenv)

## Estructura de carpetas
proyecto/
  agents/
    extractor.py        # extractor de filtros (LLM)
    planner.py          # planificador (Python)
    normalizer.py       # normalización post-scraping (Python)
    translator.py       # traductor (LLM)
  scrapers/
    base.py             # clase abstracta BasePlatformScraper
    leboncoin.py        # Tier 1
    kleinanzeigen.py    # Tier 1
    subito.py           # Tier 1
  graph/
    workflow.py         # definición del grafo LangGraph
    state.py            # TypedDict del estado del grafo
  schemas/
    models.py           # modelos Pydantic
  ui/
    app.py              # interfaz Streamlit
  cache/                # resultados cacheados (modo demo offline)
  tests/                # scripts de prueba por componente
  .env                  # claves API (no subir a git)
  .env.example          # plantilla de .env
  requirements.txt
  CLAUDE.md
  README.md

## Esquemas de datos (Pydantic) — referencia
- SearchFilters: categoria, query_busqueda, marca, modelo, precio_min,
  precio_max, anio_min, anio_max, paises_preferidos, paises_excluidos,
  notas_libres. Todos opcionales salvo categoria y query_busqueda.
- RawListing: lo que devuelve un scraper antes de normalizar. Campos crudos
  tal cual vienen de la web.
- NormalizedListing: esquema común final. Campos: id, plataforma, pais,
  titulo, titulo_es, precio_eur, moneda_original, precio_original,
  descripcion, descripcion_es, idioma, ubicacion, url, thumbnail_url,
  fecha_publicacion, categoria_detectada. Campos específicos opcionales
  (anio, km, combustible, marca, modelo) según categoría.

## Plataformas y tier de scraping
- Leboncoin (FR)     — Tier 1 (httpx + selectolax)
- Kleinanzeigen (DE) — Tier 1 (httpx + selectolax)
- Subito (IT)        — Tier 1 (httpx + selectolax)
(Ampliación futura: Willhaben AT, Bazos CZ — Tier 1; Marktplaats NL,
OLX.pl, Tutti CH, Blocket SE — Tier 2; Wallapop ES — Tier 3.)

## Convenciones de código
- Todo el código asíncrono donde tenga sentido (async/await).
- Toda salida de LLM mediante structured output con Pydantic, nunca parsing
  de texto libre.
- Cada scraper hereda de BasePlatformScraper e implementa los mismos métodos.
- Manejo de errores robusto: si un scraper falla, devuelve lista vacía y
  registra el error; nunca tumba al resto del sistema.
- Idioma de la interfaz, prompts y comentarios de cara al usuario: español.
- Logging claro en cada nodo del grafo (entrada, salida, tiempos).

## Cómo se ejecuta
- Tests de componente: python tests/test_<componente>.py
- App completa: streamlit run ui/app.py
```

---