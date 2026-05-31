"""Planificador: decide en que plataformas buscar (Python puro, sin LLM)."""

from __future__ import annotations

from schemas.models import SearchFilters


# Mapeo plataforma -> codigo ISO de pais. Se ira ampliando segun se sumen scrapers.
PLATAFORMAS_DISPONIBLES: dict[str, str] = {
    "leboncoin": "FR",
    "willhaben": "AT",
    "subito": "IT",
}


def planificar(filtros: SearchFilters) -> list[str]:
    """Devuelve la lista de plataformas en las que conviene buscar.

    Reglas:
      - Excluye plataformas cuyo pais este en `filtros.paises_excluidos`.
      - Si `filtros.paises_preferidos` no esta vacio, intersecta con esa lista.
        Si la interseccion queda vacia, ignora la preferencia y devuelve todas
        las no excluidas (mejor algo que nada).
    """
    excluidos = {p.upper() for p in filtros.paises_excluidos}
    preferidos = {p.upper() for p in filtros.paises_preferidos}

    no_excluidas = [
        nombre for nombre, pais in PLATAFORMAS_DISPONIBLES.items()
        if pais.upper() not in excluidos
    ]

    if preferidos:
        intersec = [
            nombre for nombre in no_excluidas
            if PLATAFORMAS_DISPONIBLES[nombre].upper() in preferidos
        ]
        if intersec:
            return intersec

    return no_excluidas
