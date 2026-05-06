---
id: f8a-redesign-egress-scope-2026-05-07
title: "F8A scoped egress staging verification"
assigned_to: copilot-vps
status: todo
priority: high
reviewer: codex
created_at: 2026-05-07
---

# F8A scoped egress staging verification

## Bootstrap

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Context

F8A prompt-quoting retry evidence found a production-risk bug in the old
egress nft template: it installed a host-wide `output` hook with `policy drop`,
which blocked Notion API traffic from the worker during the run window.

This task verifies the redesigned scoped egress model without running Copilot:

- Docker network: `copilot-egress`
- Linux bridge: `br-copilot`
- nft hook: `forward`
- chain policy: `accept`
- drop scope: only packets whose `iifname` is `br-copilot`

## Rules

- Do not open L3 (`RICK_COPILOT_CLI_EXECUTE` must stay false).
- Do not set `copilot_cli.egress.activated=true`.
- Do not run `copilot_cli.run` with L3/L4 open.
- Do not call Copilot.
- Never print token values.
- Rollback nft table and Docker network at the end unless the network existed
  before this task and had the expected bridge config.

## O1 — Source checks

```bash
grep -n 'define copilot_bridge = "br-copilot"' infra/networking/copilot-egress.nft.example
grep -n 'type filter hook forward priority filter; policy accept;' infra/networking/copilot-egress.nft.example
grep -n 'iifname != $copilot_bridge accept' infra/networking/copilot-egress.nft.example
! grep -n 'hook output.*policy drop' infra/networking/copilot-egress.nft.example
grep -n '_DEFAULT_DOCKER_NETWORK = "copilot-egress"' worker/tasks/copilot_cli.py
python3 scripts/verify_copilot_egress_contract.py
```

Expected: all checks pass.

## O2 — Create dedicated Docker network

If `copilot-egress` exists, inspect it. It is acceptable only if its bridge
name is `br-copilot`. If it exists with any other bridge, stop with verdict
`rojo`.

If absent, create it:

```bash
docker network create \
  --driver bridge \
  --opt com.docker.network.bridge.name=br-copilot \
  --opt com.docker.network.bridge.enable_icc=false \
  copilot-egress
```

Record whether it pre-existed or was created by this task.

## O3 — Apply scoped nft table

Backup current ruleset first:

```bash
BACKUP_DIR="/home/rick/.copilot/backups/f8a-egress-scope-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
sudo nft list ruleset > "$BACKUP_DIR/nft-ruleset-before.nft"
chmod 0600 "$BACKUP_DIR"/*
```

Then parse-check and apply:

```bash
sudo nft -c -f infra/networking/copilot-egress.nft.example
sudo nft -f infra/networking/copilot-egress.nft.example
python3 scripts/copilot_egress_resolver.py --non-strict --format json > /tmp/f8a-egress-scope-resolver.json
```

If resolver returns empty `copilot_v4` and empty `copilot_v6`, keep L3/L4
closed, record verdict `amarillo`, and rollback. Otherwise populate the sets.

## O4 — Host egress non-regression checks

With nft table active and sets populated, verify host traffic is not blocked:

```bash
curl -sS --connect-timeout 10 -o /dev/null -w "notion_http=%{http_code}\n" https://api.notion.com/v1/users
curl -sS --connect-timeout 10 -o /dev/null -w "github_http=%{http_code}\n" https://api.github.com/
curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
```

Expected:

- Notion returns an HTTP status (401/400 is OK; DNS/connect timeout is not).
- GitHub returns an HTTP status (200/403/429 are OK; DNS/connect timeout is not).
- Worker health is 200.

## O5 — Container-scoped behavior smoke

Do not use the Copilot token. Use the sandbox image only for network smoke.

```bash
IMAGE=$(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^umbral-sandbox-copilot-cli:' | head -1)
docker run --rm --network=copilot-egress --entrypoint /bin/sh "$IMAGE" -lc \
  'node -e "require(\"https\").get(\"https://api.github.com/\", r => { console.log(\"github_status=\" + r.statusCode); r.resume(); }).on(\"error\", e => { console.error(e.message); process.exit(2); })"'
```

Expected: command exits 0 and prints `github_status=<status>`.

## O6 — Rollback

```bash
sudo nft delete table inet copilot_egress 2>/dev/null || true
docker network rm copilot-egress 2>/dev/null || true   # only if this task created it
curl -s -o /dev/null -w "worker_health=%{http_code}\n" http://127.0.0.1:8088/health
```

Final state must show:

- no `inet copilot_egress` table
- no `copilot-egress` Docker network if the task created it
- `RICK_COPILOT_CLI_EXECUTE=false`
- `egress.activated=false`
- `/health` 200

## Report

Write:

```text
reports/copilot-cli/f8a-egress-scope-staging-2026-05-07.md
```

Required fields:

- verdict: verde / amarillo / rojo
- source checks result
- network pre-existed or created
- resolver IP counts and errors
- nft parse/apply result
- host egress checks (Notion/GitHub/health)
- container network smoke result
- rollback evidence
- secret scan result

## Branch / PR

Branch:

```text
rick/f8a-egress-scope-staging-2026-05-07
```

Open PR to `main` with Codex as reviewer. If `gh` is not authenticated, push
the branch and return compare URL.
