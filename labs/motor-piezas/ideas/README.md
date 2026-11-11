# Fábrica de ideas · etapa 1 del camino B

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
