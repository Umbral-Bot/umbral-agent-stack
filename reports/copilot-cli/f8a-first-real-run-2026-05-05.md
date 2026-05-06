# F8A — first controlled real Docker execution — VPS evidence

**Date:** 2026-05-06T04:11:34Z (run completion)  
**Executed by:** copilot-vps  
**Repo HEAD (main):** `7e21ea6efa05f4901f30ba48275d33bc70414fa9`  
**Approval line present:** `APPROVE_F8A_ONE_SHOT_RUN=YES` ✅

---

## Verdict

🟡 **AMARILLO**

End-to-end F8A infrastructure path validated successfully:

- L3+L4 opened cleanly, Docker sandbox spawned with full security profile, nft
  egress active with resolved Copilot IPs, token plumbed via env (never
  printed), wrapper executed Copilot CLI binary inside container, all artifacts
  + manifest + audit JSONL written, rollback executed cleanly to closed state.

The Copilot CLI binary itself **exited 1** with a CLI-flag error: the wrapper
invokes `copilot --no-banner` but the installed Copilot CLI version no longer
accepts that flag (`error: unknown option '--no-banner' (Did you mean --banner?)`).
This is a **wrapper-side bug**, not a security/sandbox failure.

No tokens leaked. No artifacts written outside the bind-mounted artifact dir.
Egress + L3 reverted. System fully back to pre-F8A safe state.

---

## Executive summary

| Phase | Result |
|---|---|
| O1 deploy verification (L3 closed) | ✅ pass — `execute_flag_off_dry_run` |
| O2.1 backup | ✅ envfile + tool_policy.yaml + nft ruleset chmod 0600 |
| O2.2 nft apply + L4 flip | ✅ table `inet copilot_egress` live, `copilot_v4` populated with `140.82.112.21`, `egress.activated=true` in working tree |
| O2.3 sandbox image + L3 flip + restart | ✅ image `umbral-sandbox-copilot-cli:6940cf0f274d`, `bridge` network, PID `3669` (active/running, HTTP 200) |
| O2.4 one-shot real run | 🟡 executed — Copilot CLI exited 1 (wrong flag), 2.718s, no output |
| O3 rollback | ✅ envfile + policy restored, nft table deleted, worker PID `3815` (post-rollback), HTTP 200 |
| Token scans | ✅ stderr, audit JSONL, manifest all clean |

---

## Gate matrix — before / during / after

| Layer | Before O2 | During O2.4 (run window) | After rollback |
|---|---|---|---|
| **L1** `RICK_COPILOT_CLI_ENABLED` | `true` ✅ | `true` ✅ | `true` ✅ |
| **L2** `copilot_cli.enabled` | `true` ✅ | `true` ✅ | `true` ✅ |
| **L3** `RICK_COPILOT_CLI_EXECUTE` | `false` ❌ CLOSED | `true` ⚠️ OPEN (PID `3669`) | `false` ❌ CLOSED (PID `3815`) |
| **L4** `egress.activated` | `false` ❌ + no nft table | `true` ⚠️ + nft `inet copilot_egress` live | `false` ❌ + no nft table |
| **L5** `_REAL_EXECUTION_IMPLEMENTED` | `True` ✅ (line 54) | `True` ✅ | `True` ✅ |

---

## One-shot real run — captured fields

| Field | Value | Source |
|---|---|---|
| `batch_id` | `f8a-first-real-run` | request metadata |
| `agent_id` | `copilot-vps-single-001` | request metadata |
| `brief_id` | `F8-B1` | request metadata |
| `mission_run_id` | `49a1496515c84826b215ae9d8ec400e9` | response |
| `decision` | `completed` | response |
| `phase` | `F8A.real_execution` | response |
| `phase_blocks_real_execution` | `false` | response |
| `executed` | `true` | response |
| `would_run` | `false` | response |
| `exit_code` | `1` | Copilot CLI subprocess exit |
| `duration_sec` | `2.718` | wall-clock measured by handler |
| `egress_activated` | `true` | runtime confirmed at request time |
| `tokens.input/output/total` | `null / null / null` | `not_reported_by_github_copilot_cli` |
| `cost_usd.value` | `null` | `not_reported_by_github_copilot_cli` |
| `prompt_sha256` | `319537882ab21529f92abe9924a1c874122ff5a8b74a8ee52b701621c3fcba3d` | manifest |

### Artifact paths

| Artifact | Path | Bytes | sha256 |
|---|---|---|---|
| `manifest.json` | `artifacts/copilot-cli/2026-05/f8a-first-real-run/copilot-vps-single-001/49a1496515c84826b215ae9d8ec400e9/manifest.json` | 2650 | n/a (manifest is the index) |
| `stdout.txt` | (same dir) | **0** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty file digest) |
| `stderr.txt` | (same dir) | **105** | `01efee5715f9ad5314079ec7cc52daf5a571794e0f85b4097b178e3fecad4783` |
| `audit_log` | `reports/copilot-cli/2026-05/49a1496515c84826b215ae9d8ec400e9.jsonl` | 2 lines | (gitignored) |

### stderr content (verbatim, no secrets)

```
error: unknown option '--no-banner'
(Did you mean --banner?)

Try 'copilot --help' for more information.
```

### Audit JSONL summary

- 2 lines (start + completion records)
- Token scan: clean (no `ghp_`, `github_pat_`, `ghs_`, `sk-` patterns)
- Path: `reports/copilot-cli/2026-05/49a1496515c84826b215ae9d8ec400e9.jsonl` (gitignored, on disk)

---

## nft / Docker snapshots

### Before run

- No `inet copilot_egress` table.
- No Docker `copilot*` network.

### During run window

```
table inet copilot_egress {
    set copilot_v4 { type ipv4_addr; flags interval; elements = { 140.82.112.21 } }
    set copilot_v6 { type ipv6_addr; flags interval }
    chain output {
        type filter hook output priority filter; policy drop;
        oifname "lo" accept
        ct state established,related accept
        udp dport 53 ip daddr 127.0.0.53 accept
        udp dport 53 ip daddr @copilot_v4 accept
        tcp dport 443 ip daddr @copilot_v4 log prefix "copilot-egress accept v4: " level info accept
        tcp dport 443 ip6 daddr @copilot_v6 log prefix "copilot-egress accept v6: " level info accept
        log prefix "copilot-egress DROP: " flags all
        counter packets 587 bytes 44713 drop
    }
    chain input { type filter hook input priority filter; policy drop; iifname "lo" accept; ct state established,related accept }
    chain forward { type filter hook forward priority filter; policy drop }
}
```

- Docker network: `bridge` (host default, used by container per envfile `COPILOT_CLI_DOCKER_NETWORK=bridge`).
- Sandbox image: `umbral-sandbox-copilot-cli:6940cf0f274d`.

### After rollback

- No `inet copilot_egress` table.
- No Docker `copilot*` network.
- Worker post-rollback PID `3815`, HTTP 200.

---

## Sandbox spec actually invoked (docker_argv)

```
docker run --rm --network=bridge --read-only \
  --tmpfs /tmp:size=64m,mode=1777,exec,nosuid,nodev \
  --tmpfs /scratch:size=64m,mode=1777,nosuid,nodev \
  --tmpfs /home/runner/.cache:size=32m,mode=1777 \
  --memory=1g --memory-swap=1g --cpus=1.0 --pids-limit=256 \
  --cap-drop=ALL --security-opt no-new-privileges \
  --user 10001:10001 --ipc=none \
  --mount type=bind,source=/home/rick/umbral-agent-stack,target=/work,readonly \
  --workdir /work \
  --name copilot-cli-49a1496515c84826b215ae9d8ec400e9 \
  --stop-timeout 600 \
  --env COPILOT_GITHUB_TOKEN --env NO_COLOR=1 \
  umbral-sandbox-copilot-cli:6940cf0f274d \
  /usr/local/bin/copilot-cli-wrapper /bin/sh -lc '...'
```

Confirmed:
- `--cap-drop=ALL`, `--security-opt no-new-privileges`, `--user 10001:10001`
- `--read-only` rootfs + scoped `--tmpfs` mounts
- Repo bind-mounted **read-only**
- Token passed via env name only (value never inlined into argv)
- `--ipc=none`, `--pids-limit=256`, memory + cpu caps applied

---

## Wrapper command (subprocess inside sandbox)

```sh
set -eu
prompt_file=/tmp/copilot-prompt.txt
cat > "$prompt_file"
exec copilot --no-banner --no-color --no-auto-update --no-remote --no-ask-user \
  --disable-builtin-mcps --secret-env-vars=COPILOT_GITHUB_TOKEN \
  --available-tools=view,grep,glob \
  --output-format=json --stream=off \
  --log-dir=/scratch/copilot-logs \
  --prompt "$(cat "$prompt_file")"
```

**Failing flag:** `--no-banner` is rejected by current Copilot CLI version
inside the sandbox image. Available alternative per error message: `--banner`.
The wrapper command is constructed in `worker/tasks/copilot_cli.py`. **Fix
required in F8A-bugfix follow-up before retrying real run.**

---

## VPS Reality Check notation

```
L1: envfile says true     / VPS process 3669 shows true      → no drift
L2: repo yaml says true   / HEAD 7e21ea6 shows true           → no drift
L3: envfile flipped to true (run window) / process 3669 true  → intended; reverted
L4: yaml flipped to true (run window) / nft live + sets       → intended; reverted
L5: repo says True        / probe real_execution_implemented=true → no drift
```

---

## Secret-output-guard checks

| Check | Result |
|---|---|
| stderr.txt token scan | ✅ clean |
| audit JSONL token scan | ✅ clean |
| manifest.json token scan | ✅ clean (manifest contains no env values) |
| `docker_argv` in response | ✅ env passed by name only (`--env COPILOT_GITHUB_TOKEN`, no value) |
| Worker journalctl window | ✅ no token patterns in any log line examined |
| Backup files chmod | ✅ `0600` on all 3 files (`copilot-cli.env`, `tool_policy.yaml`, `nft-ruleset-before.nft`) |

---

## Rollback evidence

```
RICK_COPILOT_CLI_ENABLED=true        # restored
RICK_COPILOT_CLI_EXECUTE=false       # restored from backup
egress.activated=false               # restored from backup
_REAL_EXECUTION_IMPLEMENTED = True   # unchanged (L5 stays open per F7.5A)
no copilot nft table                 # deleted
no copilot docker network            # never created
HTTP 200                             # worker healthy after rollback restart
PID 3815                             # post-rollback PID
process RICK_COPILOT_CLI_ENABLED=true
process RICK_COPILOT_CLI_EXECUTE=false
```

Backup directory (kept on disk for audit, chmod 0600):
`/home/rick/.copilot/backups/f8a-retry-20260506T040932Z/`

---

## Findings & next steps

### Finding 1 — Wrapper uses obsolete CLI flag (P1)

**Issue:** `worker/tasks/copilot_cli.py` builds the in-sandbox subprocess
command with `--no-banner`, which is no longer accepted by the Copilot CLI
version installed in `umbral-sandbox-copilot-cli:6940cf0f274d`.

**Impact:** Every real F8A run will fail at startup with exit 1 until the flag
is fixed. No security impact — sandbox/egress/token isolation worked as designed.

**Recommended fix:** Drop `--no-banner` from the exec line in the wrapper
command; the `--no-color` flag suffices for non-interactive output, and Copilot
CLI's banner is informational only.

### Finding 2 — Egress IPv6 set is empty (P3)

**Observation:** `copilot_v6` set was flushed and left empty after running the
resolver. Only `copilot_v4 { 140.82.112.21 }` was populated.

**Impact:** None for this run (Copilot CLI used IPv4). But future runs over
IPv6 will be silently dropped by the egress chain.

**Recommended fix:** Either (a) extend the resolver to populate IPv6 if Copilot
serves AAAA records, or (b) document that v4-only is intended.

### Finding 3 — Tokens/cost not reported (informational)

`tokens.source` and `cost_usd.source` both return
`not_reported_by_github_copilot_cli`. This is by design — the GitHub Copilot
CLI does not emit token/cost telemetry on stderr/stdout. If we want this
metric, we need to instrument from the API side (not feasible from the wrapper).

### Finding 4 — Run completed in 2.7s (informational)

The Copilot CLI exited at the `--no-banner` flag parse, before any inference
call, so duration is deceptively short. Real runs (post-fix) will likely take
~30-300s for the requested research prompt.

---

## Run fields summary

| Field | Value |
|---|---|
| `batch_id` | `f8a-first-real-run` |
| `agent_id` | `copilot-vps-single-001` |
| `brief_id` | `F8-B1` |
| `mission_run_id` | `49a1496515c84826b215ae9d8ec400e9` |
| `tokens` | `null` (`not_reported_by_github_copilot_cli`) |
| `cost_usd` | `null` (`not_reported_by_github_copilot_cli`) |
| `exit_code` | `1` |
| `duration_sec` | `2.718` |
| `artifact_manifest` | `artifacts/copilot-cli/2026-05/f8a-first-real-run/copilot-vps-single-001/49a1496515c84826b215ae9d8ec400e9/manifest.json` |
| `audit_log` | `reports/copilot-cli/2026-05/49a1496515c84826b215ae9d8ec400e9.jsonl` |

---

## Acceptance criteria

| Criterion | Status |
|---|---|
| O1 passed (L3 closed probe → `execute_flag_off_dry_run`) | ✅ |
| Approval line present in invocation | ✅ |
| Backup created with chmod 0600 | ✅ |
| nft table applied + sets populated | ✅ |
| L3 flipped, restart, process env reflects | ✅ |
| Exactly one real run executed | ✅ |
| Artifacts + manifest + audit written | ✅ |
| L3 reverted to false post-run | ✅ |
| L4 reverted to false post-run | ✅ |
| nft table deleted post-run | ✅ |
| Worker healthy post-rollback | ✅ |
| Secret scans clean (stderr, audit, manifest, journal) | ✅ |
| Run produced usable output | ❌ — Copilot CLI exited 1 on flag error |

**Overall:** infrastructure 100% validated, run output unusable due to wrapper
flag bug. Verdict 🟡 **AMARILLO**.

---

## Next steps

1. **F8A-bugfix PR:** drop `--no-banner` from `worker/tasks/copilot_cli.py`
   wrapper command. Add a unit test asserting the wrapper command does not
   contain rejected flags. Deploy → restart worker → re-run F8A retry with
   same prompt.
2. **Optional:** extend `copilot_egress_resolver.py` to handle IPv6 if needed.
3. **Do not retry F8A real run until F8A-bugfix is merged and deployed.**
