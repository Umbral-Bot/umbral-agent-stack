# F7 Rehearsal 4C — nft Live Apply + Rollback: Live Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Live HEAD at execution:** `62290b4` (main advanced from `8aa863d` via agent task commits)
**Evidence branch HEAD:** `a58e30a`
**MainPID throughout:** `1418206` (no restart)
**Evidence branch:** `rick/copilot-cli-f7-nft-live-rollback-evidence`

---

## 1. Objective

Apply `table inet copilot_egress` live in the kernel nftables stack, confirm
worker stays healthy and task remains blocked by L3, then **rollback immediately**
by deleting the table. Verify no persistent side-effects.

Does NOT:
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
| Live HEAD | `62290b4` |
| MainPID | `1418206` |
| `/health` | 200 |
| `copilot_cli.enabled` (L2) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (L3) | `false` |
| `egress.activated` (L4 policy) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (L5) | `False` |
| Pre-existing `inet copilot_egress` table | **none** (clean start) |
| Docker network copilot | **none** |

---

## 3. Phase B — Backup

```
backup=/home/rick/.copilot/backups/nft-ruleset-before-f7r4c-20260505T181309Z.nft
lines: 544 (existing iptables-nft + Docker bridge rules)
chmod 0600 applied
```

Backup warnings (expected): `iptables-nft` managed tables — not touched by this rehearsal.

---

## 4. Phase C — Candidate

```
candidate=/tmp/copilot-egress-f7r4c.nft
source: infra/networking/copilot-egress.nft.example
lines: 93
```

---

## 5. Phase D — Parse-Check

```bash
sudo nft -c -f /tmp/copilot-egress-f7r4c.nft
parse_check_exit=0   ✅ VALID
```

---

## 6. Phase E — Apply Live

```bash
sudo nft -f /tmp/copilot-egress-f7r4c.nft
apply_exit=0   ✅
```

Table verified after apply (`sudo nft list table inet copilot_egress`):
```
table inet copilot_egress {
    set copilot_v4 { type ipv4_addr; flags interval }
    set copilot_v6 { type ipv6_addr; flags interval }
    chain output {
        type filter hook output priority filter; policy drop;
        oifname "lo" accept
        ct state established,related accept
        udp dport 53 ip daddr 127.0.0.53 accept
        udp dport 53 ip daddr @copilot_v4 accept
        tcp dport 443 ip daddr @copilot_v4 log prefix "copilot-egress accept v4: " ...
        tcp dport 443 ip6 daddr @copilot_v6 log prefix "copilot-egress accept v6: " ...
        log prefix "copilot-egress DROP: " flags all; counter drop
    }
    chain input  { type filter hook input  priority filter; policy drop; ... }
    chain forward{ type filter hook forward priority filter; policy drop; }
}
```

Note: IP sets `copilot_v4` and `copilot_v6` are **empty** — table was applied from
template without running the resolver to populate them. This is intentional for
rehearsal (validates apply/rollback mechanics only, not full egress routing).

---

## 7. Phase F — Post-Apply Health

| Check | Result |
|---|---|
| MainPID | `1418206` — **unchanged** |
| `/health` | 200 ✅ |
| Docker network copilot | **none** |
| `egress.activated` (policy yaml) | `false` — unchanged |

Worker remained healthy with the nft table in place. Host-level firewall table
does not affect the worker process binding on loopback `127.0.0.1:8088`.

---

## 8. Phase G — Task Probe (With nft Table Active)

```json
{
  "would_run": false,
  "decision": "execute_flag_off_dry_run",
  "policy": { "execute_enabled": false },
  "egress_activated": false
}
```

✅ L3 still blocks. `egress_activated=false` because policy yaml unchanged.
No subprocess. No Copilot HTTPS. IP sets were empty anyway.

---

## 9. Phase H — Rollback

```bash
sudo nft delete table inet copilot_egress
rollback_exit=0   ✅

sudo nft list table inet copilot_egress
→ "copilot table removed"   ✅
```

Worker health after rollback:
- MainPID: `1418206` — unchanged
- `/health`: 200 ✅

---

## 10. Phase I — Final Side-Effect Check

| Check | Result |
|---|---|
| `RICK_COPILOT_CLI_EXECUTE` | `false` — unchanged |
| `RICK_COPILOT_CLI_ENABLED` | `true` — unchanged |
| `egress.activated` | `false` — unchanged |
| `_REAL_EXECUTION_IMPLEMENTED` | `False` — unchanged |
| `inet copilot_egress` table | **removed** ✅ |
| Docker network copilot | **none** ✅ |

---

## 11. Summary

| Phase | Result |
|---|---|
| Preflight | ✅ no pre-existing table |
| Backup | ✅ 544-line snapshot at `/home/rick/.copilot/backups/` |
| Parse-check | ✅ exit=0 |
| Apply live | ✅ exit=0 — table created with 3 chains, 2 sets |
| Post-apply health | ✅ worker PID 1418206, /health 200 |
| Task probe (table active) | ✅ `execute_flag_off_dry_run`, `egress_activated=false` |
| Rollback | ✅ exit=0 — table deleted cleanly |
| Post-rollback health | ✅ worker PID 1418206, /health 200 |
| Final gates | ✅ all 5 unchanged |

---

## 12. Gate Stack — Current State

```
L1  RICK_COPILOT_CLI_ENABLED=true       [open]
L2  copilot_cli.enabled=true            [open]
L3  RICK_COPILOT_CLI_EXECUTE=false      [closed]
L4  egress.activated=false              [closed — nft mechanics verified, profile ready]
L5  _REAL_EXECUTION_IMPLEMENTED=False   [closed — code constant]
```

**nft mechanics fully validated:**
- Apply: `nft -f` works, table loads, chains hook correctly
- Rollback: `nft delete table inet copilot_egress` removes cleanly in one command
- Worker: unaffected by nft table presence/absence on loopback binding
- Task: blocked by L3 regardless of nft state

**IP sets note:** Sets were empty during this rehearsal. For real egress (Rehearsal 5+),
resolver must populate `copilot_v4` before activating `egress.activated=true`.

---

## 13. Next Steps (each requires David's explicit approval)

1. **Rehearsal 5** (if approved): open L3 (`RICK_COPILOT_CLI_EXECUTE=true`) +
   flip L5 (`_REAL_EXECUTION_IMPLEMENTED=True` via PR) + apply nft with populated
   IP sets + create Docker network + run first authenticated Copilot task in sandbox.

**STOP — no egress activation, no `_REAL_EXECUTION_IMPLEMENTED=True`, no L3 flip.**
