# Secrets and Tokens Runbook — RRSS Editorial Pipeline

> **Scope:** Wave 2.A doc-only. Inventories the secrets and runtime flags
> used by the editorial pipeline, their storage, rotation, audit, and
> emergency-stop procedure. **No real values appear in this document and
> none must ever be committed to the repo.**

## 1. Inventory (names only — never values)

The pipeline reads the following from the environment. Real values live
only on the VPS in `~/.config/openclaw/env`.

### Secrets (sensitive — rotate on suspected leak)

| Name                          | Purpose                                              |
|-------------------------------|------------------------------------------------------|
| `NOTION_API_KEY`              | Notion API token used by Stage 11 / governance writes. |
| `LINKEDIN_TOKEN_PLACEHOLDER`  | Placeholder for the LinkedIn publishing token (Wave 2.B). |
| `BLOG_API_TOKEN_PLACEHOLDER`  | Placeholder for the blog channel publishing token (Wave 2.B). |

Until Wave 2.B is approved, the LinkedIn and Blog tokens are
**placeholders only**. No real publishing credentials may be stored,
referenced, or imported by any code path.

### Operational flags (non-secret, but governance-controlled)

| Name                  | Type    | Purpose                                                       |
|-----------------------|---------|---------------------------------------------------------------|
| `OPS_LOG_PATH`        | path    | Path to the structured ops log used for fetch / refusal events. |
| `PUBLISH_LOG_PATH`    | path    | Path to the publish log (#411). Append-only.                  |
| `PUBLISH_ENABLED`     | bool    | Master enable for publishing. `false` = no sends, ever.        |
| `DRY_RUN`             | bool    | When `true`, all publish paths render but do not send.         |
| `MAX_POSTS`           | int     | Hard cap on total posts per run.                               |
| `MAX_POSTS_PER_DAY`   | int     | Rolling 24h cap enforced by the publish layer.                 |

`PUBLISH_ENABLED` and `DRY_RUN` together define the runtime kill-switch
described in §5.

---

## 2. Storage

- **VPS canonical store:** `~/.config/openclaw/env`.
- File mode: readable only by the runtime user (`chmod 600`).
- Loaded explicitly per shell with `set -a; source ~/.config/openclaw/env; set +a`.
- Loaded by services via systemd `EnvironmentFile=` in their unit files.

### What must never happen

- Secrets in the repo (`.env`, fixtures, examples, prompts, tests).
- Secrets in commit messages, PR descriptions, or issue comments.
- Secrets in logs, structured or otherwise.
- Secrets passed on the command line (visible in `ps`).
- Secrets sent to any LLM call, ever.

A `.env.example` may exist for local dev; it must contain **only** names
and inert placeholder strings (e.g. `NOTION_API_KEY=replace_me`).

---

## 3. Rotation

| Item                              | Cadence            | Owner |
|-----------------------------------|--------------------|-------|
| `NOTION_API_KEY`                  | Every 90 days, or on suspected leak | David |
| `LINKEDIN_TOKEN_PLACEHOLDER`      | On vendor expiry, or on suspected leak | David |
| `BLOG_API_TOKEN_PLACEHOLDER`      | On vendor expiry, or on suspected leak | David |
| Any token after a suspected leak  | Immediate          | On-call |

Rotation procedure (high level):

1. Generate new credential at provider.
2. Update `~/.config/openclaw/env` on the VPS in a single edit.
3. Restart the consuming service per
   [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md)
   deploy table.
4. Health check the service.
5. Revoke the old credential at the provider.
6. Record rotation in the ops log (date, who, which name; never the value).

A revoked credential whose old value still appears in any cache, browser
history, or screenshot is treated as compromised until proven otherwise.

---

## 4. Auditing the repo for accidentally committed tokens

Run these from a clean checkout. Both should return **no matches** other
than this very runbook (which contains only neutralized example
fragments).

Quick scan of current tree:

```bash
git grep -nE "(sk-|ghp_|xoxb-|secret_|EAA)[A-Za-z0-9]" -- ':!docs/runbooks/secrets-and-tokens.md' || echo "clean"
```

Full history scan (slower):

```bash
git log --all -p | grep -E "sk-|ghp_|xoxb-|EAA[A-Za-z0-9]" | head
```

If either scan returns a real-looking token:

1. Treat the credential as **compromised** immediately.
2. Revoke at the provider before doing anything else.
3. Open an incident task; do not `git push --force` to "rewrite history"
   without owner approval — see operational safety in
   [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md).

A future Wave 2.B item will wire a pre-commit hook that runs this scan
automatically.

---

## 5. Emergency stop

If publishing is misbehaving (wrong content, wrong audience, runaway
volume), stop the publish layer **first**, investigate **second**.

1. On the VPS, set:
   ```
   PUBLISH_ENABLED=false
   DRY_RUN=true
   ```
   in `~/.config/openclaw/env`.
2. Restart the affected services per the deploy table.
3. Confirm via the publish log that no further sends occur.
4. If a token may be compromised, revoke it at the provider before
   re-enabling.
5. Follow the channel-specific steps in
   `docs/runbooks/publish-emergency-stop.md` (created with Wave 2.B; if
   absent, escalate to David before re-enabling).

The kill-switch is intentionally redundant: `PUBLISH_ENABLED=false` must
short-circuit the send path even if `DRY_RUN` is misread.

---

## 6. Relationship with adjacent work

- **PublishFlags (#407)** — runtime structure that reads `PUBLISH_ENABLED`,
  `DRY_RUN`, `MAX_POSTS`, `MAX_POSTS_PER_DAY` and exposes them to Stage
  10. This runbook owns the variable names; #407 owns the loader.
- **`publication_content_hash` (#410)** — a content-derived hash. **Not a
  secret.** Safe to log, safe to compare across runs.
- **`publish_log` (#411)** — append-only publish journal. Records hashes,
  channel, status, and timestamps. Must not record token values, request
  bodies, or response bodies. If a caller writes payload contents into
  the publish log, that is a defect: the log can then leak PII or worse.
- **Source use policy** — see
  [source-use-policy.md](../editorial-pipeline/source-use-policy.md) for
  what may be fetched and how it is logged.

---

## 7. Human review before enabling real tokens

No real publishing token (LinkedIn, Blog, or any future channel) may be
placed in `~/.config/openclaw/env` until **all** of the following are
true:

1. Wave 2.B runtime for the channel is merged.
2. `PublishFlags` (#407) loader is in place and tested.
3. `publish_log` (#411) is in place and tested.
4. `publication_content_hash` (#410) is in place and tested.
5. The source use policy filters from §3 of that doc are enforced at
   runtime.
6. **David has explicitly approved** enabling the channel.

Until then, the placeholder names exist purely so that code can be
written and tested against them with `DRY_RUN=true`.

---

## 8. Deferred to Wave 2.B

- Pre-commit hook running the audit scans from §4.
- `docs/runbooks/publish-emergency-stop.md` with channel-specific
  procedures.
- Token-rotation automation (provider APIs, where supported).
- Per-channel scopes / least-privilege documentation.
- Encrypted-at-rest secret store (beyond file permissions).
