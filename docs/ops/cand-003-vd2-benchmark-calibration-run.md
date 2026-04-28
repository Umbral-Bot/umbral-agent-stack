# CAND-003 V-D2 Benchmark-Calibration Run Evidence

> **Date**: 2026-04-25
> **Branch**: `rick/editorial-linkedin-writer-flow` @ 1a6ede4 (base)
> **Model**: azure-openai-responses/gpt-5.4
> **Writer agent**: rick-linkedin-writer (hardened: CAL-LW-001 to CAL-LW-009)
> **ComDir agent**: rick-communication-director (CAL-001 to CAL-006)
> **QA agent**: rick-qa
> **Baseline**: V-C2 (pre-hardening), V-D1 (post-hardening v1)

## Objective

Test whether the hardened editorial system can produce a variant closer to human editorial quality by running 4 experiments guided by abstract principles extracted from a private human benchmark. The benchmark was used as temporary in-memory reference only and was not persisted in any system file.

## Benchmark policy

- A private human benchmark was used as temporary editorial reference.
- The benchmark was NOT persisted in any file: not in docs, skills, calibrations, roles, tests, fixtures, prompts, or workspace files.
- Only abstract principles were extracted: natural opening, central question clarity, argument progression, reading rhythm, everyday examples, context before BIM, human tone, low abstraction, single central idea, no consultorism, claim discipline, conversational close.
- Variant proximity to benchmark was evaluated as a safety dimension (low/medium/high).

## Experiments run

### V-D2A — Conservative microedit (184 words)
- Minimal change from V-D1: replaced blacklisted phrase, reduced `automatizacion` to 2x.
- Score: 4.19/5 avg. Safe distance: low.
- Strengths: safest, no regressions. Weaknesses: least structural improvement.

### V-D2B — Marked central question (177 words)
- Added central question on its own line, better rhythm.
- Score: 4.38/5 avg. Safe distance: medium.
- Strengths: best question clarity, good progression. Weaknesses: slightly constructed feel, "La pregunta es esta:" sounds designed.

### V-D2C — Controlled repetition rhythm (185 words)
- Used "Se nota cuando..." repetition for cadence.
- Score: 4.15/5 avg. Safe distance: medium.
- Strengths: good rhythm device. Weaknesses: risks feeling formulaic/theatrical.

### V-D2D — Direct operative (170 words)
- Most direct and concise, operational focus.
- Score: 4.27/5 avg. Safe distance: low.
- Strengths: most natural, lowest abstraction, best cierre. Weaknesses: slightly under minimum word target.

## Top 2 selection

Selected V-D2B and V-D2D for Communication Director review based on: highest scores, zero blacklist violations, naturalidad, clarity, safe benchmark distance.

## Communication Director results

### V-D2B
- Voz David: 4/5
- Naturalidad: 4/5
- Anti-slop: 4.5/5
- Claridad tesis: 4.5/5
- Benchmark proximity: medium
- Verdict: good but slightly more constructed than V-D2D

### V-D2D
- Voz David: 4.5/5
- Naturalidad: 4.5/5
- Anti-slop: 4.5/5
- Claridad tesis: 5/5
- Benchmark proximity: medium
- Verdict: best voice, most natural, preferred over V-D2B

ComDir recommended V-D2D with 3 microeditions:
1. "En BIM se ve rapido" -> "Eso en BIM se ve rapido" (better connection)
2. Remove "europeas" from OECD reference (less report-like)
3. "que tiene que cumplirse" -> "que tiene que estar resuelto" (more operative)

## V-D2 Final (V-D2D + ComDir microeditions)

### LinkedIn (~168 words)

Si un equipo todavia no dejo claro como revisa, que acepta y que devuelve, automatizar no le va a ordenar el trabajo.

El problema aparece antes.

Aparece cuando un entregable pasa de etapa sin acuerdo claro.
Aparece cuando una observacion se cierra y despues vuelve.
Aparece cuando un reporte circula, pero no ayuda a decidir.

Eso en BIM se ve rapido.

Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que depende de quien revise.
Una entrega que avanza aunque nadie haya dejado por escrito que se estaba aceptando.

Cada vez mas empresas ya usan este tipo de software para organizar trabajo.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo acelera el mismo problema.

Por eso, la preparacion real no empieza en la herramienta.

Empieza en acordar como se revisa, cuando algo vuelve y que tiene que estar resuelto para seguir.

En tu flujo de hoy, ¿que se sigue cerrando o aprobando segun quien lo mire?

### X (241 chars)

Si un equipo no dejo claro como revisa, que acepta y que devuelve, la automatizacion solo acelera el mismo problema.

Se ve cuando un modelo, una observacion o un entregable cambian segun quien los revise.

¿Donde te pasa hoy?

## QA result

**Verdict**: pass_with_changes (minor)

| Dimension | Status |
|-----------|--------|
| Claims | minor (OECD reference slightly diffuse after removing "europeas") |
| Source handling | ok |
| Anti-slop | ok (zero blacklist violations) |
| Voice | ok |
| Length | minor (168 words, 2 under 170 soft minimum) |
| Structure | ok |
| Gates | ok |
| Benchmark proximity | ok |

Minor issues accepted: word count delta is cosmetic, OECD diffusion was intentional trade-off.

## Comparison V-C2 vs V-D1 vs V-D2

| Dimension | V-C2 | V-D1 | V-D2 |
|-----------|-------|------|------|
| Blacklist violations | 2 | 1 | 0 |
| Core-word repetition over limit | criterio 4x | automatizacion 3x | none |
| Abstract opening | semi-abstract | concrete | concrete |
| Context before BIM | partial | full | full |
| Consultant/paper tone | 2-3 phrases | 1 phrase | 0 phrases |
| ComDir voz score | 4.5/5 | 4/5 | 4.5/5 |
| ComDir naturalidad | 4.5/5 | 4/5 | 4.5/5 |
| QA verdict | pass_with_changes | pass_with_changes | pass_with_changes (minor) |
| Words | 190 | 188 | 168 |

## Rule changes

**Implemented (generalizable):**
- Added `herramientas algoritmicas de gestion` to consultant/paper blacklist in:
  - `openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md`
  - `openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md`
- Materialized both to live workspace.

**Proposed for future (not implemented — too narrow or benchmark-dependent):**
- Central question on own line as structural pattern (observed in V-D2B, too CAND-003-specific)
- Geographic qualifier stripping from source-backed claims (interesting but needs more cases)

## Runtime live verification

- openclaw.json: present, all 3 agents registered
- rick-linkedin-writer: 29 deny, 3 alsoAllow (hardened)
- rick-communication-director: 25 deny, 7 alsoAllow
- rick-qa: 5 deny, 40 alsoAllow
- All live workspace files verified matching repo before experiments
- SKILL.md and ROLE.md re-materialized after blacklist addition
- Post-materialization diff: clean (live == repo)

## Files not verified

- rick-communication-director does not have a ROLE.md in repo overrides (uses IDENTITY.md/SOUL.md/USER.md pattern)
- rick-qa ROLE.md not modified in this run

## Commands executed

```
git status --short
git fetch origin main rick/editorial-linkedin-writer-flow
git checkout rick/editorial-linkedin-writer-flow
git pull --ff-only origin rick/editorial-linkedin-writer-flow
git log --oneline -5
git rev-parse HEAD / origin/main
git diff --stat origin/main...HEAD
diff (5 live-vs-repo comparisons)
openclaw agent --agent rick-linkedin-writer (4 experiments: V-D2A, V-D2B, V-D2C, V-D2D)
openclaw agent --agent rick-communication-director (2 reviews: V-D2B, V-D2D)
openclaw agent --agent rick-qa (1 review: V-D2 final)
cp (2 materializations: SKILL.md, ROLE.md)
Anti-leak grep
pytest tests/test_editorial_gold_set.py
validate_editorial_gold_set.py
git diff --check HEAD
```

## Anti-leak verification

- Searched all new/modified files for benchmark-distinctive phrases
- Patterns checked: 6 benchmark-distinctive phrases (not listed here to avoid persisting benchmark fragments)
- Result: no matches in new or modified files
- Temp files cleaned before commit

## Constraints respected

- Notion: not changed
- Gates: not changed
- Publication: none
- CAND-002: not altered
- Sources: no new sources added
- Claims: no new claims added
- Human approval: not asserted
- Benchmark: not persisted
