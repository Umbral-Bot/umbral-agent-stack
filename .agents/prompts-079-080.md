# Prompts para Codex (079) y GitHub Copilot (080)

Usa estos textos tal cual al asignar la tarea. Así el agente se ciñe al encargo y no amplía el alcance.

---

## Para Codex — Tarea 079

```
Tarea única: sigue EXACTAMENTE el archivo .agents/tasks/2026-03-05-079-r16-merge-final-main-ci.md.

Haz SOLO esto, en este orden:
1. Mergear en main el PR de integración (#80 o #82), o si no es posible, mergear #71, #70, #69, #73 en ese orden. Resolver conflictos si los hay.
2. Ejecutar pip install -e ".[test]" y pytest tests/ -q hasta 0 failed.
3. Comprobar que existe .github/workflows/ con un job que corre pytest en push/PR.
4. Commit/push solo de los cambios de merge o del workflow si faltaba.

NO refactorices, NO añadas tests ni dependencias nuevas, NO cambies código de aplicación. Solo merge + verificación + CI.
```

---

## Para GitHub Copilot — Tarea 080

```
Tarea única: sigue EXACTAMENTE el archivo .agents/tasks/2026-03-05-080-r16-limpieza-prs-docs.md.

Haz SOLO esto:
1. Si los PRs #69, #70, #71, #73 ya están incluidos en main, cerrarlos con comentario "Incluido en PR #XX mergeado a main".
2. En README: añadir o completar sección "Ejecutar tests" (pip install -e ".[test]", pytest tests/) y mención al CI y al board (.agents/board.md).
3. Si existe CONTRIBUTING.md, añadir 2-3 líneas (branch desde main, tests antes de PR, board). Si no existe, un párrafo en README basta.
4. Actualizar .agents/board.md con el estado de tareas 077-080 (marcar completadas si aplica).

NO crees workflows nuevos, NO toques código de la app, NO añadas features. Solo PRs + README/CONTRIBUTING + board.
```
