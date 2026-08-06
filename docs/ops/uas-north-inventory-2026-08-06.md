# Inventario para el norte único — UAS (2026-08-06)

> **Pack:** PKG-UAS-NORTH-INVENTORY · rama `claude/pkg-uas-north-inventory-20260806` · base `0c666350`
> **Modo:** SOLO inventario + propuesta. Cero deletes, cero cierres de PR/rama/worktree,
> cero escritura en Notion, VPS o registry de skills.
> **Estado:** este documento **no es** el norte. Es el inventario que permite escribirlo
> y la propuesta de dónde vivirá. La ejecución de cierres es otro pack, tras GO.
>
> **→ El norte ya existe: [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md)**
> (PKG-UAS-NORTH-CANON-DRAFT, 2026-08-06). Este inventario queda como su evidencia:
> las tablas A–D y la cola de cierre §8 siguen vigentes y no se reabren aquí.

## 0. Método, y qué NO está verificado aquí

**Verificado en esta sesión** (comando + salida, superficie `código`/`git`/`gh`):

| Dato | Valor | Cómo |
|---|---|---|
| Tip `origin/main` | `0c666350` (2026-08-06) | `git log -1 --oneline origin/main` |
| PRs OPEN en el repo | **2** — [#541](https://github.com/Umbral-Bot/umbral-agent-stack/pull/541), [#521](https://github.com/Umbral-Bot/umbral-agent-stack/pull/521) | `gh pr list --state open --limit 100` |
| Refs en `origin` | 279 | `git for-each-ref refs/remotes/origin/ \| wc -l` |
| Ramas en los 4 prefijos del pack | 119 | `git for-each-ref` sobre `claude/*`, `copilot/*`+`copilot-vps/*`, `codex/*`, `feat/editorial-*`+`docs/editorial-*` |
| Docs en `docs/ops` / `docs/audits` | 182 / 148 | `git ls-tree -r --name-only origin/main` |
| `.agents/board.md` último commit | **2026-07-14** (`71e6fdc4`) → 23 días stale | `git log -1 -- .agents/board.md` |

**Entrada del paquete, NO re-verificada aquí** (el pack lo declara cerrado y prohíbe
re-diagnosticar): `OPENCLAW_OPENAI_AUTH_PASS=Y` y `OPENCLAW_AUTH_ORDER_PASS=Y`
(device login 2026-08-06; override `openai:david.a.moreira.m@gmail.com` por delante de
`openai:umbral-rick`; zombi `umbral-rick` sigue en el store, detrás, sin borrar). Este
inventario los toma como dados y no ejecutó ninguna sonda contra la VPS.

**Límite honesto de la Tabla A**: leí completos 3 documentos (los de "lectura mínima"
del pack) y usé fecha de último commit + pertenencia a frente para el resto. **El
veredicto de la Tabla A es por familia, no por archivo.** Un archivo dentro de una
familia marcada `ARCHIVAR` puede ser canónico y no lo sabría sin abrirlo. Por eso la
cola de cierre (§8) no propone borrar ni un solo doc: propone *marcar*, que es
reversible.

### Corrección a la memoria de sesión (dato consumido que estaba mal)

`MEMORY.md` de Claude registraba como **OPEN** tres PRs que hoy están **MERGED**.
Se corrige aquí porque el orquestador ya consumió ese dato:

| PR | Estado en memoria | Estado real (`gh pr view`) |
|---|---|---|
| #555 (Magnific P2.2) | "OPEN, no merge, bloqueado por API key" | **MERGED** 2026-07-23T14:37:48Z |
| #565 (n8n N0/N1/N3-lite) | "OPEN, espera GO de activación" | **MERGED** 2026-07-24T07:40:32Z |
| #572 (PKG-OPS-RESUME-A1) | "OPEN" | **MERGED** 2026-08-02T05:11:58Z |

Nada en este pack dependía de que estuvieran abiertos. El patrón sí importa y va al
norte: **la memoria de sesión envejece más rápido que el repo**, y por eso el estado
de PRs se lee con `gh`, no de memoria.

---

## 1. Tabla A — documentación (docs/ops + docs/audits + roadmap/diag/hygiene)

### A.1 — Los CANÓNICOS (lo que el norte debe citar y mantener vivo)

Estos 12 son los únicos que este inventario propone tratar como fuente vigente.
Todo lo demás es histórico o incierto.

| Doc | Frente | Veredicto | Por qué |
|---|---|---|---|
| [ops-resume-reentry-2026-08-02.md](ops-resume-reentry-2026-08-02.md) | Ops / reingreso | **CANONICO** | Es el contrato de cómo se retoma tras pausa; define ledger JSONL como SoT y por qué todo board estático se pudre |
| [user-e2e-tester-system-plan-2026-08-01.md](user-e2e-tester-system-plan-2026-08-01.md) | Tester E2E | **CANONICO** | Contrato del rol (15 prohibiciones, §3.4 criterios de GO) |
| [user-e2e-tester-playbook-2026-08-02.md](user-e2e-tester-playbook-2026-08-02.md) | Tester E2E | **CANONICO** | Suites, oráculos y ventanas; superó al plan en detalle operativo (P3-01..04) |
| [user-e2e-p4-retro-decision-2026-08-04.md](user-e2e-p4-retro-decision-2026-08-04.md) | Tester E2E | **CANONICO** | Evaluación §3.4: criterio 1 PARCIAL → recomienda **diferir** el GO de capitalización |
| [user-e2e-p3-02-calendar-2026-08-05.md](user-e2e-p3-02-calendar-2026-08-05.md) | Tester E2E | **CANONICO** | Última corrida: **BLOCKED** por login de modelo expirado en gateway (el incidente que este pack cerró) |
| [diag-rick-frescura-2026-08-01.md](diag-rick-frescura-2026-08-01.md) | Runtime Rick | **CANONICO** | Línea base de frescura + 7 fixes priorizados, ninguno aplicado. Su fix #7 nombra el `umbral-tournament-github` stale que el pack deja pendiente |
| [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md) | Editorial | **CANONICO** | Brecha norte vs actual (9 PARCIAL / D AUSENTE / I CONTRATO_OPUESTO) |
| [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) | Editorial | **CANONICO** | Contrato del norte editorial mergeado en #550 |
| [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) | Editorial | **CANONICO** | Roadmap P1–P3 del frente hoy en standby |
| [uas-main-clone-sanitize-2026-07-23.md](uas-main-clone-sanitize-2026-07-23.md) | Higiene | **CANONICO** | Define el clone canónico y la política tras la sanitización de 117 ramas |
| [worktree-hygiene-editorial-2026-07-22.md](worktree-hygiene-editorial-2026-07-22.md) | Higiene | **CANONICO** | Precedente directo de la Tabla D de este doc |
| [docs/operations/README.md](../operations/README.md) | Ops / ledger | **CANONICO** | Spec del schema del ledger + clasificación terminal/abierto |

### A.2 — Familias (veredicto de familia, no de archivo)

`docs/ops` — 182 archivos:

| Familia | # | Veredicto | Razón |
|---|---|---|---|
| `user-e2e-*` | 9 | **CANONICO** | Frente vivo; ver A.1. Los `p1/p2/p3-01` son evidencia de corrida, no contrato — canónicos como `[E]`, no como norte |
| `editorial-*` | 21 | **SUPERSEDIDO** (salvo los 3 de A.1) | 18 de 21 son actas P21–P28 de julio; el frente está en standby y su contrato vive en los 3 canónicos |
| `cand-*` | 43 | **ARCHIVAR** | Payloads/QA de CAND-001/002/003 (abr–jul). Valor histórico; ninguno es contrato. **Excepción**: la anomalía CAND-001 sigue viva como hallazgo (P4 §5.5) — el hallazgo es lo vigente, no el doc |
| `pit-*` (+ `evidence-imports/`) | 31 | **ARCHIVAR** | Torneo PIT; `pit-tournaments-archived-2026-07-22.md` ya declara el cierre del frente |
| `MEGAPROMPT-*` | 12 | **ARCHIVAR** | Prompts de un solo uso ya ejecutados |
| `notion-*` | 10 | **INCIERTO** | Mezcla schema vigente (`notion-publicaciones-*`) con auditorías puntuales. Requiere lectura antes de mover |
| `chatgpt-openclaw-agent-architect/` | 9 | **ARCHIVAR** | Kit de un agente externo que no está en el circuito actual |
| `olas-numeradas` (`d3/d35/d36/d53/o8/o15/q2`) | 8 | **ARCHIVAR** | Charters de olas cerradas (may–jun) |
| `n8n-*` | 2 | **CANONICO** | B1/B3 ACTIVOS en VPS con bot TEST desde 2026-07-25 — frente vivo, no dormido |
| `graphify-*`, `rick-*`, `tournament-*`, sueltos | ~37 | **INCIERTO** | Mezcla runbooks vigentes (`registry-backup-alert-runbook`, `sync-skills-adapters-runbook`, `gd52-reoauth-runbook`) con actas cerradas |

`docs/audits` — 148 archivos:

| Familia | # | Veredicto | Razón |
|---|---|---|---|
| Fechados 2026-03 → 2026-06 | 25 | **ARCHIVAR** | Auditorías puntuales cerradas |
| `openclaw-*` | 21 | **INCIERTO** | Incluye la matriz de migración de modelos (`data/openclaw-model-migration-matrix-2026-07-13.yaml`), que puede seguir siendo insumo del frente auth |
| `workspace-hygiene-*` (2 dirs) | 16 | **SUPERSEDIDO** | Superados por `uas-main-clone-sanitize-2026-07-23.md` y por este doc |
| `notion-*` | 13 | **ARCHIVAR** | Fixes de marzo ya aplicados |
| `granola-*` | 8 | **ARCHIVAR** | Frente cerrado (95/95 ingestados, 0 FAIL) |
| `rick-*` (live tests marzo) | ~14 | **ARCHIVAR** | Superados por `diag-rick-frescura-2026-08-01.md` |
| `codebase-audit-2026-03/`, `super-diagnostico-*` | 8 | **ARCHIVAR** | Marzo; superados por el sys-diag de #541 (que sigue OPEN) |
| Resto (vm/vps/misc) | ~43 | **INCIERTO** | Sin lectura no se distingue runbook vivo de acta |

`*roadmap*` / `*diag*` / `*hygiene*` fuera de esos dos árboles:

| Doc | Veredicto | Razón |
|---|---|---|
| `docs/11-roadmap-next-steps.md` | **INCIERTO** | Nombre de roadmap raíz; si está stale es exactamente el anti-patrón que este pack combate — leer antes de citar |
| `docs/copilot-cli-autonomy-vision-roadmap.md` | **SUPERSEDIDO** | Visión Copilot-CLI; el circuito actual no lo usa |
| `docs/roadmaps/*` (2) | **ARCHIVAR** | Capitalizaciones de Perplexity (abril) |
| `docs/40/41-hackathon-*` | **ARCHIVAR** | Marzo |
| `runbooks/runbook-vm-*-diagnosis.md` (2) | **INCIERTO** | Runbooks de VM; la VM sigue existiendo (679 pairings fallidos/día) |
| `reports/copilot-cli/f8*` (2), `scripts/*diagnos*` (3) | **ARCHIVAR** | Evidencia y utilidades de frentes cerrados |
| `infra/diagrams/architecture.mmd` | **INCIERTO** | Si refleja la topología real es canónico; si no, es deuda visible |

---

## 2. Tabla B — PRs OPEN

Solo hay **2**. Ambos docs-only, ambos `MERGEABLE`, ambos sin conflictos.

| PR | Rama | Título | Abierto | Últ. act. | Δ | Veredicto | Fundamento |
|---|---|---|---|---|---|---|---|
| **[#541](https://github.com/Umbral-Bot/umbral-agent-stack/pull/541)** | `claude/plan-sys-diag-openclaw-worksystem-2026-07-17` | sys-diag total OpenClaw × work system — plan + inventario + 10 prompts multi-IA (solo docs) | **2026-07-17** (20 días) | 2026-07-27 | +2692 / −0 | **MERGE** | Es el caso testigo del anti-dorm: docs puros, sin conflicto, esperando respuestas multi-IA de David que nunca llegaron. Su contenido (inventario + prompts) es insumo directo del norte. Mergearlo no compromete nada — es adición pura — y saca el frente del limbo. Si David no piensa contestar los 10 prompts, el norte debe decirlo y el PR igual entra como registro |
| **[#521](https://github.com/Umbral-Bot/umbral-agent-stack/pull/521)** | `copilot/docs-openclaw-models-hygiene-20260704` | docs(openclaw): per-agent `models.json` hygiene | 2026-07-04 (33 días) | 2026-07-04 | +104 / −0 | **ESPERAR** → releer en el pack de ejecución | Toca justo el dominio que este pack acaba de mover (orden de auth por agente). Mergear un doc de higiene de modelos **escrito antes** del incidente del 2026-08-06 puede consagrar guía obsoleta. Decisión: releerlo contra los 5 aprendizajes de §7 y, o bien mergear con addendum, o cerrarlo por superado. **No mergear a ciegas** |

Ninguno se cierra ni se mergea en este pack.

---

## 3. Tabla C — ramas en origin

### C.1 — El hallazgo que cambia el criterio

**Estar "ahead" de main NO significa tener trabajo sin integrar.** El repo usa
squash-merge: la rama conserva sus commits originales y queda ahead aunque su
contenido esté 100% en main. Verificado con dos casos duros:

- `feat/editorial-magnific-5-alts` → `AHEAD+1`, pero su PR **#555 está MERGED**.
- `docs/editorial-p0-norte-contract` → `AHEAD+2`, pero su PR **#550 está MERGED**.

Un barrido que use "ahead ≠ 0" como criterio de rescate reabriría 70 ramas ya
integradas. El criterio correcto es **¿existe un PR mergeado con esa `headRefName`?**

### C.2 — Clasificación de las 119 ramas

| Clase | # | Veredicto | Acción propuesta (post-GO, otro pack) |
|---|---|---|---|
| Con PR **MERGED**, contenido ya en main (`ahead=0`) | 17 | **MERGE-OR-KILL → KILL** | Borrado de rama remota, sin inventario adicional: no hay nada que perder |
| Con PR **MERGED**, `ahead>0` por squash | 70 | **MERGE-OR-KILL → KILL** | Igual que arriba. El "ahead" es artefacto del squash, no trabajo vivo |
| Sin PR mergeado, con **PR OPEN** | 2 | **KEEP** | `claude/plan-sys-diag-…` (#541) y `copilot/docs-openclaw-models-hygiene-…` (#521) — su destino lo decide la Tabla B |
| Sin PR mergeado ni abierto | **30** | **INCIERTO** | Ver C.3: requieren `git diff origin/main…rama` antes de cualquier decisión |

Desglose por prefijo (total / con PR mergeado / huérfanas):

| Prefijo | Total | PR mergeado | PR open | Huérfanas |
|---|---|---|---|---|
| `claude/*` | 19 | 17 | 1 | 1 |
| `copilot/*` + `copilot-vps/*` | 43 | 26 | 1 | 16 |
| `codex/*` | 46 | 33 | 0 | 13 |
| `feat/editorial-*` + `docs/editorial-*` | 11 | 11 | 0 | 0 |

El frente editorial está **limpio**: sus 11 ramas tienen PR mergeado. La percepción de
"muchas `feat/editorial-*` huérfanas" del brief anti-dorm es, con el dato en mano,
**incorrecta** — están ahead por squash, no abandonadas.

### C.3 — Las 30 huérfanas reales (sin PR, ordenadas por antigüedad)

Dos grupos, con riesgo muy distinto:

**Grupo 1 — divergencia enorme (`ahead` de 3 y 4 cifras): 13 ramas.** Abril–mayo,
`+410` a `+959` commits sobre main. Ese número no es trabajo propio: es que se
ramificaron de un main viejo y nunca se rebasearon. Su contenido propio puede ser
mínimo o nulo. **INCIERTO — nunca `KILL` sin `git diff origin/main...rama` primero.**

| Fecha | Rama | ahead |
|---|---|---|
| 2026-05-05 | `copilot/feat-mission-control-o13-1` | +959 |
| 2026-04-22 | `codex/cand-001-notion-draft-flow` | +886 |
| 2026-04-22 | `codex/rick-qa-cand-001-validation` | +885 |
| 2026-04-22 | `codex/notion-publicaciones-setup-runbook` | +871 |
| 2026-04-22 | `codex/editorial-stack-final-readiness-qa` | +847 |
| 2026-04-22 | `codex/editorial-pr-stack-coordination-qa` | +847 |
| 2026-04-13 | `codex/granola-raw-intake-batch` | +701 |
| 2026-04-30 | `codex/wip-granola-v2-snapshot-2026-04-30` | +579 |
| 2026-04-10 | `copilot/analyze-agent-stack-infrastructure` | +692 |
| 2026-04-10 | `copilot/research-agent-stack-infrastructure` | +692 |
| 2026-04-07 | `codex/notion-v2-drift-cleanup` | +693 |
| 2026-03-31 | `codex/session-capitalizable-promotion-v1` | +693 |
| 2026-03-31 | `codex/notion-governance-v1-contract` | +690 |
| 2026-03-07 | `claude/audit-creator-tracking-TX9zV` | +410 |

**Grupo 2 — divergencia mínima (`+1` a `+3`): 16 ramas.** Mayo–julio. Aquí sí hay
1–3 commits propios que nunca se abrieron como PR. Es el candidato natural a
"rescatar o matar" en un solo barrido: leer el diff (es pequeño) y decidir.

| Fecha | Rama | ahead |
|---|---|---|
| 2026-07-04 | `copilot/docs-openclaw-models-hygiene-20260704` | +1 *(tiene PR #521 OPEN — va en Tabla B, no aquí)* |
| 2026-06-20 | `codex/docs-pit-v2-contract` | +1 |
| 2026-06-06 | `codex/cand-prod001-stage2` | +2 |
| 2026-05-14 | `copilot/feat-o16-2-047-gap-closure` | +2 |
| 2026-05-08 | `copilot/feat-s10-publish-guard` | +3 |
| 2026-05-08 | `copilot/feat-s0-s1-discovery` | +3 |
| 2026-05-08 | `copilot/feat-s2-source-verification` | +2 |
| 2026-05-08 | `copilot/docs-notion-schema-gates` | +2 |
| 2026-05-08 | `copilot/docs-s6-s7-multiplatform-design` | +1 |
| 2026-05-08 | `copilot/docs-editorial-master-plan` | +1 |
| 2026-05-08 | `copilot-vps/052-aeco-kb-pushed-visibility-manual` | +1 |
| 2026-05-08 | `copilot-vps/052-aeco-kb-build-blocked-pat-scope` | +1 |
| 2026-05-06 | `copilot/feat-o16-infra-base` | +1 |
| 2026-05-06 | `copilot/burn-q2-o7-o9-delegates` | +1 |
| 2026-05-06 | `copilot-vps/stage4-013e-execution-2026-05-07` | +1 |
| 2026-05-06 | `copilot-vps/recover-post-force-push-2026-05-06` | +1 |
| 2026-02-26 | `copilot/create-umbral-agent-stack-repo` | +2 |

---

## 4. Tabla D — worktrees y clones hermanos

`git worktree list` en el clone canónico: **1 sola entrada** (`C:/GitHub/umbral-agent-stack`
@ `0c666350` [main]). Limpio — la sanitización de 2026-07-23 se sostiene.

Los hermanos son **clones independientes**, no worktrees de este repo. Ninguno se toca aquí.

| Ruta | Rama / HEAD | Estado | Veredicto | Fundamento |
|---|---|---|---|---|
| `C:\GitHub\umbral-agent-stack` | `main` @ `0c666350` | limpio (tras stash de higiene de este pack) | **KEEP** | Canónico |
| `C:\GitHub\umbral-agent-stack-claude` | `claude/pkg-ops-resume-a2-20260804` @ `df62cd5`, upstream **[gone]** | **limpio** | **REMOVE-CANDIDATE (seguro)** | PR #577 **MERGED** 2026-08-04. Verificado `git diff origin/main df62cd5`: el clone **no tiene nada que main no tenga** — main es superconjunto estricto (+1015 líneas). Cero riesgo de pérdida |
| `C:\GitHub\umbral-agent-stack-antigravity` | `antigravity/001-rick-recommendations` @ `6915f29` (2026-03-09) | limpio, sincronizado con su origin | **REMOVE-CANDIDATE (verificar antes)** | 5 meses sin tocar. La rama existe en origin, así que el contenido no se pierde al borrar el clone local — pero conviene confirmar que nadie la usa |
| `C:\GitHub\umbral-agent-stack-copilot` | `main` @ `82a314f`, **behind 21** | **DIRTY**: `M docs/15-model-quota-policy.md`, `?? docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md`, `?? graphify-out/` | **KEEP (bloqueado por WIP)** | Contiene un doc de auditoría **untracked** que no existe en main. Borrarlo perdería trabajo. Requiere rescate explícito antes de cualquier limpieza |
| `C:\GitHub\umbral-agent-stack-codex-coordinador` | `codex/editorial-linkedin-smoke-rescue` @ `46aa07c`, **behind 241** | **DIRTY**: 5 archivos modificados (`editorial-agent-flow.md`, `gold-set-minimum.yaml`, 2 `ROLE.md`, `CALIBRATION.md`) | **KEEP (bloqueado por WIP)** | Toca ROLE de `rick-communication-director` y `rick-qa` — superficie de runtime. Mismo caso citado en la memoria de higiene 2026-07-22 (Cursor worktrees dirty esperando a David) y sigue sin resolverse |
| `C:\GitHub\umbral-agent-stack-codex` | detached `47ffcae` | detached | **INCIERTO** | HEAD suelto sin rama; hay que ver si `47ffcae` es alcanzable desde algún ref antes de tocarlo |
| `C:\GitHub\umbral-agent-stack-codex-pit-v2-contract` | `codex/docs-pit-v2-contract` @ `16e39b4` | **`prunable`** (marcado por git) | **REMOVE-CANDIDATE** | Git ya lo declara podable. La rama existe en origin (huérfana, +1 — ver C.3) |
| `C:\GitHub\umbral-agent-forge` | `main` @ `ea4a57f` + **2 worktrees** en `C:\GitHub\copilot-worktrees\` | untracked: `.playwright-mcp/`, `tmp/` | **KEEP** | Repo distinto (forge), fuera del alcance de este pack. Se registra solo para que el barrido no lo toque por error |
| `C:\Users\david\.codex\worktrees\**` | 26 entradas, 15 en detached `3b10d7e` | — | **REMOVE-CANDIDATE (masivo)** | 15 worktrees apuntan al **mismo** SHA detached: residuo de sesiones Codex. Más 8 con rama `codex/f8*` de mayo. Es el bulto de deuda más grande y el más barato de limpiar |
| `C:\Users\david\AppData\Local\Temp\pr269-worktree` | detached `b5641f9` | — | **REMOVE-CANDIDATE** | En `Temp`, de PR #269 |

**Resumen D:** 1 KEEP canónico · 2 KEEP bloqueados por WIP real (copilot, codex-coordinador)
· 4 REMOVE-CANDIDATE individuales · 1 REMOVE-CANDIDATE masivo (26 worktrees Codex) · 1 INCIERTO.

---

## 5. Propuesta — UN path norte

```
docs/ops/uas-north-canonical-2026-08-06.md
```

**Un solo archivo, en el repo, versionado.** No un board manual (`.agents/board.md` ya
demostró que se pudre: 23 días stale), no un dashboard Notion como fuente (Fase B está
diferida y la regla vigente es "Notion es espejo, nunca fuente" —
`ops-resume-reentry-2026-08-02.md` §5).

**Regla de mantenimiento propuesta, para que no se duerma como #541:** el norte se
reescribe entero cada vez que cambia, con fecha nueva en el nombre, y el anterior queda
como histórico. Nunca se parchea in-place. Un doc que nadie se atreve a reescribir es un
doc que ya murió.

### Outline propuesto

```markdown
# Norte canónico UAS — 2026-08-06

## 1. Estado runtime / auth              ← CERRADO 2026-08-06
   - OPENCLAW_OPENAI_AUTH_PASS=Y, OPENCLAW_AUTH_ORDER_PASS=Y
   - Zombi `openai:umbral-rick` en el store, detrás en el orden, sin borrar
   - DECISIÓN PENDIENTE DE DAVID → §6

## 2. Tester E2E de usuario              ← ACTIVO, con 1 gate abierto
   - P0/P1/P2/P3-01 PASS · P3-02 BLOCKED (login expirado — causa ya resuelta)
   - Criterio 1 de §3.4 = PARCIAL → GO de capitalización DIFERIDO (P4)
   - Próximo movimiento: re-correr P3-02 sobre el gateway re-autenticado

## 3. Editorial                          ← STANDBY DELIBERADO
   - Contrato del norte: editorial-norte-hitl-contract + gap-matrix
   - 11 ramas, todas con PR mergeado. El frente no está roto: está pausado
   - Fila I del gap-matrix sigue en CONTRATO_OPUESTO, sin resolver

## 4. Skills / registry                  ← ACTIVO
   - rick-runtime v0.3.0, skills-capitalize v0.1.8, cursor-orchestrator v0.8.0
   - Regla dura: `<slug>/references/`, nunca layout plano
   - `openclaw-vps-operator` vive fuera del registry (ver §5, deuda P1)

## 5. Deuda P0–P3
   P0 · Curar fechas del backlog Notion (20 tareas abiertas sin fecha)
        → es lo único que cambia lo que Rick le responde a David mañana
   P0 · Re-correr P3-02 (cierra el criterio 1 del tester)
   P1 · 30 ramas huérfanas + 26 worktrees Codex (cola §8)
   P1 · `openclaw-vps-operator` no está en el registry: 2 copias divergentes
        (`.claude/skills/` y `.agents/skills/`) sin un solo escritor
   P1 · 2 clones hermanos dirty con WIP sin rescatar (copilot, codex-coordinador)
   P2 · #541 en limbo 20 días · #521 posiblemente superado por el incidente de auth
   P2 · 330 docs en ops+audits sin marca de vigencia
   P3 · `.agents/board.md` stale 23 días — decidir: borrar o generar

## 6. Decisión abierta: fallback cross-provider
   - Hoy la cadena es 100% mono-provider (OpenAI): un incidente tumba los 3 modelos
   - Verificado a la fuerza el 2026-08-06
   - Opciones y costo → decisión de David, no del agente
   - Adyacente: `doctor --fix` + `plugins.entries.umbral-tournament-github` stale
     (ya nombrado como fix #7 en diag-rick-frescura-2026-08-01)

## 7. Anti-patrones (lo que este sistema ya demostró que falla)
   - Board estático mantenido a mano → se pudre (evidencia: board.md, dashboards Q2)
   - PR docs-only sin dueño ni fecha de caducidad → #541, 20 días
   - "ahead ≠ 0" leído como "trabajo sin integrar" → 70 falsos positivos
   - `models status` leído como verdad de auth → §7 de este inventario
   - Memoria de sesión como fuente de estado de PRs → 3 PRs mal registrados
   - Cadena mono-provider presentada como si tuviera fallback
```

---

## 6. Espejo Notion propuesto (NO creado)

| Campo | Propuesta |
|---|---|
| **Título** | `Norte UAS — estado canónico` |
| **Hub / ubicación** | Bajo **Control Room** (superficie runtime de Rick ya existente), como página hija — no como database nueva |
| **Naturaleza** | **Espejo de solo lectura.** La fuente es `docs/ops/uas-north-canonical-*.md` en el repo. Ante discrepancia, **manda el repo** |
| **Contenido** | Solo §1, §2, §3 y §6 del outline (estado + la decisión abierta). Las tablas de deuda y la cola de cierre **no** van a Notion: son operativas de repo y ahí se pudrirían |
| **Cadencia** | Se actualiza cuando se emite un norte nuevo. Sin sync automático en esta fase |
| **Por qué no ahora** | Fase B (vista humana en Notion) está **diferida** por decisión de David del 2026-08-02 (`GO_SPLIT_FASEADO`). Crear la página ahora contradiría esa decisión. Esta fila es una **propuesta para cuando Fase B se active** |

Cero llamadas a Notion en este pack.

---

## 7. Tabla skill propose — capitalización de la re-auth (2026-08-06)

**Cero escritura en el registry.** Esto es una propuesta para `skills-capitalize` en modo
`propose-only`; la escritura exige GO explícito y un pack aparte.

Contexto de destino verificado en disco:

- `umbral-rick-runtime` → **en el registry** (`C:\GitHub\umbral-skills-registry\skills\umbral-rick-runtime\`), con `references/reference-gates.md` y `references/reference-user-e2e.md`.
- `openclaw-vps-operator` → **NO está en el registry**. Existen dos copias en el repo UAS: `.claude/skills/openclaw-vps-operator/SKILL.md` (orientación Claude) y `.agents/skills/openclaw-vps-operator/SKILL.md` (declarada canónica por la propia copia Claude). **Eso es un duplicado sin un solo escritor** — y contradice el principio del commit `e9cba96` del registry ("un solo escritor del registry"). Es deuda P1 por sí misma.

| # | Aprendizaje (texto fuente, evidencia VPS 2026-08-06) | Destino propuesto | Clasificación | Fundamento |
|---|---|---|---|---|
| 1 | `models status` puede mentir (`"ok expires in Nd"`) con el refresh ya invalidado — **no diagnosticar auth solo con `status`** | `openclaw-vps-operator` → §"Leer primero el estado vivo" y §Antipatrones | **REFUERZA** (contradice guía vigente) | El checklist actual lista `openclaw models status` sin advertencia, y los antipatrones ya dicen "asumir que un provider está activo solo porque aparece en JSON" — este es el mismo error un nivel más adentro. **No es nuevo: es una corrección** |
| 2 | La verdad está en `journalctl --user -u openclaw-gateway` (`auth_permanent` / `refresh_token_invalidated` / `401`) | `openclaw-vps-operator` → §"Leer primero el estado vivo" | **NUEVO** | El checklist actual no incluye ninguna lectura de journal. Es el oráculo externo que falta |
| 3 | Re-auth headless: TTY vía `script -qfc "openclaw models auth login --provider openai --device-code" /dev/null` (+ fifo si hace falta) | `openclaw-vps-operator` → §"Flujo operativo" (sub-sección nueva "Re-auth headless") | **NUEVO** | Ninguna skill cubre re-auth sin TTY. Es la receta que desbloqueó el incidente |
| 4 | `--force` solo **antes** de un login limpio; post-login usar `models auth order set --provider openai --agent main "<bueno>" "<zombi>"` | `openclaw-vps-operator` → misma sub-sección | **NUEVO** | Secuencia con orden obligatorio; invertirla vuelve a romper el runtime |
| 5 | Una cadena 100% mono-provider **no es fallback**: un incidente tumba los 3 modelos | `openclaw-vps-operator` → §Antipatrones **y** norte §6 | **REFUERZA** | Los antipatrones ya dicen "olvidar que este stack debe seguir avanzando aunque la VM no esté" — mismo principio de degradación elegante, aplicado a providers. La **decisión** de adoptar cross-provider es de David, no de la skill |
| 6 | **Anti-roadmap-dormido**: un PR docs-only o un roadmap sin dueño ni fecha de caducidad se duerme (evidencia: #541, 20 días). Todo entregable docs-only lleva dueño + fecha de revisión, o se cierra | `umbral-rick-runtime` → §Anti-patterns; **y** `cursor-orchestrator` (registry) por ser transversal | **REFUERZA** | `rick-runtime` §Anti-patterns ya tiene "cerrar Ola editorial solo con `docs/ops/*.md` cuando David pidió Rick en marcha" — el vecino exacto. Este agrega el eje *tiempo*, no solo el eje *sustancia* |
| 7 | **"ahead ≠ 0" no es "trabajo sin integrar"** bajo squash-merge: el criterio es "¿existe PR mergeado con esa `headRefName`?" | `pkg-receiver-protocol` → §2 "Inventario antes de destruir" | **NUEVO** | El protocolo ya exige inventariar antes de destruir, pero no dice **cómo** leer el inventario. 70 falsos positivos en este mismo pack |

**Sobre la NUEVA `uas-north-governance` que el pack ofrecía como opción: se recomienda NO crearla.**
Los 7 aprendizajes tienen destino natural en skills existentes (2 skills + 1 protocolo). Crear
una skill de gobernanza nueva para alojarlos reproduciría el problema que este pack combate:
una superficie más que mantener, sin dueño. Además, el criterio de `skills-capitalize` para
crear-vs-actualizar (el mismo que P4 aplicó al tester E2E) pide que el rol se haya ejercido
en ≥2 superficies distintas — aquí es una sola: ops de runtime UAS.

**Prerequisito bloqueante para los ítems 1–5**: `openclaw-vps-operator` no está en el
registry. Capitalizar en una de sus dos copias del repo sin resolver primero cuál es
canónica crearía una tercera versión de la verdad. **Ese es el primer ítem de la cola §8.**

---

## 8. Cola de cierre post-GO — 15 ítems priorizados

Ninguno se ejecuta en este pack. Cada uno lleva dueño y criterio de "hecho".

| # | Ítem | Dueño | Hecho cuando | Riesgo |
|---|---|---|---|---|
| 1 | Resolver la copia canónica de `openclaw-vps-operator`: `.agents/skills/` vs `.claude/skills/` → subir una al registry, dejar la otra como puntero | Claude local | Existe 1 sola fuente en `umbral-skills-registry/skills/` | Bajo — **bloquea §7 ítems 1–5** |
| 2 | Redactar `docs/ops/uas-north-canonical-2026-08-06.md` con el outline §5 | Claude local | PR abierto, sin self-merge | Nulo (docs) |
| 3 | Curar fechas del backlog Notion — 20 tareas abiertas sin `Fecha objetivo`, cerrar las de abril ya resueltas | **David** | Rick reporta como urgente algo de agosto, no de abril | Nulo (dato) — **es el que mueve la aguja** |
| 4 | Re-correr P3-02 sobre el gateway re-autenticado | Claude local (con GO) | `USER_E2E_P3_FRESHNESS_PASS` con `[E]`, o BLOCKED con capa nombrada | Bajo — cierra el criterio 1 de §3.4 |
| 5 | Decidir #541: mergear como registro o cerrar por superado | **David** | PR en estado terminal | Nulo (docs, +2692/−0) |
| 6 | Releer #521 contra los 5 aprendizajes de auth → mergear con addendum o cerrar por superado | Claude local + GO David | PR en estado terminal | Bajo |
| 7 | Borrar las 87 ramas remotas con PR mergeado (17 + 70) | Claude local (con GO) | `git ls-remote` no las lista; conteo de refs baja de 279 a ~192 | Bajo — verificado que no hay pérdida |
| 8 | Rescatar o matar el **Grupo 2** de C.3: 16 ramas con `ahead` 1–3, leyendo el diff de cada una | Claude local (con GO) | Cada una: PR abierto o rama borrada, con una línea de inventario | Medio — requiere leer 16 diffs pequeños |
| 9 | Rescatar el WIP de `umbral-agent-stack-copilot` (doc de auditoría untracked + `docs/15-model-quota-policy.md`) | Claude local (con GO) | El doc está en una rama de origin o descartado explícitamente | Medio — **hay trabajo real que perder** |
| 10 | Rescatar el WIP de `umbral-agent-stack-codex-coordinador` (5 archivos, toca ROLE de rick-qa y rick-communication-director) | Claude local (con GO) | Igual que #9 | Medio — toca superficie de runtime |
| 11 | Podar los 26 worktrees Codex de `~/.codex/worktrees` (15 comparten el mismo SHA detached) + `Temp/pr269-worktree` + el `prunable` | Claude local (con GO) | `git worktree list` en los hermanos baja a las entradas con rama viva | Bajo — pero inventariar cada uno antes, por protocolo |
| 12 | Remover los clones `umbral-agent-stack-claude` (verificado sin contenido único) y `-antigravity` | Claude local (con GO) | Directorios ausentes; ramas siguen en origin | Bajo — #12 verificado con `git diff` |
| 13 | Decidir el destino de `.agents/board.md`: borrarlo, o generarlo desde `ops_resume_board.py` | **David** | El archivo se borró, o su cabecera dice "generado, no editar" | Nulo — 23 días stale, contradice el runbook vigente |
| 14 | Marcar vigencia en los ~330 docs de `ops`+`audits`: header `> Estado: CANONICO\|HISTORICO` según §1 | Claude local (con GO) | Todo doc de A.1 marcado CANONICO; familias ARCHIVAR marcadas HISTORICO. **Sin borrar nada** | Bajo — reversible |
| 15 | Abrir los 13 huérfanos del **Grupo 1** (`ahead` 3–4 cifras) con `git diff origin/main...rama` y decidir | Claude local (con GO) | Cada una clasificada con su diff real citado | Alto — es donde más fácil se destruye algo por error. **Va último a propósito** |

Orden recomendado: **1 → 2 → 3 → 4 → 5 → 7 → 11 → 12 → 6 → 13 → 9 → 10 → 8 → 14 → 15.**
Los tres primeros desbloquean todo lo demás; el último es el más peligroso y el menos urgente.

---

## 9. Lo que este pack NO hizo

No borró ninguna rama, worktree ni clone. No cerró ni mergeó ningún PR. No escribió en
Notion, en la VPS ni en el registry de skills. No ejecutó `skills-capitalize` en ningún
modo. No tocó el zombi `openai:umbral-rick`. No corrió sondas contra el gateway ni
re-diagnosticó auth. No creó el norte — solo propuso su path y su outline.

Higiene git: el árbol tenía 1 archivo modificado (`.agents/board.md`) y 12 rutas
untracked (10 tasks de LinkedIn de 2026-08-04, `.playwright-mcp/`,
`docs/operations/ledger-uas-rick.jsonl`). Se guardaron en
`stash@{0}: pre-pkg-uas-north-inventory-20260806-hygiene` — **no descartadas** — y se
restauran al cierre del pack.
