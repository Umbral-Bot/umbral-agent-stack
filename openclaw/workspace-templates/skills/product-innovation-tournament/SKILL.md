---
name: product-innovation-tournament
description: >-
  PIT — Product Innovation Tournament: parser NL + alias /torneo_producto que
  convierte un pedido de David en pit_spec.yaml validado, confirma con gate
  literal "ok, arranca" y orquesta N lanes efímeras que compiten con
  prototipos + KPI (PROTOTYPE_URL + KPI_PACK + fulfillment). NO es el torneo
  de código D3 (PR_URL) — ese es multi-agent-tournament-orchestrator.
metadata:
  openclaw:
    emoji: "🧪"
    requires:
      env: []
---

# Product Innovation Tournament (PIT)

Skill de Rick para torneos de **producto**: lanes paralelas que investigan, formulan hipótesis, prototipan y miden KPI. Implementa [`docs/ops/product-innovation-tournament-vision-2026-06-09.md`](../../../../docs/ops/product-innovation-tournament-vision-2026-06-09.md); contrato de entrada en [`docs/schemas/pit-spec-v1.schema.json`](../../../../docs/schemas/pit-spec-v1.schema.json).

**Status:** v1.1 (PIT-2) — parser + gate + contratos + runner smoke local (tasks `pit.*` + dry-run, [`docs/ops/pit-2-runner-protocol.md`](../../../../docs/ops/pit-2-runner-protocol.md)). El spawn real de agentes efímeros OpenClaw es **PIT-2b** (siguiente PR) y requiere pit-vault desplegado + autorización David por torneo.

## When to use

- David pide un torneo de **producto/innovación**: "torneo de producto", "PIT", "competí ideas de…", "explorá qué producto…", o el alias **`/torneo_producto`**.
- La salida deseada son **prototipos con KPI medidos**, no un PR de código.

## When NOT to use — contraste D3 vs PIT

| | **D3 code** | **PIT product** |
|---|---|---|
| Skill | `multi-agent-tournament-orchestrator` | `product-innovation-tournament` (esta) |
| Input | tournament spec (docs/79 §2–§3) sobre un issue | `pit_spec.yaml` (schema v1) sobre un problema |
| Unidad de competencia | rama + PR sobre `main` | hipótesis + prototipo + KPI por iteración |
| Cierre de lane | línea literal `PR_URL=` verificable con `gh pr view` | líneas literales `PROTOTYPE_URL=` + `KPI_PACK=` + `FULFILLMENT=` verificables en el pit-vault |
| Juez | rubric sobre diffs/checks (judge kit D3.5) | fulfillment_score + scorecard producto |
| Workspace | git worktree por lane (RC-4) | subárbol `pit/<pit_id>/lanes/<lane_id>/` en umbral-pit-vault |
| Agentes | agentes existentes (rick-delivery, …) | **efímeros nuevos por torneo** (Rick los genera) |
| Iteraciones | 1 (un PR) | `iteration_count` 2–10 (input David) |
| Merge/fulfillment | `gh pr merge` con gate David | decisión fulfillment en outcome report con gate David |

Si el pedido es ambiguo ("torneo sobre X"), preguntar: *"¿D3 código (PR) o PIT producto (prototipo + KPI)?"* — nunca asumir.

---

## Invocación

Dos superficies, **mismo parser, mismo gate**:

1. **NL:** "Rick, armá un torneo de producto sobre carga mental en obra, 3 lanes, 5 iteraciones, 200 USD."
2. **Alias:** `/torneo_producto <descripción libre con parámetros>`

### Parser NL → pit_spec.yaml

Extraer del mensaje de David estas variables; lo que falte se **pregunta**, no se inventa:

| Variable | Regla de extracción | ¿Default silencioso? |
|---|---|---|
| `pit_id` | slug desde el título (`pit-<tema>-<n>`) | sí (derivado) |
| `title` / `problem_statement` | del texto libre | se confirma en el gate |
| `lane_count` | "N lanes/agentes/carriles" → 2–5 | **NO — preguntar** |
| `iteration_count` | "N iteraciones/rondas" → 2–10 | **NO — preguntar SIEMPRE** |
| `budget_usd` | "N USD/dólares de budget" | **NO — preguntar SIEMPRE; jamás default** |
| `prototype_output` | "html" / "figma" / "both" | `html` (v1) |
| `research_profile` | "académico/papers" → `academic`; "dolores/mercado" → `market_pain`; "competencia" → `competitive`; mezcla o nada → `mixed` (confirmar en gate) | `mixed` |
| `kpi_definitions` | KPIs con unidad y objetivo ("60% de check-ins") | **NO — si no hay ≥1 KPI con kpi_expected, preguntar** |
| `visual_generation` | "con visuales/mockups Magnific" → enabled + `aspect_ratio: "4:3"` (default canónico; otro ratio solo si David lo pide explícito) | enabled=false |
| `synthetic_personas` | "con personas sintéticas" → enabled (labeled siempre true) | enabled=false |
| `hypothesis_seed` | si David ya trae una hipótesis | null |
| `template_name` | — (ver Plantillas) | null |

Reglas duras del parser:

- `budget_usd` e `iteration_count` **siempre** salen de input David. Si el mensaje no los trae, la respuesta es una pregunta, no un spec.
- Escribir el spec en `pit/<pit_id>/spec/pit_spec.yaml` (pit-vault) **solo después** del gate.
- Validar SIEMPRE antes del gate: `python scripts/pit/pit_spec_validate.py <spec.yaml>` debe dar `pass`.

### Plantillas

- **Guardar:** si David dice "guarda como plantilla PIT `<nombre>`" → persistir el spec (sin `pit_id` concreto) en `templates/pit-<nombre>.yaml` del pit-vault y setear `template_name` en el spec original.
- **Usar:** "torneo desde plantilla `<nombre>`" → cargar `templates/pit-<nombre>.yaml` como base del parser; `budget_usd` e `iteration_count` se vuelven a preguntar **siempre** (no se heredan en silencio).

---

## Fase de confirmación (obligatoria — sin excepción)

Antes de cualquier spawn, Rick presenta el spec renderizado y espera el gate:

```text
PIT listo para arrancar — confirmá:

  pit_id:           pit-salud-mental-pilot
  lanes:            3 (agentes efímeros nuevos)
  iteraciones:      5
  budget:           200 USD (66.67 por lane)
  prototipo:        html · preview: túnel + Mission Control (NO URL pública)
  research:         mixed
  KPIs:             checkin_completion (60 %), time_to_checkin (30 s ↓), opt_in_signals (5 usuarios)
  visual:           Magnific 4:3 (gate: columna Prototype)
  personas sint.:   sí, etiquetadas

Para lanzar respondé literalmente: ok, arranca
```

- **Solo** la frase literal **`ok, arranca`** dispara el spawn. "dale", "sí", "go" → repetir el gate.
- Cualquier corrección de David → re-parsear, re-validar, re-presentar el gate.
- Sin respuesta = sin torneo. No hay auto-arranque.

---

## Smoke runner PIT-2 (post-gate, pre-spawn — obligatorio)

Recibido el literal `ok, arranca`, Rick **NO spawnea todavía**: primero corre el smoke local del runner ([`docs/ops/pit-2-runner-protocol.md`](../../../../docs/ops/pit-2-runner-protocol.md)):

1. **`pit.preflight`** (Worker task) — valida `pit_spec.yaml`, budget (`budget_usd` = max cost estimate; kill switch @100 % documentado, enforcement real PIT-3), vault path y `pit_vault_check`. Veredicto requerido: `PIT_PREFLIGHT_PASS`.
2. **`bash scripts/pit/pit_tournament_dry_run.sh <spec.yaml>`** — simula las N lanes en secuencia (init → 1 iteración fake → fulfillment → announce) sobre un vault scratch. Sin internet, sin Magnific, sin `sessions_spawn`. Evidencia: `~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json` con veredicto `PIT_DRY_RUN_PASS`.

Smoke rojo ⇒ STOP: se corrige spec/vault/runner y se repite. No hay spawn con smoke rojo.

> **PIT-2b (siguiente PR):** el spawn real de agentes efímeros OpenClaw (`sessions_spawn` + generador de efímeros + announce real por sesión). Esta versión del runner NO spawnea agentes — la sección siguiente queda como contrato para PIT-2b.

## Spawn — agentes efímeros (PIT-2b, contrato)

Procedimiento completo en [`docs/ops/pit-ephemeral-agent-generator.md`](../../../../docs/ops/pit-ephemeral-agent-generator.md). Resumen del contrato:

1. Rick genera **por torneo** `lane_count` agentes efímeros nuevos (prompt desde [`pit-lane-agent/ROLE.template.md`](../../pit-lane-agent/ROLE.template.md), skills mínimas, accesos acotados). No se reutilizan agentes de torneos anteriores.
2. Cada lane recibe: su `lane_id`, el spec, `budget_usd / lane_count`, `iteration_count`, write scope `pit/<pit_id>/lanes/<lane_id>/` y el tablero kanban inicial desde `templates/kanban-lane.md`.
3. Límites heredados de OpenClaw: 2–5 lanes (`maxChildrenPerAgent: 5`), spawn desde `main` standalone (G-D1b, ISSUE-001) — mismas hard rules que D3.
4. Al cierre del torneo los agentes efímeros se desactivan (kill + limpieza de registro); sus artefactos quedan en el vault.

### Ciclo por lane (× iteration_count)

`Research → Hypothesis → Prototype → KPI Track → Fulfillment → Review` sobre el tablero de 9 columnas ([protocolo](../../../../docs/ops/pit-kanban-kpi-protocol.md)). Research según `research_profile` (tiers: academic | market_pain | competitive | mixed). Visual Magnific solo con gate de columna ([pit-visual-magnific](../../../../docs/ops/pit-visual-magnific.md)); Rick es el broker — las lanes **no** llaman a Magnific directo.

---

## Cierre de lane (collect gate)

Una lane está completa **solo** si su announce final termina con las tres líneas literales:

```text
PROTOTYPE_URL=<url túnel/Mission Control>
KPI_PACK=pit/<pit_id>/lanes/<lane_id>/iterations/<n>/kpi_pack.json
FULFILLMENT=<score 0-1>
```

Verificación del parent (regla de verdad, paralela a docs/79 §4.1):

```text
lane_complete = prototype_reachable && kpi_pack_valido_contra_schema && fulfillment == compute_fulfillment(kpi_pack.kpis)
```

- `kpi_pack.json` debe validar contra `kpi-pack.schema.json` y su `fulfillment_score` debe reproducirse con `compute_fulfillment()`. Verificación ejecutable: task `pit.lane_announce` → `lane_complete` + `incomplete_reasons` (PIT-2).
- `finalStatus=success` sin esas tres líneas verificables ⇒ `lane_incomplete`.
- Judge solo con ≥2 lanes completas; el winner y la decisión de fulfillment llevan gate David y se registran en [`pit_outcome_report.yaml`](../../pit-vault/templates/pit_outcome_report.yaml).

---

## Hard stops

| Condición | Acción |
|---|---|
| Falta `budget_usd` o `iteration_count` en el input | STOP — preguntar a David (jamás default) |
| David no respondió literal `ok, arranca` | STOP — no spawn |
| `pit_spec_validate.py` ≠ pass | STOP — corregir spec |
| Smoke PIT-2 en rojo (`PIT_PREFLIGHT_FAIL` o `PIT_DRY_RUN_FAIL`) | STOP — no spawn hasta veredicto PASS |
| pit-vault sin desplegar o `pit_vault_check.py` fail | STOP — deploy/fix vault primero |
| Pedido de URL pública para el prototipo | STOP — solo túnel + Mission Control en v1 |
| Lane pide escribir fuera de su subárbol | STOP — write scope `pit/<pit_id>/lanes/<lane_id>/` |
| Lane pide llamar Magnific directo o sin gate de columna | STOP — Rick broker + gate Prototype |
| Señal sintética sin etiquetar | STOP — labeled es obligatorio |
| Sesión nested sin `sessions_spawn` | STOP — ISSUE-001 / G-D1b (igual que D3) |

---

## Post-torneo

1. Outcome report → `pit/<pit_id>/outcome/pit_outcome_report.yaml`.
2. Handoff mejora continua (improvement-supervisor) — propuestas documentadas, **no** auto-merge de prompts: [`pit-handoff-mejora-continua.md`](../../../../docs/ops/pit-handoff-mejora-continua.md).
3. Archivar: mover `pit/<pit_id>/` → `archive/<pit_id>/` (lo hace Rick).
4. Índice de procesos + checklist PIT-7: [`pit-process-index.md`](../../../../docs/ops/pit-process-index.md).

## Referencias

- Visión y decisiones: `docs/ops/product-innovation-tournament-vision-2026-06-09.md`
- Schema spec: `docs/schemas/pit-spec-v1.schema.json` + `scripts/pit/pit_spec_validate.py`
- Kanban/KPI: `docs/ops/pit-kanban-kpi-protocol.md`
- Vault: `docs/ops/pit-vault-layout.md` + `scripts/pit/pit_vault_check.py`
- Visual: `docs/ops/pit-visual-magnific.md` (Magnific 4:3 canónico)
- Agentes efímeros: `docs/ops/pit-ephemeral-agent-generator.md`
- D3 (contraste): `docs/79-tournament-protocol-openclaw-native.md`
