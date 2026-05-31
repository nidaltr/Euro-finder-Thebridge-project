"""Prueba del scraper de Leboncoin con la query 'velo'."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.models import SearchFilters
from scrapers.leboncoin import LeboncoinScraper


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


async def main() -> None:
    filtros = SearchFilters(categoria="otros", query_texto="velo")
    scraper = LeboncoinScraper()
    resultados = await scraper.buscar(filtros)
    print(f"\n=== {len(resultados)} resultados; mostrando los primeros 5 ===\n")
    for i, r in enumerate(resultados[:5], 1):
        print(f"--- Resultado {i} ---")
        print(r.model_dump_json(indent=2))
        print()


if __name__ == "__main__":
    asyncio.run(main())
