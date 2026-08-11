# PKG-UAS-DEPLOY-DISPATCHER-625 — deploy del fix + smoke A/B (2026-08-11)

> **Pack:** PKG-UAS-DEPLOY-DISPATCHER-625 · rama
> `claude/pkg-uas-deploy-dispatcher-625-20260811` · base `3abab2d` (`origin/main`,
> tip = PR #625)
> **GO David:** "go deploy dispatcher" — aplicar #625 en runtime y humear el fix
> del 400. Sin tocar env/VM_URL, sin deploy de worker/gateway.
> **Evidencia:** `~/.coord-ag-evidence/uas-deploy-dispatcher-625-20260811/`
> (journals redactados; tokens jamás impresos; scan limpio).

## Qué pasó (incluye un hotfix necesario)

1. **SYNC:** runtime a `3abab2d` (= #625 con `normalize_envelope_identity`).
   `.claude/CLAUDE.md` local (gitignoreado) intacto. Sin pip install
   (pyproject sin cambios).
2. **Preflight:** dispatcher PID 2323071 (desde 08-07), worker PID 85942 (desde
   07-25, prohibido tocarlo).
3. **Primer restart → crash-loop** (exit 1):
   `ModuleNotFoundError: No module named 'pydantic'`. Causa: la unit del
   dispatcher corre con **python3 de sistema** (solo redis/httpx), y el import
   `from worker.models import TaskType, Team` que #625 metió en
   `dispatcher/task_routing.py` arrastra pydantic al import-graph del dispatcher
   (los tests corrían en el venv, por eso no lo detectaron).
4. **Hotfix aplicado en esta PR** (mínimo, mismo espíritu G4): los sets válidos
   de team/task_type se declaran **localmente** en el dispatcher (sin pydantic),
   con la SoT documentada (enums de `worker/models`) y un **test anti-drift**
   (`test_normalize_sets_match_worker_enums`, corre en venv e importa ambos
   lados) que garantiza que no divergen. Import verificado con python3 de
   sistema. 15/15 tests de routing verdes.
5. **Segundo restart → `active (running)`**, PID nuevo **2922287**. El arranque
   drenó backlog encolado durante la ventana de crash (~90s): tasks `research`
   quedaron `blocked: no_configured_provider` — estado pre-existente del model
   router para LLM tasks, no causado por este deploy.
6. Worker NO restarteado: health `ok:true, version 0.4.0` post-deploy.

## Smokes

| Smoke | Vía | Envelope | Resultado | Veredicto |
|---|---|---|---|---|
| A | POST directo al worker | team=ops, type=cron, windows.fs.list | **HTTP 400** "Invalid request body: 2 validation errors" | ✅ contrato intacto |
| B | Cola Redis → dispatcher (vía de rick-ops) | mismo envelope inválido | **status=done**, journal: `Envelope normalizado … team 'ops' -> 'system'; task_type 'cron' -> 'general'`, worker respondió `ok:false "Solo disponible en Windows"` (ruteo VPS: team system no requiere VM) | ✅ fix vivo, sin 400 |

Repro sintético inmediato (no se esperó el cron de 23:59 UTC). Comando de Smoke B
documentado en evidencia: enqueue por `dispatcher.queue.TaskQueue` sobre
`umbral:tasks:pending` + poll de `umbral:task:{id}`.

## Hallazgo colateral (afina el de #625)

El journal del dispatcher healtcheckea la VM en `http://100.109.16.40:8088/health`
(IP de tailnet) → **HTTP 200 constante**: **pcrick SÍ está viva vía tailscale para
el dispatcher** (`WORKER_URL_VM` propio del servicio). El `VM_URL=127.0.0.1:8088`
del env — que apunta al worker VPS local — es un problema solo para quien use esa
variable (probes/plugins), no para el ruteo del dispatcher. Sin cambios de env en
este pack; la decisión de alinear `VM_URL` sigue en manos de David/Cursor.

## Verify final

- Panel: `residual=0`, `validation.ok=true` (read-only, sin mutar Notion).
- Servicios: dispatcher active PID 2922287; worker/gateway/mission-control sin
  tocar.

## Gate

**`UAS_DEPLOY_DISPATCHER_625_PASS = Y`** — HEAD contiene #625 (+hotfix en PR),
dispatcher active con PID nuevo, Smoke A = 400 directo, Smoke B = done sin 400
con warning de normalize, worker health ok, panel residual=0.

Nota honesta: el gate queda Y con el hotfix de esta PR aplicado al runtime (el
tree de runtime es la rama del pack, práctica estándar de estos packs). Al
mergear, main == runtime.

## TU TURNO (≤2)

1. Cursor mergea la PR (acta + hotfix pydantic-free con test anti-drift).
2. Nada más — Smoke B pasó; el próximo cron de rick-ops (23:59 UTC) debería
   completar sin ⚠️ en OpenClaw.
