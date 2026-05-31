"""Interfaz Streamlit del MVP Eurofinder.

UI orientada a Wallapop: campo de texto + expander con filtros estructurados
generados dinamicamente desde la taxonomia. Categoria -> grupo -> tipo se
eligen jerarquicamente, y al elegir tipo aparecen sus filtros propios.
"""

from __future__ import annotations

import asyncio
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
            st.image(r.thumbnail_url or PLACEHOLDER_IMG, use_container_width=True)
        with col_txt:
            titulo = r.titulo_es or r.titulo or "(sin titulo)"
            st.markdown(f"### {titulo}")
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
            "No se han encontrado anuncios. Prueba aflojando algun filtro "
            "(ampliar precio, quitar talla/color, cambiar tipo o categoria)."
        )
        return

    desglose: dict[str, int] = {}
    for r in resultados:
        desglose[r.plataforma] = desglose.get(r.plataforma, 0) + 1
    detalle = " - ".join(f"{k}: {v}" for k, v in sorted(desglose.items()))
    st.markdown(f"**{len(resultados)} resultados** ordenados por precio asc.")
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
    query_texto = (st.session_state.get("query_texto") or "").strip()

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

        # --- Nivel 1: categoria ---
        cat_claves = [c.clave for c in TAXONOMIA]
        cat_labels = {c.clave: c.label for c in TAXONOMIA}
        actual_cat = st.session_state.get("f_categoria") or cat_claves[0]
        if actual_cat not in cat_claves:
            actual_cat = cat_claves[0]
        idx_cat = cat_claves.index(actual_cat)
        st.selectbox(
            "Categoria", cat_claves, index=idx_cat, key="f_categoria",
            format_func=lambda k: cat_labels.get(k, k),
        )

        # --- Nivel 2: grupo (depende de la categoria) ---
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
                    st.markdown(
                        f"**Filtros de {tipo_obj.label}"
                        + (" (RAMA PROFUNDA)" if tipo_obj.rama_profunda else "")
                        + "**"
                    )
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
    _init_session()
    # Si la ultima busqueda dejo filtros nuevos del LLM pendientes de pintar,
    # los aplicamos aqui ANTES de instanciar cualquier widget.
    _aplicar_volcado_pendiente()

    st.title("Eurofinder")
    st.caption(
        "Buscador de productos de segunda mano en plataformas europeas. "
        "Escribe en espanol; los resultados se traducen automaticamente."
    )

    st.text_input(
        "Que buscas?",
        key="query_texto",
        placeholder="ej. Rolex Day-Date oro automatico, Audi A5 diesel automatico <15000, chaqueta Prada cuero hombre L...",
    )

    _render_expander_filtros()

    submitted = st.button("Buscar", type="primary")

    if submitted:
        query = (st.session_state.get("query_texto") or "").strip()
        filtros_form = _construir_filtros_desde_session()

        cambio_query = bool(query) and query != st.session_state.get("ultima_query_extraida")
        hay_filtros = _hay_algun_filtro_no_universal(filtros_form)

        if not query and not hay_filtros:
            st.error("Escribe una busqueda o ajusta filtros antes de pulsar Buscar.")
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
                    st.error(f"Error ejecutando la busqueda: {exc}")
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
        st.info("Escribe una busqueda y pulsa **Buscar** para empezar.")


main()
