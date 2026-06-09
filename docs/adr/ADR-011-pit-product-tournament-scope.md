# ADR-011: Scope del torneo de producto (PIT) vs D3 vs Mission Control v2

## Estado

Draft — 2026-06-09

Relacionado: [`docs/adr/tournament-on-openclaw-primitives.md`](tournament-on-openclaw-primitives.md) (Decision A — wrapper-only, base de D3), [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md) (D3 code), [`docs/ops/product-innovation-tournament-vision-2026-06-09.md`](../ops/product-innovation-tournament-vision-2026-06-09.md) (visión PIT).

## Contexto

El formato torneo de Umbral nació para código (D3: 1 issue → N branches → 1 PR winner). David quiere aplicar la misma mecánica competitiva a **descubrimiento de producto**: explorar un problema con N lanes que investigan, hipotetizan, prototipan y miden KPI. Surgen tres preguntas de scope:

1. ¿PIT extiende el protocolo D3 (un "modo" dentro de docs/79) o es un protocolo hermano?
2. ¿Dónde vive el estado del torneo de producto (repo, Notion, Mission Control, Obsidian)?
3. ¿Qué le corresponde a Mission Control v2 vs a PIT?

## Decisión (draft)

**PIT es un protocolo hermano de D3, no una extensión.** Comparten primitivas OpenClaw (spawn `main` standalone, G-D1b/ISSUE-001, 2–5 lanes, presupuesto→timeout, cierre verificable) pero difieren en el contrato completo de lane:

| Dimensión | D3 code | PIT product |
|---|---|---|
| Spec | tournament spec (docs/79 §2–§3) | `pit_spec.yaml` ([schema v1](../schemas/pit-spec-v1.schema.json)) |
| Workspace de lane | git worktree (RC-4) | subárbol `pit/<pit_id>/lanes/<lane_id>/` en umbral-pit-vault |
| Iteraciones | 1 (un PR) | 2–10 (input David) |
| Cierre verificable | `PR_URL=` (gh pr view) | `PROTOTYPE_URL=` + `KPI_PACK=` + `FULFILLMENT=` (schema + recomputación) |
| Agentes | estables (rick-delivery, …) | efímeros por torneo |
| Juez | rubric sobre diff/checks | fulfillment_score + scorecard producto |

Razones de no-extensión:

- docs/79 tiene invariantes acoplados a git/gh (branch naming, PR title, worktrees) que no aplican a producto; forzar un modo dual degradaría ambos contratos.
- D3 está endurecido por tres retros (RC-1..RC-4); meterle un modo nuevo reabre riesgo en el carril que ya funciona.
- Los ciclos de vida difieren: D3 termina en merge; PIT termina en decisión de fulfillment + archive + handoff de mejora.

**Estado del torneo PIT vive en `umbral-pit-vault`** (Obsidian git, separado del vault personal pull-only): kanban, kpi_packs, prototipos, outcome. El repo guarda contratos/plantillas/validadores; Notion sigue siendo superficie HITL de decisiones; **Mission Control** es superficie de **observación y preview** (túnel del prototipo, métricas), no el store del torneo.

**Mission Control v2 queda fuera del scope PIT-1:** PIT-1 solo asume el MC existente como destino del preview por túnel. Cualquier widget/board PIT en MC v2 se especifica aparte cuando MC v2 tenga su propio carril.

## Consecuencias

- (+) D3 intacto (cero cambios a docs/79 y sus skills); PIT itera sin tocar el carril de código.
- (+) Contratos PIT testeables en CI sin runtime (schemas + validadores + fórmula fulfillment).
- (−) Dos protocolos para mantener; mitigación: el [índice de procesos](../ops/pit-process-index.md) + PIT-7 auditan drift.
- (−) El vault separado añade un repo git más; mitigación: `pit_vault_init.sh`/`pit_vault_check.py` lo mantienen barato.

## Pendientes para salir de draft

- [ ] PIT-2..PIT-5 implementados (research sandbox, deploy vault, generador efímeros, broker visual).
- [ ] Primer torneo piloto (PIT-6) corrido con gate David.
- [ ] Revisión de este ADR contra lo aprendido (PIT-7) → Accepted o superseded.
