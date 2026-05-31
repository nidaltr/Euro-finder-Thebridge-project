"""Scraper de Willhaben (AT) - Tier 1.

Willhaben sirve una pagina Next.js cuyos resultados estan en el script
`<script id="__NEXT_DATA__">` como JSON, igual que Leboncoin. Los anuncios
viven en `props.pageProps.searchResult.advertSummaryList.advertSummary`.
Cada anuncio expone sus campos como una lista de `{name, values}` bajo
`attributes.attribute`.
"""

from __future__ import annotations

import json
import logging
import re
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
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)

BASE_URL = "https://www.willhaben.at"


class WillhabenScraper(BasePlatformScraper):
    nombre_plataforma = "willhaben"
    pais = "AT"
    idioma = "de"

    SEARCH_URL = f"{BASE_URL}/iad/kaufen-und-verkaufen/marktplatz"

    def build_url(self, filtros: SearchFilters) -> str:
        params: dict[str, str] = {"keyword": filtros.query_texto}
        if filtros.precio_min is not None:
            params["PRICE_FROM"] = str(int(filtros.precio_min))
        if filtros.precio_max is not None:
            params["PRICE_TO"] = str(int(filtros.precio_max))
        return f"{self.SEARCH_URL}?{urlencode(params)}"

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=30.0
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    def parse(self, html: str) -> list[RawListing]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            logger.warning("[willhaben] no se encontro __NEXT_DATA__")
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning("[willhaben] JSON invalido en __NEXT_DATA__: %s", e)
            return []

        ads: list = (
            data.get("props", {})
            .get("pageProps", {})
            .get("searchResult", {})
            .get("advertSummaryList", {})
            .get("advertSummary", [])
            or []
        )

        crudos: list[RawListing] = []
        for ad in ads:
            try:
                raw = self._parsear_anuncio(ad)
                if raw is not None:
                    crudos.append(raw)
            except Exception as e:
                logger.warning("[willhaben] anuncio malformado, se ignora: %s", e)
        return crudos

    def _parsear_anuncio(self, ad: dict) -> RawListing | None:
        # Extraer atributos como dict name -> primera value
        attrs: dict[str, str] = {}
        for a in ad.get("attributes", {}).get("attribute", []):
            vals = a.get("values") or []
            if vals:
                attrs[a["name"]] = vals[0]

        titulo = attrs.get("HEADING") or ad.get("description")
        if not titulo:
            return None

        # URL publica del anuncio: SEO_URL ya incluye el slug completo
        seo_url = attrs.get("SEO_URL", "")
        url = f"{BASE_URL}/iad/{seo_url}" if seo_url else None
        if not url:
            ad_id = attrs.get("ADID")
            url = f"{BASE_URL}/iad/object?adId={ad_id}" if ad_id else None
        if not url:
            return None

        # Precio
        precio_str = attrs.get("PRICE/AMOUNT")
        precio_num: float | None = None
        if precio_str:
            try:
                precio_num = float(precio_str)
            except ValueError:
                pass

        # Thumbnail
        imgs = ad.get("advertImageList", {}).get("advertImage", [])
        thumbnail = imgs[0].get("thumbnailImageUrl") if imgs else None

        return RawListing(
            plataforma=self.nombre_plataforma,
            pais=self.pais,
            url=url,
            id_externo=attrs.get("ADID"),
            titulo=titulo,
            descripcion=attrs.get("BODY_DYN"),
            precio_texto=attrs.get("PRICE_FOR_DISPLAY") or (f"{precio_str} EUR" if precio_str else None),
            moneda="EUR",
            ubicacion=attrs.get("LOCATION"),
            thumbnail_url=thumbnail,
            fecha_texto=attrs.get("PUBLISHED_String") or attrs.get("CHANGED_String"),
            idioma=self.idioma,
            precio_eur=precio_num,
        )
