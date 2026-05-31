"""Punto de entrada CLI: lanza el grafo Eurofinder con una query."""

from __future__ import annotations

import asyncio
import logging
import sys

from observability import (
    configure_langsmith,
    langsmith_run_config,
    langsmith_tracing,
    wait_for_langsmith_traces,
)

configure_langsmith()

from graph.workflow import build_graph


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


async def run(query: str) -> None:
    grafo = build_graph()
    with langsmith_tracing():
        await grafo.ainvoke(
            {"query": query},
            config=langsmith_run_config("cli"),
        )


def main() -> None:
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Query: ").strip()
    if not query:
        print("Query vacia, saliendo.")
        return
    try:
        asyncio.run(run(query))
    finally:
        wait_for_langsmith_traces()


if __name__ == "__main__":
    main()
