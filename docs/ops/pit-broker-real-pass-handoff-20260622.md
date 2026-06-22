# PIT broker-real PASS — final handoff (P1–P9 closure)

- **Date (UTC):** 2026-06-22
- **Surface:** Copilot Windows (repo) + read-only SSH `umbral-vps`.
- **Outcome:** **`PIT_RUN_PASS_BROKER_REAL` REACHED** — multi-lane broker-real
  validated end-to-end via the worker (`copilot_cli.run`), 3 lanes, exit 0, zero
  egress drops, gates rolled back byte-identical.
- **main top at closure:** `c7b15c52` — includes #481–#486.
- **Sandbox image:** `umbral-sandbox-copilot-cli:6940cf0f274d` (copilot CLI 1.0.36),
  pinned in `~/.config/openclaw/copilot-cli.env` (P1b).
- **Broker token:** UmbralBIM, fp `a19dbad9a470` (`/user=200`), never printed.

This document closes the broker-real lane. Gates are **closed by default** and only
opened inside an explicit, bounded, David-authorized window with guaranteed rollback.

---

## 1. Final verdicts P1–P9

| Paquete | Veredicto final | Evidencia (Windows `~/.coord-ag-evidence/…`) |
|---|---|---|
| **P1 infra (image)** | **OK** (post-P1b) | `pit-p1b-sandbox-rebuild-20260622` — rebuilt + pinned `umbral-sandbox-copilot-cli:6940cf0f274d`, smoke offline+bridge OK, gates stayed closed |
| **P2 dry** | `P2_DRY_OK` | `pit-p2a-dry-run-probe-20260620` |
| **P2 real** | `P2_PROBE_REAL_OK` | `pit-p2c-retry-egress-execute-read-probe-20260621-run3` (`decision=completed`, `executed=true`) |
| **P3 slugs+policy** | merged #482 | `config/tool_policy.yaml`: slugs in `allowed_models`, display→slug `model_aliases`, `force_default_model: false` |
| **P4 worker contract** | merged #483 · `P4_RUNTIME_LOAD_OK` | `pit-post-p4-runtime-load-20260622` — lane metadata (`pit_id/lane_id/iteration`) in audit, `reasoning_effort` incl. `xhigh`, `max→xhigh` alias |
| **P5 broker-only skill** | merged #484 | `scripts/pit/pit_spec_validate.py` + SKILL.md; `pit-p5-vps-validate-20260622` |
| **P6 token ledger** | merged #485 | `scripts/pit/pit_collect_tokens.py`; `pit-p6-vps-validate-20260622` |
| **Readiness gate + golden spec** | merged #486 | `docs/ops/pit-readiness-golden-20260622.md` + `examples/pit/pit_spec.golden-broker-v1.yaml` (validator `pass`) |
| **P9 dry smoke** | `P9_DRY_SMOKE_OK` | `pit-p9-dry-smoke-20260622` — 3 lanes `execute_flag_off_dry_run`, drop 0 |
| **P9 broker mini** | `P9_BROKER_MINI_OK` | `pit-p9-broker-mini-smoke-20260622` — 1 lane real, exit 0, DROP_DELTA 0, rollback byte-identical |
| **P9 broker golden** | **`P9_BROKER_GOLDEN_OK`** | `pit-p9-broker-golden-3lanes-20260622` (31 files) — 3 lanes real, exit 0, DROP_DELTA 0, rollback byte-identical |

### P9 golden — per-lane result (one real POST each, no retries)

| lane | model (req → resolved) | effort (req → eff) | iter | http | executed | decision | exit | egress | drop_Δ |
|---|---|---|---|---|---|---|---|---|---|
| lane-foundry-tools | gpt-5.5 → gpt-5.5 | high → high | 1 | 200 | true | completed | 0 | true | 0 |
| lane-codex-depth | "Claude Opus 4.7" → claude-opus-4.7 | max → xhigh | 2 | 200 | true | completed | 0 | true | 0 |
| lane-cost-mini | gpt-5.4-mini → gpt-5.4-mini | medium → medium | 3 | 200 | true | completed | 0 | true | 0 |

All three audit JSONL carry `pit_id=pit-golden-broker-v1` + matching `lane_id`
(event `F8A`). Totals: **DROP_DELTA=0, KERNEL_DELTA=0**.

---

## 2. Evidence (Windows paths)

All under `C:\Users\david\.coord-ag-evidence\`:

- `pit-p1b-sandbox-rebuild-20260622\` — image rebuild + pin + smoke + gates closed
- `pit-p9-dry-smoke-20260622\` — 3-lane dry baseline + validated golden spec copy
- `pit-p9-broker-mini-smoke-20260622\` — single real run + rollback pattern proof
- `pit-p9-broker-golden-3lanes-20260622\` — **golden tournament** (31 files):
  `00-authorization.txt`, `00-gates-pre.txt`, `01-resolver-summary.txt`,
  `03-response-lane-*.json`, `03-drop-delta.txt`, `04-gates-post.txt`,
  `05-audit-summary.txt`, `05-ledger-lanes.txt`, `06-secret-scan.txt` (CLEAN),
  `REPORT.md`, `VERDICT.txt`, `run-window-golden.sh`
- `pit-post-p4-runtime-load-20260622\`, `pit-p5-vps-validate-20260622\`,
  `pit-p6-vps-validate-20260622\` — package validations

Ledger (VPS): `~/umbral-pit-vault/pit/pit-golden-broker-v1/metrics/token_ledger.yaml`
— `lanes=3`, `openclaw_total=0` (no Rick spawn), per-lane real ≥ 1, exit_codes `{0}`.

---

## 3. Operational recipe — broker-real tournament

> Run only inside a bounded, David-authorized window. Every step has a guaranteed
> rollback (`trap rollback EXIT INT TERM HUP`).

### 3.1 Preflight checklist (P5)

1. `git -C ~/umbral-agent-stack pull --ff-only origin main`; confirm HEAD.
2. Worker `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8088/health` == `200`.
3. Gates **closed**: `RICK_COPILOT_CLI_EXECUTE=false`, `tool_policy.yaml` L240
   `activated: false`, `nft list table inet copilot_egress` == ABSENT.
4. Sandbox image present: `docker images | grep umbral-sandbox-copilot-cli`.
5. Token gate: `printf %s "$COPILOT_GITHUB_TOKEN" | sha256sum | cut -c1-12` ==
   `a19dbad9a470`; GitHub `/user` == 200 (value never printed).
6. Spec: `python scripts/pit/pit_spec_validate.py examples/pit/pit_spec.golden-broker-v1.yaml`
   → `status: pass` (exit 0).
7. Auth file contains the verbatim GO phrase for the run class (see §3.4).

### 3.2 Rebuild image if pruned (P1b)

```
bash worker/sandbox/refresh-copilot-cli.sh          # → umbral-sandbox-copilot-cli:<sha256-12>
# pin in ~/.config/openclaw/copilot-cli.env:
COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:<tag>
systemctl --user restart umbral-worker              # health must return 200
```

### 3.3 Single window (open → N POST → rollback)

1. **Backups (600):** `copilot-cli.env`, `tool_policy.yaml`, `nft` ruleset.
2. **Set `trap rollback EXIT INT TERM HUP`** before the first mutation.
3. **Resolve egress with GitHub Meta (mandatory):**
   `python3 scripts/copilot_egress_resolver.py --include-github-meta --non-strict --format json`;
   assert `140.82.112.0/20 ∈ ip_sets.copilot_v4` (else BLOCK).
4. **nft:** `sudo -n nft -c -f infra/networking/copilot-egress.nft.example` (parse),
   then apply, populate `copilot_v4/v6` from resolver JSON, assert `140.82.112.0/20` live.
5. **L4:** `sed -i "240s/activated: false/activated: true/" config/tool_policy.yaml`
   (assert diff == 2 lines).
6. **L3:** `sed -i "s/^RICK_COPILOT_CLI_EXECUTE=false/…=true/" copilot-cli.env`;
   `systemctl --user restart umbral-worker`; health 200; token fp recheck.
7. **N POST** `http://127.0.0.1:8088/run` (exactly one per lane, **zero retries**),
   `dry_run=false`, `--network=copilot-egress`, metadata `{pit_id,batch_id,agent_id,lane_id,iteration}`.
8. **rollback (trap):** restore env+policy from backups, `nft delete table inet
   copilot_egress`, restart worker, assert env/policy **byte-identical** and gates
   ABSENT/false, health 200.

### 3.4 GO phrases (verbatim)

- **mini-smoke:** `autorizo P9 broker-real mini-smoke copilot_cli read-only probe`
- **golden (3 lanes):** `autorizo P9 broker-real golden torneo 3 lanes copilot_cli read-only probe`
- **image rebuild (no gates):** `autorizo rebuild imagen sandbox copilot_cli en VPS (solo infra P1, sin abrir L3/L4/nft)`
- **future runs:** require a fresh, explicit, bounded phrase per window — no standing authorization.

### 3.5 Ledger (post-rollback, read-only)

```
python3 scripts/pit/pit_collect_tokens.py \
  --pit-id <pit_id> --vault-root ~/umbral-pit-vault \
  --openclaw-root ~/.openclaw --audit-root reports/copilot-cli \
  --output ~/umbral-pit-vault/pit/<pit_id>/metrics/token_ledger.yaml
```

---

## 4. Known limitations

- **`copilot_cli` tokens `not_reported`** — GitHub Copilot CLI 1.0.36 does not emit
  token/cost; the worker records `tokens: { source: "not_reported_by_github_copilot_cli" }`.
- **Historical v1 tournaments carry no `pit_id` in audit** — `pit-umbral-bim2-sharepoint-acc`
  and `pit-salud-mental-pilot` predate P4; only post-P4 runs correlate by `pit_id/lane_id`.
- **Worker-direct validated; Rick/OpenClaw spawn is P10 (optional)** — broker-real was
  proven via direct worker POSTs, not OpenClaw agent orchestration. `openclaw_total=0`
  in the ledger is expected. Full end-to-end Rick spawn under `pit-golden-broker-v1-*`
  remains an optional future phase.
- **Spec lane_ids vs operational lane_ids** — the golden spec uses
  `lane-gpt55/lane-opus47/lane-gpt54-mini`; operational runs use
  `lane-foundry-tools/lane-codex-depth/lane-cost-mini` (same models) for ledger
  continuity across dry/mini/golden.

---

## 5. Default gate state

Gates are **always closed** outside an authorized window:

| Gate | Default | Verify |
|---|---|---|
| L3 execute | `RICK_COPILOT_CLI_EXECUTE=false` | `grep '^RICK_COPILOT_CLI_EXECUTE=' ~/.config/openclaw/copilot-cli.env` |
| L4 egress | `activated: false` (L240) | `sed -n '240p' config/tool_policy.yaml` |
| nft egress | ABSENT | `sudo -n nft list table inet copilot_egress` |

Post-golden rollback confirmed all three closed and byte-identical to pre-window
backups (`env_identical=YES`, `policy_identical=YES`, `nft=ABSENT`, `health=200`).
