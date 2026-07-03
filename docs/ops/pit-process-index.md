# PIT — Índice de procesos

- **Status:** v1.2 — 2026-06-10 (PIT-2 runner smoke + PIT-2b spawn real implementados). Punto de entrada único a todos los procesos PIT; si un proceso no está aquí, no es canónico.
- **Visión:** [`product-innovation-tournament-vision-2026-06-09.md`](product-innovation-tournament-vision-2026-06-09.md).
- **Re-scope PIT-2 (2026-06-10):** PIT-2 = runner de orquestación ejecutable (smoke local, [`pit-2-runner-protocol.md`](pit-2-runner-protocol.md)); PIT-2b = spawn real OpenClaw post-smoke (mismo protocolo §7); el research sandbox quedó re-secuenciado post PIT-2b.

---

## Procesos

| # | Proceso | Doc canónico | Resumen |
|---|---------|--------------|---------|
| 1 | **Spawn** (invocación → torneo) | [SKILL product-innovation-tournament](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md) | NL o `/torneo_producto` → parser → `pit_spec.yaml` validado → gate literal `ok, arranca` → spawn de agentes efímeros |
| 2 | **Agentes efímeros** | [pit-ephemeral-agent-generator.md](pit-ephemeral-agent-generator.md) | Rick genera prompts/skills/accesos por torneo desde [`ROLE.template.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.template.md); kill + desregistro al cierre |
| 3 | **Research** | [pit-kanban-kpi-protocol.md](pit-kanban-kpi-protocol.md) §1 + SKILL | Tiers `academic \| market_pain \| competitive \| mixed` según spec; fuentes citadas en notes.md. Sandbox `pit.research_fetch` re-secuenciado post PIT-2b (PIT-2 pasó a ser el runner) |
| 4 | **Broker** (visual + capacidades) | [pit-visual-magnific.md](pit-visual-magnific.md) + [copilot-cli-autonomy-vision-roadmap.md](../copilot-cli-autonomy-vision-roadmap.md) | Las lanes no llaman servicios externos directo: piden a Rick. v1: visual Magnific; futuro: mismo patrón broker para Copilot CLI |
| 5 | **Kanban** | [pit-kanban-kpi-protocol.md](pit-kanban-kpi-protocol.md) §1 | 9 columnas canónicas (Backlog → … → Done, Stuck); plantilla [`kanban-lane.md`](../../openclaw/workspace-templates/pit-vault/templates/kanban-lane.md) |
| 6 | **KPI + fulfillment** | [pit-kanban-kpi-protocol.md](pit-kanban-kpi-protocol.md) §2–§3 | Hipótesis ↔ KPI; `kpi_pack.json` por iteración ([schema](../../openclaw/workspace-templates/pit-vault/templates/kpi-pack.schema.json)); fórmula 0–1 ejecutable (`compute_fulfillment`) |
| 7 | **Visual Magnific 4:3** | [pit-visual-magnific.md](pit-visual-magnific.md) + [umbral-bim-magnific-visual-style-v1.md](umbral-bim-magnific-visual-style-v1.md) | Default `4:3` canónico Umbral; gate columna Prototype; sin autopublicación |
| 8 | **Cierre de lane y torneo** | SKILL §Cierre + [pit-kanban-kpi-protocol.md](pit-kanban-kpi-protocol.md) §4 | `PROTOTYPE_URL=` + `KPI_PACK=` + `FULFILLMENT=` verificables; judge ≥2 lanes completas; gate David; [`pit_outcome_report.yaml`](../../openclaw/workspace-templates/pit-vault/templates/pit_outcome_report.yaml) |
| 8b | **Entrega Telegram** (deck Drive) | [pit-telegram-drive-deliverables-runbook.md](pit-telegram-drive-deliverables-runbook.md) + SKILL §Entrega Telegram | Post-outcome: `pit_deliver_telegram_pack.py` → deck `.pptx` en `pit/<pit_id>/deliverables/` → upload a carpeta Drive compartida Rick↔David → Rick manda **solo el link** por Telegram (≤12 líneas; nunca el archivo) |
| 9 | **Plantillas** | SKILL §Plantillas | "guarda como plantilla PIT `<nombre>`" → `templates/pit-<nombre>.yaml`; budget e iteraciones se re-preguntan SIEMPRE al reusar |
| 10 | **Archive** | [pit-vault-layout.md](pit-vault-layout.md) §2 | Rick mueve `pit/<pit_id>/` → `archive/<pit_id>/` al cierre; las lanes nunca |
| 11 | **Capitalización** (mejora continua) | [pit-handoff-mejora-continua.md](pit-handoff-mejora-continua.md) | `improvement_handoff.proposals[]` → improvement-supervisor → PR con gate humano; sin auto-merge |
| 12 | **Vault** (estructura + checks) | [pit-vault-layout.md](pit-vault-layout.md) | `umbral-pit-vault` separado; writes solo `pit/`; `pit_vault_init.sh` + `pit_vault_check.py` |
| 13 | **Runner smoke (PIT-2)** | [pit-2-runner-protocol.md](pit-2-runner-protocol.md) | Tasks Worker `pit.preflight / pit.lane_init / pit.iteration_close / pit.lane_announce` + `pit_tournament_dry_run.sh` (N lanes simuladas, sin spawn OpenClaw); budget kill switch documentado (stub — enforcement PIT-3) |
| 14 | **Runner spawn (PIT-2b)** | [pit-2-runner-protocol.md](pit-2-runner-protocol.md) §7 | `pit_tournament_run.sh`: gate literal + smoke `PIT_DRY_RUN_PASS` fresco → register efímeros → `sessions_spawn` × N desde `main` standalone (G-D1b) → collect contra el vault (lane result file `announce.md` + `pit.lane_announce`) → kill/desregistro SIEMPRE; veredictos `PIT_RUN_PASS\|PARTIAL\|FAIL\|BLOCKED\|PLAN_ONLY` |

## Contratos ejecutables

- `python scripts/pit/pit_spec_validate.py <spec.yaml>` — spec válido antes del gate.
- `python scripts/pit/pit_vault_check.py --vault-path <vault> --require-write-scope` — vault sano (con `PIT_VAULT_WRITE_SCOPE=pit`).
- `bash scripts/pit/pit_tournament_dry_run.sh examples/pit-salud-mental-pilot.yaml` — smoke PIT-2 local (sin OpenClaw); veredicto `PIT_DRY_RUN_PASS` en `~/.coord-ag-evidence/pit-dry-run/<pit_id>/final-metrics.json`.
- `bash scripts/pit/pit_tournament_run.sh <spec.yaml> <lanes.yaml> --gate "ok, arranca" [--plan-only]` — torneo real PIT-2b post-smoke (`--plan-only` valida sin spawn); veredicto `PIT_RUN_*` en `~/.coord-ag-evidence/pit-run/<pit_id>/run-metrics.json`.
- `python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id> [--dry-run]` — entrega post-torneo (paso 8b): deck + upload Drive + `telegram_pack.json`; veredicto `PIT_DELIVER_PACK_OK|DRY_OK|FAIL`.
- `WORKER_TOKEN=test python -m pytest tests/test_pit_spec_validate.py tests/test_pit_vault_check.py tests/test_pit_runner_tasks.py tests/test_pit_dry_run.py tests/test_pit_tournament_run.py -q` — contratos verdes en CI/local.

---

## PIT-7 — Checklist de auditoría de procesos (post-construcción)

Cuando el sistema esté construido y haya corrido ≥1 torneo real (PIT-6), PIT-7 audita proceso por proceso. Marcar con evidencia, no de memoria:

- [ ] **Spawn:** ¿todos los torneos corridos tienen frase `ok, arranca` registrada antes del spawn? ¿algún spawn sin gate?
- [ ] **Budget/iteraciones:** ¿algún torneo arrancó con `budget_usd` o `iteration_count` no provistos por David (default colado)?
- [ ] **Efímeros:** ¿agentes de torneos cerrados siguen activos/registrados? ¿algún agente reciclado entre torneos?
- [ ] **Research:** ¿las lanes citaron fuentes según su tier? ¿research sin trazas?
- [ ] **Kanban:** ¿columnas renombradas/salteadas? ¿tarjetas >1 iteración en Stuck sin reporte en outcome?
- [ ] **KPI:** ¿todos los `kpi_pack.json` validan contra el schema? ¿`fulfillment_score` reproducible con `compute_fulfillment`? ¿señales sintéticas etiquetadas al 100 %?
- [ ] **Visual:** ¿generaciones fuera de gate (columna ≠ Prototype, hipótesis no validada)? ¿algún ratio ≠ 4:3 sin pedido explícito David? ¿algún asset PIT autopublicado?
- [ ] **Preview:** ¿alguna URL pública creada? (debe ser cero)
- [ ] **Cierre:** ¿lanes contadas como completas sin las 3 líneas literales verificables?
- [ ] **Plantillas:** ¿plantillas guardadas funcionan al reusar? ¿budget/iteraciones re-preguntados?
- [ ] **Archive:** ¿torneos cerrados fuera de `archive/`? ¿lanes moviendo a archive?
- [ ] **Capitalización:** ¿proposals del handoff procesadas o acumulando polvo? ¿algún cambio de prompt mergeado sin PR/gate humano? (debe ser cero)
- [ ] **Vault:** `pit_vault_check.py` verde en VPS; ¿secretos detectados alguna vez? ¿writes fuera de `pit/`?
- [ ] **Presupuesto:** gasto real vs `budget_usd` por torneo; ¿desvíos >20 % sin explicación?

Salida de PIT-7: reporte en `docs/ops/` + propuestas de corrección vía [handoff de mejora continua](pit-handoff-mejora-continua.md).
