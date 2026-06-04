"""Agente extractor: convierte una query en lenguaje natural en SearchFilters.

El system prompt se compone en tiempo de carga a partir de la taxonomia
(`schemas/taxonomia.py`). Tras la llamada al LLM se aplica `sanear_filtros`
para descartar campos especificos que no apliquen al tipo elegido.
"""

from __future__ import annotations

from observability import configure_langsmith

configure_langsmith()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas.models import SearchFilters
from schemas.security import sanear_query
from schemas.taxonomia import (
    FILTROS_UNIVERSALES,
    buscar_tipo,
    formato_para_prompt,
    todos_los_campos_especificos,
)


MODELO = "claude-haiku-4-5-20251001"


CABECERA_PROMPT = """Eres un extractor de filtros estructurados para un \
buscador de productos de segunda mano en plataformas europeas (Francia, \
Alemania, Italia). Recibes la peticion del usuario en lenguaje natural \
(normalmente en espanol) y devuelves un objeto SearchFilters.

## Que tienes que hacer

1. Situa la busqueda en el arbol: elige `categoria` (siempre obligatoria), y \
si puedes deducirlos, `grupo` y `tipo_producto`. Si la consulta es ambigua, \
deja `tipo_producto` (y `grupo`) en null y usa `categoria="otros"` solo como \
ultimo recurso.
2. Rellena los filtros UNIVERSALES que aparezcan en la consulta: `precio_min`, \
`precio_max`, `paises_preferidos`/`paises_excluidos` (codigos ISO 2 letras), \
`estado`.
3. Rellena los filtros ESPECIFICOS del tipo elegido. NO rellenes campos de un \
tipo distinto, aunque el schema te lo permita. Si dudas, deja en null.
4. Genera `query_texto`: cadena corta y limpia, palabras clave universales \
(idealmente nombres de marca/modelo internacionales) para inyectar en el \
buscador de las plataformas. **NO incluyas la palabra generica de la categoria \
en espanol** ("coche", "movil", "telefono", "bolso", "zapatos", "ordenador", \
"television", "bicicleta", "chaqueta", "vestido", "reloj"...). Esas palabras \
no aparecen en titulos de plataformas francesas/alemanas/italianas.
5. En `notas_libres` mete cualquier restriccion cualitativa relevante que no \
tenga campo dedicado.

## Reglas duras

- `marca` y `modelo`: forma estandar internacional. "Hermes" (no "Ermes"), \
"Volkswagen" o "VW", "Day-Date" (no "Daydate").
- `paises_*`: ISO 2 letras mayusculas (FR, DE, IT, ES, ...).
- Precios: numeros en euros, sin simbolo.
- Para filtros tipo `lista` usa SIEMPRE los valores cerrados indicados; nunca \
inventes uno nuevo.
- Cuando una rama esta marcada (RAMA PROFUNDA), extra detalle si esta en la \
query: relojes (movimiento, material_caja, diametro, papeles), vinilos \
(artista, album, sello, ano, pais_prensado, formato, tamano, estados Goldmine \
del disco/portada), coches (todos los campos disponibles).
"""


EJEMPLOS_PROMPT = """## Ejemplos

Query: "Rolex Day-Date oro automatico 40mm con papeles"
-> categoria=moda, grupo=accesorios, tipo_producto=reloj, marca=Rolex, \
modelo=Day-Date, movimiento=automatico, material_caja=oro, diametro_mm=40, \
con_caja_y_papeles=si, query_texto="Rolex Day-Date"

Query: "vinilo The Beatles Abbey Road UK 1969 NM"
-> categoria=coleccionismo_arte, grupo=musica_fisica, tipo_producto=vinilo, \
artista="The Beatles", album="Abbey Road", anio=1969, pais_prensado=UK, \
estado_disco=NM, query_texto="The Beatles Abbey Road"

Query: "Audi A5 diesel automatico menos de 15000 max 100000 km"
-> categoria=vehiculos, grupo=vehiculos, tipo_producto=coche, marca=Audi, \
modelo=A5, combustible=diesel, cambio=automatico, precio_max=15000, \
km_max=100000, query_texto="Audi A5"

Query: "chaqueta Prada cuero hombre talla L"
-> categoria=moda, grupo=moda_hombre, tipo_producto=abrigos_chaquetas_hombre, \
marca=Prada, material=cuero, talla=L, query_texto="Prada"

Query: "iPhone 13 Pro 256GB negro como nuevo menos de 600 euros"
-> categoria=electronica, grupo=informatica_telefonia, tipo_producto=movil, \
marca=Apple, modelo="iPhone 13 Pro", capacidad="256GB", color=negro, \
estado=como_nuevo, precio_max=600, query_texto="iPhone 13 Pro"

Query: "sofa de cuero 3 plazas marron"
-> categoria=hogar_jardin, grupo=mobiliario, tipo_producto=sofa, \
material=cuero, color=marron, plazas_o_dimensiones="3 plazas", \
query_texto="sofa cuero"

Query: "Fender Stratocaster 1996 zurda"
-> categoria=instrumentos, grupo=cuerda, tipo_producto=guitarra_electrica, \
marca=Fender, modelo=Stratocaster, anio=1996, zurdo_diestro=zurdo, \
query_texto="Fender Stratocaster"

Query: "bici de montana Trek talla M"
-> categoria=deporte_ocio, grupo=ciclismo, tipo_producto=bicicleta, \
tipo_bici=montana, marca=Trek, talla_cuadro=M, query_texto="Trek mountain bike"

Query: "algo raro inclasificable"
-> categoria=otros, query_texto=<lo que sea util de la query>
"""


def _construir_system_prompt() -> str:
    """Compone el system prompt completo a partir de la taxonomia."""
    return "\n\n".join((CABECERA_PROMPT, formato_para_prompt(), EJEMPLOS_PROMPT))


SYSTEM_PROMPT = _construir_system_prompt()


# Conjunto de nombres de campos universales (no se sanitizan; aplican siempre).
_NOMBRES_UNIVERSALES: set[str] = {f.nombre for f in FILTROS_UNIVERSALES}
# Tambien protegemos algunos campos del esquema que no son "filtros especificos":
_NOMBRES_PROTEGIDOS: set[str] = _NOMBRES_UNIVERSALES | {
    "categoria", "grupo", "tipo_producto", "query_texto", "notas_libres",
}


def sanear_filtros(f: SearchFilters) -> SearchFilters:
    """Pone a None los campos especificos que no aplican al `tipo_producto` elegido.

    Asi el LLM puede rellenar de mas con el schema gordo sin contaminar el
    estado posterior. Si `tipo_producto` es None, dejamos los campos como
    estan (el extractor puede haber rellenado por intuicion algo util).
    """
    if f.tipo_producto is None:
        return f
    encontrado = buscar_tipo(f.tipo_producto)
    if encontrado is None:
        return f
    _, _, tipo = encontrado
    permitidos = {fd.nombre for fd in tipo.filtros} | _NOMBRES_PROTEGIDOS
    todos_especificos = todos_los_campos_especificos()
    a_borrar = (todos_especificos - permitidos)
    if not a_borrar:
        return f
    return f.model_copy(update={n: None for n in a_borrar})


def _llm() -> ChatAnthropic:
    return ChatAnthropic(model=MODELO)


async def extraer_filtros(query: str) -> SearchFilters:
    """Llama a Claude Opus con structured output, sanea, y devuelve SearchFilters.

    El system prompt (~2920 tokens, fijo entre llamadas) viaja con
    `cache_control: ephemeral` para que Anthropic lo cachee 5 min y la 2a
    llamada hit-eada cueste ~10% del tiempo.
    """
    query = sanear_query(query)
    llm = _llm().with_structured_output(SearchFilters)
    mensajes = [
        SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        ),
        HumanMessage(content=query),
    ]
    resultado: SearchFilters = await llm.ainvoke(mensajes)  # type: ignore[assignment]
    return sanear_filtros(resultado)
