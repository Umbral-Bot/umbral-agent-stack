# P1.3 — Evaluación WIP en clones hermanos (2026-08-07)

> **Pack:** PKG-UAS-P1-3-CLONE-WIP-EVAL · rama
> `claude/pkg-uas-p1-3-clone-wip-eval-20260807` · base `08667f0c`
> **GO de David (verbatim):** "go" — siguiente ítem del norte tras cierre P1.2 + housekeeping:
> P1.3 clones hermanos con WIP.
> **Alcance:** SOLO evaluación (`git status`/`diff`/`show`/`log`, comparación de contenido
> contra `origin/main`). Cero escritura, cero `git restore`/`clean`/`reset`/`stash`/`push` en los
> clones hermanos auditados. Ningún rescate se ejecutó en este pack.
> **Norte:** [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.3 ·
> SoT higiene previa: [uas-p1-2-housekeeping-pack-prs-20260807.md](uas-p1-2-housekeeping-pack-prs-20260807.md)

## 0. Resumen ejecutivo

Los dos clones hermanos con WIP declarado en el norte (`-copilot`, `-codex-coordinador`) fueron
auditados path por path contra el canónico `origin/main` (`08667f0c`, mismo HEAD del clone SYNC
de este pack). **Veredicto uniforme: los 14 paths evaluados con contenido real son
`DISCARD_SAFE`** — todo su WIP quedó subsumido por rescates y decisiones de arquitectura
posteriores ya mergeados a main (principalmente `PKG-UAS-P1-2-ORPHAN-RESCUE1` / PR #592 y
`PKG-UAS-P1-2-KEEP2-RESCUE-PS1` / PR #595, más una serie de rescates editoriales previos de
2026-05-30 y el rediseño de Fase 2/ADR-010 de HITL editorial). No se encontró ningún path apto
para `RESCUE_SELECTIVE`. El resto de artefactos (`graphify-out/`, `.png` sueltos,
`.playwright-mcp/`) son output/capturas de test regenerables, también `DISCARD_SAFE`.

**No se ejecuta ningún KILL/discard en este pack** — es evaluación pura. La ejecución (limpiar
working tree de ambos clones) queda pendiente de GO explícito de David, como exige el norte.

## 1. Clone A — `C:\GitHub\umbral-agent-stack-copilot`

| Campo | Valor |
|---|---|
| Branch | `main` |
| Ahead/behind real vs `origin/main` (tras `fetch`) | 0 / 86 (snapshot previo decía ~21 — desactualizado) |
| Merge-base | `82a314f7` = HEAD local exacto → ancestro lineal limpio, sin historia disjunta |
| Stash / worktrees | 4 stashes viejos sin relación (fuera de alcance), 1 worktree (el propio clone) |

| Path | Clasificación | Evidencia [E] |
|---|---|---|
| `docs/15-model-quota-policy.md` (modified) | **DISCARD_SAFE** | Diff local = mismo hunk, mismos blob hash `cf4e195..058ff17`, que el commit `193a579e` (PR #592, rama `rescue/copilot-dirty-2026-07-13`) ya aplicó a main. SHA256 del archivo completo idéntico entre clone y main: `cf9b0168…` |
| `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` (untracked) | **DISCARD_SAFE** | SHA256 de archivo completo idéntico a main (`2f2c000c…`), agregado por el mismo commit `193a579e` |
| `graphify-out/` (untracked, ~63 MB) | **DISCARD_SAFE** | Output generado de un análisis de grafo (timestamps de una sola corrida 2026-07-04), regenerable, sin valor de archivo |

El atraso de 86 commits no afecta la validez: la comparación fue por hash de archivo completo
contra el contenido final de main, no por diff relativo a una base vieja.

## 2. Clone B — `C:\GitHub\umbral-agent-stack-codex-coordinador`

| Campo | Valor |
|---|---|
| Branch | `codex/editorial-linkedin-smoke-rescue` |
| Ahead/behind real vs `origin/main` | 0 / 267 (coincide con snapshot previo) |
| Merge-base | `46aa07c3` = HEAD local exacto → ancestro lineal limpio, sin historia disjunta |
| Stash / worktrees | 4 stashes sin relación, 13 worktrees preexistentes conocidos (sin novedades) |

| Path | Clasificación | Evidencia [E] |
|---|---|---|
| `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md` | **DISCARD_SAFE** | Adiciones locales (calibración de voz, "Length and cadence") ya verbatim en main líneas 144-165. Main además tiene, ausente en local: sección `## Gerencia — Comunicación (O15 Ola 3 semilla)` y `Model preference` que exige `azure-openai-responses/gpt-5.5` vía `config/editorial-model.yaml`. Overwrite con la versión local sería **regresión de producción** |
| `openclaw/workspace-agent-overrides/rick-qa/ROLE.md` | **DISCARD_SAFE** | Adiciones locales (blacklist consultoría, reglas de longitud) ya verbatim en main líneas 160-162. Main tiene además, ausente en local: `## Gerencia — Mejora Continua (O15 Ola 2)`, QA estructural V1 (`arco_narrativo`/`estructura_discurso`/verdicts `blocked_*`), enforcement de benchmark C1, y `Model preference` GPT-5.5 obligatorio con "Forbidden silent fallback". **Mismo veredicto: inferior a main actual** |
| `.../director-comunicacion-umbral/CALIBRATION.md` | **DISCARD_SAFE** | CAL-005/006/007 locales = CAL-008/009/010 en main; main trae nota explícita "rescate coordinador 2026-05-30" — este mismo contenido ya fue rescatado antes |
| `.../director-comunicacion-umbral/SKILL.md`, `.../linkedin-content/SKILL.md`, `.../linkedin-david/SKILL.md` | **DISCARD_SAFE** (×3) | Todas las secciones añadidas localmente presentes verbatim en main (confirmado por grep de las cadenas añadidas) |
| `docs/ops/editorial-agent-flow.md` | **DISCARD_SAFE** | Las 6 líneas añadidas localmente presentes verbatim en main (líneas 118, 178) |
| `evals/editorial/gold-set-minimum.yaml` | **DISCARD_SAFE** | Casos `ED-GOLD-011`/`012` añadidos localmente ya existen en main con id y contenido idéntico |
| `docs/ops/editorial-linkedin-quality-smoke-tests.md` (untracked) | **DISCARD_SAFE** | Diff mínimo — main solo agrega una sección `## Related`, resto idéntico |
| `docs/ops/editorial-publicaciones-human-review-contract.md` (untracked) | **DISCARD_SAFE (superseded)** | Versión local = DRAFT `M2-WIN-01` de 2026-06-01 (`M2_WIN01_SPEC_DRAFT_READY`). Main tiene reescritura completa posterior ligada a `ADR-010-azure-editorial-blog-cms.md`, al contrato norte `editorial-norte-hitl-contract-2026-07-22.md` §5.I y a la decisión "Fila I = B". La versión local está **superada por decisiones de arquitectura posteriores** |
| `.agents/tasks/2026-07-12-001-copilot-openclaw-oauth-only-urgent.md` (untracked) | **DISCARD_SAFE** | Diff contra canónico: 0 líneas — byte-idéntico |
| `scripts/export-vscode-config.ps1` (untracked) | **DISCARD_SAFE** | Versión **pre-fix**: usa `Join-String -Separator` (bug PS 5.1 corregido en main por `-join`, PR #595) y **no** trae la advertencia de fuga de secretos en `mcp.json` que PR #595 agregó. Resto del archivo (249/251 líneas) idéntico — sin contenido único, subsumida y mejorada |
| 4× `.png` (`p10f-ifc-after-final`, `pkg5a-admin-icons-unauth`, `pkg5a-chat-unauth`, `pkg5a-noticias-public`) + `.playwright-mcp/` | **DISCARD_SAFE** | Capturas/logs de smoke Playwright de junio 2026, artefactos de test run, sin valor de código/doc (no evaluados en profundidad por instrucción del pack) |

El merge-base limpio (HEAD == merge-base, sin historia disjunta) hace que el "267 behind" sea
señal confiable de staleness real, no de historias inconexas — sin riesgo de falso positivo. El
veredicto uniforme `DISCARD_SAFE` es resultado directo de la comparación de contenido, no un
artefacto del atraso.

## 3. Orden sugerido de ejecución (pendiente de GO — fuera de este pack)

No hay fila `RESCUE_SELECTIVE`, por lo que no hay orden de rescate que priorizar. El único
trabajo pendiente es **discard/limpieza** de working tree en ambos clones, sin urgencia técnica
(nada se pierde: todo el contenido de valor ya vive en `main`):

1. **Clone A** (`-copilot`): descartar `docs/15-model-quota-policy.md` (modified),
   `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` y `graphify-out/`
   (untracked). Acción trivial — `git restore` del tracked + borrar los dos untracked/directorio.
2. **Clone B** (`-codex-coordinador`): descartar los 8 tracked modificados vía
   `git restore`/`git checkout --` y los untracked (3 docs de contenido + `.ps1` + 4 `.png` +
   `.playwright-mcp/`). **Atención:** confirmar antes de limpiar que ningún proceso local
   (smoke Playwright en curso, sesión de Codex activa) depende de ese working tree.

**Ninguna de estas dos limpiezas se ejecutó en este pack** — requieren GO explícito de David
por clone, y tocar `git restore`/`clean` en un clone hermano está fuera del alcance permitido
aquí (`Prohibido git restore / clean / reset / stash drop en los clones hermanos auditados`).

## 4. Exclusiones / fuera de alcance

- `umbral-bot-copilot` (otro repo) — explícitamente fuera de P1.3 UAS.
- Ramas locales `feat/copilot-*`/`copilot/*` del clone A y los 13 worktrees Codex/Cursor del
  clone B — no forman parte del pedido (solo working tree de la rama activa de cada clone).
- Stashes preexistentes en ambos clones (4 c/u) — sin relación con este pack, no tocados.
- VPS/Notion/OpenClaw live — no se tocó nada en vivo; toda la comparación fue contra el
  contenido de `main` en el repo canónico local.

## 5. Gate

`UAS_P13_CLONE_WIP_EVAL_PASS = Y` — inventario completo de ambos clones con clasificación y
evidencia por path. 0 acciones destructivas ejecutadas.
