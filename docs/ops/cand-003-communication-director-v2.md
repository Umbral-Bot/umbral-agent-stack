# CAND-003 — Communication Director V2

> **Date**: 2026-04-23
> **Agent**: rick-communication-director
> **Model**: azure-openai-responses/gpt-5.4
> **Run ID**: 79bb5669-60a5-44ae-bce5-09064442de1d
> **Voice source**: Resumen autorizado (guía de voz de Notion no accesible por integración)
> **Estado**: dry-run, no publicado, gates intactos

---

## 1. Diagnóstico breve

La versión anterior puede fallar en voz por tres cosas:

- Suena demasiado auditada y poco conversacional. Tiene lógica, pero no siempre suena a algo que David diría hablando con un BIM manager o con un líder de coordinación.
- Usa términos poco naturales para este contexto, especialmente "escalación", y varias frases con tono de marco metodológico más que de criterio operativo real.
- Repite estructuras abstractas como "criterio explícito", "supervisión humana implícita", "herramientas algorítmicas de gestión" sin aterrizarlas siempre en escenas reconocibles de AEC/BIM.

## 2. Frases o palabras que David probablemente no diría

- "sumar una herramienta más de IA"
- "la mayoría de equipos AEC no se hacen"
- "criterio operativo explícito" repetido demasiadas veces
- "que dispara una escalación en coordinación"
- "herramientas algorítmicas de gestión"
- "los estándares para auditar esas herramientas recién se están proponiendo"
- "guardarraíles"
- "la supervisión humana sigue siendo implícita"
- "coordinación que funciona por costumbre" si no se baja a operación concreta
- "aceptan por inercia"
- "la pregunta operativa es más básica"

Reemplazos más naturales en voz David:

- "meter IA"
- "tener claro"
- "qué revisión vale"
- "qué obliga a levantar el tema"
- "qué alcanza para coordinar bien"
- "qué se acepta y por qué"
- "automatizar un criterio flojo"
- "ir más rápido, pero mal"

## 3. Copy LinkedIn V2

En AEC, el problema no suele ser la falta de IA. Suele ser la falta de criterio claro.

Si un equipo todavía no tiene definido qué cuenta como una revisión válida de un modelo BIM, cuándo un tema necesita subirse, o qué nivel de coordinación ya es suficiente para seguir, meter automatización no ordena nada. Solo hace más rápido un proceso que ya venía ambiguo.

Y ahí está el punto. La IA no corrige criterios mal definidos. Los ejecuta a escala.

Esto no pasa solo en construcción. Hoy muchas empresas ya usan sistemas algorítmicos para gestionar trabajo, mientras los marcos de auditoría y gobierno todavía se están consolidando. La tecnología avanza más rápido que la claridad operativa.

En AEC/BIM eso se ve muy fácil:
revisiones que cambian según quién las haga,
coordinación que depende de experiencia informal,
entregables que se dan por buenos sin una regla de aceptación realmente clara.

Automatizar sobre esa base no acelera el negocio. Amplifica la ambigüedad.

Antes de escalar con IA, la conversación útil no es qué herramienta comprar.
Es algo más incómodo y más importante:

mi equipo tiene claro qué revisión vale, qué situación obliga a intervenir y qué nivel de coordinación es suficiente para avanzar.

Si eso no está definido, el cuello de botella no es la herramienta. Es el criterio.

## 4. Copy X V2

En AEC, la IA no arregla un criterio flojo. Lo ejecuta más rápido.

Si tu equipo no tiene claro qué revisión BIM vale, cuándo un tema hay que subirlo y qué nivel de coordinación es suficiente, automatizar no acelera: amplifica la ambigüedad.

Antes de más IA, más criterio.

## 5. Score editorial

| Dimensión | Score |
|-----------|-------|
| voz David | 4.5/5 |
| naturalidad | 4.5/5 |
| densidad AEC/BIM | 4/5 |
| ausencia de slop | 4.5/5 |
| claridad de tesis | 5/5 |
| riesgo de claim | medio |

## 6. Riesgos de atribución o claim

- "Hoy muchas empresas ya usan sistemas algorítmicos para gestionar trabajo" está alineado con OECD 2025, pero conviene no poner cifra en esta versión si no se va a citar explícitamente en el post o en comentario de soporte.
- "los marcos de auditoría y gobierno todavía se están consolidando" es defendible con AVERI y frontier agent governance, pero sigue siendo una síntesis interpretativa. Mejor mantenerla como framing general, no como afirmación técnica cerrada.
- "la IA no corrige criterios mal definidos. Los ejecuta a escala" es una buena tesis editorial, pero es una formulación fuerte. Está bien como lectura estratégica, no como claim cuantitativo.
- En X, "qué nivel de coordinación es suficiente" mantiene la premisa aprobada sin meter fuente nueva ni sobrepromesa.

## 7. Handoff recomendado para rick-qa

Validar tres cosas antes de siguiente pasada:

- que "subirlo" y "necesita subirse" sean aceptables como reemplazo público de "escalación" sin perder precisión operativa,
- que la frase "no acelera el negocio" no suba innecesariamente el nivel del claim, si prefieren puede quedar en "no mejora el proceso",
- que el bloque de contexto externo siga trazable a OECD + AVERI + frontier governance aunque en esta versión no se expongan cifras.

Si QA detecta sensibilidad en claim, ajuste conservador recomendado:
cambiar "Los ejecuta a escala" por "Los vuelve más visibles y más costosos".

## 8. Estado

- **dry-run**: sí
- **publicado**: no
- **gates**: intactos (`aprobado_contenido=false`, `autorizar_publicacion=false`, `gate_invalidado=false`)
- **Notion editado**: no
- **CAND-002 tocado**: no

## Verificación de seguridad

- No se expusieron secretos, tokens ni API keys
- No se escribió en Notion
- No se publicó en ninguna plataforma
- No se modificaron gates humanos
- No se activó runtime de publicación
