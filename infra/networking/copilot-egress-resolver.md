# Copilot CLI Egress Resolver — Design Note (F6 step 3)

> **Status:** DESIGN ONLY. Nothing in this document has been applied
> live in F6 step 3. `copilot_cli.egress.activated` remains `false`.

## 1. Why nftables can't take domain names directly

`nftables` matches on packet headers. By the time a packet hits the
`output` chain, the destination is already an IP — the kernel never
sees the SNI / Host header, and the rules can only allow traffic by IP
set membership. We therefore need an out-of-band resolver that:

1. Resolves each authorized endpoint to its current IPv4 / IPv6 set.
2. Atomically updates the `copilot_v4` / `copilot_v6` named sets
   declared in `infra/networking/copilot-egress.nft.example`.
3. Records the resolution + delta in an append-only audit log.
4. Refuses to install obviously-wrong sets (empty, all RFC1918, all
   loopback).

The resolver itself is **not** implemented in F6 step 3 — only its
contract is documented here so the design can be reviewed before any
`nft add element` runs on the host.

## 2. Authorized endpoints (mirror of `tool_policy.yaml`)

Mandatory (Copilot CLI cannot work without them):

- `api.githubcopilot.com` (HTTPS 443) — chat completion / agent backend
- `api.individual.githubcopilot.com` (HTTPS 443) — individual plan
- `api.business.githubcopilot.com` (HTTPS 443) — business plan
- `api.enterprise.githubcopilot.com` (HTTPS 443) — enterprise plan
- `api.github.com` (HTTPS 443) — auth / user endpoint

Optional (only when justified by real evidence in a runbook):

- `copilot-proxy.githubusercontent.com` (HTTPS 443) — content proxy

Anything else MUST be added to `config/tool_policy.yaml ::
copilot_cli.egress.allowed_endpoints` first, with a written rationale,
and never inline in the resolver.

## 3. Scoped enforcement model

The nft profile is scoped to the dedicated Docker bridge only:

- Docker network name: `copilot-egress`
- Linux bridge name: `br-copilot`
- nft hook: `forward`
- nft chain policy: `accept`
- scoped drop: packets with `iifname "br-copilot"` that are not DNS or
  HTTPS to the resolver-populated Copilot IP sets

The profile MUST NOT install a host `output` hook with `policy drop`. F8A
evidence on 2026-05-06 showed that host-wide output filtering blocks unrelated
worker traffic such as Notion API calls. The intent is to sandbox the Copilot
container, not the worker host.

Operator-created network shape:

```sh
docker network create \
  --driver bridge \
  --opt com.docker.network.bridge.name=br-copilot \
  --opt com.docker.network.bridge.enable_icc=false \
  copilot-egress
```

`COPILOT_CLI_DOCKER_NETWORK` must be `copilot-egress` for any real run.

## 4. TTL / cache strategy

- Resolver runs on a systemd timer (`copilot-egress-resolver.timer`),
  cadence `OnCalendar=*:0/15` (every 15 minutes).
- Each resolution uses the system resolver (`getaddrinfo`) — never a
  hard-coded DNS server.
- Resolved IPs are cached for max(`min(record_ttl) * 2`, 5 min).
- A successful refresh writes the new set atomically:

  ```sh
  nft -f - <<EOF
  flush set inet copilot_egress copilot_v4
  add element inet copilot_egress copilot_v4 { 140.82.112.0/20, ... }
  EOF
  ```

- A failed refresh keeps the previous set and logs `resolver_stale`.

## 5. Fallback if DNS fails

- If every authorized endpoint fails to resolve for ≥3 consecutive runs,
  the resolver:
  1. Leaves the existing IP set untouched (do not flush — a stale
     allow-list is safer than an empty one which would deny all egress
     mid-flight).
  2. Emits a `resolver_dns_outage` audit event.
  3. Triggers a healthcheck warning that surfaces to the dispatcher.
- If `--strict` is passed and any endpoint fails to resolve, exit
  non-zero so the systemd unit is marked failed.

## 6. Auditing connections

- `nftables` `log prefix` directives on accept + drop chains forward
  to journald. Operator queries:

  ```sh
  sudo journalctl -k --since "1 hour ago" | grep "copilot-egress"
  ```

- The resolver appends one JSONL record per refresh to:

  ```
  reports/copilot-cli/egress/<YYYY-MM>/<batch_id>.jsonl
  ```

  Schema: `{ts, run_id, endpoint, resolved_v4, resolved_v6, delta_v4, delta_v6, error}`.
  No tokens, no full packet payloads.

## 7. Rollback

Operator-only sequence (NOT executed by the agent in any phase):

```sh
# 1. Stop the timer + service.
sudo systemctl disable --now copilot-egress-resolver.timer
sudo systemctl disable --now copilot-egress-resolver.service

# 2. Remove the nft table (frees rules atomically).
sudo nft delete table inet copilot_egress

# 3. Remove the dedicated Docker network if no container is using it.
docker network rm copilot-egress

# 4. Remove the dropin.
sudo rm -f /etc/nftables.d/copilot-egress.nft

# 5. Flip policy off:
#    config/tool_policy.yaml :: copilot_cli.egress.activated = false
#    (already the default)

# 6. Confirm:
sudo nft list ruleset | grep -i copilot && echo "FAIL: rules still present" \
                                         || echo "rollback OK"
```

If the resolver's stale IP set ever blocks a legitimate workload, the
fastest mitigation is rollback above (deny → allow-all on the chain
deletion) followed by a fresh resolve. Do **not** edit the IP set by
hand on a live host — every modification must come from a re-run of
the resolver so the audit trail stays intact.

## 8. What F6 step 3 does NOT do

- Does NOT implement the resolver script.
- Does NOT install the systemd timer or service.
- Does NOT touch `nftables` / `iptables` / `ufw` on the host.
- Does NOT create any Docker network.
- Does NOT flip `copilot_cli.egress.activated`.
- Does NOT make any real HTTPS call to Copilot.

## 9. F6 step 4 unblock conditions

To advance to F6 step 4 (resolver implementation + dry-run install),
the following must be true and signed off:

1. This document is reviewed by David.
2. `config/tool_policy.yaml :: copilot_cli.egress.allowed_endpoints`
   is final (no churn during step 4).
3. `scripts/verify_copilot_egress_contract.py` exits 0 against this
   repo (parity between policy and artifact).
4. Operator has confirmed that the production VPS can create the dedicated
   Docker bridge `copilot-egress` / `br-copilot` and that the nft table does
   not affect host `output` traffic.
