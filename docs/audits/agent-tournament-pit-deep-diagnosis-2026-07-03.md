# Diagnóstico profundo — Torneo de agentes para innovación de producto (PIT) · visión David 2026-07-03

- **Versión:** AGENT-TOURNAMENT-DEEP-DIAG-v1 · 2026-07-03
- **Superficie:** Copilot Windows · repo `umbral-agent-stack` @ `735a6c7` (main)
- **Modo:** diagnóstico READ-ONLY — sin spawn, sin torneo real, sin writes Notion, sin gasto LLM de torneo.
- **Task:** [`.agents/tasks/2026-07-03-009-agent-tournament-deep-diagnosis.md`](../../.agents/tasks/2026-07-03-009-agent-tournament-deep-diagnosis.md)
- **Regla aplicada:** *VPS Reality Check* — todo lo runtime se reporta como **"repo dice X"**; el estado VPS actual NO fue verificado por SSH en esta sesión (fuera de scope del megaprompt). Donde la divergencia importa, se marca `⚠ VERIFICAR EN VPS`.

---

## 1. Resumen ejecutivo

**Veredicto: `pit6_ready=PARTIAL` — el sistema está mucho más avanzado de lo que la visión asume, pero el pedido exacto de David (roster fable-5/sonnet-5/kimi + 1M + enforcement de $200 + "producto terminado") tiene 3 gaps HIGH.**

1. **PIT-6 "primer torneo real" ya ocurrió en esencia.** El repo evidencia **dos torneos v1 product reales en el vault VPS**: `pit-salud-mental-pilot` (ledger 5.554.534 tokens) y `pit-umbral-bim2-sharepoint-acc` (ledger 6.617.544 tokens) — [`pit-readiness-golden-20260622.md`](../ops/pit-readiness-golden-20260622.md) §P6 + notes. David ya revisó el piloto #1 y sus lecciones están capitalizadas en [`pit-tournament-queue-002`](../ops/pit-tournament-queue-002-sharepoint-acc-umbral-bim.md) §3. ⚠ VERIFICAR EN VPS estado actual del vault/outcome.
2. **La arquitectura broker (P1–P6, P9, P10) está probada end-to-end:** P9 corrió un torneo golden **real** (3 lanes vía `copilot_cli.run`, exit 0, rollback byte-idéntico) → `PIT_RUN_PASS_BROKER_REAL` alcanzado (2026-06-22).
3. **Per-lane model existe SOLO en pit_spec v2 (broker code/research)**, no en v1 product. El runner v1 (`pit_tournament_run.py --lane-model`) aplica **un** modelo global a todos los efímeros. Gap HIGH → propuesta lanes.yaml v1.1 en §6.3.
4. **Roster David NO disponible hoy según última evidencia:** el slug audit P3 (2026-06-21, token UmbralBIM) confirma `gpt-5.5` ✅ pero **fable-5 → "no such model"**, sonnet-5 no existía, y **kimi no es modelo Copilot CLI** (es deployment Azure `Kimi-K2.5` vía `worker llm` provider `kimi_azure`). Señal fresca 2026-07-03: la superficie Copilot en Windows ya expone `claude-fable-5` y `claude-sonnet-5` → **re-probe P3 en VPS es el paso 1 del roadmap**. "Contexto 1M": Copilot CLI 1.0.36 no expone flag de context tier — sin evidencia de que sea seleccionable por lane.
5. **Budget $200: estimación sí, enforcement no.** `pit.preflight` calcula `max_cost_estimate_usd` y documenta kill switch @100 %, pero el corte duro es **stub** ([`pit_runner_core.py:72-74`](../../scripts/pit/pit_runner_core.py)). El ledger P6 (`pit_collect_tokens.py`) contabiliza **post-hoc**. Gap HIGH.
6. **Telegram → spawn: bloqueado por ISSUE-001, workaround documentado y operativo.** Sesiones nested no tienen `sessions_spawn` ([`openclaw-known-issues.md`](../external-context/openclaw-known-issues.md) §ISSUE-001). El path legal hoy: Rick parsea en Telegram → gate `ok, arranca` → operador/Copilot-VPS corre `pit_tournament_run.sh` (que hace el fan-out desde `main` standalone). Es la **Opción A** recomendada (§7).
7. **Preview web David: implementado.** MC P5.1–P5.3 completos en código (API bearer + judge UX v2 + preview firmado HMAC 15 min); túnel `pit-judge-open.ps1` local `18089` → VPS `8089`. Queue-002 G1 marca judge UX **deployado** (`802f431`). ⚠ VERIFICAR EN VPS.
8. **"Producto terminado versión usuario final":** las lanes v1 escriben HTML directo al vault (probado en piloto), pero la lección #1 fue "prototipos muy básicos". Para prototipos code-heavy el broker `copilot_cli.run` es **read-only** (`max_files_touched: 0`, write/PR = gate F9 pendiente). Gap MEDIUM-HIGH según ambición de la idea.

**Recomendación (1 frase):** correr el siguiente torneo con el pipeline ya probado (Opción A + spec v1 + lanes.yaml), gastando el esfuerzo nuevo SOLO en: re-probe de slugs (fable-5/sonnet-5), extensión lanes.yaml per-lane model, y enforcement de budget mínimo viable.

---

## 2. Visión David (fuente de verdad del diagnóstico)

Pedido natural por Telegram:

> "Crea un torneo para desarrollar [IDEA/PROBLEMA], presupuesto máximo 200 USD. Usa gpt-5.5 en max y 1M, fable-5 en max 1M, sonnet-5 en max y 1M, y kimi al final."

Expectativas: (1) Rick coordina N lanes con estrategias distintas; (2) entrega = prototipo terminado versión usuario final; (3) visible en formato web (túnel/MC, no URL pública); (4) trazabilidad del *por qué*; (5) costo vs budget con enforcement deseable; (6) aprendizaje por torneo; (7) skills/tools reutilizables validadas; (8) gate humano "ok, arranca".

**Precedente clave:** el prompt NL verbatim de David del torneo #2 (2026-06-12, [`queue-002 §1`](../ops/pit-tournament-queue-002-sharepoint-acc-umbral-bim.md)) ya ejercitó este flujo: "inicia un torneo de 3 agentes con gasto en tokens de 150 usd…". El parser de la skill PIT ([`SKILL.md`](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md) §Parser) cubre lanes/budget/iteraciones/KPIs — **no cubre modelos por lane** (gap E-2).

---

## 3. Desambiguación: los TRES (+1) mecanismos de torneo

| Mecanismo | Tipo | Qué hace | Salida | Implementación | Tests |
|---|---|---|---|---|---|
| `tournament.run` | Worker task | Torneo **ideacional** LLM: divergencia → debate → juez | Texto comparativo + verdict | [`worker/tasks/tournament.py`](../../worker/tasks/tournament.py) | `test_tournament_handler.py` |
| `github.orchestrate_tournament` | Worker task | Torneo **código** sobre ramas git (`rick/t/<id>/a..`), validación, cherry-pick winner | branches + verdict (+`final_branch`) | [`worker/tasks/github_tournament.py`](../../worker/tasks/github_tournament.py) | `test_github_tournament.py` |
| **D3 OpenClaw-native** | Skill (no worker task) | `multi-agent-tournament-orchestrator`: `sessions_spawn` × N lanes especialistas → PRs | `PR_URL` winner + final-metrics | [skill](../../openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/SKILL.md) + docs/79 | smokes D3.0–D3.5 (evidencia, no pytest) |
| **PIT product** | Skill + runner + tasks `pit.*` | Torneo **producto**: N efímeros × iteraciones, prototipo+KPI en vault | `PROTOTYPE_URL` + `KPI_PACK` + `FULFILLMENT` | skill PIT + [`pit_tournament_run.py`](../../scripts/pit/pit_tournament_run.py) + [`pit_runner.py`](../../worker/tasks/pit_runner.py) | 165 passed / 3 skipped (esta sesión, Windows) |

Para la visión David el default es **PIT product** (prototipo HTML + KPI); **D3 code** solo si pide explícitamente código/PR en un repo. La skill ya obliga a preguntar ante ambigüedad (SKILL §When NOT to use).

**PIT tiene además dos sub-modos por spec:** `schema_version: 1` (product — el de la visión) y `schema_version: 2` (broker code/repo-analysis — lanes despachan `copilot_cli.run`, read-only). El runner rutea specs v2 al broker (`pit_broker_run.py`).

---

## 4. FASE A — Inventario ejecutable (capacidad David vs repo)

| Capacidad David | ¿Implementado hoy? | Archivo/prueba | Gap |
|---|---|---|---|
| Invocación Telegram NL | ✅ parser + alias `/torneo_producto` en skill Rick | [SKILL §Invocación/Parser](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md); precedente verbatim queue-002 §1 | parser no extrae **modelos por lane** |
| Parser → pit_spec.yaml validado | ✅ | [`pit_spec_validate.py`](../../scripts/pit/pit_spec_validate.py) (pydantic, v1+v2) + [schema v1](../schemas/pit-spec-v1.schema.json) | — |
| N lanes × estrategia distinta | ✅ `lanes.yaml` (`lane_id` + `lane_focus` = ángulo) | [`examples/pit-salud-mental-pilot.lanes.yaml`](../../examples/pit-salud-mental-pilot.lanes.yaml) | — |
| N lanes × **modelo distinto** | ⚠️ SOLO v2 broker (`lanes[].model` + `reasoning_effort`) | [`examples/pit/pit_spec.openclaw-broker-v4.yaml`](../../examples/pit/pit_spec.openclaw-broker-v4.yaml) | v1 product: `--lane-model` es **global** ([`pit_tournament_run.py:994`](../../scripts/pit/pit_tournament_run.py)) → propuesta §6.3 |
| Prototipo HTML final | ✅ v1 product (vault `prototype/`); piloto #1 lo produjo | [`pit_vault.py`](../../mission_control/adapters/pit_vault.py) `_scan_lane` detecta `index.html` | calidad "producto terminado": lección #1 = básicos; código real bloqueado por broker read-only (F9) |
| Preview web para David | ✅ código completo P5.1–P5.3: API bearer, judge UX v2, preview firmado (HMAC TTL 15 min, cookie HttpOnly) | [`routes/pit.py`](../../mission_control/routes/pit.py), [`pit_preview.py`](../../mission_control/routes/pit_preview.py), [`pit-judge-open.ps1`](../../scripts/ops/pit-judge-open.ps1) (túnel 18089→8089) | ⚠ VERIFICAR deploy VPS (P5.4); queue-002 G1 dice ✅ `802f431` |
| Trazabilidad "por qué" | ✅ kanban 9 cols + hipótesis/iteración + `kpi_pack.json` + `announce.md` + `run-metrics.json` + outcome report | [`pit-kanban-kpi-protocol.md`](../ops/pit-kanban-kpi-protocol.md), [`pit-vault-layout.md`](../ops/pit-vault-layout.md) | decisión winner se captura fuera de MC (verbal → Rick escribe outcome) |
| Costo vs $200 | ⚠️ estimación en preflight + ledger post-hoc | [`pit_runner_core.py:154-193`](../../scripts/pit/pit_runner_core.py) (`max_cost_estimate_usd`, kill_switch stub); [`pit_collect_tokens.py`](../../scripts/pit/pit_collect_tokens.py) (P6) | **enforcement runtime = stub (PIT-3)**; ledger cuenta tokens, no USD por modelo |
| Aprendizaje / retro | ✅ contrato handoff + PIT-7 checklist | [`pit-handoff-mejora-continua.md`](../ops/pit-handoff-mejora-continua.md), [`pit-process-index.md`](../ops/pit-process-index.md) §PIT-7 | ¿proposals del piloto #1 procesadas? sin evidencia en repo |
| Skills/tools reutilizables | ⚠️ parcial: plantillas PIT en vault + ROLE templates + efímeros con histórico | [`pit-ephemeral-agent-generator.md`](../ops/pit-ephemeral-agent-generator.md) | NO hay pipeline "skill creada por lane → promovida al repo" (solo handoff genérico) |
| Spawn legal desde Telegram | ⚠️ workaround A operativo (operador corre runner) | ISSUE-001 + [`pit_tournament_run.sh`](../../scripts/pit/pit_tournament_run.sh); megaprompt listo en queue-002 §8 | sin path 100 % automático Telegram→spawn (por diseño de gates) |

**Tests verdes (esta sesión, Windows, `WORKER_TOKEN=test`):** `test_pit_spec_validate + test_pit_vault_check + test_pit_runner_tasks + test_pit_dry_run + test_pit_tournament_run + test_pit_openclaw_broker + test_pit_collect_tokens` → **165 passed, 3 skipped**. Suite MC (`tests/mission_control/test_pit_*`) existe además (routes/adapter/preview/UI/judge-UX).

---

## 5. FASE B — Flujo objetivo vs flujo real

### 5.1 Flujo IDEAL (visión David)

```text
Telegram (NL + modelos + $200)
   │
   ▼
Rick parsea → pit_spec.yaml + lanes.yaml (modelo por lane) → valida
   │  presenta spec renderizado
   ▼
David: "ok, arranca"  ──────────────── gate humano
   │
   ▼
spawn N efímeros (modelos/estrategias distintas) × iteraciones
   │  Research → Hypothesis → Prototype → KPI → Fulfillment → Review
   │  budget kill-switch runtime @100 %
   ▼
HTML "producto terminado" por lane → vault
   │
   ▼
David abre túnel (pit-judge-open.ps1) → /pit/judge/<pit_id> → compara → elige winner
   │
   ▼
outcome report + ledger costo vs $200 + retro/handoff + skills promovidas
```

### 5.2 Flujo REAL hoy (qué existe, qué es manual, qué falta)

| Paso | Estado | Cómo es hoy |
|---|---|---|
| Telegram NL → Rick | ✅ existe | skill PIT parsea; pregunta lo que falta (budget/iteraciones jamás default) |
| Spec + lanes válidos | ✅ existe | `pit_spec_validate.py` pass obligatorio pre-gate |
| Modelos por lane | ❌ v1 / ✅ v2 | v1 product: un solo `--lane-model` global; pedido David requiere extensión §6.3 |
| Gate "ok, arranca" | ✅ existe | frase literal; el runner aborta `PIT_RUN_BLOCKED` sin ella |
| Smoke pre-spawn | ✅ existe | `pit.preflight` + `pit_tournament_dry_run.sh` (PASS fresco ≤24 h obligatorio) |
| **Spawn** | ⚠️ **manual** | ISSUE-001: Rick nested no spawnea → operador/Copilot-VPS corre `pit_tournament_run.sh` (registra efímeros, `openclaw agent --agent main` fan-out, collect, kill SIEMPRE) |
| Ejecución lanes | ✅ probado | piloto #1 real; broker P9 real (modo v2) |
| Budget runtime | ❌ stub | solo estimate + ledger post-hoc |
| Preview David | ✅ código / ⚠ deploy | túnel 18089→8089 + judge UX v2; G1 queue-002 dice deployado |
| Judge/winner | ⚠️ semi-manual | MC muestra compare/highlights; David decide y se lo dice a Rick; Rick escribe `pit_outcome_report.yaml` |
| Retro/aprendizaje | ⚠️ manual | handoff con proposals → improvement-supervisor → PR gated |
| Archive | ✅ definido | Rick mueve `pit/<id>` → `archive/` |

### 5.3 Dos modos para David (explícito)

- **PIT product** (default para su visión): prototipo HTML + KPI + fulfillment. Spec v1.
- **D3 code** (solo si pide código en repo): lanes → PRs, juez sobre diffs, `gh pr merge` gated. docs/79.
- (Híbrido futuro: PIT product cuyo prototipo requiere código integrable → hoy limitado por broker read-only; ver R-5.)

---

## 6. FASE C — Gap matrix profundo

| Bloque | Estado | Severidad | Workaround hoy | Fix estructural |
|---|---|---|---|---|
| **Parser/Telegram** | Parser OK; no extrae modelos por lane ni "1M" | HIGH | David dicta modelos y Rick los anota en lanes.yaml manualmente | extender parser skill: `modelos por lane` → lanes.yaml v1.1 (§6.3) |
| **Spawn/OpenClaw** | ISSUE-001 (nested sin `sessions_spawn`) | BLOCKER técnico con workaround estable | Opción A: operador corre `pit_tournament_run.sh` post-gate | D4 Mission Control launcher (deferred, [`tournament-protocol.md`](../architecture/tournament-protocol.md) §migración) |
| **Models/policy** | 9 slugs confirmados (P3, 2026-06-21); fable-5 ✗, sonnet-5 ✗ (no existían), kimi ✗ (no es CLI) | **BLOCKER para el roster exacto de David** | usar roster disponible: gpt-5.5 / claude-opus-4.8 / claude-sonnet-4.6 / gpt-5.4-mini; kimi vía `llm.run` (kimi_azure) para lane ideacional o juez | **re-probe P3** (señal 2026-07-03: Windows ya ve `claude-fable-5`/`claude-sonnet-5`) → PR a `tool_policy.yaml` |
| **Vault/PIT-3 deploy** | Repo dice: vault activo (2 torneos con ledger) | LOW | — | ⚠ VERIFICAR `pit_vault_check.py` verde en VPS |
| **Runner PIT-2/2b** | Ejecutable, gates duros, plan-only, 165 tests | LOW | — | — |
| **Broker P4/P5** | Contrato probado (P9 golden real) | LOW (para research) / HIGH (para código escribible) | prototipos HTML los escribe la lane en el vault (no vía broker) | F9: write gates broker (missions con `max_files_touched>0`) |
| **Preview MC** | P5.1–P5.3 código completo; P5.4 deploy per plan pending pero G1 dice deployado | LOW | túnel + `/pit/access` token | ⚠ smoke `/pit/judge` en VPS antes del próximo torneo |
| **Budget enforcement** | estimate + kill-switch **stub**; ledger tokens post-hoc | **HIGH** | budgets chicos + `max_iterations` bajos + premium multipliers conocidos (gpt-5.5 7.5x, opus-4.8 1x, mini 0.33x) | PIT-3: corte duro en runner (checkpoint por iteración contra ledger parcial) |
| **Traceability** | kanban + kpi_pack + announce + ledger + outcome | LOW | — | capturar decisión winner en MC (post-MVP; hoy ADR-009 read-only) |
| **Learning loop** | contrato handoff + PIT-7 checklist | MEDIUM | retro manual post-torneo | correr PIT-7 tras próximo torneo; procesar proposals piloto #1 |
| **Reusable skills** | plantillas PIT + ROLE históricos; sin pipeline de promoción | MEDIUM | proposal en `improvement_handoff` → PR humano | definir "skill promotion": lane produce SKILL.md candidata → review → `openclaw/workspace-templates/skills/` |
| **Judge/outcome** | compare/highlights server-side + UX v2 cards | LOW | David decide verbal, Rick escribe outcome | botón "elegir winner" en MC (fuera de scope v1) |

### 6.3 Propuesta mínima (spec-only, NO implementada): per-lane model en modo product

**Opción recomendada: extender `lanes.yaml` (no `pit_spec` v1)** — el spec v1 tiene `additionalProperties: false` y no conoce lanes; el runner ya acepta `--lane-model` global y lo escribe en `entry["model"]` de cada efímero ([`pit_tournament_run.py:451-452`](../../scripts/pit/pit_tournament_run.py)). Cambio mínimo:

```yaml
# lanes.yaml v1.1 (propuesta — campos nuevos OPCIONALES por lane)
lanes:
  - lane_id: lane-vision-gpt
    lane_focus: "…ángulo…"
    lane_model: gpt-5.5            # NUEVO opcional: modelo del agente efímero OpenClaw
    reasoning_effort: xhigh        # NUEVO opcional: si la lane usa broker copilot_cli.run
```

Regla: `lane_model` ausente → hereda `--lane-model` global o default del gateway. Validación contra `tool_policy.allowed_models` cuando la lane declare uso de broker; para modelos OpenClaw-nativos (p.ej. kimi vía worker `llm.run`) el campo es informativo del runner y debe existir como alias en `openclaw.json` (pre-flight `PIT7_MODEL_BLOCKED:<alias>` si no, patrón queue-002 §4b). Esfuerzo estimado: ~2-4 h runner+tests.

---

## 7. FASE D — Roster de modelos David (investigación)

### 7.1 Slugs con evidencia (P3 audit VPS 2026-06-21, token UmbralBIM, CLI 1.0.36)

Fuente: [`04-slug-matrix.md`](../ops/evidence-imports/pit-p3-vps-copilot-slugs-audit-20260621/04-slug-matrix.md) + [`config/tool_policy.yaml`](../../config/tool_policy.yaml) (`allowed_models`, `force_default_model: false`).

| Slug | Disponible | Premium mult. | Nota |
|---|---|---|---|
| `gpt-5.5` | ✅ | 7.5x | default policy |
| `gpt-5.4` / `gpt-5.4-mini` / `gpt-5.3-codex` | ✅ | 1x / 0.33x / 1x | mini = lane económica |
| `claude-opus-4.8` | ✅ | **1x** | mejor ratio potencia/costo del roster probado |
| `claude-opus-4.7` | ✅ | 7.5x | |
| `claude-opus-4.6` | ✅ | 3x | |
| `claude-sonnet-4.6` / `claude-sonnet-4.5` | ✅ | 1x | |
| `fable-5-max` | ❌ "no such model" (probe control) | — | ver 7.3 |
| sonnet-5 | no probado (no existía 06-21) | — | ver 7.3 |
| gemini/grok/gpt-5.2-codex | ❌ entitlement | — | removidos de policy |

Hechos duros del CLI 1.0.36: `--model` exige **slug lowercase** (display names fallan; `model_aliases` en policy resuelve); `--reasoning-effort low|medium|high|xhigh` (alias `max`→`xhigh` lo normaliza el broker, [`copilot_cli.py:746+`](../../worker/tasks/copilot_cli.py)); **no existe** `copilot models list` (enumeración = probe por slug); slugs rechazados cuestan 0 premium requests.

### 7.2 Mapeo pedido David → lanes (con lo disponible HOY vs deseado)

| Lane pedido David | Deseado | Disponible hoy (probado) | Acción |
|---|---|---|---|
| A: gpt-5.5 max, 1M | `gpt-5.5` + `xhigh` | ✅ `gpt-5.5`+`xhigh` (7.5x) | "1M": sin flag CLI conocido — ver 7.4 |
| B: fable-5 max, 1M | `claude-fable-5`(?) + `xhigh` | ❌ (probe 06-21) | **re-probe**; señal 07-03: superficie Copilot Windows ya lista `claude-fable-5` |
| C: sonnet-5 max, 1M | `claude-sonnet-5`(?) + `xhigh` | ❌ (no existía) | **re-probe**; misma señal (`claude-sonnet-5`) |
| D: kimi al final | Kimi-K2.5 | ✅ pero **fuera del broker CLI**: worker `llm.run` provider `kimi_azure` ([`llm.py:71,761`](../../worker/tasks/llm.py), [`docs/kimi-recurso-n8n.md`](../kimi-recurso-n8n.md)) | lane D como lane **ideacional/synthesis** (v1 product permite LLM directo para trabajo no-código) o como asistente del juez |

Interim roster ejecutable YA (si David acepta sustitutos hasta el re-probe): A `gpt-5.5/xhigh` · B `claude-opus-4.8/xhigh` (1x!) · C `claude-sonnet-4.6/high` · D kimi (síntesis final).

### 7.3 Re-probe requerido (paso 1 del roadmap)

Comando patrón (VPS, mismo método P3, costo 0 si el slug no existe):

```bash
copilot -p "Reply with exactly: MODEL_PROBE_OK" --model claude-fable-5 \
  --available-tools=view --disable-builtin-mcps --no-color --no-ask-user
# repetir con: claude-sonnet-5, claude-fable-5-max (control), claude-sonnet-5-max (control)
```

Si pasan → PR a `tool_policy.yaml` (`allowed_models` + `model_aliases`: `Fable 5: claude-fable-5`, `Sonnet 5: claude-sonnet-5`).

### 7.4 "max + 1M" — compatibilidad real

- **"max"** = `reasoning_effort` → soportado (`xhigh` + alias `max`). ✅
- **"1M" (contexto)**: Copilot CLI 1.0.36 **no expone flag de context window**; el tier de contexto es una propiedad del modelo/plan del lado GitHub. No prometer 1M por lane hasta probarlo (un probe con archivo grande o docs oficiales del CLI). Para el path **Azure Foundry/OpenClaw** (no broker), el contexto depende del deployment (p.ej. gpt-5.4 dedicado) — tampoco hay evidencia 1M en repo. **Marcar como pregunta abierta Q-2.**
- **Kimi:** endpoint Azure `Kimi-K2.5` OpenAI-compatible; `max_tokens` configurable por request; sin evidencia de 1M.

---

## 8. FASE E — Telegram: path recomendado

| Opción | Pros | Cons |
|---|---|---|
| **A) Rick parsea en Telegram → David "ok, arranca" → Copilot-VPS/operador ejecuta `pit_tournament_run.sh`** | **Ya documentada y ensayada** (queue-002 §8 tiene el megaprompt listo); todos los gates duros del runner aplican; cero código nuevo | un humano/operador en el loop del spawn (hoy es feature, no bug: David quiere gate) |
| B) Telegram → relay a sesión `main` standalone (Control UI/CLI) | sin operador intermedio | requiere que David cambie de superficie (deja Telegram); mismo gate igual |
| C) Rick nested encola worker task `pit.*` (sin `sessions_spawn` en el turno) | legal vs ISSUE-001; los `pit.*` ya son worker tasks | el **spawn** no es worker task hoy: `pit_tournament_run.sh` edita `openclaw.json` + restart gateway — envolver eso en el Worker le da poderes de dios sobre el gateway (riesgo alto); requiere diseño de seguridad nuevo |
| D) Mission Control launcher (D4) | UX ideal futuro | fuera de alcance MVP; MC es read-only por ADR-009 |

**Recomendación MVP: Opción A.** Flujo concreto: (1) David manda el pedido NL por Telegram; (2) Rick responde con el spec renderizado + lanes/modelos + estimate; (3) David responde literal `ok, arranca`; (4) Rick publica el "paquete de ejecución" (spec + lanes + comando) y David (o Copilot-VPS bajo su instrucción) ejecuta el runner en la VPS; (5) el runner hace smoke → register → spawn desde `main` standalone → collect → kill; (6) David mira `/pit/judge/<pit_id>` por túnel. Gate adicional para broker-real: ventana L3/L4/nft abierta y cerrada por David (doctrina P9: sin autorización standing).

---

## 9. FASE F — Roadmap a próximo torneo real (estimaciones)

| # | Hito | Est. | Depende de |
|---|---|---|---|
| 1 | **Re-probe slugs** fable-5/sonnet-5 en VPS + PR `tool_policy.yaml` | 1-2 h | acceso VPS |
| 2 | **lanes.yaml v1.1** per-lane model en runner v1 + tests | 2-4 h | #1 (para validar contra policy) |
| 3 | **Budget enforcement mínimo** (PIT-3): checkpoint por iteración — runner consulta ledger parcial y aborta lanes al 100 % | 4-8 h | ledger P6 (existe) |
| 4 | **Smoke MC preview en VPS** (P5.4 verify): `/pit/access` + judge + preview firmado con torneo piloto existente | 1 h | túnel |
| 5 | **Verificar vault + outcome piloto #1** (¿winner registrado? ¿archive?) + procesar proposals handoff | 1-2 h | VPS |
| 6 | **Torneo real siguiente** — 2 candidatos: (a) queue-002 SharePoint-ACC (spec casi listo, gates G3 repo + G5 spec YAML pendientes) o (b) idea nueva David con el sample de abajo | ½-1 día | #1-#4 + gate "ok, arranca" |
| 7 | **PIT-7 auditoría** + retro → cerrar ADR-011 draft | 2-4 h | #6 |

Total estimado hasta torneo con roster David: **~2-3 días de trabajo efectivo** (asumiendo re-probe positivo).

### 9.1 Ejemplo concreto listo para David

**Mensaje Telegram sample:**

```text
Rick, armá un torneo de producto para [IDEA: p.ej. "asistente de handover
de obra que resume el día y genera el parte"], presupuesto máximo 200 USD,
4 lanes, 4 iteraciones. Modelos: lane A gpt-5.5 en max, lane B fable-5 en
max, lane C sonnet-5 en max, lane D kimi para síntesis final. Prototipo
html, research mixed, KPI: adopción diaria 60 %, tiempo de parte <120 s.
```

**pit_spec.yaml draft (v1 — validado `status: pass` con `pit_spec_validate.py` en esta sesión):**

```yaml
schema_version: 1
pit_id: pit-idea-david-01
mode: product
title: "Torneo producto — [IDEA placeholder]"
problem_statement: >-
  [Problema/oportunidad en 2-4 frases. Insumo de la fase Research;
  cada lane deriva su hipótesis de aquí.]
lane_count: 4
iteration_count: 4
budget_usd: 200
prototype_output: html
research_profile: mixed
kpi_definitions:
  - kpi_id: adopcion_diaria
    name: "Adopción diaria del prototipo"
    unit: "%"
    kpi_expected: 60
    direction: increase
    weight: 2.0
  - kpi_id: tiempo_tarea
    name: "Tiempo para completar la tarea núcleo"
    unit: "segundos"
    kpi_expected: 120
    direction: decrease
    weight: 1.0
visual_generation:
  enabled: true
  provider: magnific
  aspect_ratio: "4:3"
synthetic_personas:
  enabled: true
  labeled: true
preview_mode: tunnel+mission-control
vault: umbral-pit-vault
notes: >-
  Roster modelos por lane en lanes.yaml (v1.1 propuesto). Kimi solo
  síntesis (worker llm.run kimi_azure), nunca broker CLI.
```

**lanes.yaml draft (4 estrategias + modelos; campos `lane_model`/`reasoning_effort` = propuesta v1.1, hoy informativos):**

```yaml
lanes:
  - lane_id: lane-vision-max          # estrategia: visión de producto ambiciosa
    lane_model: gpt-5.5               # (v1.1) — disponible HOY
    reasoning_effort: xhigh
    lane_focus: >-
      Explorar la versión más ambiciosa del producto: qué haría que David
      lo muestre a un cliente mañana. Prototipo pulido, flujo completo.
  - lane_id: lane-craft-fable         # estrategia: artesanía UX/narrativa
    lane_model: claude-fable-5        # PENDIENTE re-probe; interim: claude-opus-4.8
    reasoning_effort: xhigh
    lane_focus: >-
      Priorizar experiencia y narrativa de usuario final: microcopy, flujo
      emocional, cero fricción. Menos features, más terminado.
  - lane_id: lane-pragmatic-sonnet    # estrategia: MVP integrable
    lane_model: claude-sonnet-5       # PENDIENTE re-probe; interim: claude-sonnet-4.6
    reasoning_effort: xhigh
    lane_focus: >-
      El MVP más barato de integrar al stack Umbral existente: reusar
      patrones del repo, camino a producción explícito en notes.md.
  - lane_id: lane-synthesis-kimi      # estrategia: contrarian + síntesis final
    lane_model: kimi-k2.5             # vía worker llm.run (kimi_azure) — NO broker CLI
    reasoning_effort: high
    lane_focus: >-
      Corre al final: audita los 3 prototipos, ataca supuestos, propone la
      síntesis/mezcla ganadora con evidencia de las otras lanes.
```

**Checklist pre-vuelo (antes del primer torneo con este formato):**

- [ ] Re-probe slugs (fable-5, sonnet-5) → `tool_policy.yaml` actualizado o interim aceptado por David
- [ ] `pit_spec_validate.py <spec>` → `status: pass`
- [ ] `pit_vault_check.py --require-write-scope` verde en VPS
- [ ] `pit_tournament_dry_run.sh <spec>` → `PIT_DRY_RUN_PASS` fresco (≤24 h)
- [ ] MC judge alcanzable por túnel (`pit-judge-open.ps1` → `/pit/access`)
- [ ] Si hay lanes broker: ventana L3/L4/nft autorizada por David (abrir/cerrar)
- [ ] Presupuesto: estimate ≤ `budget_usd`; acordado que enforcement es estimativo (hasta PIT-3)
- [ ] Gate literal `ok, arranca` registrado
- [ ] Post: collect → kill/desregistro SIEMPRE → outcome → ledger → retro PIT-7

---

## 10. FASE G — Riesgos y gates

| Riesgo | Mitigación existente | Residual |
|---|---|---|
| ISSUE-001 spawn nested (Telegram directo) | runner exige `main` standalone; abort `PIT_SPAWN_BLOCKED_ISSUE_001` | camino manual asumido (Opción A) |
| Budget overrun sin enforcement | estimate + kill-switch documentado + ledger post-hoc + multipliers conocidos | **HIGH hasta PIT-3**; usar budgets chicos e iteraciones cortas |
| Prototipos sin `lane_complete` (éxito falso) | collect exige `announce.md` + kpi_pack reproducible; `finalStatus=success` NO basta | bajo |
| Personas sintéticas sin label | validador obliga `labeled: true`; MC banner synthetic | bajo |
| Mezclar PIT con D3 | skill obliga pregunta explícita; ADR-011 protocolos hermanos | bajo |
| Skills efímeras no promovidas | handoff proposals → PR humano | MEDIUM: definir pipeline promoción (gap §6) |
| Costo kimi/fable/sonnet no contabilizado | ledger P6 cuenta OpenClaw+copilot_cli | kimi vía `llm.run` queda FUERA del ledger actual → sumar fuente kimi_azure al collector |
| Sandbox image drift | P1b: tag pinned `umbral-sandbox-copilot-cli:6940cf0f274d` | re-verificar imagen antes de ventana broker |
| Atribución tokens P10 (sub-sesiones de main) | limitación conocida documentada | fix follow-up en collector |
| Slug audit stale (06-21) | — | re-probe = paso 1 del roadmap |

**Gates permanentes:** `ok, arranca` literal por torneo (sin autorización standing — doctrina P9) · ventana L3/L4/nft abierta y cerrada por David para broker-real · NO URL pública · merge de este diagnóstico solo con revisión David.

---

## 11. Preguntas abiertas para David

1. **Q-1 Roster interim:** si fable-5/sonnet-5 no pasan el re-probe, ¿aceptás A `gpt-5.5/xhigh` · B `claude-opus-4.8/xhigh` · C `claude-sonnet-4.6/high` · D kimi?
2. **Q-2 "1M":** ¿el 1M es requisito duro por lane o aspiración? (Sin evidencia de flag de contexto en CLI 1.0.36 — probar antes de prometer.)
3. **Q-3 Próximo torneo:** ¿retomamos queue-002 (SharePoint-ACC, spec casi listo, tu prompt verbatim) o idea nueva con el sample §9.1?
4. **Q-4 Kimi:** ¿lane competidora completa o rol "síntesis/auditor al final" (como sugiere tu 'y kimi al final')? El draft asume síntesis.
5. **Q-5 Budget:** ¿bloqueamos el próximo torneo hasta tener enforcement runtime (PIT-3, +4-8 h) o corres con estimate+ledger como el piloto?
6. **Q-6 Piloto #1:** ¿quedó winner/outcome registrado? (⚠ VERIFICAR EN VPS; si no, cerrarlo alimenta el learning loop antes del próximo.)

## 12. Referencia cruzada ADR-011

[`ADR-011`](../adr/ADR-011-pit-product-tournament-scope.md) sigue **Draft**; sus pendientes ("PIT-2..5 implementados · primer piloto PIT-6 · revisión PIT-7") están sustancialmente cumplidos según evidencia de repo (piloto real + broker golden). **Propuesta:** tras el próximo torneo con gate David + PIT-7, promover ADR-011 a *Accepted* citando este diagnóstico.

---

*Diagnóstico generado en modo read-only. Ningún torneo fue ejecutado, ningún gate abierto, ningún write fuera de este PR doc-only.*
