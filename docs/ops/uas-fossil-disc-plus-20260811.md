# PKG-UAS-FOSSIL-DISC-PLUS — drop desconectadas + papelera + diag windows.fs.list (2026-08-11)

> **Pack:** PKG-UAS-FOSSIL-DISC-PLUS · rama `claude/pkg-uas-fossil-disc-plus-20260811` ·
> base `3a1e290` (`origin/main`, tip = PR #624)
> **GO David (2026-08-11):** higiene con autonomía, matar fósiles desconectados, no
> tocar valor editorial, verificar papelera por API, diagnosticar 400 de
> `windows.fs.list`, corregir docs del clon Notion muerto.
> **Evidencia:** `~/.coord-ag-evidence/uas-fossil-disc-plus-20260811/` (scan de
> secretos limpio; tokens jamás impresos).

## FASE A — Panel vs validador: **Y**

`residual=0`, `validation.ok=true`, nav = {Dashboard Rick, Alertas del Supervisor},
Bitácora viva bajo Dashboard Rick. El bloque "Bases operativas y paneles" que David
ve son **5 child_databases** (Proyectos técnicos, Tareas, Bandeja de revisión,
Bandeja Puente, Transcripciones Granola) + las 2 nav pages — ninguno cuenta como
residual; es el panel generado, no suciedad. (`a1-panel.json`)

## FASE B — Papelera de las 3: **Y**

Por API: SIM Daily / Métricas / Shortlist → las tres `archived=true, in_trash=true`;
ninguna volvió a Control Room. (`b1-trash.json`)
**Nota UI para David:** el listado de Papelera sin filtro muestra lo reciente de
toda la jerarquía; hay que **buscar por título** en el buscador de Papelera para
verlas (p. ej. "SIM Daily").

## FASE C — DROP desconectadas: **Y** (116/116, delta explicado)

Lista viva regenerada (no se reusó ciegamente el CSV de #624): criterio = sin
merge-base con origin/main, con guardas duras (main, rama del pack, `rick/stage7_5-*`,
worktree poller y su rama, tracking origin vivo). Resultado: **116 candidatas,
116 borradas, 0 fallos**. Delta vs 117 de #624: `reconciliation/align-runtime`
quedó fuera por trackear `origin/main` (regla C1 "tracking origin vivo") — KEEP.
Inventario completo pre-drop (nombre, SHA, clase, subject y files del tip) en
`f3-disconnected-drops.txt`. Sin `push --delete`, sin `gc --prune`, reflog intacto.

## FASE D — Stashes: **PARTIAL honesto**

Reevaluación completa 14/14 (reverse-apply vs origin/main + blobs untracked):
**14 WIP_REAL, 0 EMPTY, 0 SUBSUMED** → cero drops, KEEP con detalle en
`d-stashes.txt`.

## FASE E — Conectadas re-diff: **Y**

Re-diff hoy de las 39 ramas restantes (`e-connected-rediff.csv`):
- **1 NEW_SQUASH_SUBSUMED** borrada con inventario (`e-drops.txt`): la rama del pack
  #624 (diff vacío vs main, PR mergeada).
- **Falso positivo corregido:** `reconciliation/align-runtime` aparecía "subsumida"
  porque el three-dot no computa sin merge-base → reclasificada
  `DISCONNECTED_TRACKING_KEPT`, NO borrada.
- **28 UNIQUE_KEEP + 9 PROTECTED_KEEP** (familia stage7_5 completa, stage9bc,
  worktree poller) — cero drops de protegidas. Ranking con recomendación futura
  (DROP/CHERRY/KEEP) en el CSV.

## FASE F — Docs clon Notion muerto: **Y**

No existe ningún clone notion-governance en el host (find/grep home).
Patcheados los docs vivos: `.claude/skills/notion-governance-runtime/SKILL.md`
(trackeado, va en esta PR) y `.claude/CLAUDE.md` (gitignoreado por diseño —
`.gitignore:76` — así que el fix quedó aplicado en vivo en el VPS, no viaja por
PR). Ambos dicen ahora "no hay clone local en VPS; SoT es el repo GitHub
`Umbral-Bot/notion-governance`" y citan R5 del runbook
`cross-thread-vps-concurrency.md` (que ya era correcto y prohíbe usar
`-git`/`-local`). ADRs y actas históricas intactos. No se clonó nada.

## FASE G — 400 de windows.fs.list: **PARTIAL** (causa raíz probada + fix acotado)

**Cadena reconstruida (evidencia, no inferencia):**
1. `rick-ops` (cron 23:59 UTC, modelo gpt-5.4-mini) llamó la tool
   `umbral_windows_fs_list` con `path=G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas`
   y metadata libre `workerTeam="ops"`, `workerTaskType="cron"` (sesión jsonl).
2. Gateway encola (`ops_log`: task_queued team=ops type=cron) → dispatcher POST a
   `http://127.0.0.1:8088/run` → **400 en 72ms** (task_failed upstream).
3. **Causa raíz:** `TaskEnvelope` valida `team` y `task_type` contra enums cerrados
   (`Team`: marketing/advisory/improvement/lab/system/rick-orchestrator;
   `TaskType`: coding/…/triage). `"ops"` y `"cron"` no existen → pydantic revienta
   en `from_run_payload` → 400 "Invalid request body".
4. **Repro determinista** (`repro1.json`/`repro2.json`): mismo envelope con
   team=ops+type=cron → HTTP 400 con los 2 validation errors exactos; con
   team=system+type=general → HTTP 200 y el handler responde benigno
   (`ok:false "Solo disponible en Windows"` — el path por policy estaba permitido:
   `G:\Mi unidad\Rick-David` está en `config/tool_policy.yaml`).
5. La vía directa (`tool_run`, team system por default) siempre completó — por eso
   el fallo era exclusivo del camino cron/encolado. Patrón recurrente (301
   menciones de windows.fs.list en ops_log; fallos con "ops" y "rick-ops").

**No era:** policy sandbox, path traversal, VM offline, ni red.

**Fix aplicado en esta PR (G4: código de este repo + tests, sin reiniciar nada):**
`dispatcher/task_routing.py::normalize_envelope_identity` — al consumir la cola,
team/task_type fuera del enum se coercionan a `system`/`general` con warning
logueado (el contrato estricto del worker queda intacto — su 400 ante basura sigue
siendo el test `test_envelope_invalid_team`). Tests nuevos con el payload real de
producción: **4 nuevos + 47 routing/worker + 102 dispatcher, todos verdes**.
El fix queda latente hasta que se deployee el dispatcher (fuera de este pack).

**Hallazgo colateral importante (corrige a #624):** `VM_URL` en el env apunta a
`http://127.0.0.1:8088`, que es el **propio worker VPS** (uvicorn local, verificado
por `ss` + pid). El "VM pcrick viva /health 200" de #624 en realidad midió al
worker local — la reachability real de pcrick es **desconocida desde esta
evidencia**. No se tocó el env (área protegida). Decisión David/Cursor: apuntar
`VM_URL` al túnel/host real de pcrick o documentar que la VM está fuera de
servicio. Con el fix de G, `windows.fs.list` encolada pasará de 400 a completar
con `ok:false "Solo disponible en Windows"` mientras el ruteo a VM no exista —
honesto y visible, sin romper el cron.

## FASE H — Verify final

- Panel: `residual=0`, `ok=true` (`h1-panel-final.json`).
- Git: **40 ramas** (38 + main + rama del pack), 14 stashes, **origin=2 heads**,
  worktrees=2 (canónico + poller KEEP). (`h2-git-final.txt`)

## Gates

- **`UAS_PANEL_STILL_CLEAN = Y`**
- **`UAS_TRASH3_PASS = Y`**
- **`UAS_DISC117_DROP_PASS = Y`** (116 vivas de la clase, delta 1 explicado)
- **`UAS_FOSSIL_DISC_PLUS_PASS = PARTIAL`** — A+B+C=Y; D=PARTIAL (14 WIP_REAL
  KEEP), E=Y, F=Y, G=PARTIAL (diagnóstico completo + fix código/tests en PR, sin
  deploy; VM real pendiente de decisión).

## TU TURNO (≤3)

1. Cursor mergea la PR (docs + fix dispatcher con tests; deploy del dispatcher
   cuando corresponda).
2. David busca en el buscador de Papelera: "SIM Daily", "Pipeline Editorial",
   "Shortlist editorial" (el listado sin filtro no las muestra arriba).
3. David/Cursor deciden `VM_URL` real de pcrick (hoy apunta al worker VPS local);
   no se tocó env ni SSH en este pack.
