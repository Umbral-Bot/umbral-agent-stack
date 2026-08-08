# P1 — Residuales VPS: archive/uas, stashes, calendar E2E (2026-08-08)

> **Pack:** PKG-UAS-P1-VPS-RESIDUALS · rama `claude/pkg-uas-p1-vps-residuals-20260808` ·
> base `8065e00` (`origin/main`, tip = PR #613)
> **Ejecutado por:** Claude, Remote-SSH sobre `/home/rick/umbral-agent-stack` (host `srv1431451`,
> usuario `rick`) — confirmado antes de tocar nada.
> **GO citado (verbatim, evidencia en `~/.coord-ag-evidence/uas-p1-vps-residuals-20260808/AUTHZ.txt`):**
> 1. *"go a todo, dame megaprompt"* (David, 2026-08-08) — autoriza los 3 residuales de la
>    lista del orquestador.
> 2. Gate nombrado **G-WH-VPS-2** — citado explícitamente para autorizar el borrado
>    definitivo de `~/archive/uas` (creado bajo G-WH-VPS-1, 2026-07-03; regla: borrado
>    solo tras ≥30 días **y** cita explícita de este gate — ya pasaron los 30 días y esta
>    conversación lo cita).

**Fuera de alcance en este pack (no tocado):** transcripts huérfanos / `sessions cleanup
--enforce` (cerrado DEFER en PR #613), `trustedProxies`, dirs `pit-*`, zombi
`openai:umbral-rick`, `openclaw.json`, `doctor --fix`, cache npm, crontab.

---

## Fase A — G-WH-VPS-2: delete definitivo de `~/archive/uas`

**Before:** 964M — 3 clones standalone + 6 worktrees registrados en el canónico + 1
directorio no documentado (`cand-001-alt1`, un asset PNG de 4.4M).

### Re-verificación independiente (no se confió en `WHY.md` de hace 5 semanas)

`WHY.md` (creado 2026-07-03) afirmaba que las 6 ramas de los worktrees tenían *"tip ==
origin"* y que `umbral-agent-stack-cursor` tenía *"todas sus ramas con upstream
sincronizado"*. Un `git fetch origin --prune` fresco reveló que **ninguna de las 8
ramas de clones/worktrees existe ya en origin** — cientos de ramas fueron podadas del
remoto en el proceso de higiene P1.2 (2026-08-06/07) desde que se escribió `WHY.md`.
Esto activó el criterio A7 del pack (verificar UNIQUE antes de borrar) para las 8:

| Path (worktree/clone) | Rama | HEAD | Veredicto | Evidencia |
|---|---|---|---|---|
| `umbral-agent-stack-cursor` | `rick/supervisor-structured-telemetry` | `b376a4d8` | **SAFE** — PR #243 ya mergeado a main (contenido preservado bajo otro SHA vía squash) | `uas-p1-2-merged-kill-2026-08-06.md` |
| `umbral-agent-stack-copilot-cli` | `rick/copilot-cli-capability-design` | `fa704e9d` | **SAFE** — PR #269 mergeado | idem |
| `umbral-agent-stack-activation-playbook` | `rick/copilot-cli-f6-step6c4f-activation-playbook` | `bd857328` | **SAFE** — PR #271 mergeado | idem |
| `umbral-agent-stack-postmerge-evidence` | `rick/copilot-cli-postmerge-evidence-6c4d` | `7e96a879` | **SAFE** — PR #270 mergeado | idem |
| `umbral-agent-stack-f7-policy-gate` | `rick/copilot-cli-f7-policy-gate-rehearsal` | `b96a7eb4` | **SAFE** — PR #274 mergeado | idem |
| `umbral-agent-stack-f7-code-gate` | `rick/copilot-cli-f7-code-gate-rehearsal` | `0d6ad83c` | **SAFE** — `KILL_SAFE` confirmado por análisis P1.2 previo (994/1564 archivos idénticos a main, 1 de ruido) | `uas-p1-2-orphan58-analyze-capx-20260806.md` |
| `umbral-agent-stack-editorial` | `rick/editorial-linkedin-writer-flow` | `410266a0` | **SAFE** — era `CHERRY_CANDIDATE` (21 paths únicos, marcado "vivas, sin tocar" el 2026-08-07); **verificado que su contenido SÍ fue rescatado** a `docs/archive/editorial-linkedin-writer-flow-2026-05/` en `origin/main` (SKILL.md, CALIBRATION.md, LINKEDIN_WRITING_RULES.md, agent overrides, 15 docs cand-003/cand-004) | comparación directa de paths vs `origin/main` |
| `umbral-agent-stack.backup-pre-cand001-20260629-174640` | `rick-delivery/editorial-contract-paths` | `18cdc488` | **SAFE** — commit trivial (3 líneas clarificando una ruta en un doc); el texto que clarificaba fue removido/reescrito en main, moot | `git show` directo |

**Hallazgo fuera de `WHY.md`:** `cand-001-alt1/` no es un repo git — es un directorio con
un único PNG (4.4M, `magnific_crear-una-variante-de-la-...png`, asset de generación
Magnific/CAND-001) que `WHY.md` nunca documentó. **Rescatado** a
`evidencia/rescue-archive/cand-001-alt1/` antes del borrado.

**29 archivos untracked** en el clone backup (172K: 1 doc de auditoría sin match en main +
4 yaml de PIT idénticos byte a byte a los de main + 24 heartbeat logs + 1 script + 1 PR
draft) — copiados íntegros a `evidencia/rescue-archive/backup-pre-cand001-untracked/`
como seguro barato (costo casi nulo, evita cualquier juicio de valor individual innecesario).

format-patch/show de las 8 tips de rama guardado en `evidencia/rescue-archive/branch-tip-*.txt`
como respaldo adicional.

### Ejecución

1. `git worktree remove --force` × 6 (los 6 worktrees registrados) — confirmado que ya no
   aparecen en `git worktree list`.
2. `lsof`/`fuser`/`ps` sobre `~/archive/uas` — sin procesos activos.
3. `mv ~/archive/uas ~/archive/uas.PENDING-DELETE-20260808` (seguridad extra) → verificado
   rescate íntegro en evidencia → `rm -rf` definitivo.

**After:** `~/archive/uas` no existe. `df -h /`: 42% → 41% (58G libres).

**Ningún subpath disparó un STOP real** — todo se verificó seguro *antes* de borrar, no
después. Ningún dato se perdió.

---

## Fase B — Stashes del canónico

25 stashes → **18** (7 `DROP_SAFE` ejecutados, cada uno re-verificado con `git stash show -p`
inmediatamente antes de dropear, en orden de índice mayor→menor para evitar problemas de
renumeración).

| Índice original | Contenido | Razón del drop |
|---|---|---|
| 23 | (vacío) | diff nulo confirmado |
| 20 | `.agents/tasks/f8b-diagnose-egress-and-model-power-2026-05-07.md` (status/verdict) | idéntico byte a byte a `origin/main` hoy |
| 18 | `config/tool_policy.yaml` (`copilot_cli.egress.activated`) | la sección completa fue removida de `main` — moot |
| 16 | `scripts/vps/check-notion-poller.sh` (lógica DAEMON_PID/MODULE_PID) | idéntico byte a byte a `origin/main` hoy |
| 14 | (vacío) | diff nulo confirmado |
| 13 | (vacío) | diff nulo confirmado |
| 5 | (vacío) | diff nulo confirmado |

**18 KEEP** — en su mayoría WIP real y sustancial nunca capturado en `main` (evolución de
`stage7_5_copy_writer.py`, pipeline de discovery, `html_to_notion_blocks.py`, suites de
tests, actualizaciones de task-docs con contenido narrativo único). Ver
`stashes-before.txt` / `stashes-after.txt` en evidencia para la lista completa.

### Hallazgo colateral: bug de producción activo (fuera de scope, flaggeado aparte)

El stash `auto-stash-before-p11-pull` (hoy `stash@{0}`) parecía trivial (`0
insertions/deletions`, 2 archivos) y casi se clasifica `DROP_SAFE` por error — pero resultó
ser un **cambio de modo** (`chmod +x`) sobre `scripts/vps/dashboard-rick-cron.sh` y
`openclaw-panel-cron.sh`. Verificación cruzada:

- `git ls-tree origin/main` confirma que ambos archivos siguen en modo `100644`
  (no ejecutable) **hoy**.
- Ambas líneas del crontab invocan los scripts **sin prefijo `bash`**.
- `/tmp/dashboard_rick_cron.log` y `/tmp/openclaw_panel_cron.log` muestran
  **`Permission denied` en cada corrida reciente**, sin excepción.

Es decir: este bug (diagnosticado con causa raíz completa en otro stash, `2026-05-04`)
sigue activo en producción **hoy**, más de 4 meses después. El dashboard/panel solo se
refresca por el camino reactivo (upserts de Notion), nunca por el cron de respaldo — un
fallo silencioso. **No se corrigió en este pack** (fuera del allowlist A/B/C) — se
flaggeó como tarea aparte (`spawn_task`, `task_f4bdfe21`) y el stash se mantiene **KEEP**
(no se dropeó, ya que contiene el fix correcto — chmod +x — listo para aplicar).

> **Update 2026-08-08 — FIXED este pack:** PKG-UAS-VPS-CRON-CHMOD aplicó el fix real (no
> el stash a ciegas — se reprodujo limpio en repo): `git update-index --chmod=+x` en
> ambos scripts (índice `100644`→`100755`) + `chmod +x` en el filesystem del VPS
> (desbloquea el cron de inmediato, sin esperar merge). `bash -n` OK en ambos; no se
> ejecutó el cron completo (ninguno tiene `--dry-run` y ambos escriben a Notion). El
> stash `KEEP` original (`auto-stash-before-p11-pull`) sigue sin dropear hasta confirmar
> el fix corriendo sano en la próxima ventana de cron. PR sin merge.

---

## Fase C — Calendar: borrar eventos E2E probe

Búsqueda `search_events("E2E-P3-02")` sobre el calendar primary de David → exactamente 2
eventos, ambos coincidiendo verbatim con los títulos citados por el pack.

| Título | Start | REPORT verificado en repo antes de borrar | Borrado |
|---|---|---|---|
| `E2E-P3-02-20260804-1103` | 2026-08-04 13:00 -04 | `docs/ops/user-e2e-p3-02-freshness-2026-08-04.md` | **Y** |
| `E2E-P3-02-RERUN-20260806-1330` | 2026-08-06 13:30 -04 | `docs/ops/user-e2e-p3-02-rerun-20260806.md` | **Y** |

El primer evento tenía en su descripción *"no borrar hasta REPORT"* — se confirmó que el
REPORT correspondiente ya está committeado en el repo antes de proceder. Post-delete:
re-búsqueda del mismo query → 0 resultados. Ningún otro evento (reuniones reales,
Calendly, Umbral BIM) fue tocado.

---

## Gate

**`UAS_P1_VPS_RESIDUALS_PASS = Y`**

- Fase A: delete OK (964M liberados, 0 rescates perdidos — todo verificado antes de
  borrar, 2 hallazgos fuera de `WHY.md` rescatados igual).
- Fase B: inventario + drops seguros OK (7/25, cada uno re-verificado antes de ejecutar).
- Fase C: delete OK (2/2, sin falsos positivos).
- Gateway sin tocar durante todo el pack (`active`, `NRestarts=1`, sin cambio desde el
  pack anterior).
- Sin secretos ni tokens en evidencia ni en este documento (grep verificado, log de
  calendar sanitizado a título/id-corto/start/deleted).

**Pendiente de David:**
1. Revisar y priorizar el fix del cron roto (`task_f4bdfe21`) — bug real, activo desde
   2026-03-24, fix trivial (`chmod +x` × 2 archivos).
2. Mergear este PR cuando corresponda — sin self-merge.
