"""Taxonomia de Eurofinder: arbol de 4 niveles (categoria -> grupo -> tipo -> filtros).

Esta es la fuente de verdad de la estructura del producto, transcrita de
`taxonomia-eurofinder.md`. Editando este modulo se actualizan automaticamente
el extractor (prompt), la UI (expander) y el filter, porque todos lo consultan
a traves de los helpers que viven aqui abajo.

Reglas globales del arbol:
- Hay 9 categorias (8 grandes + "Otros").
- Cada categoria tiene >=1 grupos.
- Cada grupo tiene >=1 tipos de producto.
- Cada tipo lleva una lista de FiltroDef (campos especificos de ese producto).
- 3 tipos son "rama profunda" (Coche, Reloj, Vinilo): tienen ~8-10 filtros
  detallados y los scrapers idealmente los aplican a fondo.
- El resto son "rama estandar" (3-4 filtros propios).

Los nombres de los campos (FiltroDef.nombre) coinciden EXACTAMENTE con los
atributos de `SearchFilters` en `schemas/models.py`, para que la UI y el
extractor puedan leer/escribir sin diccionarios intermedios.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional


# ---------------------------------------------------------------------------
# Tipos de datos del arbol
# ---------------------------------------------------------------------------


WidgetTipo = Literal["lista", "lista_multi", "texto", "numero"]


@dataclass(frozen=True)
class FiltroDef:
    """Definicion de un filtro asociado a un tipo de producto."""

    nombre: str                          # debe coincidir con un campo de SearchFilters
    label: str                           # texto para la UI
    widget: WidgetTipo
    valores: Optional[tuple[str, ...]] = None  # solo para `lista`/`lista_multi`


@dataclass(frozen=True)
class TipoProducto:
    clave: str                           # 'coche', 'reloj', 'movil', ...
    label: str
    rama_profunda: bool
    filtros: tuple[FiltroDef, ...]


@dataclass(frozen=True)
class Grupo:
    clave: str                           # 'vehiculos', 'piezas_accesorios', ...
    label: str
    tipos: tuple[TipoProducto, ...]


@dataclass(frozen=True)
class CategoriaTax:
    clave: str                           # 'vehiculos', 'moda', 'electronica', ...
    label: str
    grupos: tuple[Grupo, ...]


# ---------------------------------------------------------------------------
# Filtros universales
# ---------------------------------------------------------------------------


VALORES_ESTADO: tuple[str, ...] = (
    "nuevo", "como_nuevo", "buen_estado", "aceptable", "para_piezas",
)
VALORES_PAISES: tuple[str, ...] = ("FR", "DE", "IT", "ES")


FILTROS_UNIVERSALES: tuple[FiltroDef, ...] = (
    FiltroDef("precio_min", "Precio minimo (EUR)", "numero"),
    FiltroDef("precio_max", "Precio maximo (EUR)", "numero"),
    FiltroDef("paises_preferidos", "Paises preferidos", "lista_multi", VALORES_PAISES),
    FiltroDef("paises_excluidos", "Paises excluidos", "lista_multi", VALORES_PAISES),
    FiltroDef("estado", "Estado de conservacion", "lista", VALORES_ESTADO),
)


# ---------------------------------------------------------------------------
# Filtros reutilizables (alias para no repetir codigo)
# ---------------------------------------------------------------------------

_F_MARCA = FiltroDef("marca", "Marca", "texto")
_F_MODELO = FiltroDef("modelo", "Modelo", "texto")
_F_TALLA = FiltroDef("talla", "Talla", "texto")
_F_COLOR = FiltroDef("color", "Color", "texto")
_F_MATERIAL = FiltroDef("material", "Material", "texto")
_F_ANIO = FiltroDef("anio", "Anio", "numero")
_F_ANIO_MIN = FiltroDef("anio_min", "Anio minimo", "numero")
_F_ANIO_MAX = FiltroDef("anio_max", "Anio maximo", "numero")
_F_KM_MAX = FiltroDef("km_max", "Kilometros maximo", "numero")

_COMBUSTIBLES: tuple[str, ...] = ("gasolina", "diesel", "hibrido", "electrico", "glp_gnc")
_F_COMBUSTIBLE = FiltroDef("combustible", "Combustible", "lista", _COMBUSTIBLES)


# ---------------------------------------------------------------------------
# TAXONOMIA (transcrita 1:1 de taxonomia-eurofinder.md)
# ---------------------------------------------------------------------------


# --- 1. VEHICULOS ---

_TIPO_COCHE = TipoProducto(
    clave="coche", label="Coche", rama_profunda=True,
    filtros=(
        _F_MARCA,
        _F_MODELO,
        _F_ANIO_MIN,
        _F_ANIO_MAX,
        _F_KM_MAX,
        _F_COMBUSTIBLE,
        FiltroDef("cambio", "Cambio", "lista", ("manual", "automatico")),
        FiltroDef("potencia_min_cv", "Potencia minima (CV)", "numero"),
        FiltroDef("puertas", "Puertas", "lista", ("2_3", "4_5")),
        FiltroDef("carroceria", "Carroceria", "lista",
                  ("berlina", "familiar", "suv", "coupe", "cabrio", "monovolumen")),
    ),
)

_TIPO_MOTO = TipoProducto(
    clave="moto", label="Moto", rama_profunda=False,
    filtros=(
        _F_MARCA, _F_MODELO,
        FiltroDef("cilindrada", "Cilindrada (cc)", "numero"),
        _F_ANIO,
        _F_KM_MAX,
    ),
)

_TIPO_FURGONETA = TipoProducto(
    clave="furgoneta", label="Furgoneta", rama_profunda=False,
    filtros=(_F_MARCA, _F_ANIO, _F_KM_MAX, _F_COMBUSTIBLE),
)

_TIPO_CARAVANA = TipoProducto(
    clave="caravana_autocaravana", label="Caravana / autocaravana", rama_profunda=False,
    filtros=(
        FiltroDef("tipo_caravana", "Tipo", "lista", ("caravana", "autocaravana", "camper")),
        FiltroDef("plazas", "Plazas", "numero"),
        _F_ANIO,
    ),
)

_TIPO_EMBARCACION = TipoProducto(
    clave="embarcacion_moto_agua", label="Embarcacion / moto de agua", rama_profunda=False,
    filtros=(
        FiltroDef("tipo_barco", "Tipo", "lista", ("lancha", "velero", "moto_agua", "neumatica")),
        FiltroDef("eslora", "Eslora (m)", "numero"),
        _F_ANIO,
    ),
)

_TIPO_RECAMBIOS = TipoProducto(
    clave="recambios", label="Recambios", rama_profunda=False,
    filtros=(
        FiltroDef("marca_compatible", "Marca compatible", "texto"),
        FiltroDef("tipo_pieza", "Tipo de pieza", "texto"),
    ),
)

_TIPO_ACC_VEHICULOS = TipoProducto(
    clave="accesorios_vehiculos", label="Accesorios (neumaticos, navegadores...)",
    rama_profunda=False,
    filtros=(
        FiltroDef("marca_compatible", "Marca compatible", "texto"),
        FiltroDef("tipo_pieza", "Tipo de accesorio", "texto"),
    ),
)


CAT_VEHICULOS = CategoriaTax(
    clave="vehiculos", label="Vehiculos",
    grupos=(
        Grupo("vehiculos", "Vehiculos", (
            _TIPO_COCHE, _TIPO_MOTO, _TIPO_FURGONETA, _TIPO_CARAVANA, _TIPO_EMBARCACION,
        )),
        Grupo("piezas_accesorios", "Piezas y accesorios", (
            _TIPO_RECAMBIOS, _TIPO_ACC_VEHICULOS,
        )),
    ),
)


# --- 2. MODA Y ACCESORIOS ---

_FILTROS_CALZADO = (
    _F_MARCA, _F_TALLA,
    FiltroDef("tipo_calzado", "Tipo", "lista",
              ("zapatillas", "zapatos", "botas", "sandalias")),
    _F_COLOR,
)

_FILTROS_ROPA = (_F_MARCA, _F_TALLA, _F_COLOR, _F_MATERIAL)

_TIPO_CALZADO_H = TipoProducto("calzado_hombre", "Calzado", False, _FILTROS_CALZADO)
_TIPO_ROPA_SUP_H = TipoProducto("ropa_superior_hombre", "Ropa superior", False, _FILTROS_ROPA)
_TIPO_ROPA_INF_H = TipoProducto("ropa_inferior_hombre", "Ropa inferior", False, _FILTROS_ROPA)
_TIPO_ABRIGOS_H = TipoProducto("abrigos_chaquetas_hombre", "Abrigos y chaquetas", False, _FILTROS_ROPA)

_TIPO_CALZADO_M = TipoProducto("calzado_mujer", "Calzado", False, _FILTROS_CALZADO)
_TIPO_ROPA_SUP_M = TipoProducto("ropa_superior_mujer", "Ropa superior", False, _FILTROS_ROPA)
_TIPO_ROPA_INF_M = TipoProducto("ropa_inferior_mujer", "Ropa inferior", False, _FILTROS_ROPA)
_TIPO_VESTIDOS = TipoProducto("vestidos", "Vestidos", False, _FILTROS_ROPA)
_TIPO_ABRIGOS_M = TipoProducto("abrigos_chaquetas_mujer", "Abrigos y chaquetas", False, _FILTROS_ROPA)

_TIPO_RELOJ = TipoProducto(
    clave="reloj", label="Reloj", rama_profunda=True,
    filtros=(
        _F_MARCA,
        _F_MODELO,
        FiltroDef("movimiento", "Tipo de movimiento", "lista",
                  ("automatico", "cuarzo", "manual")),
        FiltroDef("material_caja", "Material de la caja", "lista",
                  ("acero", "oro", "titanio", "ceramica", "chapado")),
        FiltroDef("diametro_mm", "Diametro de caja (mm)", "numero"),
        FiltroDef("genero", "Genero", "lista", ("hombre", "mujer", "unisex")),
        FiltroDef("con_caja_y_papeles", "Con caja y papeles", "lista",
                  ("si", "no", "solo_reloj")),
        _F_ANIO,
    ),
)

_TIPO_BOLSOS = TipoProducto(
    clave="bolsos", label="Bolsos", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("tipo_bolso", "Tipo", "lista", ("bandolera", "mochila", "tote", "mano")),
        _F_COLOR,
    ),
)

_TIPO_JOYERIA = TipoProducto(
    clave="joyeria", label="Joyeria", rama_profunda=False,
    filtros=(
        FiltroDef("tipo_joyeria", "Tipo", "lista",
                  ("anillo", "collar", "pendientes", "pulsera")),
        _F_MATERIAL,
    ),
)

_TIPO_GAFAS = TipoProducto(
    clave="gafas_sol", label="Gafas de sol", rama_profunda=False,
    filtros=(_F_MARCA, _F_COLOR),
)

_TIPO_CINTURONES = TipoProducto(
    clave="cinturones_otros", label="Cinturones y otros", rama_profunda=False,
    filtros=(_F_MARCA, _F_COLOR, _F_MATERIAL),
)


CAT_MODA = CategoriaTax(
    clave="moda", label="Moda y accesorios",
    grupos=(
        Grupo("moda_hombre", "Moda hombre", (
            _TIPO_CALZADO_H, _TIPO_ROPA_SUP_H, _TIPO_ROPA_INF_H, _TIPO_ABRIGOS_H,
        )),
        Grupo("moda_mujer", "Moda mujer", (
            _TIPO_CALZADO_M, _TIPO_ROPA_SUP_M, _TIPO_ROPA_INF_M, _TIPO_VESTIDOS, _TIPO_ABRIGOS_M,
        )),
        Grupo("accesorios", "Accesorios", (
            _TIPO_RELOJ, _TIPO_BOLSOS, _TIPO_JOYERIA, _TIPO_GAFAS, _TIPO_CINTURONES,
        )),
    ),
)


# --- 3. ELECTRONICA ---

_TIPO_MOVIL = TipoProducto(
    clave="movil", label="Movil / smartphone", rama_profunda=False,
    filtros=(
        _F_MARCA, _F_MODELO,
        FiltroDef("capacidad", "Capacidad (64GB, 256GB...)", "texto"),
        _F_COLOR,
    ),
)

_TIPO_PORTATIL = TipoProducto(
    clave="portatil", label="Portatil", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("procesador", "Procesador", "texto"),
        FiltroDef("ram", "RAM", "texto"),
        FiltroDef("pulgadas", "Pulgadas", "numero"),
    ),
)

_TIPO_SOBREMESA = TipoProducto(
    clave="sobremesa", label="Ordenador sobremesa", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("procesador", "Procesador", "texto"),
        FiltroDef("ram", "RAM", "texto"),
    ),
)

_TIPO_TABLET = TipoProducto(
    clave="tablet", label="Tablet", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("capacidad", "Capacidad", "texto"),
        FiltroDef("pulgadas", "Pulgadas", "numero"),
    ),
)

_TIPO_CAMARA = TipoProducto(
    clave="camara_fotos", label="Camara de fotos", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("tipo_camara", "Tipo", "lista",
                  ("reflex", "sin_espejo", "compacta", "analogica")),
        FiltroDef("con_objetivo", "Con objetivo", "lista", ("si", "no")),
    ),
)

_TIPO_TV = TipoProducto(
    clave="television", label="Television", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("pulgadas", "Pulgadas", "numero"),
        FiltroDef("resolucion", "Resolucion", "lista", ("hd", "4k", "8k")),
    ),
)

_TIPO_AUDIO = TipoProducto(
    clave="audio", label="Audio", rama_profunda=False,
    filtros=(
        _F_MARCA,
        FiltroDef("tipo_audio", "Tipo", "lista",
                  ("altavoces", "auriculares", "equipo_hifi", "barra_sonido")),
    ),
)

_TIPO_CONSOLA = TipoProducto(
    clave="consola", label="Consola", rama_profunda=False,
    filtros=(_F_MARCA, _F_MODELO),
)

_TIPO_VIDEOJUEGO = TipoProducto(
    clave="videojuego", label="Videojuego", rama_profunda=False,
    filtros=(
        FiltroDef("plataforma_videojuego", "Plataforma", "texto"),
        FiltroDef("titulo", "Titulo", "texto"),
        FiltroDef("region", "Region", "lista", ("pal", "ntsc")),
    ),
)

_TIPO_ACC_ELECTRONICA = TipoProducto(
    clave="accesorios_electronica", label="Accesorios y componentes", rama_profunda=False,
    filtros=(
        FiltroDef("marca_compatible", "Marca compatible", "texto"),
        FiltroDef("tipo", "Tipo", "texto"),
    ),
)


CAT_ELECTRONICA = CategoriaTax(
    clave="electronica", label="Electronica",
    grupos=(
        Grupo("informatica_telefonia", "Informatica y telefonia", (
            _TIPO_MOVIL, _TIPO_PORTATIL, _TIPO_SOBREMESA, _TIPO_TABLET,
        )),
        Grupo("imagen_sonido", "Imagen y sonido", (
            _TIPO_CAMARA, _TIPO_TV, _TIPO_AUDIO,
        )),
        Grupo("videojuegos", "Videojuegos", (
            _TIPO_CONSOLA, _TIPO_VIDEOJUEGO,
        )),
        Grupo("accesorios_componentes", "Accesorios y componentes", (
            _TIPO_ACC_ELECTRONICA,
        )),
    ),
)


# --- 4. HOGAR Y JARDIN ---

_FILTROS_MUEBLE = (
    _F_MATERIAL, _F_COLOR,
    FiltroDef("plazas_o_dimensiones", "Plazas o dimensiones", "texto"),
)

_TIPO_SOFA = TipoProducto("sofa", "Sofa", False, _FILTROS_MUEBLE)
_TIPO_MESA = TipoProducto("mesa", "Mesa", False, _FILTROS_MUEBLE)
_TIPO_SILLA = TipoProducto("silla", "Silla", False, _FILTROS_MUEBLE)
_TIPO_ARMARIO = TipoProducto("armario_almacenaje", "Armario / almacenaje", False, _FILTROS_MUEBLE)

_FILTROS_ELECTRODOM = (
    _F_MARCA,
    FiltroDef("tipo", "Tipo", "texto"),
    FiltroDef("eficiencia_energetica", "Eficiencia energetica", "texto"),
)

_TIPO_ELECTRO_GRANDE = TipoProducto(
    "electrodom_grandes", "Electrodomesticos grandes", False, _FILTROS_ELECTRODOM,
)
_TIPO_ELECTRO_PEQUE = TipoProducto(
    "electrodom_pequenos", "Electrodomesticos pequenos", False, _FILTROS_ELECTRODOM,
)

_FILTROS_DECO_JARDIN = (
    FiltroDef("tipo", "Tipo", "texto"),
    _F_MATERIAL,
)

_TIPO_DECORACION = TipoProducto("decoracion", "Decoracion", False, _FILTROS_DECO_JARDIN)
_TIPO_JARDIN = TipoProducto("jardin_exterior", "Jardin y exterior", False, _FILTROS_DECO_JARDIN)


CAT_HOGAR = CategoriaTax(
    clave="hogar_jardin", label="Hogar y jardin",
    grupos=(
        Grupo("mobiliario", "Mobiliario", (
            _TIPO_SOFA, _TIPO_MESA, _TIPO_SILLA, _TIPO_ARMARIO,
        )),
        Grupo("electrodomesticos", "Electrodomesticos", (
            _TIPO_ELECTRO_GRANDE, _TIPO_ELECTRO_PEQUE,
        )),
        Grupo("decoracion_jardin", "Decoracion y jardin", (
            _TIPO_DECORACION, _TIPO_JARDIN,
        )),
    ),
)


# --- 5. DEPORTE Y OCIO ---

_TIPO_BICI = TipoProducto(
    clave="bicicleta", label="Bicicleta", rama_profunda=False,
    filtros=(
        FiltroDef("tipo_bici", "Tipo", "lista",
                  ("montana", "carretera", "urbana", "electrica", "bmx")),
        _F_MARCA,
        FiltroDef("talla_cuadro", "Talla de cuadro", "texto"),
        FiltroDef("tamano_rueda", "Tamano de rueda", "texto"),
    ),
)

_FILTROS_MATERIAL_DEPORTIVO = (
    FiltroDef("deporte", "Deporte", "texto"),
    _F_MARCA,
    FiltroDef("tipo_articulo", "Tipo de articulo", "texto"),
)

_TIPO_FITNESS = TipoProducto("fitness_gimnasio", "Fitness y gimnasio", False, _FILTROS_MATERIAL_DEPORTIVO)
_TIPO_EQUIPO = TipoProducto("deportes_equipo", "Deportes de equipo", False, _FILTROS_MATERIAL_DEPORTIVO)
_TIPO_MONTANA_AGUA = TipoProducto(
    "deportes_montana_agua", "Deportes de montana / agua", False, _FILTROS_MATERIAL_DEPORTIVO,
)

_TIPO_CAMPING = TipoProducto(
    clave="material_camping", label="Material de camping", rama_profunda=False,
    filtros=(
        FiltroDef("tipo", "Tipo", "texto"),
        _F_MARCA,
    ),
)


CAT_DEPORTE = CategoriaTax(
    clave="deporte_ocio", label="Deporte y ocio",
    grupos=(
        Grupo("ciclismo", "Ciclismo", (_TIPO_BICI,)),
        Grupo("material_deportivo", "Material deportivo", (
            _TIPO_FITNESS, _TIPO_EQUIPO, _TIPO_MONTANA_AGUA,
        )),
        Grupo("camping_aire_libre", "Camping y aire libre", (_TIPO_CAMPING,)),
    ),
)


# --- 6. COLECCIONISMO Y ARTE ---

_TIPO_VINILO = TipoProducto(
    clave="vinilo", label="Vinilo", rama_profunda=True,
    filtros=(
        FiltroDef("artista", "Artista", "texto"),
        FiltroDef("album", "Album / titulo", "texto"),
        FiltroDef("sello", "Sello discografico", "texto"),
        _F_ANIO,
        FiltroDef("pais_prensado", "Pais de prensado", "texto"),
        FiltroDef("formato", "Formato", "lista", ("lp", "ep", "single", "box_set")),
        FiltroDef("tamano", "Tamano", "lista", ("12", "10", "7")),
        FiltroDef("estado_disco", "Estado del disco (Goldmine)", "lista",
                  ("M", "NM", "VG+", "VG", "G")),
        FiltroDef("estado_portada", "Estado de la portada (Goldmine)", "lista",
                  ("M", "NM", "VG+", "VG", "G")),
    ),
)

_TIPO_CD = TipoProducto(
    clave="cd_casete", label="CD / casete", rama_profunda=False,
    filtros=(
        FiltroDef("artista", "Artista", "texto"),
        FiltroDef("titulo", "Titulo", "texto"),
        _F_ANIO,
    ),
)

_TIPO_COMIC = TipoProducto(
    clave="comic_tebeo", label="Comic / tebeo", rama_profunda=False,
    filtros=(
        FiltroDef("titulo", "Titulo", "texto"),
        FiltroDef("numero_comic", "Numero", "texto"),
        FiltroDef("editorial", "Editorial", "texto"),
        FiltroDef("idioma_publicacion", "Idioma", "texto"),
    ),
)

_TIPO_LIBRO_COL = TipoProducto(
    clave="libro_coleccion", label="Libro de coleccion", rama_profunda=False,
    filtros=(
        FiltroDef("titulo", "Titulo", "texto"),
        FiltroDef("autor", "Autor", "texto"),
        FiltroDef("editorial", "Editorial", "texto"),
        _F_ANIO,
    ),
)

_TIPO_MONEDAS = TipoProducto(
    clave="monedas", label="Monedas", rama_profunda=False,
    filtros=(
        FiltroDef("pais", "Pais", "texto"),
        _F_ANIO,
        _F_MATERIAL,
    ),
)

_TIPO_SELLOS = TipoProducto(
    clave="sellos", label="Sellos", rama_profunda=False,
    filtros=(
        FiltroDef("pais", "Pais", "texto"),
        _F_ANIO,
        FiltroDef("tematica", "Tematica", "texto"),
    ),
)

_TIPO_ANTIGUEDADES = TipoProducto(
    clave="antiguedades", label="Antiguedades", rama_profunda=False,
    filtros=(
        FiltroDef("tipo", "Tipo", "texto"),
        FiltroDef("epoca", "Epoca", "texto"),
        _F_MATERIAL,
    ),
)

_TIPO_CROMOS = TipoProducto(
    clave="cromos_cartas", label="Cromos / cartas coleccionables", rama_profunda=False,
    filtros=(
        FiltroDef("coleccion", "Coleccion", "texto"),
        FiltroDef("tipo", "Tipo", "texto"),
    ),
)


CAT_COLECCIONISMO = CategoriaTax(
    clave="coleccionismo_arte", label="Coleccionismo y arte",
    grupos=(
        Grupo("musica_fisica", "Musica fisica", (_TIPO_VINILO, _TIPO_CD)),
        Grupo("comics_libros", "Comics y libros", (_TIPO_COMIC, _TIPO_LIBRO_COL)),
        Grupo("numismatica_filatelia", "Numismatica y filatelia", (
            _TIPO_MONEDAS, _TIPO_SELLOS,
        )),
        Grupo("otros_coleccionables", "Otros coleccionables", (
            _TIPO_ANTIGUEDADES, _TIPO_CROMOS,
        )),
    ),
)


# --- 7. INSTRUMENTOS MUSICALES ---

_FILTROS_CUERDA = (
    _F_MARCA, _F_MODELO,
    FiltroDef("tipo", "Tipo", "texto"),
    _F_ANIO,
    FiltroDef("zurdo_diestro", "Zurdo o diestro", "lista", ("diestro", "zurdo")),
)

_TIPO_GUIT_ELEC = TipoProducto("guitarra_electrica", "Guitarra electrica", False, _FILTROS_CUERDA)
_TIPO_GUIT_ACUS = TipoProducto("guitarra_acustica", "Guitarra acustica / clasica", False, _FILTROS_CUERDA)
_TIPO_BAJO = TipoProducto("bajo", "Bajo", False, _FILTROS_CUERDA)
_TIPO_OTRAS_CUERDAS = TipoProducto("otros_cuerda", "Otros (violin, ukelele...)", False, _FILTROS_CUERDA)

_FILTROS_TECLADO = (
    _F_MARCA, _F_MODELO,
    FiltroDef("numero_teclas", "Numero de teclas", "numero"),
)

_TIPO_PIANO = TipoProducto("piano_teclado", "Piano / teclado", False, _FILTROS_TECLADO)
_TIPO_SINTE = TipoProducto("sintetizador", "Sintetizador", False, _FILTROS_TECLADO)

_FILTROS_VIENTO_PERC = (
    FiltroDef("tipo_instrumento", "Tipo de instrumento", "texto"),
    _F_MARCA,
)

_TIPO_VIENTO = TipoProducto("viento", "Viento", False, _FILTROS_VIENTO_PERC)
_TIPO_PERCUSION = TipoProducto("percusion_bateria", "Percusion / bateria", False, _FILTROS_VIENTO_PERC)

_FILTROS_EQUIPO_MUSICA = (
    _F_MARCA, _F_MODELO,
    FiltroDef("tipo", "Tipo", "texto"),
)

_TIPO_AMPLIS = TipoProducto("amplificadores", "Amplificadores", False, _FILTROS_EQUIPO_MUSICA)
_TIPO_PEDALES = TipoProducto("pedales_efectos", "Pedales y efectos", False, _FILTROS_EQUIPO_MUSICA)
_TIPO_ACC_MUSICA = TipoProducto("accesorios_musica", "Accesorios (cuerdas, fundas...)", False, _FILTROS_EQUIPO_MUSICA)


CAT_INSTRUMENTOS = CategoriaTax(
    clave="instrumentos", label="Instrumentos musicales",
    grupos=(
        Grupo("cuerda", "Cuerda", (_TIPO_GUIT_ELEC, _TIPO_GUIT_ACUS, _TIPO_BAJO, _TIPO_OTRAS_CUERDAS)),
        Grupo("teclado", "Teclado", (_TIPO_PIANO, _TIPO_SINTE)),
        Grupo("viento_percusion", "Viento y percusion", (_TIPO_VIENTO, _TIPO_PERCUSION)),
        Grupo("equipo_accesorios", "Equipo y accesorios", (_TIPO_AMPLIS, _TIPO_PEDALES, _TIPO_ACC_MUSICA)),
    ),
)


# --- 8. NINOS Y BEBES ---

_FILTROS_ROPA_INFANTIL = (
    FiltroDef("edad_o_talla", "Talla o edad", "texto"),
    _F_MARCA,
    FiltroDef("genero", "Genero", "lista", ("nino", "nina", "unisex")),
)

_TIPO_ROPA_BEBE = TipoProducto(
    "ropa_bebe", "Ropa bebe (0-3 anos)", False, _FILTROS_ROPA_INFANTIL,
)
_TIPO_ROPA_NINO = TipoProducto(
    "ropa_nino", "Ropa nino (3-12 anos)", False, _FILTROS_ROPA_INFANTIL,
)

_TIPO_JUGUETES = TipoProducto(
    clave="juguetes", label="Juguetes", rama_profunda=False,
    filtros=(
        FiltroDef("tipo", "Tipo", "texto"),
        _F_MARCA,
        FiltroDef("edad_recomendada", "Edad recomendada", "texto"),
    ),
)

_TIPO_CARRITOS = TipoProducto(
    clave="carritos_sillas_coche", label="Carritos y sillas de coche", rama_profunda=False,
    filtros=(
        FiltroDef("tipo_carrito", "Tipo", "lista",
                  ("carrito", "silla_coche", "cuna_viaje")),
        _F_MARCA,
    ),
)

_TIPO_MOBI_INFANTIL = TipoProducto(
    clave="mobiliario_infantil", label="Mobiliario infantil", rama_profunda=False,
    filtros=(
        FiltroDef("tipo", "Tipo", "texto"),
        _F_MATERIAL,
    ),
)


CAT_NINOS = CategoriaTax(
    clave="ninos_bebes", label="Ninos y bebes",
    grupos=(
        Grupo("ropa_infantil", "Ropa infantil", (_TIPO_ROPA_BEBE, _TIPO_ROPA_NINO)),
        Grupo("juguetes", "Juguetes", (_TIPO_JUGUETES,)),
        Grupo("equipamiento", "Equipamiento", (_TIPO_CARRITOS, _TIPO_MOBI_INFANTIL)),
    ),
)


# --- 9. OTROS ---

CAT_OTROS = CategoriaTax(
    clave="otros", label="Otros",
    # Sin grupos especificos; solo aplican filtros universales.
    grupos=(),
)


# ---------------------------------------------------------------------------
# Estructura completa
# ---------------------------------------------------------------------------

TAXONOMIA: tuple[CategoriaTax, ...] = (
    CAT_VEHICULOS,
    CAT_MODA,
    CAT_ELECTRONICA,
    CAT_HOGAR,
    CAT_DEPORTE,
    CAT_COLECCIONISMO,
    CAT_INSTRUMENTOS,
    CAT_NINOS,
    CAT_OTROS,
)


# Claves de categoria (las usa schemas/models.py para construir el Literal)
CLAVES_CATEGORIA: tuple[str, ...] = tuple(c.clave for c in TAXONOMIA)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def iter_tipos() -> Iterable[tuple[str, str, TipoProducto]]:
    """Yield (categoria_clave, grupo_clave, TipoProducto) por cada tipo del arbol."""
    for cat in TAXONOMIA:
        for g in cat.grupos:
            for t in g.tipos:
                yield (cat.clave, g.clave, t)


def buscar_tipo(tipo_clave: str) -> Optional[tuple[CategoriaTax, Grupo, TipoProducto]]:
    """Devuelve (categoria, grupo, tipo) o None si la clave no existe."""
    for cat in TAXONOMIA:
        for g in cat.grupos:
            for t in g.tipos:
                if t.clave == tipo_clave:
                    return (cat, g, t)
    return None


def buscar_categoria(cat_clave: str) -> Optional[CategoriaTax]:
    for cat in TAXONOMIA:
        if cat.clave == cat_clave:
            return cat
    return None


def filtros_aplicables(tipo_clave: Optional[str]) -> list[FiltroDef]:
    """Lista de FiltroDef que la UI/filter deben mostrar para `tipo_clave`.

    Incluye los universales seguidos de los especificos del tipo. Si no hay
    `tipo_clave` (o no se encuentra), solo universales.
    """
    base = list(FILTROS_UNIVERSALES)
    if tipo_clave:
        encontrado = buscar_tipo(tipo_clave)
        if encontrado:
            _, _, t = encontrado
            base.extend(t.filtros)
    return base


def todos_los_campos_especificos() -> set[str]:
    """Nombres de todos los campos (FiltroDef.nombre) que aparecen en algun tipo.

    Util para el saneador del extractor: cualquier campo especifico que no
    figure entre los del tipo elegido se pone a None.
    """
    return {f.nombre for _, _, t in iter_tipos() for f in t.filtros}


def claves_grupo(cat_clave: str) -> tuple[str, ...]:
    cat = buscar_categoria(cat_clave)
    if cat is None:
        return ()
    return tuple(g.clave for g in cat.grupos)


def claves_tipo(cat_clave: str, grupo_clave: str) -> tuple[str, ...]:
    cat = buscar_categoria(cat_clave)
    if cat is None:
        return ()
    for g in cat.grupos:
        if g.clave == grupo_clave:
            return tuple(t.clave for t in g.tipos)
    return ()


# ---------------------------------------------------------------------------
# Render del prompt para el LLM
# ---------------------------------------------------------------------------


def _filtro_a_linea(f: FiltroDef) -> str:
    if f.widget in ("lista", "lista_multi") and f.valores:
        vals = " | ".join(f.valores)
        return f"  - `{f.nombre}` ({f.widget}): {vals}"
    return f"  - `{f.nombre}` ({f.widget})"


def formato_para_prompt() -> str:
    """Renderiza el arbol completo en markdown para inyectarlo al system prompt."""
    out: list[str] = []
    out.append("## Arbol de categorias")
    out.append("")
    out.append("Cada busqueda debe situarse en (categoria, grupo, tipo). El tipo es lo")
    out.append("que determina que filtros especificos rellenar. Marcadas con (RAMA")
    out.append("PROFUNDA) las que tienen mas filtros y exigen mayor detalle.")
    out.append("")

    for cat in TAXONOMIA:
        out.append(f"### Categoria: `{cat.clave}` ({cat.label})")
        if not cat.grupos:
            out.append("Sin grupos: solo aplican filtros universales.")
            out.append("")
            continue
        for g in cat.grupos:
            out.append(f"- Grupo `{g.clave}` ({g.label}):")
            for t in g.tipos:
                marca_prof = " (RAMA PROFUNDA)" if t.rama_profunda else ""
                out.append(f"  - Tipo `{t.clave}` ({t.label}){marca_prof}")
                for f in t.filtros:
                    out.append("    " + _filtro_a_linea(f).lstrip())
        out.append("")

    out.append("## Filtros universales (aplican a CUALQUIER busqueda)")
    out.append("")
    for f in FILTROS_UNIVERSALES:
        out.append(_filtro_a_linea(f))
    return "\n".join(out)
