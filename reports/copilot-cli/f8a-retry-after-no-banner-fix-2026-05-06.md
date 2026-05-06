# F8A retry after `--no-banner` bugfix — VPS evidence

**Date:** 2026-05-06T04:32:28Z (run completion)
**Executed by:** copilot-vps
**Repo HEAD (main, deployed):** `0cdb47ba62e1c6fcf0ea3c904d568af954b97548`
**Approval line present:** `APPROVE_F8A_ONE_SHOT_RUN=YES` ✅
**Previous failure reference:** `49a1496515c84826b215ae9d8ec400e9` (F8A first run, stderr `error: unknown option '--no-banner'`)

---

## Verdict

🟡 **AMARILLO**

The `--no-banner` bugfix is confirmed deployed and working: the obsolete flag is
no longer present in `worker/tasks/copilot_cli.py` (line 499) and the previous
stderr error (`error: unknown option '--no-banner'`) is gone.

However, Copilot CLI still exits `1`, this time **completely silently**: both
`stdout.txt` and `stderr.txt` are 0 bytes (sha256 `e3b0c44...` empty-file
digest). Duration `2.399s` indicates the CLI failed almost immediately —
consistent with an auth/session check, not an inference timeout.

End-to-end pipeline (gates → backup → nft → L3/L4 flip → Docker subprocess →
artifacts → audit → rollback) ran cleanly. No security/sandbox failure. No
secrets leaked.

---

## Executive summary

| Phase | Result |
|---|---|
| Bugfix verification (`--no-banner` removed) | ✅ `grep` → 0 hits in source |
| Worker restarted to load fixed code | ✅ PID `3815` → `4320` (HTTP 200) |
| O1 deploy verification (L3 closed) | ✅ pass — `decision=execute_flag_off_dry_run`, `phase=F8A.gated` |
| Backup created (chmod 0600) | ✅ `/home/rick/.copilot/backups/f8a-retry-no-banner-20260506T043014Z` |
| nft apply + sets populated | ✅ `inet copilot_egress` live, `copilot_v4` populated (resolver IPs) |
| L4 flipped (working tree only) | ✅ `egress.activated: true` |
| L3 + image + network flipped | ✅ `RICK_COPILOT_CLI_EXECUTE=true`, image `umbral-sandbox-copilot-cli:6940cf0f274d`, network `bridge` |
| Worker restarted on opened gates | ✅ PID `4486` (HTTP 200) |
| One-shot real run executed | 🟡 `exit_code=1`, stdout=stderr=0 bytes |
| Rollback (envfile + yaml + nft + restart) | ✅ |
| Post-rollback state | ✅ PID `4633`, /health 200, no nft table, no copilot docker network |
| Token scans (stderr, stdout, audit JSONL, manifest, journalctl) | ✅ all clean |

---

## Bugfix verification

```
$ grep -c -- '--no-banner' worker/tasks/copilot_cli.py
0
```

Wrapper command at `worker/tasks/copilot_cli.py:499`:

```sh
exec copilot --no-color --no-auto-update --no-remote --no-ask-user \
  --disable-builtin-mcps --secret-env-vars=COPILOT_GITHUB_TOKEN \
  --available-tools=view,grep,glob \
  --output-format=json --stream=off \
  --log-dir=/scratch/copilot-logs \
  --prompt "$(cat "$prompt_file")"
```

Confirmed: no `--no-banner`, matches docker_argv captured in run response.

---

## Gate matrix — before / during / after

| Layer | Before O2 | During run window | After rollback |
|---|---|---|---|
| **L1** `RICK_COPILOT_CLI_ENABLED` | `true` ✅ | `true` ✅ | `true` ✅ |
| **L2** `copilot_cli.enabled` | `true` ✅ | `true` ✅ | `true` ✅ |
| **L3** `RICK_COPILOT_CLI_EXECUTE` | `false` ❌ CLOSED | `true` ⚠️ OPEN (PID `4486`) | `false` ❌ CLOSED (PID `4633`) |
| **L4** `egress.activated` | `false` ❌ + no nft table | `true` ⚠️ + nft `inet copilot_egress` live | `false` ❌ + no nft table |
| **L5** `_REAL_EXECUTION_IMPLEMENTED` | `True` ✅ (line 54) | `True` ✅ | `True` ✅ |

---

## One-shot real run — captured fields

| Field | Value |
|---|---|
| `mission_run_id` | `ee5aa7b921d44fdcb435d1c0803656d2` |
| `batch_id` | `f8a-retry-no-banner` |
| `agent_id` | `copilot-vps-single-002` |
| `brief_id` | `F8-B1` |
| `task_id` | `6b003386-b57a-4b3b-8c93-4a3a174d1cd5` |
| `trace_id` | `7c8edd81-3c0b-4f1e-9439-c74673a975d6` |
| `decision` | `completed` |
| `phase` | `F8A.real_execution` |
| `phase_blocks_real_execution` | `false` |
| `executed` | `true` |
| `would_run` | `false` |
| `policy.execute_enabled` | `true` |
| `policy.real_execution_implemented` | `true` |
| `egress_activated` | `true` |
| `exit_code` | **`1`** |
| `duration_sec` | **`2.399`** |
| `tokens` | `null / null / null` (`not_reported_by_github_copilot_cli`) |
| `cost_usd` | `null` (`not_reported_by_github_copilot_cli`) |
| `prompt_sha256` | `319537882ab21529f92abe9924a1c874122ff5a8b74a8ee52b701621c3fcba3d` |

### Artifact paths

| Artifact | Bytes | sha256 |
|---|---|---|
| `manifest.json` | 2640 | n/a |
| `stdout.txt` | **0** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |
| `stderr.txt` | **0** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |

Paths:
- `artifacts/copilot-cli/2026-05/f8a-retry-no-banner/copilot-vps-single-002/ee5aa7b921d44fdcb435d1c0803656d2/`
- `audit_log`: `reports/copilot-cli/2026-05/ee5aa7b921d44fdcb435d1c0803656d2.jsonl` (2 lines, gitignored)

### stdout/stderr summary

Both 0 bytes. Copilot CLI exited 1 with **no diagnostic output**. The
`--no-banner` error from the previous run is gone, but no new error message
was emitted to either channel.

Hypotheses (not validated this run):

1. **Auth/subscription failure** — the CLI may be checking the
   `COPILOT_GITHUB_TOKEN` against an account that lacks an active Copilot
   subscription, and exiting silently rather than printing an error.
2. **`--log-dir` write target failure** — `/scratch/copilot-logs` is in a
   tmpfs, but if the wrapper image's CLI version requires the directory to
   pre-exist it would fail before producing output.
3. **`--secret-env-vars` flag incompatible with current CLI version** — the
   flag may have been renamed/removed similar to `--no-banner`.
4. **Egress block** — only `copilot_v4` set was populated (1 IP). If the CLI
   tries an IPv6 endpoint or an IP not in the set, `nft drop` is silent from
   inside the container (just looks like a network failure).

---

## nft / Docker snapshots

### Before run

- No `inet copilot_egress` table.
- No Docker `copilot*` network.

### During run window

- nft table `inet copilot_egress` live with chains `output`/`input`/`forward`,
  policy `drop`, `copilot_v4` populated by `scripts/copilot_egress_resolver.py
  --non-strict`.
- Docker network: `bridge` (host default; per envfile
  `COPILOT_CLI_DOCKER_NETWORK=bridge`).
- Sandbox image: `umbral-sandbox-copilot-cli:6940cf0f274d`.

### After rollback

- No `inet copilot_egress` table.
- No Docker `copilot*` network.
- Worker post-rollback PID `4633`, HTTP 200.

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
  --name copilot-cli-ee5aa7b921d44fdcb435d1c0803656d2 \
  --stop-timeout 600 \
  --env COPILOT_GITHUB_TOKEN --env NO_COLOR=1 \
  umbral-sandbox-copilot-cli:6940cf0f274d \
  /usr/local/bin/copilot-cli-wrapper /bin/sh -lc '...exec copilot --no-color ...'
```

Confirmed: `--cap-drop=ALL`, `no-new-privileges`, `--user 10001:10001`,
`--read-only` rootfs, scoped tmpfs, repo bind read-only, token by env name only.

---

## VPS Reality Check notation

```
L1: envfile says true     / VPS process 4486 shows true       → no drift
L2: repo yaml says true   / HEAD 0cdb47b shows true            → no drift
L3: envfile flipped to true (run window) / process 4486 true   → intended; reverted
L4: yaml flipped to true (run window) / nft live + sets        → intended; reverted
L5: repo says True        / probe real_execution_implemented=true → no drift
```

Wrapper code:
- repo HEAD `0cdb47b` line 499: `exec copilot --no-color ...` (no `--no-banner`)
- live process 4486 ran from same source ✅

---

## Secret-output-guard

| Check | Result |
|---|---|
| stdout.txt token scan | ✅ clean (file empty) |
| stderr.txt token scan | ✅ clean (file empty) |
| audit JSONL token scan | ✅ clean |
| manifest.json secret_scan field | ✅ `status: clean` |
| Worker journalctl run window | ✅ no token patterns |
| Backup files chmod | ✅ `0600` on all files |
| Report file token scan | ✅ clean |

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
PID 4633                             # post-rollback PID
```

Backup retained on disk for audit (chmod 0600):
`/home/rick/.copilot/backups/f8a-retry-no-banner-20260506T043014Z/`

---

## Findings & next steps

### Finding 1 — Copilot CLI exits 1 silently after fix (P1, blocker for green)

**Issue:** With `--no-banner` removed, Copilot CLI now exits `1` in 2.4s with
**no output on stdout or stderr**. Cannot diagnose root cause from inside the
container alone.

**Recommended diagnostic approach (next task, F8A-diagnose):**
1. Reproduce the run with the same docker invocation but **add
   `--log-level=debug`** to the Copilot CLI flags, or **drop `--output-format=json
   --stream=off`** to see raw output.
2. Bind-mount `/scratch/copilot-logs` to the host so the CLI's `--log-dir`
   output survives container exit.
3. Run the same CLI binary manually from a shell inside the container
   (`docker run -it --entrypoint /bin/sh ...`) and try `copilot --help` and
   `copilot --version` to confirm the binary works at all.
4. Validate `COPILOT_GITHUB_TOKEN` actually has Copilot CLI scope (token may
   need GitHub Copilot Business/Pro subscription enabled on the account).
5. Test whether `--secret-env-vars=COPILOT_GITHUB_TOKEN` is still a valid
   flag in the current Copilot CLI version (next thing that could have been
   silently renamed).

### Finding 2 — `copilot_v6` set still empty (P3, carryover from previous run)

`scripts/copilot_egress_resolver.py --non-strict` produced no IPv6 entries.
Same status as previous F8A run. Not a blocker yet but should be addressed
before any production use.

### Finding 3 — Tokens/cost not reported (informational, by design)

Same as previous run: GitHub Copilot CLI does not emit token/cost telemetry
on stderr/stdout. Source field returns `not_reported_by_github_copilot_cli`.

---

## Acceptance criteria

| Criterion | Status |
|---|---|
| `--no-banner` removed from source code | ✅ |
| Worker restarted to load bugfix | ✅ |
| O1 passed (L3 closed → `execute_flag_off_dry_run`) | ✅ |
| Approval line present | ✅ |
| Backup created with chmod 0600 | ✅ |
| nft table applied + sets populated | ✅ |
| L3 + L4 flipped only inside run window | ✅ |
| Exactly one real run executed | ✅ |
| Artifacts + manifest + audit written | ✅ |
| L3 reverted to false post-run | ✅ |
| L4 reverted to false post-run | ✅ |
| nft table deleted post-run | ✅ |
| Worker healthy post-rollback | ✅ |
| Secret scans clean (everywhere) | ✅ |
| Run produced usable output | ❌ — Copilot CLI exited 1 silently |
| Previous `--no-banner` error eliminated | ✅ |

**Overall:** bugfix confirmed effective; pipeline 100% validated for the
second time; new failure mode discovered (silent exit 1) requires
diagnostic-mode follow-up. Verdict 🟡 **AMARILLO**.

---

## Comparison to previous run

| Field | F8A first run (`49a14965...`) | F8A retry (`ee5aa7b9...`) |
|---|---|---|
| stderr bytes | 105 | **0** |
| stderr message | `error: unknown option '--no-banner'` | (none) |
| stdout bytes | 0 | 0 |
| exit_code | 1 | 1 |
| duration_sec | 2.718 | 2.399 |
| failure visibility | explicit (CLI flag error) | **silent** |
| infra path | ✅ end-to-end | ✅ end-to-end |
| rollback | ✅ clean | ✅ clean |

Progress: bug class shifted from "explicit CLI flag rejection" to "silent
exit 1". Next iteration must add diagnostic verbosity to surface the new
root cause.
