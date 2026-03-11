# 07 â€” Worker API Contract

## Base URL

```
http://WINDOWS_TAILSCALE_IP:8088
```

Para el canal GUI interactivo, el Worker corre en la misma VM en:

```
http://WINDOWS_TAILSCALE_IP:8089
```

Nota operativa:

- `8088` sigue siendo la ruta principal del Worker estándar.
- `8089` es la ruta correcta para `gui.*`.
- En la VM, `8089` debe arrancarse fuera de sesiones SSH efímeras. La forma robusta validada es la tarea programada `StartInteractiveWorkerHiddenNow`, que lanza `scripts/vm/start_interactive_worker.ps1`.

## AutenticaciÃ³n

Todos los endpoints excepto `/health` requieren autenticaciÃ³n Bearer:

```
Authorization: Bearer <WORKER_TOKEN>
```

---

## Endpoints

### `GET /health`

Health check. No requiere autenticaciÃ³n.

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

| Campo | Tipo | Requerido | DescripciÃ³n |
|-------|------|-----------|-------------|
| `schema_version` | string | âœ… | Siempre `"0.1"` |
| `task_id` | string | âœ… | UUID Ãºnico para esta tarea |
| `team` | string | âœ… | Equipo destino (`marketing`, `advisory`, `improvement`, `lab`, `system`) |
| `task_type` | string | âœ… | Tipo de tarea (`general`, `research`, `writing`, `instruction`) |
| `task` | string | âœ… | Nombre del handler a ejecutar |
| `input` | object | âœ… | Datos de entrada para el handler |
| `trace_id` | string | â€” | UUID para correlaciÃ³n de trazas |
| `status` | string | â€” | Estado (`queued`, `running`, `done`, `failed`) |
| `callback_url` | string | â€” | Webhook opcional para callback al completar/fallar |

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
- SanitizaciÃ³n de nombres de tarea y tamaÃ±o de inputs
- Task names solo alfanumÃ©ricos + `.` + `_`

---

### `POST /enqueue` *(v0.4.0+)*

Encola una tarea en Redis para ejecuciÃ³n asÃ­ncrona por el Dispatcher.
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

| Campo | Tipo | Requerido | Default | DescripciÃ³n |
|-------|------|-----------|---------|-------------|
| `task` | string | âœ… | â€” | Nombre del handler a ejecutar |
| `team` | string | â€” | `"system"` | Equipo destino |
| `task_type` | string | â€” | `"general"` | Tipo de tarea |
| `input` | object | â€” | `{}` | Datos de entrada para el handler |
| `callback_url` | string | â€” | `null` | URL webhook opcional para recibir resultado cuando termine la tarea |

**Response (200):**
```json
{
  "ok": true,
  "task_id": "uuid-generado",
  "queued": true
}
```

**Errores especÃ­ficos:**
- `400` â€” Nombre de tarea invÃ¡lido (solo alfanumÃ©ricos + `.` + `_`)
- `503` â€” Redis no disponible

### Callback Webhook (opcional)

Si `callback_url` viene en el `POST /enqueue`, el Dispatcher enviarÃ¡ un `POST`
al webhook al terminar la tarea (Ã©xito o fallo), con timeout de 10s y 1 retry
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

**Errores especÃ­ficos:**
- `404` â€” `task_id` no encontrado en Redis
- `503` â€” Redis no disponible

**Ejemplo curl:**
```bash
curl -s http://WINDOWS_TAILSCALE_IP:8088/task/UUID-AQUI/status \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

---

### `GET /task/history` *(v0.4.0+)*

Consulta historial de tareas desde Redis (`umbral:task:*`) con filtros y paginaciÃ³n.
No usa el store in-memory.

**Query params:**

| Param | Tipo | Default | DescripciÃ³n |
|-------|------|---------|-------------|
| `hours` | int | 24 | Ventana de tiempo en horas |
| `team` | string | â€” | Filtrar por equipo |
| `status` | string | â€” | Filtrar por estado (`queued`, `running`, `done`, `failed`, `blocked`, `degraded`) |
| `limit` | int | 100 | TamaÃ±o de pÃ¡gina (mÃ¡x 500) |
| `offset` | int | 0 | Offset para paginaciÃ³n |

**Response (200):**
```json
{
  "tasks": [{ "...": "..." }],
  "total": 42,
  "page": {
    "offset": 0,
    "limit": 100,
    "has_more": false
  },
  "stats": {
    "done": 35,
    "failed": 5,
    "queued": 2,
    "running": 0,
    "blocked": 0,
    "degraded": 0,
    "unknown": 0,
    "teams": {
      "marketing": 10,
      "system": 32
    }
  }
}
```

**Errores especÃ­ficos:**
- `400` â€” `status` invÃ¡lido
- `503` â€” Redis no disponible

**Ejemplo curl:**
```bash
curl -s "http://WINDOWS_TAILSCALE_IP:8088/task/history?hours=24&limit=100&offset=0" \
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

| Param | Tipo | Default | DescripciÃ³n |
|-------|------|---------|-------------|
| `limit` | int | 20 | MÃ¡ximo de tareas a retornar |
| `team` | string | â€” | Filtrar por prefijo de tarea o team |
| `status` | string | â€” | Filtrar por estado (`done`, `failed`) |

**Response (200):**
```json
{
  "tasks": [ { "task_id": "...", "task": "...", "status": "done", ... } ],
  "total": 42
}
```

---

## Task Handlers Registrados (resumen)

> El inventario exacto puede variar segun la version desplegada. Para el listado vivo usar `GET /health`.

| Task | CategorÃ­a | DescripciÃ³n |
|------|-----------|-------------|
| `ping` | System | Echo de prueba |
| `notion.write_transcript` | Notion | Escribe transcripciÃ³n en pÃ¡gina |
| `notion.add_comment` | Notion | Agrega comentario a una pÃ¡gina |
| `notion.poll_comments` | Notion | Lee comentarios recientes |
| `notion.read_page` | Notion | Lee metadata y snapshot de una pÃ¡gina |
| `notion.read_database` | Notion | Lee schema y filas de una base de datos |
| `notion.search_databases` | Notion | Busca bases de datos por tÃ­tulo |
| `notion.create_database_page` | Notion | Crea una pÃ¡gina en una base usando propiedades raw |
| `notion.update_page_properties` | Notion | Actualiza propiedades raw de una pÃ¡gina |
| `notion.upsert_task` | Notion | Crea/actualiza tarea en Kanban |
| `notion.upsert_project` | Notion | Crea/actualiza proyecto en ðŸ“ Proyectos â€” Umbral |
| `notion.update_dashboard` | Notion | Actualiza dashboard Rick |
| `notion.create_report_page` | Notion | Crea pÃ¡gina hija con reporte estructurado |
| `windows.pad.run_flow` | Windows/RPA | Ejecuta flujo de Power Automate Desktop |
| `windows.open_notepad` | Windows | Abre Notepad (interactivo) |
| `windows.open_url` | Windows | Abre una URL en el navegador predeterminado |
| `windows.write_worker_token` | Windows | Escribe token del worker |
| `windows.firewall_allow_port` | Windows | Abre puerto en firewall |
| `windows.start_interactive_worker` | Windows | Inicia worker interactivo |
| `windows.add_interactive_worker_to_startup` | Windows | Agrega worker al inicio |
| `windows.fs.ensure_dirs` | Filesystem | Crea directorios |
| `windows.fs.list` | Filesystem | Lista archivos/dirs |
| `windows.fs.read_text` | Filesystem | Lee archivo de texto |
| `windows.fs.write_text` | Filesystem | Escribe archivo de texto |
| `windows.fs.write_bytes_b64` | Filesystem | Escribe binario (base64) |
| `browser.navigate` | Browser | Abre o reutiliza una página Playwright persistente y navega a una URL |
| `browser.read_page` | Browser | Extrae texto visible y opcionalmente HTML de la página actual o un selector |
| `browser.screenshot` | Browser | Captura screenshot de página completa, viewport o selector |
| `gui.desktop_status` | GUI | Reporta tamaño de pantalla, cursor y control raíz de la sesión interactiva |
| `gui.screenshot` | GUI | Captura screenshot del escritorio Windows interactivo; prueba varios backends y reporta si la imagen es usable o es un frame negro |
| `gui.click` | GUI | Mueve el mouse y hace click en coordenadas absolutas |
| `gui.type_text` | GUI | Escribe texto en el control actualmente enfocado |
| `gui.hotkey` | GUI | Envía combinaciones de teclado a la sesión GUI |
| `gui.list_windows` | GUI | Lista ventanas top-level de la sesión interactiva, con título, clase, PID y proceso |
| `gui.activate_window` | GUI | Trae al frente una ventana por título exacto, substring o nombre de proceso |
| `system.ooda_report` | Observability | Genera reporte OODA |
| `system.self_eval` | Observability | Auto-evaluaciÃ³n del sistema |
| `linear.create_issue` | Linear | Crea issue en Linear, con soporte opcional para asociar a proyecto |
| `linear.list_teams` | Linear | Lista equipos de Linear |
| `linear.update_issue_status` | Linear | Actualiza estado de issue |
| `linear.list_projects` | Linear | Lista proyectos de Linear |
| `linear.create_project` | Linear | Crea proyecto de Linear o retorna el existente |
| `linear.attach_issue_to_project` | Linear | Asocia un issue existente a un proyecto |
| `linear.list_project_issues` | Linear | Lista issues asociadas a un proyecto |
| `linear.create_project_update` | Linear | Publica update de estado en un proyecto (health + body) |
| `n8n.list_workflows` | n8n | Lista workflows disponibles en la instancia configurada |
| `n8n.get_workflow` | n8n | Lee la definicion de un workflow por ID |
| `n8n.create_workflow` | n8n | Crea un workflow desde JSON raw |
| `n8n.update_workflow` | n8n | Actualiza un workflow existente desde JSON raw |
| `n8n.post_webhook` | n8n | Invoca un webhook sobre la instancia configurada |
| google.audio.generate | Google | Genera TTS con Gemini preview TTS |
| google.image.generate | Google | Genera imagenes y las guarda a disco via Images API compatible |
| make.post_webhook | Make | Invoca un webhook allowlisted de Make.com |
| `research.web` | Research | BÃºsqueda web (Tavily) |
| `llm.generate` | LLM | Genera texto con Gemini, OpenAI o Anthropic (segun `model`) |
| `composite.research_report` | Composite | Informe de mercado completo (research + LLM) |

---

### `llm.generate`

Genera texto usando proveedor inferido por el campo `model`.

**Input:**

| Campo | Tipo | Requerido | Default | Descripcion |
|-------|------|-----------|---------|-------------|
| `prompt` | string | âœ… | â€” | Prompt principal para el modelo |
| `model` | string | â€” | `gemini-2.5-flash` | Modelo a usar. Define proveedor automaticamente |
| `selected_model` | string | â€” | â€” | Alias de compatibilidad desde Dispatcher (`chatgpt_plus`, `claude_pro`, etc.) |
| `system` | string | â€” | `""` | Instruccion de sistema |
| `max_tokens` | int | â€” | `1024` | Limite de tokens de salida |
| `temperature` | float | â€” | `0.7` | Temperatura de muestreo |

**Modelos soportados por proveedor:**

- Gemini: `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini_pro` (alias)
- OpenAI: `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`, `gpt-4`, `chatgpt_plus` (alias), `copilot_pro` (alias)
- Anthropic: `claude-sonnet-4-20250514`, `claude-3-5-sonnet`, `claude-3-haiku`, `claude_pro` (alias)

**Errores de configuracion:**

- Si se solicita OpenAI sin `OPENAI_API_KEY` -> error `OPENAI_API_KEY not configured`
- Si se solicita Anthropic sin `ANTHROPIC_API_KEY` -> error `ANTHROPIC_API_KEY not configured`
- Si no se envÃ­a `model`, se usa Gemini por defecto (backward compatibility)

---

### `composite.research_report`

Orquesta mÃºltiples `research.web` + `llm.generate` para producir un informe de investigaciÃ³n completo.

**Input:**

| Campo | Tipo | Requerido | Default | DescripciÃ³n |
|-------|------|-----------|---------|-------------|
| `topic` | string | âœ… | â€” | Tema a investigar |
| `queries` | list[str] | â€” | auto-generados | Queries de bÃºsqueda especÃ­ficas |
| `depth` | string | â€” | `"standard"` | `"quick"` (3 queries), `"standard"` (5), `"deep"` (10) |
| `language` | string | â€” | `"es"` | Idioma del reporte |

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

### `GET /scheduled`

Lista tareas programadas a futuro (Redis sorted set). Requiere auth.

**Response (200):**
```json
{
  "ok": true,
  "scheduled": [
    {
      "task_id": "uuid",
      "task": "ping",
      "team": "system",
      "run_at": "2026-03-04T12:00:00Z",
      "created_at": "2026-03-04T03:00:00Z"
    }
  ],
  "total": 1
}
```

**Errores especÃ­ficos:**
- `503` â€” Redis no disponible

**Ejemplo curl:**
```bash
curl -s "http://WINDOWS_TAILSCALE_IP:8088/scheduled" \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

---

### `GET /providers/status` *(v0.5.0+)*

Dashboard de estado de providers. Muestra quÃ© modelos estÃ¡n configurados,
su cuota actual, nombre de modelo, y a quÃ© `task_types` enrutan como preferido.

**Response (200):**
```json
{
  "timestamp": "2026-03-04T14:00:00Z",
  "configured": ["claude_pro", "gemini_pro", "gemini_flash"],
  "unconfigured": ["azure_foundry"],
  "providers": {
    "claude_pro": {
      "configured": true,
      "model": "claude-sonnet-4-6",
      "quota_used": 30,
      "quota_limit": 200,
      "quota_fraction": 0.15,
      "quota_status": "ok",
      "routing_preferred_for": ["coding", "general", "ms_stack", "writing"]
    },
    "azure_foundry": {
      "configured": false,
      "model": "gpt-5.3-codex",
      "quota_used": 0,
      "quota_limit": 2000,
      "quota_fraction": 0.0,
      "quota_status": "unknown",
      "routing_preferred_for": []
    }
  }
}
```

**Campos por provider:**

| Campo | Tipo | DescripciÃ³n |
|-------|------|-------------|
| `configured` | bool | `true` si las env vars requeridas estÃ¡n presentes |
| `model` | string | Nombre del modelo LLM asociado |
| `quota_used` | int | Requests usados en la ventana actual |
| `quota_limit` | int | LÃ­mite de requests por ventana |
| `quota_fraction` | float | FracciÃ³n de uso (0.0â€“1.0) |
| `quota_status` | string | `ok`, `warn`, `restrict`, `exceeded`, `unknown` |
| `routing_preferred_for` | list[str] | Task types que prefieren este provider |

**Errores especÃ­ficos:**
- `503` â€” Redis no disponible

**Ejemplo curl:**
```bash
curl -s "http://WINDOWS_TAILSCALE_IP:8088/providers/status" \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

---

### `GET /tools/inventory` *(v0.5.0+)*

Inventario completo de tasks registradas en el Worker, skills detectados
del directorio `openclaw/workspace-templates/skills/`, y categorizaciÃ³n.

**Response (200):**
```json
{
  "timestamp": "2026-03-04T...",
  "total_tasks": 33,
  "tasks": [
    {"name": "figma.get_file", "module": "figma", "category": "figma"},
    {"name": "llm.generate", "module": "llm", "category": "ai"}
  ],
  "skills": ["figma"],
  "skills_detail": [
    {"name": "figma", "description": "Interact with Figma REST API..."}
  ],
  "categories": {"ai": 3, "figma": 5, "notion": 6, "windows": 11}
}
```

**Ejemplo curl:**
```bash
curl -s "http://WINDOWS_TAILSCALE_IP:8088/tools/inventory" \
  -H 'Authorization: Bearer $WORKER_TOKEN'
```

---

## Errores

| CÃ³digo | DescripciÃ³n |
|--------|-------------|
| 400 | Request invÃ¡lido, tarea desconocida, o input invÃ¡lido |
| 401 | Token faltante o invÃ¡lido |
| 404 | Tarea no encontrada (GET /tasks/{id}) |
| 429 | Rate limit excedido |
| 500 | Error interno o WORKER_TOKEN no configurado |
| 503 | Redis no disponible (POST /enqueue, GET /task/{id}/status, GET /task/history) |

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

