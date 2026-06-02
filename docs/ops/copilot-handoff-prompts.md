# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**

Last updated: 2026-06-02 — D4.1 BLOCKED · D5.3 DEGRADED

---

## Prompts listos para enviar (orden)

| # | Agente | Estado |
|---|---|---|
| D3 + D3.4 | ✅ | retro `d3-tournament-retro-2026-06-02.md` |
| D4.1 | 🟡 | `D41_MISSION_CONTROL_PR_BLOCKED` — ver **PROMPT 4b** |
| D5.3 | 🟡 | `D53_GRANOLA_SOAK_DEGRADED` — ver notas abajo |
| **4b** | 🔴 **SIGUIENTE** | Copilot Windows — cherry-pick O13.1 + PR |
| #447 | ⏸ | cerrar PR loser |

Retro doc: [`d3-tournament-retro-2026-06-02.md`](d3-tournament-retro-2026-06-02.md)

---

## Estado activo

| Hilo | Superficie | Estado | Siguiente |
|---|---|---|---|
| **W** | Copilot-VPS | ✅ | `D32_WORKTREE_CLEANUP_NOOP_OK` |
| **AA** | Copilot-VPS | ✅ | `D33_PREFLIGHT_OK` |
| **AB** | Copilot-VPS | ✅ | `M1_D33_TOURNAMENT_PARTIAL` → rescate + judge |
| **1c** | Copilot-VPS | ✅ | PR #447 rescate delivery |
| **AC** | Copilot Windows | ✅ | `D33_WINNER_MERGED` #446 @ `da8eba85` |
| **AD** | Copilot-VPS | ✅ | `D33_VPS_POST_MERGE_OK` @ `fce55518` |
| **D4.1** | VPS probe | 🟡 | rebase conflict; sin PR |
| **D5.3** | VPS soak | 🟡 | `D53_GRANOLA_SOAK_DEGRADED` |

**HEAD:** `da8eba85` (`feat: ... (#446)`). **#447** OPEN (loser kept). Issue #445: cerrar tras AD + opcional close issue.

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

## PROMPT 1b — Copilot-VPS · AB continuación (Fase 2→6) con `/goal` 🔴

**Pegar cuando hay ≥1 PR o el watcher esté cerca del deadline:**

```
/goal Terminar torneo D3.3 issue #445: cerrar Fase 2 (monitoreo), ejecutar Fases 3–6 y emitir VEREDICTO final en español. No reiniciar torneo. No merge winner. No tocar ~/.config/openclaw/env ni reiniciar gateway.

Responde SIEMPRE en español.

Contexto actual (no contradecir sin verificar):
- Parent yielded OK; lanes: good-cloud (rick-delivery), quick-lagoon (rick-qa).
- PR abierto conocido: #446 (lane sync-qa) — confirmar con gh.
- Delivery: commits locales en rama tournament/.../lane-sync-delivery; push/PR aún pendiente o bloqueado.
- Evidencia: ~/.coord-ag-evidence/D3.3/ (watch.txt, openclaw-agent.log, session.txt).

=== Fase 2 — Cierre monitoreo (máx 20 min adicionales) ===
EV=~/.coord-ag-evidence/D3.3
TID=umbral-agent-stack-445-d5f34a07

# Si el watcher bash sigue vivo: esperar BOTH_PRS_PRESENT o LANES_IDLE_BREAK o 20 min; luego documentar watch_end en watch.txt.
# Paralelo cada 3 min (no matar watcher sin necesidad):
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament:$TID" --state open --json number,title,url,headRefName | tee "$EV/open-prs-snapshot.json"

# Diagnóstico delivery (read-only, NO impersonar la lane con push salvo evidencia de que la sesión terminó y solo falta reporte):
tail -c 8000 /home/rick/.openclaw/agents/rick-delivery/sessions/a054b56a-db12-423b-ac41-68436bcd73ec.jsonl | tr ',' '\n' | grep -iE 'push|pr create|fatal|error|rejected|gh auth|compact|lane-sync-delivery' | tail -25 | tee "$EV/delivery-lane-tail.txt"
git ls-remote --heads origin 'refs/heads/tournament/*445*' | tee "$EV/remote-445-branches.txt"
stat -c '%y %n' /home/rick/.openclaw/agents/rick-delivery/sessions/a054b56a-db12-423b-ac41-68436bcd73ec.jsonl /home/rick/.openclaw/agents/rick-qa/sessions/6f3b9126-dd2c-420e-84bf-31e55887f775.jsonl | tee -a "$EV/lane-mtime.txt"

Criterio para pasar a Fase 3:
- pr_count >= 2, O
- watcher terminó (LANES_IDLE_BREAK / BOTH_PRS_PRESENT), O
- 20 min sin actividad lane (mtime jsonl >20 min) con pr_count < 2

=== Fase 3 — Collect (OBLIGATORIO) ===
cd ~/umbral-agent-stack
# Restaurar main solo ahora (lanes ya terminaron o están idle):
git checkout main 2>/dev/null || true
git pull --ff-only origin main

grep -oE 'https://github.com/Umbral-Bot/umbral-agent-stack/pull/[0-9]+' "$EV/openclaw-agent.log" | sort -u > "$EV/pr-urls-from-log.txt"
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament:$TID" --state open --json url --jq '.[].url' >> "$EV/pr-urls-from-log.txt" 2>/dev/null || true
gh pr list --repo Umbral-Bot/umbral-agent-stack --search "tournament" --state open --json number,title,url,headRefName >> "$EV/open-prs-final.json"
sort -u "$EV/pr-urls-from-log.txt" -o "$EV/pr-urls.txt"
PR_COUNT=$(wc -l < "$EV/pr-urls.txt" | tr -d ' ')
echo "pr_count=$PR_COUNT" | tee -a "$EV/run-meta.txt"

python3 - <<'PY' | tee "$EV/final-metrics.json"
import json, pathlib, re
ev = pathlib.Path.home() / ".coord-ag-evidence/D3.3"
log = (ev / "openclaw-agent.log").read_text(errors="replace") if (ev / "openclaw-agent.log").exists() else ""
prs = [l.strip() for l in (ev/"pr-urls.txt").read_text().splitlines() if l.strip()] if (ev/"pr-urls.txt").exists() else []
print(json.dumps({
  "tournament": "D3.3", "issue": 445,
  "pr_urls": prs, "pr_count": len(prs), "lanes_expected": 2,
  "lanes": {"sync-qa": "PR #446 si existe en pr_urls", "sync-delivery": "ver delivery-lane-tail.txt + remote branches"},
  "yielded": "yielded=true" in log.lower(),
  "spawn_count": len(re.findall(r"sessions_spawn", log, re.I)),
  "delivery_blocked_hypothesis": "leer delivery-lane-tail.txt",
}, indent=2, ensure_ascii=False))
PY

=== Fase 4 — Comentario issue 445 (OBLIGATORIO) ===
gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body-file "$EV/final-metrics.json"

=== Fase 5 — Worktree + task log ===
git status --short --branch | tee "$EV/worktree-final.txt"
git branch -a | grep -i tournament | tee "$EV/branches-final.txt" || true
# Append resumen a .agents/tasks/2026-06-02-020-d3.3-tournament-sync-skills-adapters.md (Log Copilot-VPS) — NO commit salvo David lo pida

=== Fase 6 — VEREDICTO (español, una sola línea + tabla) ===
M1_D33_TOURNAMENT_OK      → solo si pr_count=2 y ambos títulos contienen [tournament:...]
M1_D33_TOURNAMENT_PARTIAL → si pr_count<2 (tabla obligatoria: lane | branch remota | PR URL | causa)
M1_D33_TOURNAMENT_BLOCKED → solo si no hubo spawn o evidencia corrupta

Entregable final en español:
1) VEREDICTO
2) Tabla lanes (qa vs delivery)
3) pr-urls.txt
4) Rutas evidencia en D3.3
5) Siguiente paso para David (merge winner vs salvage vs esperar delivery)

NO merge. NO segundo torneo.
```

---

## PROMPT 1c — Copilot-VPS · rescate lane delivery (push + PR) 🔴

**Requiere:** `autorizo rescate lane delivery D3.3`

**Objetivo:** convertir commit local `9741e7c` en PR tournament sin re-ejecutar torneo.

```
/goal Rescatar lane sync-delivery del torneo D3.3: push rama local + gh pr create con título [tournament:...] y reportar URL. Responder en español. NO merge. NO segundo torneo. NO tocar gateway/env.

autorizo rescate lane delivery D3.3

Sos Copilot-VPS. Salvage operativo post M1_D33_TOURNAMENT_PARTIAL.

=== Fase 0 — Verificar rama local ===
cd ~/umbral-agent-stack
git fetch origin main
git checkout tournament/umbral-agent-stack-445-d5f34a07/lane-sync-delivery 2>/dev/null || git branch -a | grep lane-sync-delivery
git log -1 --oneline
git status --short
# Esperado: commit 9741e7c o similar "feat: add codex and cursor skill sync adapters"
ls -la scripts/sync_skills_adapters.py tests/test_sync_skills_adapters.py docs/ops/sync-skills-adapters-runbook.md 2>/dev/null | tee ~/.coord-ag-evidence/D3.3/rescue-file-check.txt

=== Fase 1 — Push (solo esta rama) ===
BRANCH=tournament/umbral-agent-stack-445-d5f34a07/lane-sync-delivery
git push -u origin "$BRANCH" 2>&1 | tee ~/.coord-ag-evidence/D3.3/rescue-push.log
git ls-remote --heads origin "$BRANCH" | tee ~/.coord-ag-evidence/D3.3/rescue-remote-head.txt

=== Fase 2 — PR create ===
gh pr create --repo Umbral-Bot/umbral-agent-stack \
  --head "$BRANCH" \
  --base main \
  --title "[tournament:umbral-agent-stack-445-d5f34a07:sync-delivery] O3 sync_skills adapters (rescate lane delivery)" \
  --body "Salvage post M1_D33_TOURNAMENT_PARTIAL. Lane delivery commiteo local antes de compactacion; push+PR manual autorizado por David. Competidor vs PR #446 (sync-qa). Closes #445 solo si David mergea este PR como winner." \
  2>&1 | tee ~/.coord-ag-evidence/D3.3/rescue-pr-create.log

# Capturar URL:
grep -oE 'https://github.com/Umbral-Bot/umbral-agent-stack/pull/[0-9]+' ~/.coord-ag-evidence/D3.3/rescue-pr-create.log | tee ~/.coord-ag-evidence/D3.3/rescue-pr-url.txt

=== Fase 3 — Actualizar métricas issue ===
EV=~/.coord-ag-evidence/D3.3
{ echo "## Rescate lane delivery D3.3"; cat "$EV/rescue-pr-url.txt" 2>/dev/null; echo ""; gh pr view $(basename $(cat "$EV/rescue-pr-url.txt") | sed 's|.*/||') --repo Umbral-Bot/umbral-agent-stack --json number,url,title 2>/dev/null; } > "$EV/issue-445-rescue-comment.md"
gh issue comment 445 --repo Umbral-Bot/umbral-agent-stack --body-file "$EV/issue-445-rescue-comment.md"

=== Fase 4 — Restaurar main ===
git checkout main
git pull --ff-only origin main
git status --short --branch

VEREDICTO: D33_DELIVERY_LANE_RESCUED | D33_DELIVERY_LANE_RESCUE_BLOCKED
Incluir: PR URL nueva, push log, si pytest local pasa en la rama antes de push (opcional: python3 -m pytest tests/ -k sync_skills -q)
```

---

## PROMPT 2 — Copilot Windows · Thread AC · judge + merge winner

**Requiere:** PR #446 + PR rescate delivery (1c) + `autorizo merge winner D3.3`

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

## PROMPT 2b — Copilot Windows · merge solo #446 (atajo, sin rescate delivery)

**Solo si David NO quiere rescate delivery y acepta cerrar #445 con una sola entrega:**

```
autorizo merge winner D3.3 solo PR 446

Sos Copilot Windows. Judge único PR #446 (sync-qa) y merge si cumple rubric d33.

cd C:\GitHub\umbral-agent-stack && git pull --ff-only origin main
gh pr view 446 --repo Umbral-Bot/umbral-agent-stack --json mergeStateStatus,statusCheckRollup,title,files
gh pr diff 446 --repo Umbral-Bot/umbral-agent-stack --color=never
python -m pytest tests/ -k sync_skills -q

Si CLEAN + checks OK → gh pr merge 446 --squash --delete-branch
gh issue comment 445 --body "Winner único: PR #446. Lane delivery quedó NO_PR (commit local 9741e7c no mergeado)."

VEREDICTO: D33_WINNER_MERGED_SINGLE_PR | D33_MERGE_446_BLOCKED
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

**Resultado VPS 2026-06-02:** `D41_MISSION_CONTROL_PR_BLOCKED` — rebase conflict `.gitignore` + `pyproject.toml`; rama remota stale; **sin PR**; tests mission **35 passed** en rama pre-rebase (.venv).

---

## PROMPT 4b — Copilot Windows · D4.1 desbloqueo (cherry-pick) 🔴

**No rebasear la rama entera** (cientos de commits ya en main). Cherry-pick solo el scaffold O13.1.

```
/goal Crear PR Mission Control O13.1 desde main limpio: cherry-pick commit scaffold, resolver solo conflictos en pyproject.toml y .gitignore, pytest mission verde, abrir PR. Responder en español.

Sos Copilot Windows. D4.1 desbloqueo tras D41_MISSION_CONTROL_PR_BLOCKED.

=== Contexto ===
- Rama remota stale: copilot/feat-mission-control-o13-1 @ e1d2bc38
- Commit scaffold O13.1: 3f150c46 feat(mission_control): O13.1 scaffold FastAPI + 5 endpoints + HTMX dashboard
- VPS: rebase origin/main → conflict .gitignore + pyproject.toml; sin PR
- VPS tests en rama vieja: 35 passed (-k mission) con .venv

=== Fase 0 — main limpio ===
cd C:\GitHub\umbral-agent-stack
git fetch origin
git checkout main
git pull --ff-only origin main
git status --short --branch

=== Fase 1 — Rama fresca (preferido) ===
git checkout -b copilot/feat-mission-control-o13-1-rebase main
git cherry-pick 3f150c46
# Si conflictos: resolver MÍNIMO en pyproject.toml + .gitignore (mantener deps/tests mission_control de 3f150c46 + main actual)
# NO traer commits de seguridad/env antiguos de la rama vieja

=== Fase 2 — Tests ===
.\.venv\Scripts\python.exe -m pytest tests/ -k mission -q
# Debe pasar (~35 tests). Si falla → documentar y NO abrir PR

=== Fase 3 — Push + PR ===
git push -u origin copilot/feat-mission-control-o13-1-rebase
gh pr create --repo Umbral-Bot/umbral-agent-stack \
  --head copilot/feat-mission-control-o13-1-rebase \
  --base main \
  --title "feat(mission_control): O13.1 scaffold FastAPI read-only dashboard" \
  --body "D4.1 O13.1. Cherry-pick 3f150c46 onto current main (stale branch rebase blocked). FastAPI :8089 read-only. Test plan: pytest -k mission. NO deploy VPS in this PR."

=== Fase 4 — Veredicto ===
VEREDICTO: D41_MISSION_CONTROL_PR_READY | D41_MISSION_CONTROL_PR_BLOCKED
Incluir: PR URL, conflictos resueltos (si hubo), pytest summary, archivos mission_control tocados
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

**Resultado VPS 2026-06-02:** `D53_GRANOLA_SOAK_DEGRADED`

| Componente | Hallazgo |
|---|---|
| notion-poller | Proceso vivo desde May 24; **unit systemd inactive/not-found** |
| redis cursor | **vacío** |
| ops_log Granola | **0 eventos** Jun 01–02; último visible Apr 24 |
| worker/dispatcher | activos; sin truncamiento Granola 24h |

**No reiniciar** sin `autorizo restart worker G-D0` o runbook poller explícito. Evidencia: `~/.coord-ag-evidence/D5.3/granola-soak-*.log`

---

## Archivo — Torneo D3.3 AB (cerrado PARTIAL)

| Campo | Valor |
|---|---|
| VEREDICTO | `M1_D33_TOURNAMENT_PARTIAL` |
| pr_count | 1 — [#446](https://github.com/Umbral-Bot/umbral-agent-stack/pull/446) sync-qa |
| delivery | commit `9741e7c` local, sin push |
| watch | `LANES_IDLE_BREAK prs=1` @ 11:34:45 |
| issue comment | [#445#issuecomment-4604044479](https://github.com/Umbral-Bot/umbral-agent-stack/issues/445#issuecomment-4604044479) |

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
| 1 | **D4.1** | Mission Control PR (AF) |
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
