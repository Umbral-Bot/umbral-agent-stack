# PIT-2 — Runner de orquestación (smoke local + spawn real PIT-2b)

- **Status:** v1.1 (PIT-2 + PIT-2b) — 2026-06-10. PIT-2 (smoke) en `claude/feat-pit-2-runner`; PIT-2b (spawn real, §7) en `claude/feat-pit-2b-spawn`.
- **Visión:** [`product-innovation-tournament-vision-2026-06-09.md`](product-innovation-tournament-vision-2026-06-09.md). **Índice:** [`pit-process-index.md`](pit-process-index.md).
- **Re-scope del roadmap:** el hito PIT-2 pasó de "research sandbox" (visión §5) a **runner de orquestación ejecutable** por decisión David 2026-06-10. El research sandbox (`pit.research_fetch`) queda re-secuenciado post PIT-2b.
- **Qué NO hace este doc (ni PIT-2b):** NO piloto real sin gate David (`ok, arranca` literal al runner), NO Magnific directo (broker Rick), NO URL pública, NO enforcement de budget en runtime (PIT-3).

---

## 1. Piezas

| Pieza | Archivo | Qué hace |
|---|---|---|
| Core ejecutable | [`scripts/pit/pit_runner_core.py`](../../scripts/pit/pit_runner_core.py) | preflight / lane_init / iteration_close / lane_announce sobre el pit-vault |
| Tasks Worker `pit.*` | [`worker/tasks/pit_runner.py`](../../worker/tasks/pit_runner.py) | wrappers finos del core, registrados en `TASK_HANDLERS` |
| Smoke orquestador | [`scripts/pit/pit_tournament_dry_run.sh`](../../scripts/pit/pit_tournament_dry_run.sh) → [`pit_dry_run.py`](../../scripts/pit/pit_dry_run.py) | torneo completo simulado, N lanes secuenciales |
| Tests | `tests/test_pit_runner_tasks.py` + `tests/test_pit_dry_run.py` | contratos del runner verdes en CI |

El core y las tasks comparten exactamente la misma implementación: lo que pasa
el smoke local es lo que ejecutará el Worker en la VPS.

## 2. Tasks Worker `pit.*`

Mismo patrón handler que D3 (`(input: dict) -> dict` con `ok`/`error`);
`vault_path` sale del input o de `PIT_VAULT_PATH`.

| Task | Input mínimo | Hace | Output clave |
|---|---|---|---|
| `pit.preflight` | `spec_path` (+`vault_path`, `require_write_scope`) | valida `pit_spec.yaml` (pydantic), budget y `pit_vault_check` read-only | `verdict: PIT_PREFLIGHT_PASS\|FAIL`, `budget{max_cost_estimate_usd, kill_switch}` |
| `pit.lane_init` | `pit_id`, `lane_id` (+`research_profile`) | crea `pit/<pit_id>/lanes/<lane_id>/kanban/board.md` (plantilla 9 columnas, placeholders rellenos) + `iterations/1/` | `board_path`, `board_created` (idempotente: nunca clobbea) |
| `pit.iteration_close` | `pit_id`, `lane_id`, `iteration` (1–10), `hypothesis`, `kpis` | calcula `fulfillment_score` con `compute_fulfillment`, escribe `iterations/<n>/kpi_pack.json` (válido contra schema) y agrega la tarjeta Hypothesis→KPI→Fulfillment al kanban | `kpi_pack_path`, `fulfillment_score`, `schema_validation` |
| `pit.lane_announce` | `pit_id`, `lane_id` (+`iteration`, `prototype_url`) | emite las 3 líneas literales de cierre y verifica reproducibilidad del fulfillment | `announce`, `lane_complete`, `incomplete_reasons` |

Notas de contrato:

- **Iteraciones 1-based:** `kpi-pack.schema.json` exige `iteration >= 1`; la
  "iteración 0" no existe — `pit.lane_init` pre-crea `iterations/1/`.
- **Write scope:** los ids se validan contra los patrones del schema (sin `/`,
  `\` ni `.`), así que las tasks solo pueden escribir bajo
  `pit/<pit_id>/lanes/<lane_id>/` ([`pit-vault-layout.md`](pit-vault-layout.md) §3).
- **`fulfillment_score` nunca viene del caller:** siempre se recalcula con
  `compute_fulfillment()` ([`pit-kanban-kpi-protocol.md`](pit-kanban-kpi-protocol.md) §3).
- **`lane_complete`** = `PROTOTYPE_URL` presente **y** fulfillment del kpi_pack
  reproducible. `finalStatus=success` sin eso ⇒ `lane_incomplete` (regla dura,
  paralela a docs/79 §4.1).
- Las señales sintéticas van SIEMPRE `synthetic: true` y
  `synthetic_personas.labeled: true` (no configurable).

## 3. Smoke `pit_tournament_dry_run.sh`

```bash
bash scripts/pit/pit_tournament_dry_run.sh examples/pit-salud-mental-pilot.yaml
# evidencia: ~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json
```

Qué simula, en secuencia y sin OpenClaw:

```text
spec.yaml ──pydantic──► vault scratch (<evidence>/vault, espejo de pit_vault_init.sh)
   │
   ├─ preflight (require_write_scope=true, PIT_VAULT_WRITE_SCOPE=pit)
   └─ por cada lane (lane-dry-a..e, secuencial):
        lane_init → iteration_close (1 iteración fake) → lane_announce
```

- **Señales fake deterministas:** sin RNG; el fulfillment de cada lane queda
  igual a su factor (`0.6, 0.8, 1.0, 0.7, 0.9`), verificable a ojo y en tests.
  Todas etiquetadas `synthetic: true`, hipótesis `validated: null` (inconclusa
  — es data fake, no valida nada).
- **`PROTOTYPE_URL` dry:** `https://dry-run.invalid/...` (TLD reservado RFC
  2606 — garantiza no-ruteo; en smoke las URLs dry son válidas para el announce).
- **Hard constraints:** NO internet, NO Magnific, NO `sessions_spawn` — quedan
  asentadas en `final-metrics.json.constraints`.
- **Veredicto:** `PIT_DRY_RUN_PASS` (exit 0) solo si preflight PASS y todas las
  lanes `lane_complete`; cualquier otra cosa `PIT_DRY_RUN_FAIL` (exit 1).
- `winner_candidate` del metrics es **informativo**: el winner real sale del
  juez + gate David (fuera del smoke).

### Layout de evidencia

```text
~/.coord-ag-evidence/pit-dry-run/<pit_id>/
├── final-metrics.json    # veredicto + budget + lanes + announces
└── vault/                # pit-vault scratch del smoke (descartable)
    └── pit/<pit_id>/lanes/lane-dry-*/...
```

## 4. Budget kill switch (stub PIT-2 → enforcement PIT-3)

- `pit_spec.budget_usd` (SIEMPRE input David, sin default) actúa en PIT-2 como
  **max cost estimate**: `pit.preflight` y el dry-run lo loguean como tope
  estimado (`max_cost_estimate_usd`) junto con `budget_per_lane_usd`.
- **Regla documentada:** al alcanzar el **100 %** del `budget_usd` estimado, el
  torneo se corta (kill) — ninguna lane sigue iterando y el estado se reporta a
  David vía outcome report.
- **Estado PIT-2:** el corte NO está aplicado por runtime
  (`kill_switch.enforced: false` en preflight/metrics); solo estimación + log.
  El enforcement real (tracking de gasto por lane + corte duro) es **PIT-3**
  (`kill_switch.enforcement_milestone`).

## 5. Guardrails

- **D3 intacto:** `tournament_lane.*`, `tournament.run` y
  `github.orchestrate_tournament` no se tocan (test de regresión en
  `tests/test_pit_runner_tasks.py::TestTaskRegistry`).
- Los gates humanos de PIT no cambian: `ok, arranca` antes de orquestar,
  fulfillment/winner con gate David, nunca URL pública.
- El smoke se ejecuta **post-gate y pre-spawn** (ver
  [SKILL](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md)
  §Smoke runner PIT-2): smoke rojo ⇒ no spawn.

## 6. Verificación

```bash
# contratos del runner
WORKER_TOKEN=test python -m pytest tests/test_pit_runner_tasks.py tests/test_pit_dry_run.py -q

# smoke completo con el piloto canónico
bash scripts/pit/pit_tournament_dry_run.sh examples/pit-salud-mental-pilot.yaml
cat ~/.coord-ag-evidence/pit-dry-run/pit-salud-mental-pilot/final-metrics.json
```

## 7. PIT-2b — spawn real de agentes efímeros (implementado)

Runner del torneo real post-smoke, patrón **D3.5b** (`sessions_spawn` × N +
yield + lane result files — evidencia VPS PRs #472/#473):

```bash
bash scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> --gate "ok, arranca"
# evidencia: ~/.coord-ag-evidence/pit-run/<pit_id>/run-metrics.json
```

| Pieza | Archivo | Qué hace |
|---|---|---|
| Runner spawn | [`scripts/pit/pit_tournament_run.sh`](../../scripts/pit/pit_tournament_run.sh) → [`pit_tournament_run.py`](../../scripts/pit/pit_tournament_run.py) | gate → smoke gate → preflight → generate → register → spawn → collect → kill/desregistro |
| Lanes file | ej. [`examples/pit-salud-mental-pilot.lanes.yaml`](../../examples/pit-salud-mental-pilot.lanes.yaml) | identidades por torneo (`lane_id` + `lane_focus`) derivadas por Rick (generador §2.1) |
| Tests | `tests/test_pit_tournament_run.py` | contratos spawn/collect/kill con mock del binario `openclaw` |

### 7.1 Fases del runner

1. **Gate David** — `--gate` debe ser la frase literal `ok, arranca`;
   cualquier otra cosa ⇒ `PIT_RUN_BLOCKED` sin tocar nada.
2. **Smoke gate** — lee `~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json`
   y exige `PIT_DRY_RUN_PASS` **fresco** (≤24 h por default, `--max-smoke-age-hours`)
   para el MISMO `pit_id` y `lane_count`. Smoke rojo/ausente/viejo ⇒ abort.
3. **Preflight** — misma implementación que la task `pit.preflight`
   (`require_write_scope=true`) contra el vault real (`PIT_VAULT_PATH` o
   `~/umbral-pit-vault`).
4. **Generate** — render de `ROLE.template.md` por lane (generador §3) +
   `agents.yaml` + roles en `pit/<pit_id>/spec/` (histórico) y en la evidencia.
5. **Register** — alta de efímeros `<pit_id>-<lane_id>` en `agents.list` de
   `openclaw.json` (backup `openclaw.json.bak-<pit_id>` + escritura atómica),
   workspace por agente con su ROLE como `AGENTS.md`, allowAgents de `main`
   parcheado (respeta `"*"`), restart gateway. Ids ya registrados ⇒ abort
   (no se reciclan efímeros entre torneos).
6. **Spawn** — `openclaw agent --agent main -m <prompt>` (sesión **standalone**,
   G-D1b): el prompt instruye a `main` a disparar los N `sessions_spawn` en un
   solo turno y **terminar el turno** (yield). Si `main` responde
   `PIT_SPAWN_BLOCKED_ISSUE_001` (sesión nested sin `sessions_spawn`), no hay
   collect.
7. **Collect** — el parent NO lee transcripts: poll del vault hasta
   `--collect-timeout-seconds`. `lane_complete` obligatorio =
   `pit/<pit_id>/lanes/<lane_id>/announce.md` presente (**lane result file**)
   **+** kpi_pack reproducible vía la misma implementación de
   `pit.lane_announce` (regla de verdad del SKILL §Cierre, paralela a docs/79
   §4.1).
8. **Kill + desregistro** — SIEMPRE (finally), aunque spawn/collect fallen:
   kill de subagentes vivos del torneo (filtro por label `<pit_id>-lane-`,
   nunca hijos ajenos), baja de `agents.list` + allowAgents + restart, y
   `agents.yaml` actualizado (`status: closed`, `killed_at`, `deregistered`)
   como evidencia de qué existió. Workspaces quedan en disco como forense.

### 7.2 Veredictos y exit codes

| Veredicto | Condición | Exit |
|---|---|---|
| `PIT_RUN_PASS` | todas las lanes `lane_complete` | 0 |
| `PIT_RUN_PARTIAL` | ≥2 lanes completas (judge posible) pero no todas | 1 |
| `PIT_RUN_FAIL` | <2 lanes completas o spawn bloqueado | 1 |
| `PIT_RUN_BLOCKED` | gate/smoke/preflight/lanes/registro fallaron pre-spawn | 2 |
| `PIT_RUN_PLAN_ONLY` | `--plan-only`: plan renderizado, sin registro ni spawn | 0 |

El judge + winner siguen FUERA del runner: gate David sobre el outcome report
(SKILL §Cierre). `PIT_RUN_PARTIAL` habilita judge con las lanes completas,
como docs/79 §4.1.

### 7.3 Flags operativos

- `--plan-only` — valida gates y renderiza prompt/roles/agents.yaml en la
  evidencia sin tocar vault ni runtime (validación post-merge sin budget).
- `--lane-model` / `--lane-tools-profile` — overrides de los efímeros
  (el profile mínimo lo fija Copilot-VPS en el piloto).
- `--lane-timeout-seconds` (1800) / `--spawn-timeout-seconds` (900) /
  `--collect-timeout-seconds` (3600) / `--collect-poll-seconds` (30).
- `--skip-gateway-restart` — el operador reinicia a mano.
- `--openclaw-config` / `OPENCLAW_CONFIG_PATH`, `--vault-path` /
  `PIT_VAULT_PATH`, `OPENCLAW_BIN`.

## 8. Post-merge (Copilot-VPS smoke)

En la VPS (clone `~/umbral-agent-stack`, pit-vault ya desplegado en PIT-1):

```bash
cd ~/umbral-agent-stack && git pull --ff-only origin main
bash scripts/pit/pit_tournament_dry_run.sh examples/pit-salud-mental-pilot.yaml
test -f ~/.coord-ag-evidence/pit-dry-run/pit-salud-mental-pilot/final-metrics.json \
  && grep -o 'PIT_DRY_RUN_[A-Z]*' ~/.coord-ag-evidence/pit-dry-run/pit-salud-mental-pilot/final-metrics.json
# esperado: PIT_DRY_RUN_PASS — guardar salida en ~/.coord-ag-evidence/
```

El dry-run usa su vault scratch propio: NO escribe en `~/umbral-pit-vault` ni
toca `openclaw.json`.

### 8.1 Post-merge PIT-2b (Copilot-VPS, sin spawn real)

Validación del runner de spawn SIN gastar budget ni tocar el runtime
(`--plan-only` no registra agentes, no reinicia gateway, no spawnea):

```bash
cd ~/umbral-agent-stack && git pull --ff-only origin main

# 1. Smoke PIT-2 fresco para el spec del piloto (gate del runner)
bash scripts/pit/pit_tournament_dry_run.sh examples/pit-salud-mental-pilot.yaml

# 2. Runner en plan-only contra el vault real
bash scripts/pit/pit_tournament_run.sh examples/pit-salud-mental-pilot.yaml \
  examples/pit-salud-mental-pilot.lanes.yaml --gate "ok, arranca" --plan-only
grep -o 'PIT_RUN_[A-Z_]*' ~/.coord-ag-evidence/pit-run/pit-salud-mental-pilot/run-metrics.json
# esperado: PIT_RUN_PLAN_ONLY; revisar spawn-prompt.md + roles/ renderizados

# 3. Verificar superficies CLI que el runner usa en modo real
command -v openclaw && openclaw tasks list --runtime subagent --json | head -5
# confirmar también: `openclaw subagents kill <id>` y `openclaw gateway restart`
# disponibles en esta versión del CLI; reportar drift si cambió la superficie
```

El primer spawn real (piloto `pit-salud-mental-pilot`) queda detrás del gate
David `ok, arranca` + frase de arranque del piloto; antes de correrlo, fijar
`--lane-tools-profile` mínimo para los efímeros (decisión Copilot-VPS +
David). Checklist completo de gates en el
[SKILL](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md)
§Hard stops.
