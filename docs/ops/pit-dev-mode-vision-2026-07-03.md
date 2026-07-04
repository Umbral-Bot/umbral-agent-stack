# PIT-DEV — Torneo "developer product" (visión + decisiones canónicas)

- **Status:** v1 (PIT-DEV) — 2026-07-03.
- **Registro canónico de la visión de David** para el nuevo modo de torneo donde
  el deliverable es un **producto técnico usable** (no un mock HTML). Este doc es
  la fuente de verdad del contrato PIT-DEV; el spec ejecutable es
  `pit_spec` `schema_version: 3` / `mode: dev`
  ([`scripts/pit/pit_spec_validate.py`](../../scripts/pit/pit_spec_validate.py)).
- Los modos existentes NO cambian: v1 producto (PROTOTYPE_URL + KPI) y v2 broker
  (`copilot_cli.run`) siguen intactos con sus contratos y tests.

---

## 1. Visión David (decisiones canónicas — 2026-07-03)

1. **Workspace curado por lane.** Rick prepara por lane un workspace curado:
   snapshot del repo (ref pinneado, `git archive`) + `CONTEXT_INDEX.md` con todo
   lo que la lane necesita saber del proyecto. Las lanes **NO trabajan sobre
   `main` vivo**. Herramienta:
   [`scripts/pit/pit_lane_workspace_init.sh`](../../scripts/pit/pit_lane_workspace_init.sh)
   (§4 de este doc).
2. **Ciclo dev por lane.** Las lanes investigan → prototipan → **PRUEBAN (tests
   reales)** → iteran hasta considerar el producto terminado (tope
   `iteration_count` del spec).
3. **Egress monitoreado.** Toda comunicación exterior de las lanes (búsquedas
   web, fetches) queda monitoreada: un agente exclusivo con rol de seguridad
   (`<pit_id>-security`, o Rick) audita el log de egress por lane
   ([`pit-security-egress-monitor.md`](pit-security-egress-monitor.md)).
4. **Jueces ejecutores.** Al cierre de lanes, jueces subagentes (también
   supervisados por seguridad) **instalan, ejecutan y evalúan** cada deliverable
   contra una rúbrica ejecutable
   ([`pit-dev-judge-protocol.md`](pit-dev-judge-protocol.md)).
5. **Rick consolida.** Rick ordena la información, decide (con gate David) y
   construye la presentación con resultados + demos (deck → Drive, flujo
   PIT-TG-DRIVE existente:
   [`pit-telegram-drive-deliverables-runbook.md`](pit-telegram-drive-deliverables-runbook.md)).
6. **Trazabilidad post-torneo.** Un agente de trazabilidad revisa que todo el
   proceso quedó trazable (spec→lanes→iteraciones→tests→judge→outcome→deck).
   Gaps → informe a Rick → Rick propone estrategia de trazabilidad automática
   (entra a mejora continua). ([`pit-traceability-agent.md`](pit-traceability-agent.md)).
7. **Rendición a David.** Rick pide autorización en decisiones importantes,
   analiza trazabilidad + eficiencia (tokens/costo/tiempo por lane), registra y
   propone mejoras para que cada torneo sea más eficiente que el anterior
   ([`pit-handoff-mejora-continua.md`](pit-handoff-mejora-continua.md) §5).
8. **Magnific: prohibido para toda lane/juez/subagente en TODOS los modos.**
   Solo Rick, fuera de las lanes, si el torneo lo pide en spec.
   `visual_generation` es decisión de Rick **post-judge para el deck**, no una
   herramienta de lane. Hard stop: *lane/juez pide Magnific ⇒ `lane_blocked`*.

---

## 2. Contraste de los 3 modos

| | **D3 code** | **PIT product (v1)** | **PIT-DEV (v3)** |
|---|---|---|---|
| Skill | `multi-agent-tournament-orchestrator` | `product-innovation-tournament` | `product-innovation-tournament` §PIT-DEV |
| Spec | tournament spec (docs/79) | `pit_spec` v1 (`mode: product`) | `pit_spec` v3 (`mode: dev`) |
| Unidad de competencia | rama + PR sobre `main` | hipótesis + prototipo + KPI | producto técnico usable + tests reales |
| Workspace | git worktree por lane | subárbol vault | **workspace curado**: snapshot repo (ref pinneado) + `CONTEXT_INDEX.md` |
| Cierre de lane | `PR_URL=` | `PROTOTYPE_URL=` + `KPI_PACK=` + `FULFILLMENT=` | `DELIVERABLE_PATH=` + `TEST_REPORT=` + `SELF_ASSESSMENT=` |
| Juez | rubric sobre diffs/checks | fulfillment_score + scorecard producto | **jueces ejecutores**: instalan, corren, evalúan (rúbrica ejecutable) |
| Seguridad | gates operador | gates operador | + agente `security` (egress ledger + veredicto) |
| Trazabilidad | evidencia D3.5b | outcome report | + agente `traceability` (cadena completa verificada) |
| Merge/decisión | `gh pr merge` gate David | fulfillment decision gate David | winner gate David; el ranking NO decide |

## 3. Cierre de lane PIT-DEV (contrato verificable)

El announce final de una lane dev termina con **tres líneas literales** y las
persiste en `pit/<pit_id>/lanes/<lane_id>/announce.md` (lane result file,
patrón D3.5b):

```text
DELIVERABLE_PATH=pit/<pit_id>/lanes/<lane_id>/deliverable/
TEST_REPORT=pit/<pit_id>/lanes/<lane_id>/iterations/<n>/test_report.json
SELF_ASSESSMENT=<0-1>
```

Regla de verdad (paralela al `KPI_PACK` reproducible de v1 y al `PR_URL`
verificable de D3):

```text
lane_complete = deliverable_presente_y_no_vacío
             && test_report_válido_contra_schema     # templates/test-report.schema.json
             && test_report.exit_code == 0
             && tests_re_ejecutables_por_el_collect  # comando declarado en el report
```

- `test_report.json` valida contra
  [`test-report.schema.json`](../../openclaw/workspace-templates/pit-vault/templates/test-report.schema.json):
  declara `command` (argv), `workdir` (relativo a la lane), `exit_code`,
  `total/passed/failed`. El collect puede **re-ejecutar** el comando declarado
  (`--re-run-tests`) y exige `exit_code == 0` — misma filosofía que el
  `fulfillment_score` reproducible del kpi_pack.
- `SELF_ASSESSMENT` ∈ [0, 1] es la autoevaluación de la lane contra el
  `deliverable_spec`; es señal, no veredicto — el veredicto es de los jueces.
- Sin esas líneas verificables la lane cuenta como `lane_incomplete`, aunque
  haya terminado "bien". Verificación ejecutable:
  [`scripts/pit/pit_dev_core.py`](../../scripts/pit/pit_dev_core.py)
  (`verify_dev_lane`).

## 4. Workspace curado por lane

Herramienta: [`scripts/pit/pit_lane_workspace_init.sh`](../../scripts/pit/pit_lane_workspace_init.sh)
(wrapper de [`pit_lane_workspace_init.py`](../../scripts/pit/pit_lane_workspace_init.py)).

- **Input:** `pit_id`, `lane_id`, repo local + **ref pinneado** (tag/commit —
  `repo_ref` del spec). Las lanes nunca trabajan sobre `main` vivo.
- **Output:** `pit/<pit_id>/lanes/<lane_id>/workspace/` con:
  - `snapshot/` — snapshot **read-only** del repo (`git archive <ref>`, NO
    worktree sobre main vivo);
  - `CONTEXT_INDEX.md` generado: mapa de `docs/`, `worker/`, `dispatcher/`,
    `client/`, `scripts/`; endpoints del Worker (desde `worker/app.py`); tasks
    registradas (`worker/tasks/`); env vars **lógicas** (nombres desde
    `.env.example`, **JAMÁS valores**) — "toda la información que la lane
    necesita".
- La lane escribe su producto en `deliverable/` (**fuera** del snapshot). Nunca
  parchea el snapshot para "mejorar main": el torneo produce un **artefacto
  nuevo**, no un PR.
- Guard ejecutable: `pit_vault_check.py` falla si aparece un directorio
  `workspace/` fuera de `pit/<pit_id>/lanes/<lane_id>/workspace/`.
- Nota operativa: un snapshot completo puede superar el tope de scan del vault
  check (`max_files=5000`); el check trunca con warning, no con error.

## 5. Fases del torneo PIT-DEV (runner)

Runner: [`scripts/pit/pit_dev_run.py`](../../scripts/pit/pit_dev_run.py)
(despachado automáticamente por `pit_tournament_run.{sh,py}` cuando el spec es
`mode: dev` — mismo patrón que la delegación broker v2).

```text
gate literal "ok, arranca"
  → dev preflight (spec v3 válido + vault check)
  → workspace init × lane (snapshot + CONTEXT_INDEX)
  → render roles (lanes dev + security + judges + traceability) + agents.yaml
  → register + spawn lanes (fan-out sessions_spawn desde main, G-D1b)
  → collect lanes (announce.md + deliverable + test_report — §3)
  → consolidación egress + spawn security → veredicto EGRESS_CLEAN|EGRESS_FLAGGED
  → [gate: lane flagged NO va a judge sin decisión explícita]
  → spawn judges (N=judge_count) → scorecards + ranking agregado
  → kill + desregistro SIEMPRE (finally)
  → run-metrics.json
--phase traceability (post-outcome/deck, separado):
  → spawn traceability agent → pit/<pit_id>/traceability/report.md
```

Gates David explícitos (documentados en el SKILL §PIT-DEV):
1. `ok, arranca` (literal) para el spawn;
2. aprobación pre-judge si security flaggeó alguna lane;
3. winner (el ranking del judge NO decide);
4. cualquier acción externa (Drive/Telegram).

## 6. Primer caso de uso (ejemplo canónico)

Torneo **"API/MCP para manejar umbral-agent-stack desde IDEs (Cursor/VS Code)"**
— David lo pedirá como primer PIT-DEV real. Spec ejecutable de ejemplo:
[`examples/pit/pit_spec.dev-mcp-ide.yaml`](../../examples/pit/pit_spec.dev-mcp-ide.yaml).

`deliverable_spec` concreto: *"Servidor MCP (stdio + HTTP) que exponga las
tasks del Worker de umbral-agent-stack a IDEs (Cursor/VS Code): listar tasks
disponibles, despachar una task con payload validado, consultar estado/resultado,
y health del Worker. Instalable con `pip install -e .` dentro del deliverable,
con tests propios ejecutables offline (mock del Worker), README con setup para
ambos IDEs y sin secretos hardcodeados (el token se lee de env)."*

## 7. Cierre y entrega post-torneo (orden canónico)

**Paso final obligatorio antes de declarar el torneo "terminado"** — lo hace
cumplir [`pit_deliver_telegram_pack.py`](../../scripts/pit/pit_deliver_telegram_pack.py)
(fail-closed) y está espejado en el SKILL §Post-torneo:

1. **Outcome report** escrito (`pit/<pit_id>/outcome/pit_outcome_report.yaml`)
   + deck borrador (`pit_build_outcome_deck.py`, no exige winner cerrado).
2. **Trazabilidad PASS**: `pit_dev_run.py --phase traceability` corrido y
   veredicto `TRACE_COMPLETE` en `pit/<pit_id>/traceability/report.md`. Con
   `TRACE_GAPS` NO hay entrega (`traceability_gaps:<lista>`): informe a Rick →
   estrategia → mejora continua.
3. **Gate David sobre el winner**: `david_gate` con la frase literal en el
   outcome. Regla de pending por **prefijo**: vacío, `pending`, `pending review
   de David`, `pending_gate`, … siguen siendo pending (no igualdad exacta).
4. **Drive upload** a `GOOGLE_DRIVE_PIT_FOLDER_ID`: deck ejecutivo **+ zip del
   deliverable winner** (`pit/<pit_id>/deliverables/<pit_id>-<winner>-deliverable.zip`,
   generado desde `lanes/<winner>/deliverable/`; sin deliverable ⇒
   `winner_deliverable_missing`, no hay entrega parcial).
5. **Telegram CIERRE**: rendición ≤15 líneas + links Drive — único mensaje
   espontáneo de fin, según la política de comunicación del SKILL
   (INICIO / BLOQUEO / CIERRE; sin progreso granular).
6. **(fase 2) Notion publish**: subpágina con resumen + links Drive. Hoy es un
   **hook documentado, NO implementado** (`notion_publish_stub` →
   `notion_page_url: null` en `telegram_pack.json`); cuando exista, usará la
   task Worker `notion.create_page` bajo el índice PIT del Control Room y el
   CIERRE sumará el link Notion.

## 8. Referencias

- Spec v3 + validador: `scripts/pit/pit_spec_validate.py` (`PitSpecDev`)
- Workspace curado: `scripts/pit/pit_lane_workspace_init.py` + §4
- Cierre + collect: `scripts/pit/pit_dev_core.py`
- Runner: `scripts/pit/pit_dev_run.py`
- Seguridad egress: `docs/ops/pit-security-egress-monitor.md`
- Jueces: `docs/ops/pit-dev-judge-protocol.md` + `judge-scorecard.schema.json`
- Trazabilidad: `docs/ops/pit-traceability-agent.md` + `scripts/pit/pit_traceability_check.py`
- Mejora continua + eficiencia: `docs/ops/pit-handoff-mejora-continua.md`
- Skill: `openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md` §PIT-DEV
