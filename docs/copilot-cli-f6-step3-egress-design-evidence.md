# Copilot CLI — F6 Step 3 Evidence: Egress Profile Design Artifacts

**Phase:** F6 step 3 — egress profile **design artifacts only**.
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** at four layers (env,
policy, execute flag, code constant). `copilot_cli.egress.activated`
remains **`false`**.

---

## 1. What F6 step 3 actually does

- Versioned the operative design of the `copilot-egress` network
  profile as repo artifacts under `infra/networking/`.
- Added a stdlib-only verifier that asserts policy ↔ artifact ↔ docs
  parity and refuses to ship if `copilot_cli.egress.activated` flips
  to `true` while the design is still in review.
- Added 11 tests pinning the verifier behaviour with `tmp_path`.

It does **not** apply nftables, iptables, or ufw rules. It does
**not** create Docker networks. It does **not** flip
`copilot_cli.egress.activated`. It does **not** install any systemd
service or timer. It does **not** make any real Copilot HTTPS call.

## 2. Files added

```
infra/networking/copilot-egress.nft.example
infra/networking/copilot-egress-resolver.md
scripts/verify_copilot_egress_contract.py        (executable, stdlib only)
tests/test_verify_copilot_egress_contract.py
docs/copilot-cli-f6-step3-egress-design-evidence.md  (this file)
docs/copilot-cli-capability-design.md            (F6 step 3 status)
```

Files NOT created / NOT touched:
- `/etc/nftables.d/copilot-egress.nft` — live ruleset, NOT created.
- `/etc/systemd/system/copilot-egress-resolver.{service,timer}` — NOT created.
- Any `nft`, `iptables`, `ip6tables`, `ufw` invocation — NOT executed.
- Any `docker network create` — NOT executed.
- `~/.openclaw/openclaw.json` — NOT touched.
- `worker/tasks/copilot_cli.py` — unchanged from F6 step 1.
- `config/tool_policy.yaml` — egress block left intact, `activated:
  false` confirmed.

## 3. nftables artifact

`infra/networking/copilot-egress.nft.example`:

- `table inet copilot_egress` with three chains (`output`, `input`,
  `forward`), all `policy drop` by default.
- Two named sets (`copilot_v4`, `copilot_v6`) declared but empty —
  populated by the resolver in F6 step 4+, never by hand.
- Egress allowed only on TCP/443 to addresses in those sets, plus DNS
  to the systemd-resolved stub on the host.
- Every accept and every drop logged with prefix `copilot-egress
  accept …` / `copilot-egress DROP: ` for `journalctl` audit.
- File header explicitly states **"DO NOT APPLY IN F6 STEP 3"** and
  documents the operator-only apply / rollback procedure.
- Endpoint comments at the bottom (`#   allowed: <host>`) mirror the
  authoritative list in `config/tool_policy.yaml ::
  copilot_cli.egress.allowed_endpoints`. The verifier enforces parity.

## 4. Resolver design note

`infra/networking/copilot-egress-resolver.md` explains:

- Why nftables can't take domain names directly (rules match on IP
  headers; SNI/Host arrives later in the stack).
- Cache strategy: `OnCalendar=*:0/15`, atomic `flush set`/`add element`
  refresh, TTL = `max(min(record_ttl) * 2, 5min)`.
- Fallback if DNS fails: keep the previous IP set, emit
  `resolver_dns_outage`, surface a healthcheck warning. Never flush to
  empty.
- Audit: one JSONL record per refresh under
  `reports/copilot-cli/egress/<YYYY-MM>/<batch_id>.jsonl` (already
  gitignored from F4).
- Rollback sequence — operator-only, never agent-driven.
- F6 step 4 unblock conditions.

## 5. Verifier — `scripts/verify_copilot_egress_contract.py`

stdlib-only. Default behaviour: read-only, no DNS, no firewall calls.

Checks performed:

| Check | Code | Severity |
|---|---|---|
| `tool_policy.yaml` contains `copilot_cli.egress.activated` | `missing_activated_flag` | error |
| `copilot_cli.egress.activated == false` | `egress_activated_true` | error |
| `copilot_cli.egress.allowed_endpoints` non-empty | `missing_allowed_endpoints` | error |
| nft artifact contains `DO NOT APPLY` | `missing_marker` | error |
| nft artifact contains `policy drop` | `missing_marker` | error |
| nft artifact declares `table inet copilot_egress` | `missing_marker` | error |
| Every policy host appears in nft artifact | `endpoint_missing_in_artifact` | error |
| nft artifact has no uncommented `nft add/delete/flush`, `iptables`, `ufw`, `systemctl start/enable/restart`, `docker network create` | `uncommented_live_command` | error |
| Resolver doc contains `DESIGN ONLY` + `rollback` | `missing_marker` | error |
| Every policy host mentioned in resolver doc | `endpoint_undocumented` | warn |
| Optional DNS sanity (`--resolve`) | `dns_resolved` / `dns_unresolved` | info / warn |

Flags:
- `--policy <path>`, `--nft <path>`, `--resolver-doc <path>` — overrides.
- `--resolve` — opt-in DNS lookup. Read-only, results printed only,
  no files written, no firewall touched.

Smoke run from this commit:

```
$ python scripts/verify_copilot_egress_contract.py
OK
$ echo $?
0
```

`--resolve` was tested only via stubbed `socket.getaddrinfo` in
`tests/test_verify_copilot_egress_contract.py` — it is NOT exercised
on the host in step 3.

## 6. Tests

```
$ WORKER_TOKEN=test python -m pytest \
    tests/test_verify_copilot_egress_contract.py \
    tests/test_verify_copilot_cli_env_contract.py \
    tests/test_copilot_cli.py \
    tests/test_rick_tech_agent.py -q
..............................................................................   [ 90%]
........                                                                          [100%]
86 passed in 1.33s
```

Coverage delta vs F6 step 2 (+12 tests):
- repo artifacts pass verifier as-is
- synthetic minimal artifacts pass
- fails when `activated: true`
- fails when `policy drop` missing in nft artifact
- fails when `DO NOT APPLY` marker missing
- fails when policy endpoint missing in nft artifact
- fails on uncommented dangerous live command
- commented dangerous live command is OK
- `--resolve` does not write files (tmp_path snapshot before/after)
- default run does NOT call `getaddrinfo` (asserts via stub raising)
- shipped policy still has egress disabled
- `main([])` exits 0 against this repo

## 7. What F6 step 3 explicitly does NOT do

- ✗ Does NOT run `nft`, `iptables`, `ip6tables`, `ufw`.
- ✗ Does NOT create or modify any Docker network.
- ✗ Does NOT install `/etc/nftables.d/copilot-egress.nft`.
- ✗ Does NOT install or enable any systemd unit / timer.
- ✗ Does NOT flip `copilot_cli.egress.activated`.
- ✗ Does NOT call any Copilot endpoint over HTTPS.
- ✗ Does NOT provision, store, or transmit any token.
- ✗ Does NOT touch `worker/`, `dispatcher/`, `~/.openclaw/`.
- ✗ Does NOT touch Notion / gates / publication.
- ✗ Does NOT open / merge / comment any PR.

## 8. F6 step 4 unblock conditions

To advance to F6 step 4 (resolver implementation + dry-run install of
the nft dropin), the following must hold:

1. This document is reviewed and approved by David.
2. `config/tool_policy.yaml :: copilot_cli.egress.allowed_endpoints`
   is final — no churn during step 4.
3. `python scripts/verify_copilot_egress_contract.py` exits 0 on the
   target VPS.
4. Operator confirmed the VPS uses `nftables` (not legacy `iptables`)
   and that no other tenant on the host depends on a permissive
   `output` policy.
5. F6 step 4 plan must keep `copilot_cli.egress.activated = false`
   while the resolver is dry-run'd; activation is gated by step 5.

## 9. Next prompt recommendation (F6 step 4 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 4: implement the resolver
> `scripts/copilot_egress_resolver.py` per the design in
> `infra/networking/copilot-egress-resolver.md`, in `--dry-run` mode
> only. The resolver must:
> - Read endpoints from `config/tool_policy.yaml`.
> - Resolve each via `getaddrinfo`.
> - Print the IP set diff that *would* be applied, never call `nft`.
> - Write the JSONL audit record to a tmp path (not `/etc`, not
>   `reports/`).
> Add tests + evidence doc. `copilot_cli.egress.activated` stays
> `false`. Live `nft` invocation is reserved for step 5.
