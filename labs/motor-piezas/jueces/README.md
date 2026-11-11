# Jueces que aprenden de las elecciones de David

Pedido de David (2026-11-11): «la diea es que los jhuueces cada vez adopten mas mis creiterios y tu busque sla
forma d elqeu lo hagan, editando sus configuraciones y/o flujos».

Hasta G28 los jueces **no** aprendían: la rúbrica decía «calibrar contra decisiones.csv», pero ningún
paso lo hacía, y la página de la galería mostraba su voto antes de que David eligiera, así que no había cómo
medir si coincidían con él.

## El ciclo

1. **Galería ciega.** `pagina_eleccion.py` arma la página del celular con alternativas y piezas numeradas,
   sin recomendaciones ni descartes.
2. **Voto sellado.** Los jueces (un agente por lente) votan antes de que David elija. `jueces.py sellar`
   guarda el voto en `votos/` con la hora y el hash de la rúbrica y de los criterios. Un voto posterior a la
   elección solo entra como prueba retroactiva.
3. **David elige por número**, idealmente con una frase de por qué. Va a `decisiones.csv` y a
   `elecciones.yaml`.
4. **Calibrar.** `jueces.py calibrar` compara cada voto sellado con la elección: si acertaron, en qué puesto
   quedó la elegida y qué lentes coincidieron. `pesos.yaml` lleva el acuerdo de cada lente con David.
5. **Aprender de los desacuerdos.** `desacuerdos.json` junta las galerías en que fallaron, con la cita de
   David y el resumen de cada juez. De ahí sale un criterio nuevo o corregido en `criterios-david.yaml`
   (siempre con su cita literal) o un cambio en la mirada de una lente en `rubricas.yaml`. Antes de
   aceptarlo se vuelve a medir sobre las galerías pasadas: si no mejora, no entra.

## Qué decide

El **juez de predicción** (`rubricas.yaml`, etapa `eleccion`) recibe todos los criterios de David y responde
«¿cuál elegiría David?». Su elección es la de los jueces. Las lentes parciales (marca, oficio, composición,
lectura…) no deciden: sus hallazgos y vetos se le muestran a David como diagnóstico.

## La prueba sobre 14 galerías pasadas (2026-11-11)

Galerías en que David ya había elegido una opción: G02 a G06, G09, G12 a G16, G22, G23 y G25. Cada juez votó
a ciegas: no sabía lo que eligió David y solo recibió los criterios aprendidos **antes** de esa galería (toda su
evidencia anterior). El azar acertaría unas 4 de 14.

| Jueces | G02–G06 (casi sin criterios) | G09–G25 (más criterios) | Total |
|---|---|---|---|
| Panel de 3 lentes, sin criterios (v1) | 2/5 | 4/9 | 6/14 |
| Panel de 5 lentes, con criterios, suma pareja (v2) | 0/5 | 3/9 | 3/14 |
| Predictor sin criterios, dos corridas | 2/5 · 2/5 | 3/9 · 5/9 | 5/14 · 7/14 |
| **Predictor con criterios, dos corridas** | 1/5 · 1/5 | **6/9 · 5/9** | 7/14 · 6/14 |
| Predictor con criterios + C46 (rechazado) | — | 5/9 · 4/9 | — |

Lo que se aprendió:
- Con criterios, el predictor acierta más cuando ya hay criterios (G09 en adelante) y es estable: sus dos
  corridas eligen lo mismo en 13 de 14 galerías. Sin criterios, sus dos corridas coinciden en 8 de 14.
- Son 14 galerías: la mejora es una señal, no una prueba. Se sigue midiendo galería a galería.
- Sumar lentes con el mismo peso empeora: lectura (3/13), costuras (2/8) y posición (2/6) empujan hacia
  opciones «seguras». La lente que más coincide con David es composición (8/13).
- C46 («entre opciones que ya se leen, no gana la más legible») salió de los desacuerdos en G03, G05 y G06,
  pero sobre G09–G25 bajó el acierto. Quedó en `rechazados`.
- Siete de 28 jueces sin criterios, a los que se les preguntó qué elegiría David, fueron a buscar
  `decisiones.csv`. Sus votos se anularon, el encargo ahora lo prohíbe y `jueces.py auditar` lo revisa en
  cada tanda.

## G28, voto sellado

Antes de que David elija G28 quedaron sellados en `votos/`: el panel de 11 lentes (`G28-v2`), dos corridas del
predictor con los 45 criterios (`G28-pred-crit-a` y `-b`) y dos con C46 (`G28-pred-crit2-a` y `-b`; el texto de C46 está en `rechazados`).
La rúbrica y los criterios del panel y del predictor están en `historial/` con su hash. No se le muestran a David hasta que elija.

## Archivos

| Archivo | Qué es |
|---|---|
| `rubricas.yaml` | Las lentes por etapa (imagen, pieza, campaña), vetos, escala, agregación y el protocolo. La versión anterior está en `historial/` |
| `criterios-david.yaml` | Lo que David valora, rechaza o pide, con cita literal y la galería desde la que vale. Cada juez recibe los que tocan su lente |
| `elecciones.yaml` | Qué eligió David en cada galería, en números de opción |
| `votos/` | Votos sellados por galería y versión de rúbrica |
| `pesos.yaml` | Acuerdo de cada lente con David (para ver qué lente lo representa mejor) |
| `calibracion.csv`, `desacuerdos.json` | Salida de `jueces.py calibrar` |
| `jueces.py` | `preparar`, `sellar`, `agregar`, `elegir`, `auditar`, `calibrar` |
| `historial/` | Rúbricas y criterios con que se sellaron votos, para comparar después |
