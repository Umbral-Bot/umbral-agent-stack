# Aprender de cada interacción con David

Pedido de David (2026-11-11): «optimiza el sistme apar ir aprendiendo a aprtir de lasinteraciones conmigo».

Cada mensaje de David sobre una galería es un dato, no solo su elección final. Después de cada mensaje:

1. **Registrar el mensaje entero.** `jueces.py elegir --texto "<mensaje literal>"` lo deja en
   `interacciones.jsonl`. Si el mensaje no elige (una pregunta, un pedido), se agrega igual a ese archivo con
   `tipo: comentario`.
2. **Valorar cada opción, no solo la ganadora.** David suele decir algo de varias opciones («se ve bien», «casi»,
   «falta la metáfora»). Se traduce a una escala de −1 a 2 y va en `--valoraciones` (con rangos: `1-3:-1,4-5:1,6:2`)
   y su frase literal por opción en `--comentarios`. Así cada galería enseña sobre todas las opciones.
3. **Revelar el voto sellado recién después** y calibrar (`jueces.py calibrar`): acierto, puesto de la elegida y
   correlación entre los puntajes de los jueces y la valoración de David (ρ).
4. **Convertir el mensaje en criterios** (`criterios-david.yaml`), siempre con cita literal:
   - lo que David dice con sus palabras entra **activo**;
   - lo que se infiere de lo que eligió (por ejemplo, que no le molestó algo que los jueces vetaron) entra
     **a prueba** y se mide en la próxima galería; si baja el acierto, pasa a `rechazados`.
5. **Corregir una lente** cuando falla de forma sistemática (por ejemplo, la de marca vetó la opción que David
   puso como la mejor). El cambio va a `rubricas.yaml` con su motivo, y la versión anterior a `historial/`.
6. **Ejemplos.** El juez de predicción recibe las últimas elecciones de David (qué había, qué eligió, qué dijo:
   `--ejemplos`). Cada galería elegida pasa a ser un ejemplo para la siguiente.

Lo que no se hace: usar la elección de una galería para corregir el voto de esa misma galería, ni dar por
aprendido un criterio que no se midió.
