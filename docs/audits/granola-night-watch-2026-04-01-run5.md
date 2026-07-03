# Granola Night Watch — 2026-04-01 run5

Generated: 2026-03-31 23:56:14 -03:00

## Summary

- Live worker `http://127.0.0.1:8088/health` still OK; version `0.4.0`, `86` tasks registered, `222` tasks in memory.
- Granola handlers still present: `granola.process_transcript`, `granola.promote_curated_session`, `granola.promote_operational_slice`, `granola.capitalize_raw`, `granola.create_human_task_from_curated_session`, `granola.update_commercial_project_from_curated_session`, `granola.create_followup`, plus legacy alias `granola.promote_session_capitalizable`.
- Raw backlog changed materially versus run4: `notion.read_database` on `Transcripciones Granola` (`3265f443-fb5c-81d7-89b9-e16eacb0082d`) now returns `43` accessible rows, not `50`.
- Current accessible mix is:
  - `3` promoted real raws with governance sync intact.
  - `4` real raws in partial / drifted state.
  - `36` pending real raws.
  - `0` pending raws with Rick acknowledgment.
- The `7` rows no longer accessible to Rick are exactly the prior smoke / temp set:
  - `3265f443-fb5c-815d-b04c-c397acb44a2e`
  - `3265f443-fb5c-816c-9878-c4d68d6543db`
  - `3265f443-fb5c-8178-82df-c28f1ecb9a78`
  - `3265f443-fb5c-8180-881a-c379c70b5a3a`
  - `3265f443-fb5c-8186-8542-c19b10af6df6`
  - `3265f443-fb5c-81f7-9c31-ee53d2126796`
  - `3355f443-fb5c-812b-ba58-f853c452e744`
- Direct `notion.read_page` on those `7` ids now fails with Notion `404 object_not_found`, so they appear removed, unshared, or otherwise no longer readable by integration `Rick`.
- Recent in-memory worker task history shows no organic Notion validation failures. The only failed tasks are the explicit `notion.read_page` probes for the `7` now-inaccessible rows and the older self-inflicted wrong-DB probe `3305f443-fb5c-81ec-89cd-c0cd34c00a08`.
- VM raw intake report is unchanged and healthy: [`C:/Granola/reports/granola-vm-raw-intake-latest.json`](C:/Granola/reports/granola-vm-raw-intake-latest.json) still shows `generated_at=2026-03-31T23:15:54Z`, `selected_count=0`, `prepared_count=0`, and worker preflight OK.
- `C:\Granola\watcher.log` is still dominated by pytest/dev watcher traffic under `C:\Users\david\AppData\Local\Temp\pytest-of-david\...`; no production raw ingest evidence there.
- No safe idempotent live fix was applied in this run.

## Poller

- Direct live VPS PID/log verification remains unavailable from this sandbox.
- Repo-side singleton guard is still present in [`C:/GitHub/umbral-agent-stack-codex/scripts/vps/notion-poller-daemon.py`](C:/GitHub/umbral-agent-stack-codex/scripts/vps/notion-poller-daemon.py):
  - `_claim_pid_file()` blocks a second daemon when the PID is alive.
  - stale PID entries are removed before startup.
  - `SIGTERM` / `SIGINT` handlers still keep cleanup graceful.
- `python -m py_compile scripts/vps/notion-poller-daemon.py` passed again.

## Promoted Real Raws

- `3305f443-fb5c-8184-953d-ebf2190afc57` | `Reunión Con Jorge de Boragó` | <https://www.notion.so/Reuni-n-Con-Jorge-de-Borag-3305f443fb5c8184953debf2190afc57>
  - route executed: `granola.process_transcript`, `granola.promote_curated_session`
  - route missing: `granola.promote_operational_slice`
  - blocker: none for base promotion
  - Rick acknowledged: yes
  - curated page: `3305f443-fb5c-81e8-941d-f1c36724b7a6` | <https://www.notion.so/Reuni-n-Con-Jorge-de-Borag-3305f443fb5c81e8941df1c36724b7a6>
  - governance fields: `Estado=Procesada`, `Fecha que Rick pasó a Notion=2026-03-31`, `Fecha que el agente procesó=2026-03-31`, `URL artefacto` synced

- `3305f443-fb5c-81db-9162-fd70c8574938` | `Konstruedu` | <https://www.notion.so/Konstruedu-3305f443fb5c81db9162fd70c8574938>
  - route executed: `granola.process_transcript`, `granola.promote_curated_session`
  - route missing: `granola.promote_operational_slice`
  - blocker: duplicate-source governance review still open for `granola_document_id=1d177374-2ff0-42a0-a032-189075f8b4c0`
  - Rick acknowledged: yes
  - curated page: `3305f443-fb5c-81cd-ba63-c6d06624f6a2` | <https://www.notion.so/Konstruedu-propuesta-6-cursos-3305f443fb5c81cdba63c6d06624f6a2>
  - governance fields: `Estado=Procesada`, `Fecha que Rick pasó a Notion=2026-03-31`, `Fecha que el agente procesó=2026-03-31`, `URL artefacto` synced

- `3305f443-fb5c-81e6-a1a5-cc0b2ebd1786` | `Asesoría discurso` | <https://www.notion.so/Asesor-a-discurso-3305f443fb5c81e6a1a5cc0b2ebd1786>
  - route executed: `granola.process_transcript`, `granola.promote_curated_session`
  - route missing: `granola.promote_operational_slice`
  - blocker: duplicate-source governance review still open for `granola_document_id=5bff2a5a-0c7a-41c6-ae34-d6662325d67f`
  - Rick acknowledged: yes
  - curated page: `3305f443-fb5c-81f5-9911-c9be3fab3c42` | <https://www.notion.so/Asesor-a-discurso-3305f443fb5c81f59911c9be3fab3c42>
  - governance fields: `Estado=Procesada`, `Fecha que Rick pasó a Notion=2026-03-31`, `Fecha que el agente procesó=2026-03-31`, `URL artefacto` synced

## Partial Promotion / Drift

These `4` raws are real rows still visible in the raw DB, but they are no longer cleanly pending. All `4` still show only `granola.process_transcript` in raw traceability, still miss both `granola.promote_curated_session` and `granola.promote_operational_slice`, and still have `comments_count=0` / `Rick acknowledged = no`.

- `3345f443-fb5c-8146-aaea-f52f11d12ed3` | `BIM Forum` | <https://www.notion.so/BIM-Forum-3345f443fb5c8146aaeaf52f11d12ed3>
  - raw status: `Pendiente`
  - artifact field: <https://www.notion.so/837b8d1851c942f5b0c64a2fb473bbcf>
  - route executed: `granola.process_transcript`
  - routes missing: `granola.promote_curated_session`, `granola.promote_operational_slice`
  - blocker: raw log says an intermediate session was created in `Registro de Sesiones y Transcripciones`, but the raw page still keeps `Estado=Pendiente`, has no promotion trace, and has no review comment.

- `3345f443-fb5c-8152-bd56-e1b3b336bc3d` | `asesoría discorso` | <https://www.notion.so/asesor-a-discorso-3345f443fb5c8152bd56e1b3b336bc3d>
  - raw status: `Pendiente`
  - artifact field: <https://www.notion.so/8da03f3384e04db59d89d5efea555ed0>
  - route executed: `granola.process_transcript`
  - routes missing: `granola.promote_curated_session`, `granola.promote_operational_slice`
  - blocker: raw log says the intermediate session was matched and updated by source URL, and the title was normalized from `discorso` to `discurso`, but the raw page still lacks `Fecha que Rick pasó a Notion`, still keeps `Estado=Pendiente`, and leaves no comment trail.

- `3345f443-fb5c-817f-a2a3-fdbc9285a5e1` | `Revisión final de proyectos de módulo de inteligencia artificial generativa` | <https://www.notion.so/Revisi-n-final-de-proyectos-de-m-dulo-de-inteligencia-artificial-generativa-3345f443fb5c817fa2a3fdbc9285a5e1>
  - raw status: `Procesada`
  - artifact field: <https://www.notion.so/733fe941bfbf44358535b87f9ec8329e>
  - route executed: `granola.process_transcript`
  - routes missing: `granola.promote_curated_session`, `granola.promote_operational_slice`
  - blocker: intermediate session appears to exist, but the raw page has no `Fecha que Rick pasó a Notion`, no `Fecha que el agente procesó`, no promotion path, and no comment acknowledgment.

- `3345f443-fb5c-81c6-9d09-d13599a4a736` | `Konstruedu` | <https://www.notion.so/Konstruedu-3345f443fb5c81c69d09d13599a4a736>
  - raw status: `Pendiente`
  - artifact field: <https://notes.granola.ai/t/0da31eae-2c0a-41ec-b18c-04be2cec4ad6>
  - route executed: `granola.process_transcript`
  - routes missing: `granola.promote_curated_session`, `granola.promote_operational_slice`
  - blocker: `URL artefacto` is holding the source Granola transcript URL instead of a promoted Notion artifact, while the raw log simultaneously claims an intermediate session was created. The row is half-processed and semantically inconsistent.

## Pending Real Raws

- `36` real raws remain fully pending.
- Common live state for all `36`:
  - route executed: `granola.process_transcript`
  - routes missing: `granola.promote_curated_session`, `granola.promote_operational_slice`
  - blocker: no human review and no explicit promotion payload
  - Rick acknowledged: no (`comments_count=0`)

IDs currently still in this clean-pending bucket:

- `3345f443-fb5c-8102-ad45-fa4ad7429bde` | `Introducción a Power BI y modelado de datos con David Moreira` | <https://www.notion.so/Introducci-n-a-Power-BI-y-modelado-de-datos-con-David-Moreira-3345f443fb5c8102ad45fa4ad7429bde>
- `3345f443-fb5c-810e-b334-d53a57e63240` | `Clase final de máster: Herramientas de IA para escalado, generación de video y audio` | <https://www.notion.so/Clase-final-de-m-ster-Herramientas-de-IA-para-escalado-generaci-n-de-video-y-audio-3345f443fb5c810eb334d53a57e63240>
- `3345f443-fb5c-811b-887b-dca9ff0db413` | `Reunión de actualización de la hoja de ruta BIM con socios de Bim Forum Chile` | <https://www.notion.so/Reuni-n-de-actualizaci-n-de-la-hoja-de-ruta-BIM-con-socios-de-Bim-Forum-Chile-3345f443fb5c811b887bdca9ff0db413>
- `3345f443-fb5c-8126-9257-d4bc8a149816` | `Embudo inteligente: estrategias de adquisición de clientes para empresas B2B` | <https://www.notion.so/Embudo-inteligente-estrategias-de-adquisici-n-de-clientes-para-empresas-B2B-3345f443fb5c81269257d4bc8a149816>
- `3345f443-fb5c-812d-8628-ec04dd7531db` | `Granola ef88925a` | <https://www.notion.so/Granola-ef88925a-3345f443fb5c812d8628ec04dd7531db>
- `3345f443-fb5c-812e-931a-c274f4fb47ed` | `Adarcus` | <https://www.notion.so/Adarcus-3345f443fb5c812e931ac274f4fb47ed>
- `3345f443-fb5c-813c-83b3-efd854490d50` | `Automatización de documentos técnicos para flujo de trabajo en DSO` | <https://www.notion.so/Automatizaci-n-de-documentos-t-cnicos-para-flujo-de-trabajo-en-DSO-3345f443fb5c813c83b3efd854490d50>
- `3345f443-fb5c-8143-a9ed-fab91281a776` | `Markdown y herramientas de IA para procesamiento de documentación técnica` | <https://www.notion.so/Markdown-y-herramientas-de-IA-para-procesamiento-de-documentaci-n-t-cnica-3345f443fb5c8143a9edfab91281a776>
- `3345f443-fb5c-814b-bb53-ea5e27353340` | `ACI Autodesk` | <https://www.notion.so/ACI-Autodesk-3345f443fb5c814bbb53ea5e27353340>
- `3345f443-fb5c-815c-b4dd-e7c5e387c39e` | `Automatización de soporte con Power Automate para Umbralbim` | <https://www.notion.so/Automatizaci-n-de-soporte-con-Power-Automate-para-Umbralbim-3345f443fb5c815cb4dde7c5e387c39e>
- `3345f443-fb5c-815d-8b16-f942e1505f9a` | `Revisión de índice para guía de bases técnicas y procesos BIM` | <https://www.notion.so/Revisi-n-de-ndice-para-gu-a-de-bases-t-cnicas-y-procesos-BIM-3345f443fb5c815d8b16f942e1505f9a>
- `3345f443-fb5c-8167-979b-f71cca933a60` | `Konstruedu 2` | <https://www.notion.so/Konstruedu-2-3345f443fb5c8167979bf71cca933a60>
- `3345f443-fb5c-8167-ab54-dc1335cea3d1` | `Get started with Granola` | <https://www.notion.so/Get-started-with-Granola-3345f443fb5c8167ab54dc1335cea3d1>
- `3345f443-fb5c-8168-9f58-cd06d91cf4da` | `Dynamo scripting para selección y ubicación de vistas en planos de Revit` | <https://www.notion.so/Dynamo-scripting-para-selecci-n-y-ubicaci-n-de-vistas-en-planos-de-Revit-3345f443fb5c81689f58cd06d91cf4da>
- `3345f443-fb5c-817b-8fda-f6a7dd05ba3f` | `BIM-Logic` | <https://www.notion.so/BIM-Logic-3345f443fb5c817b8fdaf6a7dd05ba3f>
- `3345f443-fb5c-817d-909f-ee778ffeb9ac` | `Ejercicio doker Diplomado BIM + IA Butic` | <https://www.notion.so/Ejercicio-doker-Diplomado-BIM-IA-Butic-3345f443fb5c817d909fee778ffeb9ac>
- `3345f443-fb5c-818c-81c3-d29631a881f5` | `Webinar Notebooklm` | <https://www.notion.so/Webinar-Notebooklm-3345f443fb5c818c81c3d29631a881f5>
- `3345f443-fb5c-8191-a132-f3c8469601fd` | `Dalux Field y Power BI: Captura de datos e integración de incidencias BIM` | <https://www.notion.so/Dalux-Field-y-Power-BI-Captura-de-datos-e-integraci-n-de-incidencias-BIM-3345f443fb5c8191a132f3c8469601fd>
- `3345f443-fb5c-8193-ab06-ccf21fba4597` | `Bim Forum Grupo Tecnico` | <https://www.notion.so/Bim-Forum-Grupo-Tecnico-3345f443fb5c8193ab06ccf21fba4597>
- `3345f443-fb5c-8193-abad-f63d6853d9f7` | `Técnicas de animación con IA para representación arquitectónica` | <https://www.notion.so/T-cnicas-de-animaci-n-con-IA-para-representaci-n-arquitect-nica-3345f443fb5c8193abadf63d6853d9f7>
- `3345f443-fb5c-8198-8d0b-f2bf16e14c00` | `Planificación de módulo de construcción con Ricardo para máster de tecnologías 4.0` | <https://www.notion.so/Planificaci-n-de-m-dulo-de-construcci-n-con-Ricardo-para-m-ster-de-tecnolog-as-4-0-3345f443fb5c81988d0bf2bf16e14c00>
- `3345f443-fb5c-81ab-b041-c30a819b01bb` | `BIM FOurm` | <https://www.notion.so/BIM-FOurm-3345f443fb5c81abb041c30a819b01bb>
- `3345f443-fb5c-81ad-afe5-e8e1b8373dfe` | `BIM implementación y estrategias de organización del discurso` | <https://www.notion.so/BIM-implementaci-n-y-estrategias-de-organizaci-n-del-discurso-3345f443fb5c81adafe5e8e1b8373dfe>
- `3345f443-fb5c-81b0-9be5-d7d3903dbb41` | `Reunión con Begoña` | <https://www.notion.so/Reuni-n-con-Bego-a-3345f443fb5c81b09be5d7d3903dbb41>
- `3345f443-fb5c-81b5-bc0b-d4be1ebbbde6` | `Geosys Dynamo Clase 4` | <https://www.notion.so/Geosys-Dynamo-Clase-4-3345f443fb5c81b5bc0bd4be1ebbbde6>
- `3345f443-fb5c-81b7-9df1-d89a5bcf99de` | `Geosys` | <https://www.notion.so/Geosys-3345f443fb5c81b79df1d89a5bcf99de>
- `3345f443-fb5c-81bf-93a2-c6741d236b30` | `RV: Capacitacion Dynamo- Geosys` | <https://www.notion.so/RV-Capacitacion-Dynamo-Geosys-3345f443fb5c81bf93a2c6741d236b30>
- `3345f443-fb5c-81c6-b5dd-d21626df8756` | `Automatización de flujos de trabajo y documentos en Umbralbim` | <https://www.notion.so/Automatizaci-n-de-flujos-de-trabajo-y-documentos-en-Umbralbim-3345f443fb5c81c6b5ddd21626df8756>
- `3345f443-fb5c-81c9-b323-e6073e3d68b6` | `Power Automate training plan for BIM programmers at Umbralbim` | <https://www.notion.so/Power-Automate-training-plan-for-BIM-programmers-at-Umbralbim-3345f443fb5c81c9b323e6073e3d68b6>
- `3345f443-fb5c-81ce-9154-d10bc2f7bde0` | `Asesoria discurso` | <https://www.notion.so/Asesoria-discurso-3345f443fb5c81ce9154d10bc2f7bde0>
- `3345f443-fb5c-81dd-833c-e546f9fef114` | `Reunión con Pablo` | <https://www.notion.so/Reuni-n-con-Pablo-3345f443fb5c81dd833ce546f9fef114>
- `3345f443-fb5c-81e5-ae85-dcdfbf53a210` | `IA implementación y estrategia de automatización para Umbralbim` | <https://www.notion.so/IA-implementaci-n-y-estrategia-de-automatizaci-n-para-Umbralbim-3345f443fb5c81e5ae85dcdfbf53a210>
- `3345f443-fb5c-81e5-b669-f173d4865eda` | `Reunbión con N8n` | <https://www.notion.so/Reunbi-n-con-N8n-3345f443fb5c81e5b669f173d4865eda>
- `3345f443-fb5c-81ed-9107-f090f13bd63a` | `Configuración de plantillas de incidencias en Dalux para gestión BIM en construcción` | <https://www.notion.so/Configuraci-n-de-plantillas-de-incidencias-en-Dalux-para-gesti-n-BIM-en-construcci-n-3345f443fb5c81ed9107f090f13bd63a>
- `3345f443-fb5c-81f3-9bfc-cddc09c1b4ca` | `Fundamentos de inteligencia artificial generativa para modelado BIM en Revit` | <https://www.notion.so/Fundamentos-de-inteligencia-artificial-generativa-para-modelado-BIM-en-Revit-3345f443fb5c81f39bfccddc09c1b4ca>
- `3345f443-fb5c-81f9-b687-fe0fb9d36bce` | `Planificación de sesiones para máster de inteligencia artificial y estrategia de marketing` | <https://www.notion.so/Planificaci-n-de-sesiones-para-m-ster-de-inteligencia-artificial-y-estrategia-de-marketing-3345f443fb5c81f9b687fe0fb9d36bce>
