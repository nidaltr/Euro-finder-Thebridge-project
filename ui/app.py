"""Interfaz Streamlit del MVP Eurofinder.

UI orientada a Wallapop: campo de texto + expander con filtros estructurados
generados dinamicamente desde la taxonomia. Categoria -> grupo -> tipo se
eligen jerarquicamente, y al elegir tipo aparecen sus filtros propios.
"""

from __future__ import annotations

import asyncio
import html
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from observability import (
    configure_langsmith,
    langsmith_run_config,
    langsmith_tracing,
    wait_for_langsmith_traces,
)

# Cargar .env antes de cualquier import de LangChain/LangGraph.
configure_langsmith(ROOT_DIR / ".env")

# Windows usa cp1252 en stdout por defecto. Algunos nodos (nodo_salida) hacen
# `print()` con strings que pueden contener caracteres unicode no representables
# y eso revienta la busqueda con UnicodeEncodeError. Forzamos UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import streamlit as st

from graph.workflow import build_graph
from schemas.models import NormalizedListing, SearchFilters
from schemas.security import sanear_query
from schemas.taxonomia import (
    CategoriaTax,
    FILTROS_UNIVERSALES,
    FiltroDef,
    TAXONOMIA,
    buscar_categoria,
    buscar_tipo,
    claves_grupo,
    claves_tipo,
)


PLACEHOLDER_IMG = "https://placehold.co/200x150?text=sin+foto"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
)
logger = logging.getLogger("ui.app")


st.set_page_config(page_title="Eurofinder", page_icon=":mag:", layout="wide")


def _inject_global_styles() -> None:
    """Aplica una capa visual sobria sin cambiar componentes ni estado."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #07112c;
            --bg-elevated: #0c1a3d;
            --bg-deep: #050b1d;
            --surface: rgba(255, 255, 255, 0.045);
            --surface-hover: rgba(255, 255, 255, 0.075);
            --border: rgba(255, 255, 255, 0.10);
            --border-strong: rgba(255, 255, 255, 0.18);
            --border-gold: rgba(245, 200, 66, 0.38);
            --text: #f1ecdc;
            --text-muted: #9ba6c5;
            --text-dim: #6a7593;
            --gold: #f5c842;
            --gold-hover: #fad366;
            --gold-faint: rgba(245, 200, 66, 0.12);
            --gold-glow: rgba(245, 200, 66, 0.25);
            --font-serif: Georgia, "Times New Roman", serif;
            --font-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --font-mono: "Cascadia Mono", "Consolas", monospace;
        }

        .stApp {
            background:
                radial-gradient(1100px 580px at 12% -10%, rgba(245, 200, 66, 0.08), transparent 60%),
                radial-gradient(900px 600px at 95% 8%, rgba(70, 100, 200, 0.13), transparent 60%),
                var(--bg);
            color: var(--text);
            font-family: var(--font-sans);
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1240px;
            padding: 1.6rem 2rem 4rem;
        }

        .eurofinder-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            margin-bottom: 4.2rem;
        }

        .eurofinder-brand {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .eurofinder-mark {
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border: 1px solid var(--border-gold);
            border-radius: 50%;
            background: var(--gold-faint);
            color: var(--gold);
            font-family: var(--font-serif);
            font-size: 1.2rem;
        }

        .eurofinder-brand-name {
            font-family: var(--font-serif);
            font-weight: 400;
            font-size: 1.5rem;
            color: var(--text);
            letter-spacing: 0;
        }

        .eurofinder-brand-name em {
            color: var(--gold);
            font-style: italic;
        }

        .eurofinder-live {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            font-family: var(--font-mono);
            color: var(--text-dim);
            font-size: 0.68rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .eurofinder-live-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--gold);
            box-shadow: 0 0 12px var(--gold-glow);
        }

        .eurofinder-hero {
            max-width: 820px;
            margin: 0 auto 1.25rem;
            text-align: center;
        }

        .eurofinder-title {
            font-family: var(--font-serif);
            color: var(--text);
            font-size: clamp(2.15rem, 4.5vw, 3rem);
            font-weight: 300;
            line-height: 1.05;
            letter-spacing: 0;
            margin: 0;
        }

        .eurofinder-title em {
            color: var(--gold);
            font-weight: 400;
            font-style: italic;
        }

        .eurofinder-byline {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 0.9rem;
            font-family: var(--font-mono);
            font-size: 0.66rem;
            letter-spacing: 0.2em;
            color: var(--text-dim);
            text-transform: uppercase;
        }

        .eurofinder-platforms {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            margin: 0.75rem 0 1.05rem;
            color: var(--text-dim);
            font-family: var(--font-mono);
            font-size: 0.68rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .platform-list {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .platform-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
        }

        .mini-flag {
            width: 18px;
            height: 12px;
            border-radius: 2px;
            box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18) inset;
            overflow: hidden;
            display: inline-grid;
        }

        .flag-fr {
            background: linear-gradient(90deg, #0055a4 0 33.33%, #fff 33.33% 66.66%, #ef4135 66.66%);
        }

        .flag-it {
            background: linear-gradient(90deg, #008c45 0 33.33%, #fff 33.33% 66.66%, #cd212a 66.66%);
        }

        .flag-at {
            background: linear-gradient(180deg, #ed2939 0 33.33%, #fff 33.33% 66.66%, #ed2939 66.66%);
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-baseweb="select"] > div {
            background-color: var(--bg-deep);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text);
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus {
            border-color: var(--border-gold);
            box-shadow: 0 0 0 4px rgba(245, 200, 66, 0.08);
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: var(--text-dim);
        }

        label,
        div[data-testid="stWidgetLabel"] p {
            color: var(--text-muted);
            font-size: 0.78rem;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background: var(--gold);
            border: 1px solid var(--gold);
            border-radius: 10px;
            color: #1a1305;
            font-weight: 650;
            min-height: 2.9rem;
            padding-left: 1.8rem;
            padding-right: 1.8rem;
        }

        div[data-testid="stButton"] button[kind="primary"] p {
            color: #1a1305;
            font-weight: 650;
        }

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: var(--gold-hover);
            border-color: var(--gold-hover);
            color: #1a1305;
        }

        div[data-testid="stAlert"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            color: var(--text-muted);
        }

        div[data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: none;
        }

        div[data-testid="stExpander"] summary {
            color: var(--text);
            font-weight: 600;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: none;
            padding: 1rem;
            transition: background 160ms ease, border-color 160ms ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            background: var(--surface-hover);
            border-color: var(--border-strong);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] h3 {
            color: var(--text);
            font-family: var(--font-serif);
            font-size: 1.35rem;
            font-weight: 400;
            line-height: 1.25;
            margin-bottom: 0.45rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] img {
            border-radius: 6px;
            border: 1px solid var(--border);
            object-fit: cover;
        }

        div[data-testid="stMarkdownContainer"] strong {
            color: var(--gold);
            font-weight: 500;
        }

        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stCaptionContainer"] {
            color: var(--text-muted);
        }

        a[data-testid="stLinkButton"] {
            background: transparent;
            border-radius: 10px;
            border-color: var(--border-gold);
            color: var(--gold);
            font-weight: 600;
        }

        a[data-testid="stLinkButton"]:hover {
            border-color: var(--gold);
            color: #1a1305;
            background: var(--gold);
        }

        hr {
            border-color: var(--border);
        }

        .eurofinder-footer {
            margin-top: 4rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            font-family: var(--font-mono);
            color: var(--text-dim);
            font-size: 0.66rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .eurofinder-footer b {
            color: var(--text);
            font-weight: 500;
        }

        @media (max-width: 700px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .eurofinder-header {
                margin-bottom: 2.8rem;
            }

            .eurofinder-title {
                font-size: 2.15rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <header class="eurofinder-header">
            <div class="eurofinder-brand">
                <div class="eurofinder-mark">★</div>
                <div class="eurofinder-brand-name">Euro<em>finder</em></div>
            </div>
            <div class="eurofinder-live">
                <span class="eurofinder-live-dot"></span>
                En vivo
            </div>
        </header>
        <section class="eurofinder-hero">
            <h1 class="eurofinder-title">Busca lo que deseas por <em>toda Europa</em>.</h1>
            <div class="eurofinder-byline">
                <span class="eurofinder-live-dot"></span>
                Impulsado por IA
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_platform_meta() -> None:
    st.markdown(
        """
        <div class="eurofinder-platforms">
            <div class="platform-list">
                <span class="platform-chip"><span class="mini-flag flag-fr"></span> Leboncoin</span>
                <span class="platform-chip"><span class="mini-flag flag-it"></span> Subito</span>
                <span class="platform-chip"><span class="mini-flag flag-at"></span> Willhaben</span>
            </div>
            <span>Filtros opcionales disponibles</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    st.markdown(
        """
        <footer class="eurofinder-footer">
            <span><b>Eurofinder</b></span>
            <span>Búsqueda europea de segunda mano</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ejecucion del grafo
# ---------------------------------------------------------------------------

@st.cache_resource
def _grafo():
    logger.info("Construyendo grafo (una sola vez por sesion)...")
    return build_graph()


def _ejecutar(estado_inicial: dict) -> tuple[list[NormalizedListing], SearchFilters | None]:
    grafo = _grafo()
    logger.info("Lanzando grafo. skip_extractor=%s", estado_inicial.get("skip_extractor"))

    def runner() -> dict:
        with langsmith_tracing():
            return asyncio.run(
                grafo.ainvoke(
                    estado_inicial,
                    config=langsmith_run_config("streamlit"),
                )
            )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            estado_final = pool.submit(runner).result()
    finally:
        wait_for_langsmith_traces()

    resultados = estado_final.get("resultados") or []
    filtros = estado_final.get("filtros")
    logger.info("Grafo termino con %d resultados", len(resultados))
    return resultados, filtros


# ---------------------------------------------------------------------------
# Render de tarjetas
# ---------------------------------------------------------------------------

def _formato_fecha(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d") if dt else None


def _render_tarjeta(r: NormalizedListing) -> None:
    with st.container(border=True):
        col_img, col_txt = st.columns([1, 3], vertical_alignment="top")
        with col_img:
            st.image(r.thumbnail_url or PLACEHOLDER_IMG, width="stretch")
        with col_txt:
            titulo = r.titulo_es or r.titulo or "(sin título)"
            st.markdown(f"### {html.escape(titulo)}")
            if r.titulo_es and r.titulo and r.titulo_es != r.titulo:
                st.caption(f"Original: {r.titulo}")

            meta = [f"**{r.precio_eur:,.2f} EUR**".replace(",", ".")]
            meta.append(f"{r.plataforma} ({r.pais})")
            if r.ubicacion:
                meta.append(r.ubicacion)
            fecha = _formato_fecha(r.fecha_publicacion)
            if fecha:
                meta.append(fecha)
            st.markdown(" - ".join(meta))

            descripcion = r.descripcion_es or r.descripcion
            if descripcion:
                frag = descripcion.strip().replace("\n", " ")
                if len(frag) > 300:
                    frag = frag[:300].rstrip() + "..."
                st.write(frag)

            st.link_button("Abrir anuncio original", r.url)


def _render_resultados(resultados: list[NormalizedListing]) -> None:
    if not resultados:
        st.warning(
            "No se han encontrado anuncios. Prueba aflojando algún filtro "
            "(ampliar precio, quitar talla/color, cambiar tipo o categoría)."
        )
        return

    desglose: dict[str, int] = {}
    for r in resultados:
        desglose[r.plataforma] = desglose.get(r.plataforma, 0) + 1
    detalle = " - ".join(f"{k}: {v}" for k, v in sorted(desglose.items()))
    st.markdown(f"**{len(resultados)} resultados encontrados**")
    st.caption(detalle)

    for r in resultados:
        _render_tarjeta(r)


# ---------------------------------------------------------------------------
# Estado de filtros en session_state
# ---------------------------------------------------------------------------

# Para cada widget del expander reservamos una clave `f_<nombre>` en session_state.
# Inicializamos a "vacio" segun el widget.


def _valor_vacio(widget: str) -> Any:
    if widget == "lista_multi":
        return []
    if widget == "numero":
        return 0
    return ""


def _todos_los_filtros() -> list[FiltroDef]:
    """Coleccion estable de TODOS los FiltroDef de la taxonomia (universales +
    especificos de cualquier tipo), para sembrar session_state."""
    seen: dict[str, FiltroDef] = {f.nombre: f for f in FILTROS_UNIVERSALES}
    for cat in TAXONOMIA:
        for g in cat.grupos:
            for t in g.tipos:
                for f in t.filtros:
                    seen.setdefault(f.nombre, f)
    return list(seen.values())


def _init_session() -> None:
    for f in _todos_los_filtros():
        st.session_state.setdefault(f"f_{f.nombre}", _valor_vacio(f.widget))
    st.session_state.setdefault("f_categoria", TAXONOMIA[0].clave)
    st.session_state.setdefault("f_grupo", "")
    st.session_state.setdefault("f_tipo_producto", "")
    st.session_state.setdefault("query_texto", "")
    st.session_state.setdefault("ultima_query_extraida", None)
    st.session_state.setdefault("resultados", None)
    st.session_state.setdefault("_volcado_pendiente", None)
    st.session_state.setdefault("f_orden", "Relevancia")


def _aplicar_volcado_pendiente() -> None:
    """Si hay un SearchFilters en `_volcado_pendiente`, lo vuelca al session_state.

    Llamado al inicio del script, ANTES de crear ningun widget, para evitar
    `cannot be modified after the widget with key X is instantiated`.
    """
    f = st.session_state.get("_volcado_pendiente")
    if f is None:
        return
    _volcar_filtros_a_session(f)
    st.session_state["_volcado_pendiente"] = None


def _volcar_filtros_a_session(f: SearchFilters) -> None:
    """Sincroniza el session_state con los valores extraidos por el LLM."""
    st.session_state["f_categoria"] = f.categoria
    st.session_state["f_grupo"] = f.grupo or ""
    st.session_state["f_tipo_producto"] = f.tipo_producto or ""
    for fd in _todos_los_filtros():
        valor = getattr(f, fd.nombre, None)
        if valor is None:
            st.session_state[f"f_{fd.nombre}"] = _valor_vacio(fd.widget)
            continue
        if fd.widget == "numero":
            try:
                st.session_state[f"f_{fd.nombre}"] = int(valor) if isinstance(valor, (int, float)) else 0
            except Exception:
                st.session_state[f"f_{fd.nombre}"] = 0
        elif fd.widget == "lista_multi":
            st.session_state[f"f_{fd.nombre}"] = list(valor) if valor else []
        else:
            st.session_state[f"f_{fd.nombre}"] = str(valor)


def _construir_filtros_desde_session() -> SearchFilters:
    """Toma los valores actuales del expander y construye un SearchFilters."""
    overrides: dict[str, Any] = {}
    for fd in _todos_los_filtros():
        bruto = st.session_state.get(f"f_{fd.nombre}")
        if bruto in (None, "", [], 0):
            continue
        if fd.widget == "numero":
            try:
                overrides[fd.nombre] = int(bruto)
            except Exception:
                pass
        elif fd.widget == "lista_multi":
            overrides[fd.nombre] = list(bruto)
        else:
            overrides[fd.nombre] = str(bruto).strip()

    categoria = st.session_state.get("f_categoria") or "otros"
    grupo = st.session_state.get("f_grupo") or None
    tipo_producto = st.session_state.get("f_tipo_producto") or None
    query_texto = sanear_query(st.session_state.get("query_texto") or "")

    return SearchFilters(
        categoria=categoria,
        grupo=grupo,
        tipo_producto=tipo_producto,
        query_texto=query_texto,
        **overrides,
    )


# ---------------------------------------------------------------------------
# Expander dinamico de filtros
# ---------------------------------------------------------------------------

def _opciones_vacio(*valores: str) -> list[str]:
    return ["", *valores]


def _render_filtro(fd: FiltroDef) -> None:
    """Pinta un widget que escribe en st.session_state[f_<nombre>]."""
    key = f"f_{fd.nombre}"
    label = fd.label
    if fd.widget == "lista":
        opciones = _opciones_vacio(*(fd.valores or ()))
        actual = st.session_state.get(key) or ""
        idx = opciones.index(actual) if actual in opciones else 0
        st.selectbox(label, opciones, index=idx, key=key)
    elif fd.widget == "lista_multi":
        valores = list(fd.valores or ())
        st.multiselect(label, valores, key=key)
    elif fd.widget == "numero":
        st.number_input(label, min_value=0, step=1, key=key)
    else:  # texto
        st.text_input(label, key=key)


def _render_expander_filtros() -> None:
    with st.expander("Filtros (ampliar para ajustar a mano)", expanded=False):

        # --- Nivel 1: categoría ---
        cat_claves = [c.clave for c in TAXONOMIA]
        cat_labels = {c.clave: c.label for c in TAXONOMIA}
        actual_cat = st.session_state.get("f_categoria") or cat_claves[0]
        if actual_cat not in cat_claves:
            actual_cat = cat_claves[0]
        idx_cat = cat_claves.index(actual_cat)
        st.selectbox(
            "Categoría", cat_claves, index=idx_cat, key="f_categoria",
            format_func=lambda k: cat_labels.get(k, k),
        )

        # --- Nivel 2: grupo (depende de la categoría) ---
        grupos = claves_grupo(st.session_state["f_categoria"])
        cat_obj: CategoriaTax | None = buscar_categoria(st.session_state["f_categoria"])
        grupo_labels: dict[str, str] = {}
        if cat_obj is not None:
            grupo_labels = {g.clave: g.label for g in cat_obj.grupos}
        if grupos:
            opciones_g = _opciones_vacio(*grupos)
            actual_g = st.session_state.get("f_grupo") or ""
            if actual_g not in opciones_g:
                actual_g = ""
                st.session_state["f_grupo"] = ""
            st.selectbox(
                "Grupo", opciones_g, index=opciones_g.index(actual_g), key="f_grupo",
                format_func=lambda k: grupo_labels.get(k, "(sin grupo)") if k else "(cualquiera)",
            )
        else:
            st.session_state["f_grupo"] = ""

        # --- Nivel 3: tipo de producto (depende del grupo) ---
        tipos = claves_tipo(st.session_state["f_categoria"], st.session_state.get("f_grupo", ""))
        tipo_labels: dict[str, str] = {}
        if cat_obj is not None and st.session_state.get("f_grupo"):
            for g in cat_obj.grupos:
                if g.clave == st.session_state["f_grupo"]:
                    tipo_labels = {t.clave: t.label for t in g.tipos}
                    break
        if tipos:
            opciones_t = _opciones_vacio(*tipos)
            actual_t = st.session_state.get("f_tipo_producto") or ""
            if actual_t not in opciones_t:
                actual_t = ""
                st.session_state["f_tipo_producto"] = ""
            st.selectbox(
                "Tipo de producto", opciones_t, index=opciones_t.index(actual_t),
                key="f_tipo_producto",
                format_func=lambda k: tipo_labels.get(k, "(sin tipo)") if k else "(cualquiera)",
            )
        else:
            st.session_state["f_tipo_producto"] = ""

        st.markdown("---")
        # Selector de orden de resultados. Lo dejamos arriba del todo en el
        # bloque de universales porque aplica a cualquier busqueda.
        opciones_orden = ["Relevancia", "Precio ascendente"]
        actual_orden = st.session_state.get("f_orden") or "Relevancia"
        if actual_orden not in opciones_orden:
            actual_orden = "Relevancia"
        st.selectbox(
            "Ordenar por",
            opciones_orden,
            index=opciones_orden.index(actual_orden),
            key="f_orden",
            help="'Relevancia' intercala los anuncios mas prominentes de cada "
                 "plataforma. 'Precio ascendente' lista de barato a caro (legacy).",
        )

        st.markdown("**Filtros universales**")
        for fd in FILTROS_UNIVERSALES:
            _render_filtro(fd)

        # --- Especificos del tipo elegido ---
        tipo_clave = st.session_state.get("f_tipo_producto") or None
        if tipo_clave:
            encontrado = buscar_tipo(tipo_clave)
            if encontrado is not None:
                _, _, tipo_obj = encontrado
                if tipo_obj.filtros:
                    st.markdown("---")
                    sufijo = " (rama profunda)" if tipo_obj.rama_profunda else ""
                    st.markdown(f"**Filtros de {tipo_obj.label}{sufijo}**")
                    for fd in tipo_obj.filtros:
                        _render_filtro(fd)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _hay_algun_filtro_no_universal(f: SearchFilters) -> bool:
    """True si el SearchFilters trae al menos un filtro no universal/posicional."""
    no_universales = {f.nombre for f in FILTROS_UNIVERSALES} | {
        "categoria", "grupo", "tipo_producto", "query_texto", "notas_libres",
    }
    for nombre, valor in f.model_dump(exclude_none=True).items():
        if nombre in no_universales:
            continue
        if valor not in (None, "", [], 0):
            return True
    return False


def main() -> None:
    _inject_global_styles()
    _init_session()
    # Si la ultima busqueda dejo filtros nuevos del LLM pendientes de pintar,
    # los aplicamos aqui ANTES de instanciar cualquier widget.
    _aplicar_volcado_pendiente()

    _render_header()

    col_query, col_submit = st.columns([5, 1], vertical_alignment="bottom")
    with col_query:
        st.text_input(
            "¿Qué buscas?",
            key="query_texto",
            placeholder="Ej. Rolex Day-Date oro automático, Audi A5 diésel automático <15000, chaqueta Prada cuero hombre L...",
        )
    with col_submit:
        submitted = st.button("Buscar", type="primary", use_container_width=True)

    _render_platform_meta()

    _render_expander_filtros()

    if submitted:
        query = sanear_query(st.session_state.get("query_texto") or "")
        filtros_form = _construir_filtros_desde_session()

        cambio_query = bool(query) and query != st.session_state.get("ultima_query_extraida")
        hay_filtros = _hay_algun_filtro_no_universal(filtros_form)

        if not query and not hay_filtros:
            st.error("Escribe una búsqueda o ajusta filtros antes de pulsar Buscar.")
        else:
            with st.spinner("Buscando en plataformas europeas..."):
                try:
                    orden_ui = st.session_state.get("f_orden") or "Relevancia"
                    orden_interno = (
                        "precio_asc" if orden_ui == "Precio ascendente" else "relevancia"
                    )
                    if cambio_query or (not hay_filtros and query):
                        # Hay query nueva: que el LLM extraiga desde cero.
                        estado_inicial: dict = {
                            "query": query,
                            "overrides": {},
                            "skip_extractor": False,
                            "orden": orden_interno,
                        }
                    else:
                        # Solo cambiaron filtros (o no hay query). Saltamos LLM
                        # y usamos lo del formulario tal cual.
                        estado_inicial = {
                            "query": query or filtros_form.query_texto or "",
                            "filtros": filtros_form,
                            "overrides": {},
                            "skip_extractor": True,
                            "orden": orden_interno,
                        }
                    resultados, filtros_finales = _ejecutar(estado_inicial)
                except Exception as exc:
                    st.error(f"Error ejecutando la búsqueda: {exc}")
                    return

            st.session_state["resultados"] = resultados
            if cambio_query and filtros_finales is not None:
                # No podemos mutar las claves f_* despues de pintar widgets.
                # Lo dejamos pendiente y se aplica en el proximo rerun.
                st.session_state["_volcado_pendiente"] = filtros_finales
                st.session_state["ultima_query_extraida"] = query
            st.rerun()

    if st.session_state.get("resultados") is not None:
        _render_resultados(st.session_state["resultados"])
    else:
        st.info("Escribe una búsqueda y pulsa **Buscar** para empezar.")

    _render_footer()


main()
