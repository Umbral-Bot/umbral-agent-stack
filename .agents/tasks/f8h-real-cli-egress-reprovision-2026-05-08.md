---
id: f8h-real-cli-egress-reprovision-2026-05-08
title: F8H — re-provision copilot-egress + close real-CLI gates left amarillo by F8G
status: open
verdict: pending
owner: copilot-vps
reviewer: copilot-chat
phase: F8H-real-exec
depends_on:
  - f8g-verify-canonical-pin-vps-2026-05-08 (PR #380, merged 2026-05-08, amarillo)
  - f8g-pin-gpt55-high-effort (PR #337, merged 2026-05-08)
created: 2026-05-08
governance_gate: required
---

# F8H — close the real-CLI evidence gap

## Why

F8G-verify (PR #380) closed the **worker layer** end-to-end: the canonical pin
resolves `model=gpt-5.5` + `reasoning_effort=high`, the `docker_argv` carries
`--model gpt-5.5 --reasoning-effort high` (the lowercase slug that fixed the
F8F T8 RED), and override-rejection works pre-CLI with
`error: model_not_allowed`. Verdict was **amarillo**, not verde, because:

- `copilot-egress` Docker bridge → torn down post-F8F.
- `inet copilot_egress` nft scoped chain → torn down post-F8F.
- `RICK_COPILOT_CLI_EXECUTE` was toggled `false→true→false` only for the
  `docker_argv` evidence, never for a real CLI invocation.

So gates "exit 0 with markers", "manifest record", "secret_scan=clean from a
real run", and "zero nft drops" remain unproven against the merged pin.

This task closes that gap **once**, captures evidence, and reverts.

## Pre-conditions (sign-off required BEFORE starting)

This task touches the egress lane. It must NOT run without:

- [ ] David's explicit sign-off in this task file (add `signed_off_by: david`
      and `signed_off_at: <ts>` to frontmatter).
- [ ] A documented rollback owner on standby.
- [ ] Skill `openclaw-vps-operator` consulted for the egress provisioning
      sequence.

If any pre-condition is missing → STOP and escalate via mailbox.

## Pre-flight

```bash
cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
# Confirm pin still in place
grep -nE "default_model|force_default_model|default_reasoning_effort" config/tool_policy.yaml
# Confirm egress is currently DOWN (expected starting state)
docker network ls | grep -i copilot-egress || echo "copilot-egress: absent (expected)"
sudo -n nft list tables 2>&1 | grep -i copilot_egress || echo "nft chain: absent (expected)"
# Worker baseline
systemctl --user is-active umbral-worker
curl -fsS http://127.0.0.1:8088/health
```

## Provision (governance-gated)

Re-provision strictly under the `openclaw-vps-operator` skill procedure. Do
NOT improvise the bridge/chain definitions — pull them from the canonical
spec in `runbooks/` (or whatever the operator skill points to). Capture every
command into `/tmp/f8h/provision.log`.

```bash
mkdir -p /tmp/f8h
# Apply canonical egress provisioning here per openclaw-vps-operator skill.
# (commands intentionally not duplicated here to avoid drift — read the skill)
# Verify post-provision:
docker network inspect copilot-egress | head -30 | tee -a /tmp/f8h/provision.log
sudo -n nft list table inet copilot_egress | tee -a /tmp/f8h/provision.log
```

## Flip L3 + L4 (temporary)

```bash
cp ~/.config/openclaw/copilot-cli.env /tmp/f8h/copilot-cli.env.backup
sed -i 's/^RICK_COPILOT_CLI_EXECUTE=false$/RICK_COPILOT_CLI_EXECUTE=true/' \
  ~/.config/openclaw/copilot-cli.env
# L4 (egress activation flag, name per current config) — verify via skill.
systemctl --user restart umbral-worker
sleep 2
curl -fsS http://127.0.0.1:8088/health
```

## Real T8a re-run (default path, real CLI)

Use the **same** payload from F8G T8a (no `model` in request). This time the
CLI must really execute, hit GitHub Models, and return.

Acceptance:

- [ ] Worker `/run` exit 0.
- [ ] Audit log has `model=gpt-5.5`, `reasoning_effort=high`,
      `policy.execute_enabled=true`, `policy.egress_activated=true`,
      `secret_scan=clean`.
- [ ] Manifest under `artifacts/copilot-cli/<run-id>/manifest.json` records
      `model=gpt-5.5`, `reasoning_effort=high`, output sha, byte counts.
- [ ] CLI stderr contains NO `Error: Model "..." from --model flag is not available.`
- [ ] Marker `F8H_T8A_REAL_OK` present in CLI stdout/output artefact.
- [ ] `sudo nft list ruleset | grep -A2 copilot_egress` → counters > 0 on
      ALLOW chain, **zero drops** on the DENY chain.

## Tear down (mandatory)

```bash
# Revert L3 + L4 first
cp /tmp/f8h/copilot-cli.env.backup ~/.config/openclaw/copilot-cli.env
diff /tmp/f8h/copilot-cli.env.backup ~/.config/openclaw/copilot-cli.env  # must be empty
systemctl --user restart umbral-worker && sleep 2 && curl -fsS http://127.0.0.1:8088/health
# Tear down egress per openclaw-vps-operator skill procedure
# Capture teardown log into /tmp/f8h/teardown.log
docker network ls | grep -i copilot-egress || echo "copilot-egress: torn down (expected)"
sudo -n nft list tables 2>&1 | grep -i copilot_egress || echo "nft chain: torn down (expected)"
```

## Deliverables

1. Report `reports/copilot-cli/f8h-real-cli-egress-2026-05-08.md` with:
   - Sign-off block (who, when).
   - Provisioning evidence (`/tmp/f8h/provision.log` excerpts).
   - Real T8a payload + audit + manifest excerpts.
   - nft counters before/after.
   - Teardown evidence.
   - Verdict (verde / amarillo / rojo).
2. Metrics JSON `reports/copilot-cli/f8h-real-cli-egress-2026-05-08.metrics.json`
   with `{t8a_real: pass|fail, latency_ms, tokens_in, tokens_out, cost_estimate, nft_drops}`.
3. Branch `copilot-vps/f8h-real-cli-egress-2026-05-08` → PR to `main`.
4. Update this task: `status: done`, `verdict: <color>`.
5. If anything was left non-baseline (network, chain, env flag, drop-in,
   manifest, secret) → file as a divergence finding in the report and
   restore before closing.

## Hard constraints

- `secret-output-guard` applied to all artefacts before push.
- No long-lived overrides. Anything toggled MUST be reverted.
- Do NOT patch `config/tool_policy.yaml` or any policy file from this task —
  it is verify+evidence only.
- If real T8a is RED, do NOT re-run blindly; capture the divergence and stop.

## Rollback (if anything goes sideways mid-task)

```bash
cp /tmp/f8h/copilot-cli.env.backup ~/.config/openclaw/copilot-cli.env || true
systemctl --user restart umbral-worker
curl -fsS http://127.0.0.1:8088/health
# Tear down egress unconditionally per skill
```

Then escalate via mailbox; do NOT continue.
