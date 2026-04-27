# Copilot CLI — F6 Step 6B Evidence: User-Scope Live Staging

**Phase:** F6 step 6B — operator-only user-scope staging.
**No service restart. No flag flip. No token written. No nft applied.**

**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains DISABLED at four layers
(`RICK_COPILOT_CLI_ENABLED=false`, `RICK_COPILOT_CLI_EXECUTE=false`,
`copilot_cli.enabled=false`, `_REAL_EXECUTION_IMPLEMENTED=False`).
`copilot_cli.egress.activated=false`. The live `umbral-worker.service`
process **was NOT restarted**.

---

## 1. Scope

F6 step 6A's planner output was executed verbatim from rick's shell
(no sudo). All artifacts now live at the user-scope paths discovered
in F6 step 6A. **No `/etc` write. No system-scope systemd. No nft
apply. No restart of the worker.**

## 2. Commands executed (verbatim)

```sh
install -d -m 0700 ~/.config/openclaw
install -d -m 0755 ~/.config/systemd/user/umbral-worker.service.d
install -m 0600 infra/env/copilot-cli.env.example         ~/.config/openclaw/copilot-cli.env
install -m 0600 infra/env/copilot-cli-secrets.env.example ~/.config/openclaw/copilot-cli-secrets.env
install -m 0600 infra/networking/copilot-egress.nft.example ~/.config/openclaw/copilot-egress.nft

# Render user-scope drop-in by replacing /etc/umbral/* paths with
# /home/rick/.config/openclaw/* in the system-scope example.
sed 's|/etc/umbral/copilot-cli.env|/home/rick/.config/openclaw/copilot-cli.env|; \
     s|/etc/umbral/copilot-cli-secrets.env|/home/rick/.config/openclaw/copilot-cli-secrets.env|' \
    infra/systemd/umbral-worker-copilot-cli.conf.example \
  > ~/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
chmod 0644 ~/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf

# Capture MainPID, reload, capture again to PROVE no restart occurred.
systemctl --user show umbral-worker.service -p MainPID
systemctl --user daemon-reload
systemctl --user show umbral-worker.service -p MainPID
```

## 3. Post-staging state (captured)

### 3.1 File permissions

```
$ stat -c '%U %G %a %n' \
    ~/.config/openclaw/copilot-cli.env \
    ~/.config/openclaw/copilot-cli-secrets.env \
    ~/.config/openclaw/copilot-egress.nft
rick rick 600 /home/rick/.config/openclaw/copilot-cli.env
rick rick 600 /home/rick/.config/openclaw/copilot-cli-secrets.env
rick rick 600 /home/rick/.config/openclaw/copilot-egress.nft

$ stat -c '%U %G %a %n' \
    ~/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
rick rick 644 /home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
```

### 3.2 Drop-in seen by systemd (after `daemon-reload`)

```
$ systemctl --user show umbral-worker.service -p DropInPaths
DropInPaths=/home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf

$ grep '^EnvironmentFile=' ~/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf
EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli.env
EnvironmentFile=-/home/rick/.config/openclaw/copilot-cli-secrets.env
```

### 3.3 Service NOT restarted (PID identity proof)

```
MainPID before daemon-reload: 675339
MainPID after  daemon-reload: 675339
ActiveState=active
SubState=running
```

The drop-in is on disk and visible to systemd, but the live process
**has not re-read the EnvironmentFiles**. Restart belongs to a future
F6 step 6C, gated on the capability flags being intentionally
flipped.

### 3.4 Live process environment (proof that flags don't reach the running worker)

```
$ tr '\0' '\n' < /proc/675339/environ | grep -E 'RICK_COPILOT_CLI|COPILOT_GITHUB_TOKEN'
(empty)
```

### 3.5 Worker still healthy

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
HTTP 200
```

### 3.6 Verifier — strict

```
$ python scripts/verify_copilot_cli_env_contract.py \
    --runtime ~/.config/openclaw/copilot-cli.env \
    --secrets ~/.config/openclaw/copilot-cli-secrets.env \
    --strict
[WARN ] /home/rick/.config/openclaw/copilot-cli-secrets.env:
        no_copilot_token — COPILOT_GITHUB_TOKEN not set;
        capability will reject at runtime
```

Exit code 0. The single WARN is the **desired** state for F6 step 6B:
no token has been written. Errors (wrong owner / wrong mode /
forbidden var present / classic PAT detected) are all clean.

### 3.7 Flags in the staged runtime file

```
$ grep -E '^(RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE)=' \
       ~/.config/openclaw/copilot-cli.env
RICK_COPILOT_CLI_ENABLED=false
RICK_COPILOT_CLI_EXECUTE=false
```

### 3.8 Egress NOT activated

```
$ nft list ruleset 2>/dev/null | grep -i copilot
(empty)

$ docker network ls | grep copilot
(empty)
```

The nft fragment lives at `~/.config/openclaw/copilot-egress.nft` —
**staged only**. It has not been loaded with `nft -f`. There is no
`copilot-egress` Docker network. `/etc/nftables.conf` was not
modified and still has no `include` directive (so even if a future
operator placed a fragment in `/etc/nftables.d/`, it would not
autoload — see F6 step 6A §3).

### 3.9 Secret scan on staged files

```
$ grep -vE '^\s*#' ~/.config/openclaw/copilot-cli-secrets.env \
    | grep -E 'github_pat|ghp_|ghs_'
(empty)

$ grep -cE '^COPILOT_GITHUB_TOKEN=' ~/.config/openclaw/copilot-cli-secrets.env
0
```

Only commented placeholder text (the example header) is present.

## 4. What changed on disk (live host)

Created (user-scope only):

- `/home/rick/.config/openclaw/copilot-cli.env` (0600, rick:rick)
- `/home/rick/.config/openclaw/copilot-cli-secrets.env` (0600, rick:rick)
- `/home/rick/.config/openclaw/copilot-egress.nft` (0600, rick:rick)
- `/home/rick/.config/systemd/user/umbral-worker.service.d/copilot-cli.conf` (0644, rick:rick)

Reloaded (no restart):

- `systemctl --user daemon-reload`

NOT touched:

- `/etc/umbral/` (still does not exist)
- `/etc/systemd/system/umbral-worker.service.d/` (still does not exist)
- `/etc/nftables.conf` (unchanged; no `include` directive)
- `/etc/nftables.d/` (still does not exist)
- live process (PID 675339 unchanged)
- `umbral-worker.service` ActiveState (still `active (running)`)
- worker HTTP health (still 200)
- any system-scope systemd unit
- any Docker network
- any Notion page / gate / publication surface

## 5. What F6 step 6B explicitly does NOT do

- ✗ NO sudo
- ✗ NO write under `/etc/`
- ✗ NO system-level systemd unit installed
- ✗ NO `systemctl --user restart umbral-worker.service`
- ✗ NO `systemctl --user start/stop`
- ✗ NO `nft -f` / `iptables` / `ufw` / firewall mutation
- ✗ NO Docker network creation
- ✗ NO real `COPILOT_GITHUB_TOKEN` written
- ✗ NO flag flipped (both flags remain `false`)
- ✗ NO Copilot HTTPS request
- ✗ NO `_REAL_EXECUTION_IMPLEMENTED` flip
- ✗ NO Notion / gate / publication touched
- ✗ NO PR open / merge / comment

## 6. F6 step 6C unblock conditions

To advance to F6 step 6C (intentional flag flip + restart cycle), ALL
of the following must hold:

1. Operator has minted the fine-grained PAT v2 with `Copilot Requests`
   and pasted it into `~/.config/openclaw/copilot-cli-secrets.env`
   line `COPILOT_GITHUB_TOKEN=...` via `$EDITOR` (token never
   appearing in shell history). Verifier re-run must drop the
   `no_copilot_token` warning.
2. Operator has explicitly approved a single-flag flip plan:
   `RICK_COPILOT_CLI_ENABLED=true` while leaving
   `RICK_COPILOT_CLI_EXECUTE=false` and
   `_REAL_EXECUTION_IMPLEMENTED=False`. This proves the worker
   accepts the env without trying to execute Copilot.
3. Plan for `systemctl --user restart umbral-worker.service` is
   reviewed, with rollback documented (`# manual_only` set is in
   F6 step 6A doc §6).
4. Egress remains inactive (`copilot_cli.egress.activated=false`).
5. Audit log path exists and is writable by rick.

## 7. F6 step 6C recommendation (DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 6C: operator pastes the fine-grained PAT v2 into
> `~/.config/openclaw/copilot-cli-secrets.env`, re-runs the verifier
> to confirm no errors / no warns, and performs a single
> `systemctl --user restart umbral-worker.service`. Worker MUST
> accept the env without executing Copilot
> (`_REAL_EXECUTION_IMPLEMENTED=False` is the ultimate stop). PR
> remains draft. No Notion / no gates / no publish.
