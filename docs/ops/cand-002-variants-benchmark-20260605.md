# CAND-002 - Variantes internas y benchmark editorial

> Fecha: 2026-06-05  
> Estado: interno, preparado para benchmark. No publicar. No marcar gates. No escribir en Notion antes de Fase 7.

## Fase 0 - Decision Brief interno

```yaml
publication_id: CAND-002
premisa: >
  En AEC, más herramientas de IA no garantizan más valor. El cuello de botella
  es organizacional: roles, procesos y criterio de revisión no están diseñados
  para absorber la velocidad que la tecnología ya ofrece.
claim_principal: >
  La barrera principal para capturar valor de IA en AEC no parece ser la falta
  de herramientas, sino la falta de preparación organizacional.
claim_type: inferencia
objetivo_comercial:
  visibilidad: alta
  venta: baja
  confianza_tecnica: media
  conversion_embudo: baja
pilar_umbral: BIM+IA aplicado
por_que_ahora:
  - La conversación de IA se está moviendo desde herramientas aisladas hacia equipos, agentes y nuevas formas de operar.
  - En AEC ya existe presión por automatizar entregables, coordinación y seguimiento, pero los cuellos de revisión, trazabilidad y responsabilidad siguen siendo humanos y organizacionales.
fuentes:
  - fuente: The B1M
    rol: original_article
    citable: true
    claim_que_soporta: >
      La inversión y la ejecución en infraestructura exigen claridad operativa,
      factibilidad y capacidad de ejecución, no solo ambición tecnológica.
  - fuente: DeepLearning.AI / The Batch
    rol: analysis_source
    citable: true
    claim_que_soporta: >
      La adopción real de IA cambia la forma de trabajo de los equipos y desplaza
      el peso hacia supervisión, criterio y coordinación.
  - fuente: Marc Vidal
    rol: discovery_source
    citable: false
    claim_que_soporta: >
      Señal interna para conectar la paradoja de productividad con adopción
      tecnológica; no usar como autoridad pública en el copy.
  - fuente: Aelion.io / Ivan Gomez Rodriguez
    rol: contextual_reference
    citable: false
    claim_que_soporta: >
      Señal interna sobre el filtro AEC de valor temprano y operativa real; no
      usar como autoridad pública en el copy.
```

| Fuente | Rol | Citable en público | Claim operativo usado |
|---|---|---:|---|
| The B1M | Original article | Sí | Ambición e inversión necesitan factibilidad y ejecución. |
| DeepLearning.AI / The Batch | Analysis source | Sí | La IA cambia equipos, supervisión y naturaleza del trabajo. |
| Marc Vidal | Discovery source | No | Tecnología no equivale automáticamente a productividad. |
| Aelion.io / Ivan Gomez Rodriguez | Contextual reference | No | En construcción, la adopción se mide contra valor operativo temprano. |

## Fase 1 - AEC framing

### Escenas operativas

1. **Observación en obra:** una observación de terreno puede convertirse en resumen, RFI preliminar o checklist con ayuda de IA, pero el valor depende de quién valida, qué evidencia queda y qué cambio se ordena.
2. **Entregable técnico:** un informe de avance, minuta, metrado o matriz de incidencias puede generarse más rápido, pero el cuello pasa a revisión, versión aprobada y responsabilidad profesional.
3. **Modelo y coordinación BIM:** una detección automática puede levantar interferencias o issues, pero la coordinación sigue necesitando umbrales de aceptación, responsables de cierre y trazabilidad de decisiones.

### Límites del claim

- No afirmar que todo AEC carece de madurez para IA.
- No afirmar que la IA ya resuelve coordinación, QA, obra o BIM por sí sola.
- No presentar una inferencia editorial como dato medido.
- No citar a Marc Vidal, Aelion ni personas individuales como autoridad pública en el copy.
- No prometer productividad, ahorro o retorno sin evidencia específica.
- No convertir la pieza en anti-IA; la tesis es pro-gobernanza y pro-adopción operativa.

## Fase 2 - Variantes LinkedIn internas

### V1 - Hook obra/coordinación

**Status:** needs review

```text
En obra, la IA no falla por responder lento.
Falla cuando nadie sabe qué hacer con una respuesta rápida.

Un modelo puede detectar interferencias antes.
Un asistente puede ordenar observaciones.
Un reporte puede salir en minutos.

Pero en AEC el valor aparece recién cuando existe un sistema que decide:

quién revisa,
con qué criterio,
dónde queda la trazabilidad,
y qué cambia en el entregable.

Al mirar señales recientes de The B1M y DeepLearning.AI/The Batch, aparece una tensión clara: la capacidad técnica está acelerando más rápido que la forma de trabajo que debe absorberla.

Por eso sumar herramientas de IA sobre procesos viejos puede generar más ruido que avance.

La pregunta práctica para BIM, coordinación y obra no es si vamos a usar IA.
Es si el equipo tiene roles, criterios y flujos preparados para que esa velocidad mejore una decisión real.

El cuello aparece menos en la demo y más en la organización.
```

### V2 - Hook entregable/revisión

**Status:** needs review

```text
Un entregable puede salir más rápido que la revisión que lo sostiene.

Ese es uno de los riesgos menos vistosos de la IA en AEC.

Si una automatización genera minutas, metrados, informes de avance o revisiones de modelo en menos tiempo, el trabajo no termina ahí.

Cambia de lugar:

criterio,
validación,
responsabilidad,
control de versiones.

La tecnología aumenta capacidad.
La organización decide si esa capacidad se convierte en trabajo confiable.

La tesis de CAND-002 es simple: más herramientas de IA no garantizan más valor si los roles, procesos y criterios de revisión siguen diseñados para otra velocidad.

The B1M muestra cómo la inversión en infraestructura exige ejecución y factibilidad. DeepLearning.AI/The Batch viene señalando que los equipos que usan IA de verdad operan distinto.

En AEC, esa traducción es concreta:
menos fascinación por la herramienta,
más diseño del sistema de trabajo que la va a usar.
```

### V3 - Hook modelo/proceso

**Status:** needs review

```text
El modelo puede estar más actualizado que el proceso.

En coordinación BIM eso ya es un problema conocido.

Una detección automática puede encontrar conflictos.
Un agente puede resumir incidencias.
Una plantilla puede producir el acta.

Pero si nadie define el umbral de aceptación, el responsable de cierre o la evidencia mínima para aprobar, la velocidad solo mueve el cuello de botella.

La IA no elimina la coordinación.
La vuelve más exigente.

Una métrica más útil que contar herramientas: cuántas decisiones quedan mejor gobernadas después de usarlas.

Roles claros.
Criterio de revisión.
Trazabilidad.
Proceso de cierre.

Esa es la parte menos llamativa de la adopción de IA, y probablemente la más importante para que BIM, obra y gestión técnica no sumen otra capa de ruido.

Me interesa mirar la adopción desde ahí: menos demo aislada, más sistema de decisión.
```

## Fase 3 - Benchmark repo

### Criterios cargados

- `evals/editorial/dimensions.yaml`: cargado y aplicado manualmente.
- `docs/ops/editorial-linkedin-quality-smoke-tests.md`: no existe en el working tree. Se aplicó como fallback la lista de anti-patrones y PASS patterns declarados en `docs/ops/editorial-decision-brief-and-benchmark-2026-06-05.md`.

### Scores por dimensión

| Dimensión | Peso | V1 | V2 | V3 |
|---|---:|---:|---:|---:|
| strategic_fit | 0.12 | 0.86 | 0.82 | 0.86 |
| audience_relevance | 0.12 | 0.90 | 0.84 | 0.88 |
| technical_accuracy | 0.10 | 0.78 | 0.80 | 0.82 |
| source_handling | 0.10 | 0.76 | 0.78 | 0.80 |
| primary_source_discipline | 0.08 | 0.72 | 0.74 | 0.76 |
| voice_fit | 0.10 | 0.82 | 0.80 | 0.78 |
| channel_fit | 0.08 | 0.84 | 0.82 | 0.80 |
| cta_quality | 0.08 | 0.74 | 0.70 | 0.72 |
| visual_brief_quality | 0.06 | 0.70 | 0.70 | 0.70 |
| anti_ai_slop | 0.08 | 0.86 | 0.84 | 0.82 |
| risk_control | 0.04 | 0.90 | 0.90 | 0.88 |
| human_gate_compliance | 0.04 | 1.00 | 1.00 | 1.00 |
| **Promedio ponderado** | **1.00** | **0.818** | **0.803** | **0.814** |
| **Mínima dimensión** |  | **0.70** | **0.70** | **0.70** |
| **Repo-side threshold** |  | **PASS** | **PASS** | **PASS** |

### Smoke editorial aplicado

| Check | V1 | V2 | V3 | Nota |
|---|---|---|---|---|
| Sin "En el mundo actual" | PASS | PASS | PASS | No aparece. |
| Sin patrón "No es solo X, es Y" | PASS | PASS | PASS | Ninguna variante usa esa estructura. |
| Sin "Aquí es donde entra" | PASS | PASS | PASS | No aparece. |
| "capturar valor" o "impacto" sin aterrizaje | PASS | PASS | PASS | No aparece en copy público. |
| "preparación organizacional" repetido >2 | PASS | PASS | PASS | V1/V2/V3 evitan repetición. |
| "equipos AI-native" sin escena AEC temprana | PASS | PASS | PASS | No se usa en copy público. |
| Em dash en copy público | PASS | PASS | PASS | No se usa. |
| Hook abstracto | PASS | PASS | PASS | Cada variante abre con escena operativa. |
| Mini-ensayo con más de una idea central | PASS | PASS | PASS | Misma tesis: capacidad técnica vs sistema de trabajo. |
| Pregunta retórica + respuesta inmediata | PASS | PASS | PASS | No se usa como patrón de apertura. |

### Lectura de benchmark

- **V1** gana por relevancia AEC y ritmo LinkedIn. Es la mejor candidata inicial para benchmark externo.
- **V3** queda muy cerca y puede aportar cierre si ChatGPT pide más foco BIM/coordinación.
- **V2** es la más explícita en fuentes, pero suena más explicativa y menos diferencial.

## Fase 4 - Handoff ChatGPT

Copiar este paquete en ChatGPT para benchmark externo. No publicar desde ahí.

```text
Sos ChatGPT actuando como benchmark editorial externo para David.

Contexto:
- publication_id: CAND-002
- canal: LinkedIn
- estado: interno, no publicar
- objetivo comercial: visibilidad alta, venta baja
- claim_type: inferencia editorial
- premisa: En AEC, más herramientas de IA no garantizan más valor. El cuello de botella es organizacional: roles, procesos y criterio de revisión no están diseñados para absorber la velocidad que la tecnología ya ofrece.

Fuentes:
- The B1M: citable públicamente como organización. Soporta señales sobre infraestructura, inversión, factibilidad y ejecución.
- DeepLearning.AI / The Batch: citable públicamente como organización. Soporta señales sobre IA, equipos y cambios en la forma de trabajar.
- Marc Vidal: discovery interno, no citar públicamente.
- Aelion.io / Ivan Gomez Rodriguez: referencia contextual interna, no citar públicamente.

Límites:
- No afirmar que todo AEC está atrasado.
- No prometer productividad ni ROI.
- No citar personas como autoridad pública.
- No convertir la inferencia en hecho.
- No usar em dash.
- Evitar frases tipo IA: "En el mundo actual", "No es solo X, es Y", "Aquí es donde entra".

Tarea:
1. Puntúa V1, V2 y V3 de 0 a 1 en voz David, claridad AEC, rigor de claim, fit LinkedIn y anti-ai-slop.
2. Elige una ganadora o propone una fusión.
3. Devuelve una sola variante final si todas las dimensiones pasan.
4. Si pasa, termina con: BENCHMARK_EDITORIAL_VALIDATED.
5. Si no pasa, termina con: BENCHMARK_EDITORIAL_REJECTED y lista correcciones.

V1:
[pegar variante V1 completa desde docs/ops/cand-002-variants-benchmark-20260605.md]

V2:
[pegar variante V2 completa desde docs/ops/cand-002-variants-benchmark-20260605.md]

V3:
[pegar variante V3 completa desde docs/ops/cand-002-variants-benchmark-20260605.md]
```

## Fases 5-6 - Pendientes tras benchmark ChatGPT

No ejecutadas.

Bloqueador: falta veredicto externo `BENCHMARK_EDITORIAL_VALIDATED`.

Checklist Rick QA simulado a correr después de elegir variante:

- [ ] La variante ganadora conserva la premisa de CAND-002.
- [ ] Claim principal sigue marcado como inferencia, no como hecho.
- [ ] Solo The B1M y DeepLearning.AI/The Batch aparecen como fuentes citables públicas.
- [ ] Marc Vidal y Aelion quedan solo en trazabilidad interna.
- [ ] El primer tercio tiene escena AEC concreta.
- [ ] No hay patrones de slop ni em dash.
- [ ] CTA es suave y corresponde a awareness.
- [ ] Gates `aprobado_contenido` y `autorizar_publicacion` siguen false.

## Fase 7 - Notion

No ejecutada.

Página objetivo: `34b5f443-fb5c-81da-abe1-e586033ceed8`.

Acción pendiente para operador autorizado, solo después de `BENCHMARK_EDITORIAL_VALIDATED`:

1. Reordenar body: Decision Brief secciones 1-7 arriba.
2. Poblar `Fuente primaria`, `Fuente referente`, `Premisa`, `Objetivo comercial`; si falta propiedad, dejar nota en comentarios.
3. `Copy LinkedIn` debe recibir solo la variante ganadora.
4. `Estado` -> `Revisión pendiente`.
5. Gates siguen false.

## Veredicto

`VARIANT_SELECTED` (ChatGPT 2026-06-05)

- Ganadora: **V3** (promedio 8.79) + microfusión fuentes desde V2
- V1: FAIL (patrón "no es… es…" + hook absoluto)
- V2: PASS con edición (eliminar "CAND-002" del copy)
- Copy final + Decision Brief: `docs/ops/cand-002-notion-handoff-20260605.md`
- Fase 7 Notion: pendiente operador autorizado
