"""Traductor: traduce titulo y descripcion al espanol en una unica llamada (Haiku)."""

from __future__ import annotations

import json
import logging

from observability import configure_langsmith

configure_langsmith()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from schemas.models import NormalizedListing


logger = logging.getLogger(__name__)


MODELO = "claude-haiku-4-5-20251001"

# Limite blando para no inflar el prompt con descripciones muy largas. La UI
# trunca a 300 chars al pintar, mandar mas al LLM es desperdicio.
MAX_DESCRIPCION = 300

# Solo traducimos los primeros N resultados (suficiente para la pantalla
# tipica). El resto queda con titulo_es=None y la UI cae a r.titulo.
MAX_ITEMS_TRADUCIR = 30


# Cache en memoria a nivel de modulo. Clave = (id_anuncio, hash(titulo)).
# Sobrevive entre busquedas dentro del mismo proceso de Streamlit.
_CACHE_TRADUCCIONES: dict[tuple[str, int], "ItemTraducido"] = {}


def _clave_cache(anuncio_id: str, titulo: str) -> tuple[str, int]:
    return (anuncio_id, hash(titulo))


SYSTEM_PROMPT = """Eres un traductor profesional. Recibes una lista de anuncios \
de productos de segunda mano en distintos idiomas europeos y los traduces al \
espanol. Devuelves SOLO un objeto JSON valido conforme al esquema indicado.

Reglas:
- Traduce `titulo` -> `titulo_es`. Manten nombres de marca, modelo, ciudades y \
unidades (cv, km, GB, ...) en su forma original o equivalente en espanol natural.
- Traduce `descripcion` -> `descripcion_es` si esta presente; si no, deja \
`descripcion_es` en null.
- Conserva exactamente el campo `id` de cada anuncio: lo necesitamos para mapear.
- No inventes informacion. No anadas comentarios.
- El idioma destino siempre es espanol (es-ES)."""


class ItemTraducido(BaseModel):
    id: str
    titulo_es: str
    descripcion_es: str | None = None


class Traducciones(BaseModel):
    items: list[ItemTraducido] = Field(default_factory=list)


def _llm() -> ChatAnthropic:
    return ChatAnthropic(model=MODELO)


def _items_a_traducir(resultados: list[NormalizedListing]) -> list[dict]:
    """Selecciona y prepara los anuncios cuyo idioma no es espanol.

    Salta los que ya estan en cache. Limita a MAX_ITEMS_TRADUCIR para evitar
    payloads enormes (con 90 anuncios el traductor LLM tarda 15-20s).
    """
    items = []
    for r in resultados:
        if (r.idioma or "").lower().startswith("es"):
            continue
        if not r.titulo:
            continue
        if _clave_cache(r.id, r.titulo) in _CACHE_TRADUCCIONES:
            continue
        desc = (r.descripcion or "").strip()
        if len(desc) > MAX_DESCRIPCION:
            desc = desc[:MAX_DESCRIPCION]
        items.append(
            {
                "id": r.id,
                "idioma": r.idioma,
                "titulo": r.titulo,
                "descripcion": desc or None,
            }
        )
        if len(items) >= MAX_ITEMS_TRADUCIR:
            break
    return items


async def traducir(resultados: list[NormalizedListing]) -> list[NormalizedListing]:
    """Rellena titulo_es/descripcion_es para los anuncios que no estan en espanol.

    Una sola llamada al LLM con todos los anuncios en lote (top-N, ya filtrados
    por cache). Si algo falla, los devuelve sin traducir y registra el error
    (no rompe el pipeline).
    """
    items = _items_a_traducir(resultados)

    por_id: dict[str, ItemTraducido] = {}

    if items:
        payload = json.dumps(items, ensure_ascii=False)
        llm = _llm().with_structured_output(Traducciones)
        mensajes = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Anuncios a traducir:\n{payload}"),
        ]
        try:
            resp: Traducciones = await llm.ainvoke(mensajes)  # type: ignore[assignment]
            por_id = {it.id: it for it in resp.items}
        except Exception as exc:
            logger.warning("[traductor] fallo, se devuelven sin traducir: %s", exc)
            return resultados
        # Sembrar el cache con lo recien traducido.
        id_a_titulo = {it["id"]: it["titulo"] for it in items}
        for it in resp.items:
            titulo_original = id_a_titulo.get(it.id)
            if titulo_original is not None:
                _CACHE_TRADUCCIONES[_clave_cache(it.id, titulo_original)] = it

    actualizados: list[NormalizedListing] = []
    hits_cache = 0
    for r in resultados:
        # 1) Resultado fresco del LLM.
        it = por_id.get(r.id)
        # 2) O bien hit en cache (de busquedas anteriores).
        if it is None and r.titulo:
            it = _CACHE_TRADUCCIONES.get(_clave_cache(r.id, r.titulo))
            if it is not None:
                hits_cache += 1
        if it is None:
            actualizados.append(r)
            continue
        actualizados.append(
            r.model_copy(
                update={
                    "titulo_es": it.titulo_es,
                    "descripcion_es": it.descripcion_es,
                }
            )
        )
    logger.info(
        "[traductor] llm=%d cache=%d (total resultados=%d)",
        len(por_id), hits_cache, len(resultados),
    )
    return actualizados
