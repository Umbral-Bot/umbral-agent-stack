# P1.2 — Evaluación path a path de las 5 CHERRY_CANDIDATE (2026-08-07)

> **Pack:** PKG-UAS-P1-2-ORPHAN58-CHERRY5 · rama `claude/pkg-uas-p1-2-orphan58-cherry5-20260807` ·
> base `a9488b0b`
> **GO de David:** "b" — evaluar las 5 `CHERRY_CANDIDATE` de
> [uas-p1-2-orphan58-analyze-capx-20260806.md](uas-p1-2-orphan58-analyze-capx-20260806.md) §3.1–3.5
> path a path. **Cero `git checkout` de paths a `main`. Cero `push --delete`. Solo acta +
> recomendación por fila/path.**

Las 5 ramas siguen vivas post-KILL49 ([uas-p1-2-orphan58-kill49-20260807.md](uas-p1-2-orphan58-kill49-20260807.md))
y siguen sin `merge-base` con `origin/main` — re-confirmado con `git merge-base` (exit 1) para las 5
antes de evaluar (§1). Bajo esa condición, el único rescate válido es cherry-pick puntual de paths
citados por `git ls-tree`, nunca merge/ff (`pkg-receiver-protocol` §2).

---

## 0. Resumen ejecutivo

| # | Rama | Tip | Recomendación | Esfuerzo | Riesgo |
|---|---|---|---|---|---|
| 1 | `codex/wip-granola-v2-snapshot-2026-04-30` | `e72ebab4` | **KILL_BRANCH** (28 paths, cubre también #58) | bajo | medio-bajo si se rescatara (confusión de versión vigente) |
| 2 | `rick/editorial-linkedin-writer-flow` | `410266a0` | **ARCHIVE_DOCS_ONLY** (21 paths) | bajo | bajo si se archiva; medio-alto si se "rescata" como skill activa |
| 3 | `antigravity/sync-uncommitted-changes` | `9e32a99b` | **ARCHIVE_DOCS_ONLY** (3 docs) + **DEFER_PRODUCT** (5 skills + `config/teams.yaml`) | bajo (archive) / N/A (defer) | bajo (docs); medio-bajo si se mergean las skills sin GO |
| 4 | `rick/test-github-mvp-smoke` | `9d983463` | **RESCUE_SELECTIVE** (solo `.claude/hooks/block-deployed-repo-writes.sh`) | bajo | bajo (archivo inerte); mayor si además se wirea en `settings.json` (fuera de este pack) |
| 5 | `codex/notion-governance-v1-contract` | `2221f5af` | **ARCHIVE_DOCS_ONLY** (6 paths, como contrato único) | bajo | bajo si estrictamente histórico; medio si se confunde con reactivación |

**Nada se ejecutó en este pack** — cero cherry-pick, cero delete, cero archive real. Es evaluación
con evidencia para que un GO posterior de David sea selectivo por fila.

---

## 1. Confirmación de tips y ausencia de merge-base

```
codex/wip-granola-v2-snapshot-2026-04-30   e72ebab4  NO MERGE-BASE
rick/editorial-linkedin-writer-flow        410266a0  NO MERGE-BASE
antigravity/sync-uncommitted-changes       9e32a99b  NO MERGE-BASE
rick/test-github-mvp-smoke                 9d983463  NO MERGE-BASE
codex/notion-governance-v1-contract        2221f5af  NO MERGE-BASE
```

Los 5 tips coinciden exactamente con los citados en el pack. Ninguna ganó merge-base desde el acta
del 2026-08-06.

---

## 2. Detalle por rama

### 2.1 `codex/wip-granola-v2-snapshot-2026-04-30` → **KILL_BRANCH**

28 paths reales (descontado ruido `.claude/.codex/.cursor`), tres familias:

- **19 scripts `scripts/codex_*.ps1`** de catch-up de Google Drive (`codex_drive_audit.ps1`,
  `final_drive_report.ps1`, `redact_and_sync_drive.ps1`, `validate_redaction_v2.ps1`, y 15 más).
  Los 4 leídos completos tienen **hardcodeada la ruta/fecha de un único run**:
  `$stage = 'C:\AGE_STAGE\ai-agents-export-2026-04-27'`, `$dest = 'G:\Mi unidad\...\ai-agents-export-2026-04-27'`
  — no son tooling parametrizado, son artefactos de una corrida puntual en la máquina de David.
- **2 scripts + 1 test de migración Granola V1→V2**: `run_granola_session_deprecation_migration.py`
  usa `NOTION_GRANOLA_SESSION_DB_ID`, variable **inexistente** en `worker/config.py` de `main`
  (grep vacío) — el concepto que migra ya no existe. `run_granola_shared_folder_sync.py` queda
  superado por la familia ya presente en `main` con el mismo propósito descompuesto:
  `build_granola_drive_ingest_batch.py`, `list_granola_drive_ingest_gap.py`,
  `run_granola_raw_ingest_batch.py`, `send_granola_drive_batch.py`.
- **6 docs**: todos históricos y superados — el brief V1→V2 de Notion (`main` ya tiene
  `vendor/notion-governance/` + skill `notion-governance-runtime`), el workflow VPS de
  `rick-instrucciones-vps-rama-rick.md` (`scripts/vps/ensure-main-for-run.sh` ya existe en `main`,
  ya documentado en `docs/28-rick-github-workflow.md`), y el cheatsheet ya extraído a la skill
  `openclaw-expert` canónica.

**Duda del acta resuelta:** son scripts one-shot de un catch-up ya cumplido (memoria:
`granola-drive-catchup-p11b` COMPLETE, 95 archivos, 0 FAIL), no tooling vigente — evidencia:
constantes de fecha/ruta hardcodeadas, variables de entorno inexistentes en `main`, y familia
equivalente ya presente y en uso.

**Subsunción:** `rick/windows-dirty-rescue-2026-04-27` (#58, KEEP_FOSSIL en el acta previa) tiene
sus 6 paths únicos como subconjunto exacto de estos 28 — el mismo KILL_BRANCH la cubre por
completo en contenido; la rama en sí queda fuera del alcance de este pack (no es una de las 5), sin
acción propia pendiente más allá de anotar que su contenido no aporta nada nuevo.

### 2.2 `rick/editorial-linkedin-writer-flow` → **ARCHIVE_DOCS_ONLY**

21 paths reales: skill prototipo `linkedin-post-writer` (3 archivos), overrides de agente
`rick-linkedin-writer` (3), doc de diseño (1), y 14 docs CAND-003/CAND-004.

**Evidencia de que está superado:**
- `openclaw/workspace-agent-overrides/rick-linkedin-writer/` **ya existe en `main`**, pero con
  arquitectura completamente distinta (`ROLE.md`/`SKILL.md`/`INPUTS.md`/`OUTPUTS.md`, pipeline
  SQLite Stage 5-7, status **PAUSED** EDITORIAL-03 2026-06-01) y última tocada 2026-06-29/07-22 —
  ~2 meses después del tip de esta rama. Su lista de skills activas es `linkedin-content`,
  `linkedin-david`, `editorial-source-curation`, `editorial-voice-profile` — no
  `linkedin-post-writer`.
- `docs/editorial-pipeline/production-flow-v2-2026-06-06.md` en `main` es canónico confirmado por
  David, posterior al tip de la rama, y reemplaza los gates/planes previos.
- Las reglas de calibración de voz (CAL-LW-001…009) ya están absorbidas, condensadas, dentro de
  `openclaw/workspace-templates/skills/linkedin-david/SKILL.md` de `main` (mismo lenguaje, mismos
  anti-patrones, confirmado por grep).

**Recomendación:** archivar los 21 paths como referencia histórica (destino sugerido
`docs/archive/`), **sin** reinsertar `linkedin-post-writer` en `openclaw/workspace-templates/skills/`
ni tocar el override `rick-linkedin-writer/` real de `main` (colisionaría con contenido vivo
distinto). No hay sub-lote RESCUE_SELECTIVE defendible: el prototipo induciría a error si se
registrara como skill activa hoy.

### 2.3 `antigravity/sync-uncommitted-changes` → **ARCHIVE_DOCS_ONLY + DEFER_PRODUCT**

9 paths reales, un solo commit (2026-04-29): diseño de un equipo interno `build`
(architect→implementer→reviewer→debugger→scribe) para que Rick genere código en sandbox Docker
sobre un Worker Linux nuevo, con 2 gates HITL vía Notion.

- **Docs de diseño (3)** — `docs/architecture/06-codegen-team-design.md`,
  `docs/roadmap/codegen-rollout-phases.md`, `runbooks/runbook-codegen-fase1-smoke.md`: contenido
  sustancial (no fantasía desconectada — referencia infraestructura real de `main`:
  `worker/sandbox/workspace.py`, TaskEnvelope, Langfuse, Redis, poller Notion), pero Fase 1 admite
  explícitamente que el handler `code.architect` y el Worker `:8089` **no existen** — diseño
  completo, cero código funcional. → **ARCHIVE_DOCS_ONLY**.
- **5 skills + `config/teams.yaml`** (`code-architect/debugger/implementer/reviewer/scribe`,
  contratos JSON accionables, no esqueletos vacíos) — mergearlas solas activaría en Rick un equipo
  `build` descubrible que apunta a tasks inexistentes (`code.architect`, etc.): capacidad fantasma.
  → **DEFER_PRODUCT**, tal como exige la regla del pack ("no mergear 5 skills a templates sin GO de
  producto").

**Duda del acta resuelta:** `git log origin/main --all --oneline | grep -iE "codegen.team|code-architect|code-scribe"`
→ vacío. `ADR-013-codegen-backend-stage-gate.md` es homónimo pero de otro tema (Azure vs Hostinger
para O5/`umbral-bot-2`), sin relación textual ni de fecha. No hay ADR, nota o commit posterior que
diga "descartamos codegen team" — todo apunta a **simplemente no se mergeó** (sync local
capturado), no a un rechazo consciente.

### 2.4 `rick/test-github-mvp-smoke` → **RESCUE_SELECTIVE** (alcance mínimo)

4 paths únicos reales (no 3 como estimaba el acta previa — el 4º es ruido confirmado):

| Path | Veredicto |
|---|---|
| `.claude/hooks/block-deployed-repo-writes.sh` (100755) | **Rescatar** — hook `PreToolUse` real y completo |
| `docs/audits/github-mvp-smoke-test.md` | Descartar — literalmente dice "Safe to delete", artefacto trivial del propio smoke |
| `docs/audits/notion-curation-snapshot-2026-03-16.json` | Descartar — snapshot de una corrida no-op (`counts_before == counts_after`, listas de cambio vacías) |
| `.claude/skills/openclaw-vps-operator/SKILL.md` | Descartar — ruido de entorno local (regla dura del protocolo, mismo patrón que 15/58 huérfanas del acta previa) |

El script parsea `tool_name`/`tool_input` por stdin JSON; para `Write/Edit/MultiEdit` bloquea paths
fuera de `[".claude/", ".github/copilot-instructions.md"]`; para `Bash` bloquea comandos que
"parecen escritura" mencionando `/home/rick/umbral-agent-stack` sin mencionar la variante
`-main-clean`. **No es genérico** — depende de que esa topología de clones en la VPS siga vigente
hoy (no verificado en este pack). La rama **no** trae `.claude/settings.json` con clave `hooks`: el
script nunca quedó wireado ni en su propio commit; `main` tampoco tiene hooks configurados hoy.

**Dos decisiones separadas, solo la primera cabe en "rescatar el archivo":**
1. Traer el `.sh` a disco sin tocar `settings.json` — **bajo riesgo**, archivo inerte hasta que algo
   lo referencie.
2. Wirearlo como `PreToolUse` — **mayor riesgo**, requiere verificar que las rutas VPS hardcodeadas
   siguen vigentes (memoria: `uas-main-clone-sanitize`, `pkg-uas-p1-2-branch-wt` pudieron cambiar la
   topología desde abril) y testing antes de activar. **Fuera del alcance de este pack** — es un GO
   explícito y distinto.

### 2.5 `codex/notion-governance-v1-contract` → **ARCHIVE_DOCS_ONLY**

6 paths, un contrato de gobernanza V1 coherente (ADR + operating model + 2 policies + 2 registry
YAML). `docs/policies/` y `registry/` **no existen hoy en `main`**; `docs/adr/` tiene ADR-001..013
sin ninguno de capitalización/raw (el slot ADR-005 de `main` es `publicacion-multicanal`, tema
distinto por coincidencia de número — **no hubo renumeración ni re-emisión**, confirmado).

El territorio SÍ está cubierto hoy, pero disperso y con forma completamente distinta: skill
`notion-governance-runtime` (guardrails G1-G7), y sobre todo
`docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md` — V1 proponía staging obligatorio vía
`capitalizable_session`; V2 es `raw → classify_raw → capitalize_task_from_raw` project-first, sin
esa capa intermedia, con taxonomía Dominio/Tipo/Destino (no las 8 tablas de `taxonomies-v1.yaml`),
permisos como guardrails G1-G7 (no matriz `comment/propose/edit`), y bindings reales verificados en
VPS (no placeholders `<RAW_SESSIONS_DB_ID>`).

**Duda del acta resuelta:** cubierto con otra arquitectura, no reintroducir V1. El único valor real
es histórico — ningún doc V2 actual explica *que* el diseño con staging obligatorio se descartó a
favor del flujo directo; ese pivote queda huérfano de traza. Recomendación: un doc corto de archivo
(`docs/adr/` o `docs/ops/`) que cite estos 6 paths como "V1 descartado, ver plan híbrido
2026-07-16 y `notion-governance-runtime` para lo vigente", encabezado explícito **SUPERSEDED — no
vigente**, sin copiar contenido V1 a superficies activas.

---

## 3. Pack de ejecución sugerido (orden, si David da GO por fila)

1. **RESCUE_SELECTIVE mínimo** (#4) — copiar solo `.claude/hooks/block-deployed-repo-writes.sh` a
   `main` como archivo inerte. Menor esfuerzo, menor riesgo, valor operativo más claro.
2. **ARCHIVE_DOCS_ONLY** (#2, #3-docs, #5) — 3 lotes de docs a `docs/archive/` o `docs/ops/`, cada
   uno con encabezado de supersesión citando qué lo reemplaza hoy en `main`. Se pueden bundlear en
   un solo PR docs-only si David lo prefiere.
3. **DEFER_PRODUCT** (#3-skills + `config/teams.yaml`) — sin acción hasta GO de producto explícito
   sobre el "equipo build"; no forma parte de ningún pack de ejecución hasta entonces.
4. **KILL_BRANCH** (#1) — `git push --delete` de `codex/wip-granola-v2-snapshot-2026-04-30` (cubre
   también el contenido de `rick/windows-dirty-rescue-2026-04-27`, #58, sin acción propia sobre esa
   rama en este pack).

---

## 4. Prohibido (respetado)

- Cero `git checkout` de paths a `main` — toda lectura fue vía `git show`/`git ls-tree`/`git cat-file`
  sobre refs remotos, sin tocar el working tree.
- Cero `git push --delete`.
- Cero touch a VPS/Notion/registry live.
- Ningún archive/rescue/kill se ejecutó — solo evaluación con evidencia citada.
- Ninguna recomendación sin evidencia (contenido leído, grep contra `main`, o ausencia confirmada).

---

## 5. Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: se agrega
"cherry5 brief **DONE**" a la línea existente. Ejecución (RESCUE/ARCHIVE/KILL de las 5 filas) queda
`PENDING` GO de David por fila.
