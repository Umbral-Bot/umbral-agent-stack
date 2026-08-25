# Rick Editorial — Activation Record (Phase 1)

> **Status**: ACTIVE (Phase 1) since 2026-08-25. Runtime-registered, deliberate-invocation-only (no cron, no autonomous routing), read-only Notion + no worker-write tool grant. First live cut: repair `CAND-OLA3-03`'s `Fuente primaria`, not a new `CAND-001`. Fase C outcome: `V1_PASS` (genuine V1 produced + `rick-qa`-approved) but `BLOCKED_SHORTLIST_WRITE_TASK_MISSING` — no worker task exists to register a new Shortlist/Alternativas row, so HITL-1 was never reached. See Fase C below.

This is the activation record for `PKG-MACRO-P5-Q12-T4` (David GO, 2026-08-25). It documents what changed to move `rick-editorial` from design-only (see `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`) to active, and the delta between the original contract and what was actually done. It follows the same shape as `docs/ops/rick-communication-director-agent.md`.

## Why now

`docs/ops/fuente-item-url-root-cause-2026-08-25.md` (PKG-MACRO-P5-Q12-T3) established that `CAND-OLA3-03`'s `Fuente primaria` is the buildingSMART home page, not the concrete piece, and that `rick-editorial` — the agent whose contract is supposed to prevent exactly this — had zero `openclaw.json` registration at the time. T3 built the fail-closed guard (`scripts/discovery/lib/url_classify.py::is_home_or_feed_url`) on the write paths. T4 closes the other half of the gap: activating the agent itself.

## What changed (Fase A)

### Live `~/.openclaw/openclaw.json`

- Backed up before any edit: `~/.openclaw/backups/openclaw.json.pre-rick-editorial-20260825T193635Z` (path only, no secrets in this doc).
- Added one entry to `agents.list`, placed after `rick-ops`, mirroring the `rick-qa`/`rick-communication-director` pattern:
  - `workspace`: `/home/rick/.openclaw/workspaces/rick-editorial`
  - `model.primary`: `openai/gpt-5.5` (fallbacks: `openai/gpt-5.6-sol`, `openai/gpt-5.4`)
  - `tools.profile`: `coding`, `alsoAllow`: `group:web`, `umbral_ping`, `umbral_provider_status`, `umbral_research_web`, `umbral_llm_generate`, `umbral_notion_read_page`, `umbral_notion_read_database`, `umbral_linear_update_issue_status`
  - `tools.deny`: `group:automation`, `browser`, `canvas`, `message`, `nodes`, every `umbral_notion_*` write/upsert/enrich tool, and — explicitly — `umbral_worker_enqueue` / `umbral_worker_run`, plus `umbral_make_post_webhook`, `umbral_gmail_create_draft`, `umbral_n8n_*`
  - `heartbeat.every`: `1h`, `thinkingDefault`: `xhigh`
- Added `"rick-editorial"` to `rick-orchestrator.subagents.allowAgents` (same list already containing `rick-communication-director`, `rick-delivery`, `rick-ops`, `rick-qa`, `rick-tracker`, `rick-linkedin-writer`).
- Diff against the backup is exactly these two changes. Validated twice: `python3 -c "json.load(...)"` and `openclaw config validate` — both passed.
- No gateway restart was performed or required: `openclaw agents list` reflected the new agent immediately, and the Fase B live invocation (below) routed correctly without one — same behavior observed for the `rick-qa`/`rick-communication-director` precedent.

### Model resolution — `azure-openai-responses/gpt-5.5` vs `openai/gpt-5.5`

The original ROLE.md contract named the model as `azure-openai-responses/gpt-5.5`. The live `models.providers` registry has exactly one provider key, `openai`, containing `gpt-5.6-sol`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`. There is no `azure-openai-responses` provider key in the live config. Cross-checked against:

- `rick-communication-director`'s live config, which itself uses `openai/gpt-5.6-sol` — its own activation doc records a real live smoke test (Run ID `bf1d7859-e208-4cb4-8a66-4d00e77f127d`, 2026-04-24) that captured `azure-openai-responses/gpt-5.4` as the actual model string at that time. That was a genuine literal value then, not prose — confirming the provider namespace has moved twice since (once at the 2026-07-12 revert below, again to today's `openai` key), not that anyone mis-described it.
- A March-2026 historical reference (`docs/openclaw-config-reference-2026-03.json5`, pre-edit) that also used `azure-openai-responses` as a literal provider key — same conclusion, an earlier snapshot of a namespace that has since moved.
- `docs/audits/openclaw-oauth-only-revert-2026-07-12.md`: on 2026-07-12, David ordered an emergency revert away from the `azure-openai-responses` provider entirely (`models.providers.azure-openai-responses` removed; `agents.defaults.model.primary` changed `azure-openai-responses/gpt-5.5` → `openai-codex/gpt-5.4`). That audit explicitly scoped `config/editorial-model.yaml` OUT of the revert ("requiere cambio separado si editorial debe dejar Foundry") — it was never updated afterward, and provider naming has since moved again to today's `openai/*` keys.

Conclusion: `azure-openai-responses/gpt-5.5` was a literal provider/model id, not a permanent label — it stopped being live on 2026-07-12 and the namespace has moved since. The live config's `openai/gpt-5.5` is the correct, non-substituted target — same `gpt-5.5` model version the contract required, just addressed through the current provider namespace. ROLE.md's "Model preference" section was updated to state this, briefly, pointing back here for the full chain.

**Known unresolved gap (pre-existing, not created or fixed by this package):** `config/editorial-model.yaml` — the repo-side "source of truth" enforced by `scripts/editorial/editorial_model_guard.py` — still hard-codes `required_model_id: azure-openai-responses/gpt-5.5` with an exact-string check (`assert_editorial_model`/`verify_openclaw_agent_model`). This was already flagged as out of scope on 2026-07-12 and remains unfixed today. Two things keep this from blocking `rick-editorial`'s activation:
1. `rick-editorial` is not in that config's `editorial_agents` list (`rick-orchestrator`, `rick-linkedin-writer`, `rick-communication-director`, `rick-qa`, `main` are).
2. The guard's only live caller, `scripts/editorial/apply_publication_copy.py`, hardcodes its check to agent id `rick-communication-director` only — grepped the repo, no other call site exists.

But the underlying contract is stale for every agent it does cover — `rick-communication-director`'s own live model (`openai/gpt-5.6-sol`) already fails this exact-match check today, and `rick-qa/ROLE.md` (unedited by this package) still asserts the same stale literal `azure-openai-responses/gpt-5.5` this section just moved away from. This is a real, pre-existing, cross-file inconsistency this package surfaces via code-review but does not resolve — fixing `config/editorial-model.yaml` has a blast radius across 5 agents and was explicitly deferred as separate work in the 2026-07-12 audit; T4's mandate was activating `rick-editorial`, not reconciling that contract.

### Workspace materialization

`~/.openclaw/workspaces/rick-editorial/` did not exist. Materialized via:

```bash
python3 scripts/sync_openclaw_workspace_governance.py --execute --include-bootstrap
```

after first adding `"rick-editorial": Path("~/.openclaw/workspaces/rick-editorial").expanduser()` to that script's `WORKSPACES` dict (`scripts/sync_openclaw_workspace_governance.py`). Result: `BOOTSTRAP.md` (565 bytes), `HEARTBEAT.md` (469 bytes), `ROLE.md` (copied verbatim from the repo override, 16k+ bytes). No `AGENTS.md`/`SOUL.md`/`TOOLS.md`/`IDENTITY.md`/`USER.md` and no `umbral-agent-stack` repo symlink — deliberately, matching the newer-agent precedent (`rick-linkedin-writer`) rather than the older March-bootstrap agents. Confirmed by the Fase B smoke test's `systemPromptReport.injectedWorkspaceFiles`: only `HEARTBEAT.md` and `BOOTSTRAP.md` are present on disk; `AGENTS.md`/`SOUL.md`/`TOOLS.md`/`IDENTITY.md`/`USER.md` all show `missing: true`.

### Repo-side changes

- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` — status banner, "Tools and permissions" (documents the live grant, explicitly notes the worker-tool denial), "Model preference" (the reconciliation above), and "Activation conditions" (✅/⚠️ per-condition status, with explicit deltas on condition 3 — routing is via `rick-orchestrator.subagents.allowAgents`, not `config/teams.yaml` — and condition 4 — first cut is `CAND-OLA3-03` repair, not a new `CAND-001`).
- `scripts/sync_openclaw_workspace_governance.py` — added the `rick-editorial` workspace path.
- `docs/openclaw-config-reference-2026-03.json5` — added a reference `agents.list` entry for `rick-editorial`, with an inline comment flagging the model-naming era mismatch for future readers of that historical file.

## Fase B — smoke test (reachability, no Notion)

Live gateway invocation (not `--local`), no `--deliver`, no channel reply:

```bash
openclaw agent --agent rick-editorial --message "Confirmá que sos rick-editorial: decime tu id de agente, el primer párrafo de tu ROLE.md (el banner de status), y respondé exactamente con la palabra RICK_RUNTIME_REACHABLE en una línea aparte al final. No leas ni escribas Notion. No uses ninguna tool todavia, solo confirmá que estas vivo." --json
```

Result:

- `runId`: `af3fae2e-7be7-4ec3-bba6-1fa865563ab4`, `status: ok`.
- `agentMeta.sessionId`: `6f17ba3e-7d0c-4b81-acaa-e0378b28578a`, `sessionKey`: `agent:rick-editorial:main`, `provider: openai`, `model: gpt-5.5`, `agentHarnessId: codex`.
- `durationMs`: 38146. `usage.total`: 17055 tokens.
- The agent made **zero tool calls** this turn — the response is direct text. No Notion read, no Notion write, nothing touched during the smoke test, satisfying "no escribas Publicaciones en el smoke."
- `finalAssistantVisibleText` (verbatim): identifies itself as `rick-editorial`, states it will not read/write Notion or use tools, notes it can't quote ROLE.md's first paragraph verbatim without a file read (correctly declined to fabricate), and closes with the literal line `RICK_RUNTIME_REACHABLE`.
- `systemPromptReport.tools.entries` confirms the live grant matches the config: `sessions_*`, `web_search`/`web_fetch`, `umbral_notion_read_page`/`umbral_notion_read_database` (read-only), `umbral_research_web`, `umbral_llm_generate`, `umbral_linear_update_issue_status`, `umbral_provider_status`, `umbral_ping`, `memory_search`/`memory_get`. **No** `umbral_worker_enqueue`, `umbral_worker_run`, or any `umbral_notion_*` write tool appears in the injected tool list — independently confirms the deny list is live, not just declared in config.

**`RICK_RUNTIME_REACHABLE`** — confirmed via a real live gateway call, not docs-only evidence.

## Fase C — first cut (CAND-OLA3-03 repair)

### V1 alternativa production (real, not simulated)

`rick-editorial` was invoked live with the current `CAND-OLA3-03` claim/ángulo and told to research and verify — via its own `web_search`/`web_fetch`/`umbral_research_web` tools, not assumed — a concrete buildingSMART piece to replace the home-page `Fuente primaria`.

- `runId`: `b355c726-3ae6-455f-b133-17fb29681379`, same `sessionId` as the Fase B smoke (`6f17ba3e-...`).
- `toolSummary`: 16 tool calls across `web_search`, `umbral_research_web`, `web_fetch`; 0 failures.
- Result: a full V1 alternativa (`arco_narrativo`, `estructura_discurso`, `fuente_pieza_url`, `premisa`, etc.), citing `fuente_pieza_url: https://raw.githubusercontent.com/buildingSMART/IDS/development/Documentation/UserManual/README.md` — official buildingSMART IDS standard documentation, not the org's home/feed. Verified locally against the T3 guard: `is_home_or_feed_url(...)` → `False`.
- `Resultado revisión`: `Pendiente` — never set by the agent, per contract.

### rick-qa validation (real, not simulated)

`rick-qa` was invoked live with the full V1 payload and the contract's obligatory-field rules, asked for an explicit verdict.

- `runId`: `b22ad4b6-3225-4282-816d-fd4d16a4844b`, `sessionId`: `894f695b-a6b0-4d22-9391-4007c3649d58`, model `openai/gpt-5.6-sol`.
- `toolSummary`: 1 `bash` call (args redacted by the CLI itself), 0 failures — session-trail confirmed via `openclaw sessions tail --agent rick-qa --session-key agent:rick-qa:main`.
- Verdict: `APROBADO`. All four checks OK: `arco_narrativo`, `estructura_discurso`, `fuente_pieza_url_no_home_feed`, `alineacion_con_claim_angulo`.

**`V1_PASS`** — the system (rick-editorial + rick-qa), not Claude and not David, produced and validated a genuine V1 alternativa with a concrete, verified, non-home source URL.

### Registration gap — blocked before reaching HITL-1

Per ADR-011 and this package's own prohibition on Claude/MCP writing Notion directly, registering this V1 alternativa into the "Alternativas / Shortlist" DB must happen through the Worker. Grepped `worker/tasks/__init__.py` and every `worker/tasks/editorial_*.py` file: the only four editorial task handlers are

- `editorial.promote_shortlist_approval` (`worker/tasks/editorial_promote.py`) — promotes an ALREADY-`Aprobar`'d Shortlist row into Publicaciones; fetches by `shortlist_page_id`, does not create one.
- `editorial.dedupe_candidate_vs_backlog`, `editorial.capture_negative_example`, `editorial.inject_rrss_ready` — all also operate on an existing `shortlist_page_id`.

None of the four can create a brand-new row in the Shortlist/Alternativas DB from a payload. This is a more fundamental gap than the one this package anticipated (it expected to reach HITL-1 and possibly hit `BLOCKED_HUMAN_HITL1` there) — there is currently no worker-mediated path to even register a V1 alternativa for human review, for any candidate, not just this one.

Per this package's own contingency ("if there's no worker task... do not create a duplicate — write minimal CODE + tests... OR report BLOCKED with the identified gap"), this reports as **`BLOCKED_SHORTLIST_WRITE_TASK_MISSING`** rather than writing new Notion-write infrastructure under time pressure inside an already-large activation package. See the closing REPORT for the full evidence trail and the follow-up recommendation.

## Prohibitions still in effect

Unchanged from ROLE.md's Boundaries and Human gates sections: no publish, no `aprobado_contenido`, no `autorizar_publicacion`, no Notion writes (direct or via MCP), no cron/automation, no Notion AI for editorial decisions. Activation only grants read + payload-production capability; every write path still requires either the Worker (`ADR-011`) or an authorized human/operator action.

## References

- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` — the full role contract.
- `docs/ops/rick-communication-director-agent.md` — activation precedent this doc mirrors.
- `docs/ops/fuente-item-url-root-cause-2026-08-25.md` — the gap this activation closes.
- `docs/ops/hitl2-blog-pilot-2026-08-25.md` — still-open `CAND-OLA3-03` state prior to this package.
- `notion/schemas/alternativas-shortlist.schema.yaml` — V1 Shortlist schema.
- `worker/tasks/editorial_promote.py` — the only existing Notion-write path touching this data (Shortlist `Aprobar` → Publicaciones promotion; does not create new Shortlist rows).
