# Eurofinder

Buscador P2P cross-border europeo (MVP). Recibe una búsqueda en español, consulta
varias plataformas europeas de segunda mano, normaliza y traduce los resultados,
y los devuelve como tarjetas.

Ver [CLAUDE.md](CLAUDE.md) para la especificación completa del proyecto.

## Requisitos
- Python 3.11+
- Git

## Instalación

```powershell
# 1. Clonar y entrar al directorio
cd desarollo

# 2. Crear y activar venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar navegador para Playwright
playwright install chromium

# 5. Configurar variables de entorno
copy .env.example .env
# Editar .env y rellenar ANTHROPIC_API_KEY y LANGSMITH_API_KEY
```

## Ejecución

```powershell
# App completa (interfaz Streamlit)
streamlit run ui/app.py

# Tests de componente individual
python tests/test_<componente>.py
```

## LangSmith

El proyecto carga `.env` antes de importar LangChain/LangGraph y sincroniza
`LANGSMITH_*` con las variables legacy `LANGCHAIN_*`.

Para verificar que las trazas llegan:

```powershell
python scripts/check_langsmith.py
```

Despues abre LangSmith, entra en el workspace correcto y selecciona el proyecto
`eurofinder` en Tracing.

## Leboncoin

Leboncoin puede bloquear peticiones con Datadome aunque Subito y Willhaben
funcionen. El scraper intenta primero el endpoint API no oficial mediante
`lbc` y despues el HTML antiguo. Si ambos devuelven 403, configura en `.env`:

```powershell
LEBONCOIN_PROXY_URL=http://usuario:password@host:puerto
LEBONCOIN_IMPERSONATE=chrome146
```

Lo mas fiable suele ser un proxy residencial o movil de Francia.

## Estructura

- `agents/` — extractor, planner, normalizer, translator
- `scrapers/` — uno por plataforma, heredan de `BasePlatformScraper`
- `graph/` — definición del grafo LangGraph y su estado compartido
- `schemas/` — modelos Pydantic
- `ui/` — interfaz Streamlit
- `cache/` — caché local de resultados (modo demo offline)
- `tests/` — pruebas por componente
