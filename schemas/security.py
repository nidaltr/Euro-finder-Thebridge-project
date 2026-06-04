"""Utilidades basicas de seguridad para entradas de usuario."""

from __future__ import annotations


MAX_QUERY_LENGTH = 200


def sanear_query(texto: str) -> str:
    """Limpia una busqueda libre antes de enviarla al grafo o al LLM."""
    if not texto:
        return ""
    texto = texto[:MAX_QUERY_LENGTH]
    texto = "".join(c for c in texto if c.isprintable())
    texto = " ".join(texto.split())
    return texto.strip()
