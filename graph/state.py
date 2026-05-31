"""Estado compartido del grafo LangGraph."""

from __future__ import annotations

from typing import Literal, TypedDict

from schemas.models import NormalizedListing, RawListing, SearchFilters


OrdenResultados = Literal["relevancia", "precio_asc"]


class GraphState(TypedDict, total=False):
    """Estado que fluye entre los nodos del grafo.

    `total=False` para que cada nodo pueda escribir solo los campos que produce
    sin tener que preocuparse de los demas.
    """

    query: str
    filtros: SearchFilters | None
    overrides: dict
    skip_extractor: bool
    orden: OrdenResultados
    plataformas: list[str]
    crudos_por_plataforma: dict[str, list[RawListing]]
    resultados: list[NormalizedListing]
