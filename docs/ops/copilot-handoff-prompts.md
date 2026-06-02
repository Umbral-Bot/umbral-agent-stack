# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**

Last updated: 2026-06-02 (Phase 0 D3.2 ready — issue #440, task 019)

---

## Estado activo

| Hilo | Superficie | Estado |
|---|---|---|
| **S** | Codex meta | 🟡 task 012 lane PR gate (recomendado antes torneo) |
| **T** | Copilot-VPS | 🔴 **Siguiente** — D3.2 preflight (task 019) |
| **U** | David + Copilot-VPS | ⏸ torneo run (`autorizo torneo D3.2`) |
| **V** | Copilot Windows | ⏸ merge winner post-torneo |

**G-D5.2 + O15:** ✅ cerrados (`3388bf9c`, skills live VPS).

Issue torneo: [#440](https://github.com/Umbral-Bot/umbral-agent-stack/issues/440)

---

## Thread T — Copilot-VPS · D3.2 preflight (task 019) 🔴 SIGUIENTE

```
Sos Copilot-VPS. Preflight torneo D3.2 O2 backup alerts — SIN spawn.

Preflight repo:
  cd ~/umbral-agent-stack && git pull --ff-only origin main && git log -1 --oneline
  test -f .agents/tasks/2026-06-02-019-d3.2-tournament-o2-backup-alerts.md && echo TASK_FILE_OK

Lee task 019 + spec:
  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d32-issue-440-o2-backup-alerts-spec.yaml

Ejecutar:
  mkdir -p ~/.coord-ag-evidence/D3.2
  bash scripts/openclaw/tournament-preflight-dry-run.sh \
    openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d32-issue-440-o2-backup-alerts-spec.yaml
  bash scripts/vps/check-main-allowagents.sh

Si falta skill live y David dice "autorizo sync tournament skill":
  rsync -a openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/ \
    ~/.openclaw/workspace/skills/multi-agent-tournament-orchestrator/

NO openclaw agent run. NO env. Worktree clean report.

VEREDICTO: D32_PREFLIGHT_OK | D32_PREFLIGHT_BLOCKED
```

---

## Thread U — Copilot-VPS · run torneo D3.2

**Requiere:** `D32_PREFLIGHT_OK` + David escribe `autorizo torneo D3.2`

```
autorizo torneo D3.2

Sos Copilot-VPS. Torneo real #2 issue #440.

cd ~/umbral-agent-stack && git pull --ff-only origin main && git status --short
# CLEAN required

bash scripts/vps/d3.2-tournament-run.sh

Evidencia: ~/.coord-ag-evidence/D3.2/
Lane sin PR URL = incomplete.

NO merge salvo "autorizo merge winner D3.2".

VEREDICTO: M1_D32_TOURNAMENT_OK | M1_D32_TOURNAMENT_PARTIAL
```

---

## Thread V — Copilot Windows · merge winner D3.2

**Requiere:** PR URLs del torneo + `autorizo merge winner D3.2`

```
Sos Copilot Windows. Judge + merge torneo D3.2 (#440).

cd C:\GitHub\umbral-agent-stack && git pull --ff-only origin main

Revisar PRs [tournament:...] — rubric en spec d32-issue-440.
gh pr merge <winner> --squash
gh issue comment 440 --repo Umbral-Bot/umbral-agent-stack --body "<metrics JSON>"

VEREDICTO: D32_WINNER_MERGED
```

---

## Thread S — Codex meta · lane gate task 012 (paralelo recomendado)

```
Sos Codex meta. Task 012 tournament lane PR gate.

Preflight:
  cd C:\GitHub\umbral-agent-stack
  git pull --ff-only origin main
  Test-Path .agents/tasks/2026-06-01-012-tournament-lane-pr-gate.md

Lane done solo con PR URL. PR sin merge.
VEREDICTO: M1_D31_LANE_GATE_OK
```

---

## Thread Q — G-D5.2 (CERRADO)

`G_D52_GATE_CLOSED` — no repetir.

---

## Thread R — O15 skills (CERRADO)

PR #439 → `3388bf9c` + `O15_OPENCLAW_WORKSPACE_SKILLS_OK`

---

## Thread O/P/N/Q — CERRADOS (no repetir)

| Thread | VEREDICTO |
|---|---|
| O Calendar E2E | G_D52_CALENDAR_E2E_OK |
| P merge #438 | GD52_DOCS35_MERGED |
| N Notion §6 | ADR16_LIVE_LOG_OK |

---

## Thread H — worktree D3.1 cleanup (opcional)

```
Sos Copilot-VPS. Read-only salvo "autorizo remove worktree".
  ~/umbral-agent-stack/.agents/tasks/2026-06-01-013-copilot-vps-d31-worktree-cleanup.md
VEREDICTO: D31_WORKTREE_CLEANUP_OK
```

---

## Próximo foco Q2

| Prioridad | Spine | Agente | Acción |
|---|---|---|---|
| 1 | **D3.2** | VPS + Windows | Torneo #440 (preflight → run → merge) |
| 2 | D3.2 prep | Codex meta | Task 012 lane gate (paralelo) |
| 3 | D4.1 | Copilot Windows | Mission Control PR |
| 4 | D5.3 | Copilot-VPS | Granola soak |
| 5 | D6.1 | Azure | KB AECO (26-jun) |

Friday retro **2026-06-05** — actualizar dashboard §4 spine v2.

---

## Cerrados — no repetir

- G-D5.1 → G_D51_VPS_AUDIT_OK
- G-D5.2 re-OAuth runtime → Rick OpenClaw en VPS
- Consent legacy Rick Calendar → revocado
- GCP Rick legacy clients → eliminados
- Decisión OAuth scope → **B** re-OAuth ADR
