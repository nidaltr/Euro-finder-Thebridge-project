"""Normalizador: unifica RawListings de todas las plataformas en NormalizedListing.

Sin LLM. Aplica reglas deterministas:
  - Precio numerico (usa el que ya viene del scraper o lo extrae de precio_texto).
  - Fecha (parseo flexible).
  - Idioma segun la plataforma de origen.
  - categoria_detectada: mapeo de slugs de URL por plataforma.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from schemas.models import Categoria, NormalizedListing, RawListing


logger = logging.getLogger(__name__)


# Idioma por defecto segun plataforma. El scraper ya lo rellena en RawListing.idioma,
# pero esto sirve de fallback si llega vacio.
IDIOMA_POR_PLATAFORMA: dict[str, str] = {
    "leboncoin": "fr",
    "willhaben": "de",
    "subito": "it",
}


# Slugs en la URL del anuncio -> nuestra Categoria (taxonomia nueva, 9 claves).
# Mapeo conservador; lo no listado cae a "otros".
LEBONCOIN_CATEGORIA_POR_SLUG: dict[str, Categoria] = {
    "voitures": "vehiculos",
    "utilitaires": "vehiculos",
    "motos": "vehiculos",
    "caravaning": "vehiculos",
    "camions": "vehiculos",
    "telephonie": "electronica",
    "informatique": "electronica",
    "image_son": "electronica",
    "consoles_jeux_video": "electronica",
    "vetements": "moda",
    "chaussures": "moda",
    "montres_bijoux": "moda",
    "sacs_bagages": "moda",
    "ameublement": "hogar_jardin",
    "electromenager": "hogar_jardin",
    "decoration": "hogar_jardin",
    "arts_de_la_table": "hogar_jardin",
    "linge_de_maison": "hogar_jardin",
    "bricolage": "hogar_jardin",
    "jardin_plantes": "hogar_jardin",
    "sport_plein_air": "deporte_ocio",
    "velos": "deporte_ocio",
    "instruments_musique": "instrumentos",
    "cd_musique": "coleccionismo_arte",
    "livres": "coleccionismo_arte",
    "collection": "coleccionismo_arte",
    "equipement_bebe": "ninos_bebes",
    "vetements_bebe": "ninos_bebes",
    "jeux_jouets": "ninos_bebes",
}


CATEGORIA_POR_PLATAFORMA: dict[str, dict[str, Categoria]] = {
    "leboncoin": LEBONCOIN_CATEGORIA_POR_SLUG,
}


_PRECIO_RE = re.compile(r"(\d[\d\s.,]*)")


def _parse_precio(texto: Optional[str]) -> Optional[float]:
    """Extrae un precio numerico de un string como '12 500 EUR' o '1.299,00 €'."""
    if not texto:
        return None
    m = _PRECIO_RE.search(texto)
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(" ", "")
    # Heuristica: si hay '.' y ',', el ultimo separador es el decimal.
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        # ',' como decimal solo si quedan 1-2 digitos despues
        if len(raw.rsplit(",", 1)[1]) <= 2:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "." in raw:
        if len(raw.rsplit(".", 1)[1]) > 2:
            raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_fecha(valor) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if not isinstance(valor, str):
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def _detectar_categoria(plataforma: str, url: str) -> Categoria:
    mapa = CATEGORIA_POR_PLATAFORMA.get(plataforma)
    if not mapa or not url:
        return "otros"
    for slug, cat in mapa.items():
        if f"/{slug}/" in url or f"/{slug}?" in url or url.endswith(f"/{slug}"):
            return cat
    return "otros"


def _precio_extra(raw: RawListing) -> Optional[float]:
    """Devuelve precio_eur si el scraper lo dejo via extra='allow'."""
    extras = getattr(raw, "__pydantic_extra__", {}) or {}
    valor = extras.get("precio_eur")
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _normalizar_uno(raw: RawListing) -> Optional[NormalizedListing]:
    precio = _precio_extra(raw) or _parse_precio(raw.precio_texto)
    if precio is None or not raw.titulo or not raw.url:
        return None

    idioma = raw.idioma or IDIOMA_POR_PLATAFORMA.get(raw.plataforma)
    moneda = raw.moneda or "EUR"

    ad_id = (
        f"{raw.plataforma}:{raw.id_externo}" if raw.id_externo
        else f"{raw.plataforma}:{raw.url}"
    )

    return NormalizedListing(
        id=ad_id,
        plataforma=raw.plataforma,
        pais=raw.pais,
        titulo=raw.titulo,
        descripcion=raw.descripcion or None,
        idioma=idioma,
        precio_eur=precio,
        moneda_original=moneda,
        precio_original=precio,  # MVP: aun no convertimos divisas
        ubicacion=raw.ubicacion,
        url=raw.url,
        thumbnail_url=raw.thumbnail_url,
        fecha_publicacion=_parse_fecha(raw.fecha_texto),
        categoria_detectada=_detectar_categoria(raw.plataforma, raw.url),
        posicion_plataforma=raw.posicion_plataforma,
    )


def normalizar(
    crudos_por_plataforma: dict[str, list[RawListing]],
) -> list[NormalizedListing]:
    """Convierte el dict de crudos por plataforma en una lista normalizada."""
    salida: list[NormalizedListing] = []
    for plataforma, crudos in crudos_por_plataforma.items():
        descartados = 0
        for raw in crudos:
            norm = _normalizar_uno(raw)
            if norm is None:
                descartados += 1
                continue
            salida.append(norm)
        if descartados:
            logger.info(
                "[normalizer] %s: %d descartados (sin precio/titulo/url)",
                plataforma, descartados,
            )
    return salida
