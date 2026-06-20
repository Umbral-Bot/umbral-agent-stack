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

Skill de Rick para torneos de **producto**: lanes paralelas que investigan, formulan hipótesis, prototipan y miden KPI. El contrato canónico vigente para Ruta B broker-real es [`docs/ops/pit-tournament-v2-contract.md`](../../../../docs/ops/pit-tournament-v2-contract.md). La visión histórica sigue en [`docs/ops/product-innovation-tournament-vision-2026-06-09.md`](../../../../docs/ops/product-innovation-tournament-vision-2026-06-09.md); contrato de entrada v1 en [`docs/schemas/pit-spec-v1.schema.json`](../../../../docs/schemas/pit-spec-v1.schema.json).

**Status:** v2.0 P0 alignment — parser + gate + contratos + runner smoke local (tasks `pit.*` + dry-run) **+ spawn real de agentes efímeros** vía `scripts/pit/pit_tournament_run.sh` ([`docs/ops/pit-2-runner-protocol.md`](../../../../docs/ops/pit-2-runner-protocol.md) §7). El spawn real requiere pit-vault desplegado + smoke `PIT_DRY_RUN_PASS` + autorización David por torneo (gate literal) + preflight Ruta B cuando `coding_broker: copilot_cli`.

## Contrato canónico v2 — Ruta B broker-only

Cuando el spec declare `coding_broker: copilot_cli`, la regla es literal:

- OpenClaw lane = orquestador; Worker `copilot_cli.run` = única superficie de coding/repo.
- Las lanes **NO** implementan vía `azure-openai-responses`, coding directo, shell propia, GitHub directo ni herramientas OpenClaw alternativas.
- Cada batch broker debe incluir `pit_id`, `lane_id`, `batch_id` e `iteration`.
- Los modelos de lane quedan en `lane_models[]`; no inventar slugs no verificados. Usar placeholders `TODO_P3_VPS_VERIFY_*` hasta P3.
- Si `copilot_cli.run` falla, la lane queda `blocked`; no hay mock silent fallback ni implementación alternativa para simular éxito.
- `PIT_RUN_PASS_BROKER_REAL` solo existe si el ledger de tokens + audit JSONL + Mission Control judge + gate David están completos.

Fuente de verdad: [`docs/ops/pit-tournament-v2-contract.md`](../../../../docs/ops/pit-tournament-v2-contract.md). Contrato técnico corto: [`docs/ops/pit-broker-contract.md`](../../../../docs/ops/pit-broker-contract.md).

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

- En Telegram, esta confirmación debe tener **12 líneas o menos**; el detalle completo queda en el pit-vault.
- **Solo** la frase literal **`ok, arranca`** dispara el spawn. "dale", "sí", "go" → repetir el gate.
- Cualquier corrección de David → re-parsear, re-validar, re-presentar el gate.
- Sin respuesta = sin torneo. No hay auto-arranque.

---

## Preflight Ruta B antes de spawn broker-real

Antes de spawnear lanes para un torneo con `coding_broker: copilot_cli`, Rick debe comprobar:

1. **P1 infra:** imagen sandbox Copilot CLI y red `copilot-egress` listas si el spec pide execute/egress.
2. **P2 probe:** Worker `copilot_cli.run` probado al menos en read-only con audit JSONL.
3. **Repo clone/read:** `repo_read` existe, ref fijado y paths allowlist/denylist cargados.
4. **Allowlist:** comandos, egress y MCP coinciden con `permissions`.
5. **`pit_spec_validate`:** spec validado y sin defaults silenciosos en `budget_usd` ni `iterations`.
6. **`secrets_scope`:** solo referencias declarativas; ningún valor secreto en prompt, vault o logs.
7. **Token ledger:** `metrics/token_ledger.yaml` preparado o el torneo queda como no broker-real.

Si una condición requerida falla, el veredicto es `PIT_RUN_BLOCKED` o `NEEDS_RERUN`, no fallback.

---

## Smoke runner PIT-2 (post-gate, pre-spawn — obligatorio)

Recibido el literal `ok, arranca`, Rick **NO spawnea todavía**: primero corre el smoke local del runner ([`docs/ops/pit-2-runner-protocol.md`](../../../../docs/ops/pit-2-runner-protocol.md)):

1. **`pit.preflight`** (Worker task) — valida `pit_spec.yaml`, budget (`budget_usd` = max cost estimate; kill switch @100 % documentado, enforcement real PIT-3), vault path y `pit_vault_check`. Veredicto requerido: `PIT_PREFLIGHT_PASS`.
2. **`bash scripts/pit/pit_tournament_dry_run.sh <spec.yaml>`** — simula las N lanes en secuencia (init → 1 iteración fake → fulfillment → announce) sobre un vault scratch. Sin internet, sin Magnific, sin `sessions_spawn`. Evidencia: `~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json` con veredicto `PIT_DRY_RUN_PASS`.

Smoke rojo ⇒ STOP: se corrige spec/vault/runner y se repite. No hay spawn con smoke rojo.

## Spawn — agentes efímeros (PIT-2b, ejecutable)

Procedimiento del generador en [`docs/ops/pit-ephemeral-agent-generator.md`](../../../../docs/ops/pit-ephemeral-agent-generator.md); el runner que lo ejecuta es `scripts/pit/pit_tournament_run.sh` ([protocolo §7](../../../../docs/ops/pit-2-runner-protocol.md)).

Con el smoke en `PIT_DRY_RUN_PASS`, Rick:

1. **Deriva las identidades de lane** y las escribe en un `lanes.yaml`
   (`lanes: [{lane_id, lane_focus}, ...]`, count == `lane_count`): el slug
   nombra el **ángulo de exploración**, no una tecnología (ej.
   [`examples/pit-salud-mental-pilot.lanes.yaml`](../../../../examples/pit-salud-mental-pilot.lanes.yaml)).
2. **Lanza el runner** pasando la frase literal del gate David (sin la frase
   exacta el runner aborta `PIT_RUN_BLOCKED`):

   ```bash
   bash scripts/pit/pit_tournament_run.sh pit/<pit_id>/spec/pit_spec.yaml \
     <lanes.yaml> --gate "ok, arranca"
   ```

El runner automatiza el ciclo completo del generador (§2):

- **Gates pre-spawn:** frase literal + smoke `PIT_DRY_RUN_PASS` fresco (≤24 h,
  mismo `pit_id`/`lane_count`) + `pit.preflight` PASS contra el vault real.
  Cualquier fallo ⇒ `PIT_RUN_BLOCKED` (exit 2), sin tocar el runtime.
- **Generate:** render de `ROLE.template.md` por lane + `agents.yaml` en
  `pit/<pit_id>/spec/` (histórico de qué efímeros existieron).
- **Register:** alta de los efímeros (`<pit_id>-<lane_id>`) en `agents.list` de
  `openclaw.json` (backup previo + escritura atómica) + allowAgents de `main`
  + restart gateway. No se reciclan ids de torneos anteriores (abort si existen).
- **Spawn:** `openclaw agent --agent main` standalone (G-D1b) con el fan-out
  `sessions_spawn` × N en un solo turno + yield; si `main` reporta
  `PIT_SPAWN_BLOCKED_ISSUE_001` (sesión nested) no hay collect.
- **Collect:** patrón D3.5b (lane result files) — verifica cada lane contra el
  vault con la misma implementación de `pit.lane_announce`: `lane_complete`
  obligatorio = `announce.md` presente **+** kpi_pack reproducible.
- **Kill + desregistro:** SIEMPRE al cierre (aunque el collect falle): kill de
  hijos vivos del torneo (por label, nunca ajenos), baja de `agents.list` +
  allowAgents, `agents.yaml` actualizado como histórico (`killed_at`,
  `deregistered`).

Veredictos en `~/.coord-ag-evidence/pit-run/<pit_id>/run-metrics.json`:
`PIT_RUN_PASS` (todas las lanes completas) · `PIT_RUN_PARTIAL` (≥2 completas —
judge posible) · `PIT_RUN_FAIL` (<2) · `PIT_RUN_BLOCKED` (abort pre-spawn) ·
`PIT_RUN_PLAN_ONLY` (`--plan-only`: valida y renderiza plan sin registro ni
spawn — usar para validación post-merge en VPS sin gastar budget).

Límites heredados de OpenClaw (sin cambios): 2–5 lanes
(`maxChildrenPerAgent: 5`), spawn desde `main` standalone (G-D1b, ISSUE-001),
`maxSpawnDepth >= 2` — mismas hard rules que D3.

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
- **Lane result file (PIT-2b, patrón D3.5b):** la lane persiste esas mismas 3 líneas en `pit/<pit_id>/lanes/<lane_id>/announce.md`; el collect del runner exige `announce.md` presente + kpi_pack reproducible — el transcript del subagente no es fuente de verdad.
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
| Smoke PASS viejo (>24 h) o de otro spec (`pit_id`/`lane_count` distintos) | STOP — re-correr el smoke para ESTE spec (`PIT_RUN_BLOCKED`) |
| Runner invocado sin `--gate "ok, arranca"` literal | STOP — `PIT_RUN_BLOCKED`, el runner no spawnea |
| `agent_id` efímero ya registrado (reciclado de otro torneo) | STOP — `PIT_RUN_BLOCKED`, generar identidades nuevas |
| pit-vault sin desplegar o `pit_vault_check.py` fail | STOP — deploy/fix vault primero |
| Pedido de URL pública para el prototipo | STOP — solo túnel + Mission Control en v1 |
| Lane pide escribir fuera de su subárbol | STOP — write scope `pit/<pit_id>/lanes/<lane_id>/` |
| `coding_broker: copilot_cli` pero la lane intenta implementar vía `azure-openai-responses`, OpenClaw directo o GitHub directo | STOP — `PIT_LANE_SPEC_VIOLATION` |
| Worker `copilot_cli.run` falla o no está disponible | STOP — lane `blocked`; sin mock silent fallback |
| Falta P1/P2 para un torneo que requiere broker-real | STOP — `PIT_RUN_BLOCKED`; no re-run hasta cerrar paquetes |
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
- Contrato canónico Ruta B v2: `docs/ops/pit-tournament-v2-contract.md`
- Contrato técnico broker: `docs/ops/pit-broker-contract.md`
- Resumen mega-diagnóstico 2026-06-20: `docs/ops/pit-mega-diagnostic-20260620-summary.md`
- Schema spec: `docs/schemas/pit-spec-v1.schema.json` + `scripts/pit/pit_spec_validate.py`
- Kanban/KPI: `docs/ops/pit-kanban-kpi-protocol.md`
- Vault: `docs/ops/pit-vault-layout.md` + `scripts/pit/pit_vault_check.py`
- Visual: `docs/ops/pit-visual-magnific.md` (Magnific 4:3 canónico)
- Agentes efímeros: `docs/ops/pit-ephemeral-agent-generator.md`
- D3 (contraste): `docs/79-tournament-protocol-openclaw-native.md`
