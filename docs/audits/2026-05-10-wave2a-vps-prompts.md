# Wave 2.A — VPS verification prompts (paste-ready)

**Date**: 2026-05-10
**Audience**: Copilot-VPS (the agent with SSH to the Umbral VPS).
**Purpose**: per-PR runtime verification on the real VPS clone of
`umbral-agent-stack`, in line with the
[VPS Reality Check Rule](../../umbral-agent-stack/.github/copilot-instructions.md#vps-reality-check-rule)
and the cross-repo handoff protocol.

Each prompt MUST be pasted **verbatim**. Each prompt starts with the
mandatory checkout-main + pull preamble per `cross-repo-handoff-rules.md`
to defend against the VPS clone being checked out on a stale feature
branch.

---

## VPS-1 — Verify final state of #407 (publish_guard hardening)

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

# Switch to the #407 branch in read-only mode (NO commits, NO push)
git checkout -B verify/407 origin/copilot-vps/wave2a-405-stop-button
git log --oneline -5
git diff --stat main...HEAD

# Confirm Python venv
source .venv/bin/activate
python -V

# Run the wave2a relevant tests
PYTHONPATH=. python -m pytest \
  tests/lib/test_publish_guard.py \
  tests/lib/test_runtime_flags.py \
  tests/discovery/test_publish_guard_runtime_block.py \
  -q

# Run the full suite to confirm no collateral damage
PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -20

# Smoke the runbook flow (NO real publish — guard must block)
PUBLISH_ENABLED=false DRY_RUN=true MAX_POSTS=0 PYTHONPATH=. python -c "
from scripts.discovery.lib.publish_guard import assert_can_publish, PublishBlockedError
from scripts.discovery.lib.runtime_flags import PublishFlags
flags = PublishFlags(publish_enabled=False, dry_run=True, max_posts=0, max_posts_per_day=0)
try:
    assert_can_publish(channel='linkedin', publication_content_hash='x'*64, flags=flags)
    print('FAIL: should have raised')
except PublishBlockedError as e:
    print('OK runtime_block reasons:', e.reasons)
"

# Verify ops_log received exactly one runtime_block event
tail -5 ~/.config/umbral/ops_log.jsonl | jq 'select(.event=="publish_guard.runtime_block")' | tail -3

# Restore main
git checkout main
echo "VPS-1 complete. Report: branch innocent? full suite delta? runbook smoke OK?"
```

**Expected**: 94 wave2a tests pass; full suite shows only the pre-
existing `test_stage9b_linkedin_oauth.py::test_exchange_code_persists_tokens`
failure; smoke prints `OK runtime_block reasons: ['publish_enabled=false', 'dry_run=true', 'max_posts=0', 'max_posts_per_day=0']`
(or equivalent ordering); ops_log shows one `publish_guard.runtime_block`
event.

---

## VPS-2 — Verify #402 (PR #410, publication_content_hash)

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

git checkout -B verify/402 origin/rrss-wave2a/402-publication-content-hash
git log --oneline -5
git diff --stat origin/copilot-vps/wave2a-405-stop-button...HEAD

# Confirm restrictions: no Stage 7.5 / variants / O16.2 / aeco-kb / azure
git diff --name-only origin/main...HEAD | grep -E "stage7_5|variants\.py|aeco|o16|azure|infra/docker|containerapp" || echo "OK: no forbidden paths touched"

# Activate venv and run
source .venv/bin/activate
PYTHONPATH=. python -m pytest \
  tests/lib/test_publication_hash.py \
  tests/discovery/test_publish_guard_publication_hash_integration.py \
  -q

# Full suite
PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -20

# Confirm PR is still DRAFT and labeled do-not-merge
gh pr view 410 --json isDraft,labels,mergeable,baseRefName,headRefName \
  | jq '{isDraft, labels: [.labels[].name], mergeable, baseRefName, headRefName}'

git checkout main
echo "VPS-2 complete. Report: 32 new tests pass? full suite delta = 1 (pre-existing)? PR draft+do-not-merge confirmed?"
```

**Expected**: 32 new tests pass; full suite passes 520 / fails 1 (pre-
existing); `gh pr view` returns `isDraft: true`, labels include
`do-not-merge` + `wave2`, base = `copilot-vps/wave2a-405-stop-button`.

---

## VPS-3 — Verify #404-lite (PR #411, publish_log.jsonl)

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

git checkout -B verify/404lite origin/rrss-wave2a/404-lite-publish-log
git log --oneline -5
git diff --stat main...HEAD

# Confirm restrictions: no integration with publish_guard, no dashboard,
# no real publisher wiring
git diff --name-only main...HEAD
# Expect ONLY:
#   docs/editorial-pipeline/publish-log-contract.md
#   scripts/discovery/lib/publish_log.py
#   tests/lib/test_publish_log.py

# Activate venv and run
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/lib/test_publish_log.py -q

# Full suite
PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -20

# Smoke the writer in a temp file (NO touch to ~/.config/umbral)
PYTHONPATH=. PUBLISH_LOG_PATH=/tmp/wave2a_smoke_publish_log.jsonl python -c "
from scripts.discovery.lib.publish_log import write_event, read_events
write_event({'event': 'publish_guard.runtime_block', 'channel': 'linkedin', 'would_publish': False, 'block_reasons': ['publish_enabled=false']})
print('events:', read_events())
"
rm /tmp/wave2a_smoke_publish_log.jsonl

# Confirm PR draft + labels
gh pr view 411 --json isDraft,labels,mergeable,baseRefName,headRefName \
  | jq '{isDraft, labels: [.labels[].name], mergeable, baseRefName, headRefName}'

git checkout main
echo "VPS-3 complete. Report: 18 new tests pass? full suite delta = 1 (pre-existing)? smoke prints one event? PR draft+do-not-merge confirmed?"
```

**Expected**: 18 new tests pass; full suite passes 242 / fails 1 (pre-
existing); diff name-only is exactly the 3 expected files; smoke prints
the event back; `gh pr view` returns `isDraft: true`, labels include
`do-not-merge` + `wave2`, base = `main`.

---

## VPS-4 — n8n applicability scan validation (DESIGN-ONLY)

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

# Pull the docs branch read-only
git checkout -B verify/wave2a-docs origin/rrss-wave2a/docs-and-prompts
ls -la docs/audits/2026-05-10-wave2a-*

# Confirm n8n canonical context dump exists for the scan
ls -la docs/external-context/n8n-llms-full.txt && \
  wc -l docs/external-context/n8n-llms-full.txt

# Read the scan
cat docs/audits/2026-05-10-wave2a-n8n-applicability-scan.md | head -120

# Verify n8n service state on VPS (DESIGN ONLY — DO NOT activate any workflow)
systemctl --user status n8n 2>&1 | head -10 || echo "n8n not under systemd --user (expected if installed differently)"

# If n8n is running, list workflows but DO NOT activate
if systemctl --user is-active n8n >/dev/null 2>&1; then
  echo "n8n active. Listing workflows via REST (read-only)…"
  # If n8n CLI / REST is exposed locally, list active workflows:
  # curl -s http://127.0.0.1:5678/rest/workflows | jq '.data[] | {id, name, active}'
  echo "(skipping list — operator must confirm REST endpoint availability)"
else
  echo "n8n not active. No workflows to enumerate."
fi

# CRITICAL: confirm zero productive workflows touch publish_guard / blog / linkedin
echo "Operator must visually confirm: NO active n8n workflow performs:"
echo "  - publish to LinkedIn"
echo "  - publish to blog"
echo "  - flip publish_enabled / dry_run / max_posts"
echo "  - write to ~/.config/umbral/ops_log.jsonl or publish_log.jsonl"
echo "  - mark aprobado_contenido / autorizar_publicacion in Notion"

git checkout main
echo "VPS-4 complete. Report: scan readable? n8n state? confirmed zero productive workflows touch the publish path?"
```

**Expected**: scan markdown present and readable; n8n state reported
(active or not — both acceptable, this is a design-only pass); operator
explicitly confirms NO active workflow touches the publish authority
chain.

---

## Reporting back

For each VPS-N, report in this exact shape:

```text
VPS-N result
- branch innocence: PASS / FAIL (paste evidence line)
- tests: <N passed, M failed> (list failures)
- restrictions: PASS / FAIL (paste grep evidence)
- runtime invariant: PASS / FAIL (paste smoke output)
- decisions raised: <list, or "none">
```
