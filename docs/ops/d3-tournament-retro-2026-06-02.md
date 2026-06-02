# D3.4 — Tournament retro (D3.0–D3.3)

- **Date:** 2026-06-02
- **Owner:** Cursor (repo) · evidence from Copilot-VPS + Copilot Windows
- **Spine:** D3.4 — retro tras 3 torneos reales + smoke D3.0
- **VEREDICTO:** `M1_D34_TOURNAMENT_RETRO_OK`

---

## 1. Executive summary

| Run | Issue | Spawn ×2 | PR URLs (torneo) | Winner path | Competitivo 2-PR “limpio” |
|---|---|---|---|---|---|
| **D3.0** smoke | #434 | ✅ | ✅ (smoke) | #435 merged | ✅ (smoke scope) |
| **D3.1** | #403 | ✅ | ❌ 0 | salvage **#437** | ❌ |
| **D3.2** | #440 | ✅ | ❌ 0 | salvage **#444** | ❌ |
| **D3.3** | #445 | ✅ | 1 en torneo → rescate → 2 | **#446** merged; #447 kept | ⚠️ tras rescate manual |

**Infra validada:** G-D1a/b/c, preflight 8/8, `sessions_spawn` desde `main` standalone, gate #441 (PR URL = lane complete).

**Gap recurrente:** lanes implementan pero **no cierran** push + `gh pr create` antes de idle/compactación de sesión. Salvage humano + judge Windows cerró entregables; no sustituye torneo autónomo limpio.

---

## 2. Root causes (evidence-based)

### RC-1 — Lane session compaction before push/PR

- **D3.3 delivery:** commit `9741e7c` local, TODOs push/PR pendientes, jsonl sin actividad post-11:23, `LANES_IDLE_BREAK prs=1`.
- **D3.2:** file lock stale en QA; lanes en lectura/plan sin push.
- **Mitigation v1.1:** watcher debe distinguir “lane activa” vs “idle >N min sin PR”; documentar **rescate lane** (push + PR) sin re-spawn parent.

### RC-2 — Collect phase confundía subagent success con lane complete

- Resuelto en **#441** / `docs/79` §4.1: `lane_complete = branch_pushed && pr_url && gh_pr_view_ok`.
- Torneo sigue reportando `yielded=true` con 0 PR — gate correcto, lanes no cumplen contrato.

### RC-3 — Spec en repo ≠ spec live en VPS

- D3.3 preflight: orchestrator live en sync salvo `d33-issue-445` (repo-only).
- **Mitigation:** `rsync` orchestrator **obligatorio** en Fase 0b antes de run (ya en PROMPT 1 AB).

### RC-4 — Worktree compartido entre lanes

- D3.3: `main` checkout en rama delivery mientras QA trabajaba — riesgo de conflicto.
- **Mitigation v1.1:** lanes deben usar **git worktree add** por lane o paths aislados; parent collect restaura `main` solo tras idle.

### RC-5 — Judge/merge fuera del parent OpenClaw

- Correcto por diseño v1: parent **no-merge**; David autoriza → **Copilot Windows** judge + squash.
- Rubric en spec yaml + tabla A–E en issue antes de merge.

---

## 3. What worked

1. **D3.0 smoke** — prueba end-to-end del contrato (2 PRs, winner merge).
2. **Preflight script** — `tournament-preflight-dry-run.sh` + `check-main-allowagents.sh`.
3. **Lane PR gate (#441)** — evita falso OK con 0 PRs.
4. **Evidencia** — `~/.coord-ag-evidence/D3.x/` + `final-metrics.json` + issue comments.
5. **Rescate delivery D3.3** — commit local → PR #447 → judge 446 vs 447 → merge #446.
6. **Handoffs por fases** — W → AA → AB → 1c → AC → AD reducen ambigüedad.

---

## 4. Protocol changes (v1.1 — apply in repo)

Documented in:

- [`docs/architecture/tournament-protocol.md`](../architecture/tournament-protocol.md) §7
- [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md) §4.2, §10

| Change | Action |
|---|---|
| Mandatory orchestrator rsync before run | Handoff AB Fase 0b |
| Watcher: BOTH_PRS or idle+timeout → collect | Handoff AB / 1b |
| Lane rescue playbook (no re-tournament) | Handoff 1c pattern |
| Lane worktree isolation | Spec task_template + SKILL note |
| Post-PARTIAL: salvage lane OR Codex PR, never silent close | Board + handoffs |
| Judge always Copilot Windows after ≥2 PRs | AC prompt |
| VPS pytest via `.venv/bin/python` | AD prompt note |

---

## 5. DoD Q2 honesty (torneos ≥3)

| Criterion | Status |
|---|---|
| 3 ejecuciones reales (D3.1–D3.3) | ✅ |
| Métricas en issues | ✅ (parciales + rescates) |
| 3× competitivo 2-PR sin salvage | ❌ (0/3 limpios; 1/3 tras rescate) |
| Recomendación | Mantener salvage como **plan B** documentado; opcional D3.3b re-run solo si David autoriza costo |

---

## 6. Next tournaments (D3.x / O7)

1. Exigir en `task_template`: último paso = `gh pr create` + línea `PR_URL=https://...` en announce.
2. Probar `runTimeoutSeconds` + recordatorio push a los 20 min (skill patch).
3. Mission Control (D4) como launcher v2 — no bloquea más torneos standalone.
4. Cerrar PR #447 cuando no se necesite diff forense.

---

## 7. References

| Artifact | Path / URL |
|---|---|
| D3.0 | issue #434, PR #435, `M1_D30_SMOKE_OK` |
| D3.1 | #403, `M1_D31_TOURNAMENT_PARTIAL`, #437 |
| D3.2 | #440, `M1_D32_TOURNAMENT_PARTIAL`, #444 @ `2fe58535` |
| D3.3 | #445, `M1_D33_TOURNAMENT_PARTIAL`, #446 winner `da8eba85`, #447 open |
| Handoffs | `docs/ops/copilot-handoff-prompts.md` |
| Evidencia VPS | `~/.coord-ag-evidence/D3.1/`, `D3.2/`, `D3.3/` |
