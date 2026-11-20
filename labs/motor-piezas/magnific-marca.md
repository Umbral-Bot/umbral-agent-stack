# Magnific One y la marca Umbral BIM · camino recomendado

Análisis del 2026-11-10, pedido por David: «revisa en magnific para integrar manual de marca con
magnificone creo que es el cmaino, analiza ye dstuida el mejor camniino para eso, plantillas,
braindings etc enfuncion del manual de la marca». Solo lectura: no se escribió en Magnific y no se
gastaron créditos.

## Avance

David, 2026-11-10: «Respectode kitlo e maginfic one y la marca estoytotalmente de acuerdo con lo
que proopones». Con eso quedan hechos los pasos 1 a 3, sin gastar créditos. El piloto (paso 4) sigue
esperando su OK a los 430 créditos.

1. **Línea visual: isométrica plana y clara.** De las ocho imágenes con su dirección aprobada,
   cinco son de esa línea (G-SITIO-01 y G-AFI-01 a 04, Magnific One). Las otras tres (G-SITIO-02,
   03 y 05) son íconos de diagrama con trazo grueso, hechos con Nano Banana: quedan fuera del kit
   para no mezclar estilos.
2. **Kit corregido.** Antes de tocarlo se respaldó en `magnific/kit-umbral-bim-antes-2026-11-10.json`.
   - Seis prohibiciones cargadas (las del paso 2).
   - Las cinco imágenes como referencia. Al leerlas, Magnific sumó por su cuenta cinco colores
     estimados a la paleta (entre ellos un turquesa #12A296 como primario) y dos reglas de afiche
     (sujeto a la derecha, izquierda vacía). Se volvió a la paleta UB-3 de siete colores y se
     quitaron esas dos reglas: el motor necesita el sujeto al centro.
   - Los SVG oficiales del Lockup 01 (Claro, Oscuro y Monocromo Blanco). Se descargaron de vuelta y
     su geometría y colores son idénticos a los de `Exportables\`.
   - Las dos plantillas pasaron a ser solo de imagen: «Imagen de artículo · 16:9» y «Fondo vertical ·
     9:16». El texto anterior está en el respaldo.
   - El texto de diseño del kit dice qué lockup va sobre qué fondo.
   - **Lo que no se pudo desde fuera de la app:** Magnific describe los tres SVG «sobre fondo negro»
     y al Monocromo Blanco le asigna fondos oscuros. El raster antiguo sigue en el kit. Ninguna de
     las dos cosas se puede editar con las herramientas disponibles; el texto de diseño lo aclara, y la
     sexta prohibición impide que la imagen traiga logo. La plantilla de artículo queda en 4:5 por
     su canal («post LinkedIn»), así que el pedido pide 16:9 explícito.
3. **Motor conectado** (`pedido_magnific.py`, motor 0.3k).
   - `pedido` compone cada formato de los presets, mide su zona de imagen con el mismo encuadre del
     motor y escribe el pedido. Para los presets 02 y 03, las zonas van de 3,6:1 (slide) a 0,8:1
     (LinkedIn con bajada): con una maestra 16:9, el sujeto debe caber en el 45 % del ancho y el 49 %
     del alto centrales. Pedido de ejemplo: `magnific/pedidos/articulo-ia-obra.json`.
   - `registrar` copia la imagen a `07_Motor de piezas/02_magnific` y la anota en
     `imagenes.magnific.yaml` con creación, kit, plantilla, semilla, créditos y prompt. Un contenido
     la usa con `imagen: <id>`.
   - Prueba sin créditos con G-SITIO-01 (`contenido/prueba-magnific.yaml`): los siete formatos de los
     presets 02 y 03 cumplen UB-3. Esa imagen se hizo para afiche, con la persona a la derecha, y en
     el 16:9 le corta la cabeza: es lo que la zona segura del pedido evita.

### Piloto (G24, 2026-11-10)

David aprobó el gasto: «y si apruebo el gasto de 430 creditos en maginific». Se gastaron 430 créditos
(saldo 240.000 → 239.570): la grilla de borradores (250) y una imagen final a 2k con el kit (180).

- **Pedido.** Un panel de agentes sin créditos propuso tres ideas y las juzgó con tres criterios
  (marca, recorte, sentido). Ganó la literal: un edificio de dos pisos en corte, con solo la losa y la
  tubería que atraviesa una viga en turquesa, «las que encontró una revisión automática».
- **Borradores, sin kit.** Magnific One no acepta kit en el modo borrador; se pidieron con dos
  imágenes aprobadas como referencia de estilo. Salieron 4 composiciones casi cuadradas, que
  Magnific partió en 8 mitades: ninguna tesela tiene el edificio entero. Además parecen una lámina
  escaneada (papel crema #F0EDE6, borde de hoja, trazo a mano, marcas de registro). Tres jueces
  independientes lo detectaron; por eso ninguna tesela se pasó a final.
- **Imagen final, con kit.** Se pidió directo a 2k, con la composición 1 como guía de encuadre
  (`ksMJNHs16B`). Salió en la línea: fondo claro plano (#F9F7F5), trazo fino, retícula tenue,
  turquesa solo en la losa y el tramo de tubería, sin texto ni logo. Magnific no devolvió su control
  de marca automático. Registrada como `mg-articulo-ia-obra-01` en `imagenes.magnific.yaml`.
- **Encuadre.** Magnific ignoró los márgenes pedidos: el edificio excede la zona segura en alto. El
  motor 0.3l deja que la imagen traiga su `foco` (aquí, el centro del turquesa, 0,45 y 0,71): con
  él, en el peor recorte (la diapositiva 16:9) se ve el 99 % del turquesa, contra el 75 % con el
  recorte centrado.
- **Resultado.** Las siete piezas de los presets 02 y 03 cumplen UB-3; el único aviso es el texto del
  botón de LinkedIn bajo el mínimo móvil, pedido por David. Cada ficha de pieza lleva ahora la
  procedencia de la imagen (creación, kit, créditos, foco y pedido).
- **Para la próxima imagen:** saltarse la grilla de borradores (sin kit no sirve) y pedir una imagen
  a 2k con el kit (180), con el foco medido al registrarla.

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
