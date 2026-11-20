# Tres alternativas de proceso

**Fecha:** 2026-11-06 · Implementadas en `motor.py` (`_proceso_A_grilla`, `_proceso_B_contenido`,
`_proceso_C_imagen`) y comparadas en la galería G01 (1°–4° A, 5°–8° B, 9°–12° C), con el
mismo contenido.

Las tres comparten lo que no se discute:

- **Colores:** salen de los tokens UB-3 por rol.
- **Logo:** lockups oficiales leídos de `Exportables`.
- **Tipografía:** Inter y JetBrains Mono, con rasgos `cv11 ss01 ss03`.
- **Espaciado:** múltiplos de 4 px.
- **Verificación:** la misma al final.

Lo que cambia es **qué decide primero** y, por lo tanto, quién se adapta a quién.

Leyenda de «Manual»:

- **sí:** valor fijo, no es slider.
- **parcial:** el manual acota las opciones o pone un mínimo.
- **no:** decisión de diseño libre dentro de UB-3.

## A · Grilla primero

La grilla manda y el contenido se acomoda.

| Paso | Parámetro | Tipo | Defecto | Manual |
|---|---|---|---|---|
| 1. Formato y modo | `formato` | opción | vertical (1080×1350) | no |
| | `modo` | opción | oscuro | no |
| | roles de color → tokens | regla | `roles_color` del esquema | **sí** |
| | `fondo_portada` | booleano | false | **parcial** (solo slide) |
| 2. Grilla | `margen_proporcional` | decimal (× lado menor) | 0,06 | **parcial** (múltiplo de 4) |
| | `columnas` · `filas` | entero | 6 · 8 | no |
| | `medianil_proporcional` | decimal | 0,024 | **parcial** (múltiplo de 4) |
| | `modulo_proporcional` | decimal | 0,0075 | **parcial** (múltiplo de 4) |
| 3. Zonas por celdas | `columnas_texto` | entero | 4 | no |
| | `columnas_titulo` | entero | 0 (= texto) | no |
| | `alineacion` | opción | izquierda | no |
| | `ilustracion_zona` | opción | derecha_inferior | no |
| | `filas_ubicacion` | opción | bajo_titulo | no |
| 4. Tamaños | `texto_minimo_css` | decimal (px CSS) | 11 | no |
| | `escala_valor` · `escala_numero` | decimal | 1,27 · 1,27 | no |
| | `escala_kicker` · `escala_subtitulo` · `escala_cta` | decimal | 1,0 | no |
| | `titulo_altura_relativa` | decimal (× alto) | 0,08 | no |
| | `titulo_ancho_max` | decimal | 0,96 | no |
| | familias y peso de titulares | regla | Inter 600 · JetBrains Mono | **sí** |
| | `titulo_tracking_em` · `titulo_interlineado` | decimal | −0,035 · 0,96 | no |
| 5. Pila de texto | `densidad_texto` | opción | media | no |
| | `espacio_*` | entero (módulos) | 4 · 5 · 6 · 5 | **parcial** (múltiplo de 4) |
| | `fila_*` | entero (módulos) | 3 · 1 · 3 · 2 · 3 | **parcial** (múltiplo de 4) |
| | filete | regla | 1 px | **sí** |
| | `texto_interlineado` | decimal | 1,3 | no |
| 6. Ilustración o imagen en su celda | `ilustracion_alineacion` · `ilustracion_escala` | opción · decimal | inferior · 0,92 | no |
| | `ilustracion_minimo_rel` | decimal | 0,22 | no |
| | `imagen_fuente` | referencia | null | no |
| | `imagen_encaje` | opción | sin_imagen | no |
| | `imagen_foco` | par | [0,5; 0,5] | no |
| | `imagen_radio` | opción | 8 | **parcial** (0 u 8 px) |
| 7. Pie | `logo_composicion` | opción | "01" | **sí** (archivo oficial; 02 en portadas) |
| | `logo_variante` | opción | auto (según fondo real) | **sí** |
| | `logo_altura_relativa` | decimal | 0,041 | **parcial** (ancho ≥ 120 px) |
| | `logo_posicion` | opción | inferior_izquierda | no |
| | `cta_visible` | booleano | true | no |
| | dominio | regla | umbralbim.io | **sí** |
| 8. Decoración y verificación | `trama_*` · `cruces_*` · `chip_*` | varios | ver esquema | no |
| | verificación UB-3 | regla | contraste ≥ 4,5:1 y resto de reglas | **sí** |

**Fuerte en:** coherencia entre formatos y entre piezas de una serie; todo cae en celdas, nada flota.

**Débil en:** cuando el contenido no cabe en sus celdas, el motor achica el título (A3: de 111 a 94 px) o parte líneas. Además, una celda puede quedar más grande que lo que contiene.

## B · Contenido primero

El texto define la jerarquía y la grilla se deriva de lo que el texto mide.

| Paso | Parámetro | Tipo | Defecto | Manual |
|---|---|---|---|---|
| 1. Contenido y densidad | contenido (kicker, título, filas, cuerpo, llamado) | texto | `contenido/*.yaml` | **parcial** (marca escrita, dominio) |
| | `densidad_texto` | opción | media | no |
| 2. Escala tipográfica | `texto_minimo_css` + `escala_*` | decimal | 11 · 1,0–1,27 | no |
| | `texto_ancho_max_relativo` | decimal | 0,62 | no |
| | `titulo_altura_relativa` (tope) | decimal | 0,08 | no |
| 3. Medir el bloque → grilla derivada | `columnas` · `medianil_proporcional` | entero · decimal | 6 · 0,024 | **parcial** (múltiplo de 4) |
| | columnas que toma el texto | derivado | — | — |
| 4. Ubicar las filas | `filas_ubicacion` | opción | bajo_titulo | no |
| 5. Ilustración en la zona libre mayor | `ilustracion_zona` | opción | auto (derecha, debajo o entre título y filas) | no |
| | `ilustracion_minimo_rel` | decimal | 0,22 (si la zona es menor, no hay ilustración) | no |
| 6. Pie y verificación | iguales al paso 7 y 8 de A | | | **sí / parcial** |

**Fuerte en:** legibilidad y jerarquía con cualquier cantidad de texto. El título crece hasta donde el texto lo permite (B4: 166 px en 16:9), y una ilustración que quedaría diminuta se omite (B1).

**Débil en:** dos piezas de una misma serie pueden derivar grillas distintas, porque la grilla depende del texto. La ilustración va donde sobra espacio, no donde la composición la pide.

## C · Imagen primero

La imagen define la zona libre y el texto se ubica ahí.

| Paso | Parámetro | Tipo | Defecto | Manual |
|---|---|---|---|---|
| 1. Imagen y encaje | `imagen_fuente` | referencia (`imagenes.yaml`) | null | no |
| | `imagen_encaje` | opción | fondo_completo_con_velo o sangrado_lateral | no |
| | `imagen_foco` | par | [0,5; 0,5] | no |
| 2. Zona libre | `zona_libre` | opción | auto (franja con menos detalle medido) | no |
| | `zona_libre_fraccion` | decimal | 0,55 | no |
| 3. Texto en la zona | tamaños de A/B y `columnas` | | | **sí / parcial** |
| | chip | regla | en la esquina de la zona de lectura | no |
| 4. Velo plano | `velo_opacidad` | decimal | 0,55 | **sí** (plano, sin degradado) |
| | `velo_alcance` | opción | zona_lectura | no |
| | `velo_auto` | booleano | true | no |
| | contraste mínimo | regla | 4,5:1 sobre el fondo real | **sí** |
| 5. Logo según el fondo | `logo_variante` | opción | auto | **sí** |
| | `logo_altura_relativa` | decimal | 0,041 | **parcial** |

**Fuerte en:** piezas donde la imagen es la protagonista. La legibilidad queda garantizada por medición, no por ojo: el velo sube lo justo (C2 0,55; C4 0,71) y siempre es plano.

**Débil en:** depende de la imagen.
- **Imagen sin zona limpia:** el velo casi tapa la imagen. C1 necesitó 0,96 en la franja de texto: una etiqueta gris sobre crema no llega a 4,5:1 con menos.
- **Formato vertical:** la franja con menos detalle puede ser angosta. En C2, el modo automático eligió la columna derecha, con un título de 78 px, y el pack fija la zona superior y un velo uniforme.

## Comparación

| | A · Grilla | B · Contenido | C · Imagen |
|---|---|---|---|
| Decide primero | la estructura | el texto | la imagen |
| Se adapta | el contenido (achica o parte líneas) | la grilla (columnas derivadas) | el texto (zona y velo) |
| Riesgo | celdas vacías o títulos achicados | series poco homogéneas | imagen tapada o texto angosto |
| Mejor para | series, carruseles y slides | piezas con muchos datos | portadas e imagen de campaña |
| En G01 | 1°–4° | 5°–8° | 9°–12° |

**Hipótesis para conversar (no decidida):** las tres ya comparten la escala desde el texto mínimo legible, que viene de B, y la geometría de grilla, que viene de A. Una skill final podría usar A para series, B cuando el contenido varía mucho y C cuando hay imagen protagonista: el tipo de pieza elegiría el proceso. Las elecciones de David en `decisiones.csv` deberían confirmarlo o descartarlo.
