---
id: f8g-verify-canonical-pin-vps-2026-05-08
title: F8G verify — canonical gpt-5.5 high-effort pin (worker-mediated T8 re-run)
status: open
verdict: pending
owner: copilot-vps
reviewer: copilot-chat
phase: F8G-verify
depends_on:
  - f8g-pin-gpt55-high-effort (PR #337, merged to main 2026-05-08)
  - f8f-max-model-performance-benchmark-2026-05-07 (T8 RED baseline)
created: 2026-05-08
---

# F8G verify — re-run canonical T8 against the merged pin

## Why

F8G (PR #337) merged to `main` on 2026-05-08. It pins the canonical Copilot CLI
to `gpt-5.5` with `--reasoning-effort high`, adds `force_default_model: true`,
and registers aliases `GPT-5.5`/`GPT 5.5` → `gpt-5.5`. The F8F T8 canonical
worker probe was RED precisely because the worker forwarded `GPT-5.5`
(display-name with capitals) verbatim and the CLI rejected it. The pin should
close that gap. We need worker-mediated proof on the real VPS, not a repo read.

Per repo policy: "El repo refleja intención; la VPS refleja realidad."

## Pre-flight (mandatory)

```bash
cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
# Verify the pin landed
grep -n "default_model" config/tool_policy.yaml
grep -n "force_default_model" config/tool_policy.yaml
grep -n "default_reasoning_effort" config/tool_policy.yaml
# Expected: default_model: gpt-5.5, force_default_model: true, default_reasoning_effort: high
```

## Deploy

```bash
source .venv/bin/activate
pip install -e .   # only if pyproject.toml changed; harmless if not
systemctl --user restart umbral-worker
sleep 2
curl -fsS http://127.0.0.1:8088/health
# Expect: {"ok":true,...}
```

## T8 canonical re-run

Re-run the exact same canonical worker probe used in F8F T8 — but this time
**do NOT pass `--model` from the caller**. The pin must drive the CLI to
`gpt-5.5` with `--reasoning-effort high` automatically. Capture:

1. `POST /run` payload (no model override).
2. Worker audit JSON line — must show `model: gpt-5.5` and
   `reasoning_effort: high`.
3. Artifact manifest — must record `model: gpt-5.5` and
   `reasoning_effort: high`.
4. CLI stderr — must NOT contain `Error: Model "..." from --model flag is not available.`
5. Result — must be exit 0 with markers (same canonical task as F8F T8).

Then run a **second** probe that explicitly tries to override the model with a
non-default value (e.g. `--model claude-opus-4.6`). Expected behavior with
`force_default_model: true`: worker rejects the override BEFORE invoking the
CLI, audit logs the rejection reason, exit non-zero with a clear message. No
leaks, no egress drops.

## Acceptance gates

- [ ] T8a (default path): exit 0, audit + manifest record `gpt-5.5` + `high`,
      no CLI rejection, `secret_scan=clean`, zero nft drops.
- [ ] T8b (override-rejection path): non-zero exit from worker (NOT from CLI),
      audit records the rejection reason citing `force_default_model`,
      `secret_scan=clean`, zero nft drops.
- [ ] `/health` still `{"ok":true}` after both probes.
- [ ] No drop-in service overrides left behind (revert any temporary
      `~/.config/systemd/user/umbral-worker.service.d/*.conf` if you added one).

## Deliverables

1. Report under `reports/copilot-cli/f8g-verify-canonical-pin-2026-05-08.md`
   with both probe payloads, audit excerpts, manifest excerpts, and a verdict
   (verde / amarillo / rojo).
2. Metrics JSON `reports/copilot-cli/f8g-verify-canonical-pin-2026-05-08.metrics.json`
   with `{t8a: pass|fail, t8b: pass|fail, latency_ms, tokens_in, tokens_out, cost_estimate}`.
3. Branch `copilot-vps/f8g-verify-canonical-pin-2026-05-08` → PR to `main`.
4. Update this task file: `status: done`, `verdict: <color>`.

## Hard constraints

- No secrets in the report. Apply `secret-output-guard` before pushing.
- No long-lived overrides. Anything you toggle to test, revert before closing.
- If the pin does NOT behave as expected, file the divergence as the finding —
  do NOT patch `config/tool_policy.yaml` from this task. Open a follow-up F8H
  task instead.

## Rollback

If the worker fails to start or `/health` goes red after restart:

```bash
git -C ~/umbral-agent-stack log --oneline -5 config/tool_policy.yaml
# revert the pin commit locally if needed (do NOT push the revert without sign-off):
# git revert <pin-sha> -- config/tool_policy.yaml
systemctl --user restart umbral-worker
curl -fsS http://127.0.0.1:8088/health
```

Then escalate via mailbox; do NOT continue.
