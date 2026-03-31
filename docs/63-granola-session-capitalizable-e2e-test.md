# Test E2E Controlado: Granola -> session_capitalizable

## Objetivo

Validar el estado actual del runtime V1 para una reunion real de Granola sin
capitalizacion a targets canonicos.

Este test cubre solo:

1. `raw -> session_capitalizable`
2. lectura operativa de una `session_capitalizable` real
3. comentario de revision cuando hay ambiguedad

Este test no cubre:

- tareas
- proyectos
- entregables
- CRM
- programas
- recursos
- briefing matinal
- drafts de correo

## Precondiciones exactas

- Worker levantado y accesible en `WORKER_URL`
- `WORKER_TOKEN` valido
- integracion de Notion de Rick compartida con:
  - DB raw de Granola
  - DB `session_capitalizable` actual
  - pagina `Control Room`
- reunion real disponible como markdown o texto exportado desde Granola
- para happy path, usar una reunion que no haya generado duplicados previos en
  `session_capitalizable`

## Variables y accesos a verificar

Variables minimas:

- `WORKER_URL`
- `WORKER_TOKEN`
- `NOTION_API_KEY`
- `NOTION_CONTROL_ROOM_PAGE_ID`
- `NOTION_GRANOLA_DB_ID`
- `NOTION_CURATED_SESSIONS_DB_ID`

No son necesarias para este test:

- `NOTION_TASKS_DB_ID`
- `NOTION_PROJECTS_DB_ID`
- `NOTION_HUMAN_TASKS_DB_ID`
- `NOTION_COMMERCIAL_PROJECTS_DB_ID`

Checks de acceso en Notion:

- la integracion puede crear paginas en raw
- la integracion puede crear o actualizar filas en `session_capitalizable`
- la integracion puede comentar en la pagina raw
- idealmente la integracion puede comentar tambien en la fila
  `session_capitalizable`

## Paso 1: Ingerir la reunion a raw

Preparar un archivo local, por ejemplo `granola-real.md`, con la reunion real
exportada desde Granola.

```powershell
$headers = @{ Authorization = "Bearer $env:WORKER_TOKEN" }

$content = Get-Content .\granola-real.md -Raw

$body = @{
  task = "granola.process_transcript"
  input = @{
    title = "Reunion real Granola - Cliente X"
    content = $content
    date = "2026-03-31"
    attendees = @("David", "Cliente X")
    source = "granola"
    notify_enlace = $true
  }
} | ConvertTo-Json -Depth 6

$raw = Invoke-RestMethod `
  -Method Post `
  -Uri "$env:WORKER_URL/run" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$raw | ConvertTo-Json -Depth 8
```

Respuesta esperada:

- `result.page_id`
- `result.url`
- `result.action_items_detected`
- `result.action_items_created = 0`
- `result.legacy_raw_task_writes_enabled = false`

## Paso 2: Promover raw a session_capitalizable

Usar el alias V1 contractual:

```powershell
$body = @{
  task = "granola.promote_session_capitalizable"
  input = @{
    transcript_page_id = $raw.result.url
    session_name = "Cliente X - sesion capitalizable"
    summary = "Prueba controlada V1 desde reunion real de Granola."
    add_trace_comments = $true
  }
} | ConvertTo-Json -Depth 6

$promote = Invoke-RestMethod `
  -Method Post `
  -Uri "$env:WORKER_URL/run" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$promote | ConvertTo-Json -Depth 8
```

Respuesta esperada en happy path:

- `result.session_capitalizable_page_id`
- `result.session_capitalizable_url`
- `result.session_capitalizable_db_id`
- `result.matched_existing = false` si crea una fila nueva
- `result.matched_existing = true` si resolvio una existente
- `result.match_strategy = source_url | exact_title | normalized_title_date` si
  fue update

Si quieres promover una pagina raw ya existente en Notion, puedes saltarte el
Paso 1 y usar su URL directamente en `transcript_page_id`.

## Paso 3: Leer la session_capitalizable ya resuelta

```powershell
$body = @{
  task = "granola.read_session_capitalizable"
  input = @{
    transcript_page_id = $raw.result.url
  }
} | ConvertTo-Json -Depth 6

$read = Invoke-RestMethod `
  -Method Post `
  -Uri "$env:WORKER_URL/run" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body

$read | ConvertTo-Json -Depth 8
```

Respuesta esperada:

- `result.ok = true`
- `result.matched_existing = true`
- `result.session_capitalizable_page_id`
- `result.session_capitalizable_url`

## Outputs esperados en Notion

### En raw

Debe existir una pagina nueva en la DB raw con:

- titulo de la reunion
- contenido de la reunion
- fuente `granola`

Despues de una promocion exitosa, si esos campos existen en el schema raw:

- `Estado = Procesada`
- `Fecha que el agente proceso = <fecha del test>`
- `URL artefacto = <url de session_capitalizable>`

Si `add_trace_comments = true`, debe quedar comentario de trazabilidad en raw.

### En session_capitalizable

Debe existir una fila creada o actualizada con los campos que el schema live
permita, tipicamente:

- titulo
- fecha
- fuente/origen
- `URL fuente = <url raw>`
- resumen
- notas
- `Transcripcion disponible = true`

### Si hay ambiguedad

No debe crearse ni actualizarse una fila.

La respuesta de `granola.promote_session_capitalizable` o
`granola.read_session_capitalizable` debe traer:

- `ok = false`
- `blocked_by_ambiguity = true`
- `review_comment_added = true`
- `ambiguous_matches = [...]`

El comentario esperado en raw tiene esta forma:

```text
Revision requerida por gobernanza V1.
1. Evidencia fuente: ...
2. Destino intencionado: session_capitalizable
3. Bloqueo: Multiple session_capitalizable candidates match the same raw source.
4. Siguiente revision necesaria: ...
```

## Senales de fallo

- `HTTP 400` o `HTTP 500`
- `NOTION_CURATED_SESSIONS_DB_ID not configured`
- la pagina raw se crea pero la promocion devuelve error o `not_found`
- promocion con `ok = true` pero no aparece fila en `session_capitalizable`
- `review_comment_added = false` en un caso ambiguo
- `granola.read_session_capitalizable` no puede resolver la sesion justo despues
  de una promocion exitosa
- el raw no muestra `URL artefacto` despues de una promocion exitosa

## Datos minimos a devolver despues del test

Para diagnosticar el resultado del test, devolver solo esto:

1. URL de la pagina raw
2. JSON completo de la respuesta de
   `granola.promote_session_capitalizable`
3. JSON completo de la respuesta de
   `granola.read_session_capitalizable`
4. si hubo ambiguedad:
   - texto exacto del comentario en raw
   - URLs de las filas listadas en `ambiguous_matches`
5. confirmacion visual minima de raw:
   - si `Estado = Procesada`
   - si `URL artefacto` quedo poblado
6. confirmacion visual minima de `session_capitalizable`:
   - URL de la fila
   - si fue creada o actualizada

## Criterio de exito del test

El test se considera exitoso si:

1. la reunion entra a raw sin crear tareas canonicas
2. la promocion resuelve exactamente una `session_capitalizable`
3. la lectura posterior encuentra esa misma sesion
4. no se toca ningun target canonico
5. ante ambiguedad, el sistema comenta para revision y no escribe
