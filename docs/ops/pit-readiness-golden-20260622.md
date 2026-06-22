# PIT readiness — golden tournament #3 GO/NO-GO (P1–P6 audit)

- **Date (UTC):** 2026-06-22
- **Surface:** Copilot Windows (repo) + read-only SSH `umbral-vps`.
- **Scope:** read-only audit + GO/NO-GO dictamen. **No tournament spawned, no gates
  opened (L3/L4/nft), no worker restart, no secrets.**
- **main top:** `dbcab9e5` — includes #481, #482, #483, #484, #485.
- **VPS repo HEAD:** `dbcab9e` (= main), worker `health=200`, `worker_pid=2209789`
  (P4 loaded in runtime).

This is the readiness gate before any golden tournament. The companion spec
template is `examples/pit/pit_spec.golden-broker-v1.yaml` (validated, **not**
executed).

---

## GO/NO-GO matrix

| Gate / Paquete | Veredicto histórico | Evidencia | Estado para torneo |
|---|---|---|---|
| **P1 infra** | partial | docker network `copilot-egress` **PRESENT**; sandbox image `umbral-sandbox-copilot-cli` **ABSENT** (only `redis:7-alpine`, `diygod/rsshub` on host) | **GO (dry)** · **NO-GO (broker-real)** — image must be rebuilt |
| **P2 dry** | OK | `pit-p2a-dry-run-probe-20260620` | **GO** |
| **P2 real** | `P2_PROBE_REAL_OK` | `pit-p2c-retry-egress-execute-read-probe-20260621-run3/VERDICT.txt` (`decision=completed`, `executed=true`) | **GO capability** — but proven with image tag `6940cf0f274d` now absent (see P1) |
| **P3 slugs** | `P3_SLUGS_OK` | `pit-p3-vps-copilot-slugs-audit-20260621`; `config/tool_policy.yaml` allowed_models (slugs) | **GO** |
| **P3 policy** | merged #482 | main `config/tool_policy.yaml` L49 `default_model: gpt-5.5`, L50 `force_default_model: false`, L52–62 `model_aliases`, L67–76 `allowed_models` | **GO** |
| **P4 worker** | `P4_RUNTIME_LOAD_OK` | `pit-post-p4-runtime-load-20260622` (restart `2149363→2209789`, dry `execute_flag_off_dry_run`, `max→xhigh`, audit `pit_id/lane_id/iteration`) | **GO** |
| **P5 skill** | merged #484 | `openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md` + `scripts/pit/pit_spec_validate.py` + `examples/pit/pit_spec.v2.yaml`; `pit-p5-vps-validate-20260622` example pass | **GO** |
| **P6 ledger** | merged #485 | `scripts/pit/pit_collect_tokens.py`; vault ledgers for `pit-umbral-bim2-sharepoint-acc` (6,617,544), `pit-salud-mental-pilot` (5,554,534), `pit-runtime-contract-smoke` (copilot_cli 1) | **GO** |
| **Gates runtime** | L3 false, L4 false, nft absent | scan: `RICK_COPILOT_CLI_EXECUTE=false`, `egress.activated=false`, `nft inet copilot_egress=ABSENT` | **GO (expected closed)** — dry needs them closed; broker-real needs David to open for a window |
| **P7 secrets scope** | contract present | `secrets_scope` enforced by validator (deny must contain `WORKER_TOKEN`, logical UPPER_SNAKE names only); lanes receive no secrets in sandbox | **DEFER** — contract enforced at spec level; no runtime secret-injection path to lanes |
| **P8 MC UX** | not assessed | optional pre-tournament | **DEFER** (not a blocker) |

### Golden spec validation (objective spec)

`python scripts/pit/pit_spec_validate.py examples/pit/pit_spec.golden-broker-v1.yaml`
→ **`status: pass` (exit 0)**: 3 lanes (`gpt-5.5/high`, `claude-opus-4.7/xhigh`,
`gpt-5.4-mini/medium`), `budget_usd_total=150.0`, `broker_contract.required_task=copilot_cli.run`,
`forbid_direct_llm_repo_analysis=true`, `secrets_scope.deny` ⊇ `WORKER_TOKEN`.

---

## Dictamen

- **`PIT_TOURNAMENT_DRY_RUN_GO`** ✅
  Rick may spawn the golden tournament in **dry-run** mode (no real execution).
  Every minimum is met: P2–P6 GO, validator passes on the golden spec, collector
  operational, worker `health=200`, gates **closed** (dry-run resolves to
  `execute_flag_off_dry_run`, `would_run=false` — it never touches Docker, so the
  absent sandbox image is irrelevant for dry).

- **`PIT_TOURNAMENT_BROKER_REAL_NO_GO`** ⛔ (HOLD)
  Broker-real does **not** meet the minimum criteria, because **P1 infra is not GO**:
  the sandbox image `umbral-sandbox-copilot-cli` is **absent** on the VPS (pruned
  since P2c run3). Real execution (`_build_docker_argv`) targets
  `os.environ.get("COPILOT_CLI_SANDBOX_IMAGE", "umbral-sandbox-copilot-cli")`, and
  `COPILOT_CLI_SANDBOX_IMAGE` is currently **commented out** in
  `~/.config/openclaw/copilot-cli.env`. Without the image, a real run would fail at
  `docker run`.

### Minimum criteria for broker-real (and current status)

| Criterio | Estado |
|---|---|
| P1–P6 GO | ❌ (P1 image absent) |
| P2_PROBE_REAL_OK vigente | ⚠️ verdict vigente, image artifact gone |
| P5 validator pass on objective spec | ✅ |
| token ledger collector operational | ✅ |
| worker health 200 | ✅ |

### What David must authorize/verify before broker-real (verbatim)

1. **Rebuild sandbox image on VPS** (deterministic tag):
   `bash worker/sandbox/refresh-copilot-cli.sh` → produces
   `umbral-sandbox-copilot-cli:<sha256-12>`; then pin it by uncommenting
   `COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:<tag>` (L20) in
   `~/.config/openclaw/copilot-cli.env`.
2. **Open the execution window explicitly** (David GO, bounded): L3
   `RICK_COPILOT_CLI_EXECUTE=true`, L4 `egress.activated=true`, and the `nft inet
   copilot_egress` table — for the tournament window only, closed afterward.

> **Recommendation:** `P9_DRY_GO` (dry-run golden tournament authorized) +
> `P9_BROKER_REAL_HOLD` (broker-real on hold pending sandbox-image rebuild and an
> explicit execute+egress window from David).

---

## Notes (mandatory)

- **Historical v1 tournaments carry no `pit_id` in the Copilot CLI audit** — this is
  expected. `pit-umbral-bim2-sharepoint-acc` and `pit-salud-mental-pilot` predate P4,
  so their `copilot_cli` audit has no metadata correlation; only `pit-runtime-contract-smoke`
  (post-P4 probe) shows `pit_id/lane_id` in audit JSONL.
- **A new broker-real tournament MUST emit audit with `pit_id/lane_id`** (post-P4
  contract). The P6 token-ledger collector then correlates copilot_cli calls per lane.
- The two real vault tournaments validate under the **v1 product** path of
  `pit_spec_validate.py`; the golden template here is **v2 broker** (code/repo-analysis).
- This audit changed **no runtime state**: gates stayed closed, worker was not
  restarted, no secrets printed, no tournament spawned.
