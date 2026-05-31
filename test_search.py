import asyncio

from observability import (
    configure_langsmith,
    langsmith_run_config,
    langsmith_tracing,
    wait_for_langsmith_traces,
)

configure_langsmith()

from graph.workflow import build_graph


async def test_search():
    grafo = build_graph()
    with langsmith_tracing():
        resultado = await grafo.ainvoke(
            {"query": "Rolex Day-Date oro automatico"},
            config=langsmith_run_config("test_search"),
        )
    print(f"Busqueda completada. {len(resultado.get('resultados', []))} resultados encontrados.")


try:
    asyncio.run(test_search())
finally:
    wait_for_langsmith_traces()
