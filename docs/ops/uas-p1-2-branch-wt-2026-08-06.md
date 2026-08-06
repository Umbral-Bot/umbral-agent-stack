# P1.2 — KILL de ramas mergeadas + limpieza worktrees Codex (2026-08-06)

> **Pack:** PKG-UAS-P1-2-BRANCH-WT · rama `claude/pkg-uas-p1-2-branch-wt-20260806` · base `b0f1653b`
> **Fuente del GO:** `docs/ops/uas-north-canonical-2026-08-06.md` §5 P1.2 + §7.2, sobre el inventario
> `docs/ops/uas-north-inventory-2026-08-06.md` (tablas C/D).
> **Estado:** Fase A ejecutada → **STOP, no se ejecutó Fase B** (divergencia de conteo, ver §1).
> Fase C ejecutada y cerrada. Fase D (huérfanas) inventariada, cero deletes.

---

## 0. Resumen ejecutivo

| Fase | Estado | Resultado |
|---|---|---|
| A — Re-verificación MERGED_KILL | **STOP** (no ejecutada Fase B) | 191 candidatas vs ~87 del inventario → diverge 120%, gate de seguridad del pack |
| B — KILL remoto MERGED | **NO EJECUTADA** | Bloqueada por el STOP de A. Cero ramas borradas en origin |
| C — Worktrees Codex | **DONE** | 34 worktrees/directorios removidos (13 vía `git worktree remove` + 21 dirs huérfanos sin `.git`); 9 quedan vivos (todos KEEP justificado) |
| D — Huérfanas | **DONE (solo inventario)** | 90 ramas huérfanas citadas con `git diff --stat` o ahead/behind; cero deletes |

**Nada se borró en `origin` en este pack.** Todo lo borrado (worktrees) era estado local en disco, ya sea registrado y limpio en git, ya sea cruft sin `.git` (caché pytest). Ninguna rama remota fue tocada.

---

## 1. Fase A — Re-verificación MERGED_KILL: STOP

### 1.1 Método

```
git fetch origin --prune
git ls-remote --heads origin                                    # 283 ramas (excl. main)
gh pr list --repo Umbral-Bot/umbral-agent-stack --state merged --limit 600 --json headRefName,number,mergedAt
gh pr list --repo Umbral-Bot/umbral-agent-stack --state open   --limit 600 --json headRefName,number
```

Clasificación por cruce de `headRefName` contra el set de PRs mergeados (499 PRs mergeados totales, `--limit 600` sin truncar).

### 1.2 Resultado

| Clase | # |
|---|---|
| MERGED_KILL (headRefName en PR mergeado) | **191** |
| OPEN_PR (headRefName en PR open) | 2 (`#541`, `#521` — igual que el inventario) |
| ORPHAN (sin PR) | 90 |
| **Total ramas remotas (excl. main)** | **283** |

### 1.3 Por qué diverge (verificado, no es un bug de método)

El inventario original (`uas-north-inventory-2026-08-06.md` §3) calculó ~87 (17+70) **sólo sobre 119 ramas en 4 prefijos**: `claude/*`, `copilot/*`+`copilot-vps/*`, `codex/*`, `feat/editorial-*`+`docs/editorial-*`. Este pack pide explícitamente "Listar ramas origin (excluir main/HEAD)" **sin restricción de prefijo**.

Desglose real (283 ramas totales):

| Prefijo | Total | MERGED | OPEN | ORPHAN |
|---|---|---|---|---|
| `claude/*` | 25 | 23 | 1 | 1 |
| `copilot/*` + `copilot-vps/*` | 43 | 25 | 1 | 17 |
| `codex/*` | 46 | 34 | 0 | 12 |
| `feat/editorial-*` + `docs/editorial-*` | 11 | 11 | 0 | 0 |
| **Resto (`rick/*`, `feat/tournament-*`, `cursor/*`, `antigravity/*`, `docs/*`, `fix/*`, etc. — fuera del inventario original)** | **158** | **98** | **0** | **60** |

Los 4 prefijos originales dan MERGED=93 (≈87, la diferencia es simple drift temporal: 6 PRs más se mergearon entre `0c666350` y `b0f1653b`). El salto real viene de los **158 branches fuera de esos 4 prefijos**, de las cuales **98 tienen PR mergeado** — nunca contadas en el inventario porque nunca estuvieron en su alcance.

Verificado con 2 muestras al azar del bucket "fuera de alcance" (no falsos positivos):

- `docs/openclaw-vps-operator-agent` → PR **#417 MERGED** 2026-05-14, rama sigue viva en origin.
- `rick/supervisor-routing-contract` → PR **#230 MERGED** 2026-04-20, rama sigue viva en origin.

### 1.4 Decisión

Por regla del pack (§Fase A punto 5): *"Si el conteo MERGED_KILL diverge >15% del inventario (~87), STOP y reportá antes de borrar."* 191 vs 87 = +120%. **STOP.** Fase B no se ejecutó — cero `git push origin --delete` en este pack.

El criterio de clasificación (headRefName ∈ PRs mergeados) es correcto y está verificado; lo que falta es que David confirme el **alcance**: ¿el KILL autorizado en el GO era "todo origin" o "solo los 4 prefijos del inventario"? Ver TU TURNO al final.

---

## 2. Fase B — KILL remoto MERGED: NO EJECUTADA

Bloqueada por el STOP de §1. `UAS_P12_MERGED_KILL_PASS=N` (no por fallo, sino por gate de seguridad — ver §1.4). Cero ramas borradas en `origin`.

---

## 3. Fase C — Worktrees Codex: DONE

### 3.1 Worktree del clone canónico

```
git -C C:\GitHub\umbral-agent-stack worktree list
→ C:/GitHub/umbral-agent-stack  b0f1653b [claude/pkg-uas-p1-2-branch-wt-20260806]
```

Una sola entrada — el principal. No se tocó.

### 3.2 Inventario inicial

`C:\Users\david\.codex\worktrees\` tenía **43 directorios** (no 26 — el inventario de 2026-08-06 quedó desactualizado en 17 unidades por acumulación en los últimos días). De esos 43:

- **22 registrados en git** (vía `git -C C:\GitHub\umbral-agent-stack-codex worktree list`, el "commondir" real de estas worktrees — no es `umbral-agent-stack` sino su hermano `-codex`).
- **21 sin `.git`**: carpetas huérfanas donde el registro de worktree ya había sido podado por git, pero el directorio en disco sobrevivió. Contenido verificado: solo caché (`pytest-cache-files-*`, `.codex-tmp`, `.pytest_tmp`) — cero archivos fuente.

De los 22 registrados:

| Rama/HEAD | Dirty | Veredicto |
|---|---|---|
| 13× detached `3b10d7e` (mismo SHA, sin nombre) | limpio (0 archivos) | **REMOVE seguro** — duplicado detached |
| `69c6` detached `3b10d7e` | dirty (1: `?? docs/audits/granola-automation-lineage-2026-04-02.md`, no existe en main) | **KEEP** |
| `fbf4` detached `3b10d7e` | dirty (1: `?? .codex-tmp/`, caché) | **KEEP** (regla literal: dirty ⇒ no borrar en este pack) |
| `79ed/f8a-run6-task` → `codex/f8c-github-meta-egress-resolver-2026-05-07` | limpio | **KEEP** — rama nombrada, no detached/prunable/Temp (fuera del criterio de remoción de este pack) |
| `79ed/umbral-agent-stack-codex-coordinador` (detached `e6128bc`) | dirty (11: mismos archivos WIP que el clone hermano `-codex-coordinador`, ROLE.md de rick-communication-director/rick-qa) | **KEEP** — espejo del WIP ya protegido como P1.3 |
| `copilot-cli-vision-roadmap-doc` → `codex/f8a-real-exec-path-2026-05-05` | limpio | **KEEP** — rama nombrada |
| `f8a-diagnostic-mode` → `codex/f8a-diagnostic-mode-2026-05-06` | limpio | **KEEP** — rama nombrada |
| `f8a-docker-stdin-fix` → `codex/f8a-docker-stdin-fix-2026-05-06` | limpio | **KEEP** — rama nombrada |
| `f8a-drop-no-banner` → `codex/f8a-drop-no-banner-2026-05-06` | limpio | **KEEP** — rama nombrada |
| `f8a-prompt-quoting-fix` → **`main`** | dirty (1: `A .agents/tasks/2026-05-08-001-copilot-vps-wave1_5-integration.md`, staged) | **KEEP** — dirty; nota: el archivo staged ya existe en `origin/main` (mergeado vía "Wave 1.5 integration", `d835122f`/`8d118a8b`), es contenido redundante pero se respeta la regla dirty⇒no-borrar |
| `f8g-pin-gpt55-high` → `codex/f8g-pin-gpt55-high-effort` | limpio | **KEEP** — rama nombrada |

`C:\Users\david\AppData\Local\Temp\pr269-worktree` (fuera de `.codex/worktrees` pero en el alcance explícito del paso 10): detached `b5641f9`. **NO estaba limpio** como asumía el inventario original — `git status` reporta **1075 archivos** (mayormente `D`, archivos de `.agents/*` borrados del working tree respecto del commit registrado). **KEEP** por la regla dirty⇒no-borrar; se invierte el veredicto REMOVE-CANDIDATE del inventario porque ese dato no estaba verificado ahí.

### 3.3 Ejecutado

```
# 13 worktrees detached duplicados (limpios, mismo SHA 3b10d7e)
git -C C:/GitHub/umbral-agent-stack-codex worktree remove <path> --force
  → 0e23, 2988, 3a20, 420f, 50a6, 5a58, 6c34, 7a68, 7e3e, 7e6f, ac97, cf41, d5e4

git -C C:/GitHub/umbral-agent-stack-codex worktree prune -v
  → limpió además el registro fantasma de C:/GitHub/umbral-agent-stack-codex-pit-v2-contract
    (el directorio en disco ya no existía; era bookkeeping git puro, cero contenido tocado)

# 13 directorios padre vacíos tras el remove
rmdir <path>  → 0e23, 2988, 3a20, 420f, 50a6, 5a58, 6c34, 7a68, 7e3e, 7e6f, ac97, cf41, d5e4

# 21 directorios huérfanos sin .git (solo caché pytest)
rm -rf <path>  → 05aa, 0716, 1066, 2792, 49c4, 4cac, 4e75, 589a, 5c34, 6446, 7085, 728d,
                 7cdc, 857b, 8da8, 92d5, 9dab, a069, aa10, bf02, d89a
```

**Resultado:** `C:\Users\david\.codex\worktrees\` pasó de **43 → 9** directorios. Los 9 restantes están justificados en la tabla §3.2 (6 por rama nombrada, 3 por dirty con contenido real). `Temp\pr269-worktree` se conserva por dirty (1075 archivos).

**Nota de alcance:** no se tocó ningún clone hermano de nivel superior (`C:\GitHub\umbral-agent-stack-claude`, `-antigravity`, `-codex`, `-codex-pit-v2-contract` como directorio, `-copilot`, `-codex-coordinador`) — el pack autoriza literalmente `C:\Users\david\.codex\worktrees\**` + `Temp\pr269-worktree`, no los clones de `C:\GitHub\`. Esos 6 quedan tal como los dejó el inventario, pendientes de un pack propio (ítems #9, #10, #12 de la cola de cierre del inventario).

`UAS_P12_CODEX_WT_PASS=Y` — 34 removidos, 9 conservados (todos justificados), cero pérdida de contenido (verificado: los únicos dos con contenido no-caché — `69c6` y `f8a-prompt-quoting-fix` — están en KEEP).

---

## 4. Fase D — Huérfanas: inventario, cero deletes

### 4.1 Alcance

90 ramas sin PR (mergeado ni open) en las 283 de origin. El "tope práctico" del pack era ~30 (el inventario original); **90 excede ese tope en 3×** por la misma razón que en §1.3 — alcance ampliado a todo origin en vez de los 4 prefijos originales.

Se citó `git diff --stat` (o `ahead/behind` cuando no hay merge-base) para **las 90**, no solo las ~30 conocidas, dado que el comando es local y barato una vez que `git fetch origin '+refs/heads/*:refs/remotes/origin/*'` trajo todas las refs.

### 4.2 Hallazgo crítico: 58 de 90 no tienen merge-base con `origin/main`

```
git diff --shortstat origin/main...origin/<rama>
→ fatal: origin/main...origin/<rama>: no merge base
```

Confirmado con `git merge-base origin/main origin/<rama>` → exit 1 (sin ancestro común) en los 58 casos. Esto **no es un error del comando** — es que el historial de `origin/main` ya no comparte ningún commit con esas 58 ramas. Coincide con el registro de memoria `UAS_MAIN_CLONE_SANITIZED` (2026-07-23): la sanitización del clone canónico parece haber implicado una reescritura de historia en algún punto, y estas 58 ramas quedaron "huérfanas de historia", no solo huérfanas de PR.

Para estas 58, `git rev-list --left-right --count` sí funciona (no depende de un merge-base único) y da ahead/behind, pero esos números ya no representan "commits propios sobre main" — representan el tamaño total de cada historia disjunta. **Cualquier rescate de estas 58 requiere cherry-pick de commits/archivos puntuales, no merge ni fast-forward.**

Las 14 ramas del "Grupo 1" del inventario original (`ahead` de 3-4 cifras) están **todas** en este bucket de 58 — el inventario ya intuía esto ("ese número no es trabajo propio... se ramificaron de un main viejo") pero no había confirmado la ausencia total de merge-base.

### 4.3 Tabla — 58 sin merge-base (ahead/behind, sin diffstat válido)

| Rama | Último commit | ahead | behind |
|---|---|---|---|
| `antigravity/sync-uncommitted-changes` | 2026-04-29 `9e32a99b` feat: sync uncommitted workspace changes | 940 | 1555 |
| `backup/windows-dirty-2026-04-27` | 2026-03-23 `2b301e1f` agents: delegar lead temporal a Codex (R23) | 575 | 1555 |
| `claude/audit-creator-tracking-TX9zV` | 2026-03-07 `454f446d` feat(audit): creator tracking en auditoría | 410 | 1555 |
| `codex/cand-001-notion-draft-flow` | 2026-04-22 `3a2765fa` docs: CAND-001 Notion page body update | 886 | 1555 |
| `codex/editorial-pr-stack-coordination-qa` | 2026-04-22 `d800c288` docs: audit editorial PR stack coordination | 847 | 1555 |
| `codex/editorial-stack-final-readiness-qa` | 2026-04-22 `24bf07e0` docs: final readiness QA for editorial stack | 847 | 1555 |
| `codex/granola-raw-intake-batch` | 2026-04-13 `70ba2ac5` feat(granola): fail gap audit on recent missing meetings | 701 | 1555 |
| `codex/notion-governance-v1-contract` | 2026-03-31 `2221f5af` Add Notion governance V1 contract | 690 | 1555 |
| `codex/notion-publicaciones-setup-runbook` | 2026-04-22 `7edbc6c2` docs: add Publicaciones Notion setup runbook | 871 | 1555 |
| `codex/notion-v2-drift-cleanup` | 2026-04-07 `38ca2ed9` Tighten remaining Granola V2 legacy residue | 693 | 1555 |
| `codex/rick-qa-cand-001-validation` | 2026-04-22 `c121cfd9` docs: record Rick QA validation for CAND-001 | 885 | 1555 |
| `codex/session-capitalizable-promotion-v1` | 2026-03-31 `5e6e0478` fix(granola): harden poller and promotion edge cases | 693 | 1555 |
| `codex/wip-granola-v2-snapshot-2026-04-30` | 2026-04-30 `e72ebab4` snapshot(rescue-2026-04-27): preserve one-shot Drive/Codex audit & redaction scripts | 579 | 1555 |
| `copilot/analyze-agent-stack-infrastructure` | 2026-04-10 `3d8809c9` feat: add copilot-instructions.md | 692 | 1555 |
| `copilot/create-umbral-agent-stack-repo` | 2026-02-26 `8bf3b023` Initial plan | 2 | 1555 |
| `copilot/feat-mission-control-o13-1` | 2026-05-05 `e1d2bc38` task(o15): delegate telegram bot bind to copilot-vps | 959 | 1555 |
| `copilot/research-agent-stack-infrastructure` | 2026-04-10 `3d8809c9` feat: add copilot-instructions.md | 692 | 1555 |
| `cursor/2026-03-22-001-codex-env-diagnostico` | 2026-03-22 `34fe635e` refactor(agents): Codex define canónicos, Cursor sincroniza local | 555 | 1555 |
| `cursor/bit-cora-contenido-enriquecido-4099` | 2026-03-05 `e9be3fad` docs(R16): board R14-R16, Bitácora cierre, CI workflow | 328 | 1555 |
| `cursor/board-estado-actual-e573` | 2026-03-05 `bfc0fd7d` docs(R15-070): actualizar board con estado real R8–R15 | 325 | 1555 |
| `cursor/cierre-integraci-n-main-4905` | 2026-03-05 `afd2ce0f` chore(R16-077): cierre integración main — merge PRs #69-#73 | 340 | 1555 |
| `cursor/development-environment-setup-ac64` | 2026-03-04 `13ab7d58` docs: update AGENTS.md test count to 130+ | 123 | 1555 |
| `cursor/fusi-n-prs-69-70-71-23e1` | 2026-03-05 `b038d8b6` chore: merge PRs #69, #70, #71 — pytest 847 passed | 330 | 1555 |
| `cursor/integraci-n-de-prs-en-main-3876` | 2026-03-05 `3ce23aff` ci: use pyproject.toml test extras | 336 | 1555 |
| `cursor/integraci-n-de-prs-y-pruebas-1084` | 2026-03-05 `e74b254f` chore(R16): merge PRs #69, #70, #71, #73 via PR #75 | 339 | 1555 |
| `cursor/missing-test-coverage-04dd` | 2026-04-08 `02132531` test: cover granola v1 guardrail and poller fallback | 692 | 1555 |
| `cursor/missing-test-coverage-2a09` | 2026-04-04 `309ea835` test(granola): cover guardrail comment-failure paths | 691 | 1555 |
| `cursor/missing-test-coverage-4c51` | 2026-04-14 `2cea0fc2` test(rag): cover retriever search filtering and modes | 703 | 1555 |
| `cursor/missing-test-coverage-8db5` | 2026-04-12 `dac00332` test: cover granola policy fallback and poller target dedupe | 693 | 1555 |
| `cursor/missing-test-coverage-961c` | 2026-04-07 `de091488` test: cover granola guardrail fallback and poller dedupe | 692 | 1555 |
| `cursor/missing-test-coverage-c75b` | 2026-04-09 `9ac5d445` test: cover granola v1 guardrails and poller session fallback | 692 | 1555 |
| `cursor/power-bi-libraries-formats-5c1b` | 2026-03-05 `6a64515c` docs: R16 — research librerías y formatos Power BI | 326 | 1555 |
| `cursor/r16-cierre-y-documentaci-n-bc44` | 2026-03-05 `057eb26c` docs(R16-078): board estado final R16, bitácora Notion | 329 | 1555 |
| `cursor/regression-test-coverage-0d73` | 2026-04-10 `b2965d2a` test: cover granola guardrail edge cases and poller fallback | 693 | 1555 |
| `cursor/regression-test-coverage-136d` | 2026-04-06 `1c3bbd93` test: cover session-capitalizable guardrail fallbacks | 691 | 1555 |
| `cursor/regression-test-coverage-1863` | 2026-04-15 `5cb80ac1` test(github): cover tournament edge-case branch orchestration | 736 | 1555 |
| `cursor/regression-test-coverage-91c7` | 2026-04-11 `ea7b6a41` test: cover granola guardrail and poller dedupe edges | 693 | 1555 |
| `cursor/regression-test-coverage-b904` | 2026-04-13 `de318aff` test(security): cover OData escaping, enqueue daily limit | 703 | 1555 |
| `cursor/regression-test-coverage-d34a` | 2026-04-05 `5ba092ba` test: cover session capitalizable guardrails | 691 | 1555 |
| `cursor/regression-test-coverage-e479` | 2026-04-16 `f3e36b1f` test: cover task-specific sanitizer limits | 736 | 1555 |
| `cursor/tests-document-generator-dependencias-8af0` | 2026-03-05 `d805d62f` fix: add document_generator deps to pyproject.toml | 321 | 1555 |
| `feat/bitacora-populate` | 2026-03-05 `fe5d3393` feat: notion.append_bitacora task + populate_bitacora script | 290 | 1555 |
| `feat/browser-automation-vm-research` | 2026-03-05 `8eebe4de` chore: mark PR criterion as done (PR #81) | 331 | 1555 |
| `feat/ci-readme-verificacion` | 2026-03-05 `c9e66047` ci: add pytest workflow + update README | 327 | 1555 |
| `feat/copilot-azure-foundry-audio` | 2026-03-04 `99c2ce1c` feat: Azure AI Foundry integration + audio generation tool | 194 | 1555 |
| `feat/r16-080-limpieza-prs-docs` | 2026-03-05 `46dc7582` chore(R16-080): close 11 obsolete PRs, update README/board | 225 | 1555 |
| `feat/ux1-noise-reduction` | 2026-04-14 `52acdfcf` feat(ux2a): retire allow_legacy_raw_to_canonical gate | 704 | 1555 |
| `rescue/copilot-vps/rick-vps-orphans-2026-07` | 2026-06-07 `4b8cfbb4` docs: add CAND-PROD001 decision brief | 436 | 1555 |
| `rescue/copilot-vps/rick-vps-stash-windows-fs-b64-2026-07` | 2026-03-07 `e0c5d9e6` WIP on rick/windows-fs-b64: base64 binary writes to VM | 105 | 1555 |
| `rick/copilot-cli-f7-code-gate-rehearsal` | 2026-05-05 `0d6ad83c` feat(copilot-cli): F7 rehearsal 5A open code gate only | 994 | 1555 |
| `rick/editorial-linkedin-writer-flow` | 2026-05-05 `410266a0` docs(editorial): upgrade CAND-004 traceability prototype | 915 | 1555 |
| `rick/fix-copilot-ci` | 2026-04-17 `9acdf1cd` fix(ci): handle optional copilot dependency in tests | 775 | 1555 |
| `rick/t/fcb2f1bc/a` | 2026-04-17 `893f95cc` tournament(fcb2f1bc): contestant A code change | 765 | 1555 |
| `rick/t/fcb2f1bc/b` | 2026-04-17 `ba323b9d` tournament(fcb2f1bc): contestant B code change | 765 | 1555 |
| `rick/t/fcb2f1bc/c` | 2026-04-17 `7abb789a` tournament(fcb2f1bc): contestant C code change | 765 | 1555 |
| `rick/t/fcb2f1bc/final` | 2026-04-17 `e9fb95dc` tournament(fcb2f1bc): contestant A code change | 764 | 1555 |
| `rick/test-github-mvp-smoke` | 2026-04-14 `9d983463` test: GitHub MVP smoke test via handler pipeline | 732 | 1555 |
| `rick/windows-dirty-rescue-2026-04-27` | 2026-04-27 `e77ca7c2` scripts(rescue): preserve vps branch discipline helpers | 577 | 1555 |

`behind=1555` es constante en casi todas — coherente con "todas divergen del mismo punto de reescritura de historia", no con 58 incidentes distintos.

**Propuesta:** ninguna acción en este pack. Si David quiere rescatar algo de aquí, es cherry-pick dirigido por archivo, no un GO masivo — el volumen (58 ramas, historia disjunta) hace que un barrido ciego sea la forma más fácil de perder o de "revivir" contenido ya superado.

### 4.4 Tabla — 32 con merge-base válido (diffstat real, candidatas naturales a rescatar-o-matar)

| Rama | Último commit | ahead/behind | Diff vs main |
|---|---|---|---|
| `codex/cand-prod001-stage2` | 2026-06-06 `a85563b8` | 2/163 | 3 files, +770 |
| `codex/docs-pit-v2-contract` | 2026-06-20 `16e39b40` | 1/136 | 5 files, +893/−2 |
| `coord-ag-2a/build-push-aeco-source-crawler` | 2026-05-10 `cd9f225b` | 1/304 | 1 file, +252 |
| `copilot-vps/052-aeco-kb-build-blocked-pat-scope` | 2026-05-08 `ac1973a5` | 1/346 | 1 file, +34/−2 |
| `copilot-vps/052-aeco-kb-pushed-visibility-manual` | 2026-05-08 `67845e5d` | 1/345 | 1 file, +42/−2 |
| `copilot-vps/recover-post-force-push-2026-05-06` | 2026-05-06 `e53637c1` | 1/505 | 27 files, +4338/−73 |
| `copilot-vps/stage4-013e-execution-2026-05-07` | 2026-05-06 `a36c2d53` | 1/489 | 4 files, +1259 |
| `copilot/burn-q2-o7-o9-delegates` | 2026-05-06 `8ba95c09` | 1/485 | 3 files, +431 |
| `copilot/docs-editorial-master-plan` | 2026-05-08 `beda8917` | 1/312 | 6 files, +405 |
| `copilot/docs-notion-schema-gates` | 2026-05-08 `185cf976` | 2/312 | 13 files, +1692 |
| `copilot/docs-s6-s7-multiplatform-design` | 2026-05-08 `2315271e` | 1/312 | 9 files, +1300 |
| `copilot/feat-o16-2-047-gap-closure` | 2026-05-14 `0aff027f` | 2/293 | 3 files, +514/−2 |
| `copilot/feat-o16-infra-base` | 2026-05-06 `e875b1c4` | 1/494 | 15 files, +1161 |
| `copilot/feat-s0-s1-discovery` | 2026-05-08 `c07ea222` | 3/312 | 11 files, +1998 |
| `copilot/feat-s10-publish-guard` | 2026-05-08 `51b38955` | 3/312 | 23 files, +3433/−32 |
| `copilot/feat-s2-source-verification` | 2026-05-08 `379d4cb1` | 2/312 | 9 files, +1532 |
| `cursor/cand001-magnific-megaprompt` | 2026-06-30 `bba2cf1b` | 1/120 | 1 file, +114 |
| `evidence/openclaw-e2e-cycle-001` | 2026-05-18 `a4cdfaef` | 2/275 | 6 files, +344 |
| `rescue/coordinador-dirty-2026-07-13` | 2026-07-13 `16219f25` | 1/60 | 2 files, +413/−26 |
| `rescue/copilot-dirty-2026-07-13` | 2026-07-13 `003bafc2` | 1/60 | 2 files, +128/−1 |
| `rescue/copilot-vps/editorial-contract-paths-backup-2026-07` | 2026-06-29 `18cdc488` | 1/124 | 1 file, +2/−1 |
| `rescue/copilot-vps/editorial-contract-paths-canonical-2026-07` | 2026-06-29 `5a6b7aab` | 1/108 | 1 file, +3 |
| `rescue/copilot-vps/poller-hardening-2026-07` | 2026-05-18 `b7f8e411` | 19/448 | 5 files, +149/−2 |
| `rick-delivery/notion-poller-healthcheck-hardening` | 2026-05-07 `f9b6c405` | 3/449 | 6 files, +81/−8 |
| `rick/stage7_5-multiformat` | 2026-05-08 `a2635398` | 7/334 | 14 files, +5491/−14 |
| `rick/stage7_5-voice-v2` | 2026-05-08 `9a06ad94` | 4/334 | 14 files, +6268/−33 |
| `rick/stage7_5-voice-v3` | 2026-05-08 `63aa9608` | 4/334 | 11 files, +5032/−32 |
| `tournament/…-375-fa19920/lane-docs-explanatory` | 2026-05-08 `155d4f02` | 1/349 | 1 file, +2/−2 |
| `tournament/…-440-462ef1c1/lane-backup-impl` | 2026-06-02 `77b8ca89` | 1/212 | 16 files, +457 |
| `tournament/…-440-462ef1c1/lane-backup-qa` | 2026-06-02 `815851d2` | 1/212 | 15 files, +453 |
| `tournament/…-445-d5f34a07/lane-sync-delivery` | 2026-06-02 `9741e7ce` | 1/208 | 4 files, +736/−158 |
| `tournament/…-d35-33863db/lane-openclaw-skill` | 2026-06-09 `ca6b86be` | 1/153 | 1 file, +27 |

Notables por tamaño real de contenido único: `copilot-vps/recover-post-force-push-2026-05-06` (+4338, rescate post force-push), `copilot/feat-s10-publish-guard` (+3433, publish-guard 6-gate), `rick/stage7_5-voice-v2`/`v3`/`multiformat` (+5000-6000 cada una, evals reales de voz).

`UAS_P12_ORPHAN_INVENTORY_PASS=Y` — 90/90 citadas (58 vía ahead/behind por falta de merge-base, 32 vía diffstat completo). Cero KILL, cero rescate ejecutado.

---

## 5. Lo que este pack NO hizo

- No borró ninguna rama remota (`origin`). Fase B quedó bloqueada por el gate de divergencia.
- No tocó `main`.
- No tocó los clones hermanos `-copilot`, `-codex-coordinador` (P1.3, dirty con WIP real).
- No tocó los clones hermanos de nivel superior `-claude`, `-antigravity`, `-codex`, ni el directorio `-codex-pit-v2-contract` (fuera del alcance literal de Fase C; su registro fantasma en git sí se limpió como efecto colateral de `worktree prune`, sin tocar contenido).
- No mergeó ni cerró PR #541/#521.
- No escribió en VPS, registry ni Notion.
- No hizo self-merge de este PR.

---

## 6. Higiene del pack

- Probe: `git ls-remote --heads origin "claude/pkg-uas-p1-2-branch-wt*"` → vacío, rama nueva.
- Árbol de partida: limpio (0 archivos), no hizo falta stash.
- `git checkout -B claude/pkg-uas-p1-2-branch-wt-20260806 origin/main` desde `b0f1653b`.

`HYGIENE_PASS = Y` — sin stash, sin conflicto, base confirmada.
