# Tournament protocol — launch architecture (Mega 1 / D1.2)

- **Status:** Active — decision **G-D1b** recorded 2026-06-01.
- **Owner:** David Moreira (gate) / Cursor (repo).
- **Related:** [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md) (contract), [`docs/external-context/openclaw-known-issues.md`](../external-context/openclaw-known-issues.md) (ISSUE-001), [`notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md`](https://github.com/Umbral-Bot/notion-governance/blob/main/docs/roadmap/13-q2-2026-v2-deployment-spine.md) (D1–D3).

---

## 1. Decision G-D1b — launch point v1

| Option | Verdict v1 | Rationale |
|---|---|---|
| **A — `main` / standalone** | ✅ **Selected** | ISSUE-001: only standalone sessions expose `sessions_spawn`. Lowest moving parts. No Mission Control dependency. |
| **B — Mission Control dispatcher (O13.4)** | ⏸ Deferred | O13 scaffold not deployed; adds launcher layer before first smoke. Revisit when D4 is live. |
| **C — Nested `rick-orchestrator`** | ❌ Forbidden | When `rick-orchestrator` is invoked nested from `main`, runtime **filters** `sessions_spawn` (confirmed empirically). Tournament cannot start from this path. |

**Gate David (2026-06-01):** G-D1b standalone/main — confirmed via Mega 1 coordination thread.

---

## 2. Entry surface (what “standalone” means)

The tournament **must** start in a session where OpenClaw exposes `sessions_spawn` in the tool whitelist.

### Allowed v1

| Surface | Agent | Notes |
|---|---|---|
| OpenClaw Control UI | `main` | Direct chat with `main`, not routed through nested subagent of another turn. |
| CLI (VPS) | `main` | e.g. `openclaw agent --agent main` (or documented equivalent) in a **new** standalone session. |
| Explicit skill invoke on `main` | `main` | `/skills run multi-agent-tournament-orchestrator …` **in the main session**, not delegated to nested `rick-orchestrator`. |

### Forbidden v1

| Surface | Why |
|---|---|
| Telegram → `rick-orchestrator` nested under `main` | ISSUE-001 — no `sessions_spawn` |
| Any nested subagent session as spawn parent | Same |
| Mission Control HTTP dispatcher | Not deployed (D4) |

Pre-flight in the wrapper skill **must abort** if the current session is nested (tool set lacks `sessions_spawn`) or if `sessions_spawn` is unavailable.

---

## 3. Spawn topology v1 (with `maxSpawnDepth = 2`)

With G-D1a applied (2026-06-01, VPS effective):

```
David
  └── main (standalone, depth 0) — has sessions_spawn
        └── skill: multi-agent-tournament-orchestrator
              └── sessions_spawn × N  →  lane agents (rick-delivery, rick-ops, …) at depth 1
                    └── each lane: branch + implement + gh pr create + announce-back
```

**Not v1:** `main → rick-orchestrator (nested) → lanes` — broken by ISSUE-001.

`maxSpawnDepth=2` is sufficient: lanes at depth 1; no depth-2 nesting required for v1 (orchestrator role is **`main` + skill**, not nested `rick-orchestrator`).

---

## 4. Migration path v2 (post-D4)

When Mission Control (O13) is deployed and health-OK:

1. Add launcher option **B** behind feature flag / config in the wrapper skill.
2. Dispatcher invokes the same skill body with the same pre-flight gates.
3. Keep standalone/main as **fallback** if dispatcher unhealthy.
4. Record boundary change in `notion-governance/docs/policies/05-change-management-and-automation-safety.md`.

Until then, docs and smoke tests reference **option A only**.

---

## 5. Pre-conditions checklist (wrapper — unchanged from 79 §5)

Before any tournament spawn:

1. `agents.defaults.subagents.maxSpawnDepth >= 2` — ✅ VPS 2026-06-01.
2. Current session is **standalone** with `sessions_spawn` available — ✅ D3.0 smoke 2026-06-01.
3. Each lane `agent_id` in `allowAgents` of spawn parent (`main`) — ✅ VPS **`["rick-orchestrator", "rick-delivery", "rick-qa"]`** (D3.0; David confirmed keep 2026-06-01).
4. `gh auth status` green in lane workspace — ✅ VPS 2026-06-01.
5. Git worktree clean; `main` fast-forward.

Lane completion is defined by `docs/79` §4.1: branch pushed + verified PR URL. A lane with subagent success but no PR must be recorded as `lane_incomplete` and excluded from judge.

---

## 6. References

- Protocol contract: `docs/79-tournament-protocol-openclaw-native.md`
- ADR: `docs/adr/tournament-on-openclaw-primitives.md`
- ISSUE-001: `docs/external-context/openclaw-known-issues.md`
- Implementation task: `.agents/tasks/2026-06-01-003-d2.1-multi-agent-tournament-orchestrator-skill.md`
- Skill (repo): `openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/SKILL.md`
