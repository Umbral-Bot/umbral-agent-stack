# F8B — diagnose Copilot egress drops and model-power path

- **Date (UTC):** 2026-05-07
- **Task:** [.agents/tasks/f8b-diagnose-egress-and-model-power-2026-05-07.md](../../.agents/tasks/f8b-diagnose-egress-and-model-power-2026-05-07.md)
- **Branch:** `rick/f8b-diagnose-egress-and-model-power-2026-05-07`
- **Approval:** `APPROVE_F8B_EGRESS_MODEL_DIAGNOSTIC=YES` — present in invocation.
- **Operator:** `copilot-vps` (David's Copilot agent on VPS)
- **Reviewer:** `codex`
- **Backup dir:** `/home/rick/.copilot/backups/f8b-egress-model-20260507T025022Z/`
- **Run id:** `f8b-direct-20260507T025114Z`
- **Verdict:** `amarillo`

## 0. Approval and pre-conditions

| Check | Result |
|---|---|
| `APPROVE_F8B_EGRESS_MODEL_DIAGNOSTIC=YES` | present |
| PR #324 in `main` | yes — merge commit `27927f1` is HEAD of `origin/main` |
| `get_copilot_cli_allowed_models` defined | yes — `worker/tool_policy.py:131` |
| `--model` accepted by `worker/tasks/copilot_cli.py` | yes — `copilot_cli.py:511` |
| `Claude Opus 4.7` in `config/tool_policy.yaml` | yes — line 50 |
| `scripts/verify_copilot_egress_contract.py` | `OK` |
| Worker `/health` (post restart) | `200` |

## 1. Token status (no value printed)

| Variable | Status |
|---|---|
| `COPILOT_GITHUB_TOKEN` | `present_by_name` |
| `RICK_COPILOT_CLI_EXECUTE` | `false` |
| `GITHUB_USER_HTTP` | `200` |
| `TOKEN_STATUS` | `valid` |

Worker restart: `OLD_PID=20796 NEW_PID=25636`.

Token never printed; only `COPILOT_GITHUB_TOKEN=present_by_name` emitted to logs.
The `--secret-env-vars=COPILOT_GITHUB_TOKEN` flag was passed to `copilot` so the
CLI redacts the value from its own debug logs.

## 2. Copilot CLI capability

```text
GitHub Copilot CLI 1.0.36.
Run 'copilot update' to check for updates.
```

Help excerpt for `--model` and tool gating (sandbox image
`umbral-sandbox-copilot-cli:6940cf0f274d`):

```text
--model <model>                       Set the AI model to use
--available-tools[=tools...]          Only these tools will be available to ...
--allow-tool[=tools...]               Tools the CLI has permission to use; ...
--deny-tool[=tools...]                Tools the CLI does not have permission ...
--allow-all                           Enable all permissions (equivalent to ...)
--allow-all-tools                     Allow all tools to run automatically
$ copilot --model gpt-5.2
```

`--model` is a documented flag. The CLI accepted `--model "Claude Opus 4.7"`
without raising a "model not found" error during the 43.4 s before silent exit;
no model-allowlist or auth error appears in stderr (stderr only contains the
container-readiness marker — see §4).

**Model requested:** `Claude Opus 4.7` (allow-listed in `config/tool_policy.yaml`).

## 3. Egress allow-list snapshot (resolver)

`python3 scripts/copilot_egress_resolver.py --non-strict --format json`:

```text
copilot_v4_count=3
copilot_v6_count=0
copilot_v4 = ['140.82.114.21', '4.228.31.149', '4.228.31.153']
```

Per-FQDN resolution at probe time:

| FQDN | Resolved A |
|---|---|
| `api.githubcopilot.com` | `140.82.114.21` |
| `api.individual.githubcopilot.com` | `140.82.114.21` |
| `api.business.githubcopilot.com` | `140.82.114.21` |
| `api.enterprise.githubcopilot.com` | `140.82.114.21` |
| `api.github.com` | `4.228.31.149` |
| `copilot-proxy.githubusercontent.com` | `4.228.31.153` |

## 4. Direct probe — exit / output

| Field | Value |
|---|---|
| `RUN_ID` | `f8b-direct-20260507T025114Z` |
| `DIRECT_RC` | `1` |
| `stdout_bytes` | `0` |
| `stderr_bytes` | `37` |
| Wall-clock duration | `43.794 s` |

`stderr` excerpt (full content, no secrets):

```text
F8B_CONTAINER_READY_MS=1778122272849
```

`stdout`: empty.

The CLI received the prompt, started, contacted `api.github.com`
(`4.228.31.149`, accepted), then attempted to talk to a `*.githubcopilot.com`
LB IP that was **not** in the allow-list (see §6) and exited `1` with no
diagnostic output after ~43 s of SYN retries.

## 5. nft counter delta

Before:

```text
counter packets 0 bytes 0 drop
```

After:

```text
counter packets 36 bytes 2160 drop
```

Delta: **36 packets / 2160 bytes** dropped — identical magnitude to F8A run-6,
confirming the symptom is reproducible and deterministic.

## 6. Kernel nft drop logs (no secrets)

`sudo journalctl -k --since … --until … | grep copilot-egress` produced 36
lines. Per-DST classification:

| Decision | Count | DST |
|---|---|---|
| accept v4 | 1 | `4.228.31.149` (`api.github.com`) |
| **DROP scoped** | **35** | **`140.82.113.21`** |

Reverse DNS of dropped destination:

```text
140.82.113.21 -> lb-140-82-113-21-iad.github.com
```

Sample drop line (sanitized — no secret material is present in iptables logs):

```text
May 06 22:51:16 srv1431451 kernel: copilot-egress DROP scoped:
  IN=br-copilot OUT=eth0 PHYSIN=vethee6f72e
  SRC=172.18.0.2 DST=140.82.113.21
  PROTO=TCP SPT=47130 DPT=443 SYN
```

The container retried connect() to the same `140.82.113.21:443` (35 SYNs over
~38 s, then connect() to one new source port, then exit 1).

## 7. Structured metrics JSON

`/home/rick/.copilot/backups/f8b-egress-model-20260507T025022Z/f8b-metrics.json`:

```json
{
  "container_ready_ms": 362,
  "copilot_exit_ms": 43794,
  "docker_start_ms": 0,
  "first_stdout_byte_ms": null,
  "first_stdout_byte_ms_semantics": "upper_bound_process_exit_time_when_stdout_nonempty",
  "nft_drop_delta": {
    "bytes": 2160,
    "packets": 36
  },
  "stderr_bytes": 37,
  "stdout_bytes": 0
}
```

Notes:

- `docker_start_ms` is `0` because the host did not instrument pre-`docker run`
  start time separately from the `HOST_T0_MS` snapshot taken immediately before
  the `docker run` invocation. Container readiness was 362 ms after that
  snapshot, which is a reasonable upper bound on Docker startup.
- `first_stdout_byte_ms` is `null` because the run produced 0 bytes of stdout;
  no first byte was ever emitted.

## 8. Rollback proof

```text
nft table deleted
docker network removed
worker_health=200
no copilot nft table
no copilot-egress docker network
no host-wide output drop, no residual copilot_egress
```

- nft table `inet copilot_egress` removed.
- docker network `copilot-egress` removed (this task created it; flag
  `/tmp/f8b-network-created-by-task=true`).
- Worker `/health=200` after rollback.
- `nft list ruleset` shows no host-wide `output policy drop` and no residual
  `copilot_egress` references.
- Pre-change ruleset preserved at
  `/home/rick/.copilot/backups/f8b-egress-model-20260507T025022Z/nft-ruleset-before.nft`
  (chmod 0600).

## 9. Root cause

The scoped allow-list is built from one A-record per FQDN at resolution time,
but GitHub Copilot's LB pool returns **different** IPs per resolution within
the `140.82.112.0/20` range:

- Snapshotted: `api.githubcopilot.com` → `140.82.114.21` (in allow-list).
- Container's libc resolver picked: `140.82.113.21` (NOT in allow-list).

Both IPs belong to the same GitHub-published `api` CIDR
(`140.82.112.0/20`, declared in `https://api.github.com/meta`), but the
resolver script narrows the allow-list to the single resolution it observed.
This produces a deterministic drop whenever the container resolves a different
A-record from the same RR pool.

The auth path (`api.github.com`) succeeded because its single resolved IP
(`4.228.31.149`) happens to match the in-container resolution. The model/data
path (`*.githubcopilot.com`) failed because the container resolved a sibling
LB IP. Result: silent CLI exit `1` with empty stdout/stderr.

This explains why F8A run-6 also had exactly 36 packets / 2160 bytes drop:
same RR/LB instability, same symptom.

## 10. Recommendation

Two complementary fixes (apply at least #1):

### Fix 1 — Use GitHub Meta CIDRs (preferred)

Modify [scripts/copilot_egress_resolver.py](../../scripts/copilot_egress_resolver.py)
to **replace** per-FQDN A-record snapshotting for `*.github.com` and
`*.githubcopilot.com` hosts with the published CIDRs from
`https://api.github.com/meta`:

- `meta.api` (currently includes `140.82.112.0/20`, the relevant GitHub
  control-plane block, plus Azure ranges).
- `meta.web` (covers user-facing endpoints if the CLI ever needs them).
- `meta.copilot_api` (if present in the API response — pin to it explicitly).

This makes the allow-list resilient to LB churn within GitHub's published
ranges without opening egress beyond what GitHub already declares as
authoritative.

### Fix 2 — Static fallback supplement

Until the resolver is updated, add the supplemental v4 entries
**`140.82.112.0/20`** to the runtime nft populate step, behind a feature flag
in the resolver (`--include-github-meta`), and bump
`copilot_v4_count` to include the CIDR (nft set element supports CIDR).

After either fix, re-run F8B to confirm `nft_drop_delta == {0, 0}` and a
non-empty stdout from a single `copilot --prompt` probe with
`--model "Claude Opus 4.7"`. **Only then** authorize a new canonical
`copilot_cli.run` (Plan A continues).

### Plan B trigger — NOT yet armed

Plan B (off-host gateway / proxy) is **not** required: dropped destinations
are stable, FQDNs map cleanly to GitHub Meta CIDRs, and reverse DNS confirms
they belong to GitHub's own LB pool. Reassess only if a future run drops
packets to IPs **outside** `meta.api ∪ meta.web ∪ meta.copilot_api`.

## 11. Verdict and rationale

**`amarillo`.** Token valid (200), CLI accepted `--model "Claude Opus 4.7"`,
infra path clean, rollback verified clean, no host-wide policy change, no
secret leak. The only failure mode is a missing IP in the scoped allow-list,
fully attributable to GitHub LB DNS round-robin within a known/published
CIDR. Concrete fix is identified (§10) and reversible.

Not `verde` because the direct probe still exited `1` with no output and there
was a non-zero `nft_drop_delta`. Not `rojo` because no rule was opened
beyond the scoped table, no token was printed, no host-wide drop was
introduced, and rollback succeeded.

## 12. Artifacts

| Path | Purpose |
|---|---|
| `/home/rick/.copilot/backups/f8b-egress-model-20260507T025022Z/nft-ruleset-before.nft` | Full pre-change ruleset (0600). |
| `…/nft-table-during-before.txt` | Scoped table after load, before probe. |
| `…/nft-table-during-after.txt` | Scoped table after probe. |
| `…/kernel-nft-window.txt` | 36 kernel log lines from probe window. |
| `…/dropped-dst.txt` | Sorted unique dropped DST IPs. |
| `…/accepted-dst.txt` | Sorted unique accepted DST IPs. |
| `…/f8b-egress.json` | Resolver output snapshot. |
| `…/f8b-metrics.json` | Structured metrics JSON. |
| `…/direct.out` | Probe stdout (0 bytes). |
| `…/direct.err` | Probe stderr (37 bytes — readiness marker only). |
