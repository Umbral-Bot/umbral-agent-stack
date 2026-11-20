# Fábrica de ideas · etapa 1 del camino B

> **En pausa desde el 2026-11-20.** David aclaró que las ideas de los posts las pone la editorial de UAS; el laboratorio trabaja después, con ideas creativas para la imagen (`../creativas/`). Lo aprendido aquí (C54 a C60) pasa a esa etapa.

Pedido de David (2026-11-11): «Partamos en la producción de ideas primero como se origina la idea, luego al tener una
fabrica de ideas alienadas con mi trabajo y mi estilo y mis principios, ahi recien pasamos a la siguienteetapa de ver como
sacamos metaforas d eeso, una vez tengamos la maquna par ahacer metaforas aavanzamos con convertirlas en imagenes».

Antes de esta etapa, el laboratorio buscaba metáforas para una premisa que escribía el agente sobre un artículo de
ejemplo sin tesis (M01 y M02). La dirección de arte de M02 quedó aprobada; lo que faltaba era la idea (criterio C53).

## El flujo

1. **Raíz** (`raiz-david.yaml`): quién es David, qué sostiene y cómo habla, con la fuente de cada dato (CV v6 y Notion).
2. **Manantiales** (`manantiales.md`): de dónde nace cada idea. Puede ser su experiencia, un dolor de su audiencia, una
   señal externa traducida a la obra o uno de sus pilares. Siempre con una evidencia trazable.
3. **Generadores** (`generar.md`): una fórmula de transformación por agente. Son las cuatro de la editorial de UAS más
   una propia: de la experiencia al criterio.
4. **Ficha** (`ficha.md`): la idea antes del texto. Lleva:
   - la premisa;
   - la hipótesis que se pone a prueba y la respuesta de David;
   - la cadena de la tesis;
   - la frase que queda, el gancho, la escena de obra y los canales.
5. **Validación** (`ideas.py validar`): forma y verdad por código. Aplica los rechazos de QA de UAS, la lista negra y
   las cifras, clientes y credenciales que el CV v6 no confirma. Marca también si dos ideas sostienen lo mismo.
6. **Jueces** (`../jueces/`, etapa `idea`): premisa, alineación, voz, enganche y monotonía. Votan antes que David y su
   voto se sella.
7. **Ronda con David** (`rondas/I01.json` y `ideas.py pagina`): cuatro ideas numeradas, distintas en manantial y en
   tesis. David aprueba, observa, descarta con motivo o archiva. Todo queda en `../jueces/interacciones.jsonl` para que
   los jueces aprendan.
8. **Banco** (`banco.yaml`): las ideas aprobadas, que son la entrada de la etapa 2 (metáforas).

## De dónde sale

- La ficha y la estructura hipótesis → respuesta vienen de la editorial de UAS: la alternativa V1, la cadena de la tesis
  y la estructura de discurso (`openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`). Las fórmulas, de
  `docs/ops/cand-002-rick-orchestrator-request.md`.
- Los dolores y los ganchos, de `community-pain-to-linkedin-engine`. La voz, de `director-comunicacion-umbral`.
- De la skill `asesor-discursivo` salen la premisa, el residuo y el selector de arquitectura. De `mi-contenido`, el mapa
  de la evidencia.
- Lo que UAS no tenía: medir si una idea engancha y evitar que todas repitan la misma tesis.

## Rondas

| Ronda | Fecha | Lo que dijo David | Los jueces | Lo que cambió |
|---|---|---|---|---|
| I01 | 2026-11-16 | Ninguna. Solo la 3 (la resistencia joven) le interesó como tema, «pero la redacción y narrativa está un poco extraña». La 1, correcta pero de nicho técnico; la 2, poco interesante; la 4, fuera de sus temas («yo no enseño docencia») | Eligieron la 1; ρ con su valoración −0,77 | Criterios C54 (audiencia amplia), C55 (docencia fuera), C56 (la narrativa es parte de la idea) y C57 a prueba (qué sonó extraño). Rúbricas v5, `fuera_de_alcance` en la raíz y dos pasos nuevos en `generar.md` |
| I02 | 2026-11-16 | Ninguna: «no creo que esas ideas conecten muy bien con la audiencia»; pidió proceso y persuasión en cada idea. Cinco ideas (página MdrrgxBDkFw1rcHgd6oB4a; Drive `03_ideas/2026-11-16_I02`), contadas como relato; la 2 es la 3 de I01 reescrita | Eligieron la 3 y dieron «sirve» a las cinco | 14 fichas en cinco grupos; `ideas.py` no detectó la repetición (compara palabras, no tesis): pendiente medirla por la frase que queda |
| I03 | 2026-11-20 | Espera. Cinco ideas que parten de una audiencia (profesionales AEC, dueños de pymes, jefes de proyecto, quienes deciden la compra de IA), con persuasión y proceso (página AzyFvieEjSTgc9gyfCzxLX; Drive `03_ideas/2026-11-20_I03`) | Voto de 6 jueces sellado sin leer (`jueces/votos/I03-idea-v5.json`); auditoría limpia | C58–C60; talleres en vivo de Konstruedu vetados (`fuentes-vetadas.yaml`); masterclass del 5-nov en pausa hasta que David decida |
