# Laboratorio · Motor paramétrico de piezas gráficas (Umbral BIM)

Prototipo para producir afiches, portadas, carruseles y slides de Umbral BIM a partir
de **packs de parámetros** probados, como una definición de Grasshopper con sliders:
entra el contenido de una pieza (por ejemplo, los datos de un evento), se elige un pack
y sale la pieza. Si no convence, se prueba otro pack.

Estado: **laboratorio**. Nada de esta carpeta es producción ni skill publicada. La skill
final se versionará en el registro de skills mediante PR, cuando exista acceso.

## Reglas del laboratorio

- Un solo escritor: la sesión de Claude Code en TARRO escribe en `labs/motor-piezas/`
  de esta rama y en sus propias subcarpetas de Drive (`07_Motor de piezas/` excepto
  `00_insumos/`, que es del Director Comercial y Marketing).
- Sin escrituras en Notion. La fila del experimento en «Desarrollos y Cambios de
  Sistema» la lleva el registrador (Claude Code VPS).
- Sin gasto: la exploración de maquetación es SVG/HTML. Antes de usar créditos de
  Magnific o Midjourney se informa cuántos y se espera el OK de David.
- Entrega: PR en borrador sin merge + nota de traspaso en la ficha
  `.agents/tasks/2026-11-06-001-motor-piezas-lab.md` (qué se probó, resultado, qué
  aplicar, riesgos, cómo revertir). Revisa el coordinador provisorio de UAS (Rick GPT);
  producción solo con GO de David.
- Insumos con licencia o pesados (fuentes, lockups, imágenes generadas) no se suben a
  git: se leen desde Drive o desde `insumos/` local, que está ignorado.

## Arquitectura

### Dos capas separadas

1. **Maquetación (determinista).** Formato, grilla, márgenes, escala tipográfica,
   paleta, contraste, jerarquía y posición del logo. SVG/HTML → PNG. El mismo pack
   produce siempre la misma pieza. Base: `generate.py` de la v2 (Drive), que hoy tiene
   los valores escritos en el código; el primer trabajo es sacarlos a parámetros.
2. **Imagen (generativa).** Ilustración o fondo hecho con Midjourney, Magnific u otro.
   Entra como un hueco con proporción y modo de encaje. Cada imagen se registra con
   herramienta, modelo, prompt, referencias de estilo (`--sref`, perfil o preset),
   semilla si existe y proporción. Mover un parámetro de maquetación nunca obliga a
   regenerar la imagen.

### Reglas fijas del Manual de Marca UB-3 (no son sliders)

- Tipografías: solo Inter y JetBrains Mono.
- Logo: lockups oficiales, nunca redibujados. Dominio `umbralbim.io`.
- Turquesa como acento; nunca como texto sobre fondo claro (usar el token de texto de
  marca para kickers en claro).
- Sin brillos ni degradados en piezas corporativas; espaciado en múltiplos de 4.
- Lo que rompa estas reglas se rotula como exploración, no como pieza.

### Pipeline (tres alternativas a comparar en la primera entrega)

- **A · Grilla primero:** la grilla manda y el contenido se acomoda.
- **B · Contenido primero:** tipo de pieza y cantidad de texto definen la jerarquía y
  luego la grilla.
- **C · Imagen primero:** la ilustración define la zona libre y el texto se ubica ahí.

### Esquema de parámetros

Borrador inicial en `parametros.borrador.yaml`. Cada parámetro declara capa, tipo,
opciones o rango, valor por defecto y si lo fija el manual. Un **pack** es un conjunto
de valores con nombre, el tipo de contenido para el que funciona y la decisión de David
que lo aprobó.

### Registro de decisiones

`decisiones.csv`: número de pieza, código, pack, comentario textual de David, fecha.
Es el insumo para aprender qué packs funcionan para qué contenido.

## Hipótesis de partida (de las piezas elegidas por David)

Elegidas: v1 1°; v2 1°, 12°, 20°, 22° y 24°. Comentario de David: buena distribución,
falta ajuste espacial y decisiones de diseño gráfico.

- El bloque de título funciona; las filas de fecha, hora y lugar quedan demasiado chicas
  para leerse en el celular.
- La isometría flota sin relación con la grilla y deja vacíos grandes abajo.
- En 20° la imagen está pegada como caja; en 22° y 24° funciona mejor a lienzo completo,
  pero en 24° el título queda chico y sin zona de lectura protegida.
- Los márgenes son fijos en píxeles en todos los formatos en vez de proporcionales.

Cada problema debe convertirse en un parámetro.

## Primera entrega (2026-11-06)

| Punto de la ficha | Dónde |
|---|---|
| 1. Análisis de las seis elegidas | `analisis/01_piezas-elegidas.md` (cifras en `analisis/medidas_elegidas.json`, script `analisis/medir_piezas.py`) |
| 2. Tres alternativas de proceso | `analisis/02_alternativas-proceso.md` |
| 3. Esquema y motor | `parametros.borrador.yaml` v0.2 · `motor.py` · control de réplica `packs/R1-replica-v2-01.yaml` + `comparar_replica.py` |
| 4. Galería numerada | `galerias/G01.yaml` → `galeria.py`; publicada en Drive `07_Motor de piezas/01_galerias/2026-11-06_G01/` |
| 5. Registro de decisiones | `decisiones.csv` (una fila por pieza de G01, comentario y fecha vacíos) |

## Paso a paso (desde 2026-11-06)

David pidió avanzar de a un paso: primero acordar los pasos y después crear presets dentro de cada uno, eligiendo antes de pasar al siguiente. Los pasos acordados, en orden:

1. **División:** cómo se parte el lienzo entre texto e imagen.
2. **Jerarquía:** cuánto pesa el título frente a las filas y el pie.
3. **Imagen o ilustración:** a sangre, en caja o isometría.
4. **Protección del texto:** velo, banda o color.
5. **Pie y detalles:** logo, llamado, etiqueta y trama.

El contenido y el formato son entradas, no pasos. Cada galería cambia un solo paso, con 3–4 presets sobre una base fija. Los packs del paso heredan de la base (`hereda:`) y declaran solo lo que cambia.

| Paso | Galería | Base | Presets | Estado |
|---|---|---|---|---|
| 1 · División | `galerias/G02.yaml` · Drive `01_galerias/2026-11-06_G02` | la 12° de G01 con el contraste corregido (`packs/D1`) | mitad, tercio, banda y ele (`divisiones` en el esquema) | **elegido el 2°, tercio** («se ve mejor el 2»), con más contraste abajo a la izquierda |
| 2 · Jerarquía | `galerias/G03.yaml` · Drive `01_galerias/2026-11-06_G03` | el tercio con texto chico y logo a 10:1 (`packs/E1`) | base, datos fuertes, compacta (`pila_anclaje: abajo`) y escala mayor | **elegido el 2°, datos fuertes** |
| 3 · Imagen o ilustración | `galerias/G04.yaml` · Drive `01_galerias/2026-11-06_G04` | datos fuertes con la imagen a sangre bajo velo (`packs/F1`) | a sangre, sangrado lateral, en caja e ilustración (`imagen_encaje`, `imagen_registro: lienzo`) | **elegido el 2°, sangrado lateral** |
| 4 · Protección del texto (color) | `galerias/G05.yaml` · Drive `01_galerias/2026-11-06_G05` (con `01_detalle.jpg`) | sangrado lateral: el texto ya va sobre fondo liso (`packs/H1`) | base, etiquetas blancas, turquesa claro y fondo de portada | espera la elección de David |

Comentarios de David sobre G01 (en `decisiones.csv`):
- **1°:** faltan ajustes de proporción y composición.
- **12°:** destaca por su composición, pero le faltaba contraste en los textos de abajo a la izquierda (medían 4,57–6,28:1).

Corrección desde el motor 0.3: el texto chico sobre imagen apunta a 7:1 (`contraste_sobre_imagen`) y usa los colores de texto claros (`colores_sobre_imagen`). Así el velo de la 12° sube de 0,71 a 0,73 en vez de tapar la imagen.

En G02, David volvió a pedir más contraste abajo a la izquierda en el tercio. El texto chico ya medía 7:1 o más, pero el llamado y el logo quedaban sobre la parte más clara y con más textura de la imagen. Ajustes:
- La base del paso 2 (E1) sube el objetivo a 10:1, con un velo de 0,84.
- El logotipo ahora cuenta para el velo como texto chico.

Si 10:1 se confirma, conviene subirlo a valor por defecto.

G01 se generó con el motor 0.2 (consta en cada `piezas/*.json`). Con el actual, sus zonas no cambian: solo el color del texto chico sobre imagen y la opacidad de los velos de sus piezas C.

## Cómo correr

Requisitos ya presentes en TARRO: Python 3.13 con `playwright`, `Pillow`, `numpy` y `PyYAML`, y Chrome
instalado. Playwright usa ese Chrome; no descarga navegadores. No hace falta CairoSVG.

```bash
python motor.py pieza --pack packs/A1-grilla-cuadrado-claro.yaml --salida salida/prueba
python comparar_replica.py --pack packs/R1-replica-v2-01.yaml --salida salida/prueba
python galeria.py --definicion galerias/G01.yaml              # salida/G01/galeria.html
python galeria.py --definicion galerias/G01.yaml --publicar   # copia a 07_Motor de piezas/01_galerias
python galeria.py --definicion galerias/G02.yaml              # paso 1: divisiones (salida/G02)
python galeria.py --definicion galerias/G03.yaml              # paso 2: jerarquía (salida/G03)
python galeria.py --definicion galerias/G04.yaml              # paso 3: imagen o ilustración (salida/G04)
python galeria.py --definicion galerias/G05.yaml              # paso 4: color del texto, con hoja de detalle (salida/G05)
python catalogar_imagenes.py                                   # regenera imagenes.yaml desde los PNG
python analisis/medir_piezas.py                                # re-mide las seis elegidas
```

## Estructura

```
motor.py               compone desde pack + contenido + tokens; verifica UB-3; SVG y PNG 2x
navegador.py           Chrome sin ventana: mide texto y rasteriza con las fuentes de marca
marca.py               tokens desde colors_and_type.css, contraste WCAG, lockups oficiales
galeria.py             galería numerada (1°, 2°…), hoja 00_preview.jpg, decisiones_<id>.csv
comparar_replica.py    réplica contra original v2, en el mismo Chrome
catalogar_imagenes.py  imagenes.yaml desde los metadatos de cada PNG
parametros.borrador.yaml  esquema: formatos, roles, reglas UB-3 y parámetros
rutas.yaml             rutas de TARRO (marca en Drive, solo lectura)
packs/                 un pack por pieza (valores con nombre; `hereda:` parte de otro pack)
contenido/             textos de ejemplo
galerias/              definición de cada galería
analisis/              análisis de las elegidas y de los procesos
insumos/  salida/      ignorados por git (paquetes extraídos y piezas generadas)
```

El motor lee la marca **en vivo** desde Drive:
- **Colores:** `colors_and_type.css`.
- **Logos:** `02_Logotipo/Exportables/Lockup/`.
- **Fuentes:** woff2 del Design System, que se copian con su licencia OFL junto a cada salida.

Los insumos del Director (`07_Motor de piezas/00_insumos/`) son de solo lectura. De ahí salen la base (`generate.py` portable), los vectores y las favoritas MJ. Sus copias de lockups y fuentes se comprobaron idénticas a las canónicas el 2026-11-06.

## Decisiones pendientes que el laboratorio no toma

1. **Inter Display para titulares.** La v2 los dibujó con el corte Display de Inter Variable 4.001, un 3,8 % más estrecho, sin que nadie lo pidiera. El Design System solo trae el corte de texto. ¿Se suma Display o se queda la canónica?
2. **Acento como texto en oscuro.** El motor usa `#2DD4BF` (`--ub-primary` oscuro) para kickers y números sobre carbón, como la tabla de portadas del Manual §03. El comentario del CSS dice «nunca `color: var(--ub-primary)`». ¿Se confirma o se usa `--ub-primary-text` (`#99F6E4`)? Desde el motor 0.3, el texto chico sobre imagen ya usa `#99F6E4` para llegar a 7:1; la duda sigue abierta para el texto grande y para el texto sobre fondo liso.
3. **Vista supuesta por formato** (`vista_css`): 390 px CSS para redes y 1280 para 16:9. De ahí sale el tamaño mínimo real del texto.
4. **Imágenes MJ ya hechas:** se tratan como fijas. El PNG sí trae prompt, `--v 8.2` y Job ID (ver `imagenes.yaml`); faltan `--sref`, perfil y semilla.
