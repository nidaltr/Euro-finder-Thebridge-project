"""Scraper de Subito (IT) - Tier 1, via API JSON interna.

Subito sirve la pagina de busqueda con DataDome (403 en httpx). Sin embargo el
mismo frontend consume `https://hades.subito.it/v1/search/items`, que devuelve
JSON limpio y no esta protegido si mandamos un Referer creible. Vamos directos
a ese endpoint y nos saltamos selectolax.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from schemas.models import RawListing, SearchFilters
from scrapers.base import BasePlatformScraper


logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Origin": "https://www.subito.it",
    "Referer": "https://www.subito.it/",
}


class SubitoScraper(BasePlatformScraper):
    nombre_plataforma = "subito"
    pais = "IT"
    idioma = "it"

    API = "https://hades.subito.it/v1/search/items"

    # tipo_producto -> codigo de categoria de Subito (param c=).
    # Acota la busqueda a la categoria correspondiente; sin esto, "BMW M5"
    # devuelve tambien Accessori Auto, miniaturas, etc.
    CATEGORIA_SUB: dict[str, str] = {
        "coche": "2",                      # Auto
        "moto": "3",                       # Moto e Scooter (a confirmar)
        "furgoneta": "4",                  # Veicoli commerciali (aprox)
        "caravana_autocaravana": "9",      # Caravan e camper (aprox)
        "embarcacion_moto_agua": "10",     # Nautica (aprox)
        "recambios": "5",                  # Accessori Auto
        "accesorios_vehiculos": "5",
        # Rama profunda: reloj
        "reloj": "16",                     # Abbigliamento e Accessori (relojeria incluida)
        # Rama profunda: vinilo
        "vinilo": "19",                    # Musica e Film
        "cd_casete": "19",
    }

    def build_url(self, filtros: SearchFilters) -> str:
        params: dict[str, str] = {
            "q": filtros.query_texto,
            "lim": "30",
            "start": "0",
            "qso": "true",
            "t": "s",
            "sort": "datedesc",
        }
        cat = self.CATEGORIA_SUB.get(filtros.tipo_producto or "")
        if cat:
            params["c"] = cat
        # Filtro de precio en la API de Subito: ps (price start) y pe (price end).
        if filtros.precio_min is not None:
            params["ps"] = str(int(filtros.precio_min))
        if filtros.precio_max is not None:
            params["pe"] = str(int(filtros.precio_max))
        return f"{self.API}?{urlencode(params)}"

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=30.0
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    def parse(self, html: str) -> list[RawListing]:
        import json as _json

        try:
            data = _json.loads(html)
        except _json.JSONDecodeError as e:
            logger.warning("[subito] JSON invalido: %s", e)
            return []

        ads: list[dict[str, Any]] = data.get("ads") or []
        crudos: list[RawListing] = []
        for ad in ads:
            try:
                crudos.append(self._a_raw(ad))
            except Exception as e:
                logger.warning("[subito] anuncio malformado: %s", e)
        return crudos

    def _a_raw(self, ad: dict[str, Any]) -> RawListing:
        urls = ad.get("urls") or {}
        url = urls.get("default") or urls.get("mobile") or ""

        # ID extraido de la urn: "id:ad:UUID:list:NNNN"
        urn = ad.get("urn") or ""
        id_externo = urn.rsplit(":", 1)[-1] if urn else None

        # Precio: features con uri == "/price"
        precio_num: float | None = None
        precio_texto: str | None = None
        for f in ad.get("features") or []:
            if f.get("uri") == "/price":
                vals = f.get("values") or []
                if vals:
                    key = vals[0].get("key")
                    val = vals[0].get("value")
                    if key is not None:
                        try:
                            precio_num = float(str(key).replace(",", "."))
                        except (TypeError, ValueError):
                            pass
                    precio_texto = val or (f"{key} EUR" if key else None)
                break

        # Ubicacion: geo.town / geo.city
        geo = ad.get("geo") or {}
        town = (geo.get("town") or {}).get("value")
        city = (geo.get("city") or {}).get("value")
        ubicacion = ", ".join(x for x in (town, city) if x) or None

        # Thumbnail
        images = ad.get("images") or []
        thumb = None
        if images:
            base = images[0].get("cdn_base_url") or images[0].get("base_url")
            if base:
                thumb = base if base.startswith("http") else f"https:{base}"

        # Fecha
        dates = ad.get("dates") or {}
        fecha_texto = dates.get("display_iso8601") or dates.get("display")

        return RawListing(
            plataforma=self.nombre_plataforma,
            pais=self.pais,
            url=url,
            id_externo=str(id_externo) if id_externo else None,
            titulo=ad.get("subject"),
            descripcion=ad.get("body"),
            precio_texto=precio_texto,
            moneda="EUR",
            ubicacion=ubicacion,
            thumbnail_url=thumb,
            fecha_texto=fecha_texto,
            idioma=self.idioma,
            precio_eur=precio_num,
        )
