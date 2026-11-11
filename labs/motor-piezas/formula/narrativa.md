# Camino B v2 · de la premisa a la imagen

David sobre G28 (piezas 1° a 21°, la imagen relacionada de «La IA entra a la obra»): «cual sería la metrafora? como
se relaciona el totulo con el dibujo? revisa de referencia lo que teniamos en ese sentido en laautomaitzación de
creacinod e conteindo en la editaroial automatizada de UAS, revisa lo qeuteniamos de estructura de la narrativa,
preimisa, idea, abstracción etc, creo que falta todo eso aca».

## Qué falló

Las piezas 1° a 21° dibujan un sustantivo, no una idea: una tubería que cruza una viga. Ni «la IA entra» ni «qué
sigue dependiendo del equipo» están en la imagen. Salieron de la fórmula v1 de G27, que iba del titular a un objeto
del inventario de la categoría y a una relación geométrica, sin pasar por una tesis ni por una metáfora.

## La cadena de UAS (lo que faltaba)

La editorial automatizada de UAS arma el sentido en este orden (revisión del 2026-11-11, con fuentes):

| Paso | Campo en UAS | Qué es |
|---|---|---|
| Premisa | `premisa` (Publicaciones) | la idea central en una o dos frases; no es el título |
| Arco | `arco_narrativo` | de dónde parte, qué tensiona y a dónde llega |
| Compara | línea de control | qué compara o afirma el copy, con los mismos términos |
| Hecho y consecuencia | `central_fact`, `ignored_consequence` | derivados del copy, no copiados del titular |
| Metáfora núcleo | `core_metaphor` | sujeto + estado inicial + transformación + estado terminal |
| Invariantes | `invariants` | lo que comparten todas las variantes |
| Propuesta visual | tabla para David | Mensaje, Escena y metáfora, Emoción, Estrategia comunicacional, Evitar |
| Alineación | `ALIGNMENT_VERDICT` (rick-qa) | ¿la metáfora cuenta la misma comparación que el copy? FAIL, no SOFT |

Fuentes principales: `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` (premisa, arco, regla dura de
alineación), `rick-qa/ROLE.md` (veredictos), `openclaw/workspace-templates/skills/nano-banana-image-briefs/SKILL.md`
(core_metaphor y anti-plantilla), `docs/ops/editorial-visual-brief-v2-2026-08-29.md` y la propuesta visual de
`docs/editorial-previews/2026-09-13-ia-rediseno-astra6.md` (la cremallera).

## La cadena del camino B v2

1. **Premisa** (dato de entrada). La escribe quien escribe la pieza, o viene de UAS. Si falta, se propone y David la
   confirma; sin premisa no hay imagen relacionada (la pieza va a fondo con motivo «sin tesis»).
2. **Clase de historia.** Objeto con un defecto que se sostiene (crítica), comparación abierta entre dos opciones, o
   transformación (X se vuelve Y). La tercera es nueva y está a prueba: su única evidencia es H021, la ciudad que se
   vuelve red (ver `../magnific/arnes-h021.md`).
3. **Propuesta visual**, en castellano y para David, con los campos de UAS:
   - **Mensaje**: la idea, sin objetos;
   - **Escena y metáfora**: sujeto, estado inicial, transformación y estado terminal;
   - **Emoción**;
   - **Estrategia comunicacional**: por qué se relaciona con el título, que es la pregunta de David;
   - **Evitar**.
4. **El sujeto queda abierto.** Puede ser un objeto del oficio, un objeto cotidiano con tensión (como la cremallera de
   UAS) o un campo abstracto del oficio. Exigir siempre un objeto técnico entero llevaba a dibujar el sustantivo del
   titular.
5. **Elegir la metáfora en texto, antes de gastar.** Se proponen tres metáforas numeradas y David elige. La elección
   va a `jueces/interacciones.jsonl` y enseña a los jueces.
6. **Prueba de lectura a ciegas.** Otro agente recibe solo la escena (o la imagen) y cuatro titulares, uno real, y
   tiene que adivinar cuál cuenta. Si no lo adivina, la metáfora no se lee.
7. **Alineación.** Un revisor que no escribió la metáfora responde la pregunta de rick-qa: mismos términos, mismo
   momento, misma consecuencia que la premisa.
8. **Recién entonces, los prompts** para Magnific (16:9 y 21:9), con las reglas de marca y la validación de forma de
   `validacion.md`. Hay que revisar esa validación para la clase transformación: hoy veta las secuencias y los acentos
   repartidos.

Plantilla del paso 3: `metaforas.md`.

## Cautelas

- **Un ganador no es plantilla.** La ciudad que se vuelve red funcionó una vez; sus nodos no pasan a ser el sujeto de
  todas las imágenes (regla anti-plantilla de UAS).
- **Pilotear antes de reescribir las seis categorías de `categorias.yaml`.**
- **El contenido de ejemplo no trae tesis.** La premisa de la demo es una propuesta que David tiene que confirmar.

## Primera ronda: M01 (2026-11-11)

- Cuatro metáforas para «La IA entra a la obra»: un edificio que cruza un marco, una canica ante una compuerta, un
  desagüe fuera de la grilla de baldosas y un campo de placas con las desalineadas levantadas.
- David leyó el texto: «suenan bien a simple vista», y pidió las imágenes.
- Se generaron la principal y la apaisada de cada una con Magnific One y el kit: 8 imágenes, 1.440 créditos. Detalle
  en `demo/M01-metaforas.json`.
- La revisión de alineación y la lectura a ciegas del texto, y el voto ciego sobre las imágenes, están sellados en
  `../jueces/votos/` hasta que David elija.
