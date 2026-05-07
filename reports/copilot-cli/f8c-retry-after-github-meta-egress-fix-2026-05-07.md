# F8C — retry direct Copilot diagnostic with GitHub Meta CIDR egress

- **Date (UTC):** 2026-05-07
- **Task:** [.agents/tasks/f8c-retry-after-github-meta-egress-fix-2026-05-07.md](../../.agents/tasks/f8c-retry-after-github-meta-egress-fix-2026-05-07.md)
- **Branch:** `rick/f8c-retry-after-github-meta-egress-fix-2026-05-07`
- **Approval:** `APPROVE_F8C_GITHUB_META_EGRESS_RETRY=YES` — present in invocation.
- **Operator:** `copilot-vps`
- **Reviewer:** `codex` (cc in PR body if reviewer assignment fails)
- **Backup dir:** `/home/rick/.copilot/backups/f8c-github-meta-20260507T031212Z/`
- **Run id:** `f8c-direct-20260507T031259Z`
- **Verdict:** `amarillo`

## 0. Approval and source verification (O0)

| Check | Result |
|---|---|
| `APPROVE_F8C_GITHUB_META_EGRESS_RETRY=YES` | present |
| Resolver fix in `main` (`c55676a`) | yes — HEAD `32558a3` |
| `--include-github-meta` in resolver | yes (`scripts/copilot_egress_resolver.py:450`) |
| `GITHUB_META_KEYS = ("api", "web", "copilot_api")` | yes (line 38) |
| `python3 scripts/verify_copilot_egress_contract.py` | `OK` |

## 1. Token / CLI capability (O1)

| Variable | Status |
|---|---|
| Worker restart | `OLD_PID=25636 NEW_PID=29933` |
| `worker_health` | `200` |
| `COPILOT_GITHUB_TOKEN` | `present_by_name` |
| `RICK_COPILOT_CLI_EXECUTE` | `false` |
| `GITHUB_USER_HTTP` | `200` |
| `TOKEN_STATUS` | `valid` |

Token value never printed; only `present_by_name` emitted.

Sandbox image: `umbral-sandbox-copilot-cli:6940cf0f274d`. Copilot CLI 1.0.36
from F8B unchanged. `--model` is a documented flag. Copilot CLI does not
expose a `--list-models` style command in `--help`; help mentions only
`copilot --model gpt-5.2` as example. (See §6 for runtime model error.)

## 2. Resolver with GitHub Meta CIDRs (O2)

```text
copilot_v4_count=37
copilot_v6_count=2
github_meta_included=True
github_meta_errors=[]
has_140_82_112_0_20=True
v4 sample: ['4.208.26.197/32', '4.208.26.200/32', '4.225.11.194/32',
            '4.225.11.201/32', '4.228.31.149/32', '4.228.31.150/32', ...]
```

GitHub Meta `api` CIDR `140.82.112.0/20` is **present** in `copilot_v4`,
satisfying the explicit O2 stop gate.

In the loaded nft table, set membership confirmed:

```text
copilot_v4 set line 21: 20.233.83.146, 140.82.112.0/20, ...
```

## 3. Direct probe (O4)

| Field | Value |
|---|---|
| `RUN_ID` | `f8c-direct-20260507T031259Z` |
| `DIRECT_RC` | `1` |
| `stdout_bytes` | `0` |
| `stderr_bytes` | `104` |
| Wall-clock duration | `4.606 s` |

`stderr` (full content, no secrets):

```text
F8C_CONTAINER_READY_MS=1778123556212
Error: Model "Claude Opus 4.7" from --model flag is not available.
```

`stdout`: empty.

The CLI exited within ~4.6 s (vs ~43.4 s in F8B) because the failure now
occurs at **model-selection** time, not at network-retry time.

## 4. nft accept/drop summary (O5)

```text
ACCEPTED:
      1  4.228.31.149      (api.github.com)
      2  140.82.113.21     (lb-140-82-113-21-iad.github.com — was the dropped IP in F8B)
DROPPED:
  (none)
```

`140.82.113.21`, the IP that produced 35/36 drops in F8B, is now **accepted**
because it falls inside the published `140.82.112.0/20` GitHub Meta `api`
CIDR present in the scoped allow-list. **The egress fix works.**

## 5. Structured metrics JSON (O5)

`/home/rick/.copilot/backups/f8c-github-meta-20260507T031212Z/f8c-metrics.json`:

```json
{
  "container_ready_ms": 288,
  "copilot_exit_ms": 4606,
  "docker_start_ms": 0,
  "first_stdout_byte_ms": null,
  "nft_drop_delta": {
    "bytes": 0,
    "packets": 0
  },
  "stderr_bytes": 104,
  "stdout_bytes": 0
}
```

**`nft_drop_delta = 0 packets / 0 bytes`** — the F8B drop pattern is fully
eliminated by the GitHub Meta CIDR egress fix.

`first_stdout_byte_ms` is `null` because no stdout byte was emitted (the CLI
errored before producing model output).

## 6. Secret scan

```text
direct.out:       clean
direct.err:       clean
f8c-egress.json:  clean
f8c-metrics.json: clean
```

No `gh*`/`sk-*`/`AKIA*`/PEM patterns detected in any artifact. The CLI
respected `--secret-env-vars=COPILOT_GITHUB_TOKEN`.

## 7. Rollback proof (O6)

```text
nft table deleted
docker network removed
worker_health=200
no copilot nft table
no copilot-egress docker network
no host-wide output drop, no residual copilot_egress
```

- nft table `inet copilot_egress` removed.
- Docker network `copilot-egress` removed (created by this task,
  flag `/tmp/f8c-network-created-by-task=true`).
- Pre-change ruleset preserved at
  `/home/rick/.copilot/backups/f8c-github-meta-20260507T031212Z/nft-ruleset-before.nft`
  (chmod 0600).
- Worker `/health=200` post-rollback.

## 8. Root-cause separation: egress vs. model-availability

F8B failure mode → resolved.
F8C failure mode → distinct, **not** an egress problem:

```text
Error: Model "Claude Opus 4.7" from --model flag is not available.
```

This is an explicit, non-secret error from the Copilot CLI's own model
catalog. `Claude Opus 4.7` is allow-listed in `config/tool_policy.yaml`
(operator-side gate) but is **not** in the set of models that the GitHub
Copilot backend exposes to this token through the CLI's `--model` flag.

The only example in `copilot --help` is `--model gpt-5.2`, suggesting the
backend gates models per account/plan and that `Claude Opus 4.7` requires
either a different SKU/entitlement or a slightly different display name.

## 9. Verdict and rationale

**`amarillo`.**

Per task spec (§Verdict rules):

- ❌ `verde` requires `direct probe exits 0`, `stdout contains F8C_OK`, and
  `nft_drop_delta.packets == 0`. We have only the third condition.
- ✅ `amarillo` covers "direct probe exits non-zero, but ... provider/model
  auth returns an explicit non-secret error." We have an explicit non-secret
  model-availability error from the CLI itself.
- ❌ `rojo` triggers (token failure, missing `140.82.112.0/20`, host-wide
  drop, secret leak, rollback failure, unmappable drops) all absent.

The egress fix is **proven correct** at the network layer
(`nft_drop_delta.packets == 0`, formerly-dropped IP `140.82.113.21` now
accepted). The remaining blocker is purely Copilot-backend model entitlement.

## 10. Recommendations

1. **Egress allow-list is good** — keep `--include-github-meta` in the
   runtime nft populate step before the next canonical `copilot_cli.run`.

2. **Resolve model name / entitlement.** Two non-intrusive checks before
   another probe (no `copilot_cli.run` needed):
   - Confirm the exact display name accepted by the backend: try a follow-up
     diagnostic with `--model "Claude 4 Opus"`, `"claude-opus-4.7"`, or
     `"claude-3.7-opus"`. Copilot CLI conventionally accepts
     hyphen-lowercase canonical IDs (e.g. `gpt-5.2`).
   - Verify the GitHub Copilot account/plan attached to the current
     `COPILOT_GITHUB_TOKEN` actually exposes `Claude Opus 4.7`. If the
     account is on a tier that exposes only GPT-class models, this run
     pattern is structurally infeasible regardless of allow-list.

3. **Optional fallback test** to isolate the model question entirely:
   one more F8-style direct probe **omitting** `--model` (default model)
   should produce stdout containing `F8C_OK` and confirm verde-equivalent
   behavior on the egress path.

4. **No Plan B trigger.** All accepted/dropped traffic in this window mapped
   cleanly to GitHub Meta CIDRs; off-host gateway/proxy is not warranted.

## 11. Artifacts

| Path | Purpose |
|---|---|
| `/home/rick/.copilot/backups/f8c-github-meta-20260507T031212Z/nft-ruleset-before.nft` | Pre-change full ruleset (0600). |
| `…/nft-table-during-before.txt` | Scoped table after sets loaded, before probe. |
| `…/nft-table-during-after.txt` | Scoped table after probe. |
| `…/kernel-nft-window.txt` | 3 kernel log lines from probe window. |
| `…/drop-summary.txt` | accept/drop classification by DST. |
| `…/f8c-egress.json` | Resolver output snapshot (with Meta CIDRs). |
| `…/f8c-metrics.json` | Structured metrics JSON. |
| `…/direct.out` | Probe stdout (0 bytes). |
| `…/direct.err` | Probe stderr (104 bytes — readiness marker + model error). |
