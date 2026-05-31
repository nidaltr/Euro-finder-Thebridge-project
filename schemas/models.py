"""Modelos Pydantic v2 compartidos por todo el grafo Eurofinder.

`SearchFilters` es el modelo central: lo produce el extractor LLM, lo lee la UI
y lo consumen scrapers y filter. Sus campos siguen la taxonomia definida en
`schemas/taxonomia.py`: hay 5 universales obligatorios para situar la busqueda
(query_texto, categoria, grupo, tipo_producto, precio/pais/estado) y un buen
numero de campos especificos opcionales, uno por cada FiltroDef del arbol.

Para que un campo nuevo aparezca en este modelo: anadir su `FiltroDef` al tipo
correspondiente en `taxonomia.py` y declararlo aqui con su tipo Python.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.taxonomia import CLAVES_CATEGORIA


# ---------------------------------------------------------------------------
# Literales reutilizables
# ---------------------------------------------------------------------------


# Categoria: clave nivel 1 del arbol. Se mantiene como Literal generado
# manualmente para que Pydantic + LLM tengan tipos cerrados.
Categoria = Literal[
    "vehiculos",
    "moda",
    "electronica",
    "hogar_jardin",
    "deporte_ocio",
    "coleccionismo_arte",
    "instrumentos",
    "ninos_bebes",
    "otros",
]

# Sanity-check en import: si CLAVES_CATEGORIA y el Literal divergen, romper.
assert set(CLAVES_CATEGORIA) == set(Categoria.__args__), (  # type: ignore[attr-defined]
    "CLAVES_CATEGORIA y Categoria Literal estan desincronizados. "
    "Actualiza uno u otro."
)


Estado = Literal["nuevo", "como_nuevo", "buen_estado", "aceptable", "para_piezas"]

Combustible = Literal["gasolina", "diesel", "hibrido", "electrico", "glp_gnc"]
Cambio = Literal["manual", "automatico"]
Puertas = Literal["2_3", "4_5"]
Carroceria = Literal["berlina", "familiar", "suv", "coupe", "cabrio", "monovolumen"]

TipoCaravana = Literal["caravana", "autocaravana", "camper"]
TipoBarco = Literal["lancha", "velero", "moto_agua", "neumatica"]

TipoCalzado = Literal["zapatillas", "zapatos", "botas", "sandalias"]

Movimiento = Literal["automatico", "cuarzo", "manual"]
MaterialCaja = Literal["acero", "oro", "titanio", "ceramica", "chapado"]
Genero = Literal["hombre", "mujer", "unisex", "nino", "nina"]
ConCajaYPapeles = Literal["si", "no", "solo_reloj"]

TipoBolso = Literal["bandolera", "mochila", "tote", "mano"]
TipoJoyeria = Literal["anillo", "collar", "pendientes", "pulsera"]

TipoCamara = Literal["reflex", "sin_espejo", "compacta", "analogica"]
ConObjetivo = Literal["si", "no"]
Resolucion = Literal["hd", "4k", "8k"]
TipoAudio = Literal["altavoces", "auriculares", "equipo_hifi", "barra_sonido"]
RegionVideojuego = Literal["pal", "ntsc"]

TipoBici = Literal["montana", "carretera", "urbana", "electrica", "bmx"]

FormatoVinilo = Literal["lp", "ep", "single", "box_set"]
TamanoVinilo = Literal["12", "10", "7"]
EstadoGoldmine = Literal["M", "NM", "VG+", "VG", "G"]

ZurdoDiestro = Literal["diestro", "zurdo"]

TipoCarrito = Literal["carrito", "silla_coche", "cuna_viaje"]


# ---------------------------------------------------------------------------
# SearchFilters: el modelo principal
# ---------------------------------------------------------------------------


class SearchFilters(BaseModel):
    """Filtros estructurados de una busqueda Eurofinder.

    Producido por el extractor LLM, puede ser editado en la UI, y consumido por
    scrapers y filter. Solo `query_texto` y `categoria` son obligatorios; el
    resto es opcional. La aplicabilidad de cada campo especifico a la
    `categoria/grupo/tipo_producto` elegidos se valida con la taxonomia.
    """

    # --- Localizacion en el arbol (obligatorio categoria, opcionales grupo/tipo) ---
    categoria: Categoria
    grupo: Optional[str] = None
    tipo_producto: Optional[str] = None

    # --- Universales ---
    query_texto: str
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None
    paises_preferidos: list[str] = Field(default_factory=list)
    paises_excluidos: list[str] = Field(default_factory=list)
    estado: Optional[Estado] = None
    notas_libres: Optional[str] = None

    # --- Identidad compartida ---
    marca: Optional[str] = None
    modelo: Optional[str] = None

    # --- Vehiculo: coche y otros ---
    anio: Optional[int] = None             # ramas estandar (moto, furgoneta, ...) y reloj/vinilo
    anio_min: Optional[int] = None         # coche (rango)
    anio_max: Optional[int] = None
    km_max: Optional[int] = None
    cilindrada: Optional[int] = None
    combustible: Optional[Combustible] = None
    cambio: Optional[Cambio] = None
    potencia_min_cv: Optional[int] = None
    puertas: Optional[Puertas] = None
    carroceria: Optional[Carroceria] = None
    plazas: Optional[int] = None
    eslora: Optional[float] = None
    tipo_caravana: Optional[TipoCaravana] = None
    tipo_barco: Optional[TipoBarco] = None
    marca_compatible: Optional[str] = None
    tipo_pieza: Optional[str] = None

    # --- Moda y accesorios ---
    talla: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    tipo_calzado: Optional[TipoCalzado] = None

    # Reloj (rama profunda)
    movimiento: Optional[Movimiento] = None
    material_caja: Optional[MaterialCaja] = None
    diametro_mm: Optional[int] = None
    genero: Optional[Genero] = None
    con_caja_y_papeles: Optional[ConCajaYPapeles] = None

    tipo_bolso: Optional[TipoBolso] = None
    tipo_joyeria: Optional[TipoJoyeria] = None

    # --- Electronica ---
    capacidad: Optional[str] = None
    procesador: Optional[str] = None
    ram: Optional[str] = None
    pulgadas: Optional[float] = None
    tipo_camara: Optional[TipoCamara] = None
    con_objetivo: Optional[ConObjetivo] = None
    resolucion: Optional[Resolucion] = None
    tipo_audio: Optional[TipoAudio] = None
    plataforma_videojuego: Optional[str] = None
    titulo: Optional[str] = None               # videojuego, vinilo, cd, comic, libro
    region: Optional[RegionVideojuego] = None

    # --- Hogar y jardin ---
    plazas_o_dimensiones: Optional[str] = None
    eficiencia_energetica: Optional[str] = None

    # --- Deporte y ocio ---
    tipo_bici: Optional[TipoBici] = None
    talla_cuadro: Optional[str] = None
    tamano_rueda: Optional[str] = None
    deporte: Optional[str] = None
    tipo_articulo: Optional[str] = None

    # --- Coleccionismo y arte ---
    artista: Optional[str] = None
    album: Optional[str] = None
    sello: Optional[str] = None
    pais_prensado: Optional[str] = None
    formato: Optional[FormatoVinilo] = None
    tamano: Optional[TamanoVinilo] = None
    estado_disco: Optional[EstadoGoldmine] = None
    estado_portada: Optional[EstadoGoldmine] = None
    numero_comic: Optional[str] = None
    editorial: Optional[str] = None
    idioma_publicacion: Optional[str] = None
    autor: Optional[str] = None
    pais: Optional[str] = None
    tematica: Optional[str] = None
    epoca: Optional[str] = None
    coleccion: Optional[str] = None

    # --- Instrumentos musicales ---
    zurdo_diestro: Optional[ZurdoDiestro] = None
    numero_teclas: Optional[int] = None
    tipo_instrumento: Optional[str] = None

    # --- Ninos y bebes ---
    edad_o_talla: Optional[str] = None
    edad_recomendada: Optional[str] = None
    tipo_carrito: Optional[TipoCarrito] = None

    # --- Generico (decoracion, antiguedades, cromos, camping, accesorios...) ---
    tipo: Optional[str] = None


# ---------------------------------------------------------------------------
# RawListing y NormalizedListing (no se tocan en este refactor)
# ---------------------------------------------------------------------------


class RawListing(BaseModel):
    """Anuncio tal como lo devuelve un scraper, antes de normalizar.

    Todos los campos son strings opcionales: validacion laxa a proposito, para
    que un cambio menor en el HTML de la plataforma no tumbe el pipeline.
    """

    model_config = ConfigDict(extra="allow")

    plataforma: str
    pais: str
    url: str

    id_externo: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    precio_texto: Optional[str] = None
    moneda: Optional[str] = None
    ubicacion: Optional[str] = None
    thumbnail_url: Optional[str] = None
    fecha_texto: Optional[str] = None
    idioma: Optional[str] = None
    # Posicion 1..N en que la plataforma sirvio este anuncio. Sirve para
    # ordenar por relevancia nativa (intercalando plataformas).
    posicion_plataforma: int = 0


class NormalizedListing(BaseModel):
    """Esquema comun final que se muestra al usuario (una tarjeta de resultado).

    Producido por el normalizador a partir de un `RawListing`, y enriquecido
    por el traductor con `titulo_es` / `descripcion_es`.
    """

    id: str
    plataforma: str
    pais: str

    titulo: str
    titulo_es: Optional[str] = None
    descripcion: Optional[str] = None
    descripcion_es: Optional[str] = None
    idioma: Optional[str] = None

    precio_eur: float
    moneda_original: Optional[str] = None
    precio_original: Optional[float] = None

    ubicacion: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    fecha_publicacion: Optional[datetime] = None
    categoria_detectada: Optional[Categoria] = None

    # Heredado del RawListing: posicion 1..N de la plataforma. Se usa para
    # ordenar por relevancia nativa.
    posicion_plataforma: int = 0

    anio: Optional[int] = None
    km: Optional[int] = None
    combustible: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
