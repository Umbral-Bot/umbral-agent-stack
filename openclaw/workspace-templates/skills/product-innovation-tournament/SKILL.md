---
name: product-innovation-tournament
description: >-
  PIT — Product Innovation Tournament: parser NL + alias /torneo_producto que
  convierte un pedido de David en pit_spec.yaml validado, confirma con gate
  literal "ok, arranca" y orquesta N lanes efímeras que compiten con
  prototipos + KPI (PROTOTYPE_URL + KPI_PACK + fulfillment). Incluye el modo
  PIT-DEV (spec v3): torneos de producto técnico usable con jueces ejecutores,
  security-egress y trazabilidad. NO es el torneo de código D3 (PR_URL) — ese
  es multi-agent-tournament-orchestrator.
metadata:
  openclaw:
    emoji: "🧪"
    requires:
      env: []
---

# Product Innovation Tournament (PIT)

Skill de Rick para torneos de **producto**: lanes paralelas que investigan, formulan hipótesis, prototipan y miden KPI. Implementa [`docs/ops/product-innovation-tournament-vision-2026-06-09.md`](../../../../docs/ops/product-innovation-tournament-vision-2026-06-09.md); contrato de entrada en [`docs/schemas/pit-spec-v1.schema.json`](../../../../docs/schemas/pit-spec-v1.schema.json).

**Status:** v1.3 (PIT-2b + PIT-DEV) — parser + gate + contratos + runner smoke local (tasks `pit.*` + dry-run) **+ spawn real de agentes efímeros** vía `scripts/pit/pit_tournament_run.sh` ([`docs/ops/pit-2-runner-protocol.md`](../../../../docs/ops/pit-2-runner-protocol.md) §7) **+ modo PIT-DEV** (spec v3, §PIT-DEV abajo). El spawn real requiere pit-vault desplegado + smoke `PIT_DRY_RUN_PASS` + autorización David por torneo (gate literal).

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
| `visual_generation` | "con visuales/mockups Magnific" → enabled + `aspect_ratio: "4:3"` (default canónico). **Semántica PIT-DEV FASE 6:** habilita SOLO la generación de Rick post-judge para el deck — jamás una herramienta de lane | enabled=false |
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
  visual:           Magnific 4:3 (SOLO Rick post-judge para el deck; lanes jamás)
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

`Research → Hypothesis → Prototype → KPI Track → Fulfillment → Review` sobre el tablero de 9 columnas ([protocolo](../../../../docs/ops/pit-kanban-kpi-protocol.md)). Research según `research_profile` (tiers: academic | market_pain | competitive | mixed). **Magnific: PROHIBIDO para toda lane/juez/subagente en TODOS los modos** — ni invocarlo ni pedirlo; cualquier visual es decisión de Rick post-judge para el deck ([pit-visual-magnific](../../../../docs/ops/pit-visual-magnific.md)).

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

## Broker-only enforcement (PIT-P5)

Las lanes que **leen/analizan el repo o escriben código** NO hablan con un proveedor LLM directo: **todo pasa por el Worker task `copilot_cli.run`** (contrato P4, [`docs/ops/pit-p4-broker-contract-20260621.md`](../../../../docs/ops/pit-p4-broker-contract-20260621.md)). El broker es el único que resuelve modelo→slug, aplica `reasoning_effort`, audita y corre el sandbox Docker `--network=none`. (Para visual de producto el broker sigue siendo Magnific, arriba.)

**Regla dura:** una lane que intente invocar un LLM directo para coding/análisis de repo ⇒ `lane_blocked`. Sin fallback silencioso a proveedor directo.

### Preflight obligatorio (antes de spawnear lanes broker)

Todo en verde o STOP:

- [ ] `P2_PROBE_REAL_OK` (probe real, run3)
- [ ] `P3_SLUGS_OK` — slugs + aliases en [`config/tool_policy.yaml`](../../../../config/tool_policy.yaml), `force_default_model: false`
- [ ] PRs `#481`, `#482`, `#483` mergeados en `main`
- [ ] `P4_RUNTIME_LOAD_OK` — worker reiniciado con el contrato P4 en runtime
- [ ] `pit_spec_validate` PASS sobre el spec del torneo:
      `python scripts/pit/pit_spec_validate.py <spec.yaml>` → `status: pass`

### Payload canónico de lane (broker)

Cada lane se despacha como `copilot_cli.run` con metadata PIT completa (correlación audit↔respuesta):

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "model": "Claude Opus 4.7",
    "reasoning_effort": "xhigh",
    "repo_path": "/work",
    "dry_run": true,
    "metadata": {
      "batch_id": "<batch>",
      "agent_id": "<agente efímero>",
      "pit_id": "<pit_id>",
      "lane_id": "<lane_id>",
      "iteration": 1
    }
  }
}
```

`batch_id`, `agent_id`, `pit_id`, `lane_id`, `iteration` son **obligatorios**. Grammar de ids y `reasoning_effort` permitidos (incl. alias `max`→`xhigh`) en P4. Spec ejecutable + validador: [`examples/pit/pit_spec.v2.yaml`](../../../../examples/pit/pit_spec.v2.yaml) (`broker_contract.forbid_direct_llm_repo_analysis: true`).

### Fallback policy

- `copilot_cli.run` falla (timeout, error de policy, gate cerrado) ⇒ lane `blocked` con motivo registrado. **Nunca** reintento con proveedor directo ni degradación silenciosa.
- Los gates de runtime (L3 execute, L4 egress, nft) son del operador VPS; **la skill nunca los abre**.

### Comms

Resumen a David ≤ 12 líneas (veredicto + estado de lanes + blockers). Payloads, audit JSONL y respuestas completas van a evidencia/vault, no al chat.

Doc operativa: [`docs/ops/pit-p5-broker-enforce-20260622.md`](../../../../docs/ops/pit-p5-broker-enforce-20260622.md).

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
| **Lane/juez/subagente pide o invoca Magnific (CUALQUIER modo)** | STOP — `lane_blocked`; Magnific es SOLO Rick, post-judge, fuera de las lanes (FASE 6). El registro de efímeros lo deniega vía `tools.deny` |
| Lane intenta LLM directo para coding/repo-analysis | STOP — `lane_blocked`; todo por `copilot_cli.run` (P5) |
| Preflight P5 incompleto (P2/P3 · #481-483 · P4 · validate) | STOP — no spawn de lanes broker |
| `copilot_cli.run` falla en una lane | lane `blocked`, sin fallback a proveedor directo |
| Señal sintética sin etiquetar | STOP — labeled es obligatorio |
| Pedido de adjuntar el `.pptx` por Telegram | STOP — v1 entrega SOLO link Drive (PIT-TG-DRIVE); sin Drive → fallback texto + MC hint |
| Sesión nested sin `sessions_spawn` | STOP — ISSUE-001 / G-D1b (igual que D3) |

---

## PIT-DEV — torneo "developer product" (spec v3, `mode: dev`)

Modo nuevo (visión David 2026-07-03, [`pit-dev-mode-vision-2026-07-03.md`](../../../../docs/ops/pit-dev-mode-vision-2026-07-03.md)): el deliverable es un **producto técnico usable** (ej.: API/MCP server para manejar umbral-agent-stack desde IDEs), no un mock HTML. v1 producto y v2 broker quedan intactos.

| | **D3 code** | **PIT product (v1)** | **PIT-DEV (v3)** |
|---|---|---|---|
| Cierre de lane | `PR_URL=` | `PROTOTYPE_URL=` + `KPI_PACK=` + `FULFILLMENT=` | `DELIVERABLE_PATH=` + `TEST_REPORT=` + `SELF_ASSESSMENT=` |
| Juez | rubric sobre diffs | fulfillment + scorecard producto | **jueces ejecutores**: instalan, corren y evalúan (rúbrica ejecutable + `JUDGE_SCORE`) |

### Qué cambia respecto a v1

- **Workspace curado por lane**: snapshot del repo (ref pinneado del spec, `git archive`) + `CONTEXT_INDEX.md` — las lanes NUNCA trabajan sobre `main` vivo. El producto va en `deliverable/`, fuera del snapshot ([`pit_lane_workspace_init.sh`](../../../../scripts/pit/pit_lane_workspace_init.sh)).
- **Tests reales**: cada iteración con tests deja `test_report.json` (schema en vault `templates/`); `lane_complete` = deliverable presente + report válido (`exit_code: 0`) + tests **re-ejecutables** por el collect.
- **Security-egress**: lanes y jueces DECLARAN su egress (`egress.jsonl`); el agente `<pit_id>-security` consolida, contrasta y emite `EGRESS_CLEAN | EGRESS_FLAGGED` por lane ([`pit-security-egress-monitor.md`](../../../../docs/ops/pit-security-egress-monitor.md)).
- **Jueces ejecutores** (`judge_count`, default 2), spawneados POST-cierre de lanes: scorecards contra `judge-scorecard.schema.json` + ranking agregado — **el ranking NO decide** ([`pit-dev-judge-protocol.md`](../../../../docs/ops/pit-dev-judge-protocol.md)).
- **Trazabilidad post-torneo**: agente + script verifican la cadena spec→…→deck ([`pit-traceability-agent.md`](../../../../docs/ops/pit-traceability-agent.md), [`pit_traceability_check.py`](../../../../scripts/pit/pit_traceability_check.py)).

### Runner

El runner v1 detecta el spec dev y delega (mismo patrón que el broker v2):

```bash
bash scripts/pit/pit_tournament_run.sh pit/<pit_id>/spec/pit_spec.yaml \
  <lanes.yaml> --gate "ok, arranca"            # fases: lanes → security → judges
bash scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> \
  --gate "ok, arranca" --plan-only              # validación post-merge sin spawn
python scripts/pit/pit_dev_run.py <spec.yaml> --phase traceability \
  --gate "ok, arranca"                          # post-outcome/deck
```

Kill + desregistro SIEMPRE al cierre (todos los efímeros del torneo: lanes, security, judges, traceability — prefijo `<pit_id>-`).

### Gates David explícitos (PIT-DEV)

1. **Spawn:** literal `ok, arranca` — sin la frase exacta el runner aborta `PIT_RUN_BLOCKED`.
2. **Pre-judge:** si security flaggeó una lane (`EGRESS_FLAGGED`), el judge NO corre sobre ella; incluirla exige decisión explícita (`--judge-flagged-lanes "<motivo>"`, registrada en métricas; + gate David si es grave). Sin `verdict.md` no hay judge (fail-closed).
3. **Winner:** el ranking del judge NO decide — Rick consolida y David da el gate (regla existente).
4. **Acción externa:** cualquier salida (Drive/Telegram, flujo PIT-TG-DRIVE) pide autorización, como siempre.

### Hard stops PIT-DEV (además de los generales)

| Condición | Acción |
|---|---|
| Falta `deliverable_spec`, `repo_ref`, `budget_usd`, `iteration_count`, `security_monitor: required` o `traceability: required` en el spec | STOP — `pit_spec_validate` ≠ pass |
| Lane parchea el snapshot para "mejorar main" | STOP — el torneo produce un artefacto nuevo, no un PR |
| `workspace/` fuera de `pit/<pit_id>/lanes/<lane_id>/` | STOP — `pit_vault_check` falla |
| Egress real no declarado (divergencia ledger vs logs) | lane `EGRESS_FLAGGED` — judge bloqueado sin decisión explícita |
| Juez evalúa una lane flaggeada sin decisión registrada | STOP |
| Lane/juez pide Magnific | STOP — `lane_blocked` (regla global FASE 6) |

### Rendición a David (cierre — plantilla ≤15 líneas)

```text
TORNEO PIT-DEV · <pit_id>
Estado: cerrado · Winner: <lane_id> (gate David: <frase/pending>)
Scores (rúbrica ejecutable): <lane> <score> · <lane> <score> · <lane> <score>
Seguridad: <EGRESS_CLEAN × N | EGRESS_FLAGGED: lane-x (<motivo>)>
Trazabilidad: <TRACE_COMPLETE | TRACE_GAPS(<lista>)>
Eficiencia: <spent>/<budget> USD (est.) · tokens: <total o not_reported> · duración: <hh:mm>
vs torneo anterior: <mejor/peor en costo/tiempo, 1 línea>
Deliverable winner: pit/<pit_id>/lanes/<lane>/deliverable/ (instala: <sí/no> · tests: <N pass>)
Mejoras registradas: <n> propuestas → handoff mejora continua §5
Deck: <link Drive | pending gate>
Próximo paso propuesto: <1 línea — requiere tu autorización>
```

---

## Post-torneo

1. Outcome report → `pit/<pit_id>/outcome/pit_outcome_report.yaml`.
2. **Entrega Telegram** (deck ejecutivo en Drive) → sección siguiente.
3. Handoff mejora continua (improvement-supervisor) — propuestas documentadas, **no** auto-merge de prompts: [`pit-handoff-mejora-continua.md`](../../../../docs/ops/pit-handoff-mejora-continua.md).
4. Archivar: mover `pit/<pit_id>/` → `archive/<pit_id>/` (lo hace Rick).
5. Índice de procesos + checklist PIT-7: [`pit-process-index.md`](../../../../docs/ops/pit-process-index.md).

---

## Entrega Telegram post-torneo (PIT-TG-DRIVE)

Tras judge + outcome report + gate David (winner cerrado, `david_gate` ≠ pending):

1. Rick (o el operador) corre el deliver pack contra el vault:

   ```bash
   python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id>   # --dry-run para validar sin Drive
   ```

   El script construye el deck (`pit/<pit_id>/deliverables/<pit_id>-outcome-deck.pptx`,
   builder [`pit_build_outcome_deck.py`](../../../../scripts/pit/pit_build_outcome_deck.py)),
   lo sube a la carpeta Drive compartida Rick↔David (Worker task
   `google_drive.upload_file`) y escribe
   `pit/<pit_id>/deliverables/telegram_pack.json` con `summary_lines[]` listos.
   Veredicto: `PIT_DELIVER_PACK_OK | drive_url=…` (setup en
   [`pit-telegram-drive-deliverables-runbook.md`](../../../../docs/ops/pit-telegram-drive-deliverables-runbook.md)).

2. Rick envía por Telegram la plantilla fija (≤12 líneas + link Drive — formato
   ejecutivo de [`queue-002 §9`](../../../../docs/ops/pit-tournament-queue-002-sharepoint-acc-umbral-bim.md)):

   ```text
   TORNEO PIT · <pit_id>
   Estado: cerrado · Winner: <lane_id> · Fulfillment: <score>
   Resumen:
   • <1 línea problema>
   • <N lanes> · budget <spent>/<budget> USD (estimado)
   • KPI clave: <kpi_id> <achieved> vs <expected> <unit>
   • Aprendizaje: <1 validated o refuted>
   Deck ejecutivo (Google Drive):
   <web_view_link>
   Preview prototipos (PC + túnel): scripts/ops/pit-judge-open.ps1 → /pit/judge/<pit_id>
   Detalle vault: pit/<pit_id>/outcome/pit_outcome_report.yaml
   ```

3. Rick registra la entrega en el outcome (`deliverables:` — `drive_deck_url`,
   `drive_file_id`, `telegram_sent_at`).

Reglas duras:

- **NUNCA** `sendDocument`/`sendPhoto` del `.pptx` por Telegram en v1 — solo el link Drive.
- Si Drive no está configurado (`PIT_DELIVER_PACK_FAIL | reason=drive_not_configured`):
  fallback texto + MC judge hint (comportamiento actual). Rick **no inventa** links.
- Si el upload falla: reportar `PIT_DELIVER_PACK_FAIL` + motivo; sin link no hay mensaje "con deck".
- El deck va SOLO a `GOOGLE_DRIVE_PIT_FOLDER_ID` (carpeta compartida); el prototipo HTML
  sigue en túnel + Mission Control — nunca URL pública.

---

## Referencias

- Visión y decisiones: `docs/ops/product-innovation-tournament-vision-2026-06-09.md`
- PIT-DEV (modo dev, spec v3): `docs/ops/pit-dev-mode-vision-2026-07-03.md`
- Schema spec: `docs/schemas/pit-spec-v1.schema.json` + `scripts/pit/pit_spec_validate.py`
- Kanban/KPI: `docs/ops/pit-kanban-kpi-protocol.md`
- Vault: `docs/ops/pit-vault-layout.md` + `scripts/pit/pit_vault_check.py`
- Visual: `docs/ops/pit-visual-magnific.md` (Magnific 4:3 canónico)
- Agentes efímeros: `docs/ops/pit-ephemeral-agent-generator.md`
- D3 (contraste): `docs/79-tournament-protocol-openclaw-native.md`
