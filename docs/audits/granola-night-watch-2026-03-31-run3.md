# Granola Night Watch � 2026-03-31 run3

Generated: 2026-03-31 16:58:07 -03:00

## Summary

- Worker local `http://127.0.0.1:8088/health` OK; Granola handlers present: `granola.process_transcript`, `granola.promote_curated_session`, `granola.promote_operational_slice`, `granola.create_human_task_from_curated_session`, `granola.update_commercial_project_from_curated_session`, `granola.capitalize_raw`, `granola.create_followup`.
- Raw backlog live: 49 total = 6 smoke/test from 2026-03-17, 3 promoted real raws, 40 real pending raws.
- Candidate raws all retain only `ingest_path=granola.process_transcript`; none shows raw comments or Rick acknowledgment.
- Promoted raws had governance drift; fixed in place by syncing `Fecha que Rick pas� a Notion=2026-03-31` and `Trazabilidad` with `promotion_path=granola.promote_curated_session` + curated page ids.
- Local worker logs in `.tmp/worker-local-8088.err.log` show no recent Notion validation/runtime errors; in-memory `/tasks` shows only successful read/poll/update calls in this run.
- VPS poller singleton guard remains present in repo-side `scripts/vps/notion-poller-daemon.py`, but this sandbox still cannot directly inspect the live VPS PID/log state.

## Promoted Raws

- `3305f443-fb5c-8184-953d-ebf2190afc57` | Reunión Con Jorge de Boragó | https://www.notion.so/Reuni-n-Con-Jorge-de-Borag-3305f443fb5c8184953debf2190afc57
  route executed: `granola.promote_curated_session` (confirmed by curated `URL fuente` match / raw comments)
  route missing: raw governance sync was missing before this run; now fixed.
  blocker: none for base promotion.
  Rick acknowledgment: yes. Raw comment confirms curated promotion to page `3305f443-fb5c-81e8-941d-f1c36724b7a6`.
  fields after fix: `Fecha que Rick pas� a Notion=2026-03-31`; `Trazabilidad` now points to curated page `https://www.notion.so/Reuni-n-Con-Jorge-de-Borag-3305f443fb5c81e8941df1c36724b7a6`.

- `3305f443-fb5c-81db-9162-fd70c8574938` | Konstruedu | https://www.notion.so/Konstruedu-3305f443fb5c81db9162fd70c8574938
  route executed: `granola.promote_curated_session` (confirmed by curated `URL fuente` match / raw comments)
  route missing: raw governance sync was missing before this run; now fixed.
  blocker: none for base promotion.
  Rick acknowledgment: yes. Raw comments show curated promotion, capitalization to bridge/follow-up, and a 2026-03-31 governance review comment about same-day duplicate source document `1d177374-2ff0-42a0-a032-189075f8b4c0`.
  fields after fix: `Fecha que Rick pas� a Notion=2026-03-31`; `Trazabilidad` now points to curated page `https://www.notion.so/Konstruedu-propuesta-6-cursos-3305f443fb5c81cdba63c6d06624f6a2`.

- `3305f443-fb5c-81e6-a1a5-cc0b2ebd1786` | Asesoría discurso | https://www.notion.so/Asesor-a-discurso-3305f443fb5c81e6a1a5cc0b2ebd1786
  route executed: `granola.promote_curated_session` (confirmed by curated `URL fuente` match / raw comments)
  route missing: raw governance sync was missing before this run; now fixed.
  blocker: none for base promotion.
  Rick acknowledgment: yes. Raw comments show curated promotion and a 2026-03-31 governance review comment about same-day duplicate source document `5bff2a5a-0c7a-41c6-ae34-d6662325d67f`.
  fields after fix: `Fecha que Rick pas� a Notion=2026-03-31`; `Trazabilidad` now points to curated page `https://www.notion.so/Asesor-a-discurso-3305f443fb5c81f59911c9be3fab3c42`.

## Pending Real Raws

All 40 pending raws share the same current state unless noted otherwise:
- route executed: `granola.process_transcript` (from `Trazabilidad`)
- routes missing: `granola.promote_curated_session`; `granola.promote_operational_slice`
- blocker: no human review / no explicit promotion payload yet
- Rick acknowledgment: none (`comments_count=0`)

- `3345f443-fb5c-8167-ab54-dc1335cea3d1` | 2026-02-04 | Get started with Granola | https://www.notion.so/Get-started-with-Granola-3345f443fb5c8167ab54dc1335cea3d1
- `3345f443-fb5c-810e-b334-d53a57e63240` | 2026-02-10 | Clase final de máster: Herramientas de IA para escalado, generación de video y audio | https://www.notion.so/Clase-final-de-m-ster-Herramientas-de-IA-para-escalado-generaci-n-de-video-y-audio-3345f443fb5c810eb334d53a57e63240
- `3345f443-fb5c-817f-a2a3-fdbc9285a5e1` | 2026-02-12 | Revisión final de proyectos de módulo de inteligencia artificial generativa | https://www.notion.so/Revisi-n-final-de-proyectos-de-m-dulo-de-inteligencia-artificial-generativa-3345f443fb5c817fa2a3fdbc9285a5e1
- `3345f443-fb5c-8198-8d0b-f2bf16e14c00` | 2026-02-13 | Planificación de módulo de construcción con Ricardo para máster de tecnologías 4.0 | https://www.notion.so/Planificaci-n-de-m-dulo-de-construcci-n-con-Ricardo-para-m-ster-de-tecnolog-as-4-0-3345f443fb5c81988d0bf2bf16e14c00
- `3345f443-fb5c-815d-8b16-f942e1505f9a` | 2026-02-18 | Revisión de índice para guía de bases técnicas y procesos BIM | https://www.notion.so/Revisi-n-de-ndice-para-gu-a-de-bases-t-cnicas-y-procesos-BIM-3345f443fb5c815d8b16f942e1505f9a
- `3345f443-fb5c-81f3-9bfc-cddc09c1b4ca` | 2026-02-19 | Fundamentos de inteligencia artificial generativa para modelado BIM en Revit | https://www.notion.so/Fundamentos-de-inteligencia-artificial-generativa-para-modelado-BIM-en-Revit-3345f443fb5c81f39bfccddc09c1b4ca
- `3345f443-fb5c-81ed-9107-f090f13bd63a` | 2026-02-24 | Configuración de plantillas de incidencias en Dalux para gestión BIM en construcción | https://www.notion.so/Configuraci-n-de-plantillas-de-incidencias-en-Dalux-para-gesti-n-BIM-en-construcci-n-3345f443fb5c81ed9107f090f13bd63a
- `3345f443-fb5c-81c6-b5dd-d21626df8756` | 2026-02-25 | Automatización de flujos de trabajo y documentos en Umbralbim | https://www.notion.so/Automatizaci-n-de-flujos-de-trabajo-y-documentos-en-Umbralbim-3345f443fb5c81c6b5ddd21626df8756
- `3345f443-fb5c-81c9-b323-e6073e3d68b6` | 2026-02-25 | Power Automate training plan for BIM programmers at Umbralbim | https://www.notion.so/Power-Automate-training-plan-for-BIM-programmers-at-Umbralbim-3345f443fb5c81c9b323e6073e3d68b6
- `3345f443-fb5c-81bf-93a2-c6741d236b30` | 2026-02-25 | RV: Capacitacion Dynamo- Geosys | https://www.notion.so/RV-Capacitacion-Dynamo-Geosys-3345f443fb5c81bf93a2c6741d236b30
- `3345f443-fb5c-8193-abad-f63d6853d9f7` | 2026-02-25 | Técnicas de animación con IA para representación arquitectónica | https://www.notion.so/T-cnicas-de-animaci-n-con-IA-para-representaci-n-arquitect-nica-3345f443fb5c8193abadf63d6853d9f7
- `3345f443-fb5c-8191-a132-f3c8469601fd` | 2026-02-26 | Dalux Field y Power BI: Captura de datos e integración de incidencias BIM | https://www.notion.so/Dalux-Field-y-Power-BI-Captura-de-datos-e-integraci-n-de-incidencias-BIM-3345f443fb5c8191a132f3c8469601fd
- `3345f443-fb5c-81e5-ae85-dcdfbf53a210` | 2026-02-26 | IA implementación y estrategia de automatización para Umbralbim | https://www.notion.so/IA-implementaci-n-y-estrategia-de-automatizaci-n-para-Umbralbim-3345f443fb5c81e5ae85dcdfbf53a210
- `3345f443-fb5c-815c-b4dd-e7c5e387c39e` | 2026-02-27 | Automatización de soporte con Power Automate para Umbralbim | https://www.notion.so/Automatizaci-n-de-soporte-con-Power-Automate-para-Umbralbim-3345f443fb5c815cb4dde7c5e387c39e
- `3345f443-fb5c-81f9-b687-fe0fb9d36bce` | 2026-02-27 | Planificación de sesiones para máster de inteligencia artificial y estrategia de marketing | https://www.notion.so/Planificaci-n-de-sesiones-para-m-ster-de-inteligencia-artificial-y-estrategia-de-marketing-3345f443fb5c81f9b687fe0fb9d36bce
- `3345f443-fb5c-8168-9f58-cd06d91cf4da` | 2026-03-02 | Dynamo scripting para selección y ubicación de vistas en planos de Revit | https://www.notion.so/Dynamo-scripting-para-selecci-n-y-ubicaci-n-de-vistas-en-planos-de-Revit-3345f443fb5c81689f58cd06d91cf4da
- `3345f443-fb5c-811b-887b-dca9ff0db413` | 2026-03-02 | Reunión de actualización de la hoja de ruta BIM con socios de Bim Forum Chile | https://www.notion.so/Reuni-n-de-actualizaci-n-de-la-hoja-de-ruta-BIM-con-socios-de-Bim-Forum-Chile-3345f443fb5c811b887bdca9ff0db413
- `3345f443-fb5c-8102-ad45-fa4ad7429bde` | 2026-03-03 | Introducción a Power BI y modelado de datos con David Moreira | https://www.notion.so/Introducci-n-a-Power-BI-y-modelado-de-datos-con-David-Moreira-3345f443fb5c8102ad45fa4ad7429bde
- `3345f443-fb5c-813c-83b3-efd854490d50` | 2026-03-04 | Automatización de documentos técnicos para flujo de trabajo en DSO | https://www.notion.so/Automatizaci-n-de-documentos-t-cnicos-para-flujo-de-trabajo-en-DSO-3345f443fb5c813c83b3efd854490d50
- `3345f443-fb5c-8126-9257-d4bc8a149816` | 2026-03-04 | Embudo inteligente: estrategias de adquisición de clientes para empresas B2B | https://www.notion.so/Embudo-inteligente-estrategias-de-adquisici-n-de-clientes-para-empresas-B2B-3345f443fb5c81269257d4bc8a149816
- `3345f443-fb5c-8143-a9ed-fab91281a776` | 2026-03-04 | Markdown y herramientas de IA para procesamiento de documentación técnica | https://www.notion.so/Markdown-y-herramientas-de-IA-para-procesamiento-de-documentaci-n-t-cnica-3345f443fb5c8143a9edfab91281a776
- `3345f443-fb5c-81e5-b669-f173d4865eda` | 2026-03-04 | Reunbión con N8n | https://www.notion.so/Reunbi-n-con-N8n-3345f443fb5c81e5b669f173d4865eda
- `3345f443-fb5c-812e-931a-c274f4fb47ed` | 2026-03-06 | Adarcus | https://www.notion.so/Adarcus-3345f443fb5c812e931ac274f4fb47ed
- `3345f443-fb5c-81ad-afe5-e8e1b8373dfe` | 2026-03-06 | BIM implementación y estrategias de organización del discurso | https://www.notion.so/BIM-implementaci-n-y-estrategias-de-organizaci-n-del-discurso-3345f443fb5c81adafe5e8e1b8373dfe
- `3345f443-fb5c-817b-8fda-f6a7dd05ba3f` | 2026-03-09 | BIM-Logic | https://www.notion.so/BIM-Logic-3345f443fb5c817b8fdaf6a7dd05ba3f
- `3345f443-fb5c-81b7-9df1-d89a5bcf99de` | 2026-03-11 | Geosys | https://www.notion.so/Geosys-3345f443fb5c81b79df1d89a5bcf99de
- `3345f443-fb5c-8167-979b-f71cca933a60` | 2026-03-12 | Konstruedu | https://www.notion.so/Konstruedu-3345f443fb5c8167979bf71cca933a60
- `3345f443-fb5c-81b0-9be5-d7d3903dbb41` | 2026-03-13 | Reunión con Begoña | https://www.notion.so/Reuni-n-con-Bego-a-3345f443fb5c81b09be5d7d3903dbb41
- `3345f443-fb5c-81ce-9154-d10bc2f7bde0` | 2026-03-16 | Asesoria discurso | https://www.notion.so/Asesoria-discurso-3345f443fb5c81ce9154d10bc2f7bde0
- `3345f443-fb5c-818c-81c3-d29631a881f5` | 2026-03-16 | Webinar Notebooklm | https://www.notion.so/Webinar-Notebooklm-3345f443fb5c818c81c3d29631a881f5
- `3345f443-fb5c-814b-bb53-ea5e27353340` | 2026-03-17 | ACI Autodesk | https://www.notion.so/ACI-Autodesk-3345f443fb5c814bbb53ea5e27353340
- `3345f443-fb5c-81dd-833c-e546f9fef114` | 2026-03-17 | Reunión con Pablo | https://www.notion.so/Reuni-n-con-Pablo-3345f443fb5c81dd833ce546f9fef114
- `3345f443-fb5c-81ab-b041-c30a819b01bb` | 2026-03-18 | BIM FOurm | https://www.notion.so/BIM-FOurm-3345f443fb5c81abb041c30a819b01bb
- `3345f443-fb5c-81b5-bc0b-d4be1ebbbde6` | 2026-03-18 | Geosys Dynamo Clase 4 | https://www.notion.so/Geosys-Dynamo-Clase-4-3345f443fb5c81b5bc0bd4be1ebbbde6
- `3345f443-fb5c-817d-909f-ee778ffeb9ac` | 2026-03-24 | Ejercicio doker Diplomado BIM + IA Butic | https://www.notion.so/Ejercicio-doker-Diplomado-BIM-IA-Butic-3345f443fb5c817d909fee778ffeb9ac
- `3345f443-fb5c-812d-8628-ec04dd7531db` | 2026-03-27 | Granola ef88925a | https://www.notion.so/Granola-ef88925a-3345f443fb5c812d8628ec04dd7531db
- `3345f443-fb5c-8152-bd56-e1b3b336bc3d` | 2026-03-30 | asesoría discorso | https://www.notion.so/asesor-a-discorso-3345f443fb5c8152bd56e1b3b336bc3d
- `3345f443-fb5c-8146-aaea-f52f11d12ed3` | 2026-03-30 | BIM Forum | https://www.notion.so/BIM-Forum-3345f443fb5c8146aaeaf52f11d12ed3
- `3345f443-fb5c-8193-ab06-ccf21fba4597` | 2026-03-30 | Bim Forum Grupo Tecnico | https://www.notion.so/Bim-Forum-Grupo-Tecnico-3345f443fb5c8193ab06ccf21fba4597
- `3345f443-fb5c-81c6-9d09-d13599a4a736` | 2026-03-30 | Konstruedu | https://www.notion.so/Konstruedu-3345f443fb5c81c69d09d13599a4a736

## Notes

- Ignored smoke/test raws from 2026-03-17 because their status did not change in this run.
- `Konstruedu` and `Asesor�a discurso` now have raw governance fields synced, but both still carry open source-level ambiguity about same-day duplicate Granola documents that Rick flagged for manual review.
