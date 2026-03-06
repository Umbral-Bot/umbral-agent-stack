# Quick Wins auditoría — 3 clones y tareas

Para ejecutar en paralelo los quick wins con 3 agentes Codex (GPT-5.4), usar esta asignación en esta máquina.

| Carpeta (clone) | Rama | Tarea | Archivo de tarea |
|-----------------|------|-------|------------------|
| `c:\GitHub\umbral-agent-stack` | `codex/audit-qw-worker` | **102** — Worker (QW-1, QW-2, QW-3, QW-5 worker, QW-6) | `.agents/tasks/2026-03-07-102-r21-codex-audit-qw-worker.md` |
| `c:\GitHub\umbral-agent-stack-config` | `codex/audit-qw-config` | **103** — Config (.env.example, scripts Bitácora) | `.agents/tasks/2026-03-07-103-r21-codex-audit-qw-config.md` |
| `c:\GitHub\umbral-agent-stack-dispatcher` | `codex/audit-qw-dispatcher` | **104** — Dispatcher (task_queued on retry) | `.agents/tasks/2026-03-07-104-r21-codex-audit-qw-dispatcher.md` |

**Uso:** Abrir cada carpeta en Codex (o en una ventana distinta), asegurarse de que el clone esté en la rama indicada (`git branch`), y dar al agente la tarea del archivo correspondiente (o el contenido de ese archivo como prompt).

**Orden de merge sugerido:** PR config (103) → PR dispatcher (104) → PR worker (102).
