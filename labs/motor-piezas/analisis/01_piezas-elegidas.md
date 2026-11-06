# Análisis de las seis piezas elegidas

**Fecha:** 2026-11-06 · **Laboratorio:** motor paramétrico de piezas · **Rama:** `rick/motor-piezas-lab`

Elegidas por David: v1 1°; v2 1°, 12°, 20°, 22° y 24°. Su comentario, textual
(`00_insumos/resumen_elecciones_plantillas.md`):

> «del primer lote el que se ve mejor por distribución espacial es el 1, pero falta ajuste
> espacial de diseño gráfico […] me gusta como se ve el 12, 22, 24, 20, pero les falta trabajo
> en cuanto a diseño gráfico, decisiones de diseño, composición…»

Cada problema se midió y se convirtió en un parámetro del esquema v0.2
(`parametros.borrador.yaml`). Las cifras salen de `analisis/medir_piezas.py`:

- v2: cajas reales en Chrome, con las fuentes de su propio paquete.
- v1: valores declarados en su SVG, porque su paquete no trae Bebas ni Oswald.
- Contraste sobre imagen: percentil 10 del PNG original bajo cada texto.
- Contraste sobre fondo plano: color contra color.

El detalle completo está en `analisis/medidas_elegidas.json`.

## Resumen medido

| Pieza | Formato | Título | Valor de fila en el celular | Texto más chico en el celular | Tamaños distintos | Vacío mayor (columna izquierda) | Contraste más bajo | Faltas UB-3 |
|---|---|---|---|---|---|---|---|---|
| v1 1° | 1:1 claro | 140 px (Bebas) | 7,9 px CSS | 4,0 px CSS | 9 | 33 % del alto | 2,82:1 (kicker turquesa) | Bebas y Oswald, `umbralbim.com`, wordmark escrito como texto, texto turquesa sobre claro |
| v2 1° | 1:1 claro | 100 px | 7,2 px CSS | 4,0 px CSS | 8 | 37 % del alto | 2,82:1 (números 01–03) | números turquesa `#0FA994` sobre claro |
| v2 12° | LinkedIn oscuro | 76 y 64 px | — | 3,6 px CSS | 5 | 27 % del alto | 6,69:1 | `--ub-bg-cover` fuera de una presentación |
| v2 20° | 4:5 oscuro + S17b | 104 px | 7,2 px CSS | 4,0 px CSS | 8 | 38 % del alto | 7,24:1 | — |
| v2 22° | 4:5 oscuro + S16b | 104 px | — | 4,0 px CSS | 4 | (imagen a sangre) | 6,91:1 | velo en degradado |
| v2 24° | 16:9 oscuro + S2b | 112 px | — | 7,3 px CSS en notebook; 2,2 en celular | 4 | 32 % del alto | **4,49:1 (bajada)** | velo en degradado; bajada bajo 4,5:1 |

Lectura en el celular: 1080 px de pieza se ven a ~390 px CSS, así que 1 px CSS equivale a 2,77 px de lienzo.
Un valor de 20 px queda en 7,2 px CSS y una etiqueta de 12 px, en 4,3. El texto cómodo empieza en 11–14 px CSS.

## Hallazgos transversales

1. **Las filas no se leen en el celular.** Es la hipótesis del brief, confirmada en las cinco piezas con datos. Parámetro: `texto_minimo_css` (11 por defecto), con todos los tamaños de texto como escala de ese mínimo.
2. **Tamaños casi iguales.** La v2 usa 11, 12, 13, 14 y 15 px para chip, etiquetas, kicker, subtítulo y llamado: cinco escalones que no se distinguen y suman ruido. Parámetros `escala_*` (1,0 por defecto: un solo tamaño de etiqueta).
3. **Márgenes en px fijos y desiguales.** En la v2 el margen es de 64 px a los lados y 56 abajo en 1:1 y 4:5; de 56 y 44 en LinkedIn; de 88 y 80 en 16:9. No escala con el formato ni respeta el mismo margen en los cuatro lados. Parámetro: `margen_proporcional` (fracción del lado menor, múltiplo de 4). `margen_inferior_proporcional` existe solo para poder reproducir la v2.
4. **La isometría y la imagen flotan.** Se colocan por coordenadas sueltas. El borde inferior de la isometría queda a 167 px (v2 1°) y 35 px (12°) de cualquier línea de texto. Su borde derecho queda 101 px (1°) y 90 px (12°) antes del margen: no se alinea con nada. Parámetros: `ilustracion_anclaje: zona_grilla`, `ilustracion_zona` e `imagen_encaje: caja_alineada_grilla | sangrado_lateral`.
5. **La cruz de registro superior derecha pisa el chip «EJEMPLO»** en todas las piezas v2: el chip termina justo en la línea de las cruces. Parámetro: `chip_ancla: caja`.
6. **Texto turquesa sobre claro.** Ocurre en la v2 1° (números) y en la v1 (kicker, subtítulo, números y llamado), con 2,82:1. UB-3 lo prohíbe; el rol `numero` pasa a `acento_texto` (`--ub-primary-text`, 9,63:1).
7. **Velo en degradado.** En 22° y 24°, `generate.py` hornea en la imagen un velo que va de 0,82 a 0,28 de opacidad de izquierda a derecha (`prepare_mj`, modo `fullbleed`). Es un degradado, y UB-3 los prohíbe en piezas corporativas. Además no protege la lectura donde la imagen es clara: en la 24° la bajada queda en 4,49:1. Parámetros: `velo_opacidad`, plano y con ajuste automático (`velo_auto`) hasta 4,5:1 medido, y `velo_alcance`.
8. **El fondo de portada (`#1A1A2E`) está en la portada LinkedIn 12°.** El CSS lo permite solo en portadas 16:9, divisores y portada de documento impreso (§1b). Parámetro: `fondo_portada`, que la verificación rechaza fuera de `slide`.
9. **La v2 dibuja los títulos con Inter Display, no con la Inter del Design System.** Su Inter Variable 4.001 tiene eje de tamaño óptico (14–32) y, a ≥ 32 px, Chrome y CairoSVG usan el corte Display, un 3,8 % más estrecho. Las woff2 canónicas son el corte de texto. Con tamaño óptico 14, la variable mide exactamente lo mismo que la canónica (564,8 px de «WORKSHOP» a 100 px). **Decisión pendiente para David:** si los titulares deben usar Inter Display, hay que sumarla al Design System; hoy no está.
10. **Fecha de ejemplo inconsistente.** Las piezas dicen «Jueves 20 nov 2026», pero el 20-nov-2026 es viernes. El contenido de la galería usa «Jueves 19 nov 2026». El control de réplica conserva el texto original.

## Pieza por pieza

### v1 1° · save the date 1:1 claro (primer lote)

**Por qué gustó:** el título grande arriba a la izquierda, las filas numeradas debajo y la isometría a la derecha forman una distribución clara. Es la estructura que la v2 heredó.

**Valores como parámetros:**

| Parámetro | Valor |
|---|---|
| `formato` | cuadrado |
| `modo` | claro |
| `margen_proporcional` | 0,067 (72 px) |
| `titulo_altura_relativa` | ≈0,09 (Bebas 140 px) |
| `texto_minimo_css` | 4,0 |
| `escala_valor` | 22/11 |
| `ilustracion_anclaje` | libre |

**Exploración, no plantilla.** Rompe UB-3 en cuatro puntos:
- Usa Bebas Neue y Oswald.
- Usa el dominio `umbralbim.com`.
- Recompone el wordmark como texto (`#wordmark` junto al isotipo) en lugar de usar el lockup oficial.
- Pone texto turquesa sobre claro.

La banda roja de «EJEMPLO» a todo el ancho ya se corrigió en la v2.

**Qué se conserva:** la distribución, que es lo que David elogió. Se lleva a Inter con los parámetros de la v2 1°.

### v2 1° · STD-1080x1080-CLA

**Valores como parámetros:** completos en `packs/R1-replica-v2-01.yaml`. El motor regenera la pieza solo desde ese pack (ver «Control» más abajo). Los principales:

| Parámetro | Valor | Equivale a |
|---|---|---|
| `margen_proporcional` | 0,0593 | 64 px |
| `margen_inferior_proporcional` | 0,0519 | 56 px |
| `titulo_altura_relativa` | 0,0673 | 100 px |
| `texto_minimo_css` | 4,33 | etiqueta de 12 px |
| `escala_valor` | 1,67 | 20 px |
| `escala_numero` | 2,17 | 26 px |
| `filas_ancho_relativo` | 0,463 | 500 px |
| `ilustracion_anclaje` | libre, centro (0,70; 0,46), escala 1,28 | — |

**Ajuste espacial propuesto (implementado en la galería G01 como 1°, 5° y 9°):**

| Parámetro | v2 | Propuesto | Por qué |
|---|---|---|---|
| `texto_minimo_css` | 4,33 | 11 | filas legibles en el celular |
| `escala_valor` / `escala_numero` | 1,67 / 2,17 | 1,27 / 1,27 | menos saltos de tamaño, número y valor del mismo peso visual |
| `escala_kicker`, `escala_subtitulo`, `escala_cta` | 1,25 / 1,17 / 1,08 | 1,0 | un solo tamaño de etiqueta |
| `margen_inferior_proporcional` | 0,0519 | (igual al margen) | mismo margen en los cuatro lados |
| `ilustracion_anclaje` | libre | zona_grilla, `derecha_inferior` | la isometría cae en una celda, alineada abajo con la grilla |
| `columnas_titulo` / `columnas_texto` | — | 6 / 3 | título a todo el ancho; filas e isometría comparten el resto |
| `chip_ancla` | linea_cruces | caja | el chip deja de pisar la cruz |
| rol `numero` | `acento` | `acento_texto` | 2,82:1 → 9,63:1 |

### v2 12° · LI-OSC (portada LinkedIn oscura)

**Valores como parámetros:**

| Parámetro | Valor |
|---|---|
| `formato` | linkedin |
| `modo` | oscuro |
| `fondo_portada` | true (`#1A1A2E`) |
| `margen_proporcional` | 0,089 (56 px de 627) |
| `titulo_altura_relativa` | 0,088 la línea 1 y 0,074 la línea 2 (76 y 64 px: **dos tamaños en un mismo título**) |
| `texto_minimo_css` | 3,6 |
| `logo_composicion` | "02" |
| `ilustracion_anclaje` | libre |

**Problemas:**
- Usa el azul de portada fuera de una presentación.
- Usa dos cuerpos en el título.
- La isometría flota.
- El texto más chico, a 3,6 px CSS, no se lee en el feed del celular.

**Ajuste propuesto (G01 3°, 7° y 11°):**
- Fondo carbón `--ub-bg` en lugar del azul de portada.
- Un solo cuerpo de título (`titulo_altura_relativa: 0,13`).
- `filas_ubicacion: columna_derecha`: en apaisado, los datos van al lado del título y no debajo.
- `modulo_proporcional: 0,012`, para que el ritmo vertical no baje de 8 px.
- `logo_altura_relativa: 0,06`.

### v2 20° · TAL-1350-OSC-V-S17b (taller 4:5 + imagen constructivista)

**Valores como parámetros:**

| Parámetro | Valor |
|---|---|
| `formato` | vertical |
| `modo` | oscuro |
| `titulo_altura_relativa` | 0,056 |
| `texto_minimo_css` | 4,3 |
| imagen | caja libre de 440 × 560 px en (584, 360), radio 8 y velo uniforme del 16 % |

**Problemas:**
- La imagen es una caja suelta: su borde superior (y = 360) queda entre el subtítulo (344) y el primer filete (392), sin alinearse con ninguno.
- Su margen derecho es de 56 px, contra 64 a la izquierda.
- Ocupa el 41 % × 41 % del lienzo.
- Bajo las filas queda un vacío del 38 % del alto.

**Ajuste propuesto (G01 2°):**
- `imagen_encaje: sangrado_lateral`: la imagen ocupa celdas de la grilla desde la fila siguiente a la cabecera hasta la fila del pie, y sangra al borde derecho.
- Título a todo el ancho (`columnas_titulo: 6`) y filas en tres columnas.
- `imagen_foco: [0,62; 0,5]`, para que el brazo robótico quede en cuadro.

### v2 22° · CAR-OSC-V-S16b (carrusel 4:5 + puerta pixel art)

**Valores como parámetros:**

| Parámetro | Valor |
|---|---|
| `formato` | vertical |
| `modo` | oscuro |
| `imagen_encaje` | fondo completo |
| velo | degradado de 0,82 a 0,28 |
| `titulo_altura_relativa` | 0,056 (cuatro líneas de 104 px, interlineado 1,08) |
| `titulo_linea_acento` | ultima |

**Problemas:**
- El velo es un degradado.
- El haz de luz de la puerta cruza el título.
- El título, a 0,056 del alto, es chico para una portada de carrusel.

Contraste medido: 6,91:1 (cumple).

**Ajuste propuesto (G01 10°):**
- `zona_libre: superior` y `velo_alcance: completo`: un velo plano y uniforme, con opacidad calculada para 4,5:1.
- Título a todo el ancho, de 147 px.
- La puerta sigue visible bajo el bloque de texto.

### v2 24° · SLC-OSC-V-S2b (portada 16:9 + abstracto)

**Valores como parámetros:**

| Parámetro | Valor |
|---|---|
| `formato` | slide |
| `modo` | oscuro |
| `fondo_portada` | true |
| velo | degradado |
| `titulo_altura_relativa` | 0,075 |
| `texto_minimo_css` | 7,3 a 1280 px CSS |
| `logo_composicion` | "02" |

**Problemas:**
- El título es chico para 16:9.
- No hay zona de lectura protegida: la bajada mide 4,49:1, bajo AA.
- Kicker y subtítulo de 16 px se pierden contra un título de 112 px.

**Ajuste propuesto (G01 4°, 8° y 12°):**
- `titulo_altura_relativa: 0,12` (149 px tras ajustarse a la zona).
- `velo_alcance: zona_lectura`: una franja plana alineada a la grilla que sangra al borde, con opacidad automática (0,71).
- `texto_minimo_css: 14`.
- `escala_subtitulo: 1,6`.
- `filas_ubicacion: al_pie`.

## Control: el motor regenera la v2 1° solo desde un pack

`packs/R1-replica-v2-01.yaml` → `comparar_replica.py`. Ambas piezas se renderizan en el mismo Chrome.

- **Posición:** todas las cajas quedan dentro de ±3 px en vertical y ±4,3 px en horizontal (el chip). Isometría y logo coinciden exactamente.
- **Píxeles:** la diferencia media es de 5,6/255. Como referencia, el mismo SVG v2 renderizado con CairoSVG y con Chrome difiere en 6,4/255.
- **Anchos:** los títulos miden 14–17 px más con la fuente canónica. Es el hallazgo 9 (Inter Display frente a Inter de texto), no un error de composición.
- **Verificación:** marca sola la falta UB-3 de la v2 (números turquesa, 2,82:1) y el choque entre el chip y la cruz. Por eso el control figura como exploración.
