# Pass 6 — Método de trabajo: síntesis y propuesta

## 1. ¿Cuál es el flujo real hoy?

```
David decide → Cursor (lead) redacta MEGAPROMPT + task file → sprint index
  → David pega prompt en la superficie (Copilot Windows / Copilot-VPS / Codex / Claude)
  → agente: preflight clone → rama {agente}/* → trabajo → PR → veredicto TOKEN_OK
  → David firma gates (G-*) → merge → (si runtime) handoff Copilot-VPS con push main previo
```

Evidencia: `sprint-2026-07-02-prompts-index.md`, `copilot-handoff-prompts.md`, PROTOCOL § Handoffs, este mismo audit.

## 2. Qué funciona bien (conservar)

| Artefacto | Valor probado |
|---|---|
| **MEGAPROMPT por hilo** con preflight explícito y PROHIBIDO | reproducible, audit trail, evita scope creep |
| **Task files `.agents/tasks/` + board** | trazabilidad y handoffs entre superficies |
| **Gates G-\* firmados por David** | control humano en puntos irreversibles (merge, VPS, delete) |
| **Veredictos-token** (`*_OK`, `GO_PARTIAL`) | estado parseable de un vistazo |
| **PROTOCOL § push main antes de handoff VPS** | cuando se cumple, elimina el STOP `TASK_FILE_MISSING` |
| Skills `.agents/skills/` (vps-deploy, execution-split, secret-guard) | codifican reglas duras por superficie |

## 3. Qué falla (causas del caos actual)

| Falla | Evidencia | Efecto |
|---|---|---|
| **Docs solo en working tree** (ni commit ni push) | 27 archivos sprint 2026-07-02 en `-copilot`; 58 en base; 16 en coordinador | handoffs rotos, riesgo pérdida total, VPS ciego |
| **Clone nuevo por tarea** en vez de rama/worktree | 6 clones pit-* en un día (jun-22) + fresh + p2c | 17 clones, 90% muertos |
| **Clone equivocado / secuestrado** | base (lead Cursor) quedó en rama `codex/*` con dirty desde jun-06 | el lead pierde su superficie limpia |
| **IDs de task duplicados** | `2026-07-02-001/002` significan cosas distintas en base vs `-copilot` | ambigüedad en handoffs |
| **`main` local stale** en casi todos los clones | audit: hasta 1438 behind; incluso `-copilot` estaba 3 behind | preflights parten de estado viejo |
| **PRs zombi** | 6 de 8 PRs abiertos son de mayo | ruido en la cola de decisión |
| **Board stale en main** | header 2026-06-04/R23; lo actualizado vive en ramas sin merge | board deja de ser fuente de verdad |

## 4. ¿Conviene skill/agent custom por IDE+IA?

Solo donde hay ROI claro y regla dura repetida. Propuesta mínima (NO proliferar):

| IDE + IA | Rol canónico | Skill/agent custom | Qué debe leer al inicio |
|---|---|---|---|
| **Cursor** | Lead / orquestador / tasks+board | **SÍ (nuevo, 1)**: rule `uas-lead-preflight` — obliga `git pull main` + board + "commit+push antes de cerrar hilo" | `board.md`, PROTOCOL, sprint index |
| **Copilot Windows** | Azure/Foundry, PR ops, pilotos locales | **YA EXISTE** (`copilot-instructions.md` + skills `windows-vps-execution-split`, `openclaw-foundry-activation`) — añadir 1 línea: clone canónico `-copilot` | board, MEGAPROMPT del hilo |
| **Copilot VPS** | Runtime SSH OpenClaw/Worker | **YA EXISTE** (`openclaw-vps-operator`, `vps-deploy-after-edit`) — suficiente | task + `git pull --ff-only main` |
| **Codex** | Deep debug / synthesis / PIT | **NO nuevo** — usar mismo preflight de MEGAPROMPT; el problema fue disciplina de commit, no falta de skill | board, task |
| **Claude Code** | Feature branches puntuales | **YA EXISTE** (`.claude/commands/`) — suficiente | mailbox/task si aplica |
| **Antigravity** | Research esporádico | **NO** — congelado hasta reactivación | board |

**Regla nueva más rentable (no-skill, protocolo):** *"Ningún hilo se declara done sin `git push` de sus artefactos y SHA anotado en el task Log"* — ya está en PROTOCOL para VPS; extenderla a TODA superficie. Cero código, mata la falla #1.

## 5. Cadencia de higiene propuesta

- **Por hilo:** al cerrar → push + task Log + recomendación archivar hilo IDE.
- **Semanal (Cursor lead):** revisar `gh pr list` (cerrar zombis), `git -C <clones-KEEP> status` (detectar dirty), board refresh.
- **Mensual:** re-correr Pass 1 (script en este audit) y comparar contra tabla canónica.
