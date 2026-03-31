# Granola Raw Ingest Gap Live Audit — 2026-03-31

## Objetivo

Medir el gap real entre:

- el cache live de Granola exportable hoy;
- y la base raw live de Notion `Transcripciones Granola`.

Este corte cubre el tramo:

`Granola cache/API -> exporter -> Notion raw`

No cubre promoción a `session_capitalizable` ni capitalización a destinos canónicos.

## Comando canónico

```powershell
python scripts/list_granola_raw_ingest_gap.py
python scripts/list_granola_raw_ingest_gap.py --json
```

## Resumen ejecutivo

Estado inicial detectado en este frente:

- `cache_scanned = 45`
- `exportable = 43`
- `skipped_unusable = 2`
- `raw_total = 9`
- `raw_real = 3`
- `raw_smoke = 6`
- `likely_present = 1`
- `batch1_recent_unique = 4`
- `batch1_recent_ambiguous = 2`
- `historic_unique = 32`
- `historic_ambiguous = 4`

Estado live después del intake batch controlado y de corregir el monitor para leer `granola_document_id` desde `Trazabilidad`:

- `raw_total = 49`
- `raw_real = 43`
- `raw_smoke = 6`
- `likely_present = 41`
- `batch1_recent_unique = 0`
- `batch1_recent_ambiguous = 0`
- `historic_unique = 0`
- `historic_ambiguous = 2`

Conclusión final:

- Rick ya tiene capacidad real para cubrir el intake `Granola -> raw` usando el runner controlado.
- El backlog seguro quedó absorbido en raw.
- Solo quedan 2 casos ambiguos same-day que no deben subirse a ciegas.
- Esos 2 casos ya quedaron marcados con comentario de revisión V1 en sus raws históricos.

## Raw real ya presente al inicio del diagnóstico

- `Reunión Con Jorge de Boragó` — raw `3305f443-fb5c-8184-953d-ebf2190afc57`
- `Konstruedu` — raw `3305f443-fb5c-81db-9162-fd70c8574938`
- `Asesoría discurso` — raw `3305f443-fb5c-81e6-a1a5-cc0b2ebd1786`

## Likely Present

Estos casos tienen match exacto de título contra raw y no caen en familia repetida.

- `2026-03-27` — `Reunión Con Jorge de Boragó` — `e52c8fa0-b837-4999-8993-6480db0f5461`

## Batch 1 — Recent Unique

Estos son los candidatos más seguros para un primer batch raw-only.

- `2026-03-30` — `Bim Forum Grupo Tecnico` — `fdc2ec12-ce69-4002-9c14-3ec934076bba`
- `2026-03-30` — `BIM Forum` — `22fae407-0e26-420d-8529-2a174d526ade`
- `2026-03-27` — `Granola ef88925a` — `ef88925a-eeec-4fb6-a1dd-61c8cf26b336`
- `2026-03-24` — `Ejercicio doker Diplomado BIM + IA Butic` — `7b4c36ee-f6e1-47ad-a3e9-393558b8d40b`

## Batch 1 — Recent Ambiguous

Estos son recientes, pero no conviene ingresarlos a ciegas mientras raw no persista `Granola document_id`.

- `2026-03-30` — `Konstruedu` — `465e8f31-27b2-4c17-9db8-951cb8ef983c`
  razón: ya existe un `Konstruedu` en raw y el título se repite en cache
- `2026-03-30` — `asesoría discorso` — `15918ab7-7354-4d55-9714-d93942aca89c`
  razón: near-duplicate fuerte con `Asesoría discurso` ya presente en raw

## Historic Ambiguous

- `2026-03-23` — `Konstruedu` — `1d177374-2ff0-42a0-a032-189075f8b4c0`
- `2026-03-23` — `Asesoría discurso` — `5bff2a5a-0c7a-41c6-ae34-d6662325d67f`
- `2026-03-16` — `Asesoria discurso` — `178d3758-410c-4872-bf7d-0eb6c64e934a`
- `2026-03-12` — `Konstruedu` — `6752772d-f05a-42cc-ba08-85b700031b2e`

## Historic Unique

- `2026-03-18` — `Geosys Dynamo Clase 4` — `5786dbfc-2aee-4863-ad8b-a904476d3cbf`
- `2026-03-18` — `BIM FOurm` — `9de0b6a1-1220-4216-8807-c9146fb647e8`
- `2026-03-17` — `ACI Autodesk` — `d2446076-948f-4a66-ba6e-ade1d910db13`
- `2026-03-17` — `Reunión con Pablo` — `36849af3-c729-4122-a608-8d067a4c0502`
- `2026-03-16` — `Webinar Notebooklm` — `124fc73b-d189-43d3-a998-204d6e28738c`
- `2026-03-13` — `Reunión con Begoña` — `3d382a3d-268f-4ac7-8d93-982cc65f869f`
- `2026-03-11` — `Geosys` — `39a9b662-f11d-4ea5-be4c-274a03283469`
- `2026-03-09` — `BIM-Logic` — `941b77f6-0996-4c8a-b7ea-832a4124e3b5`
- `2026-03-06` — `BIM implementación y estrategias de organización del discurso` — `4d4c239d-9b04-4329-954b-793e82d878da`
- `2026-03-06` — `Adarcus` — `c4c715f3-0852-4974-87ad-50c484a5a2fe`
- `2026-03-04` — `Reunbión con N8n` — `09971dd7-c5c8-4e3e-a24f-167b5dba6058`
- `2026-03-04` — `Embudo inteligente: estrategias de adquisición de clientes para empresas B2B` — `b1467fc0-1589-4443-9db5-c80fd8171832`
- `2026-03-04` — `Automatización de documentos técnicos para flujo de trabajo en DSO` — `afe055f8-7247-4cd3-b4ba-0d3182bd3eab`
- `2026-03-04` — `Markdown y herramientas de IA para procesamiento de documentación técnica` — `d62b1ff1-0854-4e90-8d07-44e00ed0ea03`
- `2026-03-03` — `Introducción a Power BI y modelado de datos con David Moreira` — `0d227c2b-a8c3-47bd-bde3-82577d25cf63`
- `2026-03-02` — `Dynamo scripting para selección y ubicación de vistas en planos de Revit` — `dea2d141-2712-44ed-b918-b23387e415cd`
- `2026-03-02` — `Reunión de actualización de la hoja de ruta BIM con socios de Bim Forum Chile` — `8fc994c7-7d73-42a9-a9dd-6a55d5df7741`
- `2026-02-27` — `Automatización de soporte con Power Automate para Umbralbim` — `1c82ad57-5f11-4964-b80d-cc6293f85170`
- `2026-02-27` — `Planificación de sesiones para máster de inteligencia artificial y estrategia de marketing` — `66c97514-d5b1-4182-8902-8a92f7561ce6`
- `2026-02-26` — `Dalux Field y Power BI: Captura de datos e integración de incidencias BIM` — `cf8d253d-bb16-455f-9a83-15387723b0c7`
- `2026-02-26` — `IA implementación y estrategia de automatización para Umbralbim` — `1cb2db05-b149-4704-be03-20100200ac9a`
- `2026-02-25` — `RV: Capacitacion Dynamo- Geosys` — `ebeb207b-4bba-4c7c-8c70-ba30463f778c`
- `2026-02-25` — `Automatización de flujos de trabajo y documentos en Umbralbim` — `ecc2437c-50c8-466d-bcb7-195a0845ff01`
- `2026-02-25` — `Power Automate training plan for BIM programmers at Umbralbim` — `5bf8a5f0-591d-4bd0-966c-4dcd67227093`
- `2026-02-25` — `Técnicas de animación con IA para representación arquitectónica` — `8973fe4d-5510-4dd1-991c-24f7bde58f04`
- `2026-02-24` — `Configuración de plantillas de incidencias en Dalux para gestión BIM en construcción` — `40bbecc0-6bdc-4bc7-817c-17196e0d23a9`
- `2026-02-19` — `Fundamentos de inteligencia artificial generativa para modelado BIM en Revit` — `ab759f79-3184-4194-ab3e-e5085dc925a6`
- `2026-02-18` — `Revisión de índice para guía de bases técnicas y procesos BIM` — `369062f4-9d2a-4c60-9acd-1b2bbe256d59`
- `2026-02-13` — `Planificación de módulo de construcción con Ricardo para máster de tecnologías 4.0` — `8865434e-4331-42f8-b341-a41a87bb5dfd`
- `2026-02-12` — `Revisión final de proyectos de módulo de inteligencia artificial generativa` — `17253e95-64e9-4620-8297-4f14fe86d772`
- `2026-02-10` — `Clase final de máster: Herramientas de IA para escalado, generación de video y audio` — `c8fceaa8-d819-418e-955b-3c3de19aca6d`
- `2026-02-04` — `Get started with Granola` — `fc81fb00-894b-4640-bc89-c29a88f0b4c8`

## Estado final live

### Backlog seguro absorbido

Se ejecutó intake raw-only controlado para:

- los 4 `batch1_recent_unique`;
- los 31 `historic_unique`;
- y 5 casos inicialmente ambiguos que sí podían resolverse por fecha distinta del raw histórico.

Con eso, el monitor live quedó en:

- `41` casos `likely_present`;
- `0` `batch1_recent_unique`;
- `0` `batch1_recent_ambiguous`;
- `0` `historic_unique`;
- `2` `historic_ambiguous`.

### Ambiguos residuales

Los únicos casos que siguen fuera de raw por política V1 son:

- `2026-03-23` — `Konstruedu` — `1d177374-2ff0-42a0-a032-189075f8b4c0`
- `2026-03-23` — `Asesoría discurso` — `5bff2a5a-0c7a-41c6-ae34-d6662325d67f`

Ambos comparten mismo título y misma fecha con raws históricos ya existentes, por lo que no corresponde crear una nueva página raw sin revisión humana.

### Comentarios de revisión dejados live

Se dejó comentario V1 de revisión en:

- `Konstruedu` — raw `3305f443-fb5c-81db-9162-fd70c8574938`
- `Asesoría discurso` — raw `3305f443-fb5c-81e6-a1a5-cc0b2ebd1786`

Esos comentarios incluyen:

- evidencia fuente con `granola_document_id`;
- bloqueo por ambigüedad same-day;
- y la siguiente revisión necesaria para Rick.

## Lectura operativa

- Desde Notion raw, la cola segura ya está absorbida.
- Desde Granola cache, ya no queda backlog seguro pendiente.
- El problema residual ya no es de cobertura masiva, sino de resolución manual de 2 duplicados same-day.

## Falencia estructural

La base raw no persiste hoy `Granola document_id`.

Eso impide una reconciliación 1:1 confiable en familias como:

- `Konstruedu`
- `Asesoría discurso`

Antes de automatizar en serio este tramo, conviene persistir un identificador fuente fuerte en raw.
