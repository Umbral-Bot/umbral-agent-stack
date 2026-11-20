# Fábrica de ideas creativas · entre la editorial de UAS y los prompts

Pedido de David (2026-11-20): «esto entraría después de las ideas que genere la editorial automatizada que estoy
creando […] parte de ejemplos de items que están en el notion de ese piloto y desde ahí salen las ideas creativas que
representen la idea de la editorial pero con el objetivo de conectar a las personas que pueden ser potenciales
alumnos, potenciales seguidores de linkedin para mí, potenciales clientes, conectarlos e incentivarlos para que lean el
post». Y después: «lo que tienes que hacer es una fábrica de ideas pero ideas creativas con las cuales después en otro
paso hacemos los prompts».

## La cadena

1. **Editorial de UAS** (Notion, base Publicaciones): el ítem con su título, premisa, claim, copy y etapa de audiencia.
   La idea de la pieza la pone la editorial; aquí no se reescribe.
2. **Fábrica de ideas creativas** (esta carpeta): por cada ítem, conceptos visuales que representan esa idea y que
   buscan que un público concreto (alumnos, seguidores o clientes de David) se detenga y lea el post. Sin prompts.
3. **David elige** un concepto por ítem (`rondas/C01.json`, página numerada, voto de los jueces sellado antes).
4. **Prompts** (paso siguiente, `../formula/`): el concepto elegido pasa a prompt(1) y prompt(2) y a Magnific.
5. **Motor de piezas**: la imagen entra a la pieza en todos los formatos.

## Archivos

- `ficha.md`: los campos de una idea creativa y sus reglas.
- `generar.md`: el encargo de un agente (un ítem por agente).
- `creativas.py`: `validar` (forma, vetos de marca en la escena, monotonía dentro del ítem) y `pagina` (la página
  numerada para el celular, agrupada por ítem).
- `rondas/C01.json`: los ítems de entrada, las fichas, las presentadas y las notas del editor.

## Lo que se trae del laboratorio

- De las rondas de metáforas (M01, M02): la idea tiene que enganchar y no solo entenderse (C51); la dirección de arte
  de M02 funciona (C53); metáfora y no ilustración literal (C47, C48); el arnés H021 («X que se vuelve Y», de
  izquierda a derecha) como uno de los caminos, no como plantilla.
- De la fábrica de ideas (I01 a I03, en pausa): audiencia amplia (C54), la narrativa es parte de la idea (C56),
  persuasión (C59) y proceso visible (C58).
