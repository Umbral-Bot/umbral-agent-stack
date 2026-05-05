# F7 Rehearsal 4A — Sandbox Image Build + Offline Smoke: Live Evidence

**Date:** 2026-05-05
**Operator:** David (human) + Rick AI (automated evidence)
**Live HEAD at start:** `6fde9ad` (main)
**Evidence branch:** `rick/copilot-cli-f7-sandbox-image-evidence`

---

## 1. Objective

Build the sandbox Docker image `umbral-sandbox-copilot-cli` and run offline smoke tests.

**Does NOT:**
- Activate Copilot real execution
- Change `_REAL_EXECUTION_IMPLEMENTED`
- Change `RICK_COPILOT_CLI_EXECUTE`
- Activate egress
- Use Copilot token
- Restart worker

---

## 2. Phase A — Preflight

| Item | Value |
|---|---|
| Live HEAD | `6fde9ad` |
| MainPID | `1418206` |
| `/health` | 200 |
| `copilot_cli.enabled` (L2) | `true` |
| `RICK_COPILOT_CLI_EXECUTE` (L3) | `false` |
| `egress.activated` (L4) | `false` |
| `_REAL_EXECUTION_IMPLEMENTED` (L5) | `False` |
| Docker version | `29.2.1` |
| Sandbox image pre-build | **missing** |

---

## 3. Phase B — Build Script Inspection

**`worker/sandbox/refresh-copilot-cli.sh`:**
- Deterministic tag: `sha256(Dockerfile + copilot-cli-smoke + copilot-cli-wrapper)[:12]`
- Does NOT push to registry
- Does NOT install on host
- Does NOT pass `COPILOT_GITHUB_TOKEN` to build
- Does NOT touch running worker/dispatcher/gateway
- Build uses network only for Docker base image pull + npm install (not Copilot HTTPS runtime)

**`worker/sandbox/Dockerfile.copilot-cli`:**
- Base: `node:22.14-bookworm-slim`
- Installs: `@github/copilot@1.0.36` (pinned), `git`, `tini`, `ca-certificates`
- `gh` CLI deliberately NOT installed (defense-in-depth)
- Non-root user: uid `10001` (`runner`)
- Entrypoint: `tini` → `copilot-cli-smoke` (safe default)
- Runtime flags: `--network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges --security-opt=seccomp=default`

---

## 4. Phase C — Build

```
bash worker/sandbox/refresh-copilot-cli.sh --print
→ umbral-sandbox-copilot-cli:6940cf0f274d

bash worker/sandbox/refresh-copilot-cli.sh
→ refresh-copilot-cli.sh: built umbral-sandbox-copilot-cli:6940cf0f274d
→ TAG=6940cf0f274d
```

All 8 layers resolved from cache (image was previously built on this Docker daemon):
- `node:22.14-bookworm-slim` base
- `apt-get install ca-certificates git tini`
- `npm install -g @github/copilot@1.0.36`
- `useradd runner (uid 10001)`
- `COPY copilot-cli-smoke`
- `COPY copilot-cli-wrapper`
- `chmod 0555 ...`
- `WORKDIR /work`

---

## 5. Phase D — Image Verification

| Item | Value |
|---|---|
| Image | `umbral-sandbox-copilot-cli:6940cf0f274d` |
| Image ID | `sha256:fe0daf3dc7178a3ebf35b331932bd4e83fcba7f243da27c4583ba428f7862ea0` |
| Size | `233,588,356 bytes (~223 MB)` |
| Created | `2026-04-26T15:45:31` |
| Host `which copilot` | **missing** (expected — not installed on host) |
| Host npm global copilot | **absent** |

Host remains clean — Copilot binary confined to image only.

---

## 6. Phase E — Offline Smoke Results

### Run smoke: `bash worker/sandbox/run-copilot-cli-smoke.sh`

```
run-copilot-cli-smoke.sh: NO token will be injected. NO network.
```

| Check | Result |
|---|---|
| uid is 10001 (non-root) | ✅ PASS |
| seccomp filter mode active (Seccomp=2) | ✅ PASS |
| no_new_privs=1 | ✅ PASS |
| CapEff is 0 (all caps dropped) | ✅ PASS |
| copilot binary present (`copilot --version` = 1.0.36) | ✅ PASS |
| no auth-related env vars leaked | ✅ PASS |
| DNS resolution blocked (--network=none) | ✅ PASS |
| /work is read-only | ✅ PASS |
| /scratch is writable (tmpfs) | ✅ PASS |
| wrapper blocks `git push` | ✅ PASS |
| wrapper blocks `rm -rf` | ✅ PASS |

**passes=11 / fails=0 → SMOKE_RESULT=ok**

### Wrapper tests: `bash worker/sandbox/test-copilot-cli-wrapper.sh`

**Banned (53 cases — all PASS):**
- `git push` variants (11): push, -f, --force, --force-with-lease, --mirror, --tags, --delete, --set-upstream, -u, --no-verify, and git remote add/set-url
- `git` dangerous ops: config --global, filter-branch, update-ref
- `gh pr *` (8): create, merge, comment, review, close, edit, ready, reopen
- `gh release *` (3): create, delete, upload
- `gh repo *` (5): create, delete, edit, rename, archive
- `gh secret *` (2): set, delete, + gh secret
- `gh auth *` (5): login, logout, refresh, setup-git, + gh auth
- `gh api`, `gh workflow run/disable/enable`
- `gh ssh-key add`, `gh gpg-key add`
- `rm -rf`, `rm -fr`, `chmod -R`, `chown -R`, `dd if=`, `mkfs`, `sudo`, `su -`

**Allowed (7 cases — all PASS):**
- `git status`, `git log`, `git diff`, `ls -la`, `cat README`, `echo hello`, `git fetch`

**passes=60 / fails=0 → WRAPPER_TEST_RESULT=ok**

---

## 7. Phase F — Side-Effect Verification

| Check | Result |
|---|---|
| Worker MainPID | `1418206` (unchanged — no restart) |
| `/health` | 200 |
| nft copilot rules | none |
| Docker network copilot | none |
| `_REAL_EXECUTION_IMPLEMENTED` | `False` |
| `egress.activated` | `false` |
| `RICK_COPILOT_CLI_EXECUTE` | `false` |

---

## 8. Phase G — Task Probe Still Blocked

```json
{
  "would_run": false,
  "phase_blocks_real_execution": true,
  "decision": "execute_flag_off_dry_run",
  "policy": {
    "execute_enabled": false,
    "real_execution_implemented": false,
    "phase_blocks_real_execution": true
  },
  "egress_activated": false
}
```

✅ Task still blocked at L3 — no subprocess, no Copilot HTTPS.

---

## 9. Summary

| Component | Status |
|---|---|
| Sandbox image built | ✅ `umbral-sandbox-copilot-cli:6940cf0f274d` |
| Smoke tests (11 checks) | ✅ 11/11 PASS |
| Wrapper deny-list (60 checks) | ✅ 60/60 PASS |
| Non-root UID enforcement | ✅ uid 10001 |
| seccomp + no-new-privs + cap-drop=ALL | ✅ all active |
| Network isolation (--network=none) | ✅ DNS blocked |
| Read-only /work mount | ✅ confirmed |
| Host copilot binary | ✅ absent |
| No token injected in build/smoke | ✅ confirmed |
| Worker unchanged (no restart) | ✅ PID 1418206 |
| Task probe | ✅ `execute_flag_off_dry_run` |
| All 5 gates unchanged | ✅ L3/L4/L5 closed |

---

## 10. Gate Stack — Current State

```
L1  RICK_COPILOT_CLI_ENABLED=true       [open]
L2  copilot_cli.enabled=true            [open]
L3  RICK_COPILOT_CLI_EXECUTE=false      [closed]
L4  egress.activated=false              [closed]
L5  _REAL_EXECUTION_IMPLEMENTED=False   [closed — code constant]
```

---

## 11. Next Steps (each requires David's explicit approval)

1. **Rehearsal 4B** (if approved): open L3+L5 simultaneously → observe Docker container launches,
   runs `copilot-cli-smoke` (not a real prompt), fails gracefully because no token + network=none.
   Rollback: restore L3=false + restart.
2. **Full activation (F8+)**: separate explicit gate-by-gate procedure.

**STOP — no egress activation, no `_REAL_EXECUTION_IMPLEMENTED=True`, no L3 flip.**
