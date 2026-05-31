"""Traducciones canonical -> idioma local de plataforma.

El extractor LLM produce valores canonicos en espanol (chaqueta, sofa, movil...).
Cada scraper necesita una version en su idioma para enriquecer la URL de busqueda
y obtener resultados mas relevantes desde la fuente.
"""

from __future__ import annotations


# canonical -> {locale: termino_local}
TRADUCCIONES_BUSQUEDA: dict[str, dict[str, str]] = {
    # --- tipo_prenda ---
    "chaqueta": {"fr": "veste", "it": "giacca", "de": "Jacke", "en": "jacket"},
    "pantalon": {"fr": "pantalon", "it": "pantaloni", "de": "Hose", "en": "pants"},
    "vestido": {"fr": "robe", "it": "vestito", "de": "Kleid", "en": "dress"},
    "camisa": {"fr": "chemise", "it": "camicia", "de": "Hemd", "en": "shirt"},
    "abrigo": {"fr": "manteau", "it": "cappotto", "de": "Mantel", "en": "coat"},
    "jersey": {"fr": "pull", "it": "maglione", "de": "Pullover", "en": "sweater"},
    "zapatillas": {"fr": "baskets", "it": "scarpe", "de": "Sneaker", "en": "sneakers"},
    "zapatos": {"fr": "chaussures", "it": "scarpe", "de": "Schuhe", "en": "shoes"},
    "calzado": {"fr": "chaussures", "it": "scarpe", "de": "Schuhe", "en": "shoes"},
    "botas": {"fr": "bottes", "it": "stivali", "de": "Stiefel", "en": "boots"},
    "bolso": {"fr": "sac", "it": "borsa", "de": "Tasche", "en": "bag"},
    "cinturon": {"fr": "ceinture", "it": "cintura", "de": "Guertel", "en": "belt"},
    # --- electronica subcategoria ---
    "movil": {"fr": "telephone", "it": "telefono", "de": "Handy", "en": "smartphone"},
    "telefono": {"fr": "telephone", "it": "telefono", "de": "Handy", "en": "phone"},
    "smartphone": {"fr": "smartphone", "it": "smartphone", "de": "Smartphone", "en": "smartphone"},
    "ordenador": {"fr": "ordinateur", "it": "computer", "de": "Computer", "en": "computer"},
    "portatil": {"fr": "ordinateur portable", "it": "portatile", "de": "Laptop", "en": "laptop"},
    "tablet": {"fr": "tablette", "it": "tablet", "de": "Tablet", "en": "tablet"},
    "camara": {"fr": "appareil photo", "it": "fotocamera", "de": "Kamera", "en": "camera"},
    "audio": {"fr": "audio", "it": "audio", "de": "Audio", "en": "audio"},
    "television": {"fr": "television", "it": "televisione", "de": "Fernseher", "en": "tv"},
    "consola": {"fr": "console", "it": "console", "de": "Konsole", "en": "console"},
    "smartwatch": {"fr": "montre connectee", "it": "smartwatch", "de": "Smartwatch", "en": "smartwatch"},
    # --- hogar subcategoria ---
    "sofa": {"fr": "canape", "it": "divano", "de": "Sofa", "en": "sofa"},
    "mesa": {"fr": "table", "it": "tavolo", "de": "Tisch", "en": "table"},
    "silla": {"fr": "chaise", "it": "sedia", "de": "Stuhl", "en": "chair"},
    "mueble": {"fr": "meuble", "it": "mobile", "de": "Moebel", "en": "furniture"},
}


def traducir_termino(canonical: str | None, idioma: str) -> str | None:
    """Devuelve el termino en el idioma indicado, o None si no hay traduccion."""
    if not canonical:
        return None
    mapa = TRADUCCIONES_BUSQUEDA.get(canonical.lower())
    if not mapa:
        return None
    return mapa.get(idioma.lower())
