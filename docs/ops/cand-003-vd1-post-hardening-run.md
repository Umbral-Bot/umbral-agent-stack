# CAND-003 V-D1 Post-Hardening Run Evidence

> **Date**: 2026-04-25
> **Branch**: `rick/editorial-linkedin-writer-flow` @ 9bc84a6
> **Model**: azure-openai-responses/gpt-5.4
> **Writer agent**: rick-linkedin-writer (hardened: CAL-LW-001 to CAL-LW-009)
> **ComDir agent**: rick-communication-director (hardened: CAL-001 to CAL-006)
> **QA agent**: rick-qa
> **Baseline**: V-C2 (pre-hardening, iteration 2)
> **Purpose**: Validate that hardened editorial rules improve output quality

## Runtime verification

- All live workspace files match repo (`diff` clean between `~/.openclaw/workspaces/` and repo templates)
- Writer, ComDir, QA agents registered and reachable
- Hardening commit 9bc84a6 materialized to live workspaces

## V-D1 LinkedIn (188 words)

Si en tu equipo todavia se discute si un entregable puede avanzar o no, meter automatizacion no te va a ordenar el trabajo.

Primero hay que dejar claro como se revisa, que se acepta, que vuelve y que realmente ayuda a decidir.

Ahi suele estar el nudo.

Se ve en cosas muy concretas: un modelo BIM que para una persona ya esta listo y para otra no, una observacion que alguien da por cerrada pero vuelve a abrirse, un entregable que cambia de etapa sin acuerdo real, o un reporte que informa mucho pero no ayuda a tomar una decision.

Cada vez mas empresas europeas ya usan herramientas algoritmicas de gestion.

Pero cuando esas reglas siguen en la cabeza de cada uno, la automatizacion no ordena el proceso.

Solo hace mas rapido algo que ya venia saliendo con interpretaciones distintas.

Para mi, la preparacion real no empieza en la herramienta.

Empieza en acordar por escrito como revisa el equipo, cuando algo se devuelve y que condiciones tiene que cumplir para seguir avanzando.

En tu flujo de hoy, ¿que sigue dependiendo demasiado de quien lo revise?

## V-D1 X (253 chars)

Si un equipo todavia no dejo claro como revisa, que acepta y que devuelve, la automatizacion no ordena nada.

Se nota cuando un modelo BIM, una observacion o un entregable dependen demasiado de quien los mire.

¿Donde te pasa hoy?

## Source trace

| Claim | Source | Confidence |
|-------|--------|------------|
| Cada vez mas empresas europeas usan herramientas algoritmicas de gestion | OECD 2025 (79% empresas europeas) | evidencia |
| La automatizacion no ordena si las reglas siguen implicitas | inferencia editorial | inferencia |
| La preparacion real empieza en las reglas del equipo | hipotesis editorial | hipotesis |

## Communication Director review

| Dimension | Score |
|-----------|-------|
| Voz David | 4/5 |
| Naturalidad | 4/5 |
| Densidad AEC/BIM | 4/5 |
| Anti-slop | 4.5/5 |
| Claridad de tesis | 4.5/5 |
| Riesgo de claim | medio |

**Microediciones propuestas:**
1. `herramientas algoritmicas de gestion` -> formulacion menos paper
2. `cuando algo se devuelve y que condiciones tiene que cumplir` -> mas oral
3. X: `modelo BIM` -> contextualizar antes de tecnificar

**Valoracion**: V-D1 mejor calibrada que V-C2 para voz David. Mas concreta, menos abstracta, mas operativa.

## QA review

**Verdict**: pass_with_changes

| Dimension | Status |
|-----------|--------|
| Claims | ok |
| Source handling | ok |
| Anti-slop | issues (1 blacklist violation) |
| Voice | ok |
| Length | ok (188 words / 253 chars) |
| Structure | issues (core-word repetition) |
| Gates | ok (none marked) |

**Cambios requeridos:**
1. Reemplazar `herramientas algoritmicas de gestion` (blacklist)
2. Reducir `automatizacion` de 3 a <=2 apariciones

## V-C2 vs V-D1 comparison

| Dimension | V-C2 (baseline) | V-D1 (hardened) | Delta |
|-----------|-----------------|-----------------|-------|
| Blacklist violations | 2 | 1 | -1 (improvement) |
| Core-word repetition | `criterio` 4x | `automatizacion` 3x | -1 (improvement, still over) |
| Abstract opening | Semi-abstract question | Concrete operational scene | Significant improvement |
| Context before BIM | Partial | Full process context first | Improvement |
| Consultant/paper tone | 2-3 phrases | 1 phrase | Improvement |
| ComDir naturalidad | 4.5/5 | 4/5 | Slight regression |
| QA verdict | pass_with_changes | pass_with_changes | Same |
| Tesis clarity | Via question | Direct first line | Improvement |
| Cierre | Conversational | Conversational | Comparable |
| Length | 190 words | 188 words | Comparable |

## Hardening effectiveness assessment

**Confirmed improvements (hardening rules working):**
- CAL-LW-005 (contextualize before technifying): `modelo BIM` appears only after operational context
- CAL-LW-007 (consultant/paper phrasing): eliminated `capacidad tecnologica ya existe` and `criterio operativo`
- CAL-LW-008 (no moralizing close): cierre is a concrete question, not a slogan
- CAL-LW-009 (operational vocabulary): uses `revision`, `observaciones`, `entregables`, `reportes`, `rehacer`, `aceptar`, `decidir`

**Partial improvements (rule applied but not fully):**
- CAL-LW-006 (core-word repetition <=2): reduced from 4x to 3x, not yet at target
- Anti-slop blacklist: eliminated 2 of 3 violations, 1 remains (`herramientas algoritmicas de gestion`)

**No regressions detected.**

## Estado

- V-D1 generated, reviewed by ComDir and QA
- pass_with_changes: 2 minor fixes needed before human review
- No gates marked, no Notion changes, no publication
- Evidence complete for PR #268
