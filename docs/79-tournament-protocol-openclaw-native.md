# 79 — Tournament Protocol (OpenClaw-native)

- **Status:** Draft v1 — formato estándar tournament 1-issue → N-branches → 1-winner sobre primitivas nativas OpenClaw.
- **Date:** 2026-05-06
- **Closes:** O7 → checkbox "Definir formato tournament estándar" (Plan Q2-2026 línea ~468).
- **Built on:** [`docs/adr/tournament-on-openclaw-primitives.md`](adr/tournament-on-openclaw-primitives.md) (ADR commit `aecc68c`, Decision A — Wrapper-only).
- **Implemented by (pending, ~12-15h):** skill `multi-agent-tournament-orchestrator` (a crear en `~/.openclaw/skills/`).
- **Related:** [`docs/69-tournament-over-branches-runbook.md`](69-tournament-over-branches-runbook.md) — handler legacy `github.orchestrate_tournament` (Python). Este protocolo lo **reemplaza** para tournaments multi-agente reales sobre OpenClaw 2026.5.3+; el handler legacy queda como fallback LLM-puro.

---

## 1. Por qué este protocolo

OpenClaw 2026.5.3-1 expone `sessions_spawn` + `/subagents` + el patrón `parallel-specialist-lanes` con cobertura ≥ 80 % de lo que un tournament necesita (ver ADR §2-§4). El protocolo evita reimplementar spawn/isolation/concurrency/cleanup en Python y deja al wrapper sólo: pre-flight, render del task body por lane, recolección de PRs, aplicación de rubric, merge del winner, soft-close de losers.

**Fuera de scope de este doc:** detalles de cómo `sessions_spawn` aísla el runtime, cómo se hace push-completion, o cómo se calcula `runTimeoutSeconds` desde `usd_budget_cap`. Eso vive en el ADR §2 y §5.

---

## 2. Contrato del tournament

Un tournament es una unidad atómica con:

| Campo | Tipo | Descripción |
|---|---|---|
| `tournament_id` | str | Slug derivado de `<repo>-<issue_number>-<short_sha>` (8 chars). Ej. `umbral-agent-stack-321-7752e42`. Se usa en branch naming + PR title prefix + Mission Control update key. |
| `issue_id` | str | `<owner>/<repo>#<number>` o `LIN-<id>` para Linear. Una sola fuente de verdad por tournament. |
| `lanes` | list | 2–5 lanes. Cada lane es una `{specialty, agent_id, task_template, model?, runTimeoutSeconds?}` (ver §3). |
| `winner_rubric` | str (markdown) | Texto que el orchestrator (depth-1) usa para decidir. Vive en el SKILL.md del lane-class, no en el código. |
| `usd_budget_cap` | float (opcional) | El wrapper lo traduce a `runTimeoutSeconds` por lane usando el costo del modelo del lane (ADR §5 paso 2). |
| `cleanup_policy` | enum | `keep-losers` (default v1) \| `soft-close` \| `hard-delete` (no usar en v1). |

**Invariantes:**

1. **N entre 2 y 5.** Más allá de 5 viola `agents.defaults.subagents.maxChildrenPerAgent: 5`. Si necesitás más, abrí dos tournaments paralelos sobre el mismo issue (anti-patrón en v1).
2. **Cada lane es un agente distinto.** No se puede tener dos lanes con el mismo `agent_id` (rompe la metáfora "specialist lane" y duplica transcript path).
3. **El orchestrator que dispara los spawns es siempre depth-1.** El usuario (David) dispara `rick-orchestrator`, este invoca el skill, el skill spawnea los lanes (depth 2). No se permite anidar tournaments.
4. **El branch base es siempre `main` actualizado.** Pre-flight aborta si el repo tiene worktree dirty o si `git fetch origin main` no es fast-forward.

---

## 3. Lane spec

```yaml
lane:
  specialty: backend-typescript        # slug, identifica al lane en métricas + branch name
  agent_id: rick-delivery              # debe estar en allowAgents del orchestrator
  task_template: |
    # Tarea: <issue_title>
    Issue: <issue_url>
    Branch: tournament/<tournament_id>/lane-<specialty>
    Specialty focus: <prompt-specifico-de-este-lane>

    Contract (read-only invariants):
      - NO modificás otros lanes, NO mergeás vos mismo.
      - Al terminar: gh pr create --title "[tournament:<tournament_id>:<specialty>]" --body-file <body>.
      - Anunciá de vuelta: PR URL + diff stats + checks status.
  model: gpt-5-mini                    # opcional; default lane agent's model
  runTimeoutSeconds: 1800              # opcional; el wrapper puede sobrescribir vía usd_budget_cap
```

**Lane convention de branch:** `tournament/<tournament_id>/lane-<specialty>`. Sin excepciones (parser de métricas asume este formato).

**Lane convention de PR title:** `[tournament:<tournament_id>:<specialty>] <issue_title>`. Permite filtrar con `gh pr list --search "[tournament:<tournament_id>:"`.

---

## 4. Flujo end-to-end

```
USER → rick-orchestrator (depth 0)
        │
        │  /skills run multi-agent-tournament-orchestrator <tournament_spec.yaml>
        ▼
   Pre-flight (wrapper)
     ├── git status clean? + main fast-forward?
     ├── allowAgents cubre todos los lanes?
     ├── agents.defaults.subagents.maxSpawnDepth >= 2?     ← bloquea si no
     └── usd_budget_cap → runTimeoutSeconds por lane
        │
        ▼
   sessions_spawn × N (depth 1 → depth 2)
     ├── lane-backend-typescript (rick-delivery)    ─┐
     ├── lane-python              (rick-delivery)    │  paralelo, isolated
     └── lane-no-code             (rick-ops)        ─┘
        │
        │  cada lane:
        │   1. crear branch tournament/<id>/lane-<specialty>
        │   2. implementar
        │   3. gh pr create
        │   4. announce-back: { pr_url, diff_stats, checks_status }
        ▼
   Push-completion (nativo) → orchestrator junta los N announces
        │
        ▼
   Winner pick (orchestrator turn, aplica winner_rubric)
     ├── gh pr merge <winner> --squash
     └── for loser in losers:
           gh pr close --comment "tournament loser, kept for forensic"
           (NO se borra el branch en v1; cleanup_policy=keep-losers)
        │
        ▼
   Cleanup
     ├── /subagents kill all (sólo los hijos no-anunciados, si los hay)
     └── auto-archive nativo a 60min se encarga del resto
        │
        ▼
   Métricas → Notion + Linear
     ├── leer: openclaw tasks list --runtime subagent --json
     ├── leer: gh pr view --json para cada PR
     └── post: 1 update Notion "Mission Control" + 1 comentario Linear
```

---

## 5. Pre-conditions (chequeadas por el wrapper)

Las 3 del ADR §7, copiadas como gate del skill:

1. `agents.defaults.subagents.maxSpawnDepth >= 2` en `~/.openclaw/openclaw.json`. **Hoy: NO. Default es 1.** Requiere PR separado + sign-off David vía skill `openclaw-vps-operator`. **Sin esto el primer tournament no corre.**
2. Cada `agent_id` de los lanes tiene `tools.profile: "coding"` (necesario para `git`/`gh`).
3. `gh auth status` green dentro del workspace de cada lane (hoy: OK como user `rick`, token `UmbralBIM`).

---

## 6. Métricas mínimas v1

Por tournament (post-merge), el wrapper emite:

```json
{
  "tournament_id": "umbral-agent-stack-321-7752e42",
  "issue_id": "Umbral-Bot/umbral-agent-stack#321",
  "lanes_total": 3,
  "lanes_completed": 3,
  "lanes_pr_mergeable": 2,
  "winner_specialty": "backend-typescript",
  "time_to_first_pr_seconds": 412,
  "time_to_winner_seconds": 1840,
  "tokens_total": 78421,
  "usd_estimated": 0.42
}
```

Fuente nativa: `openclaw tasks list --runtime subagent --json` (timing + tokens) + `gh pr view --json` (mergeable + checks).

No hay agregación cross-tournament en v1. Eso es post-MVP.

---

## 7. Smoke test mandatorio antes del primer tournament real

El primer PR del wrapper **debe** incluir un end-to-end smoke contra un issue trivial (ej. typo en doc). Criterios de aceptación del smoke:

- [ ] `tournament_id` generado y consistente en branch + PR title + métricas.
- [ ] N=2 lanes paralelos, ambos producen PR.
- [ ] Orchestrator picks winner aplicando rubric (rubric trivial para smoke: "PR con menos líneas modificadas").
- [ ] Winner mergeado a `main` vía `gh pr merge --squash`.
- [ ] Loser cerrado con comentario, branch preservado.
- [ ] Métricas posteadas a Notion Mission Control.
- [ ] `/subagents kill all` no encuentra hijos vivos al final.

**El primer tournament real (post-smoke)** será sobre un issue de O1 hardening, decidido por David. No se ejecuta tournament sobre nada antes del smoke.

---

## 8. Open items (no bloquean v1)

- Aggregator cross-tournament (dashboard de % winners por specialty/lane). Post-MVP.
- Soporte `cleanup_policy: hard-delete` (borrar branches losers automáticamente). Requiere política explícita de retención de evidencia forense; postergado.
- Tournaments anidados (orchestrator dispara sub-orchestrators). Bloqueado por `maxSpawnDepth: 2`. No hay caso de uso v1.
- Integración con `github.orchestrate_tournament` legacy: el handler Python queda como fallback LLM-puro (sin código real, sólo discovery/develop/debate/judge). Si en algún momento se quiere tournament sin código, se invoca el handler directamente, no este protocolo.

---

## 9. Referencias

- ADR: [`docs/adr/tournament-on-openclaw-primitives.md`](adr/tournament-on-openclaw-primitives.md) (commit `aecc68c`).
- Spike task: [`.agents/tasks/2026-05-06-014-copilot-vps-spike-openclaw-subagents-tournament.md`](../.agents/tasks/2026-05-06-014-copilot-vps-spike-openclaw-subagents-tournament.md).
- Plan Q2-2026: [`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`](https://github.com/Umbral-Bot/notion-governance/blob/main/docs/roadmap/12-q2-2026-platform-first-plan.md) → O7.
- OpenClaw native docs (en VPS): `/home/rick/.npm-global/lib/node_modules/openclaw/docs/tools/subagents.md` + `…/concepts/parallel-specialist-lanes.md`.
- Skill governance: `openclaw-vps-operator` (para el flip de `maxSpawnDepth`).
