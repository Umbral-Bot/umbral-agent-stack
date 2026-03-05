# Task R13 — Cursor Cloud: Poblar Bitácora Umbral Agent Stack

**Fecha:** 2026-03-04  
**Ronda:** 13  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/bitacora-populate`

---

## Contexto

Se creó una base de datos en Notion llamada **Bitácora — Umbral Agent Stack** para documentar la evolución del proyecto desde su inicio. La página tiene permisos configurados.

**URL:** https://www.notion.so/umbralbim/85f89758684744fb9f14076e7ba0930e  
**Database ID:** `85f89758684744fb9f14076e7ba0930e`

**Estructura de la base de datos:**
- **Título** (Title) — Resumen breve del evento
- **Fecha** (Date) — Cuándo ocurrió
- **Ronda** (Select) — Pre-R11, R11, R12, R13, Hackathon, Ad-hoc
- **Tipo** (Select) — Hito, PR mergeado, Decisión de diseño, Tarea creada, Documentación, Skill creado, Bug fix, Otro
- **Detalle** (Rich text) — Descripción ampliada
- **Referencia** (URL) — Link a PR, archivo, documento
- **Agente** (Select) — Cursor, Codex, Copilot, Claude, Antigravity, Cloud1-5, Manual
- **Estado** (Select) — Completado, En curso, Bloqueado, Pendiente

---

## Objetivo

Usar el skill de Notion y las credenciales existentes para poblar la Bitácora con la historia del proyecto. El agente debe implementar la capacidad de escribir en esta base de datos y luego ejecutar el poblamiento inicial.

---

## Tareas requeridas

### 1. Añadir task `notion.append_bitacora` al Worker

Crear handler que inserte una fila en la base de datos Bitácora.

**Archivos:**
- `worker/config.py` — añadir `NOTION_BITACORA_DB_ID: str | None = os.environ.get("NOTION_BITACORA_DB_ID")`
- `worker/notion_client.py` — función `append_bitacora(database_id, titulo, fecha, ronda, tipo, detalle, referencia, agente, estado)`
- `worker/tasks/notion.py` — `handle_notion_append_bitacora`
- `worker/tasks/__init__.py` — registrar `"notion.append_bitacora"`
- `.env.example` — `NOTION_BITACORA_DB_ID=85f89758684744fb9f14076e7ba0930e`

**Input del handler:**
```json
{
  "titulo": "R12 mergeada — 8 PRs",
  "fecha": "2026-03-04",
  "ronda": "R12",
  "tipo": "Hito",
  "detalle": "Merge de 8 PRs: Granola, document generation, 45 skills...",
  "referencia": "https://github.com/Umbral-Bot/umbral-agent-stack/pulls?q=is%3Apr+is%3Amerged",
  "agente": "Manual",
  "estado": "Completado"
}
```

**Notion API:** `POST /v1/pages` con `parent: { database_id }` y properties mapeadas a los nombres exactos de las columnas (Título, Fecha, Ronda, Tipo, Detalle, Referencia, Agente, Estado).

---

### 2. Actualizar skill Notion

En `openclaw/workspace-templates/skills/notion/SKILL.md`, añadir sección:

### 7. Añadir entrada a Bitácora

Task: `notion.append_bitacora`

```json
{
  "titulo": "Resumen del evento",
  "fecha": "2026-03-04",
  "ronda": "R12",
  "tipo": "Hito",
  "detalle": "Descripción detallada...",
  "referencia": "https://...",
  "agente": "Cursor",
  "estado": "Completado"
}
```

---

### 3. Script `scripts/populate_bitacora.py`

Script que lee la historia del proyecto y llama a `notion.append_bitacora` (vía Worker o directamente a Notion API si el Worker no está disponible).

**Fuentes de datos:**
- `.agents/board.md` — rondas, logros
- `.agents/tasks/*.md` — tareas creadas por ronda
- `gh pr list --state merged` (opcional) — PRs mergeados
- Datos conocidos: Hackathon R1-R2, R3-R7, R8-R11, R12, R13

**Lógica:** Generar lista de entradas (titulo, fecha, ronda, tipo, detalle, referencia, agente) y por cada una llamar al Worker con `notion.append_bitacora` o a la API de Notion.

**Uso:**
```bash
NOTION_BITACORA_DB_ID=85f89758684744fb9f14076e7ba0930e \
NOTION_API_KEY=... \
WORKER_URL=http://localhost:8088 WORKER_TOKEN=... \
python scripts/populate_bitacora.py
```

Modo `--dry-run`: imprimir entradas sin escribir.

---

### 4. Entradas iniciales a incluir (mínimo)

| Título | Ronda | Tipo | Agente |
|--------|-------|------|--------|
| Hackathon base — Diagnóstico y arranque | Hackathon | Hito | Cursor |
| Multi-LLM Worker + Model Router | R6 | PR mergeado | Codex, Copilot |
| Langfuse Tracing + OODA | R7 | PR mergeado | Codex, Copilot |
| Linear webhooks + Provider Health | R8 | PR mergeado | Codex, Antigravity |
| OpenClaw skills — Figma, Notion, Windows | R9 | Skill creado | Cursor Cloud, Codex |
| Skills BIM, Cloud, Content, Document generation | R11 | Skill creado | Cloud1-8 |
| Pipeline Granola + Google Cal/Gmail (task) | R12 | Tarea creada | Cloud7, Cloud1 |
| Bitácora — Poblamiento inicial | R13 | Documentación | Cursor Cloud |

El script debe inferir más entradas desde `.agents/tasks/` y `board.md`.

---

### 5. Tests

- `tests/test_notion_bitacora.py` — test del handler con mock de httpx
- Test de `populate_bitacora.py --dry-run` que verifique que genera N entradas

---

## Variables de entorno

En la VPS / entorno donde corre el Worker:
```bash
NOTION_BITACORA_DB_ID=85f89758684744fb9f14076e7ba0930e
NOTION_API_KEY=...  # ya existe
```

---

## Criterios de éxito

- [ ] Task `notion.append_bitacora` implementado y registrado
- [ ] Skill Notion actualizado con la nueva task
- [ ] `scripts/populate_bitacora.py` implementado
- [ ] Ejecutar `populate_bitacora.py` (o --dry-run) y verificar salida
- [ ] Tests añadidos
- [ ] PR abierto a `main`
