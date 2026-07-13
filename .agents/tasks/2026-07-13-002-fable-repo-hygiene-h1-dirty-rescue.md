---
id: "2026-07-13-002"
title: "Higiene repos H1 — rescate de dirty state y stashes (BORRADOR — NO ejecutar sin GO de David)"
status: pending
assigned_to: copilot
created_by: fable
priority: high
sprint: b0004
created_at: 2026-07-13T17:35:00Z
updated_at: 2026-07-13T18:30:00Z
---

> **BORRADOR.** Esta tarea NO se ejecuta hasta GO explícito de David sobre la
> matriz H0–H6 del plan
> `docs/audits/repo-hygiene-plan-windows-vps__2026-07-13__b0004__src-fable.md`.
> H1 es **solo captura** (copiar/parchear a zona de rescate): no hace
> `git clean`, `reset`, `stash drop` ni borra nada.

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

- [ ] 4 unidades capturadas con MANIFEST.md (archivo, hash, veredicto, evidencia).
- [ ] Los 6 únicos-valiosos capturados: human-review-contract 174L,
      export-vscode-config.ps1, quota-policy diff, audit azure-foundry,
      stash RAG-pgvector, stash megaprompt-blog (+ stash cola-torneos).
- [ ] `.env` del coordinador preservado localmente SIN pasar por git ni por la zona versionada.
- [ ] Cero comandos destructivos ejecutados (`clean`/`reset`/`stash drop`/`rm`).
- [ ] Los `RESCATAR_PR` quedan en rama(s) de rescate con PR abierto (docs only).
- [ ] Sin secretos en la zona de rescate.
- [ ] Log actualizado + fila H1 del plan marcada done.

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
