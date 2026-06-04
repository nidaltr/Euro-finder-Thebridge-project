"""Pruebas del saneado basico de entradas de usuario."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.security import MAX_QUERY_LENGTH, sanear_query


def test_sanear_query_vacia() -> None:
    assert sanear_query("") == ""


def test_sanear_query_colapsa_espacios() -> None:
    assert sanear_query("  rolex    day-date   oro  ") == "rolex day-date oro"


def test_sanear_query_elimina_caracteres_no_imprimibles() -> None:
    assert sanear_query("Audi\x00 A5\n\t diesel") == "Audi A5 diesel"


def test_sanear_query_limita_longitud() -> None:
    assert len(sanear_query("x" * (MAX_QUERY_LENGTH + 50))) == MAX_QUERY_LENGTH
