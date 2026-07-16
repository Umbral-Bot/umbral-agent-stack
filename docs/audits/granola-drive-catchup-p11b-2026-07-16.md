# Granola Drive Catch-up (P1.1b) — Closeout Snapshot — 2026-07-16

## Objetivo

Ingerir en la DB raw canónica `Transcripciones Granola` los transcripts que
David pega manualmente, verbatim, como archivos `.md` en la carpeta
Drive-sincronizada:

```
G:\Mi unidad\07_Sesiones y Transcripciones\Notas y Transcripciones\Granola\
```

Cubre solo el tramo `Drive .md -> parser -> granola.process_transcript ->
Notion raw`. **No cubre capitalización** (promoción a proyecto/tarea/sesión
curada canónica) — eso queda fuera de scope por diseño, per
`docs/54-granola-capitalize-raw-slice.md` y la skill
`notion-governance-runtime`.

## Resultado

**P1_1B_CATCHUP_COMPLETE.** 95/95 archivos elegibles ingeridos y verificados
en Notion, 0 FAIL, en 13 lotes ejecutados entre 2026-07-15 y 2026-07-16.
Verificación final (snapshot Notion re-paginado desde cero, 133 páginas,
`has_more=false`): `create=0, update_transcript=0, review_ambiguous=0,
skip=95/95`.

- Inventario Drive: 96 archivos totales, 95 elegibles (1 excluido:
  `Comgrap - MCP.md`, 0 bytes). Sin archivos `Indice_Transcripciones_Locales_*`
  en esa subcarpeta.
- Smoke `BIM Forum - Automatización` (2026-07-13, `source=granola_mcp`, con
  `granola_document_id` real) **excluida en todos los lotes** — sin `.md`
  correspondiente en Drive a la fecha de este cierre.
- Fuente/captura: `Fuente=granola_drive_md` en las 95 páginas, contenido =
  transcript verbatim completo (no solo resumen AI).
- `Procesar con agente=False` verificado en cada una de las 95 páginas
  escritas — cero capitalización ejecutada por este trabajo.
- Trigger del agente Notion "review y capitalización V2.1" (en particular
  "Propiedad actualizada en Transcripciones Granola"): **confirmado OFF por
  David antes de lote 6, nunca reactivado durante este trabajo.**

## PRs mergeados a `main`

| PR | SHA | Contenido |
|---|---|---|
| [#532](https://github.com/Umbral-Bot/umbral-agent-stack/pull/532) | `1bea7988` | Parser (`scripts/vm/granola_drive_md_ingest.py`), gap-check (`scripts/list_granola_drive_ingest_gap.py`), batch builder (`scripts/build_granola_drive_ingest_batch.py`) + 48 tests |
| [#533](https://github.com/Umbral-Bot/umbral-agent-stack/pull/533) | `2e4e5b90` | Sender (`scripts/vm/send_granola_drive_batch.py`, dry-run por defecto) + 13 tests |
| [#534](https://github.com/Umbral-Bot/umbral-agent-stack/pull/534) | `21570485` | Fix `worker/notion_client.py::replace_blocks_in_page` (borrado concurrente + retry 429) — infra general del worker, no específico de P1.1b; encontrado en vivo durante lote 1 (Susana Millán WSP, 353 bloques legacy) |

VPS y local `main` confirmados en `21570485` (o posterior) antes de cada lote
de escritura.

## Lotes ejecutados

| Lote | Items | Acción | Notas |
|---|---|---|---|
| 1 | 5 | update | BIM Forum 2, Sesión 3 power automate -WSP, WSP Power Automate Sesión 5, BIM FOrum ("Hoja de ruta BIM Chile"), Susana Millán WSP. Encontró y disparó el fix de `replace_blocks_in_page` (#534); reintento con `force_reconcile` tras el fix, verificado. |
| 2 | 5 | update | Butic Reu con Marcos, Konstruedu Membresia IA, Sesión GT BIM Forum, konstruedu, konstruedu 2 |
| 3 | 5 | 2 update + 3 create | Comgrap Openclaw, Comgrap Dynamo-Carcel · Reunión Marcos y Eduardo Butic Webinar, Sesión de seguimiento WSP, WSP despliegue |
| 4 | 5 | 3 update + 2 create | Curso Dynamo Geosys C1/C2/C4 · Sesión 1 WSP, Sesión 2 WSP |
| 5 | 5 | create | Welcome Day Butic, Reunión con Marco Butic, Comgrap Umbral BIM, konstruedu Contratos, WSP Sharepoint Copilot |
| 6 | 5 | create | Bim Forum GT Radar BIM, BIM Forum Grupo Tecnico Mandnates, WSP Copilot, Konstruedu Rolando, Butic AECODE. **Preflight de trigger Notion introducido aquí** (David confirma OFF). |
| 7 | 5 | create | BIM Forum MT Estándar Publicos, Konstruedu Revisión cursos, konstruedu cursos grabados Feedback, Reunión con MArcos y Eduardo Butic, Konstruedu Tema contratos con Sergio |
| 8 | 10 | update | Últimos 10 update_transcript de longitud: workshop embudo inteligente, webinar notebooklm, Arquitectura y Robots, Propuesta Duma Design, Reunión Rafael Propuesta, 4x asesoría discurso, Susana WPS 2. Restricción de familia levantada; batch subido a 10; patrón driver-script introducido. |
| 9 | 10 | update | Últimos update_transcript restantes: ACI Autodesk, Adarcus Umrbal Convenio, Adarcus, asesoría discurso 3, BIM Logic, borago, Dessau Peru 2, n8n, reunion begoña, Reunión con Pablo |
| 10 | 10 | create | Webinar Said Herrera, Curso Dynamo Geosys C3→"Geosys 2", Máster en IA para AEC, WSP Power Automate sesión 6, Sesión 4 Power automate WSP, David Barco Gest Project, Embajadores n8n LATAM, Aecode Webinar, Copilot 365 WPS Susana Millan, BIM Forum MT Estándar#2. Guarda de seguridad create (aborta si dry-run matched_existing inesperado) introducida aquí. |
| 11 | 10 | create | Consulta OMAR, Capitalizame (solo título de reunión, sin relación con capitalización del pipeline), BIM Forum GT→"Bim Forum Grupo Tecnico 2", How Anthropic's sales team, Sesion ayuda Microsoft, BIM Forum - GT, Asesoría Discurso -13/11, Demo Viktor, Nicolas Iglu. DB cruzó 100 páginas — paginación confirmada necesaria desde aquí. |
| 12 | 10 | create | Mcrosoft ISV, Asesoría Discurso -11→"...11 2", Evelio Sanchez, Reunión Cecilia Sepulveda, Asesoría Discurso 16/15, Reunión Jorge Leed Master 4.0, llamada con Rafael, Dasseu Peru→"...2", Parte de invitación AECODE |
| 13 (cierre) | 10 | create | BIM Forum 3→"BIM Forum 2", Butic Reunión con Begoña, Escultura IA Mario Morales, konstruedu 3→"Konstruedu 2", Konstruedu Revisión cursos→"...2", Microsoft, Reunión con Javier Cabo Rodriguez, Reunión con Marco, Reunión Konstruedu Cursos grabados, Reunión Microsoft Startup |

**Total: 35 (lotes 1-7, 5/lote) + 60 (lotes 8-13, 10/lote) = 95.**

Varios títulos colisionaron con páginas ya existentes bajo el mismo nombre
(reuniones distintas, mismo asunto recurrente) — el propio
`_resolve_new_raw_title` del worker los auto-numeró ("Geosys 2", "BIM Forum
2", "Konstruedu 2", etc.) en vez de sobreescribir contenido ajeno. Ningún
caso fue un duplicado real: se verificó fecha distinta en cada colisión antes
de ingerir.

## Método de verificación (los 95, sin excepción)

Por cada item: dry-run contra el worker (confirma `create`/`reconcile` +
`matched_existing` esperado) → execute (siempre `--execute` explícito,
nunca por omisión) → lectura directa de Notion (no solo la respuesta HTTP):
tipo de bloque (`paragraph` únicamente), fecha de edición, conteo de
caracteres vs. archivo fuente (tolerancia ±2, el header agrega 1 char de
trailing newline recortado por Notion), y `Procesar con agente=False`.

Desde lote 5, todos los `execute` en la VPS corrieron **detached**
(`nohup` + poll de archivo `.done`) — una caída de la conexión SSH que lanzó
el proceso no se contó como FAIL mientras la verificación en Notion pasara
(confirmado en la práctica: 2 caídas de transporte, 0 pérdida de datos real).

## Tracking externo

No se encontró tarea/board de agentes dedicado a P1.1b para actualizar a
`done`: `.agents/tasks/2026-07-14-001-copilot-vps-granola-p11-readiness.md`
es una tarea previa y distinta (readiness VPS del smoke MCP P1.1, asignada a
Copilot, sin relación directa con este catch-up de Drive). Una búsqueda en
Notion tampoco encontró una página/tarea dedicada con ese nombre. Este
documento es el registro de cierre.

## Pendiente (fuera de scope, no un error)

- **Smoke "BIM Forum - Automatización"**: sin `.md` en Drive aún. Un
  gap-check futuro la va a detectar solo cuando David deposite el archivo —
  no requiere lógica especial.
- **Trigger del agente Notion**: sigue OFF (última confirmación de David,
  previa a lote 6). Nadie lo reactivó durante este trabajo — su reactivación
  es decisión de David.
- **Capitalización**: cero ejecutada. Todas las 95 páginas quedan en estado
  raw; su promoción a proyecto/tarea/sesión canónica (si corresponde) es un
  trabajo separado y explícitamente fuera de este catch-up.

## Infraestructura reusable (todo en `main`)

- `scripts/vm/granola_drive_md_ingest.py` — parser + payload builder
- `scripts/list_granola_drive_ingest_gap.py` — gap-check + overrides + reglas
  de colisión (título+fecha exacta → update; sin match → create; near-dup +
  fecha exacta → escalate a revisión)
- `scripts/build_granola_drive_ingest_batch.py` — batch builder
- `scripts/vm/send_granola_drive_batch.py` — sender al worker, dry-run por
  defecto, selección por `--relative-paths`/`--limit`
- `worker/notion_client.py::replace_blocks_in_page` — fix de concurrencia +
  retry en 429 (PR #534), beneficia cualquier reemplazo de bloques en
  páginas con conteo grande de bloques legacy, no solo Granola

Los scripts `.tmp/loteN_driver.py` (loop dry-run→execute→verify por lote) no
se commitearon — eran de un solo uso por lote, recrear si se retoma este
flujo exacto más adelante.
