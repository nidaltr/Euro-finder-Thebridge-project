"""Smoke test de los modelos Pydantic + taxonomia."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.models import NormalizedListing, RawListing, SearchFilters
from schemas.taxonomia import (
    CLAVES_CATEGORIA,
    FILTROS_UNIVERSALES,
    buscar_tipo,
    iter_tipos,
)


def main() -> None:
    # Taxonomia
    tipos = list(iter_tipos())
    print(f"Total tipos en taxonomia: {len(tipos)}")
    profundas = [t.clave for _, _, t in tipos if t.rama_profunda]
    print(f"Ramas profundas: {profundas}")
    print(f"Claves de categoria: {CLAVES_CATEGORIA}")
    print(f"Filtros universales: {[f.nombre for f in FILTROS_UNIVERSALES]}")
    print()

    # Construir un SearchFilters con campos de rama profunda
    f = SearchFilters(
        categoria="moda",
        grupo="accesorios",
        tipo_producto="reloj",
        query_texto="Rolex Day-Date",
        marca="Rolex",
        modelo="Day-Date",
        movimiento="automatico",
        material_caja="oro",
        diametro_mm=40,
        con_caja_y_papeles="si",
        anio=2018,
    )
    print("=== SearchFilters (Reloj rama profunda) ===")
    print(f.model_dump_json(indent=2, exclude_none=True))
    print()

    # Construir uno de coche
    coche = SearchFilters(
        categoria="vehiculos",
        grupo="vehiculos",
        tipo_producto="coche",
        query_texto="Audi A5",
        marca="Audi",
        modelo="A5",
        anio_min=2018,
        anio_max=2020,
        km_max=100000,
        combustible="diesel",
        cambio="automatico",
        precio_max=15000,
    )
    print("=== SearchFilters (Coche rama profunda) ===")
    print(coche.model_dump_json(indent=2, exclude_none=True))
    print()

    # Y un vinilo
    vinilo = SearchFilters(
        categoria="coleccionismo_arte",
        grupo="musica_fisica",
        tipo_producto="vinilo",
        query_texto="The Beatles Abbey Road",
        artista="The Beatles",
        album="Abbey Road",
        anio=1969,
        pais_prensado="UK",
        estado_disco="NM",
    )
    print("=== SearchFilters (Vinilo rama profunda) ===")
    print(vinilo.model_dump_json(indent=2, exclude_none=True))
    print()

    # Comprobar lookup
    encontrado = buscar_tipo("reloj")
    assert encontrado is not None
    cat, gru, tipo = encontrado
    print(f"buscar_tipo('reloj') -> {cat.clave}/{gru.clave}/{tipo.clave} "
          f"({len(tipo.filtros)} filtros)")

    # Sanity de RawListing y NormalizedListing
    crudo = RawListing(
        plataforma="leboncoin", pais="FR",
        url="https://www.leboncoin.fr/ad/voitures/123",
        id_externo="123", titulo="Audi A5 2018",
        precio_texto="14000 EUR", moneda="EUR",
    )
    print("\n=== RawListing ===")
    print(crudo.model_dump_json(indent=2, exclude_none=True))

    norm = NormalizedListing(
        id="leboncoin:123", plataforma="leboncoin", pais="FR",
        titulo="Audi A5 2018", precio_eur=14000.0, url=crudo.url,
        categoria_detectada="vehiculos",
    )
    print("\n=== NormalizedListing ===")
    print(norm.model_dump_json(indent=2, exclude_none=True))


if __name__ == "__main__":
    main()
