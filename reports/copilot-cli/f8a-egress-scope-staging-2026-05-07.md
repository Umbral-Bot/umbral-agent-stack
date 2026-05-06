# F8A Scoped Egress Staging Verification

**Date:** 2026-05-07
**Verdict:** 🟢 verde
**Task spec:** `.agents/tasks/f8a-redesign-egress-scope-2026-05-07.md`
**Branch:** `rick/f8a-egress-scope-staging-2026-05-07`
**Live HEAD at start:** `750872f`
**Copilot real run:** ❌ none (out of scope; L3/L4 stayed closed)

## Summary

Validates the redesigned scoped egress profile that addresses the host-wide
drop policy regression discovered in the
`f8a-retry-after-prompt-quoting-fix-2026-05-06` evidence report.

The new model uses:

| Element | Value |
|---|---|
| Docker network | `copilot-egress` |
| Linux bridge | `br-copilot` |
| nft hook | `forward` |
| chain policy | `accept` |
| drop scope | only packets with `iifname = br-copilot` |

Outcome: nft table parses + applies cleanly, host outbound traffic is **not**
affected, container traffic from `copilot-egress` reaches whitelisted GitHub
IPs over TLS, and rollback removed both the nft table and the docker network
(this task created it).

## O1 — Source checks ✅

```text
infra/networking/copilot-egress.nft.example:36   define copilot_bridge = "br-copilot"
infra/networking/copilot-egress.nft.example:52       type filter hook forward priority filter; policy accept;
infra/networking/copilot-egress.nft.example:55       iifname != $copilot_bridge accept
(grep "hook output.*policy drop")                NO MATCH ✓
worker/tasks/copilot_cli.py:163                  _DEFAULT_DOCKER_NETWORK = "copilot-egress"
scripts/verify_copilot_egress_contract.py        OK (exit 0)
```

## O2 — Docker network ✅

`docker network inspect copilot-egress` returned not-found before this task.
Network was created by this task with the required options:

```text
docker network create \
  --driver bridge \
  --opt com.docker.network.bridge.name=br-copilot \
  --opt com.docker.network.bridge.enable_icc=false \
  copilot-egress
```

| Field | Value |
|---|---|
| pre_existing | false |
| created_by_task | true |
| bridge_name | `br-copilot` |
| icc | disabled |

## O3 — nft apply + resolver ✅

Backup taken before changes:
`/home/rick/.copilot/backups/f8a-egress-scope-20260506T224604Z/nft-ruleset-before.nft`

```text
sudo nft -c -f infra/networking/copilot-egress.nft.example   parse OK ✓
sudo nft -f infra/networking/copilot-egress.nft.example      apply OK ✓
```

Resolver (`scripts/copilot_egress_resolver.py --non-strict --format json`):

| set | count | sample |
|---|---:|---|
| `copilot_v4` | 3 | `140.82.114.21`, `4.228.31.149`, `4.228.31.153` |
| `copilot_v6` | 0 | — |
| errors | 0 | — |

Sets populated successfully. Final table:

```text
table inet copilot_egress {
    set copilot_v4  { type ipv4_addr; flags interval; elements = { 4.228.31.149, 4.228.31.153, 140.82.114.21 } }
    set copilot_v6  { type ipv6_addr; flags interval }
    chain forward {
        type filter hook forward priority filter; policy accept;
        iifname != "br-copilot" accept
        ct state established,related accept
        udp dport 53 accept
        tcp dport 53 accept
        tcp dport 443 ip  daddr @copilot_v4 log prefix "copilot-egress accept v4: " level info accept
        tcp dport 443 ip6 daddr @copilot_v6 log prefix "copilot-egress accept v6: " level info accept
        log prefix "copilot-egress DROP scoped: " flags all
        counter packets 0 bytes 0 drop
    }
}
```

The first rule short-circuits non-bridge traffic, so host packets never reach
the drop. Compare this with the previous template, which used
`hook output ... policy drop` and required every host process to be
explicitly allowlisted (the bug that broke Notion).

## O4 — Host egress non-regression ✅

With the scoped table active, host TLS traffic remained healthy:

| Endpoint | Result |
|---|---|
| `https://api.notion.com/v1/users` | `notion_http=401` (auth challenge — endpoint reachable) |
| `https://api.github.com/` | `github_http=200` |
| `http://127.0.0.1:8088/health` | `worker_health=200` |

This is the regression the previous host-wide template caused (39 DNS-failure
events on the worker during an 8-min window). The scoped template no longer
exhibits that behavior.

## O5 — Container network smoke ✅ (no Copilot token used)

Image: `umbral-sandbox-copilot-cli:6940cf0f274d`

```text
docker run --rm --network=copilot-egress --entrypoint /bin/sh \
  umbral-sandbox-copilot-cli:6940cf0f274d -lc \
  'node -e "require(\"https\").get(\"https://api.github.com/\", r => { ... })"'
```

| Field | Value |
|---|---|
| stdout | `github_status=403` |
| exit_code | `0` |

`api.github.com` resolves to `140.82.114.21`, which is in `copilot_v4`, so the
TLS handshake completes. GitHub returns 403 to unauthenticated `node https`
requests with no `User-Agent` — that is an HTTP-level response, confirming the
container reached the host. Drop counter stayed at `0 packets / 0 bytes` for
this smoke (no off-allowlist destination was attempted; future regression
tests should add a negative case for that).

## O6 — Rollback ✅

```text
sudo nft delete table inet copilot_egress       ✓ removed
docker network rm copilot-egress                ✓ removed (created by this task)
```

Final live state:

| Surface | Value |
|---|---|
| `inet copilot_egress` nft table | absent ✓ |
| `copilot-egress` docker network | absent ✓ |
| `RICK_COPILOT_CLI_ENABLED` | `true` (L1 stays open) |
| `RICK_COPILOT_CLI_EXECUTE` | `false` (L3 closed) ✓ |
| `egress.activated` | `false` (L4 closed) ✓ |
| `/health` | `200` ✓ |

## Secret scan

| Surface | Result |
|---|---|
| this report body | clean — no `ghp_*`, `github_pat_*`, `ghs_*`, `sk-*`, `WORKER_TOKEN`, or token literals |
| Copilot token usage during smoke | none — `O5` did not pass any token to the container |

## Verdict — 🟢 verde

The redesigned scoped egress model is safe to enable in a future F8A real-run
window:
- Host outbound traffic is unaffected.
- Container traffic from the dedicated bridge is filtered against the same
  resolver-driven IP set as before.
- Apply / rollback path is clean and idempotent.

Recommended next: a fresh `f8a-first-real-run` retry under the scoped profile,
keeping the same rollback discipline (close L3/L4, drop nft, drop docker
network if created by the task).
