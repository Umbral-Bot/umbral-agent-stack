# P1.2 — Ejecución compuesta filas CHERRY 2–5 + KILL #58 (2026-08-07)

> **Pack:** PKG-UAS-P1-2-ORPHAN58-CHERRY25-EXEC · rama
> `claude/pkg-uas-p1-2-orphan58-cherry25-exec-20260807` · base `72c344c7`
> **GO de David (verbatim):** "acepta las recomendaciones del orquestador — ejecución compuesta
> filas CHERRY 2–5 + KILL #58."
> **SoT:** [uas-p1-2-orphan58-cherry5-20260807.md](uas-p1-2-orphan58-cherry5-20260807.md),
> [uas-p1-2-orphan58-cherry1-kill-20260807.md](uas-p1-2-orphan58-cherry1-kill-20260807.md),
> [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2.

## 0. Resultado en una línea por fila

| Fila | Rama | Acción | Estado |
|---|---|---|---|
| 4 | `rick/test-github-mvp-smoke` (hook) | RESCUE_SELECTIVE | **STOP parcial** — ver §1 |
| 2 | `rick/editorial-linkedin-writer-flow` | ARCHIVE_DOCS_ONLY (21 paths) | **DONE** + rama **KILL** |
| 3 | `antigravity/sync-uncommitted-changes` | ARCHIVE (3 docs) + DEFER (5 skills + teams.yaml) | **DONE** + rama **KILL** |
| 5 | `codex/notion-governance-v1-contract` | ARCHIVE_DOCS_ONLY (6 paths + README pivote) | **DONE** + rama **KILL** |
| 58 | `rick/windows-dirty-rescue-2026-04-27` | KILL directo (subsumida por fila 1, ya ejecutada en pack previo) | **DONE** |

Reconfirmación previa a tocar nada: los 5 tips coinciden exactamente con los esperados por el pack
y ninguno tiene merge-base con `origin/main` (`git merge-base` exit 1 en las 5).

---

## 1. Fila 4 — STOP parcial (hallazgo nuevo, no ejecutado)

**Qué se intentó:** `git show 9d983463:.claude/hooks/block-deployed-repo-writes.sh` → mismo path en
la rama de trabajo. El archivo se copió byte-idéntico (79 líneas, confirmado por diff directo).

**Por qué se detuvo:** `git add` reportó el path como **ignorado por `.gitignore`**:

```
.gitignore:78:.claude/hooks/block-deployed-repo-writes.sh
```

Contexto del `.gitignore` (líneas 72–80, sin tocar en este pack):

```
# === VPS local-only surfaces ===
# These files exist on the VPS but are not part of the canonical shared repo.
# .claude/ y .agents/ contienen config de sesión de Claude Code y hooks que
# difieren por entorno. El audit snapshot es data generada en runtime.
.claude/CLAUDE.md
.claude/settings.json
.claude/hooks/block-deployed-repo-writes.sh
.agents/board.md
docs/audits/notion-curation-snapshot-2026-03-16.json
```

Esto es evidencia **nueva**, no disponible cuando el acta CHERRY5 evaluó esta fila como "bajo
riesgo, archivo inerte": `main` excluye explícitamente este path exacto por diseño, con el mismo
razonamiento que ya encontró el agente evaluador de la fila 4 — el hook depende de rutas VPS
hardcodeadas (`/home/rick/umbral-agent-stack` vs `-main-clean`) y "difiere por entorno". Forzar el
tracking con `git add -f` habría contradicho una política deliberada del repo sin GO explícito, así
que se detuvo ahí: **el archivo no quedó trackeado, se removió del working tree** (quedó solo
ignorado, sin riesgo de commit accidental).

**Consecuencia en cascada:** dado que la regla del pack ata los deletes de §E a "A–D commiteados", y
A no se completó, **`rick/test-github-mvp-smoke` no se borró** — sigue viva en origin @ `9d98346325e870628773fe132ff5859f5e456e15`,
a la espera de decisión de David (ver TU TURNO en el REPORT).

---

## 2. Fila 2 — `rick/editorial-linkedin-writer-flow` → ARCHIVE_DOCS_ONLY

21 paths reconfirmados por `git ls-tree` (coincide exacto con la allowlist del pack) copiados a
`docs/archive/editorial-linkedin-writer-flow-2026-05/`, preservando subpaths relativos. Cada
archivo lleva un encabezado insertado:
- Después del `# H1` para los 18 archivos Markdown con encabezado plano.
- Después del cierre del front-matter YAML (segundo `---`) para `SKILL.md`.

Texto del encabezado: *"SUPERSEDED / HISTÓRICO — no runtime; reemplazado por
`openclaw/workspace-agent-overrides/rick-linkedin-writer/` (PAUSED) +
`docs/editorial-pipeline/production-flow-v2-2026-06-06.md` + `linkedin-david`."*

No se escribió nada en `openclaw/workspace-templates/skills/linkedin-post-writer/` ni se tocó el
override `rick-linkedin-writer/` real de `main` (confirmado: `git diff --cached --stat` sobre esos
dos paths, vacío).

Rama borrada tras confirmar cero PR abierto (`gh pr list --state open --search "head:..."` → `[]`).

---

## 3. Fila 3 — `antigravity/sync-uncommitted-changes` → ARCHIVE + DEFER

**Archivados** (3, `docs/archive/codegen-team-design-2026-04/`, encabezado *"SUPERSEDED /
HISTÓRICO — diseño no implementado; handlers `code.*` y Worker Linux `:8089` ausentes en `main`"*):
`docs/architecture/06-codegen-team-design.md`, `docs/roadmap/codegen-rollout-phases.md`,
`runbooks/runbook-codegen-fase1-smoke.md`.

**Diferidos** (6, `docs/archive/deferred-codegen-team-2026-04/`, encabezado *"DEFERRED_PRODUCT — no
cablear a Rick/templates hasta GO de producto explícito"*): los 5 `SKILL.md` de
`code-architect/debugger/implementer/reviewer/scribe` (renombrados `<skill>-SKILL.md` para evitar
looks-like-live en un directorio plano) + `config/teams.yaml` del tip, guardado como
`teams-build-deferred.yaml` con el mismo encabezado en formato comentario YAML.

`config/teams.yaml` de `main` **no se tocó** — confirmado (`git status --porcelain -- config/teams.yaml`
vacío antes y después del commit).

Rama borrada tras confirmar cero PR abierto.

---

## 4. Fila 5 — `codex/notion-governance-v1-contract` → ARCHIVE_DOCS_ONLY

6 paths a `docs/archive/notion-governance-v1-2026-03/`, preservando subpaths (`docs/adr/`,
`docs/architecture/`, `docs/policies/` x2, `registry/` x2). Encabezado *"SUPERSEDED — V1
descartado; vigente: `.claude/skills/notion-governance-runtime/SKILL.md` +
`docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md`"* insertado después del H1 (4
archivos Markdown) o como comentario YAML al inicio (2 archivos `.yaml`, que no tenían H1 ni
front-matter delimitado).

README del pivote: [uas-p1-2-orphan58-notion-gov-v1-superseded-20260807.md](uas-p1-2-orphan58-notion-gov-v1-superseded-20260807.md)
(18 líneas de cuerpo) explica qué proponía V1, por qué el slot `ADR-005` de `main` es una
coincidencia de número (no una renumeración) y por qué V2 (`granola-capitalization-hybrid-plan-2026-07-16.md`
+ skill `notion-governance-runtime`) cubre el mismo terreno con arquitectura distinta.

**Confirmado:** no se creó `docs/policies/`, `registry/` ni `docs/adr/ADR-005-*` en ninguna
superficie activa de `main` — todo vive exclusivamente bajo `docs/archive/notion-governance-v1-2026-03/`
(`git status --porcelain | grep -v docs/archive` → vacío para esos patrones).

Rama borrada tras confirmar cero PR abierto.

---

## 5. Fila 58 — `rick/windows-dirty-rescue-2026-04-27` → KILL

Subsumida por contenido en la fila 1 (`codex/wip-granola-v2-snapshot-2026-04-30`), ya borrada en
`PKG-UAS-P1-2-ORPHAN58-CHERRY1-KILL` (2026-08-07). GO de David en este pack autorizó explícitamente
el KILL de #58 (a diferencia del pack anterior, que la protegía hasta nuevo GO). Cero PR abierto
confirmado, `git push origin --delete` ejecutado.

---

## 6. Post-check consolidado

```
Borradas (4, confirmado ls-remote vacío):
rick/editorial-linkedin-writer-flow
antigravity/sync-uncommitted-changes
codex/notion-governance-v1-contract
rick/windows-dirty-rescue-2026-04-27

NO borrada (STOP parcial fila 4, sigue viva):
rick/test-github-mvp-smoke               9d983463

FOSSIL restantes (vivas, sin tocar, sin acción en este pack):
cursor/power-bi-libraries-formats-5c1b   6a64515c
cursor/regression-test-coverage-b904     de318aff
feat/bitacora-populate                   fe5d3393

Sin relación, verificadas sin tocar:
#541 OPEN (claude/plan-sys-diag-openclaw-worksystem-2026-07-17)
#521 OPEN (copilot/docs-openclaw-models-hygiene-20260704)
```

## 7. Prohibido (respetado)

- Cero wire del hook en `settings.json` — ni siquiera se llegó a esa decisión, el archivo no quedó
  trackeado.
- Cero merge de skills `code-*` o `linkedin-post-writer` a templates vivos.
- Cero pisado del override `rick-linkedin-writer/` real de `main`.
- Cero pisado de `config/teams.yaml` de `main`.
- Cero KILL de FOSSIL distintos de #58 (Power BI, regression-b904, bitacora-populate intactas).
- Cero touch a VPS/Notion/registry live fuera del archive.

## 8. Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: filas 2/3/5 +
#58 → **EXEC DONE**. Fila 4 → **STOP parcial**, hook no rescatado por conflicto con `.gitignore` de
`main`, rama fuente `rick/test-github-mvp-smoke` sigue viva a la espera de decisión de David.
