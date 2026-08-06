# P1.2 — KILL de ramas remotas con PR mergeado, todo origin (2026-08-06)

> **Pack:** PKG-UAS-P1-2-MERGED-KILL · rama `claude/pkg-uas-p1-2-merged-kill-20260806` · base `54a6b519`
> **GO de David (verbatim):** "alcance A — autorizo borrar las ramas remotas con PR ya mergeado en TODO
> origin (universo ~191 del acta #588), no solo los 4 prefijos."
> **Precede a este pack:** [uas-p1-2-branch-wt-2026-08-06.md](uas-p1-2-branch-wt-2026-08-06.md) (PR #588,
> MERGED) — dejó Fase B en STOP por divergencia de conteo. Este pack resuelve esa Fase B con alcance
> confirmado por David.

---

## 1. Recómputo (no se confió en el número 191 del acta anterior)

```
git fetch origin --prune
git ls-remote --heads origin                                                    # 284 refs, excl. main
gh pr list --repo Umbral-Bot/umbral-agent-stack --state merged --limit 600 --json headRefName,number,mergedAt   # 500 PRs
gh pr list --repo Umbral-Bot/umbral-agent-stack --state open   --limit 600 --json headRefName,number            # 2 PRs
```

```
KILL = heads ∩ {headRefName de PRs merged} − {headRefName de PRs open} − {main} − {rama de este pack}
```

| Métrica | Valor |
|---|---|
| Ramas remotas totales (excl. `main`) | 284 |
| PRs mergeados (universo de cruce) | 500 |
| PRs open | 2 — `#541` (`claude/plan-sys-diag-openclaw-worksystem-2026-07-17`), `#521` (`copilot/docs-openclaw-models-hygiene-20260704`) |
| Solapamiento open∩merged (sanity check) | 0 — confirma que ninguna de las 2 open está mal clasificada |
| **KILL (a borrar en este pack)** | **192** |

192 vs 191 del acta anterior: +1, coherente con drift temporal normal (un PR más se mergeó entre el acta
#588 y ahora). Cruce contra las 90 huérfanas del acta anterior: **0 solapamiento** — ninguna huérfana
entró en la lista KILL por error.

## 2. Lista exacta (192 ramas, escrita ANTES del primer delete)

`rama` — `PR#`

```
antigravity/001-rick-recommendations — 110
antigravity/083-analisis-contenido-perdido — 87
antigravity/086-recuperar-browser-automation — 88
audit-2026-03-quick-wins — 106
claude/090-implementar-notion-bitacora — 96
claude/docs-tanda-b-security-plan — 543
claude/editorial-roadmap-norte-2026-07-22 — 551
claude/feat-azure-editorial-blog-v1 — 466
claude/feat-cap-p0-verify-append — 537
claude/feat-cap-p1-task-from-raw — 538
claude/fix-cap-p1-canonical-identity-safe-update — 539
claude/fix-granola-p1-1-observability — 530
claude/fix-p2a-poller-v2-isolation — 540
claude/fix-replace-blocks-large-pages — 534
claude/fix-tanda-a-runtime-guardrails — 542
claude/granola-mcp-free-capture — 531
claude/p11b-closeout-audit — 535
claude/p11b-granola-drive-catchup — 532
claude/p11b-granola-drive-catchup-sender — 533
claude/pkg-uas-north-canon-draft-20260806 — 583
claude/pkg-uas-north-inventory-20260806 — 582
claude/pkg-uas-north-paso5-close-20260806 — 586
claude/pkg-uas-openclaw-stubs-20260806 — 584
claude/pkg-uas-openclaw-stubs-close-20260806 — 585
claude/pkg-uas-p1-2-branch-wt-20260806 — 588
claude/pkg-user-e2e-p3-02-rerun-20260806 — 587
claude/plan-granola-capitalization-hybrid — 536
claude/task-004-project-governance — 114
codex/accion-2-sync-openclaw-workspaces — 154
codex/aeco-aca-pull-auth-followup — 455
codex/aeco-ghcr-auth-followup — 451
codex/aeco-ghcr-build-workflow — 450
codex/auth-lifecycle-tracking — 251
codex/cand-002-source-driven-flow — 267
codex/core-first-stabilization — 449
codex/diagnostico-openclaw-integral-r24 — 153
codex/editorial-gold-set-minimum — 253
codex/editorial-research-capitalization — 249
codex/f8a-diagnostic-mode-2026-05-06 — 300
codex/f8a-docker-stdin-fix-2026-05-06 — 302
codex/f8a-drop-no-banner-2026-05-06 — 298
codex/f8a-egress-model-power-task-2026-05-07 — 324
codex/f8a-history-recovery-2026-05-07 — 316
codex/f8a-real-exec-path-2026-05-05 — 294
codex/f8a-run6-after-token-refresh-task-2026-05-07 — 314
codex/feat-editorial-unpublish — 494
codex/feat-o15-gmail-calendar-skills — 439
codex/feat-pit-p3-policy-slugs-aliases — 482
codex/fix-pit-p2c-egress-github-meta-requirement — 481
codex/ghcr-auth-issue-link — 453
codex/notion-editorial-hub-traceability — 261
codex/notion-publicaciones-db-audit — 262
codex/notion-publicaciones-provisioner-dry-run — 258
codex/notion-publicaciones-readonly-audit — 259
codex/notion-publicaciones-schema-spec — 254
codex/notion-publicaciones-test-record-qa — 263
codex/openclaw-rick-editorial-agent-contract — 264
codex/ops-logger-observability-integration — 256
codex/publish-attempt-tracking — 252
codex/structured-error-classification — 250
codex/supervisor-registry-resolver — 234
codex/task-012-tournament-lane-pr-gate — 441
coord-o16/fix-o16-2-seed-doc-id-key — 408
coord-o16/o16-2-buildingsmart-smoke-plan — 409
copilot-vps/013-ghi-rollup-into-main — 334
copilot-vps/013g-markdown-annotations-and-url-canonical — 329
copilot-vps/013h-nested-inline-divider-image-link — 332
copilot-vps/013i-blockquote-block — 333
copilot-vps/rollback-013e-and-013f-content-capture — 325
copilot-vps/wave2a-405-stop-button — 407
copilot-vps/workspace-hygiene-vps-2026-07-02 — 501
copilot-vps/workspace-hygiene-vps-fase-b-2026-07-03 — 505
copilot/082-capitalizar-cerrados — 85
copilot/085-recuperar-bitacora-scripts — 89
copilot/docs-gd52-adr-scopes — 438
copilot/docs-pit-broker-real-pass-handoff-20260622 — 487
copilot/docs-pit-readiness-golden-20260622 — 486
copilot/feat-o8a-granola-length-instrumentation — 295
copilot/feat-o8i-notion-poller-cursor-checkpoint — 296
copilot/feat-pit-broker-contract — 483
copilot/feat-pit-broker-enforce-skill — 484
copilot/feat-pit-broker-max-wall-sec — 489
copilot/feat-pit-token-ledger — 485
copilot/fix-pit-dev-quality-gates-20260704 — 522
copilot/graphify-pilot-f1-f4 — 495
copilot/windows-workspace-hygiene-fase-a-2026-07-03 — 506
copilot/windows-workspace-hygiene-fase-a-cierre-2026-07-03 — 507
copilot/workspace-hygiene-audit-2026-07-02 — 496
copilot/workspace-hygiene-pass8-2026-07-03 — 497
cursor/development-environment-setup-4b63 — 6
cursor/development-environment-setup-6340 — 3
cursor/diagn-stico-completo-del-sistema-5be1 — 7
cursor/pytest-fastapi-lifespan-9a62 — 69
cursor/rick-voice-capitalize-mvp — 511
cursor/workflow-ci-pytest-a6f3 — 73
docs/agent-skill-windows-vps-execution-split — 415
docs/custom-agent-coordinador-de-agentes — 416
docs/editorial-p0-norte-contract — 550
docs/editorial-shortlist-schema-mirror — 552
docs/editorial-smoke-e2e-2026-07-23 — 562
docs/env-google-keys-example — 107
docs/openclaw-vps-operator-agent — 417
feat/antigravity-dashboard-tools-sync — 48
feat/antigravity-personal-skills — 51
feat/claude-skill-builder-pipeline — 50
feat/claude-skills-validation — 49
feat/codex-skills-notion-windows — 46
feat/copilot-openclaw-proxy — 44
feat/copilot-skills-llm-make-obs — 45
feat/cursor-cloud-skills-figma — 47
feat/editorial-approve-promote-shortlist — 554
feat/editorial-candidate-dedupe — 557
feat/editorial-copy-long-form-v2 — 556
feat/editorial-discard-negative-loop — 558
feat/editorial-hitl2-publish-bridge — 559
feat/editorial-listo-rrss-inject — 560
feat/editorial-magnific-5-alts — 555
feat/editorial-rick-v1-contract-align — 561
feat/skills-coverage-single-word — 70
feat/tournament-phase2-contestant-artifact — 205
feat/tournament-phase2-eligibility-policy — 216
feat/tournament-phase2-final-cherry-pick — 206
feat/tournament-phase2-judge-contract — 207
feat/tournament-phase2-pytest-sandbox-infra — 213
feat/tournament-phase2-pytest-target-runner — 214
feat/tournament-phase2-python-ast-lint — 212
feat/tournament-phase2-python-compile-validation — 210
feat/tournament-phase2-rejudge-with-validation — 211
feat/tournament-phase2-single-file-code-change — 208
feat/tournament-phase2-target-file-code-change — 209
feat/vps-repo-policy-ensure-main — 423
fix/llm-gpt54-max-completion-tokens — 203
fix/task-type-testing-drift — 420
fix/tournament-pytest-target-tmpfs-mounts — 215
fix/tournament-winner-parser-multilingual — 204
integracion-prs-69-70-71-73 — 80
reconciliation/align-runtime — 195
rescue/copilot-vps/canonical-untracked-2026-07 — 504
rick/ambiguity-signal-passive — 237
rick/ambiguous-improvement-task-detection — 231
rick/close-task-2026-05-19-001 — 424
rick/closed-ooda-loop-contract — 233
rick/copilot-cli-capability-design — 269
rick/copilot-cli-f6-step6c4f-activation-playbook — 271
rick/copilot-cli-f7-egress-staging-evidence — 280
rick/copilot-cli-f7-execute-gate-rehearsal-evidence — 276
rick/copilot-cli-f7-nft-live-rollback-evidence — 282
rick/copilot-cli-f7-policy-gate-rehearsal — 274
rick/copilot-cli-f7-policy-gate-rehearsal-evidence — 275
rick/copilot-cli-f7-readiness-rehearsal-evidence — 277
rick/copilot-cli-f7-sandbox-image-evidence — 278
rick/copilot-cli-postmerge-evidence-6c4d — 270
rick/docs73-post-234-alignment — 235
rick/f8a-diagnose-silent-exit-2026-05-06 — 301
rick/f8a-first-real-run-2026-05-05 — 297
rick/f8a-retry-after-no-banner-fix-2026-05-06 — 299
rick/f8a-run6-after-token-refresh-2026-05-07 — 322
rick/f8b-diagnose-egress-and-model-power-2026-05-07 — 326
rick/fix-composite-research-timeout — 226
rick/github-mvp-handlers — 196
rick/github-mvp-hardening — 198
rick/github-ops-skill-clean — 217
rick/github-tournament-phase1 — 200
rick/granola-capitalization-guardrails-9227 — 246
rick/granola-project-first-rule — 248
rick/granola-transcript-reconciliation-9227 — 245
rick/improvement-supervisor-activation-playbook — 240
rick/improvement-supervisor-role — 229
rick/notion-operation-trace-guardrail-d657 — 247
rick/phase6b-activation-readiness-docs-4721 — 244
rick/reconcile-skill-modelos-doc — 228
rick/rescue-secret-output-guard-2026-05-20 — 425
rick/runtime-role-tools-models-clean — 227
rick/stage7_5-source-verify — 387
rick/supervisor-config-consistency — 238
rick/supervisor-dispatcher-invariance-tests — 236
rick/supervisor-observability-events — 239
rick/supervisor-observability-monitoring — 242
rick/supervisor-observability-runtime-wiring — 241
rick/supervisor-resolution-contract — 232
rick/supervisor-routing-contract — 230
rick/supervisor-structured-telemetry — 243
rick/tournament-routing-clean — 219
rick/tournament-runbook-clean — 218
rick/untrack-local-only-surfaces — 199
rick/vps — 105
rick/windows-fs-b64 — 5
rick/windows-fs-tools — 4
rrss-wave2a/402-publication-content-hash — 410
rrss-wave2a/404-lite-publish-log — 411
rrss-wave2a/docs-and-prompts — 412
tournament/umbral-agent-stack-434-484277c0/lane-lane-a — 435
```

192 líneas. Ninguna coincide con `main`, con `#541`/`#521` (open), ni con las 90 huérfanas del acta
[uas-p1-2-branch-wt-2026-08-06.md](uas-p1-2-branch-wt-2026-08-06.md) §4.

## 3. Ejecución

7 lotes de `git push origin :refs/heads/<rama1> :refs/heads/<rama2> ...` (30 refspecs por lote, último
lote 12). Salida literal completa en el log de la corrida; resumen:

| Métrica | Valor |
|---|---|
| N planificadas | 192 |
| N borradas (`[deleted]` confirmado por git) | **192** |
| N fallidas | **0** |

Post-check:

```
git ls-remote --heads origin | wc -l   # 93 (92 ramas + main), antes 284 (283 + main)
comm -12 <(sort kill_names.txt) <(sort heads_after.txt)   # vacío — 0 residuales
```

Las 192 ramas de §2 ya no existen en `origin`. Ninguna falló, ninguna quedó protegida.

`UAS_P12_MERGED_KILL_PASS=Y` — 192/192, 0 fallidas.

## 4. Prohibido (respetado)

- Cero `--force` a `main`.
- Cero KILL de huérfanas (verificado por cruce §1).
- Cero touch a `#541`/`#521` (excluidas explícitamente del cómputo).
- Cero touch a VPS, Notion, registry.
- Cero borrado de worktrees en este pack.
