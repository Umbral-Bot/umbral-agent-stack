# Copilot handoff prompts (Windows + VPS)



Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**



Last updated: 2026-06-02 (D3.2 closed #444; **D3.3 Phase 0** issue #445 + task 020)



---



## Estado activo



| Hilo | Superficie | Estado | Requiere |

|---|---|---|---|

| **W** | Copilot-VPS | ✅ | `D32_WORKTREE_CLEANUP_NOOP_OK` |

| **AA** | Copilot-VPS | ✅ | `D33_PREFLIGHT_OK` @ `420e9f6f` |

| **AB** | Copilot-VPS | 🔴 **Siguiente** | `autorizo torneo D3.3` |

| **AC** | Copilot Windows | ⏸ | 2 PR URLs + `autorizo merge winner D3.3` |

| **AD** | Copilot-VPS | ⏸ | post-merge tras AC |

| **AF** | Copilot Windows | ⏸ paralelo | Mission Control PR (D4.1) |

| **AG** | Copilot-VPS | ⏸ paralelo | Granola soak read-only (D5.3) |



**HEAD canónico:** `2fe58535` (PR #444). Issue torneo activo: [#445](https://github.com/Umbral-Bot/umbral-agent-stack/issues/445)



**Lección D3.2:** torneo PARTIAL (0 PR URLs) → salvage #444. D3.3 exige **PR URL por lane** antes de cerrar lane.



---



## Thread W — Copilot-VPS · cleanup worktree D3.2 (opcional, recomendado antes torneo)



**Requiere:** David escribe exactamente: `autorizo cleanup worktree D3.2`



```

Sos Copilot-VPS. Cleanup post D3.2 — READ-ONLY salvo acciones git locales explícitas abajo.

NO borrar ~/.coord-ag-evidence/D3.2/ ni ~/.coord-ag-evidence/D3.2/salvage-artifacts.tgz



=== Fase 0 — Preflight repo ===

cd ~/umbral-agent-stack

git fetch origin main

git checkout main

git pull --ff-only origin main

git log -1 --oneline

git status --short --branch



Si worktree NO clean → documentar cada archivo untracked/modified antes de continuar.



=== Fase 1 — Inventario torneo residual ===

git branch -a | grep -iE 'tournament|lane-backup' || echo NO_TOURNAMENT_BRANCHES

find scripts -maxdepth 3 -name 'lane-backup-*' -print 2>/dev/null || true

find . -maxdepth 2 -name 'registry_backup_alert.py' 2>/dev/null | grep -v scripts/registry || true



=== Fase 2 — Cleanup (solo si hay residuo) ===

# Si estás en rama tournament/*:

git checkout main

git pull --ff-only origin main



# Borrar ramas locales tournament/* ya mergeadas o obsoletas (NO origin/main):

for b in $(git branch | grep -i tournament || true); do

  git branch -D "$b" 2>/dev/null || true

done



# Untracked lane scripts fuera de main (ej. scripts/registry_backup_alert.py sueltos):

# SOLO borrar si duplican scripts/registry/registry_backup_alert.py ya en main @ 2fe58535

git status --short



=== Fase 3 — Verificación final ===

git status --short --branch   # debe quedar ## main...origin/main sin M/??

test -f scripts/registry/registry_backup_alert.py && echo SALVAGE_ON_MAIN_OK

test -d ~/.coord-ag-evidence/D3.2 && echo EVIDENCE_PRESERVED_OK



=== Entregable ===

Tabla: rama eliminada | archivo removido | evidencia intacta sí/no



VEREDICTO: D32_WORKTREE_CLEANUP_OK | D32_WORKTREE_ALREADY_CLEAN | D32_WORKTREE_CLEANUP_BLOCKED

```



---



## Thread AA — Copilot-VPS · D3.3 preflight (task 020) 🔴 SIGUIENTE



**Sin spawn.** **Sin** `openclaw agent run`. **Sin** tocar env.



```

Sos Copilot-VPS. Preflight torneo D3.3 O3 sync_skills adapters — issue #445.



Objetivo: confirmar que el repo, spec, skill orchestrator, allowAgents y dry-run están listos

ANTES de que David autorice el torneo real.



=== Fase 0 — Repo sync ===

cd ~/umbral-agent-stack

git fetch origin main && git checkout main && git pull --ff-only origin main

git log -1 --oneline

git status --short --branch



PASS si HEAD incluye task 020 y spec d33 (Cursor push previo).

FAIL si TASK_FILE_MISSING o SPEC_MISSING → VEREDICTO D33_PREFLIGHT_BLOCKED repo desactualizado.



test -f .agents/tasks/2026-06-02-020-d3.3-tournament-sync-skills-adapters.md && echo TASK_FILE_OK

test -f openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d33-issue-445-sync-skills-adapters-spec.yaml && echo SPEC_OK

test -f scripts/vps/d3.3-tournament-run.sh && echo RUN_SCRIPT_OK



=== Fase 1 — Evidencia ===

mkdir -p ~/.coord-ag-evidence/D3.3

EV=~/.coord-ag-evidence/D3.3/preflight-$(date +%Y%m%d%H%M).log

exec > >(tee -a "$EV") 2>&1

echo "preflight_start=$(date -Iseconds)"



=== Fase 2 — Skill orchestrator live ===

ORCH_REPO=openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator

ORCH_LIVE=~/.openclaw/workspace/skills/multi-agent-tournament-orchestrator

if [ ! -f "$ORCH_LIVE/SKILL.md" ]; then

  echo ORCHESTRATOR_LIVE_MISSING

  echo "Esperando: autorizo sync tournament skill"

  # Si David ya autorizó en el mismo turno:

  # rsync -a "$ORCH_REPO/" "$ORCH_LIVE/"

else

  echo ORCHESTRATOR_LIVE_OK

  diff -qr "$ORCH_REPO/examples/" "$ORCH_LIVE/examples/" 2>/dev/null | head -20 || true

fi



=== Fase 3 — Dry-run 8/8 ===

bash scripts/openclaw/tournament-preflight-dry-run.sh \

  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d33-issue-445-sync-skills-adapters-spec.yaml



=== Fase 4 — allowAgents ===

bash scripts/vps/check-main-allowagents.sh



=== Fase 5 — Runtime sanity (read-only) ===

curl -sf http://127.0.0.1:8088/health | head -c 500 || echo WORKER_HEALTH_FAIL

systemctl --user is-active openclaw-gateway.service 2>/dev/null || echo GATEWAY_STATUS_UNKNOWN

/home/rick/.npm-global/bin/openclaw status 2>/dev/null | head -30 || true



=== Fase 6 — Baseline sync_skills (read-only) ===

python3 scripts/sync_skills_to_vps.py --dry-run 2>&1 | tail -20

python3 -m pytest tests/ -q --co -k sync 2>/dev/null | tail -10 || echo NO_EXISTING_SYNC_TESTS_OK



=== Fase 7 — Worktree gate ===

if [ -n "$(git status --porcelain)" ]; then

  echo WORKTREE_DIRTY_BLOCKED

  git status --short

  VEREDICTO D33_PREFLIGHT_BLOCKED

  exit 1

fi



echo "preflight_end=$(date -Iseconds)"

echo Log: $EV



Criterios PASS:

- TASK_FILE_OK + SPEC_OK + RUN_SCRIPT_OK

- dry-run script exit 0

- allowAgents incluye rick-delivery + rick-qa

- worktree clean



VEREDICTO: D33_PREFLIGHT_OK | D33_PREFLIGHT_BLOCKED

```



---



## Thread AB — Copilot-VPS · run torneo D3.3 (real)



**Requiere:** `D33_PREFLIGHT_OK` + David escribe: `autorizo torneo D3.3`



```

autorizo torneo D3.3



Sos Copilot-VPS. Torneo real #3 issue #445 — O3 sync_skills adapters.



=== Reglas duras (D3.2 lesson) ===

1. Lane sin PR URL = INCOMPLETE — no counts as done.

2. Cada lane debe: branch → implement → pytest → git push → gh pr create → announce JSON con pr_url.

3. NO merge. NO touch ~/.config/openclaw/env. NO gateway restart salvo blocker allowAgents.

4. Parent standalone main — NO nested orchestrator spawn.

5. Evidencia obligatoria en ~/.coord-ag-evidence/D3.3/



=== Fase 0 — Pre-run gate ===

cd ~/umbral-agent-stack

git fetch origin main && git checkout main && git pull --ff-only origin main

git status --short --branch

# STOP si dirty



mkdir -p ~/.coord-ag-evidence/D3.3

EV=~/.coord-ag-evidence/D3.3

echo "run_start=$(date -Iseconds)" | tee "$EV/run-meta.txt"

git log -1 --oneline | tee -a "$EV/run-meta.txt"



=== Fase 1 — Ejecutar torneo ===

chmod +x scripts/vps/d3.3-tournament-run.sh

bash scripts/vps/d3.3-tournament-run.sh



=== Fase 2 — Monitoreo post-spawn (cada 15–30 min hasta fin o timeout 7200s) ===

# Session id desde:

cat "$EV/session.txt"



# Spawn evidence:

grep -iE 'sessions_spawn|lane|pr_url|incomplete|error' "$EV/openclaw-agent.log" | tail -80



# PRs creadas:

gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament" --state open --json number,title,url,headRefName



=== Fase 3 — Collect phase (obligatorio antes de veredicto) ===

# Extraer PR URLs de log + gh:

grep -oE 'https://github.com/Umbral-Bot/umbral-agent-stack/pull/[0-9]+' "$EV/openclaw-agent.log" | sort -u | tee "$EV/pr-urls.txt"



PR_COUNT=$(wc -l < "$EV/pr-urls.txt" | tr -d ' ')

echo "pr_count=$PR_COUNT" | tee -a "$EV/run-meta.txt"



# Métricas JSON mínimo:

python3 - <<'PY' | tee "$EV/final-metrics.json"

import json, pathlib, re

ev = pathlib.Path.home() / ".coord-ag-evidence/D3.3"

log = (ev / "openclaw-agent.log").read_text(errors="replace") if (ev / "openclaw-agent.log").exists() else ""

prs = sorted(set(re.findall(r"https://github.com/Umbral-Bot/umbral-agent-stack/pull/\\d+", log)))

print(json.dumps({

  "tournament": "D3.3",

  "issue": 445,

  "pr_urls": prs,

  "pr_count": len(prs),

  "lanes_expected": 2,

  "yielded": "yielded=true" in log.lower(),

}, indent=2))

PY



=== Fase 4 — Comentario issue (obligatorio) ===

gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body-file "$EV/final-metrics.json"



=== Fase 5 — Worktree report ===

git status --short --branch

git branch -a | grep -i tournament || true



=== Veredicto ===

M1_D33_TOURNAMENT_OK     → pr_count=2, ambos lanes con PR URL, spawn x2 evidenciado

M1_D33_TOURNAMENT_PARTIAL → spawn OK pero pr_count<2 o lane incomplete (documentar causa por lane)

M1_D33_TOURNAMENT_BLOCKED → preflight falló mid-run o worktree corrupto



NO merge winner. Esperar Thread AC + autorización David.

```



---



## Thread AC — Copilot Windows · judge + merge winner D3.3



**Requiere:** `M1_D33_TOURNAMENT_OK` (o PARTIAL con 2 PRs revisables) + David: `autorizo merge winner D3.3`



```

autorizo merge winner D3.3



Sos Copilot Windows. Judge torneo D3.3 (#445) y merge squash del ganador.



=== Fase 0 — Repo sync ===

cd C:\GitHub\umbral-agent-stack

git fetch origin main

git checkout main

git pull --ff-only origin main

git log -1 --oneline

git status --short --branch



=== Fase 1 — Listar PRs torneo ===

gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament" --state open --json number,title,url,headRefName,statusCheckRollup,additions,deletions



# Si David pegó PR URLs explícitas, validar cada una:

# gh pr view <N> --repo Umbral-Bot/umbral-agent-stack --json title,body,files,statusCheckRollup,mergeStateStatus



=== Fase 2 — Rubric (spec d33-issue-445) ===

Leer:

  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d33-issue-445-sync-skills-adapters-spec.yaml



Por cada PR candidata, puntuar 1–5:

  A) Cumple acceptance #445 (codex+cursor adapters, dry-run default, tests, runbook)

  B) Tests CI-safe (fixtures only, no live paths)

  C) Diff mínimo correcto

  D) Sin scope-creep (no registry bulk, no VPS execute en tests, no env)

  E) checks verdes



Documentar tabla comparativa en comentario issue antes de merge.



=== Fase 3 — Diff review (obligatorio) ===

# Reemplazar N1 N2 con números reales:

gh pr diff N1 --repo Umbral-Bot/umbral-agent-stack --color=never > %TEMP%\d33-pr-N1.diff

gh pr diff N2 --repo Umbral-Bot/umbral-agent-stack --color=never > %TEMP%\d33-pr-N2.diff



Revisar: scripts/sync_skills* tests/fixtures docs/ops/sync-skills-adapters-runbook.md

Rechazar si toca: .env, openclaw.json, VPS secrets, umbral-skills-registry bulk



=== Fase 4 — Tests local (obligatorio si diffs razonables) ===

python -m pytest tests/ -k sync_skills -q

# Si falla → NO merge; comentar en issue con traceback



=== Fase 5 — Merge winner ===

gh pr view WINNER --repo Umbral-Bot/umbral-agent-stack --json mergeStateStatus,statusCheckRollup

# Solo si CLEAN + checks SUCCESS:

gh pr merge WINNER --repo Umbral-Bot/umbral-agent-stack --squash --delete-branch



git fetch origin main

git pull --ff-only origin main

git log -1 --oneline



=== Fase 6 — Cierre issue ===

gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body "Winner: PR #WINNER. Loser kept per cleanup_policy. HEAD: $(git log -1 --oneline)"



VEREDICTO: D33_WINNER_MERGED

Incluir: winner PR URL, SHA squash, loser PR URL (sin merge)

```



---



## Thread AD — Copilot-VPS · post-merge D3.3



**Requiere:** `D33_WINNER_MERGED` con SHA conocido



```

Sos Copilot-VPS. Post-merge D3.3 salvage/winner.



cd ~/umbral-agent-stack

git fetch origin main && git checkout main && git pull --ff-only origin main

git log -1 --oneline

git log --oneline -5 | grep -iE '#445|445' || git log --grep='#445' -1 --oneline

git status --short --branch



# Verificar entregables en main:

test -f docs/ops/sync-skills-adapters-runbook.md && echo RUNBOOK_OK || echo RUNBOOK_MISSING

python3 -m pytest tests/ -k sync_skills -q



HEAD debe incluir squash winner #445 (no solo 2fe58535).

NO borrar ~/.coord-ag-evidence/D3.3/



VEREDICTO: D33_VPS_POST_MERGE_OK | D33_VPS_POST_MERGE_BLOCKED

```



---



## Thread AF — Copilot Windows · D4.1 Mission Control PR (paralelo)



**Independiente del torneo.** No bloquea D3.3.



```

Sos Copilot Windows. D4.1 Mission Control — abrir o retomar PR scaffold O13.1.



cd C:\GitHub\umbral-agent-stack

git fetch origin

git branch -a | grep -i mission-control



# Si existe rama remota copilot/feat-mission-control-o13-1:

git checkout copilot/feat-mission-control-o13-1 2>$null || git fetch origin copilot/feat-mission-control-o13-1:copilot/feat-mission-control-o13-1 && git checkout copilot/feat-mission-control-o13-1

git rebase origin/main

# Resolver conflictos mínimos; NO scope creep



python -m pytest tests/ -k mission -q 2>$null || python -m pytest tests/ -q --co | findstr mission



gh pr list --repo Umbral-Bot/umbral-agent-stack --head copilot/feat-mission-control-o13-1 --json number,state,url

# Crear PR si no existe; si existe → actualizar body con test plan



Entregable: PR URL + pytest mission count + diff summary (FastAPI :8089 read-only)



VEREDICTO: D41_MISSION_CONTROL_PR_READY | D41_MISSION_CONTROL_PR_BLOCKED

```



---



## Thread AG — Copilot-VPS · D5.3 Granola soak read-only (paralelo)



```

Sos Copilot-VPS. D5.3 Granola soak — READ-ONLY. NO restart worker salvo gate G-D0 explícito.



cd ~/umbral-agent-stack && git pull --ff-only origin main



=== Checks ===

systemctl --user status notion-poller 2>/dev/null | head -15 || pgrep -af notion-poller

journalctl --user -u umbral-worker -n 30 --no-pager 2>/dev/null | tail -20

journalctl --user -u openclaw-dispatcher -n 20 --no-pager 2>/dev/null | tail -15



# Redis cursor sample (prefix only, no secrets):

redis-cli GET notion:poll:cursor 2>/dev/null | head -c 80



# Últimas filas Granola classify si log existe:

grep -i granola ~/.config/umbral/ops_log.jsonl 2>/dev/null | tail -5 || true



Documentar: poller alive sí/no, último evento, errores 24h, truncamiento evidenciado sí/no.



VEREDICTO: D53_GRANOLA_SOAK_OK | D53_GRANOLA_SOAK_DEGRADED | D53_GRANOLA_SOAK_BLOCKED

```



---



## Archivo — D3.2 (cerrado)



| Hilo | VEREDICTO |

|---|---|

| T preflight | D32_PREFLIGHT_OK |

| U torneo | M1_D32_TOURNAMENT_PARTIAL |

| salvage #444 | D32_ISSUE440_MERGED @ 2fe58535 |

| VPS post-merge | D32_VPS_POST_MERGE_OK |



---



## Próximo foco Q2



| Prioridad | Spine | Secuencia |

|---|---|---|

| 1 | **D3.3** | W (opcional) → **AA** → AB → AC → AD |

| 2 | D4.1 | AF paralelo |

| 3 | D5.3 | AG paralelo |

| 4 | D3.4 | Retro protocolo tras D3.3 |

| 5 | D6.1 | KB AECO (26-jun) |



Friday retro **2026-06-05** — actualizar dashboard §4 spine v2.



---



## Cerrados — no repetir



- G-D5.1 → G_D51_VPS_AUDIT_OK

- G-D5.2 → G_D52_GATE_CLOSED

- O15 skills → O15_OPENCLAW_WORKSPACE_SKILLS_OK @ 3388bf9c

- D3.2 salvage → #444 @ 2fe58535

- Task 012 lane gate → #441 @ 462ef1c1


