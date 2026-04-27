# Copilot CLI — F6 Step 6A Evidence: Live Staging Readiness

**Phase:** F6 step 6A — discover the live systemd / nftables surface,
emit a verifiable install plan. **No live changes performed.**
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains DISABLED at four layers
(env=false, policy=false, execute=false,
`_REAL_EXECUTION_IMPLEMENTED=False`). `copilot_cli.egress.activated`
remains `false`.

---

## 1. Why F6 step 6A exists (and why the original step 6 plan was wrong)

The previous recommendation assumed `umbral-worker.service` lived
under `/etc/systemd/system/` and would consume an `EnvironmentFile=`
under `/etc/umbral/`. That assumption was unverified. F6 step 6A
runs read-only discovery against the live host before producing any
install plan, so the operator never installs a drop-in into a path
that doesn't control the running process.

## 2. Discovery (read-only)

All commands below were executed read-only. Output captured in this
session:

### 2.1 `umbral-worker.service` — actual scope

```
$ systemctl --user status umbral-worker.service --no-pager
● umbral-worker.service - Umbral Worker API
     Loaded: loaded (/home/rick/.config/systemd/user/umbral-worker.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-04-17 11:06:01 -04
   Main PID: 675339 (python)

$ systemctl --user show umbral-worker.service \
    -p FragmentPath -p DropInPaths -p EnvironmentFiles
EnvironmentFiles=/home/rick/.config/openclaw/env (ignore_errors=no)
FragmentPath=/home/rick/.config/systemd/user/umbral-worker.service
DropInPaths=
```

System-scope check returns absent:

```
$ systemctl status umbral-worker.service --no-pager
Unit umbral-worker.service could not be found.
```

**Conclusion: unit scope is `user`.** The system-scope path
`/etc/systemd/system/umbral-worker.service.d/` would have been
inert.

### 2.2 Process

```
$ ps -eo pid,user,cmd | grep umbral-worker
 675339 rick     /home/rick/umbral-agent-stack/.venv/bin/python -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 --log-level info
```

Runs as `rick`, not `root`.

### 2.3 nftables host configuration

```
$ test -f /etc/nftables.conf && head /etc/nftables.conf
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
    chain input   { type filter hook input   priority filter; }
    chain forward { type filter hook forward priority filter; }
    chain output  { type filter hook output  priority filter; }
}
$ find /etc -maxdepth 3 -iname '*nft*'
/etc/nftables.conf
```

There is **no `include` directive** in `/etc/nftables.conf`. The
directory `/etc/nftables.d/` does NOT exist and would NOT be
auto-loaded. Anything dropped under `/etc/nftables.d/` would just sit
there.

### 2.4 Docker network

```
$ docker network ls | grep -i copilot
(empty)
```

No `copilot-egress` Docker network exists.

### 2.5 Existing user-scope units

```
/home/rick/.config/systemd/user/n8n.service
/home/rick/.config/systemd/user/openclaw-dispatcher.service
/home/rick/.config/systemd/user/openclaw-gateway.service
/home/rick/.config/systemd/user/openclaw-gateway.service.bak.20260308-175041
/home/rick/.config/systemd/user/openclaw.service.legacy-disabled
/home/rick/.config/systemd/user/umbral-worker.service
```

## 3. Decisions

| Item | Decision | Reason |
|---|---|---|
| Unit scope | `user` | `umbral-worker.service` only present at user scope |
| Drop-in directory | `/home/rick/.config/systemd/user/umbral-worker.service.d/` | mirrors fragment path |
| Drop-in file | `/home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf` | unique name avoids collisions |
| EnvironmentFile (runtime flags) | `/home/rick/.config/openclaw/copilot-cli.env` | adjacent to existing `/home/rick/.config/openclaw/env` |
| EnvironmentFile (secrets) | `/home/rick/.config/openclaw/copilot-cli-secrets.env` | same dir, mode 0600 enforced by `install -m 0600` |
| nftables staging file | `/home/rick/.config/openclaw/copilot-egress.nft` | NOT under `/etc/nftables.d/`; nothing autoloads it |
| Reload command | `systemctl --user daemon-reload` | matches user scope; no sudo |
| Sudo required | NO | full plan runs from rick's shell |

The shipped artifact `infra/systemd/umbral-worker-copilot-cli.conf.example`
still references `/etc/umbral/...` paths. The plan in §5 explicitly
calls out that the operator must **edit a `.template` copy** of that
artifact to use the user-scope envfile paths before the final
`copilot-cli.conf` lands. We deliberately do NOT modify the shipped
artifact in this step — it remains the canonical system-scope
template for environments where umbral-worker is system-managed.

`/etc/nftables.d/` is **NOT autoloaded** on this host. Even if F6
step 6B ever installed a file there, it would have no effect until a
human added an `include "/etc/nftables.d/*.nft"` line to
`/etc/nftables.conf`. F6 steps 6+ keep the nft fragment in
`/home/rick/.config/openclaw/copilot-egress.nft` and never under
`/etc/nftables.d/`, so a misconfigured autoload can't be the thing
that activates egress by accident.

## 4. Planner — `scripts/plan_copilot_cli_live_staging.py`

stdlib-only. Read-only. The planner's `_safe_systemctl()` wrapper
**refuses** any verb outside `{status, cat, show, is-active,
is-enabled}`. There is no path through the planner that runs
`systemctl daemon-reload`, `systemctl --user daemon-reload`,
`systemctl start/stop/restart/enable/disable`, `nft`, `iptables`,
`ufw`, `docker network`, or any `sudo` command.

Outputs:
- `--format json` (default): structured plan, schema
  `copilot-cli-live-staging-plan/v1`.
- `--format shell`: human-readable comments + commands prefixed by
  `# manual_only —`. NO command is executed.

Cache:
- `--write-report <path>` only accepts paths under
  `reports/copilot-cli/` (gitignored from F4). Anything else raises
  `PlannerRefused` (exit 3).

Live smoke from this commit:

```
$ python scripts/plan_copilot_cli_live_staging.py --format shell | head -10
# === Copilot CLI live staging plan (DRY-RUN) ===
# unit_scope: user
# fragment_path: /home/rick/.config/systemd/user/umbral-worker.service
# nftables_autoloads_directory: False

# --- install commands (manual_only, NOT executed) ---
# manual_only — operator runs from rick's shell, no sudo
install -d -m 0700 /home/rick/.config/openclaw
install -m 0600 infra/env/copilot-cli.env.example /home/rick/.config/openclaw/copilot-cli.env
install -m 0600 infra/env/copilot-cli-secrets.env.example /home/rick/.config/openclaw/copilot-cli-secrets.env
```

## 5. Manual install command pack for F6 step 6B (NOT executed)

These commands go into `rick`'s shell. **No `sudo`.** All flags
remain `false` after running them.

```sh
# 1. Provision env files (user scope, mode 0600, owner rick implicit).
install -d -m 0700 /home/rick/.config/openclaw
install -m 0600 infra/env/copilot-cli.env.example \
        /home/rick/.config/openclaw/copilot-cli.env
install -m 0600 infra/env/copilot-cli-secrets.env.example \
        /home/rick/.config/openclaw/copilot-cli-secrets.env

# 2. Paste the fine-grained PAT v2 with `Copilot Requests` into the
#    secrets file. Use $EDITOR so the value never appears in shell
#    history. Do NOT echo it.
$EDITOR /home/rick/.config/openclaw/copilot-cli-secrets.env

# 3. Install the systemd drop-in TEMPLATE (not the final file).
install -d -m 0755 /home/rick/.config/systemd/user/umbral-worker.service.d
install -m 0644 infra/systemd/umbral-worker-copilot-cli.conf.example \
        /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf.template

# 4. Edit the .template into the final copilot-cli.conf, replacing the
#    EnvironmentFile= paths with the user-scope ones:
#       EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli.env
#       EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli-secrets.env
$EDITOR /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf.template
mv /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf.template \
   /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf

# 5. Verify the contract BEFORE reload:
python scripts/verify_copilot_cli_env_contract.py \
    --runtime /home/rick/.config/openclaw/copilot-cli.env \
    --secrets /home/rick/.config/openclaw/copilot-cli-secrets.env \
    --strict

# 6. Reload (NOT restart):
systemctl --user daemon-reload

# 7. Confirm drop-in is now visible:
systemctl --user show umbral-worker.service -p DropInPaths

# 8. DO NOT systemctl --user restart umbral-worker.service yet — every
#    flag is still false, so a restart would just re-read the same
#    disabled state. The restart belongs to F6 step 6C.
```

## 6. Manual rollback command pack (NOT executed)

```sh
rm -f /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
rm -f /home/rick/.config/openclaw/copilot-cli.env \
      /home/rick/.config/openclaw/copilot-cli-secrets.env
systemctl --user daemon-reload
systemctl --user show umbral-worker.service -p DropInPaths   # should be empty
```

## 7. Tests

```
$ WORKER_TOKEN=test python -m pytest \
    tests/test_plan_copilot_cli_live_staging.py \
    tests/test_copilot_cli.py \
    tests/test_rick_tech_agent.py \
    tests/test_verify_copilot_egress_contract.py \
    tests/test_copilot_egress_resolver.py \
    tests/test_verify_copilot_cli_env_contract.py -q
............................................................   [100%]
132 passed in 1.86s
```

Coverage delta vs F6 step 5 (+18 tests):

- `_safe_systemctl` refuses every mutating verb (start, stop, restart,
  enable, disable, reload, daemon-reload, kill, mask).
- `_safe_systemctl` allows `show` and prefixes `--user`.
- Unit discovery → user scope.
- Unit discovery → system scope.
- Unit discovery → absent.
- nftables.conf without `include` → autoload False.
- nftables.conf with `include "..*.nft"` → autoload True + glob captured.
- nftables.conf absent → `conf_present` False.
- Recommended paths: user / system / absent.
- Install commands marked `manual_only` (user + system).
- Install commands NEVER include `restart umbral-worker` outside a comment.
- Rollback commands marked `manual_only`.
- `write_report` refuses `tmp_path` and `/etc/...`.
- `write_report` accepts `reports/copilot-cli/...` and round-trips.
- `build_plan.guards` block sudo / etc / nft / iptables / docker /
  flags / tokens.
- `main()` does not print token values from
  `COPILOT_GITHUB_TOKEN`/`GH_TOKEN`/`GITHUB_TOKEN` env vars.

## 8. What F6 step 6A explicitly does NOT do

- ✗ Does NOT use `sudo`.
- ✗ Does NOT create `/etc/umbral/`.
- ✗ Does NOT create `~/.config/openclaw/copilot-cli{,-secrets}.env`.
- ✗ Does NOT create any `umbral-worker.service.d/` drop-in.
- ✗ Does NOT call `systemctl daemon-reload` (system or user).
- ✗ Does NOT call `nft`, `iptables`, `ip6tables`, `ufw`.
- ✗ Does NOT create or modify any Docker network.
- ✗ Does NOT activate `copilot_cli.egress.activated`.
- ✗ Does NOT flip `RICK_COPILOT_CLI_ENABLED`,
  `RICK_COPILOT_CLI_EXECUTE`, or `_REAL_EXECUTION_IMPLEMENTED`.
- ✗ Does NOT restart `umbral-worker.service`.
- ✗ Does NOT touch Notion / gates / publication.

## 9. F6 step 6B unblock conditions

To advance to F6 step 6B (the operator runs the install pack from §5):

1. This document reviewed and approved by David.
2. Operator has the fine-grained PAT v2 with `Copilot Requests`
   minted and recorded in a secrets manager. Token must NOT travel
   over chat / email / shell history.
3. Operator has confirmed the rollback pack from §6 in their head /
   notes BEFORE running the install.
4. F6 step 6B plan must keep every flag false. Reload only, no
   restart, no flag flip.
5. After install, `python scripts/verify_copilot_cli_env_contract.py
   --runtime /home/rick/.config/openclaw/copilot-cli.env --secrets
   /home/rick/.config/openclaw/copilot-cli-secrets.env --strict`
   must exit 0.
6. After install, `systemctl --user show umbral-worker.service -p
   DropInPaths` must list the new copilot-cli.conf path.

## 10. Next prompt recommendation (F6 step 6B — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6B: operator-only execution of the install pack
> from §5. The agent observes verifier output and updates evidence
> docs only; the operator runs every command from rick's shell. ALL
> flags stay false. NO restart of umbral-worker.service. PR remains
> draft.
