# F7 Rehearsal 3 — Egress/Sandbox Readiness: Live Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Live HEAD:** `8a9fe7a`
**Evidence branch:** `rick/copilot-cli-f7-readiness-rehearsal-evidence`

---

## 1. Objective (Rehearsal 3)

Validate that the environment is ready for a future real Copilot CLI execution, **without** lifting
`_REAL_EXECUTION_IMPLEMENTED` and **without** executing real Copilot.

Checks:
1. Sandbox scripts present
2. Docker accessible
3. Env/token contract verified
4. Egress profile designed but NOT applied
5. Audit/logging healthy
6. `copilot_cli.run` still blocked by `_REAL_EXECUTION_IMPLEMENTED=False`

---

## 2. Phase A — Preflight

| Item | Value |
|---|---|
| Live HEAD | `8a9fe7a` |
| MainPID | `1415290` (unchanged throughout) |
| `/health` | 200 |
| `copilot_cli.enabled` (L2) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (L3) | `false` |
| `egress.activated` (L4) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (L5) | `False` |

---

## 3. Phase B — Env/Token Contract

```
python3 scripts/verify_copilot_cli_env_contract.py \
  --runtime ~/.config/openclaw/copilot-cli.env \
  --secrets ~/.config/openclaw/copilot-cli-secrets.env \
  --strict
→ OK — no findings.
```

**Token names present in live process env (values never printed):**
```
COPILOT_GITHUB_TOKEN   ← present by name
RICK_COPILOT_CLI_ENABLED
RICK_COPILOT_CLI_EXECUTE
WORKER_TOKEN           ← present by name
```

---

## 4. Phase C — Sandbox Files & Docker

**Sandbox scripts — all present:**

| File | Size | Mode |
|---|---|---|
| `worker/sandbox/Dockerfile.copilot-cli` | 3373 B | `rw-rw-r--` |
| `worker/sandbox/copilot-cli-smoke` | 3936 B | `rwxrwxr-x` |
| `worker/sandbox/copilot-cli-wrapper` | 2565 B | `rwxrwxr-x` |
| `worker/sandbox/refresh-copilot-cli.sh` | 2764 B | `rwxrwxr-x` |
| `worker/sandbox/run-copilot-cli-smoke.sh` | 1225 B | `rwxrwxr-x` |
| `worker/sandbox/test-copilot-cli-wrapper.sh` | 5851 B | `rwxrwxr-x` |

**Docker:**
- Version: `29.2.1`
- Server: `29.2.1`
- Cgroup Driver: `systemd` / Cgroup v2
- Security Options: present
- Status: **accessible**

**Sandbox image `umbral-sandbox-copilot-cli`:** **NOT PRESENT** (not yet built)

→ Offline smoke: **SKIPPED** (image missing — build requires explicit approval)

---

## 5. Phase E — Egress Contract

```
python3 scripts/verify_copilot_egress_contract.py
→ OK
```

**Egress resolver dry-run (no writes, no nft applied):**
DNS resolution of allowlisted endpoints confirmed reachable (dry-run only):
- `api.githubcopilot.com:443` → `140.82.113.22`
- `api.individual.githubcopilot.com:443` → `140.82.113.22`
- `api.github.com:443` → `4.228.31.149`
- `copilot-proxy.githubusercontent.com:443` → resolved

**Live checks:**
- nft copilot rules: **none**
- Docker network copilot: **none**

Egress profile designed (`config/tool_policy.yaml :: egress.activated=false`) — **NOT applied.**

---

## 6. Phase F — Live Task Probe (Readiness Confirmed)

**Decision:** `execute_flag_off_dry_run` — task still blocked at L3 as expected.

```json
{
  "would_run": false,
  "phase": "F6.step1",
  "phase_blocks_real_execution": true,
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "env_enabled": true,
    "policy_enabled": true,
    "execute_enabled": false,
    "real_execution_implemented": false,
    "phase_blocks_real_execution": true
  },
  "egress_activated": false
}
```

No Copilot HTTPS. No subprocess. No real execution.

Phase G (temporary execute=true probe) **NOT needed** — Fase F already confirms stack readiness.

---

## 7. Phase H — Side-Effect Audit

| Check | Result |
|---|---|
| Latest audit log | `reports/copilot-cli/2026-05/d32a206146e44b95b78cb69528572e0d.jsonl` |
| Token scan (ghp_, github_pat_, ghs_, sk-) | **CLEAN** |
| nft copilot rules | none |
| Docker network copilot | none |
| Copilot HTTPS | none |
| Notion/publish | none |
| MainPID | `1415290` (unchanged — no restart) |
| `/health` | 200 |

---

## 8. Readiness Summary

| Component | Status |
|---|---|
| Env/token contract | ✅ OK |
| Sandbox scripts | ✅ all present |
| Docker daemon | ✅ accessible (v29.2.1) |
| Sandbox image `umbral-sandbox-copilot-cli` | ⚠️ NOT BUILT — requires explicit build step |
| Egress contract verifier | ✅ OK |
| Egress DNS resolution (dry-run) | ✅ endpoints reachable |
| Live nft rules | ✅ none (not applied) |
| Live Docker network | ✅ none (not created) |
| Gate L5 `_REAL_EXECUTION_IMPLEMENTED` | ✅ `False` — final barrier intact |
| Task probe decision | ✅ `execute_flag_off_dry_run` (expected) |
| Audit log clean | ✅ |

**One pending prerequisite before real execution can be attempted:**
- Build sandbox image `umbral-sandbox-copilot-cli` from `worker/sandbox/Dockerfile.copilot-cli`
  (requires `docker build` command with explicit operator approval)

---

## 9. Gate Stack — Current State

```
L1  RICK_COPILOT_CLI_ENABLED=true       [open]
L2  copilot_cli.enabled=true            [open — F7.rehearsal-1]
L3  RICK_COPILOT_CLI_EXECUTE=false      [closed — last envfile gate]
L4  egress.activated=false              [closed — yaml, not applied]
L5  _REAL_EXECUTION_IMPLEMENTED=False   [closed — code constant, final barrier]
```

---

## 10. Next Steps (require David's approval per step)

1. **Build sandbox image** (`docker build -t umbral-sandbox-copilot-cli worker/sandbox/`) — offline test only
2. **Run offline smoke** (`run-copilot-cli-smoke.sh`, `--network=none`) — no internet
3. **Rehearsal 4** (if approved): open L3+L5 simultaneously → observe Docker container launch
   fail gracefully (image invoked but Copilot not installed/authenticated) — still no real output
4. **Full activation** (F8+): requires separate explicit gate per step

**No action without David's explicit approval per step.**
