# Validación del prompt(2) antes de gastar créditos

- 1 · Forma. JSON válido. estado debe ser OK, NO_ENCAJA o CIFRA. Con OK, categoria coincide con la ruteada y ningún campo queda vacío, salvo «reparo». NO_ENCAJA lleva a fondo y CIFRA a diagrama.
- 2 · Largo. Cada cuerpo, sin cola, tiene entre 25 y 55 palabras y 400 caracteres como máximo. El cuerpo 16:9 y el 21:9 son distintos.
- 3 · Marco literal. El 16:9 empieza con «Isometric line illustration of » y contiene «, whole and centred with wide empty space around it. » y «flat teal, the ». El 21:9 empieza con «Isometric line illustration: » y contiene «, centred, empty margins at both ends» y «flat teal, the single ».
- 4 · Acentos. Lleva 1 o 2, con exactamente 1 en evento y exactamente 2 en comparación. Cada acento tiene de 2 a 6 palabras y aparece literal en los dos cuerpos. «Only one part is flat teal» o «Only two parts are flat teal» coincide con len(acentos), y «teal» aparece una sola vez en cada cuerpo.
- 5 · Color y estilo. No hay `#[0-9a-fA-F]{3,6}` ni otro color que teal (red, orange, yellow, green, blue, cyan, turquoise, purple, pink, black, white, grey, gray, brown, gold, silver, dark). Tampoco adjetivos de estilo: flat vector, minimal, clean, elegant, sleek, modern, futuristic, cinematic, photorealistic, vibrant.
- 6 · Cifras. No hay dígitos `[0-9]` ni un número en palabra junto a una unidad en inglés (three weeks, twice, percent, times, per cent). Si David pidió imagen sobre una pieza «dato», también se vetan las palabras de la cita numérica.
- 7 · Siglas y marcas. Nada que coincida con `\b[A-Z]{2,}\b`, y ninguna marca o software de la lista: BIM, IFC, IDS, BCF, RFI, CDE, ISO, AI, IA, Revit, Navisworks, Solibri, Autodesk, Dynamo, Rhino, Tekla, Speckle, Procore, Magnific, Umbral.
- 8 · Negaciones. En el cuerpo no aparece `\b(no|not|never|without|neither|nor|none|nothing|nobody)\b` ni «n't». Solo la cola de mg1 y el bloque de marca de nb21 llevan negaciones, y esas las pone el código.
- 9 · Lista negra general (palabra completa, sin distinguir mayúsculas): text, letter, word, label, caption, sign, signage, logo, screen, monitor, laptop, tablet, dashboard, interface, app, chart, graph, diagram, infographic, arrow, icon, symbol, marker, pin, document, paper, sheet, folder, file, stamp, calendar, clock, person, people, worker, engineer, hand, team, avatar, silhouette, robot, brain, chip, circuit, hologram, drone, scan, magnifying, glow, neon, gradient, shadow, reflection, photo, realistic, render, 3D, blur, bokeh, cutaway, cross-section, sectional, exploded, x-ray, dashed, dotted, faint, ghost, transparent, translucent, question mark, check mark, tick, warning, glass box, showcase, before and after.
- 10 · Regla del 21:9. Contiene «the single». No lleva row of, rows, each, every bay, series, sequence, repeated, timeline, stages, steps ni one after another.
- 11 · Reglas por categoría. hallazgo: sin fixed, resolved, repaired, rerouted, solved, corrected, alternative ni bypass. comparacion: contiene «half» o «halves» y «seam»; sin better, best, winner, preferred, chosen, selected, favoured, old, new, worn, damaged, cracked, broken, before, after, balance ni versus. interfaz: contiene «plate», «joint», «meet» o «flush/offset»; sin cable, wire, plug, socket, cloud, network, data, stream, puzzle ni connector. pendiente: un acento contiene «empty» y la relación contiene stops, short, gap o ends; sin filled, delivered, arrives, installed, received, answered, question, decision, owner ni chair. transformacion: contiene «footprint» u «outline» y un verbo de continuidad (rises, grows, turns); sin floor plan, plan view, blueprint, drawing, sketch, dimension, phase, crane ni worker. evento: termina en «Every other part is plain line work.»; sin session, webinar, workshop, audience, stage, podium, microphone, speaker, leader line, part number ni light bulb.
- 12 · Sujeto no repetido. El sustantivo núcleo del sujeto no coincide con ninguno de {sujetos_recientes} (las últimas 5 piezas) ni con el del ejemplo de la categoría. Si coincide, se marca monotonía y se reintenta.
- 13 · Revisión semántica. no_mostrar no está vacío y ninguno de sus sustantivos `en` aparece en los cuerpos. compara existe y cada evidencia es subcadena literal del titular o la bajada. El código solo comprueba que existan; el juicio de alineación (CAND-WLCA-01) es de rick-qa o David antes de los créditos.
- 14 · Ensamblado. En mg1_kit, el texto final termina exactamente en «No text, no markers, no logo.». En nb21_sin_kit, contiene una sola vez el BLOQUE_MARCA completo del formato que corresponde, y el hex solo aparece dentro de ese bloque. En los dos motores, el cuerpo es idéntico byte a byte (el registro guarda su hash).
- 15 · Fallo. El código arma la lista de errores y hace un solo reintento de prompt(1) con esa lista. Si vuelve a fallar, la ruta es fondo con motivo «validacion». Nunca se envía un prompt sin validar ni se corrige a mano sin dejar registro.

## Notas de la síntesis

Síntesis de las tres propuestas (Contenido editorial, Gramática visual y OPERACIÓN) con los dos jueces. Qué se tomó de cada una:
- Categorías por tipo de mensaje, que David reconoce leyendo el copy. Comparación con prioridad (CAND-WLCA-01). Evento por código. Gate de cifras con números en palabra y exclusiones de normas y versiones.
- Ruteo en cascada con pesos y umbrales en YAML. LLM solo como fallback, con confianza ≥ 0,70 y cita literal. Salidas fail-closed. Validador que bloquea siglas, dígitos, hex y negaciones. Post-generación medida. Cuerpo de la escena por LLM y marca por código.
- Lo abierto se cuenta con geometría sólida, sin líneas tenues ni discontinuas (veredicto de G27 sobre B1). El tipo de recurso solo desempata. Una categoría que pierde dos rondas HITL se retira.

Decisiones propias de esta síntesis:
- junta + estándar se fusionan en «interfaz».
- decisión + hueco se fusionan en «pendiente»: un receptor vacío dibujado sólido, sin «empty dashed outline» y sin carpetas, para no invitar pseudotexto.
- Comparación lleva sus 2 acentos contiguos en la costura, para no romper el ancla única.
- Evento usa el emblema (1 acento), no la vista explosionada.
- Se elimina el «matiz»: la imagen no lleva un tercer elemento tenue.
- Quedan fuera dos-estados, red, capas, despiece, recorrido y campo. Campo (retícula con una anomalía, tipo: fondo con recorte óptimo) puede pilotearse aparte.

Cambio sobre la fórmula vigente: formula-grafico-relacionado.md aplica B1 con dos recorridos discontinuos. Este set los quita («The pipe still runs through the beam.»), así que el prompt de hallazgo deja de ser el probado. La B1 corregida no se ha generado.

Madurez: solo hallazgo tiene pilotos (G24 a G27, y con discontinuos). Las otras cinco son hipótesis. Pilotear cada categoría cuesta 2×180 = 360 créditos en Magnific One o 2×65 = 130 en Nano Banana 2.1, siempre con el OK de David. Orden sugerido:
1. hallazgo corregida
2. interfaz y pendiente (cubren los fixtures openBIM y RFI)
3. comparación
4. evento
5. transformación, al final por riesgo de cotas y rótulos

Pedido de David («prueba b1 también en nano banana 2.1 para comparar»): la comparación ya está en el registro. G28 tiene mg-articulo-ia-obra-nb-p1, p2, a1 y a2, a 65 créditos cada una, sin kit y con lJo6GJSgv9 como referencia. Pero se mandó el texto que Magnific One ya había expandido (hex y composición propia), así que mezcla texto y motor.

Lo que vi en los dos originales que hay en salida/G28/img (nb-p1, nb-a1), contra B1 de Magnific One (formula-p1, formula-a1). No es un veredicto; la elección es de David:
- Ningún hex aparece dibujado como texto.
- nb-p1: trazo más pesado (perfiles dobles con cara blanca). El turquesa cae en un tramo de viga bajo la tubería, no en la tubería, y el choque se lee menos.
- nb-a1: sale casi en alzado frontal, no isométrica, con dos manchas turquesa separadas (un bloque en la viga superior y un tramo de tubería). Eso rompe el ancla única.
- formula-p1: trazo fino y choque legible, pero los discontinuos casi no se ven y el objeto ocupa el 73 % del alto.
- formula-a1: vista oblicua.

Medidas del registro: acento de nb-p2 de 18×20 % del cuadro contra 7×8 % en formula-p1; objeto de nb-a2 del 6 % al 90 % del ancho. Los originales de nb-p2 y nb-a2 no están en salida/G28/img (solo las versiones difusas), así que su hex no se revisó.

Comparación limpia propuesta (no ejecutada, necesita OK de David): mismo cuerpo, solo cambia el envoltorio.
- Mínima: el prompt_enviado de B1 sin cola + BLOQUE_MARCA nb21, en 16:9 y 21:9. Cuesta 130 créditos y se compara 1:1 con formula-p1 y formula-a1.
- Completa: la B1 corregida (ejemplo de hallazgo) en los dos motores. Cuesta 2×180 + 2×65 = 490 créditos.

Decisiones abiertas para David:
- Qué hacer con la capa 3 mientras no exista. Por ahora la pieza va a fondo con capa3_pendiente.
- Hex o nombres de color en el bloque nb21. Por defecto hex, ya que 2 de 2 originales salieron sin texto.
- Los umbrales de post-generación (acento ≤ 12 %/15 %, separación ≤ 2 %, margen ≥ 6 %) son iniciales y hay que calibrarlos con G24 a G28.
- El grosor del trazo no tiene control automático y queda en HITL.

Las regresiones del router se calcularon a mano y no se ejecutaron. El copy real de CAND-WLCA-01 no se leyó en esta pasada.

Archivos sugeridos para guardar:
- labs/motor-piezas/magnific/ruteo.categorias.yaml: léxicos, pesos, bloques e inventarios.
- labs/motor-piezas/magnific/prompt1-grafico-relacionado.md: la plantilla.
- Constantes COLA_MG1 y BLOQUE_MARCA_16x9/21x9 en pedido_magnific.py.
- Un fixture de ruteo con 15 a 20 copies reales.
- Actualizar formula-grafico-relacionado.md para quitar los discontinuos de B1.

Los ejemplos de prompt(2) se muestran como los recibiría Magnific One (cuerpo + cola). En nb21 la cola se reemplaza por el bloque de marca. En este paso no se gastaron créditos ni se modificó ningún archivo.
