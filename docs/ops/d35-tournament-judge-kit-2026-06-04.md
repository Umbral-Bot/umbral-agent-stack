# D3.5 — Kit de evaluación y juzgamiento de torneos

Sistema para que **David** evalúe resultados de torneos **sin correr el torneo aún**. Cuando autorices D3.5, Copilot-VPS ejecuta; vos juzgás con esta plantilla; Copilot Windows mergea solo con gate explícito.

## Arquitectura (respuesta corta: ¿Azure + `gh`?)

| Capa | Dónde corre | Qué hace |
|------|-------------|----------|
| **Orquestador** | VPS — OpenClaw sesión **`main` standalone** | `sessions_spawn` × N lanes (skill `multi-agent-tournament-orchestrator`) |
| **Lanes (subagentes)** | VPS — agentes OpenClaw (`rick-delivery`, `rick-ops`, …) | **Código en clone** `~/umbral-agent-stack`: `git checkout -b`, editar, `git push`, **`gh pr create`** |
| **Inferencia LLM** | Típicamente **Azure AI Foundry / Azure OpenAI** vía alias del gateway OpenClaw | Pensar/redactar; **no** es un “agente ACA” haciendo el PR |
| **Judge + merge** | **Copilot Windows** | `gh pr diff`, checks, rubric; merge squash si David autoriza |
| **D6.1 KB jobs** | Azure Container Apps (otro carril) | **No** es el runtime del torneo D3.x |

```text
David → main (VPS OpenClaw)
          → sessions_spawn → lane agents (mismo VPS, tools.profile coding)
                → git + gh CLI en ~/umbral-agent-stack
                → PR en GitHub
          → collect PR_URL (obligatorio)
David → scorecard (este doc)
Copilot Windows → judge + merge (gate)
```

**Sí:** los subagentes de lane deben usar **`gh`** (y git) en la VPS; preflight exige `gh auth status` OK (`tournament-protocol.md` §5).

**D3.6 (roadmap):** skill [`tournament-github-cli`](../../openclaw/workspace-templates/skills/tournament-github-cli/SKILL.md) + plugin `umbral-tournament-github` para guardrails (`tournament/` branches, título PR, `PR_URL`). Ver [`d36-tournament-github-cli-plugin-roadmap-2026-06-04.md`](d36-tournament-github-cli-plugin-roadmap-2026-06-04.md).

**No:** no es “desplegar dos Copilot en Azure” para el torneo; Azure alimenta el **modelo**, la **superficie de ejecución** del torneo es **OpenClaw en VPS**.

---

## Fase A — Antes del torneo (David checklist)

- [ ] Issue elegido (1 issue, 2 lanes, `agent_id` distintos).
- [ ] `winner_rubric` escrito (copiar plantilla §3).
- [ ] Frase: `autorizo D3.5 clean tournament rerun` + issue #___.
- [ ] Copilot-VPS: preflight 8/8 (`tournament-preflight-dry-run.sh`).

---

## Fase B — Recolección (Copilot-VPS → vos)

Pedir carpeta evidencia: `~/.coord-ag-evidence/D3.5/` con:

- `run-start.txt` (SHA `main`)
- `final-metrics.json` o equivalente con `pr_urls[]` y, por lane, `worktree_path` (aislamiento RC-4; lo devuelve `tournament_lane.create_branch` con `use_worktree=true`)
- Log de VEREDICTO: `D35_CLEAN_TOURNAMENT_OK` | `PARTIAL` | `BLOCKED`

**Regla dura:** `OK` solo si `pr_count >= 2` y cada URL verificada con `gh pr view`.

**Aislamiento (criterio scorecard §3):** verificar que cada lane reporta su `worktree_path` bajo `~/.coord-ag-evidence/worktrees/<tournament_id>/lane-<specialty>` — confirma que la lane no compartió worktree (ver `docs/79` §4.3).

---

## Fase C — Scorecard David (copiar y completar)

```markdown
# Scorecard torneo: <tournament_id>
Issue: Umbral-Bot/umbral-agent-stack#___
Fecha: ___
Rubric (1 párrafo): ___

| Criterio | Peso | Lane A (<specialty>) | Lane B (<specialty>) | Notas |
|----------|------|----------------------|----------------------|-------|
| Cumple issue (scope correcto) | 30 | 0–3 | 0–3 | |
| Diff mínimo correcto | 20 | 0–3 | 0–3 | additions/deletions |
| Tests / CI verde | 20 | 0–3 | 0–3 | statusCheckRollup |
| Aislamiento (solo su branch) | 15 | 0–3 | 0–3 | sin tocar otras lanes |
| Calidad operativa (docs, logs) | 15 | 0–3 | 0–3 | |
| **Total ponderado** | 100 | | | |

PR URLs:
- Lane A: https://github.com/Umbral-Bot/umbral-agent-stack/pull/___
- Lane B: https://github.com/Umbral-Bot/umbral-agent-stack/pull/___

Decisión David:
- [ ] Winner: lane ___ / PR #___
- [ ] Rechazar ambas (no merge)
- [ ] Pedir rescate lane ___ (sin re-torneo)

Gate merge (solo si winner claro):
`autorizo merge winner D3.5 PR <número>`
```

Escala 0–3 por celda: 0 = no cumple, 1 = parcial, 2 = cumple, 3 = excelente.

---

## Fase D — Comandos judge (Copilot Windows)

Pegar tras tener 2 PR URLs:

```powershell
cd C:\GitHub\umbral-agent-stack
git fetch origin main
$prA = <número A>
$prB = <número B>
gh pr view $prA --json number,title,url,headRefName,additions,deletions,mergeable,statusCheckRollup,body
gh pr view $prB --json number,title,url,headRefName,additions,deletions,mergeable,statusCheckRollup,body
gh pr diff $prA --repo Umbral-Bot/umbral-agent-stack
gh pr diff $prB --repo Umbral-Bot/umbral-agent-stack
```

Salida esperada del agente judge:

```text
VEREDICTO: D35_JUDGE_RECOMMENDATION_READY
Winner recomendado: PR #___ (lane ___)
Razón (3 bullets):
Perdedor: PR #___ — mantener abierto | cerrar sin merge (según David)
```

**David** rellena scorecard §3; si coincide con recomendación → frase merge.

---

## Fase E — Cierre administrativo

| Situación | Acción |
|-----------|--------|
| Winner mergeado | Cerrar PRs perdedores con comentario + `autorizo cerrar PR #___` |
| PARTIAL (1 PR) | Rescate lane: `autorizo rescate lane <specialty> D3.5` — **no** re-spawn parent |
| 0 PR | Abort; retro en issue; no merge |

---

## Integración eval harness (#462)

Cuando el torneo toque código editorial/agentes, opcional cruzar con:

- `docs/evals/core-eval-harness.md`
- `evals/editorial/dimensions.yaml` (solo si el issue es editorial)

Torneos infra/Ops usan rubric en spec YAML, no gold-set editorial.

---

## Prompt listo — Copilot Windows judge (post-D3.5)

```text
Sos Copilot Windows. Judge read-only torneo D3.5.
Responder en espanol. NO merge sin "autorizo merge winner D3.5 PR <n>".

Inputs: PR URLs de ambas lanes + winner_rubric del spec + scorecard David si existe.

Ejecutar gh pr view/diff (ver docs/ops/d35-tournament-judge-kit-2026-06-04.md Fase D).
Entregar tabla criterios + recomendación winner + riesgos merge.

VEREDICTO: D35_JUDGE_RECOMMENDATION_READY | D35_JUDGE_BLOCKED
```

---

## Historial

- v1 2026-06-04 — Cursor lead, post `UNIFIED_PLAN_CONSENSUS_READY`.
