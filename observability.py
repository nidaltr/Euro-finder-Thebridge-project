"""Configuracion compartida de LangSmith para Eurofinder.

Debe ejecutarse antes de importar LangChain/LangGraph para que los callbacks de
tracing lean las variables correctas desde el arranque.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT = "eurofinder"

_TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUE_VALUES


def configure_langsmith(env_path: Path | None = None, *, override: bool = True) -> None:
    """Carga `.env` y normaliza variables LangSmith/LangChain."""

    load_dotenv(env_path or PROJECT_ROOT / ".env", override=override)

    tracing_enabled = _is_truthy(
        os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")
    )
    if not tracing_enabled:
        return

    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT")
    project = (
        os.getenv("LANGSMITH_PROJECT")
        or os.getenv("LANGCHAIN_PROJECT")
        or DEFAULT_PROJECT
    )

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

    if api_key:
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if endpoint:
        endpoint = endpoint.rstrip("/")
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    if project:
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGCHAIN_PROJECT"] = project

    # En ejecuciones cortas de CLI/tests evita que el proceso termine antes de
    # que el tracer suba los spans. Se puede sobreescribir desde el entorno.
    os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")


def is_langsmith_enabled() -> bool:
    return _is_truthy(os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2"))


def get_langsmith_project() -> str:
    return os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or DEFAULT_PROJECT


@contextmanager
def langsmith_tracing() -> Iterator[None]:
    """Contexto explicito para agrupar runs en el proyecto configurado."""

    if not is_langsmith_enabled():
        yield
        return

    try:
        from langsmith import tracing_context
    except Exception as exc:  # pragma: no cover - solo defensivo en entornos rotos.
        logger.debug("No se pudo activar tracing_context de LangSmith: %s", exc)
        yield
        return

    with tracing_context(enabled=True, project_name=get_langsmith_project()):
        yield


def langsmith_run_config(entrypoint: str) -> dict:
    """Config comun para que la traza raiz sea facil de encontrar en la UI."""

    return {
        "run_name": "eurofinder_search",
        "tags": ["eurofinder", entrypoint],
        "metadata": {"entrypoint": entrypoint},
    }


def wait_for_langsmith_traces() -> None:
    """Bloquea hasta que los callbacks pendientes se hayan enviado."""

    if not is_langsmith_enabled():
        return
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
    except Exception as exc:  # pragma: no cover - no debe romper la busqueda.
        logger.debug("No se pudieron esperar los tracers de LangSmith: %s", exc)
