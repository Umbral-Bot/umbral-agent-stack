# F7 Rehearsal 4B — Egress Profile Live-Staging: Live Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Live HEAD:** `5d29df0`
**MainPID throughout:** `1418206` (no restart)
**Evidence branch:** `rick/copilot-cli-f7-egress-staging-evidence`

---

## 1. Objective

Validate egress profile artifacts in live-staging mode — resolver dry-run, nft
syntax check, contract verifier — **without applying nft rules or activating egress.**

Does NOT:
- Apply nft live (`nft -f`)
- Activate `copilot_cli.egress.activated`
- Change `RICK_COPILOT_CLI_EXECUTE`
- Change `_REAL_EXECUTION_IMPLEMENTED`
- Create Docker network
- Execute Copilot or use token
- Restart worker

---

## 2. Phase A — Preflight

| Item | Value |
|---|---|
| Live HEAD | `5d29df0` |
| MainPID | `1418206` |
| `/health` | 200 |
| `copilot_cli.enabled` (L2) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (L3) | `false` |
| `egress.activated` (L4) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (L5) | `False` |
| Live nft copilot rules | **none** |
| Live Docker network copilot | **none** |

---

## 3. Phase B — Egress Artifacts Inventory

| File | Size | Status |
|---|---|---|
| `infra/networking/copilot-egress.nft.example` | 3477 B | present |
| `infra/networking/copilot-egress-resolver.md` | 5263 B | present |
| `scripts/verify_copilot_egress_contract.py` | 10485 B | present |
| `scripts/copilot_egress_resolver.py` | 10820 B | present |

**nft example header confirms:**
- `# NOTE: THIS FILE IS A REPO TEMPLATE — DO NOT APPLY IN F6 STEP 3.`
- Declares `table inet copilot_egress` with `set copilot_v4`, `set copilot_v6`
- Default policy: `type filter hook output priority 0; policy drop;`
- Allows: loopback, established/related, DNS (127.0.0.53), TCP 443 to `@copilot_v4`/`@copilot_v6`
- All chains have default deny + log drop for audit

**Policy egress block (`config/tool_policy.yaml`):**
```yaml
egress:
  profile_name: copilot-egress
  activated: false
  allowed_endpoints:
    - api.githubcopilot.com:443
    - api.individual.githubcopilot.com:443
    - api.business.githubcopilot.com:443
    - api.enterprise.githubcopilot.com:443
    - api.github.com:443
    - copilot-proxy.githubusercontent.com:443
  blocked_by_default:
    - "*"
  enforcement: docker network + egress firewall (nftables) + deny-by-default
```

---

## 4. Phase C — Contract Verifier

```
python3 scripts/verify_copilot_egress_contract.py
→ OK
```

---

## 5. Phase D — Resolver Dry-Run

**JSON output (no writes, `would_apply: false`):**

```json
{
  "dry_run": true,
  "would_apply": false,
  "generated_at": "2026-05-05T17:32:19Z",
  "ip_sets": {
    "copilot_v4": ["140.82.113.21", "4.228.31.149", "4.228.31.153"],
    "copilot_v6": []
  },
  "endpoints": [
    {"endpoint": "api.githubcopilot.com:443",            "v4": ["140.82.113.21"]},
    {"endpoint": "api.individual.githubcopilot.com:443", "v4": ["140.82.113.21"]},
    {"endpoint": "api.business.githubcopilot.com:443",   "v4": ["140.82.113.21"]},
    {"endpoint": "api.enterprise.githubcopilot.com:443", "v4": ["140.82.113.21"]},
    {"endpoint": "api.github.com:443",                   "v4": ["4.228.31.149"]},
    {"endpoint": "copilot-proxy.githubusercontent.com:443","v4": ["4.228.31.153"]}
  ],
  "errors": []
}
```

**NFT output (dry-run, commented — NOT a live command):**
```
# DRY-RUN OUTPUT — DO NOT PIPE INTO `nft`.
# would_apply: False
# nft flush set inet copilot_egress copilot_v4
# nft add element inet copilot_egress copilot_v4 { 140.82.113.21, 4.228.31.149, 4.228.31.153 }
# (no IPv6 addresses resolved)
```

IP set summary (as of 2026-05-05T17:32:19Z):
- `140.82.113.21` — GitHub Copilot API cluster (4 endpoints)
- `4.228.31.149` — api.github.com
- `4.228.31.153` — copilot-proxy.githubusercontent.com
- IPv6: none resolved

---

## 6. Phase E — Staged Candidate

Template copied to `/tmp/copilot-egress-f7r4b.nft` (93 lines). NOT committed.
Confirms header: `# NOTE: THIS FILE IS A REPO TEMPLATE — DO NOT APPLY IN F6 STEP 3.`

---

## 7. Phase F — Parse-Check

```bash
nft -c -f /tmp/copilot-egress-f7r4b.nft   # as user rick
→ netlink: Error: cache initialization failed: Operation not permitted
→ exit=1

sudo nft -c -f /tmp/copilot-egress-f7r4b.nft   # with root
→ exit=0 (PASS)
```

**Finding:** `nft -c` requires kernel netlink cache initialization which needs root
even in check-only mode (`-c`). The template syntax is **valid** (sudo confirms exit=0).
Non-root failure is a permission boundary, not a syntax error.

**No `nft -f` was run** — only check mode with sudo.

---

## 8. Phase G — No Live Mutation

| Check | Result |
|---|---|
| nft copilot rules | **none** |
| Docker network copilot | **none** |
| Worker MainPID | `1418206` (unchanged) |
| `/health` | 200 |

---

## 9. Phase H — Task Probe Still Blocked

```json
{
  "would_run": false,
  "phase_blocks_real_execution": true,
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "execute_enabled": false,
    "phase_blocks_real_execution": true
  },
  "egress_activated": false
}
```

✅ L3 still closed. No subprocess. No Copilot HTTPS.

---

## 10. Summary

| Component | Status |
|---|---|
| Egress contract verifier | ✅ OK |
| Resolver dry-run (JSON) | ✅ 6 endpoints, 3 IPv4 addrs, no errors |
| Resolver dry-run (nft) | ✅ dry-run only, commented, would_apply=false |
| nft template syntax | ✅ VALID (`sudo nft -c` exit=0) |
| nft parse-check as user | ⚠️ requires root (netlink cache) — expected |
| No live nft rules applied | ✅ confirmed |
| No Docker network created | ✅ confirmed |
| Worker unchanged | ✅ PID 1418206, no restart |
| Task probe | ✅ `execute_flag_off_dry_run` |
| egress.activated | ✅ `false` |
| All 5 gates unchanged | ✅ L3/L4/L5 closed |

---

## 11. Gate Stack — Current State

```
L1  RICK_COPILOT_CLI_ENABLED=true       [open]
L2  copilot_cli.enabled=true            [open]
L3  RICK_COPILOT_CLI_EXECUTE=false      [closed]
L4  egress.activated=false              [closed — verified, profile ready but not applied]
L5  _REAL_EXECUTION_IMPLEMENTED=False   [closed — code constant]
```

**Egress readiness:** Template syntax valid. Resolver dry-run resolves all 6
allowlisted endpoints. IP sets ready. Awaiting: (a) operator approval + (b)
`_REAL_EXECUTION_IMPLEMENTED=True` PR before any live apply makes sense.

---

## 12. Next Steps (each requires David's explicit approval)

1. **Rehearsal 4C** (if approved): apply nft egress profile live (L4 activation only),
   verify with `nft list table inet copilot_egress`, no Copilot execution yet.
2. **Rehearsal 5** (if approved): open L3+L5 together → first real Docker container
   launch with authenticated Copilot (sandbox, --network=copilot, egress enforced).

**STOP — no egress activation, no `_REAL_EXECUTION_IMPLEMENTED=True`, no L3 flip.**
