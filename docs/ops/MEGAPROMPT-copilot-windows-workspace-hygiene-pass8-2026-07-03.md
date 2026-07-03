MEGAPROMPT — Copilot Windows · Workspace Hygiene Pass 8 + cierre task 006
Versión: UAS-WORKSPACE-HYGIENE-PASS8-v1 · 2026-07-03
Modo: rescates + PRs + limpieza ramas locales · NO archivado físico sin G-WH-2
Clone canónico: C:\GitHub\umbral-agent-stack-copilot
Hilo: **continuación del mismo hilo WH** (task 2026-07-02-006)

================================================================================
CONTEXTO (ya ejecutado por Cursor — NO repetir)
================================================================================
- PR #496 MERGED → audit docs + sprint rescue en main @ 164000c8+
- PR #495 MERGED → Graphify GO_PARTIAL S7/R6, G-GR-1 firmado, task 002 → done
- G-WH-1 FIRMADO por David 2026-07-03 (modelo canónico Pass 9 aprobado)
- Push remoto: origin/codex/cand-prod001-stage2 incluye a85563b8 (stage3)
- MEGAPROMPT VPS listo: docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt
  → David lo pegará en Copilot-VPS cuando Pass 8 Windows cierre

Referencias obligatorias:
- docs/audits/workspace-hygiene-2026-07-02/README.md
- docs/audits/workspace-hygiene-2026-07-02/08-rescue-candidates.md
- docs/audits/workspace-hygiene-2026-07-02/09-canonical-model.md
- .agents/tasks/2026-07-02-006-workspace-hygiene-audit.md

================================================================================
ROL
================================================================================
Sos GitHub Copilot Windows (merge master UAS). Ejecutás Pass 8: rescates desde
clones obsoletos, PRs a main, limpieza de ramas locales en -copilot, y cierre
task 006. NO movés clones a _archive (eso es Fase A post-rescates, gate G-WH-2
a 30 días). NO ejecutás VPS en esta pasada.

================================================================================
PREFLIGHT (bloqueante)
================================================================================
cd C:\GitHub\umbral-agent-stack-copilot
git remote get-url origin    # Umbral-Bot/umbral-agent-stack.git
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline         # debe ser >= merge #495
test-path docs/audits/workspace-hygiene-2026-07-02/09-canonical-model.md
test-path .graphifyignore

Si falta audit o graphifyignore → STOP y reportar a Cursor.

================================================================================
PASS 8A — Rescate clone base (umbral-agent-stack)
================================================================================
Material: stash local `pre-rescue-pass8` + untracked en C:\GitHub\umbral-agent-stack
(ver 08-rescue-candidates.md §1). Commit a85563b8 ya en origin/codex/cand-prod001-stage2.

```powershell
cd C:\GitHub\umbral-agent-stack-copilot
git checkout -b cursor/rescue-base-clone-2026-07 origin/main

# Aplicar stash del base (si existe)
git -C C:\GitHub\umbral-agent-stack stash list
# Si hay stash@{0} pre-rescue-pass8:
git -C C:\GitHub\umbral-agent-stack stash show -p "stash@{0}" | git apply --index 2>$null
# Copiar untracked manualmente (si no están en stash):
$src = "C:\GitHub\umbral-agent-stack"
$dst = "C:\GitHub\umbral-agent-stack-copilot"
@(
  "config/editorial-model.yaml",
  "docs/adr/ADR-009-linkedin-company-api.md",
  "docs/audits/foundry-gpt-5.5-audit-20260606.md",
  "docs/audits/openclaw-gpt-5.5-alias-activation-20260606.md",
  "docs/audits/openclaw-gpt-5.5-promotion-20260607.md",
  "scripts/editorial",
  "evals/editorial",
  "prompts/rick/blog-copy-system.md",
  "prompts/rick/x-copy-system.md",
  "tests/test_editorial_production.py"
) | ForEach-Object {
  if (Test-Path "$src\$_") { Copy-Item -Recurse -Force "$src\$_" "$dst\$_" -ErrorAction SilentlyContinue }
}

# NO incluir: .agents/board.md, .claude/settings.local.json (stale locales)
git status --short
git diff --stat
```

Revisar diff editorial/OpenClaw overrides contra VPS Reality Check (solo reportar drift;
no push VPS). Commitear material válido, push, abrir PR:

Título: `ops(editorial): rescue base clone dirty state 2026-07`
Body: referencia task 006 Pass 8, lista archivos, exclusiones.

================================================================================
PASS 8B — Rescate coordinador (umbral-agent-stack-codex-coordinador)
================================================================================
```powershell
cd C:\GitHub\umbral-agent-stack-copilot
git checkout -b codex/rescue-editorial-contracts-2026-07 origin/main

$src = "C:\GitHub\umbral-agent-stack-codex-coordinador"
$dst = "C:\GitHub\umbral-agent-stack-copilot"
@(
  "docs/ops/editorial-linkedin-quality-smoke-tests.md",
  "docs/ops/editorial-publicaciones-human-review-contract.md",
  "docs/ops/editorial-agent-flow.md",
  "evals/editorial/gold-set-minimum.yaml",
  "openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md",
  "openclaw/workspace-agent-overrides/rick-qa/ROLE.md",
  "openclaw/workspace-templates/skills/director-comunicacion-umbral/CALIBRATION.md",
  "openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md",
  "openclaw/workspace-templates/skills/linkedin-content/SKILL.md",
  "openclaw/workspace-templates/skills/linkedin-david/SKILL.md"
) | ForEach-Object {
  $dir = Split-Path "$dst\$_" -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Copy-Item -Force "$src\$_" "$dst\$_"
}
# NO copiar: *.png, .playwright-mcp/, scripts/export-vscode-config.ps1

git add -A
git status --short
```

PR separado: `ops(editorial): rescue coordinador contracts + linkedin calibrations`

================================================================================
PASS 8C — Verificaciones únicas (read-only, log en task 006)
================================================================================
1. cand001-v31: revisar `?? _patch_blog_prompt.py` → descartar si one-shot
2. stunning-fiesta worktree: `git cherry origin/main HEAD` → reportar +/- 
3. umbral-agent-stack-codex: copiar solo `docs/audits/granola-*.md` si no en main
4. umbral-agent-stack-config: `git log --oneline origin/main..main -- docs/ | head`

Registrar resultados en Log de task 006 (sin commits si todo descartable).

================================================================================
PASS 8D — Limpieza ramas locales en -copilot (post-PRs)
================================================================================
```powershell
cd C:\GitHub\umbral-agent-stack-copilot
git checkout main && git pull --ff-only origin main
git branch --merged main | Where-Object { $_ -notmatch 'main' }
# Borrar solo ramas merged y upstream gone (NO borrar copilot/* activas sin merge)
git fetch --prune
```

Listar ramas eliminadas en Log task 006.

================================================================================
PASS 8E — Cierre task 006 + board
================================================================================
Actualizar:
- `.agents/tasks/2026-07-02-006-workspace-hygiene-audit.md` → status `done`
- `.agents/board.md` → 006 done; 002 done; enlazar PRs Pass 8
- `docs/audits/workspace-hygiene-2026-07-02/README.md` → veredicto final
- `docs/audits/workspace-hygiene-2026-07-02/07-debt-register.md` → marcar P0-2, P1-1 resueltos si PRs mergeados

PR de cierre (rama `copilot/workspace-hygiene-pass8-closeout`):
solo task/board/README/debt updates — sin código editorial si ya en PRs 8A/8B.

================================================================================
GATES PENDIENTES (reportar a David, NO ejecutar sin firma)
================================================================================
| Gate | Acción |
|------|--------|
| G-WH-2 | Borrado definitivo clones archivados (30 días) |
| PR #480 | PIT v2 — merge o cierre |
| PRs zombi mayo | #421 #418 #413 #389 #379 — cerrar con comentario |
| Archivado Fase A | Move-Item 11 clones → C:\GitHub\_archive\uas\ + WHY.md |
| VPS handoff | David pega MEGAPROMPT VPS en hilo Copilot-VPS |

================================================================================
PROHIBICIONES
================================================================================
- NO commitear graphify-out/
- NO mergear sin CI verde (vos sos merge master — mergeá tus PRs Pass 8 tras green)
- NO borrar clones físicos (solo ramas git locales merged)
- NO restart VPS / NO touch openclaw-gateway
- NO usar umbralbim-resource (producto web)

================================================================================
RESPUESTA ESPERADA
================================================================================
```
WORKSPACE_HYGIENE_PASS8_DONE |
  rescue_base_pr=# |
  rescue_coord_pr=# |
  closeout_pr=# |
  verifications=OK |
  vps_megaprompt_ready=YES |
  pending_gates=G-WH-2,#480,zombis,Fase-A
```
