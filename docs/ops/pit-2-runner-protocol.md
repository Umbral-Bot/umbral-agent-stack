# PIT-2 — Runner de orquestación (smoke local, sin spawn OpenClaw)

- **Status:** v1 (PIT-2) — 2026-06-10. Implementado en `claude/feat-pit-2-runner`.
- **Visión:** [`product-innovation-tournament-vision-2026-06-09.md`](product-innovation-tournament-vision-2026-06-09.md). **Índice:** [`pit-process-index.md`](pit-process-index.md).
- **Re-scope del roadmap:** el hito PIT-2 pasó de "research sandbox" (visión §5) a **runner de orquestación ejecutable** por decisión David 2026-06-10. El research sandbox (`pit.research_fetch`) queda re-secuenciado post PIT-2b.
- **Qué NO hace este hito:** NO spawn de agentes efímeros OpenClaw (`sessions_spawn`) — eso es **PIT-2b** (siguiente PR). NO piloto real, NO deploy VPS, NO Magnific, NO internet.

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

## 7. PIT-2b — siguiente PR (spawn real)

Lo que este hito deja explícitamente fuera y PIT-2b implementa:

1. Spawn real de agentes efímeros vía OpenClaw `sessions_spawn` (G-D1b,
   ISSUE-001, 2–5 lanes) usando el
   [generador de efímeros](pit-ephemeral-agent-generator.md).
2. Lanes corriendo su ciclo real (Research → … → Review) contra el pit-vault de
   la VPS, con announce real por sesión (las mismas 3 líneas literales).
3. Collect del parent verificando `lane_complete` con `pit.lane_announce`.
4. Kill + desregistro de efímeros al cierre.

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
