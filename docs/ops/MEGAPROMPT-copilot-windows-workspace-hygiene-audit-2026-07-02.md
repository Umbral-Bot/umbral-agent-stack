MEGAPROMPT — Copilot Windows · Auditoría workspace UAS (multi-IDE, multi-clone, multi-hilo)
Versión: UAS-WORKSPACE-HYGIENE-v1 · 2026-07-02
Modo: diagnóstico + propuesta · NO destructivo sin gate David
Clone canónico Windows Copilot: C:\GitHub\umbral-agent-stack-copilot

================================================================================
ROL
================================================================================
Sos GitHub Copilot Windows en la workstation de David. Ejecutás una auditoría
**completa** del caos operativo de umbral-agent-stack: clones locales Windows,
hilos Cursor/Copilot/Claude/Codex, ramas, deudas, y propuesta de orden canónico.

NO borrás clones, NO archivás hilos, NO mergeás PRs, NO tocás VPS en esta pasada
(solo generás el MEGAPROMPT VPS como entregable Pass 10).

================================================================================
CONTEXTO INMEDIATO (no perder)
================================================================================
- Graphify piloto cerró: GO_PARTIAL S7/R6 — PR abierto, sin merge, G-GR-1 pendiente David
- Rick voz MVP: capitalización pendiente (task 2026-07-02-004)
- Notion MCP audit: task 2026-07-02-005 (hilo paralelo)
- Azure oai-umbral-agents-prod creado para UAS/Rick
- Protocolo: .agents/PROTOCOL.md — Cursor lead; Copilot-VPS requiere push main antes handoff

================================================================================
PREFLIGHT (Pass 0 — bloqueante)
================================================================================
cd C:\GitHub\umbral-agent-stack-copilot
git remote get-url origin
git fetch origin main
git status -sb
git checkout main
git pull --ff-only origin main
git checkout -b copilot/workspace-hygiene-audit-2026-07-02

Leer:
- .agents/PROTOCOL.md
- .agents/board.md
- docs/ops/sprint-2026-07-02-prompts-index.md
- AGENTS.md

================================================================================
PASS 1 — Inventario clones Windows (evidencia)
================================================================================
Ejecutar y capturar salida en docs/audits/workspace-hygiene-2026-07-02/01-clones-windows.md:

```powershell
Get-ChildItem C:\GitHub -Directory |
  Where-Object { $_.Name -match 'umbral-agent' } |
  ForEach-Object {
    $p = $_.FullName
    $remote = git -C $p remote get-url origin 2>$null
    $branch = git -C $p branch --show-current 2>$null
    $head = git -C $p log -1 --oneline 2>$null
    $dirty = (git -C $p status --porcelain 2>$null | Measure-Object -Line).Lines
    $behind = git -C $p rev-list --count HEAD..origin/main 2>$null
    $ahead = git -C $p rev-list --count origin/main..HEAD 2>$null
    [PSCustomObject]@{
      Clone=$_.Name; Path=$p; Branch=$branch; Dirty=$dirty
      BehindMain=$behind; AheadMain=$ahead; HEAD=$head; Remote=$remote
    }
  } | Format-Table -AutoSize
```

Por cada clone clasificar:
- **KEEP** (canónico o activo)
- **ARCHIVE** (worktree histórico, mergeable o obsoleto)
- **RESCUE** (tiene cambios únicos no en main — listar paths)
- **DELETE-CANDIDATE** (duplicado limpio, 0 valor)

Clones conocidos hoy (verificar, no asumir):
umbral-agent-stack, umbral-agent-stack-copilot, umbral-agent-stack-codex-coordinador,
umbral-agent-stack-codex, umbral-agent-stack-claude, umbral-agent-stack-antigravity,
umbral-agent-stack-copilot-fresh, umbral-agent-stack-config, pit-* variants, cand001-v31, etc.

================================================================================
PASS 2 — Hilos Cursor (evidencia + recomendación)
================================================================================
Fuentes a inspeccionar:
- C:\Users\david\.cursor\projects\ — carpetas *umbral-agent*, *notion-governance*
- agent-transcripts si accesibles (solo títulos/metadata, no volcar secretos)
- .agents/tasks/ + board — qué hilos tienen task activa
- docs/ops/*MEGAPROMPT* — hilos con prompt formal

Construir docs/audits/workspace-hygiene-2026-07-02/02-cursor-threads.md:

| Hilo/tema | Estado inferido | Task/PR | Recomendación |
|-----------|-----------------|---------|---------------|
| Graphify F1–F2 Cursor | done local | 2026-07-02-002 | ARCHIVAR tras G-GR-1 |
| Rick voz capitalización | assigned cursor | 2026-07-02-004 | MANTENER activo |
| Notion MCP audit | assigned codex | 2026-07-02-005 | MANTENER (hilo paralelo) |
| CAND-001 closeout | done | 2026-07-02-001 | ARCHIVAR |
| … | | | |

Regla: **MANTENER** = tiene task assigned/in_progress o PR abierto sin merge.
**ARCHIVAR** = done/blocked >14 días o superseded por board.

================================================================================
PASS 3 — Hilos GitHub Copilot Windows
================================================================================
Fuentes:
- docs/ops/copilot-handoff-prompts.md (tabla hilos GR, RV, NM, históricos D*)
- .agents/tasks/*copilot*
- Ramas copilot/* locales en clones
- PRs abiertos: gh pr list --repo Umbral-Bot/umbral-agent-stack --state open

docs/audits/workspace-hygiene-2026-07-02/03-copilot-windows-threads.md

Incluir hilo Graphify F3–F4:
- Veredicto GO_PARTIAL — PR abierto — NO merge hasta G-GR-1 David
- Recomendación hilo: MANTENER hasta merge PR o cierre explícito

================================================================================
PASS 4 — Hilos Claude Code
================================================================================
Fuentes:
- Clone umbral-agent-stack-claude (rama, dirty, HEAD vs main)
- .claude/commands/ en repo
- .agents/tasks con assigned_to: claude o ramas claude/*
- gh pr list --author ... --head claude/

docs/audits/workspace-hygiene-2026-07-02/04-claude-threads.md

================================================================================
PASS 5 — Hilos Codex / Antigravity / otros
================================================================================
Clones: umbral-agent-stack-codex, codex-coordinador, antigravity, pit-*

docs/audits/workspace-hygiene-2026-07-02/05-other-agents-threads.md

Identificar duplicación codex-coordinador vs codex vs base.

================================================================================
PASS 6 — Extracción método de trabajo (síntesis)
================================================================================
docs/audits/workspace-hygiene-2026-07-02/06-working-method.md

Responder:
1. ¿Cuál es el flujo real hoy? (board → MEGAPROMPT → clone → rama → PR → merge)
2. ¿Qué funciona bien? (artefactos concretos: PROTOCOL, board, MEGAPROMPT, tasks)
3. ¿Qué falla? (clone equivocado, docs solo local, hilos zombie, push main olvidado)
4. ¿Conviene skill/agent custom por IDE+IA?

Tabla propuesta:

| IDE + IA | Rol canónico | Skill/agent custom? | Qué debe leer al inicio |
|----------|--------------|----------------------|-------------------------|
| Cursor | Lead/orquestador | ¿cursor rule + skill? | board, PROTOCOL |
| Copilot Windows | Azure + PR merge + piloto local | ¿copilot-instructions? | board, MEGAPROMPT |
| Copilot VPS | Runtime SSH | openclaw-vps-operator | task + git pull main |
| Codex | Deep debug / synthesis | umbral-repo-codex | board, task |
| Claude Code | Feature branches | .claude/commands | mailbox si aplica |
| Antigravity | Research | — | board |

Recomendar SOLO skills/agents con ROI claro — no proliferar.

================================================================================
PASS 7 — Deudas técnicas y estratégicas
================================================================================
docs/audits/workspace-hygiene-2026-07-02/07-debt-register.md

**Técnica:** clones sucios, ramas stale, docs sin push, graphify runbooks=0 nodos,
Notion REST vs MCP gap (task 006), tests CI billing, etc.

**Estratégica:** demasiados clones PIT históricos, falta clone canónico documentado,
Graphify GO_PARTIAL (no skill), Rick voz no capitalizado en repo, cutover Azure umbral-bot.

Priorizar: P0 / P1 / P2 con owner agente sugerido.

================================================================================
PASS 8 — Rescate desde clones obsoletos
================================================================================
Por cada clone ARCHIVE/RESCUE:
- git diff origin/main --stat (top 20 archivos si dirty o ahead)
- ¿Hay docs/ops, .agents/tasks, scripts únicos no en main?

docs/audits/workspace-hygiene-2026-07-02/08-rescue-candidates.md

Lista accionable: "cherry-pick / copiar manual / descartar" — NO ejecutar rescate.

================================================================================
PASS 9 — Modelo canónico propuesto (Windows + GitHub)
================================================================================
docs/audits/workspace-hygiene-2026-07-02/09-canonical-model.md

Propuesta mínima (David firma G-WH-1):

| Superficie | Clone canónico | Ramas | Hilos activos máx |
|------------|----------------|-------|-------------------|
| Cursor lead | umbral-agent-stack-copilot O umbral-agent-stack | cursor/* | 2 |
| Copilot Windows | umbral-agent-stack-copilot | copilot/* | 2 |
| Codex | umbral-agent-stack-codex-coordinador | codex/* | 2 |
| Claude | umbral-agent-stack-claude | claude/* | 1 |
| Antigravity | umbral-agent-stack-antigravity | antigravity/* | 1 |
| Archivo | pit-*, cand001-v31, *-fresh | — | 0 (congelar) |

Incluir tabla **hilos activos vs archivar** por IDE (entregable principal David).

================================================================================
PASS 10 — Generar MEGAPROMPT VPS (no ejecutar)
================================================================================
Escribir docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt

Debe incluir preflight SSH:
```bash
cd ~/umbral-agent-stack   # verificar si es el único checkout
find ~ -maxdepth 3 -type d -name 'umbral-agent-stack*' 2>/dev/null
git remote -v && git branch -a && git status -sb
git fetch origin main && git log -1 --oneline origin/main
```

Auditar clones VPS sueltos, rama rick/vps vs main, OpenClaw workspaces,
systemd/crons — proponer UN checkout canónico ~/umbral-agent-stack.

NO ejecutar en VPS desde Windows — solo entregar prompt para David pegar en Copilot-VPS.

================================================================================
PASS 11 — Consolidación y PR
================================================================================
Índice maestro: docs/audits/workspace-hygiene-2026-07-02/README.md

Actualizar:
- .agents/tasks/2026-07-02-006-workspace-hygiene-audit.md (Log)
- .agents/board.md

PR: copilot/workspace-hygiene-audit-2026-07-02
Solo docs audit + task/board — NO merge sin David.

Veredicto:
WORKSPACE_HYGIENE_AUDIT_READY | clones_windows=N | rescue=N | hilos_activos=N | canonical_proposed=YES

================================================================================
PROHIBIDO
================================================================================
- rm -rf clones / git clean -fdx sin autorización
- Merge PR Graphify u otros
- Archivar hilos en IDE (solo recomendar)
- Tocar VPS runtime
- Secretos en docs
