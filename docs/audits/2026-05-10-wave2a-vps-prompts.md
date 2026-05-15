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

## VPS-2 — Verify #402 (PR #410, publication_content_hash) [REFRESHED 2026-05-13 post-rebase]

> **Contexto**: #410 fue rebaseada sobre `origin/main` el 2026-05-13
> tras el merge de #407 (`30e5489f`). Nuevo HEAD = `dc42e38f`, nueva
> base = `main`, single commit (no merge ancestry). Cero conflictos.
> Tests locales 132/132 verdes. Restricciones intactas. Aún DRAFT +
> `do-not-merge` — esta verificación NO autoriza merge.

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

# Single commit branch directly on top of main (post-rebase)
git checkout -B verify/402 origin/rrss-wave2a/402-publication-content-hash
git log --oneline -5
# Expected: HEAD = dc42e38f, parent = 30e5489f (merge of #407)
test "$(git rev-parse HEAD)" = "dc42e38f4cb10071990edef92a8721844a235c5a" \
  && echo "HEAD OK" || echo "HEAD MISMATCH (re-confirm con repo-side antes de mergear)"

# Diff vs main: must show ONLY the 5 files of #410
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
# Expect EXACTLY:
#   docs/editorial-pipeline/publication-content-hash-contract.md
#   scripts/discovery/lib/dedup.py
#   scripts/discovery/lib/publication_hash.py
#   tests/discovery/test_publish_guard_publication_hash_integration.py
#   tests/lib/test_publication_hash.py

# Confirm restrictions: no Stage 7.5 / variants / O16.2 / aeco-kb / azure / containerapp / publisher real / Notion writes
git diff --name-only origin/main...HEAD | grep -E "stage7_5|variants\.py|aeco|o16|azure|infra/docker|containerapp|notion|n8n|cron|publisher" \
  && echo "WARN: forbidden path touched — abort verification" \
  || echo "OK: no forbidden paths touched"

# Activate venv and run targeted tests
source .venv/bin/activate
PYTHONPATH=. python -m pytest \
  tests/lib/test_publication_hash.py \
  tests/discovery/test_publish_guard_publication_hash_integration.py \
  tests/lib/test_publish_flags.py \
  tests/discovery/test_publish_guard_flags_integration.py \
  tests/discovery/test_publish_guard.py \
  -q
# Expected (per repo-side rehearsal 2026-05-13): 132 passed in <2s

# Full suite (sanity check no regression)
PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -20

# Confirm PR still DRAFT + do-not-merge + base=main
gh pr view 410 --json isDraft,labels,mergeable,baseRefName,headRefName,headRefOid \
  | jq '{isDraft, labels: [.labels[].name], mergeable, baseRefName, headRefName, headRefOid}'

# Read-only: NO push, NO merge, NO label change, NO branch delete
git checkout main
echo "VPS-2 complete. Report: HEAD == dc42e38f? 132 targeted tests PASS? full suite green or only pre-existing fail? PR isDraft=true + labels include do-not-merge + base=main confirmed?"
```

**Expected (PASS criteria)**:
- HEAD `dc42e38f4cb10071990edef92a8721844a235c5a`
- Diff name-only = exactly the 5 files listed above
- Forbidden-path grep returns "OK: no forbidden paths touched"
- 132 targeted tests pass
- Full suite shows no regression vs `main` (only pre-existing failures, if any)
- `gh pr view` returns `isDraft: true`, labels `[do-not-merge, wave2]`, `mergeable: MERGEABLE`, `baseRefName: main`, `headRefOid: dc42e38f...`

**ABORT criteria** (report immediately, do NOT continue):
- HEAD mismatch
- Forbidden-path grep finds anything
- Any of the 132 targeted tests fail
- Full suite shows a NEW regression vs `main`

---

## VPS-3 — Verify #404-lite (PR #411, publish_log.jsonl) [REFRESHED 2026-05-13 con requisitos explícitos de David]

> **Contexto**: David autorizó VPS-3 el 2026-05-13. Verificación
> read-only. Cero merge, cero push, cero label change, cero touch a
> `~/.config/umbral/publish_log.jsonl` productivo (usar `PUBLISH_LOG_PATH`
> temporal). Cero integración con `publish_guard` (eso es Wave 2.B).

```bash
cd ~/umbral-agent-stack && \
  git checkout main && \
  git pull --ff-only origin main && \
  git status --short && \
  git branch --show-current && \
  git fetch origin

git checkout -B verify/404lite origin/rrss-wave2a/404-lite-publish-log
git log --oneline -5
# Expected HEAD = 2c6fe4600dac9b24004743134c7eb44a0b13902b (o reportar si cambió)
test "$(git rev-parse HEAD)" = "2c6fe4600dac9b24004743134c7eb44a0b13902b" \
  && echo "HEAD OK" || echo "HEAD CHANGED — reportar nuevo SHA"

# Diff vs main: must show ONLY 3 files (1 doc + 1 lib + 1 test)
git diff --name-only origin/main...HEAD
# Expect EXACTLY:
#   docs/editorial-pipeline/publish-log-contract.md
#   scripts/discovery/lib/publish_log.py
#   tests/lib/test_publish_log.py

# Confirm restrictions: no integration with publish_guard, no publisher real,
# no cron, no n8n, no Notion writes, no O16.2, no Stage 7.5 / variants
git diff --name-only origin/main...HEAD | grep -E "publish_guard|stage7_5|variants\.py|aeco|o16|azure|containerapp|notion|n8n|cron|publisher" \
  && echo "WARN: forbidden integration touched — abort" \
  || echo "OK: no forbidden paths touched"

# Activate venv
source .venv/bin/activate

# Targeted tests
PYTHONPATH=. python -m pytest tests/lib/test_publish_log.py -q
# Expected: 18 passed (per repo-side rehearsal 2026-05-12: 18/18 in 1.41s)

# Full suite (sanity check no regression)
PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -20

# === Smoke test the writer in a TEMP path (NEVER touch ~/.config/umbral) ===
SMOKE_LOG="/tmp/wave2a_vps3_smoke_$(date +%s).jsonl"
echo "Using temp log: $SMOKE_LOG"

PYTHONPATH=. PUBLISH_LOG_PATH="$SMOKE_LOG" python <<'PY'
import os, json
from scripts.discovery.lib.publish_log import write_event, read_events

# 1. Round-trip: write_event + read_events
event = {
    "event": "publish_guard.runtime_block",
    "channel": "linkedin",
    "would_publish": False,
    "block_reasons": ["publish_enabled=false", "dry_run_enabled"],
    "flags": {
        "publish_enabled": False,
        "dry_run": True,
        "max_posts": 1,
        "max_posts_per_day": 1,
    },
    "publication_content_hash": "p" * 64,
    "source_content_hash": "s" * 64,
}
original_keys = set(event.keys())
original_snapshot = json.dumps(event, sort_keys=True)

write_event(event)

# (a) Confirm the dict was NOT mutated by the writer
assert json.dumps(event, sort_keys=True) == original_snapshot, "MUTATION: writer modified the input dict"
print("PASS: write_event does not mutate the original dict")

# (b) Read back
events = read_events()
assert len(events) == 1, f"expected 1 event, got {len(events)}"
e = events[0]

# (c) Confirm timestamp_utc was added
assert "timestamp_utc" in e, "MISSING: timestamp_utc not added on write"
assert e["timestamp_utc"].endswith("Z") or "+" in e["timestamp_utc"], f"timestamp_utc not UTC ISO: {e['timestamp_utc']}"
print(f"PASS: timestamp_utc present and UTC: {e['timestamp_utc']}")

# (d) Confirm canonical contract fields preserved
required = {"event", "channel", "would_publish", "block_reasons", "flags", "publication_content_hash", "source_content_hash"}
missing = required - set(e.keys())
assert not missing, f"MISSING canonical fields: {missing}"
print(f"PASS: canonical fields preserved: {sorted(required)}")

# (e) Confirm flags sub-dict preserved as documented
assert e["flags"]["publish_enabled"] is False
assert e["flags"]["dry_run"] is True
assert e["flags"]["max_posts"] == 1
assert e["flags"]["max_posts_per_day"] == 1
print("PASS: flags sub-dict preserved with all 4 fields")

# 2. Append-only: second write must NOT overwrite the first
event2 = dict(event)
event2["event"] = "publish_guard.pass"
write_event(event2)
events_after = read_events()
assert len(events_after) == 2, f"APPEND-ONLY VIOLATION: expected 2 events, got {len(events_after)}"
assert events_after[0]["event"] == "publish_guard.runtime_block"
assert events_after[1]["event"] == "publish_guard.pass"
print(f"PASS: append-only confirmed (2 events, in order)")

# 3. JSONL format (one JSON per line, parseable independently)
log_path = os.environ["PUBLISH_LOG_PATH"]
with open(log_path) as f:
    lines = [ln for ln in f.read().splitlines() if ln.strip()]
assert len(lines) == 2
for ln in lines:
    json.loads(ln)  # raises if not valid JSON
print(f"PASS: JSONL format valid ({len(lines)} lines, each parseable)")

print("\n=== VPS-3 ROUND-TRIP: ALL CHECKS PASS ===")
PY

# Cleanup temp log
rm -f "$SMOKE_LOG"
echo "Cleaned up: $SMOKE_LOG"

# Confirm publish_log.py does NOT import publish_guard (no cross-integration)
grep -E "from scripts.discovery.lib.publish_guard|import.*publish_guard" \
    scripts/discovery/lib/publish_log.py \
  && echo "WARN: publish_log integrates with publish_guard — Wave 2.B regression" \
  || echo "OK: publish_log does not integrate with publish_guard (Wave 2.A scope respected)"

# Confirm no productive log was touched
test -f ~/.config/umbral/publish_log.jsonl && echo "INFO: productive log exists (untouched)" || echo "INFO: no productive log present"
ls -la ~/.config/umbral/publish_log.jsonl 2>/dev/null | head -1

# PR state (read-only)
gh pr view 411 --json isDraft,labels,mergeable,baseRefName,headRefName,headRefOid \
  | jq '{isDraft, labels: [.labels[].name], mergeable, baseRefName, headRefName, headRefOid}'

git checkout main
echo "VPS-3 complete. Report PASS/PARTIAL/FAIL + tests count + temp path used + round-trip evidence + restrictions verified + listo-para-merge yes/no"
```

**Expected (PASS criteria)**:
- HEAD `2c6fe4600dac9b24004743134c7eb44a0b13902b` (o reportar nuevo SHA)
- Diff name-only = exactly the 3 files listed
- Forbidden-path grep returns "OK: no forbidden paths touched"
- 18 targeted tests pass
- Round-trip script prints "ALL CHECKS PASS" with all 5 sub-checks (mutation, timestamp_utc, canonical fields, flags sub-dict, append-only, JSONL)
- `publish_log.py` does NOT import `publish_guard`
- Productive log untouched
- `gh pr view` returns `isDraft: true`, labels `[do-not-merge, wave2]`, `baseRefName: main`

**Reportar como**:
- **PASS**: todos los criterios arriba; #411 listo para merge cuando David autorice.
- **PARTIAL**: tests verdes + round-trip OK pero algún campo canónico falta o no preserva exactamente. Detallar gap.
- **FAIL**: tests rojos, round-trip falla, mutación detectada, integración indebida con publish_guard, o productive log fue tocado.

**Restricciones cero-touch**: NO push, NO merge, NO label change, NO branch delete, NO touch a `~/.config/umbral/publish_log.jsonl`, NO cron, NO publisher real, NO Notion writes, NO n8n.

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
