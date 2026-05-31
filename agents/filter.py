"""Filtro post-normalizacion: aplica las restricciones extraidas a los resultados.

Filosofia:
- HARD (descarte directo si no se cumple): precio_max/min, marca, tipo_prenda,
  subcategoria, capacidad, combustible, transmision, talla. Para los textuales
  se usan sinonimos multilingues; un anuncio pasa si su titulo o descripcion
  contiene alguno de los sinonimos del valor pedido.
- SOFT por conflicto (descarte solo si menciona un valor INCOMPATIBLE):
  genero, estado.
- Ignorados (no filtra): color, material. Demasiado poco fiables en titulos
  cortos.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Iterable

from schemas.models import NormalizedListing, SearchFilters


logger = logging.getLogger(__name__)


def _normalizar(texto: str) -> str:
    """Lower + sin diacriticos. Sin colapsos: mantiene espacios y guiones tal
    cual, para que el word-boundary del modelo (M5 ≠ M50) funcione."""
    s = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# Variante: colapsa "256 GB" -> "256gb" (solo digito-espacio-letra). Util para
# matchear capacidades cuando el LLM da "256GB" y el titulo dice "256 GB".
_RE_UNIDADES = re.compile(r"(\d)\s+([a-z])")


def _normalizar_unidades(texto: str) -> str:
    return _RE_UNIDADES.sub(r"\1\2", _normalizar(texto))


# Sinonimos multilingues (ES/FR/IT/DE/EN). Para cada valor "canonico" (clave)
# listamos las formas que pueden aparecer en titulos de cualquier plataforma.
SINONIMOS: dict[str, list[str]] = {
    # genero
    "hombre": ["hombre", "homme", "uomo", "herren", "men", "mens", "man", "masculin"],
    "mujer": ["mujer", "femme", "donna", "damen", "women", "womens", "ladies", "feminin"],
    "unisex": ["unisex"],
    "nino": ["nino", "enfant", "bambino", "kinder", "kids", "child"],
    # combustible
    "gasolina": ["gasolina", "essence", "benzina", "benzin", "gasoline", "petrol"],
    "diesel": ["diesel", "tdi", "hdi", "cdi"],
    "electrico": ["electrico", "electrique", "elettrico", "elektrisch", "electric"],
    "hibrido": ["hibrido", "hybride", "ibrido", "hybrid", "mhev", "phev"],
    "gas": ["glp", "gpl", "lpg", "gnc", "cng", "metano"],
    # transmision
    "automatica": [
        "automatica", "automatique", "automatik", "automatic",
        "s tronic", "stronic", "s-tronic", "dsg", "tiptronic", "multitronic",
        "automat",
    ],
    "manual": ["manual", "manuelle", "manuale", "manuell", "schaltgetriebe"],
    # estado
    "nuevo": ["nuevo", "neuf", "nuovo", "neu", "brand new"],
    "como_nuevo": ["como nuevo", "comme neuf", "come nuovo", "neuwertig", "like new"],
    "buen_estado": ["buen estado", "bon etat", "buono stato", "guter zustand"],
    "aceptable": ["aceptable", "acceptable", "accettabile", "akzeptabel"],
    # tipo_prenda
    "chaqueta": ["chaqueta", "veste", "giacca", "jacke", "jacket", "blazer"],
    "pantalon": ["pantalon", "pantaloni", "hose", "pants", "trousers", "jeans"],
    "vestido": ["vestido", "robe", "vestito", "kleid", "dress"],
    "camisa": ["camisa", "chemise", "camicia", "hemd", "shirt", "blusa", "blouse"],
    "abrigo": ["abrigo", "manteau", "cappotto", "mantel", "coat"],
    "jersey": ["jersey", "pull", "maglione", "pullover", "sweater", "sudadera", "hoodie"],
    "zapatillas": [
        "zapatillas", "baskets", "sneakers", "scarpe da ginnastica", "sneaker",
    ],
    "zapatos": ["zapatos", "chaussures", "scarpe", "schuhe", "shoes", "calzado"],
    "calzado": ["calzado", "chaussures", "scarpe", "schuhe", "shoes", "zapatos"],
    "botas": ["botas", "bottes", "stivali", "stiefel", "boots"],
    "bolso": ["bolso", "sac", "borsa", "tasche", "bag", "handbag", "handtasche"],
    "cinturon": ["cinturon", "ceinture", "cintura", "guertel", "belt"],
    # electronica subcategoria
    "movil": ["movil", "telephone", "telefono", "handy", "smartphone", "phone", "celular"],
    "telefono": ["telephone", "telefono", "phone", "movil", "handy", "smartphone"],
    "smartphone": ["smartphone", "telephone", "telefono", "phone"],
    "ordenador": ["ordenador", "ordinateur", "computer", "pc", "laptop", "portatil", "notebook"],
    "portatil": ["portatil", "laptop", "ordinateur portable", "notebook"],
    "tablet": ["tablet", "tablette", "tableta"],
    "camara": ["camara", "appareil photo", "fotocamera", "kamera", "camera"],
    "audio": ["audio", "auriculares", "casque", "cuffie", "kopfhorer", "headphones"],
    "television": ["television", "tele", "tv", "fernseher"],
    "consola": ["consola", "console", "konsole"],
    "smartwatch": ["smartwatch", "watch", "reloj inteligente", "montre connectee"],
    # hogar subcategoria
    "sofa": ["sofa", "canape", "divano", "couch"],
    "mesa": ["mesa", "table", "tavolo", "tisch"],
    "silla": ["silla", "chaise", "sedia", "stuhl", "chair"],
    "mueble": ["mueble", "meuble", "mobile", "mobel", "furniture"],
    "electrodomestico": ["electrodomestico", "electromenager", "elettrodomestico", "haushaltsgerat"],
    "decoracion": ["decoracion", "decoration", "decorazione", "deko"],
    "iluminacion": ["iluminacion", "luminaire", "illuminazione", "lampe", "lampada"],
    "jardin": ["jardin", "giardino", "garten", "garden"],
}


# Grupos de valores mutuamente excluyentes. Se renombra `transmision` a `cambio`
# para alinear con la taxonomia (SearchFilters.cambio). Los campos no presentes
# en SearchFilters se ignoran a traves de getattr con default None.
# Cuando el usuario busca un vehiculo COMPLETO (coche/moto/furgoneta...), hay
# que descartar anuncios que claramente son piezas, recambios, accesorios o
# replicas a escala (1:18, modellauto, etc.).
TIPOS_VEHICULO_COMPLETO: frozenset[str] = frozenset({
    "coche", "moto", "furgoneta", "caravana_autocaravana", "embarcacion_moto_agua",
})


# Red de seguridad final: tokens UNIVERSALES que delatan que el anuncio NO es
# un producto principal (es replica a escala, anuncio de demanda, o alquiler).
# El filtrado real lo hace el scoping por categoria nativa de cada plataforma
# en los `build_url` de los scrapers; aqui solo cazamos lo que esa categoria
# no atrapa de oficio.
PIEZAS_REPLICAS_TOKENS: tuple[str, ...] = (
    # replicas / miniaturas a escala (universal)
    "1:18", "1/18", "1:43", "1/43", "1:24", "1/24", "1:12", "1/12",
    "modellauto", "modellino", "miniatura", "miniature",
    "diecast", "die-cast",
    "norev", "minichamps", "gt spirit", "kyosho", "autoart", "burago",
    "matchbox",
    "scala 1", "escala 1", "echelle 1", "massstab 1",
    # anuncios de demanda (busco/cerco/suche), no de venta
    "suche:", "cerco:", "cherche:", "wanted:", "busco:",
    "ich suche", "io cerco", "je cherche",
    # alquileres (no venta)
    "mieten", "alquiler ", "noleggio", "noleggiare", "louer ", "a louer",
    "for rent",
)


GRUPOS_EXCLUYENTES: dict[str, list[str]] = {
    "genero": ["hombre", "mujer", "unisex", "nino"],
    "estado": ["nuevo", "como_nuevo", "buen_estado", "aceptable"],
    "combustible": ["gasolina", "diesel", "electrico", "hibrido", "gas"],
    "cambio": ["manual", "automatico"],
}


def _candidatos(valor: str) -> list[str]:
    base = _normalizar(valor)
    fijos = SINONIMOS.get(base)
    if fijos:
        return [_normalizar(s) for s in fijos]
    return [base]


def _contiene_cualquier(tokens: Iterable[str], *campos: str | None) -> bool:
    textos = [_normalizar(c) for c in campos if c]
    return any(token in t for t in textos for token in tokens)


def _talla_presente(talla: str, *campos: str | None) -> bool:
    """Match seguro: talla con word-boundary; evita 'L' dentro de LEVI'S."""
    talla_n = _normalizar(talla)
    if not talla_n:
        return True
    patron = re.compile(rf"(?:^|[^a-z0-9]){re.escape(talla_n)}(?:$|[^a-z0-9])")
    for c in campos:
        if c and patron.search(_normalizar(c)):
            return True
    return False


def _marca_en_titulo(marca: str, titulo: str | None) -> bool:
    """Marca debe aparecer (case+accent insensitive) en el TITULO. Si hay
    sinonimos multilingues registrados, basta con que aparezca cualquiera."""
    if not titulo:
        return False
    titulo_n = _normalizar(titulo)
    for tok in _candidatos(marca):
        if tok in titulo_n:
            return True
    return False


def _modelo_match(modelo: str, titulo: str | None) -> bool:
    """True si `modelo` aparece en `titulo` con word-boundary y separador flex.

    Reglas:
    - Normalizamos titulo y modelo (lower, sin diacriticos).
    - Partimos el modelo por espacios y guiones (Day-Date -> ['day','date'],
      M5 -> ['m5'], iPhone 13 Pro -> ['iphone','13','pro']).
    - PRIMARY: regex con los tokens unidos por `[\\W_]*`, con bordes
      no alfanumericos para evitar matches dentro de palabras mas largas
      (M5 NO matchea en M50/M5i).
    - FALLBACK (>=2 tokens): cada token debe aparecer en titulo con
      word-boundary, en cualquier orden y posicion.
    """
    if not titulo or not modelo:
        return False
    titulo_n = _normalizar(titulo)
    modelo_n = _normalizar(modelo)
    tokens = [t for t in re.split(r"[\s\-]+", modelo_n) if t]
    if not tokens:
        return False
    # Primary: tokens contiguos con separador flexible.
    cuerpo = r"[\W_]*".join(re.escape(t) for t in tokens)
    patron_primary = re.compile(
        rf"(?:^|[^a-z0-9])(?:{cuerpo})(?:[^a-z0-9]|$)"
    )
    if patron_primary.search(titulo_n):
        return True
    # Fallback: cada token suelto en cualquier orden (solo si >=2 tokens).
    if len(tokens) < 2:
        return False
    for t in tokens:
        if not re.search(rf"(?:^|[^a-z0-9]){re.escape(t)}(?:[^a-z0-9]|$)", titulo_n):
            return False
    return True


def _es_pieza_o_replica(titulo: str | None, descripcion: str | None) -> bool:
    """True si el titulo/descripcion parece de una pieza, recambio o replica."""
    textos = [_normalizar(c) for c in (titulo, descripcion) if c]
    if not textos:
        return False
    for tok in PIEZAS_REPLICAS_TOKENS:
        tok_n = _normalizar(tok)
        for t in textos:
            if tok_n in t:
                return True
    return False


def _conflicto_categorico(
    campo: str, valor_pedido: str, titulo: str | None, descripcion: str | None,
) -> bool:
    """True si menciona un valor incompatible del mismo grupo."""
    alternativas = GRUPOS_EXCLUYENTES.get(campo, [])
    if valor_pedido not in alternativas:
        return False
    pedido_toks = _candidatos(valor_pedido)
    pedido_visible = _contiene_cualquier(pedido_toks, titulo, descripcion)
    if pedido_visible:
        return False
    for alt in alternativas:
        if alt == valor_pedido:
            continue
        alt_toks = _candidatos(alt)
        if _contiene_cualquier(alt_toks, titulo, descripcion):
            return True
    return False


def filtrar(
    resultados: list[NormalizedListing],
    filtros: SearchFilters,
) -> list[NormalizedListing]:
    salida: list[NormalizedListing] = []
    descartados: dict[str, int] = {}

    def descartar(motivo: str) -> None:
        descartados[motivo] = descartados.get(motivo, 0) + 1

    # Match auxiliar para capacidad: usa el normalizador con colapso de
    # "256 GB" -> "256gb". Mira titulo Y descripcion (no solo titulo).
    def _capacidad_match(valor: str, titulo: str | None, descripcion: str | None) -> bool:
        v = _normalizar_unidades(valor)
        for c in (titulo, descripcion):
            if c and v in _normalizar_unidades(c):
                return True
        return False

    for r in resultados:
        # --- precio ---
        if r.precio_eur is None or r.precio_eur <= 0:
            descartar("precio_cero")
            continue
        if filtros.precio_max is not None and r.precio_eur > filtros.precio_max:
            descartar("excede_precio_max")
            continue
        if filtros.precio_min is not None and r.precio_eur < filtros.precio_min:
            descartar("bajo_precio_min")
            continue

        # --- marca: en el TITULO unicamente ---
        if filtros.marca and not _marca_en_titulo(filtros.marca, r.titulo):
            descartar("marca_ausente_titulo")
            continue

        # --- modelo: en el TITULO unicamente, con word-boundary ---
        if filtros.modelo and not _modelo_match(filtros.modelo, r.titulo):
            descartar("modelo_ausente_titulo")
            continue

        # --- anti-piezas/replicas para vehiculos completos ---
        if filtros.tipo_producto in TIPOS_VEHICULO_COMPLETO:
            if _es_pieza_o_replica(r.titulo, r.descripcion):
                descartar("es_pieza_o_replica")
                continue

        # --- HARD: capacidad (mira titulo y descripcion, con colapso de
        # unidades "256 GB" -> "256gb") ---
        if filtros.capacidad and not _capacidad_match(
            filtros.capacidad, r.titulo, r.descripcion,
        ):
            descartar("capacidad_ausente")
            continue

        # --- SOFT por conflicto ---
        conflicto = False
        for campo in GRUPOS_EXCLUYENTES:
            valor = getattr(filtros, campo, None)
            if valor and _conflicto_categorico(campo, valor, r.titulo, r.descripcion):
                descartar(f"conflicto_{campo}")
                conflicto = True
                break
        if conflicto:
            continue

        salida.append(r)

    if descartados:
        logger.info("[filtro] descartados: %s", descartados)
    logger.info("[filtro] %d -> %d resultados", len(resultados), len(salida))
    return salida
