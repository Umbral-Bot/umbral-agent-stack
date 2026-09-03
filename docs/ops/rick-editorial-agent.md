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

Conclusion: `azure-openai-responses/gpt-5.5` was a literal provider/model id, not a permanent label — it stopped being live on 2026-07-12 and the namespace has moved since. The live config's `openai/gpt-5.5` is the correct, non-substituted target — same `gpt-5.5` model version the contract required, just addressed through the current provider namespace. ROLE.md's "Model preference" section stated this until T9, which moved that agent to `openai/gpt-5.6-sol`; the stale-guard consequence (aplicar copy exige `--skip-model-verify`) sigue documentada allí y acá.

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

### T5 follow-up — the gap is closed

`PKG-MACRO-P5-Q12-T5` implemented `editorial.create_shortlist_alternativa` (`worker/tasks/editorial_create_shortlist.py`), the task this section identified as missing: creates one V1 row in the Shortlist DB, always `Resultado revisión = Pendiente`, fail-closed on `fuente_pieza_url` via the same `is_home_or_feed_url` guard, idempotent by `alternativa_id`. HITL-1 is now actually reachable — David can act on a Shortlist row a worker call creates. See `notion/schemas/alternativas-shortlist.schema.yaml`'s `creation:` section for the implementation record and T5's own REPORT for the CODE/E2E outcome (`BLOCKED_SHORTLIST_WRITE_TASK_MISSING` → `NOTION_SHORTLIST_DS_ID` still absent from the live server env at T5 close).

### T6 — E2E live: the V1 row exists in Notion

David GO (2026-08-26): set `NOTION_SHORTLIST_DS_ID` on the live server (single line appended to `~/.config/openclaw/env`, backed up first; `NOTION_POLLER_ENABLE_PROMOTE` left untouched/unset), restarted `umbral-worker`, and ran the full E2E cycle for real via `POST /enqueue` (operator: Claude; `rick-editorial` never enqueues).

- **Dry-run**: `task_id 7c0fbfe5-8a4c-423a-8d49-11d30e24e292` — `ok:true, would_create:true`, preview showed `Resultado revisión: Pendiente`.
- **Live create**: `task_id 60d3c07e-4807-4333-bbc5-fd321626b8fc`, `2026-08-26T02:03:48Z` → `created:true`, `shortlist_page_id 3c85f443-fb5c-8118-97e8-c8f2d5f52ae7` (Notion `created_time: 2026-08-26T02:03:00Z` — same minute as the enqueue, consistent identity). Read back (read-only): `fuente_pieza_url` = the concrete IDS piece, `Resultado revisión = Pendiente`, `promovido_a = []`. Shortlist DB: 0 → 1 row.
- **Negative control**: `task_id 05534c22-79ad-4d22-969b-5e5c40f041f6`, home URL `https://www.buildingsmart.org/` → `fuente_pieza_url_is_home_or_feed`, no row created (DB stayed at 1).
- **Idempotency**: second live call, same `alternativa_id` → `task_id 35511953-fef6-4584-8fa7-310e15bbf258`, `already_exists:true`, same `shortlist_page_id` — no duplicate (DB stayed at 1).
- **Publicaciones untouched**: `CAND-OLA3-03` (`3a55f443-fb5c-81d1-b1f6-fe1b95dfd336`) re-read after all of the above — `Fuente primaria` is still the home page, `origen_alternativa` still `[]`. Nothing was promoted, approved, or archived. HITL-1 (`Resultado revisión = Aprobar` on the new Shortlist row) is David's decision, next, in Notion — not part of this package.

**`P5_Q12_SHORTLIST_CREATE_E2E_LIVE = Y`.**

### T7 — HITL-1 → promote live: the draft row exists in Publicaciones

David performed HITL-1 himself on 2026-08-26, setting `Resultado revisión = Aprobar` — observed at preflight with the Shortlist row's `last_edited_time` at `2026-08-26T14:50:00Z`, before this package wrote anything. (That timestamp is now `15:13:00Z`: the promote itself writes `promovido_a` back to the same row, so it no longer reads as David's edit time. The `Aprobar` value is his; the later bump is ours.) Preflight re-verified that live and independently before acting: `Aprobar`, `fuente_pieza_url` = the concrete IDS piece, `promovido_a` still empty, `is_home_or_feed_url(...) = False`. `NOTION_POLLER_ENABLE_PROMOTE` remained absent throughout — the promotion was a deliberate one-shot worker call by an authorized operator (Claude via `POST /enqueue`), never the poller and never `rick-editorial`.

- **Dry-run**: `task_id 5b6050be-7fce-4990-b11e-ea2ae803b2a0` → `would_promote:true`, preview showed `Estado: Borrador`, both gates `false`, `Fuente primaria` = the IDS piece. Zero writes.
- **Live promote**: `task_id 615d4ac2-9cb9-49cf-8fe8-059dd4420cfd`, `2026-08-26T15:13:27Z` → `created:true`, `publicacion_page_id 3c85f443-fb5c-818c-8464-ca2da6571a6c` (Notion `created_time 2026-08-26T15:13:00Z` — same minute, consistent identity).
- **New Publicaciones row, read back read-only**: `Estado = Borrador`; `Fuente primaria` = the concrete IDS piece (**not** the home page — the defect this whole Q12 thread started from is corrected in this new row); `origen_alternativa → 3c85f443-fb5c-8118-97e8-c8f2d5f52ae7`; `aprobado_contenido = false`; `autorizar_publicacion = false`; `Creado por sistema = true`; `Canal = blog`; `Tipo de contenido = blog_post`; `publication_id = shortlist-CAND-OLA3-03-SHORTLIST-V1`. All copy fields (`Copy Blog`/`LinkedIn`/`X`/`Newsletter`) empty, `Estado imagen` unset, `published_url` unset — **this package deliberately writes no copy**; V2 drafting is separate work.
- **Back-link**: the Shortlist row's `promovido_a` now points at the new Publicaciones page.
- **Idempotency**: second live enqueue of the same `shortlist_page_id` → `task_id 9f958e1a-99f8-445d-a1bd-d989d1a36d72`, `already_promoted:true`, same `publicacion_page_id`, no duplicate. Queried Publicaciones by `origen_alternativa` → exactly 1 linked row.
- **The old `CAND-OLA3-03` was NOT touched**: `3a55f443-fb5c-81d1-b1f6-fe1b95dfd336` re-read after everything — `Fuente primaria` still the home page, `origen_alternativa` still `[]`, `last_edited_time` still `2026-07-22T07:31:00Z` (a month before this work began, proving no write reached it). That legacy row remains unfixed and out of scope; the corrected source lives in the new row, not in it.

**`P5_Q12_PROMOTE_E2E_LIVE = Y`.** Still open downstream, by design: no copy written, no image, both human gates closed, nothing published.

### T8 — legacy archivada + copy V2 en la fila nueva

David (2026-08-26): "elimina la vieja y continuamos solo con la nueva". Interpretado como **archivar**, no borrar: `archived: true` es reversible (la página sigue recuperable por API y restaurable desde la papelera de Notion). No se ejecutó ningún delete permanente.

**Fase A — legacy archivada.** Preflight read-only confirmó la identidad de la fila antes de tocarla (`publication_id = CAND-OLA3-03`, `Fuente primaria` = home de buildingsmart.org, `last_edited 2026-07-22`, `archived: false`). Archivada vía worker `notion.update_page_properties` (`task_id 0274bb2c-66c9-4eee-87d4-8bded5f5f8a3`, solo `archived: true`, sin properties extra y sin `Estado = Descartado` — esa fila fue un intento del sistema con fuente mala, no una señal negativa de contenido). Verificado después: `archived: true`, `in_trash: true`, página aún recuperable. La fila nueva y la Shortlist quedaron intactas en esta fase.

**`P5_Q12_LEGACY_ARCHIVED = Y`** — page `3a55f443-fb5c-81d1-b1f6-fe1b95dfd336`.

**Fase B — copy V2, tres rondas.** El contenido lo produjo `rick-editorial` (sesión `a0b63f0d`) y lo validó `rick-qa` (sesión `1872bfcf`); Claude no redactó el artículo, solo operó el ciclo y aplicó el resultado.

1. **Ronda 1** se descartó por tres defectos. Solo uno de ellos lo atrapó `validate_publication_payload`: la frase de fail automático `"no es solo"` (único `ok=False`). Los otros dos los detectó una verificación mecánica aparte del operador, porque **el validador no los cubre**: una **URL corrupta** en el copy de empresa (`…/IDS/development/UserManual/README.md`, sin el segmento `/Documentation/`) — exactamente la clase de fallo de fuente que abrió este hilo Q12, y el validador no tiene ningún chequeo de URL — y longitudes fuera de objetivo (LinkedIn 1259 chars contra 500-700; X 308 contra 280), donde la cota de LinkedIn solo emite *warning* y la de X no existe en `channel-criteria-v1.yaml`. Las cotas mal puestas en el primer prompt fueron del operador, no del agente. **No confiar en `VALIDATION_OK` para URL ni para longitud de X.**
2. **Ronda 2** pasó el validador (`ok=True`, cero URLs alucinadas, sin em dash, cierre canónico presente) pero `rick-qa` la **RECHAZÓ** por trazabilidad de claims: la fuente no sostiene que openBIM sea una "infraestructura común", ni las afirmaciones de intercambio "sin reinterpretarlo" ni "sin perder interoperabilidad".
3. **Ronda 3** quitó esas tres formulaciones y las sustituyó por lo que el manual sí documenta (IDS como estándar buildingSMART para especificar y comprobar requisitos de información sobre modelos IFC; separación aplicabilidad/requisitos; herramientas de distintos proveedores), dejando openBIM como encuadre editorial explícito. `rick-qa` **APROBADO** (`run dca39706`), re-verificando la fuente con `web_fetch` real.

**Aplicación.** `scripts/editorial/apply_publication_copy.py --write-body` sobre `3c85f443-fb5c-818c-8464-ca2da6571a6c`. Dos incidentes documentados:

- **Guard de modelo stale** (el que T4 ya documentó y difirió): `MODEL_VERIFY_FAIL: 'openai/gpt-5.6-sol' != 'azure-openai-responses/gpt-5.5'`. Se usó `--skip-model-verify` con evidencia, tal como el pack autoriza. La *intención* del guard sí se cumple: el copy lo escribió `rick-editorial` corriendo en `gpt-5.5`, la versión que el contrato exige; lo stale es el namespace (`azure-openai-responses` se removió del config vivo el 2026-07-12) y el agente que chequea (`rick-communication-director`, que no es el autor).
- **Columna inexistente**: el primer intento live devolvió `HTTP 400 — "Copy LinkedIn empresa is not a property that exists"`. La DB Publicaciones live tiene `Copy Blog`, `Copy LinkedIn`, `Copy X`, `Copy Newsletter`, `trace_id` y `Comentarios revisión`, pero **no** `Copy LinkedIn empresa` (P2.3 existe en el tooling del repo, no en Notion). Crear columnas es decisión de David (ADR-007 §44), así que **no se creó**: el copy de empresa quedó producido y aprobado, preservado verbatim en `evals/editorial/shortlist-cand-ola3-03-shortlist-v1-final-copy.yaml` bajo una clave que el script ignora, para aplicarlo cuando exista la columna.

**Estado final de la fila nueva** (leído read-only): `Copy Blog` 2663 chars (394 palabras, sobre el ancla de 350-500+), `Copy LinkedIn` 684, `Copy X` 233, y 9 bloques de body (callout con marcador + divider + 7 párrafos, verificados uno a uno vía la API de bloques: sin cuerpo duplicado). `Fuente primaria` sigue siendo la pieza IDS concreta — la dejó el promote de T7, este pack no la escribe: el payload la lleva como metadato pero `build_properties` no la aplica. `Estado = Borrador`, `aprobado_contenido = false`, `autorizar_publicacion = false`, `gate_invalidado = false`, `Estado imagen` sin setear, `published_url` sin setear. La fila vieja sigue archivada y no recibió copy nueva.

**Correcciones de code-review aplicadas dentro del pack.** La primera aplicación live escribió en `Comentarios revisión` — campo que David lee — los ids de sesión/run de los agentes y sus nombres, violando la regla de `CLAUDE.md` ("no emitir telemetría, trace IDs, nombres de modelo en output de Notion"), y además atribuía el fallo del validador a la ronda equivocada. Ambos se corrigieron y se **re-aplicaron en vivo**: el campo quedó en prosa editorial accionable, sin telemetría. El re-apply confirmó la idempotencia del body (`BODY_SKIP_ALREADY_PRESENT`, 9 bloques, un solo marcador). Un tercer hallazgo del review — que el YAML habría corrompido saltos de párrafo por usar escalares de flujo — se **verificó y se descartó**: el YAML round-trips byte a byte y el salto simple entre `Fuente:` y el cierre canónico lo escribió el propio agente. Aun así se pasaron los `copy_*` a escalares literales (`|`) por consistencia con el ancla `cand-001-final-copy.yaml` y para que futuras ediciones a mano no dependan de reglas de plegado.

**`P5_Q12_V2_COPY_LIVE = Y`.** Sigue abierto por diseño: sin imagen (Magnific fuera de alcance), ambos gates humanos cerrados, nada publicado. El segundo OK de David es sobre estas redacciones.

### T9 — Sol + pasada de voz: por qué salió el meta y cómo se cerró

David rechazó el copy r3 por voz: el artículo hablaba de su propio proceso editorial. **Causa raíz** (4 puntos, con evidencia):

1. **El autor fue `rick-editorial`**, no el worker ni `apply_publication_copy.py`. El script solo transporta texto a Notion; no reescribe. Lo que se aplicó es literalmente lo que produjo el agente.
2. **La identidad del ROLE prima el registro de operador.** `ROLE.md` se abre con *"Rick Editorial is the editorial operations layer"*; el agente escribe desde esa identidad y, sin una barrera explícita, la arrastra al texto público.
3. **La jerga del operador se filtró desde el prompt.** En la ronda 3 de T8, el prompt de corrección le pidió literalmente mantener *"openBIM solo como encuadre editorial"* y aclarar *"que quede claro que es la lectura editorial, no una cita"*. El agente lo obedeció al pie de la letra y publicó *"La lectura editorial desde openBIM es concreta:"*. **El defecto se originó en la instrucción, no en el modelo.**
4. **La pasada de voz obligatoria no se ejecutó.** `ROLE.md` §"Editorial -> Communication Director" la exige cuando el candidato es copy público que depende de la voz de David. En T8 se fue directo de editorial a `rick-qa`, y `rick-qa` valida trazabilidad de fuente, no voz: por eso aprobó un texto correcto que sonaba a informe.

T9 cierra las cuatro con artefactos durables, no solo con un prompt de una sesión: la lista anti-meta quedó escrita en `ROLE.md` §Boundaries (para (2) y (3), de modo que no dependa de que cada prompt se acuerde de repetirla), y la pasada de voz pasó de "Hand off when…" a **obligatoria y con orden vinculante** en `ROLE.md` §"Editorial -> Communication Director" (para (4)). En el artículo la lista anti-meta nunca aparece; solo gobierna la instrucción al agente.

**Modelo.** `rick-editorial` pasó a `openai/gpt-5.6-sol` (ChatGPT Sol, provider `openai`/OAuth; sin Azure, sin Gemini en fallbacks). Backup del config antes de tocarlo; diff redactado verificado: **un solo agente cambió**, el resto del roster intacto. `openclaw config validate` OK. El modelo aplicó **en caliente, sin reiniciar el gateway** (mismo comportamiento que T4). Smoke: `provider openai`, `model gpt-5.6-sol`, `fallbackUsed: false`, `RICK_SOL_REACHABLE`.

**Sobre "esfuerzo alto o muy alto", con precisión.** No es configurable en este modelo, pero la formulación inicial de esta nota era demasiado absoluta y el code-review la corrigió. Lo exacto: un **flag explícito** lo rechaza el gateway (`Thinking level "xhigh" is not supported for openai/gpt-5.6-sol. Use one of: off.`, y `high` tampoco existe), mientras que un **`thinkingDefault` en el config sí se tolera**: se ignora en silencio y la request sale con `thinking: off` igual. Evidencia de que tolerarlo es lo normal en este stack: `main`, `rick-orchestrator`, `rick-qa`, `rick-communication-director` y `rick-linkedin-writer` corren Sol con `thinkingDefault: xhigh` hoy, y dos de ellos participaron en la cadena que produjo r4. Se dejó `off` en este agente porque describe lo que el runtime hace de verdad; el efecto es idéntico en ambos casos. **No se tocó a los otros cinco agentes**: la evidencia se obtuvo sobre uno solo y mass-editar el roster por una prueba puntual sería injustificado. **Queda una decisión abierta para David:** Sol sin dial de razonamiento vs. `gpt-5.5` con `xhigh`, que sí lo soporta.

**Copy r4 — cadena de tres pasos, en orden.** `rick-editorial` (Sol) produjo → `rick-communication-director` pasó voz y **corrigió** (`VEREDICTO_VOZ: CORREGIDO`: marcó *"abordar esa definición"*, *"orden operativo"*, *"aporta el contexto para esta conversación"* y reescribió el cuerpo para que hable desde lo que el equipo pide, revisa y comprueba) → `rick-qa` **APROBADO**, re-verificando la fuente con `web_fetch`. Ninguno de los tres pasos se salteó.

**Reemplazo del body sin duplicar marcador.** El marcador de `--write-body` embebe el `trace_id`, así que cambiar `r3`→`r4` y re-correr **habría apilado un segundo cuerpo** (12 bloques nuevos sobre 9 viejos). Se enumeraron los 9 bloques existentes, se verificó que **todos** pertenecían al body r3 (callout con marcador + divider + 7 párrafos, nada ajeno), se archivaron uno a uno vía API, se confirmó la página en 0 bloques, y recién entonces se aplicó r4. Resultado: 12 bloques, **un solo marcador**.

**Estado final** (read-back independiente): `Copy Blog` 2785 chars (413 palabras), `Copy LinkedIn` 660, `Copy X` 246, 12 bloques de body con un marcador. `Fuente primaria` sigue siendo la pieza IDS (la dejó T7; este pack no la escribe). `Estado = Borrador`, los tres gates en `false`, `Estado imagen` y `published_url` sin setear. Verificado sobre propiedades **y** body: cero apariciones de "lectura editorial", "encuadre editorial", "metodológica" o "el problema rara vez aparece"; todas las URLs live byte-idénticas a la pieza IDS (el validador no chequea URLs, se chequeó aparte).

**`P5_Q12_EDITORIAL_MODEL_SOL = Y`** · **`P5_Q12_V2_COPY_R4_LIVE = Y`**. Sigue abierto por diseño: sin imagen, gates cerrados, nada publicado.

### T10 — brief visual escrito, generación BLOCKED por env

David dio GO para pasar a imagen (5 variantes, elige después, nadie publica). El brief se escribió; la generación **no pudo correr** por falta de credencial, y eso quedó como BLOCKED honesto en vez de forzarse.

**Preflight** (read-only): fila en `Borrador`, tres gates en `false`, `Fuente primaria` = pieza IDS, `Copy Blog` r4 presente (2785 chars), y todos los campos de imagen vacíos — `Estado imagen` sin setear, es decir elegible. `magnific.generate_variants` cargada en el worker. `NOTION_POLLER_ENABLE_MAGNIFIC` y `NOTION_POLLER_ENABLE_PROMOTE` confirmados ausentes (chequeo por conteo, sin dump de env).

**Fase 2 — Visual brief.** Lo produjo `rick-editorial` (Sol), no Claude. Se le pasó explícitamente que **no repitiera** el sufijo anti-slop de ADR-006, porque `_build_prompt` lo concatena solo cuando el prompt sale del `Visual brief` (`worker/tasks/magnific.py:119-129`): duplicarlo habría inflado el prompt sin aportar nada. **Ojo, no es incondicional:** si se pasa un `prompt` explícito por input, `_build_prompt` retorna en la primera línea y **se saltea el sufijo entero** — quien override-ee el prompt para retocar wording tiene que incluir el anti-slop a mano o pierde la guarda de ADR-006. El brief describe una escena AECO concreta (oficina técnica junto a obra, monitor con modelo BIM seccionado, tres paneles del mismo elemento con propiedades completas / nombres distintos / campos vacíos), figura humana solo parcial y de espaldas, sin marcas de terceros, `sin texto legible`, 4:3 con zona de respiro. Verificado contra las reglas antes de escribirlo. Se escribió **solo** la propiedad `Visual brief` sobre la fila `3c85f443-fb5c-818c-8464-ca2da6571a6c` (Publicaciones; no confundir con la Shortlist `3c85f443-fb5c-8118-97e8-c8f2d5f52ae7`, que difiere en un segmento del medio) vía worker, `task_id fdbd9f20-5bab-479a-aa0e-8c7b6ca85162`; no se tocó copy ni gates.

**Fase 3 — dry-run.** `task_id 7c236bf3-8a6e-4ac0-8896-15e6f14567b4` → `would_generate: true`, `count: 5`, `aspect_ratio classic_4_3`, `resolution 2k`, `model realism`, y el prompt derivado = brief + sufijo anti-slop. Cero llamadas a Magnific, cero escrituras.

**Fase 3 — live: BLOCKED.** `MAGNIFIC_API_KEY` está **ausente** del server (`grep -c '^MAGNIFIC_API_KEY=' ~/.config/openclaw/env` → `0`). No se seteó: no había GO puntual para esa credencial, y el pack lo prohíbe explícitamente. Tampoco se usó el MCP de Magnific como bypass — las URLs a Notion las escribe el Worker (ADR-011) — ni se encendió el poller.

Se corrió igual el live para dejar evidencia dura: `task_id e8417dde-1993-4dba-af81-1218d17df48a`, `2026-08-26T20:39:57Z` → `ok: false`, `error: MAGNIFIC_API_KEY not configured on server`. **La task falla cerrada antes de cualquier escritura** (`_magnific_headers()` levanta antes del write interino de `Generando`), y se verificó leyendo la página después: `Estado imagen` sigue vacío — **no** quedó en `Error` ni `Generando` —, `imagen_error` vacío, las cinco `imagen_alt_*_url` en `None`, `Selección imagen` y `Visual asset URL` sin setear, gates en `false` y copy r4 intacto. Esa garantía no es una anécdota de esta corrida: la fija el test de regresión `tests/test_magnific.py::test_no_api_key_configured_blocks_before_any_write`, que afirma `update_page_properties.assert_not_called()`. Si alguien hoistea el write interino por encima del chequeo de credencial, ese test lo atrapa.

La fila queda limpia y elegible para reintentar, **pero setear la credencial no alcanza por sí solo**: `worker/config.py:81` toma `MAGNIFIC_API_KEY` como snapshot a nivel de módulo, en el import, y el handler lee `config.MAGNIFIC_API_KEY` (no `os.environ`) en cada llamada. Agregar la línea al env **sin reiniciar `umbral-worker` devuelve exactamente el mismo error**, y es fácil leerlo como "la key está mal" y volver a editar el env en vez de reiniciar. Es el mismo procedimiento que ya hizo falta en T6 para `NOTION_SHORTLIST_DS_ID`. Orden correcto para el reintento: (1) GO de David para la credencial, (2) agregar la línea al env, (3) `systemctl --user restart umbral-worker`, (4) confirmar en `/health`, (5) recién entonces re-enqueue con `dry_run:false`.

**`P5_Q12_VISUAL_VARIANTS_LIVE = BLOCKED`** — capa **env/config**, variable exacta `MAGNIFIC_API_KEY`. Todo lo demás del camino quedó listo: brief escrito, prompt derivado verificado, task cargada, fila elegible. HITL-2 (elegir imagen, marcar casillas, Telegram) no es este pack.

### T11 — búsqueda de la credencial: no está la API key REST (y el OAuth del MCP tampoco quedó completado)

David indicó que la `MAGNIFIC_API_KEY` ya estaba en la VPS y pidió engancharla al worker. **Se buscó a fondo y no está.** Lo que sí está en la VPS es una credencial de Magnific, pero de **otro tipo**, y no sirve para este camino.

**Dónde se buscó** (por NOMBRE de variable, nunca por patrón de token, y sin imprimir valores):

- Los tres `EnvironmentFile` que carga `umbral-worker` según systemd: `~/.config/openclaw/env`, `~/.config/openclaw/copilot-cli.env`, `~/.config/openclaw/copilot-cli-secrets.env` → ninguno tiene la línea.
- `~/.openclaw/.env`, `~/.env`, `<repo>/.env`, `<repo>/.env.*`, `~/.config/openclaw/backups/env.*`, `~/.config/openclaw/*.env`.
- `.env.example` y `openclaw/env.template` del repo: en ambos la línea está **comentada** y con marcador de plantilla — `CHANGE_ME_MAGNIFIC_API_KEY` en el primero, `xxx` en el segundo. Plantilla, no credencial.
- Barrido de `/home/rick` y `/etc` (74.165 archivos, excluyendo `.git`, `node_modules`, `.venv`, caches y transcripciones) buscando una asignación real `MAGNIFIC_API_KEY=<valor>`: **cero resultados**.
- `~/.openclaw/openclaw.json`: no menciona el nombre de la variable.

**Lo que sí existe, y por qué no aplica.** `openclaw.json` tiene un server MCP `magnific` cuyo campo `auth` es literalmente la palabra `oauth` (5 caracteres), no una key, y sus `args` no contienen nada con forma de secreto. Y el camino MCP tampoco está realmente disponible: bajo `~/.mcp-auth/` hay **20 registros de cliente** (`d26f403b*_client_info.json`) para ese server y **cero** `*_tokens.json` — de ningún server. Es decir, existe un *registro de cliente* OAuth, no una credencial de usuario utilizable: el OAuth nunca se completó. Así que el MCP no era una alternativa que se descartó por ADR-011 solamente; tampoco habría funcionado. Eso concuerda con `docs/ops/magnific-editorial-setup-2026-06-06.md`, que lo dice explícito en su encabezado: *"Magnific MCP … (OAuth cuenta Magnific; **sin API key en MCP**)"*, y trata la REST key como un camino aparte: *"Fallback producción (sin MCP OAuth): API key REST en `~/.config/openclaw/env` como `MAGNIFIC_API_KEY` + script Worker."*.

Son dos credenciales distintas para dos caminos distintos: el worker (`worker/tasks/magnific.py`) manda el header `x-magnific-api-key`, que es REST y **no** se deriva de un token OAuth de MCP. Usar el MCP para generar sería justamente el bypass del Worker que ADR-011 prohíbe (las URLs a Notion las escribe el Worker), así que no se hizo.

**No se tocó nada.** Sin key instalable, no se modificó `~/.config/openclaw/env`, no se reinició el worker, no se corrió generación, no se encendió ningún poller. La fila `3c85f443-fb5c-818c-8464-ca2da6571a6c` se releyó al cierre para no darlo por sentado: `last_edited_time` sigue en `2026-08-26T20:39:00Z`, exactamente donde la dejó T10 — `Visual brief` presente (464 chars), `Estado imagen` vacío (elegible), `imagen_error` vacío, las cinco `imagen_alt_*_url` en `None`, `Estado = Borrador`, los tres gates en `false`, `Fuente primaria` y copy r4 (`trace_id …-r4`) intactos.

**Observación aparte, preexistente y fuera de alcance de este pack:** ese mismo directorio acumula **1.442** archivos `*_code_verifier_*.txt` huérfanos repartidos en 21 carpetas `mcp-remote-*`, **117 de ellos escritos hoy**, con cero tokens completados nunca. Eso apunta a un reintento de OAuth que falla en bucle y crece sin límite. No se tocó acá — no es la credencial que este pack buscaba y arreglarlo es trabajo aparte.

**`P5_Q12_VISUAL_VARIANTS_LIVE = BLOCKED`** (sin cambio respecto de T10) — capa **env/config**. Para desbloquear hace falta que David consiga la API key REST desde su cuenta Magnific y la instale; **no se le pidió pegarla al chat**. Para desbloquear se sigue **el mismo orden de 5 pasos ya escrito en T10 más arriba**, que empieza por el GO puntual de David para la credencial y **no** se repite acá para que no diverjan. Los dos puntos que más se prestan a confusión: la línea debe llevar un valor real (`MAGNIFIC_API_KEY=<valor>`; vacía falla igual, el handler hace `(… or "").strip()` y levanta), y **sin reiniciar el worker** `worker/config.py` sigue con `None` y devuelve el error idéntico, que se lee como "la key está mal".

### T12 — las 5 variantes existen

David consiguió la API key REST, la puso él mismo en `~/.config/openclaw/env` y reinició el worker. Verificado antes de tocar nada, sin leer el valor: la asignación existe (`len=34`, no placeholder), y el worker vivo es **PID 1648574**, arrancado a las `11:09:42 -04`, **~9 segundos después** del mtime del env (`11:09:33 -04`; ambos hora local, el resto de los timestamps de esta sección son UTC) — o sea que el snapshot de `worker/config.py` ya incluye la credencial y **no hizo falta reiniciar de nuevo**. `NOTION_POLLER_ENABLE_MAGNIFIC` sigue **ausente** (0 asignaciones, chequeo por conteo).

Preflight de la fila: `Borrador`, tres gates en `false`, `Estado imagen` vacío (elegible), `Visual brief` de T10 presente (464 chars), copy r4 intacto.

**Dry-run** (`task_id c4b5aa22-0c67-498b-98e8-efb302f158ad`): `would_generate: true`, `count 5`, `classic_4_3` / `2k` / `realism`, prompt de 795 chars terminando en el sufijo anti-slop — confirmando que salió del `Visual brief` y **no** se pisó con un `prompt` explícito, que habría salteado el sufijo (la trampa documentada en T10). Cero créditos.

**Live** (`task_id be7924a1-eff4-4733-8e32-23e0e5573d61`, `2026-08-27T15:14:09Z` → `15:16:07Z`, **117,5 s**): `generated: 5/5`, `error: None`, `Estado imagen = Listo para selección`.

**Read-back independiente**: `imagen_alt_1_url` … `imagen_alt_5_url` las cinco pobladas (CDN de Magnific/Freepik), `imagen_cantidad = 5`, `imagen_generada_at = 2026-08-27`, `imagen_error` vacío, `last_edited 15:16` — consistente con el `task_id` y su timestamp. Sin tocar lo que es de David: `Selección imagen` **sin setear**, `Visual asset URL` **sin setear**. Intactos: `Estado = Borrador`, los tres gates en `false`, `Fuente primaria` (pieza IDS), `Copy Blog` r4 (2785 chars, `trace_id …-r4`), `Visual brief`, `published_url` sin setear.

**⚠️ Las 5 URLs son links firmados que caducan en ~1 hora — el hallazgo más importante de T12.**
El handler guarda la URL del CDN **tal cual, sin descargar ni re-hostear** (`worker/tasks/magnific.py:346`), y esas URLs traen `?token=exp=<epoch>~hmac=…`. Medido sobre la fila: las cinco expiran entre `16:14:35Z` y `16:16:05Z`, o sea ~60 min después de generarlas. La caducidad **se aplica de verdad**: `HEAD` sobre la URL vigente devuelve `200 image/png`; la misma URL con un `exp` pasado devuelve `403`.

Eso choca de frente con HITL-2, que es una acción humana en escala de horas o días: si David abre la fila mañana, las cinco vistas previas van a ser `403` mientras `Estado imagen` sigue diciendo `Listo para selección`. Y si elige antes de notarlo, `scripts/editorial/sync_visual_asset_from_selection.py` copia `imagen_alt_N_url` **verbatim** a `Visual asset URL`, con lo cual el link muerto pasa a ser el asset de portada de la publicación.

Segunda trampa encadenada: con `Estado imagen = Listo para selección` la fila **ya no es elegible** para regenerar — ese valor está en `_ALREADY_DONE_STATES` (`worker/tasks/magnific.py:75`), así que un reintento ingenuo se saltea en silencio. Recuperarse exige resetear el estado a mano y volver a gastar créditos.

Nada de esto está documentado en `magnific-editorial-setup-2026-06-06.md` ni en `editorial-magnific-p22-poller-2026-07-23.md`. **No se arregló acá** (re-hostear las imágenes es infraestructura nueva y necesita su propio GO); queda levantado para decidir.

**`P5_Q12_VISUAL_VARIANTS_LIVE = Y`** — las cinco variantes se generaron y quedaron escritas por el Worker, que es lo que el gate pedía. Con la salvedad de arriba: el artefacto es perecedero. Lo que sigue abierto es HITL-2 y es de David: elegir Alt 1–5, marcar las casillas y la confirmación por Telegram. Nada de eso se tocó acá, y el post no está publicado.



### T13 — arco_narrativo: paréntesis de estrategia, no andamiaje de proceso (2026-09-03)

David aprobó el 2026-09-03 el formato de `arco_narrativo` (PKG-EDITORIAL-V1-ARCO-PARENS-SOT-1): el CUERPO del campo es la historia de la pieza; las alusiones a estrategia interna (de qué parte, qué tensiona, a dónde llega) van entre paréntesis **después** de la frase que etiquetan — `(punto de partida: …)`, `(tensión: …)`, `(cierre: …)`. El `Right` anterior de `ROLE.md` enseñaba justo el andamiaje que ahora queda prohibido (`Parte de que RICS… Tensiona la distancia… Llega a que los equipos BIM…`), y por eso `CAND-IA-FLUJOS-AEC-SHORTLIST-V1` (2026-09-03) pasó `rick-qa` con ese mismo andamiaje sin etiquetas y el arco seguía ilegible como historia. Se actualizó `ROLE.md` (`rick-editorial` y `rick-qa`), el contrato §3, la plantilla de payload, `shortlist-format.md`, `SKILL.md` de `editorial-source-curation` y `docs/67` §5.1 con el mismo criterio. No se tocó `cadena_tesis` (ahí las etiquetas son el formato exigido). El rewrite en vivo de esa misma fila de Shortlist queda para el siguiente paquete, post-merge.

## Prohibitions still in effect

Unchanged from ROLE.md's Boundaries and Human gates sections: no publish, no `aprobado_contenido`, no `autorizar_publicacion`, no Notion writes (direct or via MCP), no cron/automation, no Notion AI for editorial decisions. Activation only grants read + payload-production capability; every write path still requires either the Worker (`ADR-011`) or an authorized human/operator action.

## References

- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md` — the full role contract.
- `docs/ops/rick-communication-director-agent.md` — activation precedent this doc mirrors.
- `docs/ops/fuente-item-url-root-cause-2026-08-25.md` — the gap this activation closes.
- `docs/ops/hitl2-blog-pilot-2026-08-25.md` — still-open `CAND-OLA3-03` state prior to this package.
- `notion/schemas/alternativas-shortlist.schema.yaml` — V1 Shortlist schema.
- `worker/tasks/editorial_promote.py` — the only existing Notion-write path touching this data (Shortlist `Aprobar` → Publicaciones promotion; does not create new Shortlist rows).
