# Granola Direct API Validation — 2026-03-09

Ejecutado por: codex

## Objetivo

Validar un método directo, sin PAD, para ingerir una reunión real desde Granola
en la VM hacia la base de transcripciones de Notion y el comentario a `@Enlace`.

## Método

- VM Windows con la app de Granola instalada
- token local leído desde:
  - `C:\Users\Rick\AppData\Roaming\Granola\supabase.json`
- endpoints internos usados:
  - `get-documents`
  - `get-document-metadata`
  - `get-document-transcript`
- ingestión final:
  - `granola.process_transcript`

## Reunión validada

- título:
  - `BIM implementación y estrategias de organización del discurso`
- `document_id`:
  - `4d4c239d-9b04-4329-954b-793e82d878da`

## Resultado

- transcript real obtenido:
  - sí
- página creada en la base de Notion de transcripciones:
  - sí
- URL de la página:
  - `https://www.notion.so/BIM-implementaci-n-y-estrategias-de-organizaci-n-del-discurso-31f5f443fb5c812c931bd1dab2082f71`
- comentario a `@Enlace`:
  - sí
- action items automáticos:
  - `0`

## Conclusión

El método preferido actual para Granola en la VM es la API interna del desktop
app, no el cache local ni el export manual. El watcher Markdown se mantiene como
fallback.
