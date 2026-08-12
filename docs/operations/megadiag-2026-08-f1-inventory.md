# Mega-diagnóstico general 2026-08 — F1 Inventario mecánico (Windows)

> **Status:** ACTA — ejecución de la Fase 1 (F1) del plan `megadiag-plan-2026-08-12.md`
> (`main` @ `5b2cc8a1`, #629). Cubre E1 (workspace/git post-higiene) + E7-probes
> (banca) + E7-bis (umbral-bot-2, bot IN por GO de David).
> **Emitido por:** PKG-MACRO-MEGADIAG-F1 (Claude, 2026-08-12).
> **Rama:** `claude/macro-megadiag-f1-20260812` @ base `main` `5b2cc8a1`.
> **Superficie:** solo Windows (`C:\GitHub`), solo lectura. Cero mutación de runtime,
> cero deletes, cero stash drop, cero merge/checkout de WIP ajeno.
> **PR:** draft docs-only, label `do-not-merge`.
> **Timestamp de las lecturas:** 2026-08-12 ~01:40 a ~02:30 (hora local Windows, UTC-4),
> salvo donde se cita timestamp propio de GitHub Actions.

## Resumen ejecutivo

- **E1**: origin de `umbral-agent-stack` sigue limpio (2 heads exactos, `main` +
  `rick/stage7_5-multiformat`). Pero **el residual de ramas locales en la familia
  `umbral-bot-*` volvió a crecer** desde el cierre de Pack 3 (2026-08-11): `-claude`
  2→9 locales, `-codex` 1→6 locales + 8 archivos dirty nuevos + 2 stashes nuevos,
  `-cursor` 2→3 locales. Nada se tocó; queda como fila de decisión (§ criterio 3).
- **E7**: los tres ítems de banca re-verificados **siguen vigentes tal cual**:
  `WinError 3` reproducible también desde esta máquina, `VM_URL` confirmado con
  **0 lectores en código** (grep exhaustivo hoy), CI de `main` **roja en el commit
  más reciente** (`5b2cc8a1`) — pero con un hallazgo nuevo: son **13 tests rojos en
  dos causas distintas**, no una sola (§ E7.3).
- **E7-bis**: `umbral-bot-2` vivo — `origin/main` @ `8230213f`, apex y beta
  responden HTTP 200. El `gh run list` / `gh workflow list` de ese repo está
  **BLOCKED capa permiso-cliente** (el PAT activo no resuelve el repo vía GraphQL/API
  aunque el remote git es correcto y funciona por protocolo git puro).

`MEGADIAG_F1_INVENTORY_PASS = Y` — las filas sin `[E]` completo quedan explícitas como
`PENDING`/`BLOCKED` con capa nombrada, no como afirmación.

---

## E1 — Workspace y git post-higiene

### E1.1 — `ls C:\GitHub` vs línea base de 47

`[E]` `Get-ChildItem -Path C:\GitHub -Directory` → **39 carpetas** (2026-08-12).

La línea base de `macro-plan-2026-08-11.md` (Pack 1, cierre 2026-08-11) fue
**68 → 47**. 39 < 47 es progreso esperado, no alarma: los packs 2–4 (mismo día,
posteriores al corte de Pack 1) eliminaron clones adicionales documentados —
`umbral-agent-stack-codex-coordinador` (worktree), `notion-governance-temp`,
`notion-governance-antigravity` — que bajan el conteo por debajo de 47 sin que
falte nada del inventario declarado. Reconciliado: **sin fila pendiente**.

Carpetas no-repo presentes y no auditadas en profundidad (fuera de foco explícito
del plan, solo lectura de existencia): `_archive`, `_deliverables`, `_sandbox`,
`.coord-ag-evidence` (evidencia histórica may-jun, sin relación con git). `_wt`
**vacío** (confirmado, ver E1.3).

### E1.2 — Origin heads por repo (criterio de cierre #4)

| Repo | Heads en origin | Estado |
|---|---|---|
| `umbral-agent-stack` | **2**: `main` @ `5b2cc8a1` + `rick/stage7_5-multiformat` @ `a263539` | PASS — exactamente lo declarado, `[E]` `git ls-remote --heads origin` |
| `umbral-bot-2` (comparte las 4 clones `umbral-bot-*`) | **106** | Audit diferido — ya señalado en `macro-plan-2026-08-11.md` ("remotos de otros repos: heads huérfanas, audit diferido"); hoy queda **cuantificado por primera vez** |
| `dynamo-mcp` | **26** | ídem, diferido |
| `visor-ifc` | **21** | ídem, diferido |
| `notion-governance` | **4** | ídem, diferido |
| `umbral-skills-registry` | **4** | ídem, diferido |
| `umbral-agent-forge` | **3** | ídem, diferido |

`[E]` comando por repo: `git -C <clone> ls-remote --heads origin | wc -l`, corrido
2026-08-12. No se borró ningún head remoto.

### E1.3 — Clones canónicos `umbral-agent-stack` (familia UAS Windows)

| Clone | Rama activa | Dirty | Stashes | Locales | Nota |
|---|---|---|---|---|---|
| `umbral-agent-stack` (primary/Cursor) | `main` @ `5b2cc8a1` | 2 untracked (`ledger-macro-hygiene-2026-08-11.jsonl`, `macro-plan-2026-08-11.md` — la hoja viva del programa, esperado) | 8 KEEP | 1 | en sync con origin, sin tocar |
| `umbral-agent-stack-claude` (yo) | era `claude/macro-megadiag-plan-20260812` @ `14d9853` (ya mergeada, #629), limpia | 0 | 2 KEEP (históricos, no tocados) | 3 tras mi propia rama F1 | higiene clásica aplicada: `checkout main` → `reset --hard origin/main` → `checkout -b claude/macro-megadiag-f1-20260812` |
| `umbral-agent-stack-antigravity` | `main` @ `66564a2` (stale, sin fetch reciente) | 0 | 0 | 1 | sin cambios vs Pack 2 |
| `umbral-agent-stack-codex` | `main` @ `66564a2` (stale) | 0 | 0 | 1 | sin cambios vs Pack 2 |
| `umbral-agent-stack-copilot` | `main` @ `66564a2` (stale) | 0 | 4 KEEP | 1 | sin cambios vs Pack 2 |

`[E]` `git status -sb` + `git stash list` + `git branch --list | wc -l` por clone,
2026-08-12. Ningún stash abierto, ningún checkout de WIP ajeno.

### E1.4 — Satélites (`notion-governance`, `dynamo-mcp`, `visor-ifc`, `umbral-skills-registry`)

| Repo | Rama activa | Dirty (archivos) | Stashes | Locales | vs baseline 08-11 |
|---|---|---|---|---|---|
| `notion-governance` | `main` @ `b7b2bb3` | 0 | 1 KEEP | 1 | sin cambios |
| `notion-governance-cursor` (WIP KEEP) | `cursor/b2b-root-move` | **142** | 0 | 2 | sin cambios (142 = 142) |
| `dynamo-mcp` (WIP KEEP) | `main` | **20** | 3 KEEP | 1 | sin cambios (20 = 20) |
| `visor-ifc` (WIP KEEP) | `master` | 3 (ledger + evidence dirs) | 2 KEEP | 1 | consistente (doc 08-11 no daba número exacto) |
| `umbral-skills-registry` | `main` @ `5a209b4`, **limpio** | 0 | 0 | 2 (`main` + `claude/pkg-skill-cap-pkg-receiver-0.4.0-20260806`, rama histórica ya shippeada, no checked out) | **mejoró**: el WIP dirty `pkg-receiver` de 08-11 ya no existe — consistente con shipping posterior (v0.5.0 documentado en paso 2 CERRADO) |

`[E]` `git status --porcelain | wc -l` por repo, 2026-08-12. Ninguno de los WIP
KEEP (`notion-governance-cursor`, `dynamo-mcp`, `visor-ifc`) fue abierto ni tocado,
solo contado.

Worktree residual `copilot-worktrees/umbral-agent-forge/umbralbim-potential-goggles`
(rama `umbralbim-init-umbral-agent-forge` @ `f6cd711`): **70 dirty**, idéntico al
número documentado en 08-11 (`git status --porcelain | wc -l` = 70). Sin cambios,
sin abrir.

### E1.5 — Familia `umbral-bot-*` (producto, bot IN por GO de David)

| Clone | Rama activa | Dirty | Stashes | Locales | Δ vs baseline 08-11 |
|---|---|---|---|---|---|
| `umbral-bot-copilot` | `main` @ `8b4b3fd` [behind 7, stale] | 0 | 24 KEEP | 1 | sin cambios (24 = 24) |
| `umbral-bot-codex` | `main` @ `16dad11` [behind 1] | **8** (`services/azure-api`: 5 modificados + `observability/` nuevo) | **23** (era 21) | **6** (era 1) | **DRIFT nuevo** — ver detalle abajo |
| `umbral-bot-claude` | `claude/pkg-n8n-ledger-deploy-20260812` @ `65e6880`, limpia | 0 | 5 KEEP | **9** (era 2) | **DRIFT nuevo** — ver detalle abajo |
| `umbral-bot-cursor` (WIP KEEP) | `cursor/beta-3-parts-handoffs-2026-06-08` [ahead 3] | **151** (era 146) | 4 KEEP | **3** (era 2) | drift leve |

**Detalle `umbral-bot-codex` (drift más grande):** desde el cierre de Pack 3
(08-11, "1 = main") aparecieron 5 ramas locales nuevas —
`codex/fix-n8n-ledger-concurrency-20260812`, `codex/pkg-foro-n8n-access-integrity-20260811`
(`[gone]`, ya mergeada y borrada en origin), `codex/pkg-langfuse-hobby-20260812`
(activa), `codex/pkg-mkt-legal-sc-review-20260812`, `codex/pkg-n8n-ledger-20260811`
(`[gone]`) — más 8 archivos dirty sin commitear en `services/azure-api/` (incluye
`package-lock.json`, `chatProductOrchestrator.ts`, `chatProductStartup.ts`,
`config.ts`, directorio nuevo `observability/`) y 2 stashes adicionales. Es trabajo
activo post-hygiene, no destruido, solo inventariado.

**Detalle `umbral-bot-claude`:** el WIP `foro` de 08-11
(`claude/pkg-foro-bugs-polish-20260811` @ `6e4138b`) **sigue existiendo como rama
local** (no se perdió), pero ya no es la rama activa — el clone avanzó a trabajo
más reciente (`pkg-n8n-ledger-deploy-20260812`, PR #634/#635 ya ejecutado según su
propio mensaje de commit). Alrededor quedaron 6 ramas más con tracking `[gone]` o
apuntando a `origin/main` (mergeadas, sin limpiar localmente):
`pkg-foro-bugs-polish-20260811`, `pkg-foro-bugs-polish-deploy-20260811`,
`pkg-foro-n8n-access-integrity-deploy-20260811`, `pkg-mkt-d365-lead-connect-20260811`,
`pkg-mkt-d365-mcp-visual-20260811`, `pkg-mkt-d365-sales-provision-20260811`,
`pkg-sentry-sdk-20260811`.

`[E]` `git branch -vv` + `git status --porcelain | wc -l` + `git stash list` por
clone, 2026-08-12. Cero ramas borradas, cero stash tocado.

### E1.6 — Criterio de cierre del paso 1 (macro-plan-2026-08-11.md, re-evaluado hoy)

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Un clon canónico por IDE/runtime y por repo; cero clones hermanos "por comodidad" | **PASS** | 15 clones canónicos revisados (§E1.3–E1.5), ningún hermano no declarado; único worktree extra (`copilot-worktrees/.../umbralbim-potential-goggles`) ya inventariado desde 08-11 |
| 2 | Cero worktrees huérfanos; cada `.tmp-*`/`_wt-*` cerrado o inventariado | **PASS** | `_wt/` vacío (`ls -la` 2026-08-12); sin carpetas `.tmp-*` en el listado de 39; único worktree activo, no huérfano, referenciado por `git worktree list` de `umbral-agent-forge` |
| 3 | Ramas locales: solo `main` + las que un pack activo esté usando; el resto clasificado antes de borrar | **PARCIAL** | drift nuevo en `umbral-bot-claude` (2→9), `umbral-bot-codex` (1→6), `umbral-bot-cursor` (2→3) desde el cierre de Pack 3 — ninguna se borró sin clasificar (cumple la regla dura), pero el criterio de "solo main + activa" ya no se sostiene y pide un nuevo pack de clasificación (fila de decisión) |
| 4 | `origin` de cada repo: `main` + KEEP declarados explícitamente | **PASS** (UAS) / **DIFERIDO conocido** (satélites + bot-2) | §E1.2 — UAS exacto; el resto es el mismo "audit diferido" de 08-11, ahora cuantificado |
| 5 | Dirty y stashes: inventariados uno por uno; nada se destruye sin fila en acta | **PASS** | tablas §E1.3–E1.5, cero stash drop, cero reset destructivo fuera de mi propia rama nueva |
| 6 | Roots del workspace Cursor sin paths inexistentes | **PENDING** | no verificable desde comandos git/filesystem de esta sesión (requiere inspección de configuración del workspace de Cursor); no se adivina |

---

## E7 — Banca y riesgos abiertos (re-probe)

### E7.1 — Path G: `WinError 3` (pcrick)

`[E]` `Test-Path "G:\"` → `True` (la unidad G: **sí** está montada en esta máquina
Windows). `Test-Path "G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas"` → **`False`**.
2026-08-12 01:40.

**Sigue vigente**, y ahora confirmado también desde esta máquina (no solo desde
pcrick vía cron): la carpeta declarada no existe en la unidad G: montada. Pide la
misma decisión binaria de siempre: crear la carpeta o cambiar el path del cron. No
se creó ni se modificó nada.

### E7.2 — `VM_URL` vestigial

`[E]` `grep -rn "VM_URL" C:\GitHub\umbral-agent-stack` (todo el árbol, sin filtro de
extensión) → **17 líneas, en 15 archivos, el 100% dentro de `docs/`** (planes,
audits, runbooks históricos). **Cero coincidencias en código real**
(`dispatcher/service.py`, `.env.example`, `openclaw/env.template`, `scripts/*.py`,
`scripts/*.sh` no contienen la cadena literal `VM_URL`; sí contienen `WORKER_URL_VM`,
que es la variable en uso real).

**Confirma exactamente** la afirmación de `macro-plan-2026-08-11.md`: "0 lectores en
código". Re-probe de agosto, no heredado de mayo. Sigue como banca sin cerrar
(decisión pendiente de David: borrar `VM_URL` del env o alinearla).

### E7.3 — CI roja de `main` (citada en E3, re-verificada aquí)

`[E]` `gh run list --branch main --limit 15` (repo `umbral-agent-stack`, 2026-08-12):
**los 15 últimos runs del workflow `Tests` en `main` están en `failure`**, incluido
el del commit más reciente `5b2cc8a1` (run `31565877150`,
`2026-08-12T05:14:12Z`, 1m52s).

`[E]` `gh run view 31565877150 --log-failed`: **13 failed, 4752 passed, 5 skipped,
2 xfailed** en 71.35s. Desglose por causa (hallazgo nuevo — el plan citaba una sola
causa, hay dos):

1. **Schema Publicaciones 0.2.0 vs fixtures (10/13 tests)** — confirma la causa
   documentada. `test_notion_publicaciones_provisioner.py` y
   `test_notion_publicaciones_schema.py` esperan `'0.1.0'` y reciben `'0.2.0'`;
   `test_notion_readonly_audit.py` (6 tests) falla porque el fixture
   `tests/fixtures/notion/publicaciones_database_valid.json` no tiene 12
   propiedades que el schema 0.2.0 ya declara (`Estado imagen`,
   `imagen_alt_1_url`…`imagen_alt_5_url`, `imagen_cantidad`, `imagen_error`,
   `imagen_generada_at`, `listo_rrss`, `origen_alternativa`, `Selección imagen`) →
   verdict `WARN` en vez de `PASS`.
2. **`test_stage3_promote.py::TestRun` (3/13 tests) — causa NO citada en el plan**:
   `test_dry_run_does_not_mutate`, `test_commit_mutates_exactly_selected`,
   `test_idempotent_commit` fallan con `assert 0 == 1` / `assert 0 == 3` /
   `assert (0 == 0 and 0 == 3)` — la promoción no está seleccionant/promoviendo
   los ítems esperados. Es una causa distinta a la deuda de Publicaciones; no se
   investigó más a fondo (fuera de foco de F1, que es solo lectura/enumeración).

Fila de decisión para F3 (CI y drift, Opus): la CI de `main` no es roja por una
sola deuda conocida, son **dos** — el fixture de Publicaciones y una regresión en
`stage3_promote` que no estaba en la banca original.

### E7.4 — Transcripts ~16 GB

Fuera de alcance de F1 (superficie VPS, corresponde a F2 en paralelo). No se tocó.

---

## E7-bis — `umbral-bot-2` (bot IN, GO de David, acotado)

### E7-bis.1 — `origin/main` SHA

`[E]` `git ls-remote origin refs/heads/main` desde `umbral-bot-claude` →
`8230213faad97b45e1d3ab53a0dad491947d804a`. 2026-08-12.

### E7-bis.2 — `gh run list` / CI status

**BLOCKED capa permiso-cliente.** `[E]`:

- `git remote -v` en las 4 clones `umbral-bot-*` → `https://github.com/Umbral-Bot/umbral-bot-2.git`
  (remote correcto, confirmado por protocolo git puro — `ls-remote` de E7-bis.1
  funcionó sobre este mismo remote).
- `gh repo view --repo Umbral-Bot/umbral-bot-2` → `GraphQL: Could not resolve to a
  Repository with the name 'Umbral-Bot/umbral-bot-2'. (repository)` (reproducido 2
  veces).
- `gh auth status` → cuenta activa `UmbralBIM` vía `GITHUB_TOKEN` (PAT de grano
  fino, `github_pat_11BUELCXI...`); existe una segunda cuenta OAuth clásica
  (`gho_...`, scopes `repo`+`workflow`) pero **no está activa**.

La sonda que distingue esta capa de otras (no es "host/versión" ni "preflight del
modelo"): el remote git funciona (protocolo git, sin API), pero la API
REST/GraphQL de GitHub no resuelve el mismo repo con el mismo token — consistente
con un PAT de grano fino cuya lista de repos autorizados no incluye
`Umbral-Bot/umbral-bot-2`. No se intentó `gh auth switch` (cambiaría la cuenta
activa para toda la sesión/todos los repos, fuera del alcance acotado de este
probe de solo lectura) ni se probaron tokens alternativos.

### E7-bis.3 — URLs vivas

`[E]` `curl -s -o /dev/null -w "%{http_code}"`, 2026-08-12 01:4x, sin login:

| URL | HTTP | Latencia |
|---|---|---|
| `https://umbralbim.io/` | **200** | 2.10s |
| `https://beta.umbralbim.io/` | **200** | 1.00s |

Ambas vivas y respondiendo. No se navegó más allá del status/HEAD, no se
interactuó con formularios ni login.

### E7-bis.4 — Prohibiciones respetadas

Cero apertura de WIP `foro`/`cursor` dirty (§E1.5 solo contó archivos, no abrió
ninguno). Cero publish Lovable. Cero mutación Azure.

---

## Gate

```
MEGADIAG_F1_INVENTORY_PASS = Y
```

Las únicas filas sin `[E]` completo son explícitamente `PENDING` (criterio 6 del
paso 1, §E1.6) o `BLOCKED capa permiso-cliente` (E7-bis.2) — ninguna se afirmó sin
evidencia. Cero mutación de runtime. Cero write en `umbral-skills-registry`. Cero
delete, cero stash drop, cero checkout de WIP ajeno. La única escritura de esta
sesión es este documento y la rama que lo contiene.
