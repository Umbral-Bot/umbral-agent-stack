# Prompt R19 — Codex: Tarea 097 (supervisor Notion)

Copia y pega todo el bloque siguiente a Codex. Las instrucciones de Git van siempre primero.

---

## Para Codex — Copiar desde aquí

```
TAREA 097 — Supervisor Notion alert: JSON seguro + NOTION_SUPERVISOR_ALERT_PAGE_ID.

=== INSTRUCCIONES GIT (OBLIGATORIAS) ===
1. Antes de cualquier cambio: git fetch origin && git checkout main && git pull origin main
2. Crear tu rama: git checkout -b codex/097-supervisor-notion-mejoras
3. Trabaja SOLO en la rama codex/097-supervisor-notion-mejoras. No hagas merge a main ni a otras ramas.
4. Al terminar: commit, git push origin codex/097-supervisor-notion-mejoras, y abre un PR a main. No mergees el PR tú mismo.

=== TAREA ===
Sigue el archivo .agents/tasks/2026-03-07-097-r19-codex-supervisor-notion-mejoras.md

Resumen de lo que debes hacer:
1. En scripts/vps/supervisor.sh: añadir una función (ej. post_notion_alert()) que construya el payload JSON del aviso a Notion de forma segura (evitar que saltos de línea o comillas rompan el JSON). Si existe NOTION_SUPERVISOR_ALERT_PAGE_ID, pasar "page_id" en el input de notion.add_comment; si no, el Worker usará NOTION_CONTROL_ROOM_PAGE_ID. Reemplazar el bloque actual del curl del alert por la llamada a esa función.
2. En docs/62-operational-runbook.md: en la tabla de variables de entorno, añadir NOTION_SUPERVISOR_ALERT_PAGE_ID (opcional), descripción: page ID donde el supervisor postea el aviso; si no se define, se usa NOTION_CONTROL_ROOM_PAGE_ID.
3. Abrir PR a main con título: fix(R19-097): supervisor Notion alert — JSON seguro y NOTION_SUPERVISOR_ALERT_PAGE_ID.

No cambies la lógica de reinicio (check_worker, restart_worker, etc.). Solo el envío del alert a Notion.
```

---

## Recordatorio para próximas tareas

En cada prompt para Codex (o cualquier agente) incluir siempre al inicio:

- **Pull:** `git fetch origin && git checkout main && git pull origin main` antes de crear la rama.
- **Rama:** Crear y usar solo la rama indicada (ej. `codex/097-supervisor-notion-mejoras`).
- **Merge:** No hacer merge a main por su cuenta; solo push de la rama y abrir PR.
- **PR:** Abrir PR a main; el merge lo hace un humano o se indica explícitamente.
