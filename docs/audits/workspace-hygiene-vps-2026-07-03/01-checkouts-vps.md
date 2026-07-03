# Pass V1 — Inventario de checkouts UAS en la VPS

> Fecha: 2026-07-03 · Read-only · Método: `find` (~, /opt, /srv, /tmp) + `git worktree list` del canónico

## Totales

- **5 clones independientes** (con `.git/` propio)
- **10 worktrees** vinculados al canónico (comparten objetos, ramas y stashes con `~/umbral-agent-stack`)
- **2 residuos**: 1 dir vacío + 1 worktree prunable en /tmp
- Nada en `/opt`, `/srv` ni `/tmp` (salvo el prunable)

## Tabla de clasificación

| # | Path | Tipo | Rama | Últ. commit | vs origin/main | Dirty | Stash | Tamaño | Clasificación |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `~/umbral-agent-stack` | CLONE | `main` | 60f605a 2026-07-02 | 0↓ 0↑ | 5 untracked | 24 | 487M | **KEEP (CANÓNICO)** |
| 2 | `~/.openclaw/workspace/umbral-agent-stack` | CLONE | `rick/vps` | 4b8cfbb 2026-06-07 | 5↓ 13↑ | 1 (chmod) | 1 único | 9.4M | **RESCUE** (P0) |
| 3 | `~/umbral-agent-stack.backup-pre-cand001-20260629-174640` | CLONE | `rick-delivery/editorial-contract-paths` | 18cdc48 2026-06-29 | 1↓ 1↑ | 29 untracked | 24 (dup) | 456M | **RESCUE→ARCHIVE** |
| 4 | `~/umbral-agent-stack-cursor` | CLONE | `rick/supervisor-structured-telemetry` | b376a4d 2026-04-20 | 1435↓ 822↑ | 0 | 0 | 390M | **ARCHIVE** (todo en origin) |
| 5 | `~/umbral-agent-stack-cand001-apply-20260629-174758` | CLONE | `main` (stale @61de099) | 2026-06-29 | stale | 0 | 0 | 33M | **DELETE-candidate** |
| 6 | `~/.openclaw/workspaces/rick-delivery/umbral-agent-stack-poller-hardening` | WORKTREE | `rick-delivery/poller-healthcheck-hardening` | b7f8e41 2026-05-18 | 346↓ 19↑ | 0 | (comp.) | — | **RESCUE** (P0) |
| 7 | `~/umbral-agent-stack-copilot-cli` | WORKTREE | `rick/copilot-cli-capability-design` | fa704e9 2026-04-27 | 1453↓ 936↑ | 0 | (comp.) | 18M | ARCHIVE (tip = origin) |
| 8 | `~/umbral-agent-stack-editorial` | WORKTREE | `rick/editorial-linkedin-writer-flow` | 410266a 2026-05-05 | 1453↓ 915↑ | 0 | (comp.) | 11M | ARCHIVE (tip = origin) |
| 9 | `~/umbral-agent-stack-activation-playbook` | WORKTREE | `rick/copilot-cli-f6-step6c4f-activation-playbook` | bd85732 2026-04-29 | 1453↓ 941↑ | 0 | (comp.) | — | ARCHIVE (tip = origin) |
| 10 | `~/umbral-agent-stack-postmerge-evidence` | WORKTREE | `rick/copilot-cli-postmerge-evidence-6c4d` | 7e96a87 2026-04-27 | 1453↓ 938↑ | 0 | (comp.) | — | ARCHIVE (tip = origin) |
| 11 | `~/umbral-agent-stack-f7-code-gate` | WORKTREE | `rick/copilot-cli-f7-code-gate-rehearsal` | 0d6ad83 2026-05-05 | 1453↓ 994↑ | 0 | (comp.) | — | ARCHIVE (tip = origin) |
| 12 | `~/umbral-agent-stack-f7-policy-gate` | WORKTREE | `rick/copilot-cli-f7-policy-gate-rehearsal` | b96a7eb 2026-05-05 | 1453↓ 967↑ | 0 | (comp.) | — | ARCHIVE (tip = origin) |
| 13 | `~/umbral-agent-stack-lane-sqlite-impl` | WORKTREE | `tournament/…403…/lane-sqlite-impl` | 52a4b6e 2026-06-01 | 125↓ **0↑** | 0 | (comp.) | — | DELETE-candidate (contenido en main) |
| 14 | `~/.coord-ag-evidence/worktrees/…434…/lane-lane-a` | WORKTREE | `tournament/…434…/lane-lane-a` | 34e9b6b 2026-06-10 | — | 0 | — | 43M (dir) | DELETE-candidate (tip = origin) |
| 15 | `~/.coord-ag-evidence/worktrees/…434…/lane-lane-b` | WORKTREE | `tournament/…434…/lane-lane-b` | 63e9111 2026-06-10 | — | 0 | — | (incl.) | DELETE-candidate (tip = origin) |
| — | `~/.coord-ag-evidence/worktrees/umbral-agent-stack-d35-33863db/` | dir vacío | — | — | — | — | — | 8K | DELETE-candidate (vacío; rama en origin) |
| — | `/tmp/lane-b-clean-SjKNoJ` | prunable | detached 7876c61 | — | — | — | — | — | DELETE-candidate (`git worktree prune`) |

> `(comp.)` = los worktrees comparten los 24 stashes y las 203 ramas locales del canónico.
> Los "↑ ahead" enormes de las ramas de abril–mayo (915–994) reflejan el linaje pre-rewrite de la historia (R18–R21, ya capitalizado según Windows Pass 8); **sus tips están en origin al mismo SHA**, por eso son ARCHIVE seguros.

## Detalle del canónico (`~/umbral-agent-stack`)

- `main` @ `60f605a`, sincronizado 0↓/0↑ con origin/main.
- **Dirty**: 5 untracked → `00_auditoria_schema_rick_cursor.md` (jun-16) + 4 specs PIT (`examples/pit/pit-openclaw-broker-v2/v3.lanes.yaml`, `pit_spec.openclaw-broker-v2/v3.yaml`, jun-27/28). Los specs v1/v4 SÍ están tracked en main; v2/v3 nunca se commitearon → candidatos a rescue (ver Pass V4).
- **24 stashes** (2026-05-05 → 2026-06-02): WIP de stage7_5, voice-v2, f8e ladder, copilot-vps 013/029, pre-deploys. Espejo exacto del patrón que Windows Pass 8 tuvo que rescatar. Lista completa en apéndice abajo.
- **203 ramas locales**: censo contra `ls-remote` real → **81 respaldadas exactas en remoto · 19 mergeadas en main · 103 con tip no respaldado**. De las 103, la gran mayoría son evidencia F7/F8 (may), lanes `rick/t/<hash>/{a,b,c,final}` de tournaments, y stacks editoriales ya capitalizados por otra vía. Triage individual queda bajo gate (Pass V4).
- **Refspec estrecho (hallazgo)**: `remote.origin.fetch` solo trae `main` y `copilot/*` → los remote-tracking refs estaban incompletos (63 locales vs 237 heads reales en origin). Durante el censo se hizo un fetch explícito completo (`+refs/heads/*:refs/remotes/origin/*`, solo refs de tracking, sin tocar ramas locales) para clasificar con precisión → ahora 249 refs. **Propuesta bajo gate**: persistir el refspec completo en config.

## Detalle `rick/vps` (ver Pass V4 para plan)

7 commits que **no existen ni en `origin/rick/vps` ni en `origin/main`** (verificado commit por commit):

```
4b8cfbb 2026-06-07 docs: add CAND-PROD001 decision brief
38d3da1 2026-03-08 feat: standard operating model and linear issue creation improvements
9f17e16 2026-03-07 agents: mensaje para Rick - puede usar SSH a la VM desde la VPS
504aca7 2026-03-07 fix(scripts): quitar apostrofos y em-dash en vm-ssh-key-diagnostic.ps1
6846369 2026-03-07 fix(scripts): escape comillas dobles en vm-ssh-key-diagnostic.ps1
a220b34 2026-03-07 fix(scripts): comillas en vm-ssh-key-diagnostic.ps1 para PowerShell
c7d7608 2026-03-07 docs(runbook): SSH VM desde PC + script diagnostico vm-ssh-key-diagnostic.ps1
```

- Diff acumulado vs main: 16 archivos, +542/−32 (identity/ Embudo V2, docs/34-linear-first, scripts linear/vm-ssh, `.rick/`).
- Además el local está **141 commits behind de `origin/rick/vps`** → la rama remota siguió otra vida; convergencia requiere decisión explícita, NUNCA merge silencioso.
- Stash único: `WIP on rick/windows-fs-b64: … windows.fs.write_bytes_b64`.
- Dirty: solo `chmod +x openclaw/bin/worker-call` (trivial, probablemente intencional en runtime).

## Apéndice — stashes del canónico (24)

```
2026-06-02 On main: d3.3-preflight-local-log
2026-06-02 On main: copilot-vps-pre-o15-skills-sync-2026-06-02
2026-05-20 On main: pre-pr423-deploy fork-fase-a + scripts-experimentales
2026-05-08 On copilot/feat-s0-s1-discovery: parallel-agent-s0-s1-wip-rescued-by-h3
2026-05-08 WIP on copilot/docs-s6-s7-multiplatform-design
2026-05-08 WIP on copilot/docs-editorial-master-plan (notion schema audit + lib/gates)
2026-05-08 On rick/stage7_5-integration: integration-wip-canonical-helper-wire
2026-05-08 WIP on rick/stage7_5-source-verify (LLM copywriter LinkedIn)
2026-05-08 On rick/stage7_5-voice-v2: voice-v2-multiformat-WIP-pre-source-verify
2026-05-08 On rick/stage7_5-integration: voice-v2 wip recovery
2026-05-07 On rick/042-test-suite-cleanup: rick-042-test-cleanup-wip
2026-05-07 On main: vps-deploy-035-pre-pull
2026-05-07 On copilot-vps/029-stage5-deterministic-ranking: fase2-prep untracked
2026-05-07 On main: pre-029-stash
2026-05-07 WIP on main: 9cf9c01 task(031) diagnose POST /run 400
2026-05-07 WIP on main: 2d1ff8d task(copilot-vps) 018 prompt injection audit
2026-05-07 On rick/f8e-…: stash-pre-015-rick-ceo-from-f8e-branch
2026-05-07 On rick/f8e-…: auto-stash before 013i
2026-05-07 On copilot-vps/013h-…: stash-pre-013h-switch-to-main-for-O9-task
2026-05-06 On copilot-vps/rollback-013e-and-013f-…: stash-pre-014-spike
2026-05-06 On main: copilot-vps-stash-stage4
2026-05-05 On main: stash-pre-task-012-rerun-2
2026-05-05 On rick/f7-5a-code-gate-deploy: stash-before-task-012-rerun
2026-05-05 WIP on main: 4b4b70a (post merge #292)
```
