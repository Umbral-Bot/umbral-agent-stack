---
id: "2026-07-13-002"
title: "Higiene repos H1 — rescate de dirty state y stashes"
status: done
assigned_to: fable
created_by: fable
priority: high
sprint: b0004
created_at: 2026-07-13T17:35:00Z
updated_at: 2026-07-13T20:15:00Z
---

> **GO David 2026-07-13.** Ejecutado. Alcance restringido a 3 ubicaciones
> (`umbral-agent-stack-copilot`, `umbral-agent-stack-codex-coordinador`,
> Cursor `reo`/`wah`/`weo`) — no destructivo: cero `clean`/`reset`/`stash
> drop`/`rm`, cero `worktree remove --force` sobre worktrees vivos, cero
> `branch -D` remoto.

## Objetivo

Capturar en una zona de rescate todo el material dirty y los stashes únicos de
los checkouts Windows antes de cualquier fase destructiva (H3+), con veredicto
por archivo. Los veredictos por archivo ya fueron **pre-verificados** el
2026-07-13 (análisis + verificación adversarial independiente; detalle en
`docs/audits/data/repo-hygiene-inventory-2026-07-13.yaml`) — esta tarea ejecuta
la captura y re-confirma byte-igualdades al momento de correr.

Zona de rescate propuesta: `C:\GitHub\_archive\uas\rescue-2026-07-13\<unidad>\`
con un `MANIFEST.md` por unidad (archivo, hash, veredicto, evidencia).

## Unidades de rescate (veredictos verificados 2026-07-13)

### U1 — `umbral-agent-stack-codex-coordinador` — 3 únicos + verificación

**RESCATAR (únicos verificados):**
- `??` docs/ops/editorial-publicaciones-human-review-contract.md — **COPIA
  ÚNICA de 174 líneas** (main solo tiene una versión de 38; 129 líneas no
  vacías existen SOLO aquí; blob 768015bd sin rastro en historia de ningún
  repo). Máxima prioridad de la unidad.
- `??` scripts/export-vscode-config.ps1 — único (251 líneas, sin rastro en
  historia de ambos repos).
- `.env` **ignorado** en la raíz del worktree (3136 bytes, 2026-04-23) — tiene
  4 claves `AZURE_OPENAI_*` que no están en el .env del codex ni del canónico.
  **Preservar localmente (mover/copiar a ubicación segura fuera del worktree);
  NUNCA commitear ni copiar a la zona de rescate versionada.**

**VERIFICAR-Y-CERRAR (redundantes verificados — solo re-confirmar hash):**
- Los 8 `M` (editorial-agent-flow, gold-set, 2 ROLE.md, CALIBRATION, 3 SKILL.md):
  diff byte-idéntico al stash compartido `S2-RESCUE-01` (sha1 patch 55b72ab9) y
  contenido ya en main (CAL-008/009/010 «rescate coordinador 2026-05-30»).
- `??` editorial-linkedin-quality-smoke-tests.md (subset estricto de main),
  `??` task 2026-07-12-001 (blob idéntico al tracked en main).

**DESCARTE FIRMADO PENDIENTE:** 4 png de sesión + `.playwright-mcp/`.

### U2 — `umbral-agent-stack-copilot` — 3 valiosos

- `M` docs/15-model-quota-policy.md (+7/-1) — **VALIOSO**: bloque «Estado
  operativo vigente 2026-07-04 (post-MP1 OPENCLAW_AZURE_ONLY=YES)» ausente de
  main. Candidato a PR docs.
- `??` docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md
  (121 líneas) — **NO existe en main**. Candidato directo a PR docs.
- `stash@{0}` (2026-06-12) — **VALIOSO**: tabla «Cola de torneos (David — no
  perder)» en docs/ops/pit-process-index.md, ausente de main.
- `??` graphify-out/ (63 MB artefactos generados): **excluido** (megaprompt
  graphify) — no capturar, no borrar en H1.
- Nota H2 relacionada (no parte de H1 pero mismo repo): rama
  `backup/local-untracked-2026-04-29` @ 684b2758 es **single point of failure**
  (22 archivos +1216 líneas en ningún otro lugar) — su push de respaldo es la
  primera acción de H2.

### U3 — worktrees Cursor `reo`/`wah`/`weo` — captura mínima de registro

Verificado 2026-07-13: dirty byte-idéntico entre los 3 (hash diff 7894d8f5) y
**100% superseded por main** (blobs idénticos, CRLF, o reescrituras
posteriores; update.zip: 18/18 entradas byte-idénticas módulo CRLF a blobs de
origin/main; aplicar el diff de quota-policy sería regresión).

- Guardar UNA copia del patch + lista de untracked en el MANIFEST (registro
  histórico) — nada de esto es candidato a PR.
- Prerequisito de la remoción H4. Si `git worktree remove --force` falla con
  «directory in use»: `git fsmonitor--daemon stop` dentro de cada worktree.

### U4 — Stashes Windows (15 en 4 repos)

| Repo | Stashes | Veredicto verificado |
|---|---|---|
| canónico | 5 | **stash@{0} ÚNICO-VALIOSO**: backlog P2 «Migración RAG: Azure Cognitive Search → pgvector» (+23 líneas docs/11-roadmap-next-steps.md, ahorro ~USD 73/mes) → commitear a rama docs. stash@{1..4}: superseded/stale — descarte firmado pendiente |
| claude | 2 | **stash@{0} ÚNICO-VALIOSO**: docs/ops/claude-code-azure-editorial-blog-megaprompt.md (163 líneas, no existe en ningún lado) → capturar. stash@{1}: settings locales — descartable |
| codex (compartidos con coordinador) | 4 | blobs que no existen en ninguna ref (verificado `--find-object`) — capturar `stash show -p` de los 4 y triage individual |
| copilot | 4 | stash@{0} valioso (ver U2); stash@{1..3} triage |

- Por cada stash: `git stash show -p 'stash@{N}' > rescate.patch` (+ para los
  que tengan tercer padre de untracked: `git show 'stash@{N}^3'`).
  **No hacer `stash drop` en H1.**

## Procedimiento (por unidad)

```powershell
# 1. Crear zona: C:\GitHub\_archive\uas\rescue-2026-07-13\<unidad>\
# 2. git -C <checkout> diff > <unidad>-tracked.patch  (diff completo de los M)
# 3. Copy-Item de cada untracked capturable (respetando exclusiones y la regla .env)
# 4. Por archivo: git hash-object vs origin/main → veredicto en MANIFEST.md
# 5. Stashes: git stash show -p + git show stash@{N}^3 (untracked) → .patch numerado
# 6. Commit del MANIFEST consolidado + los RESCATAR_PR en rama fable/hygiene-h1-rescue-20260713
```

## Criterios de aceptación

> Actualizados tras el GO de David (2026-07-13, alcance restringido a 3 de
> las 4 unidades del borrador — ver Log 20:15). El patrón "MANIFEST.md /
> zona de rescate en `_archive\uas`" del borrador original se reemplazó por
> ramas `rescue/*` con commits documentados (equivalente funcional, más
> simple: el commit message ES el manifest).

- [x] 3 unidades en alcance evaluadas con evidencia por ítem (ver tabla
      2026-07-13 20:15). Unidad "stashes canónico/claude" (U4 del borrador)
      queda **fuera de esta corrida** — no estaba en el GO.
- [x] Únicos-valiosos EN ALCANCE capturados: human-review-contract 174L,
      export-vscode-config.ps1, quota-policy diff, audit azure-foundry.
      Stash cola-torneos → `pending_human` (no capitalizado, evidencia
      guardada, stash intacto). Stashes RAG-pgvector (canónico) y
      megaprompt-blog (claude) quedan fuera de alcance de este GO.
- [x] `.env` del coordinador: documentado (path + count=4), **no tocado**
      (ni copiado ni commiteado).
- [x] Cero comandos destructivos ejecutados.
- [x] Los rescates quedan en ramas `rescue/copilot-dirty-2026-07-13` y
      `rescue/coordinador-dirty-2026-07-13`, pusheadas a origin (sin PR —
      no solicitado; abrir PR es acción trivial pendiente si David lo pide).
- [x] Sin secretos en las ramas de rescate (solo nombres de archivo/doc content).
- [x] Log actualizado + tarea marcada `done`.

## Log

### [fable] 2026-07-13 17:35
Borrador inicial a partir del inventario read-only.

### [fable] 2026-07-13 18:30
Actualizado con veredictos del análisis multi-agente + verificación adversarial:
(1) REFUTACIÓN aceptada en U1 — human-review-contract.md es copia única de 174
líneas (el análisis inicial invirtió el diff) y existe un `.env` ignorado con
claves únicas que un `worktree remove --force` destruiría; (2) los 8 M del
coordinador quedaron verificados redundantes (== stash S2-RESCUE-01 y main);
(3) U3 degradada a captura mínima (todo superseded verificado byte-nivel);
(4) U4 ampliada con 3 stashes únicos-valiosos identificados (RAG-pgvector,
megaprompt-blog, cola-torneos). NO ejecutar sin GO de David.

### [fable] 2026-07-13 20:15 — EJECUTADO (GO David, alcance restringido)

GO explícito recibido con alcance acotado a 3 ubicaciones (no las 4 unidades
del borrador — se excluyeron canónico y claude, quedan pendientes de un H1
futuro). Re-verifiqué todo en vivo (fetch de `origin/main` en copilot y
coordinador; re-diff/re-hash de cada ítem) antes de clasificar, porque el
estado pudo cambiar desde el análisis de la tarde.

#### Clasificación (evidencia resumida; detalle completo en los comandos de
la sesión)

**`umbral-agent-stack-copilot`**

| Ítem | Veredicto | Evidencia |
|---|---|---|
| `M docs/15-model-quota-policy.md` | **KEEP_RESCUE** | Base `cf4e195` = blob actual de `origin/main` (no está stale); el diff agrega el bloque "Estado operativo vigente 2026-07-04" con link al audit — ausente de main. |
| `?? docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` | **KEEP_RESCUE** | `git cat-file -e origin/main:<path>` → no existe. 121 líneas. Enlazado desde el ítem anterior — se rescatan juntos. |
| `?? graphify-out/` | **excluido** | Fuera de evaluación por instrucción previa (megaprompt graphify) — no tocado. |
| `stash@{0}` (2026-06-26, "pre-p10-sec63-route-a") | **PENDING_HUMAN** | +11 líneas en `docs/ops/pit-process-index.md`: tabla "Cola de torneos (David — no perder)" con 2 torneos (`pit-salud-mental-pilot`, `pit-sharepoint-acc-umbral-bim`) y reglas de torneos #2+. Confirmado ausente de main (`grep "cola de torneos"` = 0). Es exactamente el caso "torneos" que la instrucción marcó de-dudar → **no capitalizado, no descartado**; patch completo guardado en el scratchpad de la sesión para referencia. El stash en sí **no se tocó** (no hay riesgo de pérdida). |
| `stash@{1}` (2026-04-11, IDE config) | **DISCARD_SAFE** | `.claude/settings.local.json` (config local, tracked mas no vale la pena versionar cross-máquina) + 2 diffs de 1 línea en `.claude/commands/{pr,routing}.md` (referencias a `/linear` y a un doc ya consolidado) — trivial, sin pérdida real. |
| `stash@{2}` (2026-03-04, `.env.example` +7 Azure) | **ALREADY_IN_MAIN** | El bloque Azure de marzo (5 vars, `gpt-5.2-chat`/eastus) es un subconjunto obsoleto: `origin/main` ya tiene un bloque Azure muchísimo más completo (endpoint, key, deployment `gpt-5.3-codex`, AI Search, editorial blog, etc.). |
| `stash@{3}` (2026-03-04, `AGENT_INSTRUCTIONS.md`) | **ALREADY_IN_MAIN** | Task-brief histórico (Ronda 2 Copilot): pide `scripts/vps/worker-supervisor.sh` + `DEFAULT_LLM_MODEL`. El deliverable real (`scripts/vps/supervisor.sh`) ya existe y está activo en producción (crontab, board.md); el enrutamiento de modelos fue reemplazado por el sistema multi-modelo actual. Es un documento de instrucciones, no un artefacto perdido. |

**`umbral-agent-stack-codex-coordinador`**

| Ítem | Veredicto | Evidencia |
|---|---|---|
| 8 archivos `M` (editorial-agent-flow, gold-set, 2×ROLE.md, CALIBRATION, 3×SKILL.md) | **ALREADY_IN_MAIN** | Hash del diff completo = `58b7be19...`, **idéntico** al hash del `stash@{0}` compartido `S2-RESCUE-01`. Contenido reflejado en main como `CAL-008/009/010` con la etiqueta literal "rescate coordinador 2026-05-30, renumerado ex CAL-00x". |
| `?? docs/ops/editorial-publicaciones-human-review-contract.md` | **KEEP_RESCUE** | Working copy 174 líneas vs 38 en `origin/main` (main es un subconjunto). **Rescatado.** |
| `?? docs/ops/editorial-linkedin-quality-smoke-tests.md` | **ALREADY_IN_MAIN** | Working copy 131 líneas vs 136 en main — main es superset estricto. |
| `?? .agents/tasks/2026-07-12-001-copilot-openclaw-oauth-only-urgent.md` | **ALREADY_IN_MAIN** | `hash-object` idéntico (`26e220a4...`) al blob tracked en main. |
| `?? scripts/export-vscode-config.ps1` | **KEEP_RESCUE** | 251 líneas; `git log --all` vacío para esa ruta en ambos repos — sin rastro previo. **Rescatado.** |
| `?? 4×*.png` + `.playwright-mcp/` | **DISCARD_SAFE** | Screenshots y caché de sesión (p10f-ifc-after-final.png, pkg5a-*.png) — artefactos de sesión sin valor de código/doc. |
| `stash@{0}` "S2-RESCUE-01" | **ALREADY_IN_MAIN** | Mismo contenido que los 8 M (ver arriba); duplicado. |
| `stash@{1,2,3}` (compartidos con `umbral-agent-stack-codex`) | **FUERA DE ALCANCE** | Pertenecen a ramas `codex/*` (structured-error-classification, umb-131-curar-tareas-granola, 095-actualizar-docs-board), no al trabajo editorial propio del coordinador. El GO listó "codex-coordinador", no "codex" — no se accionaron. Documentados para una H1 futura sobre el clone `-codex`: `stash@{1}` docs/68-editorial-phase-1-manual.md (+80L, abr-23), `stash@{2}` diagnóstico env (mar-22), `stash@{3}` scripts/vps/supervisor.sh (+64/-10, mar-05). |
| `.env` (ignorado, raíz del worktree) | **documentado, preservado en su lugar** | Existe. **4 claves** `AZURE_*` (solo nombres, sin valores impresos ni copiados): `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_IMAGE_DEPLOYMENT`. No coincide con el `.env` del clone `-codex` ni del canónico. **No se tocó, no se copió, no se commiteó** — sigue solo en `C:\GitHub\umbral-agent-stack-codex-coordinador\.env`. |

**Cursor `reo` / `wah` / `weo`**

| Ítem | Veredicto | Evidencia |
|---|---|---|
| Los 3 worktrees (dirty completo) | **ALREADY_IN_MAIN / DISCARD_SAFE** (1 solo grupo — trío idéntico) | Re-verificado hoy: hash del `git diff` = `7894d8f5...` idéntico en los 3. `scripts/get_db_parent.py` y `scripts/setup_notion_tasks_db.py`: blob de la working copy = blob de `origin/main` (ya mergeados). `docs/15-model-quota-policy.md`: el diff de febrero reintroduce una tabla vieja (nomenclatura "Gemini Pro" simple) que aplicarla sería *regresión* frente al contenido actual de julio. `runbook-full-stack-vps.md`: solo ruido CRLF. `.env.example`: re-encoding superado. `update.zip`/`vps_pub_key.txt`/`worker_err.txt`/`worker_out.txt`: artefactos de sesión de febrero, contenidos ya verificados presentes en main. Sin material único — nada capitalizado. |

#### Acciones ejecutadas

1. **`rescue/copilot-dirty-2026-07-13`** — creada desde `origin/main` (0ab0d3d5) vía worktree temporal (`C:\GitHub\.rescue-copilot`, corta para evitar `MAX_PATH` de Windows), commit `003bafc2` con los 2 archivos KEEP_RESCUE de copilot, **pusheada a origin**. Worktree temporal removido tras el push (mío, de esta sesión — no era un worktree vivo del inventario).
2. **`rescue/coordinador-dirty-2026-07-13`** — mismo patrón (`C:\GitHub\.rescue-coord`), commit `16219f25` con los 2 archivos KEEP_RESCUE del coordinador, **pusheada a origin**. Worktree temporal removido tras el push.
3. `umbral-agent-stack-copilot` y `umbral-agent-stack-codex-coordinador` **no fueron modificados** — los archivos se copiaron desde ahí hacia los worktrees de rescate, nunca al revés. `git status` de ambos clones sigue mostrando el mismo dirty que antes de esta corrida (por diseño: H1 no limpia, solo respalda).
4. Cero `worktree remove --force` sobre worktrees vivos, cero `branch -D` remoto, cero `stash drop`, cero `clean`/`reset`. `.env` del coordinador no tocado.

#### Incidente menor (no bloqueante)

Windows `MAX_PATH` (260 caracteres) rompió el primer intento de worktree temporal bajo la ruta profunda del scratchpad de sesión (`...\6b2ac2d7-.../scratchpad\rescue-staging\...`). Las 2 ramas `rescue/*` ya habían sido creadas antes del fallo (checkout parcial); `git worktree remove --force` sobre las rutas rotas confirmó que nunca llegaron a registrarse (`worktree list` ya estaba limpio). Reintenté con rutas cortas (`C:\GitHub\.rescue-*`) — sin pérdida ni necesidad de tocar ningún worktree vivo.

#### Conteo final

- **Rescatados (KEEP_RESCUE, capitalizados en `rescue/*`, pusheados):** 4 archivos en 2 commits — `docs/15-model-quota-policy.md` + `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` (copilot); `docs/ops/editorial-publicaciones-human-review-contract.md` + `scripts/export-vscode-config.ps1` (coordinador).
- **Descartados (ALREADY_IN_MAIN o DISCARD_SAFE, verificados, sin acción):** 9 ítems/grupos — copilot stash@{1,2,3} (3); coordinador 8M-group + quality-smoke-tests + task-file + stash@{0} + 4png-group (5); trío Cursor (1 grupo).
- **Pendientes de humano:** 1 — `stash@{0}` de copilot (tabla "Cola de torneos"), patch guardado, stash intacto, sin capitalizar.
- **Fuera de alcance (documentado, no accionado):** 3 stashes compartidos codex/coordinador que pertenecen a ramas `codex/*` — candidatos a un H1 futuro sobre `umbral-agent-stack-codex`.
- **`.env` con secretos:** 1 ubicación documentada (path + count=4, sin valores) — sin tocar.

**Veredicto:** `REPO_HYGIENE_H1_OK | rescued=4 | discarded=9 | pending_human=1`
