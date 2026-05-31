"""Diagnostico minimo para confirmar que Eurofinder sube trazas a LangSmith."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from observability import (  # noqa: E402
    configure_langsmith,
    get_langsmith_project,
    langsmith_tracing,
    wait_for_langsmith_traces,
)


def main() -> None:
    configure_langsmith(ROOT_DIR / ".env")

    from langsmith import Client, traceable

    @traceable(name="eurofinder_diagnostic_trace")
    def diagnostic(value: str) -> dict:
        return {"ok": True, "value": value}

    project = get_langsmith_project()
    with langsmith_tracing():
        result = diagnostic("langsmith-ok")

    wait_for_langsmith_traces()

    client = Client()
    runs = list(client.list_runs(project_name=project, limit=5))

    print(f"OK: traza enviada a LangSmith en el proyecto '{project}'.")
    print(f"Resultado local: {result}")
    print("Ultimos runs visibles:")
    for run in runs:
        print(f"- {run.name} | {run.id}")


if __name__ == "__main__":
    main()
