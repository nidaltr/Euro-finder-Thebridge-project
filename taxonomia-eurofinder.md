# Taxonomía de Eurofinder — Especificación de categorías y filtros

Documento de diseño para reconstruir el modelo de datos del proyecto.
Sustituye al esquema plano anterior. Es la fuente de verdad de la estructura.

---

## 1. Cómo leer este documento

El proyecto tiene una jerarquía de **cuatro niveles**:

```
CATEGORÍA  →  GRUPO  →  TIPO DE PRODUCTO  →  FILTROS
```

- **Categoría**: las 8 grandes áreas (+ "Otros").
- **Grupo**: subdivisión dentro de la categoría. Incluye siempre un grupo de
  "piezas / accesorios" donde aplica, para separar el producto completo de
  sus recambios.
- **Tipo de producto**: el objeto concreto. Es el nivel donde viven los filtros.
- **Filtros**: campos que acotan la búsqueda de ese tipo de producto.

Hay dos clases de tipo de producto:

- **RAMA PROFUNDA** (marcada con ★): sus filtros se implementan a fondo y los
  scrapers los aplican de verdad sobre cada plataforma. Son **Coches, Relojes
  y Vinilos**.
- **RAMA ESTÁNDAR**: tiene 3-4 filtros propios además de los universales, pero
  el filtrado fino es más básico. La búsqueda funciona igualmente.

Cada filtro se marca como:
- `[lista]` — desplegable de valores cerrados (se indican los valores).
- `[texto]` — campo de texto libre.
- `[número]` — valor numérico (rango min/max donde aplique).

---

## 2. Filtros universales

Se aplican a CUALQUIER búsqueda, en las 8 categorías. Se definen una sola vez.

| Filtro | Tipo | Notas |
|---|---|---|
| Texto de búsqueda | `[texto]` | Lo que escribe el usuario. Campo principal. |
| Categoría | `[lista]` | Una de las 8 + "Otros". Determina qué filtros aparecen. |
| Precio mín / máx | `[número]` | En euros. |
| País | `[lista multi]` | Países donde buscar. Por defecto: todos. Permite preferir o excluir. |
| Estado de conservación | `[lista]` | nuevo / como nuevo / buen estado / aceptable / para piezas |

Regla de comportamiento por defecto: si el usuario no rellena un filtro, NO se
descarta nada por ese criterio. El sistema busca de forma amplia y solo acota
con lo que el usuario (o el extractor LLM) haya especificado.

---

## 3. El árbol completo de las 8 categorías

### CATEGORÍA 1 — VEHÍCULOS

```
Vehículos
├── Vehículos (grupo)
│   ├── ★ Coche          [RAMA PROFUNDA]
│   ├── Moto
│   ├── Furgoneta
│   ├── Caravana / autocaravana
│   └── Embarcación / moto de agua
└── Piezas y accesorios (grupo)
    ├── Recambios
    └── Accesorios (neumáticos, navegadores, etc.)
```

**★ Coche — filtros (rama profunda):**
- Marca `[texto]`
- Modelo `[texto]`
- Año mín / máx `[número]`
- Precio mín / máx `[número]` (universal)
- Kilómetros máx `[número]`
- Combustible `[lista]`: gasolina / diésel / híbrido / eléctrico / GLP-GNC
- Cambio `[lista]`: manual / automático
- Potencia mín (CV) `[número]`
- Puertas `[lista]`: 2/3 / 4/5
- Carrocería `[lista]`: berlina / familiar / SUV / coupé / cabrio / monovolumen
- Estado `[lista]` (universal)

> Nota de implementación: la subcategoría "Coche" y el grupo "Piezas y
> accesorios" están separados a propósito. Una búsqueda de coche NO debe
> devolver recambios. Además, descartar siempre anuncios sin precio o con
> precio 0 € (son de desguaces/profesionales sin precio publicado).

**Moto — filtros (estándar):** marca `[texto]`, modelo `[texto]`,
cilindrada `[número]`, año `[número]`, kilómetros máx `[número]`.

**Furgoneta — filtros (estándar):** marca `[texto]`, año `[número]`,
kilómetros máx `[número]`, combustible `[lista]`.

**Caravana / autocaravana — filtros (estándar):** tipo `[lista]`: caravana /
autocaravana / camper; plazas `[número]`; año `[número]`.

**Embarcación / moto de agua — filtros (estándar):** tipo `[lista]`: lancha /
velero / moto de agua / neumática; eslora `[número]`; año `[número]`.

**Piezas y accesorios — filtros (estándar):** marca compatible `[texto]`,
tipo de pieza `[texto]`.

---

### CATEGORÍA 2 — MODA Y ACCESORIOS

```
Moda y accesorios
├── Moda hombre (grupo)
│   ├── Calzado
│   ├── Ropa superior (camisetas, camisas, jerséis...)
│   ├── Ropa inferior (pantalones, vaqueros...)
│   └── Abrigos y chaquetas
├── Moda mujer (grupo)
│   ├── Calzado
│   ├── Ropa superior
│   ├── Ropa inferior
│   ├── Vestidos
│   └── Abrigos y chaquetas
└── Accesorios (grupo)
    ├── ★ Reloj           [RAMA PROFUNDA]
    ├── Bolsos
    ├── Joyería
    ├── Gafas de sol
    └── Cinturones y otros
```

**★ Reloj — filtros (rama profunda):**
- Marca `[texto]`
- Modelo `[texto]`
- Precio mín / máx `[número]` (universal)
- Tipo de movimiento `[lista]`: automático / cuarzo / manual
- Material de la caja `[lista]`: acero / oro / titanio / cerámica / chapado
- Diámetro de caja `[número]` (mm)
- Género `[lista]`: hombre / mujer / unisex
- Con caja y papeles `[lista]`: sí / no / solo reloj
- Estado `[lista]` (universal)
- Año de fabricación `[número]`

> Nota: enfocado a relojería de gama media-alta (Tudor, Omega, Longines,
> Seiko, Hamilton...). La verificación se basa en marca + modelo + papeles.

**Calzado (hombre/mujer) — filtros (estándar):** marca `[texto]`,
talla `[texto]`, tipo `[lista]`: zapatillas / zapatos / botas / sandalias;
color `[texto]`.

**Ropa superior / inferior / vestidos / abrigos — filtros (estándar):**
marca `[texto]`, talla `[texto]`, color `[texto]`, material `[texto]`.

**Bolsos — filtros (estándar):** marca `[texto]`, tipo `[lista]`: bandolera /
mochila / tote / mano; color `[texto]`.

**Joyería — filtros (estándar):** tipo `[lista]`: anillo / collar / pendientes
/ pulsera; material `[texto]`.

**Gafas de sol — filtros (estándar):** marca `[texto]`, color `[texto]`.

---

### CATEGORÍA 3 — ELECTRÓNICA

```
Electrónica
├── Informática y telefonía (grupo)
│   ├── Móvil / smartphone
│   ├── Portátil
│   ├── Ordenador sobremesa
│   └── Tablet
├── Imagen y sonido (grupo)
│   ├── Cámara de fotos
│   ├── Televisión
│   └── Audio (altavoces, auriculares, hi-fi)
├── Videojuegos (grupo)
│   ├── Consola
│   └── Videojuego
└── Accesorios y componentes (grupo)
    └── Accesorios (fundas, cargadores, componentes PC...)
```

**Móvil / smartphone — filtros (estándar):** marca `[texto]`,
modelo `[texto]`, capacidad `[texto]` (64GB, 256GB...), color `[texto]`.

**Portátil — filtros (estándar):** marca `[texto]`, procesador `[texto]`,
RAM `[texto]`, pulgadas `[número]`.

**Ordenador sobremesa — filtros (estándar):** marca `[texto]`,
procesador `[texto]`, RAM `[texto]`.

**Tablet — filtros (estándar):** marca `[texto]`, capacidad `[texto]`,
pulgadas `[número]`.

**Cámara de fotos — filtros (estándar):** marca `[texto]`, tipo `[lista]`:
réflex / sin espejo / compacta / analógica; con objetivo `[lista]`: sí / no.

**Televisión — filtros (estándar):** marca `[texto]`, pulgadas `[número]`,
resolución `[lista]`: HD / 4K / 8K.

**Audio — filtros (estándar):** marca `[texto]`, tipo `[lista]`: altavoces /
auriculares / equipo hi-fi / barra de sonido.

**Consola — filtros (estándar):** marca `[texto]`, modelo `[texto]`.

**Videojuego — filtros (estándar):** plataforma `[texto]`, título `[texto]`,
región `[lista]`: PAL / NTSC.

---

### CATEGORÍA 4 — HOGAR Y JARDÍN

```
Hogar y jardín
├── Mobiliario (grupo)
│   ├── Sofá
│   ├── Mesa
│   ├── Silla
│   └── Armario / almacenaje
├── Electrodomésticos (grupo)
│   ├── Grandes (lavadora, frigorífico, horno...)
│   └── Pequeños (cafetera, aspiradora...)
└── Decoración y jardín (grupo)
    ├── Decoración
    └── Jardín y exterior
```

**Sofá / Mesa / Silla / Armario — filtros (estándar):** material `[texto]`,
color `[texto]`, plazas o dimensiones `[texto]`.

**Electrodomésticos — filtros (estándar):** marca `[texto]`,
tipo `[texto]`, eficiencia energética `[texto]`.

**Decoración / Jardín — filtros (estándar):** tipo `[texto]`,
material `[texto]`.

---

### CATEGORÍA 5 — DEPORTE Y OCIO

```
Deporte y ocio
├── Ciclismo (grupo)
│   └── Bicicleta
├── Material deportivo (grupo)
│   ├── Fitness y gimnasio
│   ├── Deportes de equipo
│   └── Deportes de montaña / agua
└── Camping y aire libre (grupo)
    └── Material de camping
```

**Bicicleta — filtros (estándar):** tipo `[lista]`: montaña / carretera /
urbana / eléctrica / BMX; marca `[texto]`; talla de cuadro `[texto]`;
tamaño de rueda `[texto]`.

**Material deportivo — filtros (estándar):** deporte `[texto]`,
marca `[texto]`, tipo de artículo `[texto]`.

**Camping — filtros (estándar):** tipo `[texto]`, marca `[texto]`.

---

### CATEGORÍA 6 — COLECCIONISMO Y ARTE

```
Coleccionismo y arte
├── Música física (grupo)
│   ├── ★ Vinilo          [RAMA PROFUNDA]
│   └── CD / casete
├── Cómics y libros (grupo)
│   ├── Cómic / tebeo
│   └── Libro de colección
├── Numismática y filatelia (grupo)
│   ├── Monedas
│   └── Sellos
└── Otros coleccionables (grupo)
    ├── Antigüedades
    └── Cromos / cartas coleccionables
```

**★ Vinilo — filtros (rama profunda):**
- Artista `[texto]`
- Álbum / título `[texto]`
- Sello discográfico `[texto]`
- Año de edición `[número]`
- País de prensado `[lista]` (los coleccionistas distinguen ediciones por país)
- Formato `[lista]`: LP / EP / single / box set
- Tamaño `[lista]`: 12" / 10" / 7"
- Estado del disco `[lista]`: M / NM / VG+ / VG / G (escala Goldmine)
- Estado de la portada `[lista]`: M / NM / VG+ / VG / G
- Precio mín / máx `[número]` (universal)

> Nota: la identificación por artista + álbum + sello + año + país es muy
> precisa. Es ideal para el extractor y para el filtrado fino.

**CD / casete — filtros (estándar):** artista `[texto]`, título `[texto]`,
año `[número]`.

**Cómic / tebeo — filtros (estándar):** título `[texto]`, número `[texto]`,
editorial `[texto]`, idioma `[texto]`.

**Libro de colección — filtros (estándar):** título `[texto]`,
autor `[texto]`, editorial `[texto]`, año `[número]`.

**Monedas — filtros (estándar):** país `[texto]`, año `[número]`,
material `[texto]`.

**Sellos — filtros (estándar):** país `[texto]`, año `[número]`,
temática `[texto]`.

**Antigüedades — filtros (estándar):** tipo `[texto]`, época `[texto]`,
material `[texto]`.

**Cromos / cartas — filtros (estándar):** colección `[texto]`,
tipo `[texto]`, estado `[lista]` (universal).

---

### CATEGORÍA 7 — INSTRUMENTOS MUSICALES

```
Instrumentos musicales
├── Cuerda (grupo)
│   ├── Guitarra eléctrica
│   ├── Guitarra acústica / clásica
│   ├── Bajo
│   └── Otros (violín, ukelele...)
├── Teclado (grupo)
│   ├── Piano / teclado
│   └── Sintetizador
├── Viento y percusión (grupo)
│   ├── Viento
│   └── Percusión / batería
└── Equipo y accesorios (grupo)
    ├── Amplificadores
    ├── Pedales y efectos
    └── Accesorios (cuerdas, fundas...)
```

**Guitarra eléctrica / acústica / bajo — filtros (estándar):**
marca `[texto]`, modelo `[texto]`, tipo `[texto]`, año `[número]`,
zurdo/diestro `[lista]`: diestro / zurdo.

**Piano / teclado / sintetizador — filtros (estándar):** marca `[texto]`,
modelo `[texto]`, número de teclas `[número]`.

**Viento / percusión — filtros (estándar):** tipo de instrumento `[texto]`,
marca `[texto]`.

**Amplificadores / pedales — filtros (estándar):** marca `[texto]`,
modelo `[texto]`, tipo `[texto]`.

---

### CATEGORÍA 8 — NIÑOS Y BEBÉS

```
Niños y bebés
├── Ropa infantil (grupo)
│   ├── Ropa bebé (0-3 años)
│   └── Ropa niño (3-12 años)
├── Juguetes (grupo)
│   └── Juguetes
└── Equipamiento (grupo)
    ├── Carritos y sillas de coche
    └── Mobiliario infantil
```

**Ropa infantil — filtros (estándar):** talla / edad `[texto]`,
marca `[texto]`, género `[lista]`: niño / niña / unisex.

**Juguetes — filtros (estándar):** tipo `[texto]`, marca `[texto]`,
edad recomendada `[texto]`.

**Carritos y sillas de coche — filtros (estándar):** tipo `[lista]`:
carrito / silla de coche / cuna de viaje; marca `[texto]`.

**Mobiliario infantil — filtros (estándar):** tipo `[texto]`,
material `[texto]`.

---

### CATEGORÍA 9 — OTROS

Cajón de sastre. Cualquier producto que no encaje en las 8 anteriores.
Solo usa los **filtros universales** (texto, precio, país, estado).
Garantiza que ninguna búsqueda se quede sin respuesta.

---

## 4. Resumen para implementación

- **Categorías**: 8 + "Otros".
- **Estructura**: 4 niveles (categoría → grupo → tipo → filtros).
- **Filtros universales**: texto, categoría, precio, país, estado. Aplican a todo.
- **Ramas profundas (★)**: Coche, Reloj, Vinilo. Filtros aplicados a fondo por
  los scrapers.
- **Ramas estándar**: 3-4 filtros propios además de los universales.
- **Piezas/accesorios**: siempre en un grupo aparte, nunca mezclado con el
  producto completo.
- **Comportamiento por defecto**: filtro vacío = no se descarta nada por él.
- **Regla anti-basura (heredada del bug de coches)**: descartar anuncios sin
  precio o con precio 0 €.

## 5. Notas para Claude Code

Esta taxonomía sustituye al `SearchFilters` plano anterior. El nuevo modelo
debe representar la jerarquía de 4 niveles, no una lista plana de campos.
Sugerencia de enfoque (a validar al implementar): una estructura de datos
(diccionario o ficheros de configuración) que describa el árbol, de forma que
añadir una categoría, un grupo o un tipo de producto sea editar esa estructura
y no reescribir el esquema ni el extractor. El extractor debe primero situar la
búsqueda en categoría → grupo → tipo, y después rellenar los filtros de ese tipo.
Los filtros que un scraper no sepa aplicar en una plataforma concreta se aplican
en el filtro post-scraping; los que no se puedan aplicar en ningún sitio se
guardan como contexto pero no descartan resultados.
