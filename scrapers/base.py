"""Clase base abstracta para todos los scrapers de plataformas."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from schemas.models import RawListing, SearchFilters
from scrapers._traducciones import traducir_termino


logger = logging.getLogger(__name__)


# Presupuesto duro por intento HTTP (fetch + parse). Cuando vence, el intento
# se descarta y devolvemos [] o pasamos al reintento relajado. Evita que un
# scraper lento envenene el timeout global del nodo_scraping.
INTENTO_TIMEOUT_S = 6.0


class BasePlatformScraper(ABC):
    """Contrato comun de todos los scrapers de plataforma.

    Las subclases declaran su identidad (nombre, pais, idioma) e implementan
    build_url / fetch / parse. El metodo publico `buscar` encadena los tres y
    absorbe cualquier excepcion devolviendo lista vacia, para que un fallo en
    una plataforma no tumbe al resto del pipeline.

    La normalizacion al esquema comun NO la hace el scraper: se hace despues,
    en agents/normalizer.py, sobre los RawListing de todas las plataformas.
    """

    nombre_plataforma: str = ""
    pais: str = ""
    idioma: str = ""
    intento_timeout_s: float = INTENTO_TIMEOUT_S

    @abstractmethod
    def build_url(self, filtros: SearchFilters) -> str:
        """Construye la URL de busqueda a partir de los filtros."""

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Descarga el HTML (o JSON crudo) de la URL."""

    @abstractmethod
    def parse(self, html: str) -> list[RawListing]:
        """Parsea la respuesta cruda y devuelve una lista de RawListing."""

    async def buscar(self, filtros: SearchFilters) -> list[RawListing]:
        """Ejecuta build_url -> fetch -> parse y maneja errores devolviendo [].

        Si el primer intento devuelve 0 crudos, intenta un reintento con la
        query relajada antes de rendirse. Preferimos `marca + modelo` (si
        estan disponibles) por encima de heuristicas de tokens, porque el
        extractor ya nos da la informacion canonica internacional.
        """
        try:
            crudos = await self._buscar_una_vez(filtros)
        except asyncio.TimeoutError:
            logger.warning(
                "[%s] intento principal expiro tras %.1fs",
                self.nombre_plataforma, self.intento_timeout_s,
            )
            crudos = []
        except Exception as exc:
            logger.exception(
                "[%s] fallo durante buscar: %s", self.nombre_plataforma, exc
            )
            return []
        if crudos:
            return crudos

        query_relajada = self._query_relajada(filtros)
        if query_relajada is None or query_relajada == filtros.query_texto:
            return crudos

        filtros_relajados = filtros.model_copy(
            update={"query_texto": query_relajada}
        )
        logger.info(
            "[%s] 0 resultados, reintentando con %r",
            self.nombre_plataforma, query_relajada,
        )
        try:
            return await self._buscar_una_vez(filtros_relajados)
        except asyncio.TimeoutError:
            logger.warning(
                "[%s] reintento relajado expiro tras %.1fs",
                self.nombre_plataforma, self.intento_timeout_s,
            )
            return []
        except Exception as exc:
            logger.exception(
                "[%s] fallo en reintento relajado: %s",
                self.nombre_plataforma, exc,
            )
            return []

    def _query_relajada(self, filtros: SearchFilters) -> str | None:
        """Elige una query mas permisiva. None si no hay forma de relajar."""
        if filtros.marca:
            if filtros.modelo:
                return f"{filtros.marca} {filtros.modelo}".strip()
            return filtros.marca
        tokens = filtros.query_texto.split()
        if len(tokens) > 2:
            return " ".join(tokens[:-1])
        return None

    async def _buscar_una_vez(self, filtros: SearchFilters) -> list[RawListing]:
        filtros_enriquecidos = self._enriquecer_query(filtros)
        url = self.build_url(filtros_enriquecidos)
        logger.info("[%s] URL: %s", self.nombre_plataforma, url)
        html = await asyncio.wait_for(self.fetch(url), timeout=self.intento_timeout_s)
        crudos = self.parse(html)
        # Asigna posicion 1..N en el orden en que la plataforma sirvio los
        # anuncios. Permite ordenar por relevancia nativa mas adelante.
        crudos = [
            c.model_copy(update={"posicion_plataforma": i})
            for i, c in enumerate(crudos, start=1)
        ]
        logger.info("[%s] %d anuncios crudos", self.nombre_plataforma, len(crudos))
        return crudos

    def _enriquecer_query(self, filtros: SearchFilters) -> SearchFilters:
        """Anade al texto de busqueda la traduccion local de tipo_prenda /
        subcategoria si existe. Asi cada plataforma filtra desde el origen."""
        if not self.idioma:
            return filtros
        extras = []
        for campo in ("tipo_prenda", "subcategoria"):
            valor = getattr(filtros, campo, None)
            traducido = traducir_termino(valor, self.idioma)
            if traducido:
                extras.append(traducido)
        if not extras:
            return filtros
        nueva = filtros.query_texto
        # Evita duplicar si ya esta presente.
        baja = nueva.lower()
        for e in extras:
            if e.lower() not in baja:
                nueva = (nueva + " " + e).strip()
        return filtros.model_copy(update={"query_texto": nueva})
