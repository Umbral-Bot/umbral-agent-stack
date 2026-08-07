# P1 — F8A DISCARD (2026-08-07)

> **GO de David (verbatim):** "GO F8A DISCARD ademas quizas hay que revisar en la vps
> si hay residuos… pero por ahora GO F8A DISCARD"
> **Ejecutor:** Cursor (orquestador) · post [uas-p1-hygiene-closeout-20260807.md](uas-p1-hygiene-closeout-20260807.md)

## 1. Qué bloqueaba

Worktree `C:\Users\david\.codex\worktrees\f8a-prompt-quoting-fix` tenía la rama `main`
del repo `-codex-coordinador`, con **1 archivo staged** sin commit:

- `.agents/tasks/2026-05-08-001-copilot-vps-wave1_5-integration.md` (+371)
- Ahead/behind enorme = historias disjuntas (mismo patrón P1.2), no trabajo útil pendiente

Por eso Clone B quedó detached en el closeout.

## 2. Acciones

1. `git restore --staged .` + `git restore .` + `git clean -fd` en el worktree f8a
2. `git worktree remove` del path f8a (+ `prune`) — path ya no existe
3. En `C:\GitHub\umbral-agent-stack-codex-coordinador`: `checkout main` + `reset --hard origin/main`
4. Sync de `-copilot` a `origin/main` (mismo tip)

## 3. Post-check [E]

| Clone | Branch | HEAD | status |
|---|---|---|---|
| `-copilot` | `main` | `1379830c` (= `origin/main`) | limpio |
| `-codex-coordinador` | `main` | `1379830c` (= `origin/main`) | limpio |

`Test-Path` f8a → False. Origin heads sin cambio: `main` + `rick/stage7_5-multiformat`.

## 4. Fuera de alcance (explícito)

- Higiene VPS / residuos remotos — diferido por David ("por ahora")
- Worktrees KEEP restantes y 15 stashes KEEP — sin tocar
- `stage7_5` KEEP_INDEFINITE — sin tocar
