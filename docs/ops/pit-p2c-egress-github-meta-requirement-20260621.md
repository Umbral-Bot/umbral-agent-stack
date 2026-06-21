# PIT P2c Egress GitHub Meta Requirement - 2026-06-21

## Context

PIT P2c run2 authenticated successfully, but the real read-only
`copilot_cli.run` probe ended partial because nft dropped 35 outbound
connections to `140.82.112.21:443`. The resolver had been run without
GitHub Meta, so the nft allow-list contained only the point-in-time DNS
answers: 3 IPv4 addresses, not the broader GitHub load-balancer CIDRs.

This was not an auth failure and must not trigger token rotation.

## Requirement

Every live activation, live probe, or operator runbook that prepares nft
sets for real Copilot CLI traffic must resolve with GitHub Meta enabled:

```sh
python scripts/copilot_egress_resolver.py \
  --for-live-activation \
  --include-github-meta \
  --format json
```

`--for-live-activation` implies `--include-github-meta`, but runbooks
should keep the explicit flag visible so command transcripts are easy to
audit. Before the single real POST in a live probe, evidence must show
`140.82.112.0/20` in the resolver output and in the nft set.

## Repository guardrail

`scripts/verify_copilot_egress_contract.py` scans the canonical
activation playbook. If a live resolver command omits both
`--include-github-meta` and `--for-live-activation`, the verifier fails
with `github_meta_flag_missing`.

Target validation:

```sh
python scripts/verify_copilot_egress_contract.py --strict
python -m pytest tests/test_copilot_egress_resolver.py tests/test_verify_copilot_egress_contract.py
```

