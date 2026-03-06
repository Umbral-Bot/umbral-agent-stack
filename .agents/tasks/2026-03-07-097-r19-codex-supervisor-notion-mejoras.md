# Task R19 — Supervisor Notion alert: JSON seguro + NOTION_SUPERVISOR_ALERT_PAGE_ID (Codex)

**Fecha:** 2026-03-07  
**Ronda:** 19  
**Agente:** Codex  
**Rama:** `codex/097-supervisor-notion-mejoras` — trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar código:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/097-supervisor-notion-mejoras`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/097-supervisor-notion-mejoras`, abrir PR a main. No mergear el PR tú mismo salvo que se te indique.

---

## Objetivo

Mejorar el envío del aviso a Notion en `scripts/vps/supervisor.sh`: payload JSON seguro (evitar que saltos de línea rompan el request) y soporte opcional para `NOTION_SUPERVISOR_ALERT_PAGE_ID`.

---

## Contexto

- El supervisor ya llama a **POST /run** (en main). Si reinicia Worker o Dispatcher, hace un `curl` con el mensaje en el body. Si el texto tiene saltos de línea o comillas, el JSON puede romperse.
- El Worker acepta `notion.add_comment` con `input: { "text": "...", "page_id": "..." }`. `page_id` es opcional; si no se envía, usa `NOTION_CONTROL_ROOM_PAGE_ID`.

---

## Tareas

1. **En `scripts/vps/supervisor.sh`:**
   - Añadir una función (p. ej. `post_notion_alert()`) que:
     - Construya el payload JSON de forma segura (p. ej. escapar el texto para JSON o usar un método que no rompa con saltos de línea/comillas).
     - Use `NOTION_SUPERVISOR_ALERT_PAGE_ID` si está definida; si no, el Worker usará su default (Control Room).
   - Si usas `page_id` en el input, pasar `page_id` solo cuando `NOTION_SUPERVISOR_ALERT_PAGE_ID` esté definida.
   - Reemplazar el bloque actual del `curl` que envía el alert por una llamada a esa función.

2. **En `docs/62-operational-runbook.md`:**
   - En la tabla de variables de entorno (sección 1.4), añadir si no está: `NOTION_SUPERVISOR_ALERT_PAGE_ID` (opcional). Descripción: "Page ID donde el supervisor postea el aviso de reinicio; si no se define, se usa NOTION_CONTROL_ROOM_PAGE_ID."

3. **PR:** Un único PR desde `codex/097-supervisor-notion-mejoras` a main. Título: `fix(R19-097): supervisor Notion alert — JSON seguro y NOTION_SUPERVISOR_ALERT_PAGE_ID`.

---

## Criterios de éxito

- [ ] `supervisor.sh` usa una función que construye el JSON del alert de forma segura.
- [ ] Soporte opcional para `NOTION_SUPERVISOR_ALERT_PAGE_ID` documentado y usado en el script.
- [ ] Runbook actualizado con la nueva variable.
- [ ] PR abierto a main; no mergear sin indicación.

---

## Restricciones

- No cambiar la lógica de reinicio (check_worker, restart_worker, check_dispatcher, etc.). Solo el bloque de envío del alert a Notion.
- No hacer merge a main ni eliminar ramas. Solo push de tu rama y abrir PR.
