# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**

Last updated: 2026-06-02 — W/AA cerrados; **AB sigue** @ HEAD `6f560d6b`

---

## Prompts listos para enviar (orden)

| # | Agente | Cuándo | Autorización David |
|---|---|---|---|
| 1 | **Copilot-VPS** | **Ahora** | `autorizo torneo D3.3` + `autorizo sync tournament skill` |
| 2 | Copilot Windows | Tras torneo + 2 PRs | `autorizo merge winner D3.3` |
| 3 | Copilot-VPS | Tras merge winner | (automático post-AC) |
| 4 | Copilot Windows | Paralelo | — (D4.1 Mission Control) |
| 5 | Copilot-VPS | Paralelo | — (D5.3 Granola soak) |

---

## Estado activo

| Hilo | Superficie | Estado | Siguiente |
|---|---|---|---|
| **W** | Copilot-VPS | ✅ | `D32_WORKTREE_CLEANUP_NOOP_OK` |
| **AA** | Copilot-VPS | ✅ | `D33_PREFLIGHT_OK` @ `420e9f6f` |
| **AB** | Copilot-VPS | 🔴 **ENVIAR AHORA** | torneo real #445 |
| **AC** | Copilot Windows | ⏸ | judge + merge winner |
| **AD** | Copilot-VPS | ⏸ | post-merge winner |
| **AF** | Copilot Windows | ⏸ paralelo | Mission Control PR |
| **AG** | Copilot-VPS | ⏸ paralelo | Granola soak |

**HEAD canónico:** `6f560d6b` (capitalización preflight). Issue torneo: [#445](https://github.com/Umbral-Bot/umbral-agent-stack/issues/445)

**Lección D3.2:** lane sin PR URL = INCOMPLETE. No declarar `M1_D33_TOURNAMENT_OK` si `pr_count < 2`.

---

## PROMPT 1 — Copilot-VPS · Thread AB · torneo D3.3 🔴

**Pegar en Copilot-VPS:**

```
autorizo torneo D3.3
autorizo sync tournament skill

Sos Copilot-VPS. Torneo real #3 issue #445 — O3 sync_skills adapters.

=== Reglas duras (D3.2 lesson) ===
1. Lane sin PR URL = INCOMPLETE — no cuenta como done.
2. Cada lane debe: branch → implement → pytest → git push → gh pr create → announce JSON con pr_url.
3. NO merge. NO touch ~/.config/openclaw/env. NO gateway restart salvo blocker allowAgents.
4. Parent standalone main — NO nested orchestrator spawn.
5. Evidencia obligatoria en ~/.coord-ag-evidence/D3.3/
6. Si una lane termina sin PR URL, documentar causa exacta (file lock, gh auth, timeout, etc.)

=== Fase 0 — Pre-run gate ===
cd ~/umbral-agent-stack
git fetch origin main && git checkout main && git pull --ff-only origin main
git log -1 --oneline
git status --short --branch
# STOP si dirty — no spawn

mkdir -p ~/.coord-ag-evidence/D3.3
EV=~/.coord-ag-evidence/D3.3
echo "run_start=$(date -Iseconds)" | tee "$EV/run-meta.txt"
git log -1 --oneline | tee -a "$EV/run-meta.txt"

=== Fase 0b — Sync orchestrator (autorizado) ===
ORCH_REPO=openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator
ORCH_LIVE=~/.openclaw/workspace/skills/multi-agent-tournament-orchestrator
rsync -a "$ORCH_REPO/" "$ORCH_LIVE/"
test -f "$ORCH_LIVE/examples/d33-issue-445-sync-skills-adapters-spec.yaml" && echo D33_SPEC_LIVE_OK

=== Fase 1 — Ejecutar torneo ===
chmod +x scripts/vps/d3.3-tournament-run.sh
bash scripts/vps/d3.3-tournament-run.sh
# Timeout hasta 7200s — no interrumpir salvo crash gateway

=== Fase 2 — Monitoreo (cada 15–30 min hasta fin) ===
cat "$EV/session.txt"
grep -iE 'sessions_spawn|lane|pr_url|incomplete|error|announce' "$EV/openclaw-agent.log" | tail -100 | tee "$EV/monitor-$(date +%H%M).txt"
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament" --state open --json number,title,url,headRefName | tee "$EV/open-prs.json"

=== Fase 3 — Collect phase (OBLIGATORIO antes de veredicto) ===
grep -oE 'https://github.com/Umbral-Bot/umbral-agent-stack/pull/[0-9]+' "$EV/openclaw-agent.log" | sort -u > "$EV/pr-urls-from-log.txt"
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament:445" --state open --json url --jq '.[].url' >> "$EV/pr-urls-from-log.txt" 2>/dev/null || true
sort -u "$EV/pr-urls-from-log.txt" -o "$EV/pr-urls.txt"
PR_COUNT=$(wc -l < "$EV/pr-urls.txt" | tr -d ' ')
echo "pr_count=$PR_COUNT" | tee -a "$EV/run-meta.txt"

python3 - <<'PY' | tee "$EV/final-metrics.json"
import json, pathlib, re
ev = pathlib.Path.home() / ".coord-ag-evidence/D3.3"
log = (ev / "openclaw-agent.log").read_text(errors="replace") if (ev / "openclaw-agent.log").exists() else ""
prs_file = ev / "pr-urls.txt"
prs = [l.strip() for l in prs_file.read_text().splitlines() if l.strip()] if prs_file.exists() else []
if not prs:
    prs = sorted(set(re.findall(r"https://github.com/Umbral-Bot/umbral-agent-stack/pull/\d+", log)))
lanes = re.findall(r"lane[-_](sync-delivery|sync-qa|backup-impl|backup-qa)", log, re.I)
print(json.dumps({
  "tournament": "D3.3",
  "issue": 445,
  "head_at_run": open(ev / "run-meta.txt").read().splitlines()[1] if (ev / "run-meta.txt").exists() else None,
  "pr_urls": prs,
  "pr_count": len(prs),
  "lanes_expected": 2,
  "lanes_mentioned": sorted(set(lanes)),
  "yielded": "yielded=true" in log.lower(),
  "spawn_count": len(re.findall(r"sessions_spawn", log, re.I)),
}, indent=2))
PY

=== Fase 4 — Comentario issue (obligatorio) ===
gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body-file "$EV/final-metrics.json"

=== Fase 5 — Worktree report ===
git status --short --branch
git branch -a | grep -i tournament || echo NO_TOURNAMENT_BRANCHES

=== Fase 6 — Actualizar task 020 log ===
# Append VEREDICTO + pr_urls to .agents/tasks/2026-06-02-020-d3.3-tournament-sync-skills-adapters.md
# NO commit en VPS salvo David lo pida — reportar diff al final

=== Veredicto (elegir uno) ===
M1_D33_TOURNAMENT_OK      → pr_count=2, spawn x2 evidenciado, ambos PR [tournament:...]
M1_D33_TOURNAMENT_PARTIAL → spawn OK pero pr_count<2 (causa por lane obligatoria)
M1_D33_TOURNAMENT_BLOCKED → crash pre-spawn o worktree corrupto

NO merge winner. Esperar Prompt 2 (Copilot Windows) + autorización David.
Incluir en respuesta: pr_urls.txt completo, final-metrics.json, tail 30 líneas openclaw-agent.log
```

---

## PROMPT 2 — Copilot Windows · Thread AC · judge + merge winner

**Pegar después del torneo, cuando existan ≥2 PRs tournament:**

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

=== Fase 1 — PRs torneo ===
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament" --state open --json number,title,url,headRefName,statusCheckRollup,additions,deletions,mergeStateStatus

# Validar cada PR candidata:
# gh pr view <N> --repo Umbral-Bot/umbral-agent-stack --json title,body,files,statusCheckRollup,mergeStateStatus

=== Fase 2 — Rubric (spec d33) ===
Leer:
  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d33-issue-445-sync-skills-adapters-spec.yaml

Tabla comparativa (1–5 por criterio A–E del spec):
| PR | A acceptance | B CI-safe | C diff mín | D no creep | E checks | TOTAL |
Publicar tabla en comentario #445 ANTES de merge.

=== Fase 3 — Diff review (obligatorio) ===
gh pr diff <N1> --repo Umbral-Bot/umbral-agent-stack --color=never | Out-File "$env:TEMP\d33-pr-N1.diff" -Encoding utf8
gh pr diff <N2> --repo Umbral-Bot/umbral-agent-stack --color=never | Out-File "$env:TEMP\d33-pr-N2.diff" -Encoding utf8

Revisar solo: scripts/sync_skills* tests/fixtures docs/ops/sync-skills-adapters-runbook.md
RECHAZAR merge si toca: .env, openclaw.json, VPS secrets, bulk umbral-skills-registry

=== Fase 4 — Tests local (obligatorio) ===
python -m pytest tests/ -k sync_skills -q
# Si falla → NO merge; gh issue comment 445 con traceback

=== Fase 5 — Merge winner ===
gh pr view <WINNER> --repo Umbral-Bot/umbral-agent-stack --json mergeStateStatus,statusCheckRollup
# Solo si mergeStateStatus=CLEAN y checks SUCCESS:
gh pr merge <WINNER> --repo Umbral-Bot/umbral-agent-stack --squash --delete-branch

git fetch origin main
git pull --ff-only origin main
git log -1 --oneline

=== Fase 6 — Cierre ===
gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body "Winner: PR #<WINNER>. Loser: PR #<LOSER> (kept). HEAD: $(git log -1 --oneline)"

VEREDICTO: D33_WINNER_MERGED
Incluir: winner URL, squash SHA, loser URL, rubric table summary
```

---

## PROMPT 3 — Copilot-VPS · Thread AD · post-merge D3.3

**Pegar después de `D33_WINNER_MERGED`:**

```
Sos Copilot-VPS. Post-merge D3.3 winner/salvage.

cd ~/umbral-agent-stack
git fetch origin main && git checkout main && git pull --ff-only origin main
git log -1 --oneline
git log --oneline -8 | grep -iE '445|#445' || git log --grep='#445' -3 --oneline
git status --short --branch

test -f docs/ops/sync-skills-adapters-runbook.md && echo RUNBOOK_OK || echo RUNBOOK_MISSING
python3 -m pytest tests/ -k sync_skills -q

# Evidencia torneo intacta:
ls -la ~/.coord-ag-evidence/D3.3/ | head -20

HEAD debe incluir squash winner #445 (no quedar solo en 6f560d6b / 2fe58535).
NO borrar ~/.coord-ag-evidence/D3.3/

VEREDICTO: D33_VPS_POST_MERGE_OK | D33_VPS_POST_MERGE_BLOCKED
```

---

## PROMPT 4 — Copilot Windows · Thread AF · D4.1 Mission Control (paralelo)

```
Sos Copilot Windows. D4.1 Mission Control — retomar PR scaffold O13.1.

cd C:\GitHub\umbral-agent-stack
git fetch origin
git checkout main
git pull --ff-only origin main
git branch -a | findstr mission-control

git fetch origin copilot/feat-mission-control-o13-1:copilot/feat-mission-control-o13-1 2>$null
git checkout copilot/feat-mission-control-o13-1
git rebase origin/main
# Conflictos mínimos; NO scope creep fuera O13.1

python -m pytest tests/ -k mission -q 2>$null
if ($LASTEXITCODE -ne 0) { python -m pytest tests/ -q --co | findstr mission }

gh pr list --repo Umbral-Bot/umbral-agent-stack --head copilot/feat-mission-control-o13-1 --json number,state,url,statusCheckRollup
# Crear PR si no existe con test plan explícito

Entregable: PR URL + count tests mission + 5 bullets diff summary

VEREDICTO: D41_MISSION_CONTROL_PR_READY | D41_MISSION_CONTROL_PR_BLOCKED
```

---

## PROMPT 5 — Copilot-VPS · Thread AG · D5.3 Granola soak (paralelo)

```
Sos Copilot-VPS. D5.3 Granola soak — READ-ONLY. NO restart worker salvo gate G-D0 explícito.

cd ~/umbral-agent-stack && git pull --ff-only origin main

EV=~/.coord-ag-evidence/D5.3
mkdir -p "$EV"
LOG="$EV/granola-soak-$(date +%Y%m%d%H%M).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== poller ==="
systemctl --user status notion-poller 2>/dev/null | head -15 || pgrep -af notion-poller

echo "=== worker 24h ==="
journalctl --user -u umbral-worker --since "24 hours ago" --no-pager 2>/dev/null | grep -iE 'granola|classify|error|truncate' | tail -30 || true

echo "=== dispatcher 24h ==="
journalctl --user -u openclaw-dispatcher --since "24 hours ago" --no-pager 2>/dev/null | tail -20 || true

echo "=== redis cursor prefix ==="
redis-cli GET notion:poll:cursor 2>/dev/null | head -c 80; echo

echo "=== ops_log granola ==="
grep -i granola ~/.config/umbral/ops_log.jsonl 2>/dev/null | tail -10 || true

Tabla final: componente | alive | último evento | errores 24h | truncamiento evidenciado

VEREDICTO: D53_GRANOLA_SOAK_OK | D53_GRANOLA_SOAK_DEGRADED | D53_GRANOLA_SOAK_BLOCKED
Log: $LOG
```

---

## Archivo — Threads W / AA (cerrados)

| Hilo | VEREDICTO | Notas |
|---|---|---|
| W cleanup D3.2 | `D32_WORKTREE_CLEANUP_NOOP_OK` | Nada que limpiar |
| AA preflight D3.3 | `D33_PREFLIGHT_OK` | OK=8 FAIL=0 WARN=2; evidencia `~/.coord-ag-evidence/D3.3/` |

---

## Archivo — D3.2 (cerrado)

| Hilo | VEREDICTO |
|---|---|
| preflight | D32_PREFLIGHT_OK |
| torneo | M1_D32_TOURNAMENT_PARTIAL |
| salvage | D32_ISSUE440_MERGED @ 2fe58535 |
| VPS post-merge | D32_VPS_POST_MERGE_OK |

---

## Próximo foco Q2

| Prioridad | Spine | Secuencia |
|---|---|---|
| 1 | **D3.3** | **AB** → AC → AD |
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
