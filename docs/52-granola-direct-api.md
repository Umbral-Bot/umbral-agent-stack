# Granola Direct API on VM

Este documento registra el método operativo preferido para ingerir reuniones
reales de Granola hacia Notion sin depender de export manual en Markdown ni de
RPA/PAD.

## Método preferido

- Fuente de autenticación local:
  - `C:\Users\Rick\AppData\Roaming\Granola\supabase.json`
- Token usado:
  - `workos_tokens.access_token`
- Script operativo:
  - [granola_api_ingest.py](/c:/GitHub/umbral-agent-stack-codex/scripts/vm/granola_api_ingest.py)

## Endpoints internos validados

- `POST https://api.granola.ai/v1/get-documents`
- `POST https://api.granola.ai/v1/get-document-metadata`
- `POST https://api.granola.ai/v1/get-document-transcript`

## Hallazgo clave

`cache-v4.json` puede mostrar reuniones válidas con estos campos vacíos:

- `notes_markdown`
- `notes_plain`
- `summary`
- `overview`

Aun así, `get-document-transcript` sí devuelve el transcript completo real.

## Flujo operativo

1. El script corre en la VM donde está instalada la app de Granola.
2. Obtiene el token local desde `supabase.json`.
3. Lista reuniones o selecciona una por `document_id`, título parcial o “latest”.
4. Descarga transcript y metadata reales desde la API interna.
5. Convierte el transcript a Markdown.
6. Envía el contenido al Worker local con `granola.process_transcript`.
7. El Worker:
   - crea la página en la base de transcripciones de Notion,
   - intenta crear action items,
   - comenta en OpenClaw a `@Enlace`.

## Validación real cerrada

Reunión usada:

- título: `BIM implementación y estrategias de organización del discurso`
- `document_id`: `4d4c239d-9b04-4329-954b-793e82d878da`

Resultado:

- página creada:
  - `31f5f443-fb5c-812c-931b-d1dab2082f71`
- URL:
  - `https://www.notion.so/BIM-implementaci-n-y-estrategias-de-organizaci-n-del-discurso-31f5f443fb5c812c931bd1dab2082f71`
- `notification_sent = true`
- `action_items_created = 0`

## Estado operativo

- método preferido:
  - API directa de Granola en la VM
- método fallback:
  - watcher de exports Markdown en `C:\Granola\exports`
- PAD:
  - no necesario en esta etapa

## Limitaciones conocidas

- La API es interna y no documentada; puede cambiar sin aviso.
- El speaker mapping actual es heurístico:
  - `microphone` -> `David/host`
  - `system` -> `Interlocutor`
- `action_items_created` puede quedar en `0` si la base de tareas de Notion no
  está disponible o si el transcript no trae estructura suficiente para
  extracción simple.
