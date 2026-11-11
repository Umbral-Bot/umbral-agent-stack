# Demo del camino B sin créditos (G28, 2026-11-11)

Recorrido completo de una pieza, de su contenido al texto que iría a Magnific, sin generar ninguna imagen.

| Paso | Quién | Archivo |
|---|---|---|
| 1. Ruteo de «La IA entra a la obra» | código (`formula.py rutear`) | `ruteo-ia-obra.json`: hallazgo por regla, 4 contra 2 de pendiente |
| 2. prompt(1) | código (`formula.py preparar`) | `prompt1-ia-obra.md`: esqueleto común + bloque de hallazgo |
| 3. prompt(2) | un agente que solo leyó `prompt1-ia-obra.md` | `prompt2-ia-obra.json` |
| 4. Validación y ensamblado | código (`formula.py validar`) | `pedido-ia-obra.json`: pasa las comprobaciones al primer intento; 4 textos (16:9 y 21:9, Magnific One con kit y Nano Banana 2.1) |
| 5. Revisión de alineación | otro agente, que no ruteó ni escribió | abajo |

Prueba negativa (no guardada): el mismo prompt(2) con recorridos discontinuos, una sigla, una cifra, una
negación, un tercer acento y una fila en el 21:9 sacó 17 errores y la orden de reintento.

Caso openBIM (fixture del repo): el léxico no decide (interfaz 5, hallazgo 4). El clasificador
(`clasificador-openbim.md`, respuesta en `clasificacion-openbim.json`) eligió interfaz con confianza 0,86;
`formula.py aceptar` lo cerró en `ruteo-openbim-aceptado.json`.

## Revisión de alineación (pre-revisión; la aprobación es de David)

ALIGNMENT = OK. La imagen muestra un único choque sin resolver entre la camisa y el estribo, y
`no_mostrar` deja fuera el remedio, el cierre y al equipo: cumple la categoría hallazgo.

Avisos del revisor, sin cambiar el prompt (nunca se corrige a mano sin registro):

- **Ruteo.** «se revisan» y «revisan con IA» salen de la misma frase. Así lo define el léxico (una
  revisión, y además hecha con IA), pero hay que mirarlo cuando se calibre con unas 20 piezas.
- **Riesgo de dibujo.** Magnific podría pasar la camisa limpia entre dos estribos, que es el arreglo. A
  tamaño de feed, un estribo fino y una camisa, los dos en turquesa, pueden leerse como una sola mancha.
  Propone una relación más explícita: «the sleeve runs straight through one stirrup».
