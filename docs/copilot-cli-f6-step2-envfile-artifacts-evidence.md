# Copilot CLI — F6 Step 2 Evidence: EnvFile Artifacts + Verifier

**Phase:** F6 step 2 — repo artifacts (systemd dropin example, env
file examples, verifier script). **Nothing is installed live.**
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** at four layers (env, policy,
execute flag, code constant).

---

## 1. What F6 step 2 actually does

- Adds three repo artifacts under `infra/` declaring the production
  layout for the systemd dropin and the two env files.
- Adds `scripts/verify_copilot_cli_env_contract.py` — a stdlib-only
  verifier that, when the live files exist, asserts the contract
  (owner/group/mode + variable separation + no classic PAT).
- Adds 11 tests pinning the verifier behaviour using `tmp_path`; never
  touches `/etc/umbral` or any real secret.

It does **not** create `/etc/umbral/*`, **not** install the systemd
dropin, **not** run `systemctl`, **not** restart any service, **not**
provision any token.

## 2. Files added

```
infra/systemd/umbral-worker-copilot-cli.conf.example
infra/env/copilot-cli.env.example
infra/env/copilot-cli-secrets.env.example
scripts/verify_copilot_cli_env_contract.py     (executable, stdlib only)
tests/test_verify_copilot_cli_env_contract.py
docs/copilot-cli-f6-step2-envfile-artifacts-evidence.md   (this file)
docs/copilot-cli-capability-design.md          (F6 step 2 status)
```

Files explicitly NOT touched / NOT created:
- `/etc/umbral/copilot-cli.env` — live secrets layout, NOT created here.
- `/etc/umbral/copilot-cli-secrets.env` — live secrets, NOT created here.
- `/etc/systemd/system/umbral-worker.service.d/copilot-cli.conf` — live
  dropin, NOT created here.
- `~/.openclaw/openclaw.json` — live runtime, NOT touched.
- `worker/tasks/copilot_cli.py` — handler from F6 step 1 unchanged.
- `config/tool_policy.yaml` — F4 contracts unchanged.
- `.env.example` — F6 step 1 changes unchanged.

## 3. systemd dropin example

Location in repo: `infra/systemd/umbral-worker-copilot-cli.conf.example`

```ini
[Service]
EnvironmentFile=-/etc/umbral/copilot-cli.env
EnvironmentFile=-/etc/umbral/copilot-cli-secrets.env
```

Notes:
- Leading `-` makes systemd tolerate file absence (capability stays
  disabled by default at the worker layer in that case).
- This file lives in the repo only. To install (when authorized):

  ```sh
  sudo install -m 0644 infra/systemd/umbral-worker-copilot-cli.conf.example \
       /etc/systemd/system/umbral-worker.service.d/copilot-cli.conf
  sudo systemctl daemon-reload
  sudo systemctl restart umbral-worker
  ```

  **F6 step 2 does NOT run these commands.**

## 4. Env file examples

`infra/env/copilot-cli.env.example` — non-secret runtime flags:

```sh
RICK_COPILOT_CLI_ENABLED=false
RICK_COPILOT_CLI_EXECUTE=false
# COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:6940cf0f274d
```

`infra/env/copilot-cli-secrets.env.example` — secrets only:

```sh
# COPILOT_GITHUB_TOKEN=github_pat_<paste real fine-grained PAT v2 here>
```

The secrets example is **only a commented placeholder**. Hard rules
documented inline:
- ONLY `COPILOT_GITHUB_TOKEN` (no `GH_TOKEN`, no `GITHUB_TOKEN`)
- ONLY fine-grained PAT v2 with `Copilot Requests` (or OAuth Copilot CLI / OAuth gh-app)
- NO classic PAT (`ghp_*`)
- NO `gh auth login`
- NO `~/.copilot/config.json`
- Rotate ≤90 days

## 5. Verifier — `scripts/verify_copilot_cli_env_contract.py`

stdlib-only Python 3.10+. Default behaviour: **safe to run with no live
files** (exits 0 with `[INFO] missing_file_skipped`).

Checks performed when files exist:

| Check | Code | Severity |
|---|---|---|
| File mode == `0600` | `perm_mode` | error |
| Owner == `rick` | `perm_owner` | error |
| Group == `rick` | `perm_group` | error |
| `copilot-cli.env` contains `COPILOT_GITHUB_TOKEN` assignment | `secret_in_runtime_file` | error |
| `copilot-cli-secrets.env` contains `GH_TOKEN` or `GITHUB_TOKEN` assignment | `wrong_token_var` | error |
| Either file contains `ghp_…` (classic PAT, even in comments) | `classic_pat_detected` | error |
| `COPILOT_GITHUB_TOKEN` absent in secrets file | `no_copilot_token` | warn |
| File missing (default mode) | `missing_file_skipped` | info |
| File missing (`--strict`) | `missing_file` | error |

Flags:
- `--strict` — exit non-zero if env files are missing.
- `--no-perm-check` — skip ownership/mode checks (useful in CI without root).
- `--runtime <path>`, `--secrets <path>` — override default paths.

**Output safety:** the verifier never prints token values. Findings
reference line offsets only. Test
`test_verifier_does_not_print_token_values` enforces this with a fake
leak string.

Smoke run from this commit:

```
$ python scripts/verify_copilot_cli_env_contract.py
[INFO ] /etc/umbral/copilot-cli.env: missing_file_skipped — runtime env file absent
[INFO ] /etc/umbral/copilot-cli-secrets.env: missing_file_skipped — secrets env file absent
$ echo $?
0
```

## 6. Tests

```
$ WORKER_TOKEN=test python -m pytest \
    tests/test_verify_copilot_cli_env_contract.py \
    tests/test_copilot_cli.py \
    tests/test_rick_tech_agent.py -q
..........................................................................   [100%]
74 passed in 1.03s
```

Coverage delta vs F6 step 1 (+11 tests):
- passes in default mode when files missing
- fails in strict mode when files missing
- runtime file rejects `COPILOT_GITHUB_TOKEN` assignment
- secrets file rejects `GH_TOKEN`
- secrets file rejects `GITHUB_TOKEN`
- classic PAT detected in secrets (assignment line)
- classic PAT detected in runtime file (even in a comment)
- clean files pass
- verifier does not print token values (capsys)
- repo example artifacts pass their own contract
- systemd dropin example exists and contains the two `EnvironmentFile=` lines

## 7. What F6 step 2 explicitly does NOT do

- ✗ Does NOT create `/etc/umbral/*`.
- ✗ Does NOT install the systemd dropin.
- ✗ Does NOT run `systemctl daemon-reload` or `systemctl restart`.
- ✗ Does NOT provision, log, or transmit any token.
- ✗ Does NOT flip any flag.
- ✗ Does NOT touch the worker handler (F6 step 1 unchanged).
- ✗ Does NOT activate egress.
- ✗ Does NOT modify `~/.openclaw/`.
- ✗ Does NOT touch Notion / gates / publication.
- ✗ Does NOT open / merge / comment any PR.

## 8. Manual install command sequence (for F6 step 3+, when authorized)

```sh
# 1. Provision env files (operator runs these manually):
sudo install -d -m 0700 -o rick -g rick /etc/umbral
sudo install -m 0600 -o rick -g rick \
     infra/env/copilot-cli.env.example /etc/umbral/copilot-cli.env
sudo install -m 0600 -o rick -g rick \
     infra/env/copilot-cli-secrets.env.example /etc/umbral/copilot-cli-secrets.env
sudo $EDITOR /etc/umbral/copilot-cli-secrets.env   # paste the real PAT

# 2. Install systemd dropin:
sudo install -d -m 0755 /etc/systemd/system/umbral-worker.service.d
sudo install -m 0644 \
     infra/systemd/umbral-worker-copilot-cli.conf.example \
     /etc/systemd/system/umbral-worker.service.d/copilot-cli.conf

# 3. Verify contract BEFORE reload:
python scripts/verify_copilot_cli_env_contract.py --strict

# 4. Reload + restart (only if step 3 exits 0):
sudo systemctl daemon-reload
sudo systemctl restart umbral-worker

# 5. Verify worker came back without leaking the token to logs:
journalctl -u umbral-worker -n 20 --no-pager | grep -iE "token|copilot" || echo "OK no token in logs"
```

## 9. Risks / open items for F6 step 3+

- **Step 3 — egress activation:** flip `copilot_cli.egress.activated:
  true` plus iptables/nftables rules per design §10.2. Until step 3,
  the sandbox runs with `--network=none`, so even if step 2 examples
  were installed live the container couldn't talk to Copilot servers.
- **Step 4 — operation scoping enforcement:** wire
  `allowed_operations`/`forbidden_operations` from each mission contract
  into the wrapper / handler so anything outside is refused. Today only
  the 53-pattern deny-list is enforced.
- **Step N — real subprocess wiring:** flip
  `_REAL_EXECUTION_IMPLEMENTED` to True in a single, reviewed commit.
  Add `subprocess.run` call gated by all four layers. Add early
  `error: token_missing` rejection if `COPILOT_GITHUB_TOKEN` absent.
- **Token rotation observability:** cron / healthcheck warning ≥7 days
  before PAT expiration. Not in step 2.
- **Verifier hardening:** in CI the script runs with `--no-perm-check`
  because the test runner has uid != `rick`. Production must always run
  with perm checks enabled (default).

## 10. Next prompt recommendation (F6 step 3 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 3: design (NOT activate) the egress profile.
> Add `infra/networking/copilot-egress.nft.example` declaring the
> nftables rules per design §10.2 (allow only Copilot endpoints, drop
> everything else). Update verifier to optionally check that the
> profile would resolve. `copilot_cli.egress.activated` stays `false`.
> No live nftables / iptables touched. PR remains draft.
