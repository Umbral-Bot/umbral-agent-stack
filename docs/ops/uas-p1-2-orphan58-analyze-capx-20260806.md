# P1.2 — Análisis de las 58 huérfanas sin merge-base + propuesta capitalización (2026-08-06)

> **Pack:** PKG-UAS-P1-2-ORPHAN58-CAPX · rama `claude/pkg-uas-p1-2-orphan58-capx-20260806` · base `30faf421`
> **GO de David:** (1) analizar las 58 huérfanas sin merge-base con `main` citadas en
> [uas-p1-2-branch-wt-2026-08-06.md](uas-p1-2-branch-wt-2026-08-06.md) §4.2–4.3; (2) proponer
> capitalización propose-only. **Cero deletes, cero cherry-pick a main, cero ship --apply en este
> pack.**

---

## 0. Resumen ejecutivo

| Fase | Estado | Resultado |
|---|---|---|
| A — Re-inventario 58 huérfanas | **DONE** | 58/58 re-confirmadas (existencia + `git merge-base` exit 1), 0% divergencia vs el acta origen |
| B — Capitalización propose-only | **DONE** | 4 deltas propuestos a `pkg-receiver-protocol` (0 solapados/duplicados, 1 refuerza, 3 nuevos), 0 aplicados |

| Etiqueta | # | Significado |
|---|---|---|
| **KILL_SAFE** | 49 | Sin valor único vs `main` — absorbido por nombre/contenido, torneo, swarm de test-coverage duplicado, QA/audit de un candidato ya resuelto, o ruido de entorno local |
| **CHERRY_CANDIDATE** | 5 | Contenido único real (scripts, prototipo de skill, hook), candidato a evaluación de cherry-pick puntual |
| **KEEP_FOSSIL** | 4 | Valor incierto o tema fuera del núcleo activo del proyecto — queda en origin |
| **SKIP_OPAQUE** | 0 | No hizo falta — las 58 fueron inspeccionables vía `git ls-tree` sin riesgo |
| **Total** | **58** | |

**Nada se borró ni se cherry-pickeó en este pack.** Es clasificación con evidencia, para que un GO posterior sea selectivo, no un barrido ciego.

---

## 1. Fase A — Re-inventario

### 1.1 Método

```
git fetch origin --prune
# Para cada una de las 58 ramas del acta origen (§4.3):
git rev-parse -q --verify origin/<rama>                              # existencia
git merge-base origin/main origin/<rama>                             # confirma exit 1
git rev-list --left-right --count origin/main...origin/<rama>        # ahead/behind (historias disjuntas)
git ls-tree -r --name-only origin/<rama> | sort > branch_paths
comm -23 branch_paths /tmp/main_paths.txt                            # paths que NO existen en main hoy
```

`comm -23` sobre nombres de archivo (no contenido) es la única comparación posible sin merge-base
— un `git diff origin/main...<rama>` de tres puntos falla (`fatal: no merge base`); un diff de dos
puntos (`git diff origin/main <rama>`) mostraría el repo entero como "diferente" porque las
historias son disjuntas, no es señal útil. La cuenta de paths únicos por nombre es una
aproximación deliberadamente conservadora: si un path ya existe en `main` (mismo nombre), se asume
absorbido o superado salvo evidencia puntual en contrario; si el path no existe en ningún lado de
`main`, es candidato real a mirar.

### 1.2 Resultado de la re-verificación

```
MISSING=0 STILL_NO_MB=58 NOW_HAS_MB=0
```

**58/58 confirmadas** — misma cardinalidad que el acta origen, `git merge-base` sigue fallando en
las 58, ninguna ganó merge-base desde entonces (no hubo rebase/reset que las reconectara), ninguna
desapareció de `origin`. **Divergencia = 0%** — muy por debajo del umbral de 20% del pack. No aplica
el STOP parcial.

### 1.3 Hallazgo metodológico: ruido de entorno local

`comm -23` reveló que `.claude/skills/openclaw-vps-operator/SKILL.md` aparece como "único" en
**15 de las 58 ramas**, sin relación temática entre ellas (torneo, CI, docs, granola, editorial).
No es contenido intencional de esas ramas — es el archivo de skill local que cada committer tenía
en su working tree en el momento del commit (`.claude/skills/` no vive en `main`, vive en el perfil
del usuario). Se descontó como ruido antes de contar "paths únicos" con valor real; ver Fase B
Delta #4 para la capitalización de esta técnica.

---

## 2. Tabla completa — 58 huérfanas

`ahead/behind` = `git rev-list --left-right --count origin/main...origin/<rama>` (no representa
"commits propios": son dos historias disjuntas por la reescritura de `main` de 2026-07-23; ver
[uas-p1-2-branch-wt-2026-08-06.md](uas-p1-2-branch-wt-2026-08-06.md) §4.2). `paths(n)` = cantidad de
paths presentes en la rama y ausentes por nombre en `main` hoy (0 = todo absorbido por nombre).

| # | Rama | Tip | Fecha | ahead/behind | paths(n) | Etiqueta |
|---|---|---|---|---|---|---|
| 1 | `antigravity/sync-uncommitted-changes` | `9e32a99b` | 2026-04-29 | 940/1564 | 9 | **CHERRY_CANDIDATE** |
| 2 | `backup/windows-dirty-2026-04-27` | `2b301e1f` | 2026-03-23 | 575/1564 | 0 | KILL_SAFE |
| 3 | `claude/audit-creator-tracking-TX9zV` | `454f446d` | 2026-03-07 | 410/1564 | 0 | KILL_SAFE |
| 4 | `codex/cand-001-notion-draft-flow` | `3a2765fa` | 2026-04-22 | 886/1564 | 8 | KILL_SAFE |
| 5 | `codex/editorial-pr-stack-coordination-qa` | `d800c288` | 2026-04-22 | 847/1564 | 2 | KILL_SAFE |
| 6 | `codex/editorial-stack-final-readiness-qa` | `24bf07e0` | 2026-04-22 | 847/1564 | 2 | KILL_SAFE |
| 7 | `codex/granola-raw-intake-batch` | `70ba2ac5` | 2026-04-13 | 701/1564 | 0 | KILL_SAFE |
| 8 | `codex/notion-governance-v1-contract` | `2221f5af` | 2026-03-31 | 690/1564 | 6 | **CHERRY_CANDIDATE** |
| 9 | `codex/notion-publicaciones-setup-runbook` | `7edbc6c2` | 2026-04-22 | 871/1564 | 1 (ruido) | KILL_SAFE |
| 10 | `codex/notion-v2-drift-cleanup` | `38ca2ed9` | 2026-04-07 | 693/1564 | 0 | KILL_SAFE |
| 11 | `codex/rick-qa-cand-001-validation` | `c121cfd9` | 2026-04-22 | 885/1564 | 3 (2 reales+ruido) | KILL_SAFE |
| 12 | `codex/session-capitalizable-promotion-v1` | `5e6e0478` | 2026-03-31 | 693/1564 | 1 | KILL_SAFE |
| 13 | `codex/wip-granola-v2-snapshot-2026-04-30` | `e72ebab4` | 2026-04-30 | 579/1564 | 28 | **CHERRY_CANDIDATE** |
| 14 | `copilot/analyze-agent-stack-infrastructure` | `3d8809c9` | 2026-04-10 | 692/1564 | 0 | KILL_SAFE |
| 15 | `copilot/create-umbral-agent-stack-repo` | `8bf3b023` | 2026-02-26 | 2/1564 | 0 | KILL_SAFE |
| 16 | `copilot/feat-mission-control-o13-1` | `e1d2bc38` | 2026-05-05 | 959/1564 | 1 (ruido) | KILL_SAFE |
| 17 | `copilot/research-agent-stack-infrastructure` | `3d8809c9` | 2026-04-10 | 692/1564 | 0 | KILL_SAFE |
| 18 | `cursor/2026-03-22-001-codex-env-diagnostico` | `34fe635e` | 2026-03-22 | 555/1564 | 0 | KILL_SAFE |
| 19 | `cursor/bit-cora-contenido-enriquecido-4099` | `e9be3fad` | 2026-03-05 | 328/1564 | 0 | KILL_SAFE |
| 20 | `cursor/board-estado-actual-e573` | `bfc0fd7d` | 2026-03-05 | 325/1564 | 0 | KILL_SAFE |
| 21 | `cursor/cierre-integraci-n-main-4905` | `afd2ce0f` | 2026-03-05 | 340/1564 | 0 | KILL_SAFE |
| 22 | `cursor/development-environment-setup-ac64` | `13ab7d58` | 2026-03-04 | 123/1564 | 0 | KILL_SAFE |
| 23 | `cursor/fusi-n-prs-69-70-71-23e1` | `b038d8b6` | 2026-03-05 | 330/1564 | 0 | KILL_SAFE |
| 24 | `cursor/integraci-n-de-prs-en-main-3876` | `3ce23aff` | 2026-03-05 | 336/1564 | 0 | KILL_SAFE |
| 25 | `cursor/integraci-n-de-prs-y-pruebas-1084` | `e74b254f` | 2026-03-05 | 339/1564 | 0 | KILL_SAFE |
| 26 | `cursor/missing-test-coverage-04dd` | `02132531` | 2026-04-08 | 692/1564 | 0 | KILL_SAFE |
| 27 | `cursor/missing-test-coverage-2a09` | `309ea835` | 2026-04-04 | 691/1564 | 1 | KILL_SAFE |
| 28 | `cursor/missing-test-coverage-4c51` | `2cea0fc2` | 2026-04-14 | 703/1564 | 0 | KILL_SAFE |
| 29 | `cursor/missing-test-coverage-8db5` | `dac00332` | 2026-04-12 | 693/1564 | 0 | KILL_SAFE |
| 30 | `cursor/missing-test-coverage-961c` | `de091488` | 2026-04-07 | 692/1564 | 0 | KILL_SAFE |
| 31 | `cursor/missing-test-coverage-c75b` | `9ac5d445` | 2026-04-09 | 692/1564 | 0 | KILL_SAFE |
| 32 | `cursor/power-bi-libraries-formats-5c1b` | `6a64515c` | 2026-03-05 | 326/1564 | 1 | KEEP_FOSSIL |
| 33 | `cursor/r16-cierre-y-documentaci-n-bc44` | `057eb26c` | 2026-03-05 | 329/1564 | 0 | KILL_SAFE |
| 34 | `cursor/regression-test-coverage-0d73` | `b2965d2a` | 2026-04-10 | 693/1564 | 0 | KILL_SAFE |
| 35 | `cursor/regression-test-coverage-136d` | `1c3bbd93` | 2026-04-06 | 691/1564 | 1 | KILL_SAFE |
| 36 | `cursor/regression-test-coverage-1863` | `5cb80ac1` | 2026-04-15 | 736/1564 | 1 (ruido) | KILL_SAFE |
| 37 | `cursor/regression-test-coverage-91c7` | `ea7b6a41` | 2026-04-11 | 693/1564 | 0 | KILL_SAFE |
| 38 | `cursor/regression-test-coverage-b904` | `de318aff` | 2026-04-13 | 703/1564 | 0 | KEEP_FOSSIL |
| 39 | `cursor/regression-test-coverage-d34a` | `5ba092ba` | 2026-04-05 | 691/1564 | 1 | KILL_SAFE |
| 40 | `cursor/regression-test-coverage-e479` | `f3e36b1f` | 2026-04-16 | 736/1564 | 1 (ruido) | KILL_SAFE |
| 41 | `cursor/tests-document-generator-dependencias-8af0` | `d805d62f` | 2026-03-05 | 321/1564 | 0 | KILL_SAFE |
| 42 | `feat/bitacora-populate` | `fe5d3393` | 2026-03-05 | 290/1564 | 2 | KEEP_FOSSIL |
| 43 | `feat/browser-automation-vm-research` | `8eebe4de` | 2026-03-05 | 331/1564 | 0 | KILL_SAFE |
| 44 | `feat/ci-readme-verificacion` | `c9e66047` | 2026-03-05 | 327/1564 | 1 | KILL_SAFE |
| 45 | `feat/copilot-azure-foundry-audio` | `99c2ce1c` | 2026-03-04 | 194/1564 | 0 | KILL_SAFE |
| 46 | `feat/r16-080-limpieza-prs-docs` | `46dc7582` | 2026-03-05 | 225/1564 | 1 | KILL_SAFE |
| 47 | `feat/ux1-noise-reduction` | `52acdfcf` | 2026-04-14 | 704/1564 | 0 | KILL_SAFE |
| 48 | `rescue/copilot-vps/rick-vps-orphans-2026-07` | `4b8cfbb4` | 2026-06-07 | 436/1564 | 0 | KILL_SAFE |
| 49 | `rescue/copilot-vps/rick-vps-stash-windows-fs-b64-2026-07` | `e0c5d9e6` | 2026-03-07 | 105/1564 | 0 | KILL_SAFE |
| 50 | `rick/copilot-cli-f7-code-gate-rehearsal` | `0d6ad83c` | 2026-05-05 | 994/1564 | 1 (ruido) | KILL_SAFE |
| 51 | `rick/editorial-linkedin-writer-flow` | `410266a0` | 2026-05-05 | 915/1564 | 21 | **CHERRY_CANDIDATE** |
| 52 | `rick/fix-copilot-ci` | `9acdf1cd` | 2026-04-17 | 775/1564 | 1 (ruido) | KILL_SAFE |
| 53 | `rick/t/fcb2f1bc/a` | `893f95cc` | 2026-04-17 | 765/1564 | 2 | KILL_SAFE |
| 54 | `rick/t/fcb2f1bc/b` | `ba323b9d` | 2026-04-17 | 765/1564 | 2 | KILL_SAFE |
| 55 | `rick/t/fcb2f1bc/c` | `7abb789a` | 2026-04-17 | 765/1564 | 2 | KILL_SAFE |
| 56 | `rick/t/fcb2f1bc/final` | `e9fb95dc` | 2026-04-17 | 764/1564 | 1 (ruido) | KILL_SAFE |
| 57 | `rick/test-github-mvp-smoke` | `9d983463` | 2026-04-14 | 732/1564 | 4 | **CHERRY_CANDIDATE** |
| 58 | `rick/windows-dirty-rescue-2026-04-27` | `e77ca7c2` | 2026-04-27 | 577/1564 | 6 | KEEP_FOSSIL |

### 2.1 Razones agrupadas (KILL_SAFE, 49)

- **Duplicado exacto** (#14, #17): mismo SHA `3d8809c9` — literalmente la misma rama con dos
  nombres.
- **Torneo explícito** (#53–56): `.rick/tournaments/fcb2f1bc/{a,b,c}.md` — contestants de un
  torneo automático; solo un lane se elige y mergea, el resto es residuo por diseño.
- **Swarm de test-coverage duplicado** (#26–31, #34–37, #39–40, 12 ramas `missing-test-coverage-*`
  / `regression-test-coverage-*`): mismo rango de fechas (abril), mismo target (guardrails/poller de
  Granola V1, `session-capitalizable`), ninguna con PR — patrón de generación paralela de patches de
  cobertura sobre código V1 hoy superado por la arquitectura V2. Tres de ellas (#27, #35, #39)
  proponen literalmente el mismo path `tests/test_worker_config.py` — tres lanes distintos
  compitiendo por el mismo archivo, ninguno elegido.
- **Bookkeeping R14–R16 ya integrado** (#19–25, #33, #41, #43): docs de board/bitácora, "merge PRs
  #69-73", "pytest 847 passed", updates de `AGENTS.md` — literalmente el registro histórico de una
  integración de PRs (#69, #70, #71, #73, #75, #81) que ya ocurrió hace meses.
- **QA/audit de un candidato ya resuelto** (#4–6, #11): CAND-001 (Notion draft flow, RickQA
  validation) y la coordinación/readiness del editorial stack de abril — trazas de un ciclo de
  validación puntual, sin contenido generalizable; el trabajo editorial avanzó muchas rondas después
  (Ola 2/3, gap-matrix norte 2026-07-22).
- **CI config superado** (#44, #46): proponen `.github/workflows/{pytest,tests}.yml`; `main` corre
  hoy `.github/workflows/test.yml` — nombres distintos, generación anterior de la CI.
- **Absorbido por nombre+existencia en `main`** (#2, #3, #7, #9, #10, #12, #16, #18, #45, #47–50,
  #52): el path relevante de cada rama ya existe en `main` bajo el mismo nombre (granola V1→V2,
  Azure Foundry, delegación de agentes, rescates VPS de julio) — se asume superado por evolución
  salvo que aparezca como CHERRY_CANDIDATE.
- **Trivial** (#15): "Initial plan", 2 archivos, rama de arranque del repo (26 de febrero).

### 2.2 KEEP_FOSSIL (4) — duda real, no se propone acción

- **#32** `cursor/power-bi-libraries-formats-5c1b` — doc de investigación sobre formatos Power BI
  (`.pbix`/`.pbip`/`.pbir`); tema no aparece en ningún otro lugar del proyecto activo, relevancia
  incierta.
- **#38** `cursor/regression-test-coverage-b904` — único del swarm de test-coverage con tema
  distinto (OData escaping, límite diario de encolado, LRU del limiter — seguridad/rate-limit, no
  Granola); no se agrupó con el resto del swarm por ese motivo.
- **#42** `feat/bitacora-populate` — script `populate_bitacora.py` + test; utilidad de bitácora
  Notion de marzo, posible solape con tooling de gobernanza Notion actual, no verificado.
- **#58** `rick/windows-dirty-rescue-2026-04-27` — sus 6 paths únicos son un **subconjunto exacto**
  de los de `codex/wip-granola-v2-snapshot-2026-04-30` (#13, CHERRY_CANDIDATE). Se deja en
  KEEP_FOSSIL en vez de KILL_SAFE porque la subsunción no está en la lista de motivos KILL_SAFE del
  pack; si David da GO a evaluar #13, esta rama queda sin acción propia (contenido cubierto).

---

## 3. Top CHERRY_CANDIDATE (5, dentro del máximo de 15)

Ninguna se cherry-pickeó. Esto es evaluación, no ejecución — el siguiente pack (si David lo pide)
tomaría cada path uno por uno como hizo `PKG-UAS-P1-2-ORPHAN-RESCUE1`.

### 3.1 `codex/wip-granola-v2-snapshot-2026-04-30` (28 paths únicos)

`snapshot(rescue-2026-04-27): preserve one-shot Drive/Codex audit & redaction scripts`. Scripts
operativos de auditoría/redacción/export de Drive (`scripts/codex_drive_audit.ps1`,
`redact_and_sync_drive.ps1`, `redact_fast_and_sync.ps1`, `validate_redaction_v2.ps1`,
`export_curated_to_drive.ps1`, `final_drive_report.ps1`, y 9 más `scripts/codex_*.ps1`) +
`scripts/run_granola_session_deprecation_migration.py` + `run_granola_shared_folder_sync.py` + su
test + 6 docs (`docs/67-resumen-estrategia-web-umbral.md`, 2 audits de abril, cheatsheet openclaw,
2 docs de instrucciones VPS/Rick). Comparte 6 de estos paths con `rick/windows-dirty-rescue-2026-04-27`
(#58) — evaluar esta rama cubre ambas. **Duda a resolver antes de cherry-pick:** si estos scripts
ya cumplieron su función en el catch-up de Drive que memoria marca `COMPLETE` (P1.1b, 95 archivos
ingeridos) o si siguen siendo tooling operativo vigente.

### 3.2 `rick/editorial-linkedin-writer-flow` (21 paths únicos)

`docs(editorial): upgrade CAND-004 traceability prototype`. Prototipo completo de un skill
**`linkedin-post-writer`** para `openclaw/workspace-templates/skills/` (`SKILL.md`,
`CALIBRATION.md`, `LINKEDIN_WRITING_RULES.md`) + overrides de agente
(`openclaw/workspace-agent-overrides/rick-linkedin-writer/{AGENTS,HEARTBEAT}.md`) + 15 docs de
CAND-003/CAND-004 (variants, benchmark calibration, microedit, architect review, traceability
contract). Es un dominio **distinto** de `linkedin-human-outreach` (memoria: esa skill es
page-follow/connect, no redacción de posts) — si el prototipo de escritura de posts nunca se
canonizó en el registry, esto podría ser la única copia. **Duda a resolver:** si el prototipo
sigue vigente o fue superado por el pipeline editorial actual (Ola 2/3, `production-flow-v2`).

### 3.3 `antigravity/sync-uncommitted-changes` (9 paths únicos)

`feat: sync uncommitted workspace changes (teams, skills, docs)`. Diseño de un "codegen team"
completo: `docs/architecture/06-codegen-team-design.md`, `docs/roadmap/codegen-rollout-phases.md`,
`runbooks/runbook-codegen-fase1-smoke.md`, y 5 skills de `openclaw/workspace-templates/skills/`
(`code-architect`, `code-debugger`, `code-implementer`, `code-reviewer`, `code-scribe`). Iniciativa
de abril que no aparece en ningún acta posterior conocida — **duda a resolver:** si el "codegen
team" se abandonó deliberadamente o simplemente no llegó a mergearse.

### 3.4 `rick/test-github-mvp-smoke` (4 paths únicos)

`test: GitHub MVP smoke test via handler pipeline`. Incluye
**`.claude/hooks/block-deployed-repo-writes.sh`** — un hook `PreToolUse` real (no ruido: se leyó
el contenido completo) que bloquea escrituras accidentales sobre un "repo deployado", parseando
`tool_name`/`tool_input` y devolviendo `allow`/`ask` vía JSON. Dado que este mismo hilo trabajó con
higiene de clones/worktrees (memoria: `uas-main-clone-sanitize`, `pkg-uas-p1-2-branch-wt`), un hook
de seguridad de esa naturaleza podría tener valor operativo hoy. + `docs/audits/github-mvp-smoke-test.md`
+ `docs/audits/notion-curation-snapshot-2026-03-16.json`.

### 3.5 `codex/notion-governance-v1-contract` (6 paths únicos)

`Add Notion governance V1 contract`. `docs/adr/ADR-005-raw-capitalizable-capitalization.md` +
`docs/architecture/02-operating-model-v1.md` + `docs/policies/02-permissions-by-surface.md` +
`docs/policies/03-capitalization-rules.md` + `registry/runtime-bridge-contract.yaml` +
`registry/taxonomies-v1.yaml`. Es contrato de gobernanza **V1** — el sistema vigente hoy es V2
(memoria: `notion-governance-runtime`, hybrid plan P1/P2a mergeados). No se clasificó KILL_SAFE
porque no se verificó punto a punto si el ADR-005 o las políticas se re-emitieron con otro número
en la migración a V2, o si simplemente no se documentó ese salto — esa verificación es justamente
el trabajo de un pack de cherry-pick.

---

## 4. Fase B — Propuesta de capitalización vN — modo: **propose-only**

Lectura obligatoria de canónico completada antes de proponer: `pkg-receiver-protocol` v0.3.4
(`C:\GitHub\umbral-skills-registry\skills\pkg-receiver-protocol\SKILL.md` + `manifest.yaml`).
Registry confirmado de un solo escritor (`git status --porcelain` limpio antes de leer). Dry-run de
gate corrido para el único slug candidato:

```
SHIP_VALIDATE_PASS=Y
SHIP_DRIFT_GATE_PASS=Y
SHIP_SKILL_NOOP=Y
[claude_desktop] pkg-receiver-protocol -> noop
[codex]          pkg-receiver-protocol -> noop
Pending changes: 0
```

Sin drift, sin HOLD — un patch aquí shipearía limpio si David da GO en modo `capitalize`.

| # | Skill (slug) | Estado | Acción | Delta (resumen) | Solape | Clase | Evidencia | Riesgo/Drift |
|---|---|---|---|---|---|---|---|---|
| 1 | `pkg-receiver-protocol` | 0.3.4/experimental | patch (semver: minor→0.4.0) | §2: sin merge-base ⇒ historias disjuntas, ahead no mide trabajo propio, rescate solo por cherry-pick puntual | refuerza (cita §2 punto 2, regla `ahead≠0` 2026-08-06) | regla estable | "58/58 ramas huérfanas... `git merge-base` exit 1" (Fase A §1.2 de este hilo) | SAFE (update) |
| 2 | `pkg-receiver-protocol` | 0.3.4/experimental | patch (semver: minor→0.4.0) | §2: nuevo bullet — STOP parcial si el conteo de inventario re-verificado diverge del umbral que trae el paquete, sin ajustar el plan en silencio | nuevo | regla estable | `uas-p1-2-branch-wt-2026-08-06.md` §1.4 (191 vs ~87, +120%, STOP) + este hilo (58 vs 58, 0%, sin STOP) | SAFE (update) |
| 3 | `pkg-receiver-protocol` | 0.3.4/experimental | patch (semver: minor→0.4.0) | §2: nuevo bullet — separar runtime (SKILL.md activo) de histórico al clasificar contenido para archive/kill; un mismo path puede mezclar ambos, el runtime se excluye siempre | nuevo | patrón operativo | memoria `pkg-uas-p1-2-keep1-archive.md` + `pkg-uas-p1-2-orphan-keep3.md` (cadena de hoy) | SAFE (update) |
| 4 | `pkg-receiver-protocol` | 0.3.4/experimental | patch (semver: minor→0.4.0) | §2: nuevo bullet — descartar paths de config/entorno local (`.claude/skills/**`, `.codex/**`, `.cursor/**`) antes de juzgar valor de una rama sin merge-base por comparación de nombres | nuevo | patrón operativo | Fase A §1.3 de este hilo: mismo path en 15/58 ramas sin relación temática | SAFE (update) |

### Delta #1
Solape: refuerza (cita `SKILL.md` §2 punto 2, regla dura 2026-08-06 "Bajo squash-merge, ahead≠0 no
es trabajo sin integrar")
Cuando `git merge-base origin/main origin/<rama>` falla (exit 1, sin ancestro común), el
ahead/behind de `git rev-list --left-right --count` no mide "commits propios" — mide el tamaño de
dos historias completamente disjuntas (p. ej. tras una reescritura de `main`). Nunca tratar ese
ahead como señal de trabajo sin integrar; el único rescate válido es cherry-pick de archivos
puntuales citados por `git ls-tree`/`comm`, nunca merge/ff.
Evidencia: "MISSING=0 STILL_NO_MB=58 NOW_HAS_MB=0" — 58/58 huérfanas de `umbral-agent-stack`
re-verificadas sin merge-base con `origin/main`, consistente con `UAS_MAIN_CLONE_SANITIZED`
(memoria, 2026-07-23).

### Delta #2
Solape: nuevo
Cuando el paquete pide re-verificar un conteo de inventario previo (ramas, archivos, candidatos)
contra un umbral de divergencia, correr la verificación completa antes de cualquier acción
destructiva/masiva sobre ese conjunto: si diverge por encima del umbral, STOP parcial, reportar el
número real y seguir solo con el subconjunto verificado — nunca ajustar el plan original en
silencio.
Evidencia: `uas-p1-2-branch-wt-2026-08-06.md` §1.4 — "191 vs 87 = +120%. STOP." (umbral 15%) y este
mismo hilo — "58/58... Divergencia = 0%" (umbral 20%, sin STOP). Dos paquetes consecutivos de
cursor-orchestrator ya traen este gate en su propio texto; falta en el contrato del receptor.

### Delta #3
Solape: nuevo
Antes de archivar/matar contenido que vive en un directorio de skill o config activa, separar
explícitamente qué es runtime (`SKILL.md`/manifest cargado por un agente vivo) de qué es histórico
(runbooks, reports, docs de una versión superada): el mismo path puede mezclar ambos. Un directorio
con `SKILL.md` activo nunca entra al lote de archive/kill aunque el resto del contenido sea
histórico — se excluye y se cita aparte.
Evidencia: memoria `pkg-uas-p1-2-keep1-archive.md` — "SKILL.md es runtime, excluir" (fila PIT,
`ARCHIVE_DOCS_ONLY`), confirmado con diff 0 tras ejecutar.

### Delta #4
Solape: nuevo
Al comparar `git ls-tree -r --name-only <rama-huérfana>` contra los paths de `main` para estimar
contenido único de una rama sin merge-base, descartar primero paths de config/entorno local del
committer (`.claude/skills/**`, `.codex/**`, `.cursor/**`, cachés) antes de juzgar valor de rescate
— reflejan lo que había en el working tree al commitear, no contenido intencional de la rama.
Evidencia: `.claude/skills/openclaw-vps-operator/SKILL.md` apareció como "único" en 15/58 huérfanas
de este pack, sin relación temática entre sí — puro artefacto de captura local (Fase A §1.3).

**Qué pasará tras GO** (si David da GO en modo `capitalize` sobre esta tabla): (1) patch a
`SKILL.md` de `pkg-receiver-protocol` con los 4 deltas dentro de §2; (2) bump `manifest.yaml` a
`0.4.0` + entrada en `notes:` con esta evidencia; (3) `validate_manifest.py` + secret/scope check +
`ship_skill.py --slug pkg-receiver-protocol --apply --commit --push` → despliega a
`claude_desktop` + `codex` (los únicos targets `enabled: true` hoy; `cursor`/`copilot_chat`/
`antigravity`/`cursor_rules` siguen `false`, sin cambio).

**Qué NO pasará:** no se habilita ninguna plataforma nueva; no se toca `cursor-orchestrator` (el
"STOP si diverge" es del lado receptor, no de su § Gobernanza de emisión); no se cherry-pickea
ninguna de las 5 CHERRY_CANDIDATE; no se borra ninguna de las 49 KILL_SAFE.

### Descartadas por solape / evaluadas sin evidencia

- `cursor-orchestrator` — evaluado (el pack lo listaba como candidato típico); el patrón "STOP si
  diverge" es de ejecución del receptor, no de la lógica de emisión/routing del orquestador — cae
  fuera de su frontera de gobernanza declarada en `skills-capitalize`. Sin delta propuesto.
- `openclaw-vps-operator` — evaluado; este hilo no tocó VPS ni runtime OpenClaw. Sin evidencia, sin
  delta.
- `umbral-rick-runtime` — evaluado; este hilo no tocó Rick/OpenClaw. Sin evidencia, sin delta.
- NUEVA skill de triage de huérfanas — evaluada; el aprendizaje cae dentro de la frontera ya
  declarada de `pkg-receiver-protocol` §2 (higiene git / inventario antes de destruir), no cruza a
  un dominio nuevo. Se propone como patch, no como skill nueva.

**¿GO, correcciones, o solo proponer?** — este pack cierra en `propose-only`: la tabla queda lista
para que un hilo futuro (o este mismo, si David responde) la re-invoque en modo `capitalize`.

---

## 5. Prohibido (respetado)

- Cero `git push --delete` sobre cualquiera de las 58.
- Cero cherry-pick a `main` (ni de las 5 CHERRY_CANDIDATE).
- Cero `ship_skill.py --apply` / `--commit` / `--push` (solo dry-run, confirmado arriba).
- Cero `sync_skills.py --reconcile --apply`.
- Cero touch a VPS/Notion.
- Un solo escritor del registry — confirmado limpio antes y después de los dry-runs.
- Ninguna etiqueta sin evidencia citada (tabla §2 + razones agrupadas §2.1/§2.2 + detalle §3).

---

## 6. Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: se agrega
"orphan58 **analyze DONE**" a la línea existente; deletes/cherry-pick/capitalize quedan `PENDING`
GO de David.
