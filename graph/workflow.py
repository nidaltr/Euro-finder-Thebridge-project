"""Grafo LangGraph del MVP.

Flujo: extractor -> planificador -> scraping -> normalizador -> traductor
       -> ordenar -> salida.
"""

from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from agents.extractor import extraer_filtros
from agents.filter import filtrar
from agents.normalizer import normalizar
from agents.planner import planificar
from agents.translator import traducir
from graph.state import GraphState
from schemas.models import RawListing
from scrapers.base import BasePlatformScraper
from scrapers.leboncoin import LeboncoinScraper
from scrapers.subito import SubitoScraper
from scrapers.willhaben import WillhabenScraper


logger = logging.getLogger(__name__)


SCRAPING_TIMEOUT_S = 25.0


# Registro plataforma -> clase de scraper.
REGISTRO_SCRAPERS: dict[str, type[BasePlatformScraper]] = {
    "leboncoin": LeboncoinScraper,
    "willhaben": WillhabenScraper,
    "subito": SubitoScraper,
}


async def nodo_extractor(state: GraphState) -> dict:
    """Llama al LLM, salvo que el estado pida saltarselo (filtros ya vienen)."""
    if state.get("skip_extractor"):
        existentes = state.get("filtros")
        logger.info(
            "[extractor] omitido (skip_extractor=True). Filtros recibidos: %s",
            existentes.model_dump() if existentes else None,
        )
        return {}
    query = state["query"]
    logger.info("[extractor] query: %r", query)
    filtros = await extraer_filtros(query)
    logger.info("[extractor] filtros: %s", filtros.model_dump())
    return {"filtros": filtros}


async def nodo_aplicar_overrides(state: GraphState) -> dict:
    """Aplica los campos no-vacios de `overrides` sobre los filtros existentes.

    Lo que envia la UI gana al LLM. Si no hay overrides ni filtros, no toca nada.
    """
    overrides = state.get("overrides") or {}
    filtros = state.get("filtros")
    if filtros is None or not overrides:
        return {}
    limpio = {k: v for k, v in overrides.items() if v not in (None, "", [], {})}
    if not limpio:
        return {}
    nuevos = filtros.model_copy(update=limpio)
    logger.info("[overrides] aplicados: %s", limpio)
    return {"filtros": nuevos}


async def nodo_planificador(state: GraphState) -> dict:
    filtros = state["filtros"]
    assert filtros is not None, "planificador necesita filtros del extractor"
    plataformas = planificar(filtros)
    logger.info("[planificador] plataformas: %s", plataformas)
    return {"plataformas": plataformas}


async def nodo_scraping(state: GraphState) -> dict:
    """Lanza todos los scrapers en paralelo con un timeout global.

    Si un scraper falla o expira, su lista queda vacia y el resto continua.
    """
    filtros = state["filtros"]
    plataformas = state["plataformas"]
    assert filtros is not None

    nombres: list[str] = []
    tareas: list[asyncio.Task[list[RawListing]]] = []
    for nombre in plataformas:
        cls = REGISTRO_SCRAPERS.get(nombre)
        if cls is None:
            logger.warning("[scraping] plataforma sin scraper registrado: %s", nombre)
            continue
        nombres.append(nombre)
        tareas.append(asyncio.create_task(cls().buscar(filtros), name=nombre))

    inicio = asyncio.get_event_loop().time()
    done, pending = await asyncio.wait(
        tareas, timeout=SCRAPING_TIMEOUT_S, return_when=asyncio.ALL_COMPLETED
    )
    for p in pending:
        p.cancel()
        logger.warning("[scraping] timeout de %s tras %.1fs", p.get_name(), SCRAPING_TIMEOUT_S)

    por_plataforma: dict[str, list[RawListing]] = {}
    for nombre, tarea in zip(nombres, tareas):
        if tarea in done:
            try:
                por_plataforma[nombre] = tarea.result()
            except Exception as exc:
                logger.warning("[scraping] %s fallo: %s", nombre, exc)
                por_plataforma[nombre] = []
        else:
            por_plataforma[nombre] = []
    elapsed = asyncio.get_event_loop().time() - inicio
    for nombre, lst in por_plataforma.items():
        logger.info("[scraping] %s -> %d crudos", nombre, len(lst))
    logger.info("[scraping] tiempo total: %.2fs", elapsed)
    return {"crudos_por_plataforma": por_plataforma}


async def nodo_normalizador(state: GraphState) -> dict:
    crudos = state.get("crudos_por_plataforma") or {}
    resultados = normalizar(crudos)
    logger.info("[normalizador] %d resultados normalizados", len(resultados))
    return {"resultados": resultados}


async def nodo_filtro(state: GraphState) -> dict:
    """Aplica los filtros extraidos sobre los resultados normalizados."""
    filtros = state["filtros"]
    assert filtros is not None
    resultados = state.get("resultados") or []
    filtrados = filtrar(resultados, filtros)
    return {"resultados": filtrados}


async def nodo_traductor(state: GraphState) -> dict:
    resultados = state.get("resultados") or []
    traducidos = await traducir(resultados)
    return {"resultados": traducidos}


async def nodo_ordenar(state: GraphState) -> dict:
    """Ordena los resultados segun la estrategia elegida por el usuario.

    - 'relevancia' (default): intercalado natural por posicion nativa de cada
      plataforma (la primera de cada plataforma primero, luego la segunda,
      etc.). Desempate por nombre de plataforma para determinismo.
    - 'precio_asc': legacy, ordenado de barato a caro.
    """
    resultados = list(state.get("resultados") or [])
    orden = state.get("orden") or "relevancia"
    if orden == "precio_asc":
        resultados.sort(key=lambda r: r.precio_eur)
    else:
        resultados.sort(key=lambda r: (r.posicion_plataforma, r.plataforma))
    logger.info("[ordenar] estrategia=%s, %d resultados", orden, len(resultados))
    return {"resultados": resultados}


async def nodo_salida(state: GraphState) -> dict:
    resultados = state.get("resultados") or []
    print(f"\n=== {len(resultados)} resultados (ordenados por precio asc) ===\n")
    for i, r in enumerate(resultados, 1):
        titulo = r.titulo_es or r.titulo or ""
        print(
            f"{i:>3}. {r.precio_eur:>9.2f} EUR | {r.plataforma}/{r.pais} | "
            f"{titulo[:80]}"
        )
        if r.titulo_es and r.titulo and r.titulo != r.titulo_es:
            print(f"     original: {r.titulo[:80]}")
        if r.ubicacion:
            print(f"     ubicacion: {r.ubicacion}")
        print(f"     {r.url}")
        print()
    return {}


def build_graph():
    """Construye y compila el grafo LangGraph del MVP."""
    g = StateGraph(GraphState)
    g.add_node("extractor", nodo_extractor)
    g.add_node("aplicar_overrides", nodo_aplicar_overrides)
    g.add_node("planificador", nodo_planificador)
    g.add_node("scraping", nodo_scraping)
    g.add_node("normalizador", nodo_normalizador)
    g.add_node("filtro", nodo_filtro)
    g.add_node("traductor", nodo_traductor)
    g.add_node("ordenar", nodo_ordenar)
    g.add_node("salida", nodo_salida)

    g.add_edge(START, "extractor")
    g.add_edge("extractor", "aplicar_overrides")
    g.add_edge("aplicar_overrides", "planificador")
    g.add_edge("planificador", "scraping")
    g.add_edge("scraping", "normalizador")
    g.add_edge("normalizador", "filtro")
    g.add_edge("filtro", "traductor")
    g.add_edge("traductor", "ordenar")
    g.add_edge("ordenar", "salida")
    g.add_edge("salida", END)

    return g.compile()
