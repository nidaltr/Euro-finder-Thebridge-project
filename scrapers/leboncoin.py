"""Scraper de Leboncoin (FR) - Tier 1.

Leboncoin sirve una pagina Next.js cuyos resultados estan en el script
`<script id="__NEXT_DATA__">` como JSON. Lo extraemos y mapeamos directamente,
sin tocar el DOM con selectolax (mas robusto que selectores CSS).
"""

from __future__ import annotations

import json
import logging
import os
import re
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


class LeboncoinScraper(BasePlatformScraper):
    nombre_plataforma = "leboncoin"
    pais = "FR"
    idioma = "fr"
    intento_timeout_s = 18.0

    BASE_URL = "https://www.leboncoin.fr/recherche"

    # tipo_producto canonico -> codigo de categoria de Leboncoin (param ?category=).
    # Acota la busqueda a la seccion correspondiente para no devolver piezas
    # cuando se busca un coche, ni miniaturas, ni alquileres.
    CATEGORIA_LBC: dict[str, str] = {
        "coche": "2",                     # Voitures
        "moto": "3",                      # Motos
        "furgoneta": "5",                 # Utilitaires
        "caravana_autocaravana": "4",     # Caravaning
        "embarcacion_moto_agua": "6",     # Nautisme
        "recambios": "44",                # Equipement auto
        "accesorios_vehiculos": "44",
        # Rama profunda: reloj
        "reloj": "42",                    # Montres & Bijoux
        # Rama profunda: vinilo
        "vinilo": "26",                   # CD - Musique (incluye vinilos)
        "cd_casete": "26",
    }

    CATEGORIA_LBC_API: dict[str, str] = {
        "coche": "VEHICULES_VOITURES",
        "moto": "VEHICULES_MOTOS",
        "furgoneta": "VEHICULES_UTILITAIRES",
        "caravana_autocaravana": "VEHICULES_CARAVANING",
        "embarcacion_moto_agua": "VEHICULES_NAUTISME",
        "recambios": "VEHICULES_EQUIPEMENT_AUTO",
        "accesorios_vehiculos": "VEHICULES_EQUIPEMENT_AUTO",
        "reloj": "MODE_MONTRES_ET_BIJOUX",
        "vinilo": "LOISIRS_CD_MUSIQUE",
        "cd_casete": "LOISIRS_CD_MUSIQUE",
    }

    def build_url(self, filtros: SearchFilters) -> str:
        params: dict[str, str] = {"text": filtros.query_texto}
        cat = self.CATEGORIA_LBC.get(filtros.tipo_producto or "")
        if cat:
            params["category"] = cat
        if filtros.precio_min is not None or filtros.precio_max is not None:
            lo = int(filtros.precio_min) if filtros.precio_min is not None else "min"
            hi = int(filtros.precio_max) if filtros.precio_max is not None else "max"
            params["price"] = f"{lo}-{hi}"
        return f"{self.BASE_URL}?{urlencode(params)}"

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=30.0
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    async def buscar(self, filtros: SearchFilters) -> list[RawListing]:
        """Busca con el cliente API actual y cae al HTML legacy si no pasa.

        Leboncoin bloquea cada vez mas el scraping HTML con Datadome. El paquete
        `lbc` usa el endpoint `finder/search` y curl-cffi para imitar TLS de
        navegador. Si tu IP queda bloqueada, se puede configurar un proxy con
        `LEBONCOIN_PROXY_URL`.
        """

        try:
            crudos = await self._buscar_api_lbc(filtros)
            if crudos:
                return [
                    c.model_copy(update={"posicion_plataforma": i})
                    for i, c in enumerate(crudos, start=1)
                ]
        except Exception as exc:
            logger.warning("[leboncoin] API lbc no disponible: %s", exc)
        return await super().buscar(filtros)

    async def _buscar_api_lbc(self, filtros: SearchFilters) -> list[RawListing]:
        import asyncio
        from urllib.parse import urlparse

        import lbc

        def _proxy_desde_env():
            proxy_url = os.getenv("LEBONCOIN_PROXY_URL", "").strip()
            if not proxy_url:
                return None
            parsed = urlparse(proxy_url)
            if not parsed.hostname or not parsed.port:
                raise ValueError("LEBONCOIN_PROXY_URL debe incluir host y puerto")
            return lbc.Proxy(
                host=parsed.hostname,
                port=parsed.port,
                username=parsed.username,
                password=parsed.password,
                scheme=parsed.scheme or "http",
            )

        def _run() -> list[RawListing]:
            client = lbc.Client(
                proxy=_proxy_desde_env(),
                impersonate=os.getenv("LEBONCOIN_IMPERSONATE", "chrome146"),
                timeout=15.0,
                max_retries=1,
            )
            category_name = self.CATEGORIA_LBC_API.get(filtros.tipo_producto or "")
            category = getattr(lbc.Category, category_name) if category_name else lbc.Category.TOUTES_CATEGORIES
            price = None
            if filtros.precio_min is not None or filtros.precio_max is not None:
                price = [
                    int(filtros.precio_min or 0),
                    int(filtros.precio_max or 999999999),
                ]
            kwargs: dict[str, Any] = {
                "text": filtros.query_texto,
                "category": category,
                "limit": 35,
            }
            if price is not None:
                kwargs["price"] = price
            result = client.search(**kwargs)
            return [self._ad_api_a_raw(ad) for ad in result.ads]

        return await asyncio.to_thread(_run)

    def _ad_api_a_raw(self, ad: Any) -> RawListing:
        images = getattr(ad, "images", None) or []
        location = getattr(ad, "location", None)
        ubicacion = getattr(location, "city_label", None) if location else None
        precio = getattr(ad, "price", None)
        precio_texto = f"{int(precio)} EUR" if isinstance(precio, (int, float)) else None
        return RawListing(
            plataforma=self.nombre_plataforma,
            pais=self.pais,
            url=str(getattr(ad, "url", "") or ""),
            id_externo=str(getattr(ad, "id", "") or "") or None,
            titulo=getattr(ad, "subject", None),
            descripcion=getattr(ad, "body", None),
            precio_texto=precio_texto,
            moneda="EUR",
            ubicacion=ubicacion,
            thumbnail_url=images[0] if images else None,
            fecha_texto=getattr(ad, "first_publication_date", None),
            idioma=self.idioma,
            precio_eur=float(precio) if isinstance(precio, (int, float)) else None,
        )

    def parse(self, html: str) -> list[RawListing]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            logger.warning("[leboncoin] no se encontro __NEXT_DATA__")
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning("[leboncoin] JSON invalido en __NEXT_DATA__: %s", e)
            return []

        ads: list[dict[str, Any]] = (
            data.get("props", {})
            .get("pageProps", {})
            .get("searchData", {})
            .get("ads", [])
            or []
        )

        crudos: list[RawListing] = []
        for ad in ads:
            try:
                images = ad.get("images") or {}
                location = ad.get("location") or {}
                price_list = ad.get("price") or []
                precio_num = float(price_list[0]) if price_list else None
                precio_texto = f"{int(price_list[0])} EUR" if price_list else None
                crudos.append(
                    RawListing(
                        plataforma=self.nombre_plataforma,
                        pais=self.pais,
                        url=str(ad.get("url") or ""),
                        id_externo=str(ad.get("list_id") or "") or None,
                        titulo=ad.get("subject"),
                        descripcion=ad.get("body"),
                        precio_texto=precio_texto,
                        moneda="EUR",
                        ubicacion=location.get("city_label"),
                        thumbnail_url=images.get("thumb_url"),
                        fecha_texto=ad.get("first_publication_date"),
                        idioma=self.idioma,
                        # extra='allow' permite que el normalizador use precio_eur
                        # directamente sin re-parsear precio_texto.
                        precio_eur=precio_num,
                    )
                )
            except Exception as e:
                logger.warning("[leboncoin] anuncio malformado, se ignora: %s", e)
                continue
        return crudos
