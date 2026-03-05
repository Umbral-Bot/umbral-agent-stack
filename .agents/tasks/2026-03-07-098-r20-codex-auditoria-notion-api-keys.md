# Task R20 — Auditoría de variables Notion (API keys y page/DB IDs) — Codex

**Fecha:** 2026-03-07  
**Ronda:** 20  
**Agente:** Codex  
**Rama:** `codex/098-auditoria-notion-keys` — trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar código:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/098-auditoria-notion-keys`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/098-auditoria-notion-keys`, abrir PR a main. No mergear el PR tú mismo.

---

## Objetivo

Hay varias variables de entorno relacionadas con Notion en el repo y en los `.env` (NOTION_API_KEY, NOTION_API_KEY_RICK, NOTION_SUPERVISOR_API_KEY, NOTION_DASHBOARD_PAGE_ID, NOTION_CONTROL_ROOM_PAGE_ID, NOTION_SUPERVISOR_ALERT_PAGE_ID, NOTION_TASKS_DB_ID, NOTION_GRANOLA_DB_ID, NOTION_BITACORA_DB_ID, etc.). El objetivo es **auditar para qué se usa cada una** y proponer una simplificación: en principio deberíamos tener solo **Rick** (una key para Worker, poller, dashboard, Control Room) y **Supervisor** (key + page para avisos de reinicio). Detectar si algo se nos escapa o si hay redundancia/legacy.

---

## Tareas

1. **Inventario:** Buscar en todo el repo (worker/, scripts/, dispatcher/, docs/, .env.example, runbooks) todas las variables que empiecen por `NOTION_` (API keys, page IDs, database IDs). Listar cada una.

2. **Uso por variable:** Para cada variable, indicar:
   - En qué archivo(s) se usa (y si se lee de `os.environ` / `config`).
   - Qué funcionalidad depende de ella (ej. "Worker notion.add_comment", "supervisor.sh alert", "dashboard_report_vps.py", "enrich_bitacora_pages.py").
   - Si es una **API key** (token de integración) o un **ID** (página/DB).

3. **Documento de auditoría:** Crear `docs/auditoria-notion-env-vars.md` con:
   - Tabla: variable | tipo (key / page_id / db_id) | dónde se usa | rol (Rick / Supervisor / otro)
   - Sección "Recomendación": qué mantener como Rick, qué como Supervisor, y cuáles son opcionales o legacy (ej. NOTION_API_KEY_RICK si no se usa en código).
   - Si alguna key está duplicada o puede unificarse, indicarlo.

4. **Solo documentación:** No cambiar código ni .env.example en esta tarea. Solo el archivo `docs/auditoria-notion-env-vars.md` y, si aplica, una línea en el runbook o README que enlace a esa auditoría.

5. **PR:** Abrir PR a main desde `codex/098-auditoria-notion-keys`. Título: `docs(R20-098): auditoría variables Notion — uso por key y recomendación Rick/Supervisor`.

---

## Criterios de éxito

- [ ] `docs/auditoria-notion-env-vars.md` existe con inventario completo y recomendación de simplificación.
- [ ] Queda claro cuáles son las dos identidades objetivo (Rick, Supervisor) y qué variables corresponden a cada una.
- [ ] PR abierto a main.

---

## Restricciones

- No modificar worker/config.py ni scripts ni .env.example. Solo crear el doc de auditoría (y enlace si se desea).
