"""Prueba del agente extractor sobre queries diversas (ramas profundas + estandar)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Forzar UTF-8 en stdout para que los prints con acentos no revienten en Windows.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from agents.extractor import extraer_filtros


QUERIES = [
    "Rolex Day-Date oro automatico 40mm con papeles",
    "vinilo The Beatles Abbey Road UK 1969 NM",
    "Audi A5 diesel automatico menos de 15000 max 100000 km",
    "chaqueta Prada cuero hombre talla L",
    "iPhone 13 Pro 256GB negro como nuevo menos de 600",
    "sofa de cuero 3 plazas marron",
    "Fender Stratocaster 1996 zurda",
    "bici de montana Trek talla M",
    "algo raro inclasificable",
]


async def main() -> None:
    for i, q in enumerate(QUERIES, 1):
        print(f"=== Query {i}: {q!r} ===")
        f = await extraer_filtros(q)
        print(f.model_dump_json(indent=2, exclude_none=True))
        print()


if __name__ == "__main__":
    asyncio.run(main())
