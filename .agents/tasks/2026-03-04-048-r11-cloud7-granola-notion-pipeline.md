---
id: "048"
title: "Granola → Notion Pipeline: transcripciones, compromisos, proactividad de Rick"
assigned_to: cursor-agent-cloud-7
branch: feat/cloud7-granola-notion-pipeline
round: 11
status: done
created: 2026-03-04
---

## Objetivo

Investigar la mejor arquitectura para integrar Granola (app de transcripción instalada en la VM Windows) con Notion, Google Calendar, Gmail y el sistema de Rick. Proponer la solución óptima y crear un SKILL.md + implementar los handlers necesarios.

## Contexto del stack actual

**YA EXISTE** en el stack:
- `notion.write_transcript` — handler que crea una página en la Granola Inbox DB de Notion (`NOTION_TASKS_DB_ID`)
- `worker/tasks/notion_markdown.py` — convierte Markdown a bloques de Notion
- `windows.fs.read_text` — Rick puede leer archivos desde la VM
- `windows.fs.list` — Rick puede listar archivos en carpetas de la VM
- La página de Notion destino: `https://www.notion.so/umbralbim/dd181874b8944120a41fe1e0a98577b8`

**Granola** (https://granola.ai):
- Plan básico de David instalado en la VM Windows
- Exporta transcripciones en formato Markdown
- Carpeta de exportación típica: `C:\Users\<usuario>\Documents\Granola\` o similar
- NO tiene API pública documentada (verificar si plan básico tiene webhook/export automático)

## Parte 1: Investigación (OBLIGATORIA antes de implementar)

Investigar y documentar en `docs/50-granola-notion-pipeline.md`:

### 1a. Capacidades de Granola plan básico
- ¿Tiene export automático a carpeta local?
- ¿Formato de export? (markdown, txt, json)
- ¿Tiene webhook o API?
- ¿Puede exportar a Google Drive directamente?
- ¿Qué metadata incluye el export? (título reunión, fecha, participantes, action items)
- Fuentes: https://granola.ai/help + https://community.granola.ai + Reddit + AppSumo reviews

### 1b. Arquitecturas posibles — evaluar y recomendar UNA

| Opción | Descripción | Pros | Contras |
|--------|-------------|------|---------|
| A | VM detecta archivo nuevo → Rick lo lee con `windows.fs.read_text` → sube a Notion | Sin dependencias externas | Requiere polling o file watcher |
| B | VM exporta a Google Drive → Rick detecta vía Google Drive API → sube a Notion | Google Drive como buffer | Necesita Google Drive API |
| C | Granola webhook (si existe) → Dispatcher → Worker → Notion | Más elegante | Solo si Granola tiene webhook |
| D | Script en VM que monitorea carpeta → POST directo al Worker → Notion | Automático | Requiere script corriendo en VM |

**Recomendar la arquitectura más simple y robusta dado que:**
- David tiene Google Drive montado en `G:\Mi unidad\`
- La VM ya tiene el Worker corriendo
- Rick ya puede leer archivos de la VM con `windows.fs.read_text`

## Parte 2: Implementar el pipeline completo

### 2a. Watcher script en VM: `scripts/vm/granola_watcher.py`

Script que corre en la VM y monitorea la carpeta de exports de Granola:

```python
# Detecta archivos .md nuevos en carpeta Granola
# Llama al Worker: POST /run con task "notion.write_transcript"
# Marca el archivo como procesado (rename o move a /processed/)
```

Variables de entorno en VM:
```
GRANOLA_EXPORT_DIR=C:\Users\rick\Documents\Granola
WORKER_URL=http://127.0.0.1:8088
WORKER_TOKEN=<token>
```

### 2b. Nuevos handlers en Worker

#### `granola.process_transcript`

Handler completo que:
1. Recibe `{title, content, date, attendees, action_items}`
2. Sube la transcripción a Notion (página en la DB `NOTION_TASKS_DB_ID`)
3. Notifica a "Enlace" agregando comentario en la página creada: *"Transcripción lista para optimizar"*
4. Extrae `action_items` y los convierte en tareas Notion (usando `notion.upsert_task`)
5. Si `GOOGLE_CALENDAR_ID` está configurado, crea eventos de seguimiento

#### `granola.create_followup`

Handler que Rick usa de forma proactiva:
1. Recibe `{transcript_page_id, followup_type}`
2. `followup_type: "proposal"` → crea borrador Word/PDF con propuesta (usando python-docx)
3. `followup_type: "email_draft"` → guarda borrador en Gmail (via Gmail API)
4. `followup_type: "reminder"` → crea tarea en Notion con fecha límite

### 2c. Integración Google Calendar (opcional, si hay tiempo)

Si `GOOGLE_CALENDAR_CREDENTIALS` está configurado:
- Nuevo handler `calendar.create_event`: crea evento en Google Calendar desde action items de la reunión

### 2d. Skill OpenClaw: `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md`

Skill que le enseña a Rick cuándo y cómo usar el pipeline:
- Triggers: "reunión terminada", "subir transcripción", "procesar granola", "compromisos reunión"
- Procedimientos: cómo activar el pipeline, cómo pedir follow-up
- Proactividad: Rick revisa Notion, ve que hay transcripción sin follow-up → sugiere próximos pasos

## Parte 3: Documentación

Crear `docs/50-granola-notion-pipeline.md` con:
- Arquitectura recomendada (diagrama en Mermaid)
- Setup del watcher en VM
- Variables de entorno necesarias
- Flujo completo: Granola → VM → Worker → Notion → Enlace → Rick

## Variables de entorno a agregar

```
GRANOLA_EXPORT_DIR=C:\Users\rick\Documents\Granola    # carpeta de exports en VM
GRANOLA_PROCESSED_DIR=C:\Users\rick\Documents\Granola\processed
NOTION_GRANOLA_DB_ID=<id de la DB de transcripciones>   # ya existe como NOTION_TASKS_DB_ID
ENLACE_NOTION_USER_ID=<mention_id de Enlace en Notion>  # para notificaciones
GOOGLE_CALENDAR_ID=<id del calendario de David>          # opcional
```

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud7-granola-notion-pipeline

# 1. Investigar Granola (leer docs + web search)
# 2. Documentar en docs/50-granola-notion-pipeline.md
# 3. Crear scripts/vm/granola_watcher.py
# 4. Agregar handlers en worker/tasks/granola.py
# 5. Registrar en worker/tasks/__init__.py
# 6. Crear skill SKILL.md
# 7. Agregar vars a .env.example
# 8. Tests en tests/test_granola.py

python -m pytest tests/test_granola.py -v -p no:cacheprovider

git add .
git commit -m "feat: granola-notion pipeline — watcher, handlers, calendar, proactive followup"
git push -u origin feat/cloud7-granola-notion-pipeline
gh pr create \
  --title "feat: Granola → Notion pipeline con follow-up proactivo de Rick" \
  --body "Watcher VM + handlers granola.process_transcript + granola.create_followup + skill + docs"
```

## Criterio de éxito

- `docs/50-granola-notion-pipeline.md` documenta arquitectura elegida con justificación
- `scripts/vm/granola_watcher.py` funcional (monitorea carpeta, llama al Worker)
- `worker/tasks/granola.py` con al menos 2 handlers
- `skills/granola-pipeline/SKILL.md` válido
- Tests pasan
- Variables de entorno documentadas en `.env.example`

## Log

### [cursor-agent-cloud-7] 2026-03-04

**Investigación Granola:**
- Plan básico NO tiene API, webhook, ni export automático
- Cache local (cache-v3.json) ya no incluye transcripts completos desde Feb 2026
- Arquitectura recomendada: VM File Watcher (Opción A) — David copia notas a carpeta monitoreada

**Archivos creados:**
- `docs/50-granola-notion-pipeline.md` — investigación + arquitectura + setup
- `scripts/vm/granola_watcher.py` — file watcher con watchdog + fallback polling
- `worker/tasks/granola.py` — 2 handlers: `granola.process_transcript` + `granola.create_followup`
- `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md` — skill con triggers y proactividad
- `tests/test_granola.py` — 32 tests unitarios

**Archivos modificados:**
- `worker/tasks/__init__.py` — registrar 2 nuevos handlers
- `worker/config.py` — agregar `ENLACE_NOTION_USER_ID`
- `.env.example` — agregar variables Granola

**Tests:** 32/32 passed. Suite completa: 652 passed (49 pre-existentes fallan por rate limiting, sin relación).
