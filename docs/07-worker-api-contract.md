# 07 — Worker API Contract

## Base URL

```
http://WINDOWS_TAILSCALE_IP:8088
```

## Autenticación

Todos los endpoints excepto `/health` requieren autenticación Bearer:

```
Authorization: Bearer <WORKER_TOKEN>
```

---

## Endpoints

### `GET /health`

Health check. No requiere autenticación.

**Response (200):**
```json
{
  "ok": true,
  "ts": 1740600000,
  "version": "0.4.0",
  "tasks_registered": ["ping", "notion.add_comment", "..."],
  "tasks_in_memory": 42
}
```

---

### `POST /run`

Ejecuta una tarea. Acepta dos formatos:

#### TaskEnvelope v0.1 (formato completo)

```json
{
  "schema_version": "0.1",
  "task_id": "uuid-generado",
  "team": "marketing",
  "task_type": "writing",
  "task": "notion.add_comment",
  "input": { "text": "Hola mundo" },
  "trace_id": "uuid-optional"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `schema_version` | string | ✅ | Siempre `"0.1"` |
| `task_id` | string | ✅ | UUID único para esta tarea |
| `team` | string | ✅ | Equipo destino (`marketing`, `advisory`, `improvement`, `lab`, `system`) |
| `task_type` | string | ✅ | Tipo de tarea (`general`, `research`, `writing`, `instruction`) |
| `task` | string | ✅ | Nombre del handler a ejecutar |
| `input` | object | ✅ | Datos de entrada para el handler |
| `trace_id` | string | — | UUID para correlación de trazas |
| `status` | string | — | Estado (`queued`, `running`, `done`, `failed`) |
| `callback_url` | string | — | Webhook opcional para callback al completar/fallar |

#### Legacy (backward compat)

```json
{
  "task": "ping",
  "input": {}
}
```

Se convierte internamente a TaskEnvelope con `task_id` generado, `team="system"`, `task_type="general"`.

**Response (200):**
```json
{
  "ok": true,
  "task_id": "uuid",
  "task": "ping",
  "team": "system",
  "trace_id": "uuid",
  "result": { "echo": { "task": "ping", "input": {} } }
}
```

**S7 Protecciones:**
- Rate limiting por IP (429 si se excede)
- Sanitización de nombres de tarea y tamaño de inputs
- Task names solo alfanuméricos + `.` + `_`

---

### `POST /enqueue` *(v0.4.0+)*

Encola una tarea en Redis para ejecución asíncrona por el Dispatcher.
Pensado para servicios externos (Make.com, n8n, webhooks) que no necesitan Python SDK.

**Request:**
```json
{
  "task": "research.web",
  "team": "marketing",
  "task_type": "research",
  "input": { "query": "AI trends 2026" },
  "callback_url": "https://hooks.make.com/tu-webhook"
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `task` | string | ✅ | — | Nombre del handler a ejecutar |
| `team` | string | — | `"system"` | Equipo destino |
| `task_type` | string | — | `"general"` | Tipo de tarea |
| `input` | object | — | `{}` | Datos de entrada para el handler |
| `callback_url` | string | — | `null` | URL webhook opcional para recibir resultado cuando termine la tarea |

**Response (200):**
```json
{
  "ok": true,
  "task_id": "uuid-generado",
  "queued": true
}
```

**Errores específicos:**
- `400` — Nombre de tarea inválido (solo alfanuméricos + `.` + `_`)
- `503` — Redis no disponible

### Callback Webhook (opcional)

Si `callback_url` viene en el `POST /enqueue`, el Dispatcher enviará un `POST`
al webhook al terminar la tarea (éxito o fallo), con timeout de 10s y 1 retry
si hay timeout o error 5xx.

**Payload ejemplo:**
```json
{
  "task_id": "uuid-generado",
  "status": "done",
  "task": "research.web",
  "result": { "ok": true, "result": { "..." : "..." } },
  "completed_at": 1741086000
}
```

**Ejemplo curl:**
```bash
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/enqueue \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer $WORKER_TOKEN' \
  -d '{"task":"ping","team":"system","input":{"msg":"hello"}}'
```

---

### `GET /task/{task_id}/status` *(v0.4.0+)*

Consulta el estado de una tarea encolada desde Redis.

**Response (200):**
```json
{
  "task_id": "uuid",
  "status": "queued",
  "task": "research.web",
  "team": "marketing",
  "task_type": "research",
  "result": null,
  "error": null,
  "created_at": "2026-03-04T10:00:00+00:00",
  "queued_at": 1741082400.0
}
```

**Errores específicos:**
- `404` — `task_id` no encontrado en Redis
- `503` — Redis no disponible

**Ejemplo curl:**
```bash
curl -s http://WINDOWS_TAILSCALE_IP:8088/task/UUID-AQUI/status \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

---

### `GET /tasks/{task_id}`

Consultar estado de una tarea por `task_id`. Requiere auth.
Usa el store **in-memory** (tareas ejecutadas por POST /run).

**Response (200):**
```json
{
  "task_id": "uuid",
  "task": "ping",
  "status": "done",
  "result": { "echo": {} },
  "error": null,
  "started_at": "2026-03-04T03:30:00Z",
  "completed_at": "2026-03-04T03:30:01Z"
}
```

**Response (404):** si `task_id` no se encuentra en el store in-memory.

---

### `GET /tasks`

Listar tareas recientes. Filtrable. Requiere auth.

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `limit` | int | 20 | Máximo de tareas a retornar |
| `team` | string | — | Filtrar por prefijo de tarea o team |
| `status` | string | — | Filtrar por estado (`done`, `failed`) |

**Response (200):**
```json
{
  "tasks": [ { "task_id": "...", "task": "...", "status": "done", ... } ],
  "total": 42
}
```

---

## Task Handlers Registrados (25)

| Task | Categoría | Descripción |
|------|-----------|-------------|
| `ping` | System | Echo de prueba |
| `notion.write_transcript` | Notion | Escribe transcripción en página |
| `notion.add_comment` | Notion | Agrega comentario a una página |
| `notion.poll_comments` | Notion | Lee comentarios recientes |
| `notion.upsert_task` | Notion | Crea/actualiza tarea en Kanban |
| `notion.update_dashboard` | Notion | Actualiza dashboard Rick |
| `notion.create_report_page` | Notion | Crea página hija con reporte estructurado |
| `windows.pad.run_flow` | Windows/RPA | Ejecuta flujo de Power Automate Desktop |
| `windows.open_notepad` | Windows | Abre Notepad (interactivo) |
| `windows.write_worker_token` | Windows | Escribe token del worker |
| `windows.firewall_allow_port` | Windows | Abre puerto en firewall |
| `windows.start_interactive_worker` | Windows | Inicia worker interactivo |
| `windows.add_interactive_worker_to_startup` | Windows | Agrega worker al inicio |
| `windows.fs.ensure_dirs` | Filesystem | Crea directorios |
| `windows.fs.list` | Filesystem | Lista archivos/dirs |
| `windows.fs.read_text` | Filesystem | Lee archivo de texto |
| `windows.fs.write_text` | Filesystem | Escribe archivo de texto |
| `windows.fs.write_bytes_b64` | Filesystem | Escribe binario (base64) |
| `system.ooda_report` | Observability | Genera reporte OODA |
| `system.self_eval` | Observability | Auto-evaluación del sistema |
| `linear.create_issue` | Linear | Crea issue en Linear |
| `linear.list_teams` | Linear | Lista equipos de Linear |
| `linear.update_issue_status` | Linear | Actualiza estado de issue |
| `research.web` | Research | Búsqueda web (Tavily) |
| `llm.generate` | LLM | Genera texto con Gemini |
| `composite.research_report` | Composite | Informe de mercado completo (research + LLM) |

---

### `composite.research_report`

Orquesta múltiples `research.web` + `llm.generate` para producir un informe de investigación completo.

**Input:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `topic` | string | ✅ | — | Tema a investigar |
| `queries` | list[str] | — | auto-generados | Queries de búsqueda específicas |
| `depth` | string | — | `"standard"` | `"quick"` (3 queries), `"standard"` (5), `"deep"` (10) |
| `language` | string | — | `"es"` | Idioma del reporte |

**Output:**

```json
{
  "report": "# Informe...\n\n## Resumen Ejecutivo\n...",
  "sources": [{"title": "...", "url": "...", "query": "..."}],
  "queries_used": ["query1", "query2"],
  "stats": {
    "total_sources": 15,
    "research_time_ms": 4500,
    "generation_time_ms": 3200
  }
}
```

**Proceso interno:**
1. Si no hay `queries`, usa `llm.generate` para generar N queries relevantes
2. Ejecuta `research.web` para cada query (errores individuales no crashean)
3. Consolida resultados y genera reporte con `llm.generate`
4. Si LLM falla, retorna datos raw como fallback

**Ejemplo curl:**

```bash
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer $WORKER_TOKEN' \
  -d '{
    "task": "composite.research_report",
    "input": {
      "topic": "AI market trends 2026",
      "depth": "standard",
      "language": "es"
    }
  }'
```

---

## Errores

| Código | Descripción |
|--------|-------------|
| 400 | Request inválido, tarea desconocida, o input inválido |
| 401 | Token faltante o inválido |
| 404 | Tarea no encontrada (GET /tasks/{id}) |
| 429 | Rate limit excedido |
| 500 | Error interno o WORKER_TOKEN no configurado |
| 503 | Redis no disponible (POST /enqueue, GET /task/{id}/status) |

---

## Ejemplos curl

### Desde bash (VPS)

```bash
# Health check
curl http://WINDOWS_TAILSCALE_IP:8088/health

# Run con TaskEnvelope
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer $WORKER_TOKEN' \
  -d '{"schema_version":"0.1","task_id":"test-001","team":"system","task_type":"general","task":"ping","input":{"msg":"hello"}}'

# Consultar tarea
curl -s http://WINDOWS_TAILSCALE_IP:8088/tasks/test-001 \
  -H 'Authorization: Bearer $WORKER_TOKEN'

# Listar tareas recientes
curl -s 'http://WINDOWS_TAILSCALE_IP:8088/tasks?limit=10' \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

### Desde PowerShell (Windows)

```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8088/health

# Run
$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer $env:WORKER_TOKEN"
}
$body = '{"task":"ping","input":{"msg":"hello"}}'
Invoke-RestMethod -Uri http://localhost:8088/run -Method POST -Headers $headers -Body $body
```
