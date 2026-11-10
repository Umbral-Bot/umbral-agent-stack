# Magnific One y la marca Umbral BIM · camino recomendado

Análisis del 2026-11-10, pedido por David: «revisa en magnific para integrar manual de marca con
magnificone creo que es el cmaino, analiza ye dstuida el mejor camniino para eso, plantillas,
braindings etc enfuncion del manual de la marca». Solo lectura: no se escribió en Magnific y no se
gastaron créditos.

## Conclusión

Magnific One es el camino para las **imágenes**: es el único modelo que aplica un kit de marca
(Magnific cambia a él cuando hay kit). Pero la pieza final no debe salir de Magnific: el texto, el
logo, la grilla y la verificación los pone el motor de piezas. Antes de usarlo hay que corregir el
kit «Umbral BIM», que hoy no tiene prohibiciones, ni el manual, ni un logo vectorial.

## Qué hay hoy

**Kit «Umbral BIM»** (creado el 2026-11-03, de David):
- Bien: la paleta UB-3 (7 colores, con el primario de relleno separado del texto de marca), una
  descripción del sistema leída de `colors_and_type.css` y reglas de movimiento sobrias.
- Falta: **0 prohibiciones**, **0 documentos** (el manual no está cargado) y **0 tipografías**.
- El único logo es un raster del lockup **Claro**, que el propio kit describe «sobre fondo negro»,
  donde no se lee. No hay ninguna marca usable (`logo_marks` vacío).
- Dos plantillas sin probar, «Post LinkedIn» (4:5, fondo claro) y «Portada de reel» (9:16).
  Las dos piden que la imagen traiga el titular y el logo.

**Biblioteca Magnific** (`05_Biblioteca Magnific`, 4 y 5 de noviembre): 152 registros, unos
25.000 créditos.
- **Resultado:** 61 se conservaron, 53 quedaron por corregir y 29 se descartaron.
- **Por corregir:** 38 de las 53 tenían brillo, resplandor o sombra dramática, y 8 usaban el
  turquesa como fondo. Dos extensiones inventaron pseudo-texto.
- **Descartadas:** foto de stock, fotorrealismo con cielo degradado y render 3D: 24 de las 29.
- **Lo conservado:** fondo claro, plano, neutros dominantes, turquesa de acento y espacio libre
  para el texto. Ocho de esas imágenes tienen la «dirección aprobada por David» (G-SITIO, G-AFI).

**Costos** (simulados, sin cobro):
- Una imagen con el kit a 2k: 180 créditos.
- Una grilla de exploración de 8: 250 créditos.
- Saldo actual: 240.000.

**API REST.** Es la que usa el worker de la VPS para Rick (`worker/tasks/magnific.py`). Su
referencia pública ([índice](https://docs.magnific.com/llms.txt)) no expone Magnific One ni
kits de marca, así que el kit se usa desde la app o desde el MCP, no desde la VPS.

## Por qué Magnific no debe hacer la pieza completa

- **El logo.** El manual (§02 y §07) exige el lockup trazado, tomado de `Exportables\`, sin
  rehacerlo. Un modelo de imagen dibuja el logo; no coloca el archivo.
- **El texto.** El motor mide el contraste sobre los píxeles reales, compone en Inter con tildes,
  respeta la grilla de 4 px y los tamaños mínimos. El control de marca de Magnific es el juicio de
  un modelo, no una medición.
- **La evidencia.** La biblioteca ya mostró pseudo-texto en las extensiones.

Reparto: **Magnific One + kit hacen la imagen; el motor hace la pieza.**

## Camino en cuatro pasos

1. **Elegir la línea visual** (decisión de David). Un kit sostiene un estilo, y sus imágenes de
   referencia lo definen.
   - **Isométrica plana y clara** (recomendada): las 8 aprobadas siguen esta línea y es la que
     mejor cumple el manual.
   - **Neovintage** (N1, N3, N4).
   - **La ilustración de Midjourney** que usa hoy el laboratorio.
2. **Corregir el kit.** No gasta créditos, pero escribe en la cuenta de Magnific, así que
   necesita el OK de David.
   - **Seis prohibiciones**, tomadas de las fallas reales: brillo o resplandor; luz y sombras
     dramáticas; degradados; turquesa como fondo; foto de stock, fotorrealismo y render 3D;
     texto, letras, números o logotipos dentro de la imagen. Son el único canal que Magnific
     aplica como prohibición: las reglas escritas en la descripción son solo consejo.
   - **Imágenes de referencia** de la línea elegida, tomadas de las que ya están en Magnific.
   - **Logo:** los SVG oficiales (Oscuro, Claro y Monocromo blanco) en lugar del raster mal
     descrito. No es para que la IA lo dibuje: sirve para que el kit y su control conozcan el
     logo real.
   - **Plantillas:** cambiar las dos actuales por plantillas solo de imagen, con la zona libre
     donde el motor pone el texto.
   - **David, en la app:** subir `Manual de Marca.pdf`. Desde fuera de la app no se pueden subir
     PDF.
3. **Conectar con el motor** (código del laboratorio).
   - **Pedido de imagen.** El motor ya sabe dónde va la imagen en cada formato: puede escribir la
     proporción de esa zona y dónde caerá el texto.
   - **Una imagen maestra por artículo**, recortada por el motor para cada formato: 180
     créditos y no 180 por formato. En su ficha, Magnific One no trae 4:5 entre sus
     proporciones, pero acepta un tamaño exacto; eso queda por probar.
   - **Procedencia:** la imagen entra a `imagenes.yaml` con la creación, el kit, la semilla y los
     créditos.
   - **Última compuerta:** la verificación UB-3 del motor, no el control de Magnific.
4. **Piloto con créditos**, con el OK de David: una grilla de 8 (250) y una imagen final a 2k
   (180), 430 créditos en total. Sale una galería con el Preset 02 y el Preset 03 en sus formatos
   con esa imagen.

## Fuera de este camino

- **Rick en la VPS.** Sigue en la API sin kit. Si Magnific publica kits en la API, se revisa.
- **Sincronía con el manual.** El kit es una copia derivada de UB-3, como el mapa para ChatGPT.
  Si cambian el CSS o el manual, hay que actualizarlo. Conviene anotarlo en la skill
  `umbral-brand-identity`.
- **Límites diarios.** Magnific limita por día las referencias y las plantillas nuevas: el
  paso 2 puede tomar más de un día.
- **Sin ver.** Las imágenes de la biblioteca se juzgaron por su catálogo; aquí no se miraron una
  por una.
