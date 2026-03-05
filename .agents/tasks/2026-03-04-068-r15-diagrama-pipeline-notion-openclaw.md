# Task R15 — Diagrama detallado del pipeline y publicación en Notion (OpenClaw)

**Fecha:** 2026-03-05  
**Ronda:** 15  
**Agente:** Cursor Agent Cloud / Code Claude  
**Branch:** `feat/diagrama-pipeline-notion-openclaw`

---

## Contexto

Se necesita un **diagrama del pipeline** del Umbral Agent Stack que sea **simple, minimal y contundente**, con los flujos y condicionantes claros. El diagrama debe publicarse al **final** de la página de Notion **OpenClaw**.

**Página destino:** https://www.notion.so/umbralbim/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca  
**Page ID:** `30c5f443fb5c80eeb721dc5727b20dca`

---

## Objetivo

1. Revisar el repositorio (al menos lo necesario) para entender al detalle flujos y arquitectura.
2. Crear un diagrama detallado del pipeline que incluya **condicionantes** (decisiones, ramas).
3. El diagrama debe ser **simple, minimal y contundente** (fácil de leer, sin ruido).
4. Añadir el diagrama **al final** del contenido de la página OpenClaw en Notion.

---

## Fuentes a revisar (mínimo)

- `docs/01-architecture-v2.3.md` — arquitectura y flujo de tarea
- `docs/00-overview.md` — visión general
- `docs/30-linear-notion-architecture.md` — Linear + Notion
- `docs/50-granola-notion-pipeline.md` — pipeline Granola
- `dispatcher/service.py` — loop principal: dequeue → model_router → worker (VPS o VM) → complete/fail
- `dispatcher/notion_poller.py` — Notion → clasificación → smart_reply / encolar
- `dispatcher/smart_reply.py` — handle_smart_reply, workflows, encolar tarea
- `dispatcher/router.py` — TeamRouter, VM vs VPS
- `dispatcher/model_router.py` — selección de modelo, cuotas, bloqueos
- `dispatcher/linear_webhook.py` — webhook Linear → encolar
- `worker/app.py` — POST /run, health, task history
- `openclaw/workspace-templates/TOOLS.md` — tareas disponibles
- `infra/diagrams/architecture.mmd` — diagrama existente (referencia)

---

## Condicionantes a reflejar en el diagrama

- **Origen de la tarea:** Notion (poller), Telegram/OpenClaw, Linear (webhook), cron/scheduled, Make/webhook.
- **Clasificación:** intent (pregunta vs tarea vs instrucción) → smart_reply (respuesta directa) vs encolar.
- **Encolado:** team, task_type → ModelRouter selecciona modelo (si es LLM) o no inyecta modelo.
- **Cuota:** si no hay cuota disponible → bloqueo o aprobación según política.
- **Worker destino:** `requires_vm` + VM online → Worker VM; si no → Worker VPS.
- **Ejecución:** Worker ejecuta task → éxito → Notion upsert, Linear notify, callback; fallo → retry o fail, alertas.
- **Pipelines laterales:** Granola watcher → Worker; RRSS (n8n); document generation; etc. (solo los que quepan sin saturar el diagrama).

El diagrama no tiene que incluir todo: priorizar el **flujo principal** (Notion/Telegram → Rick/Dispatcher → Redis → Worker → resultado) y 2–4 condicionantes clave (origen, VM sí/no, modelo/cuota, éxito/fallo).

---

## Formato del diagrama

- **Mermaid** (flowchart o graph) para que se pueda pegar en Notion (Notion soporta Mermaid en bloques de código).
- Títulos de nodos en español.
- Leyenda breve opcional debajo (1–3 líneas) si hace falta aclarar siglas.

---

## Tareas requeridas

1. **Revisar repo** — Leer las fuentes listadas (y las que consideres necesarias) y anotar flujo principal y condicionantes.

2. **Diseñar el diagrama** — Crear un archivo Mermaid (p. ej. `docs/diagrams/pipeline-umbral-openclaw.mmd` o `.md` con bloque mermaid) que contenga:
   - Flujo de punta a punta: entrada (Notion/Telegram/Linear) → clasificación → encolado → selección de modelo (si aplica) → selección de worker (VPS/VM) → ejecución → resultado y notificaciones.
   - Ramas/condiciones: por ejemplo “¿VM requerida y VM up?” → sí → Worker VM; no → Worker VPS. “¿Tarea LLM?” → ModelRouter. “¿Cuota ok?” → ejecutar / bloquear.

3. **Publicar en Notion** — Añadir al **final** de la página OpenClaw el diagrama:
   - Opción A: Usar la API de Notion para append de un bloque de tipo `code` con el contenido Mermaid (lenguaje `mermaid`) al page_id `30c5f443fb5c80eeb721dc5727b20dca`.
   - Opción B: Si ya existe task/handler para “añadir bloques a una página” (p. ej. notion.enrich_bitacora_page o similar), reutilizarlo pasando el page_id de OpenClaw y un bloque con el diagrama.
   - Requiere `NOTION_API_KEY` (y que la integración tenga acceso a esa página).

4. **Documentar** — En el PR, indicar la ruta del archivo del diagrama y que fue añadido al final de la página OpenClaw. Si el diagrama está en el repo, enlazar desde el README o desde `docs/01-architecture-v2.3.md` de forma opcional.

---

## Criterios de éxito

- [ ] Diagrama del pipeline creado (Mermaid), simple y contundente, con condicionantes claros.
- [ ] Diagrama añadido al final de la página Notion OpenClaw (page_id `30c5f443fb5c80eeb721dc5727b20dca`).
- [ ] Archivo del diagrama en el repo (p. ej. `docs/diagrams/pipeline-umbral-openclaw.mmd` o en un .md).
- [ ] PR abierto a `main`.
