---
fuente: Notion AI (workspace Umbral, desde Gobernanza/Control Room)
prompt_origen: Prompt 2 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: agentes custom, DBs canónicas, vistas, legacy V1, créditos
modo: read-only
estado_completitud: COMPLETE_WITH_VISIBILITY_LIMITS (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

# Auditoría read-only — Workspace Umbral BIM

Alcance: solo superficies Notion visibles. No ejecuté agentes ni edité nada. Nota previa: Notion no me expone un listado central de agentes con triggers/modelo/ejecuciones; lo que sigue es lo verificable desde páginas y bases.

## 1. Agentes custom (asistentes Notion)

Inventario del hub **Asistentes Notion** dentro de Sistemas y Automatizaciones.[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21)

| Nombre | Qué hace | Trigger | Estado | Modelo | Última ejecución | Etiqueta |
| --- | --- | --- | --- | --- | --- | --- |
| Analista | Instrucciones de Notion AI personal: análisis metódico, basado en datos (fuente de este chat)[[2]](https://app.notion.com/p/Analista-3a05f443fb5c80dfaa46dd22b2552033?pvs=21) | Manual (chat) | ON (activa) | No visible | No visible | ACTIVE_HEALTHY |
| Claudio | Asistente local de edición/esquema/extracción; explícitamente NO capitaliza ni arquitectura[[3]](https://app.notion.com/p/Claudio-3345f443fb5c8059b27ceb5e1dfb30fa?pvs=21) | Manual (chat) | UNKNOWN | No visible | No visible | UNKNOWN |
| Analista Power BI - AEC Expert | No abierta; solo título visible[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21) | UNKNOWN | UNKNOWN | — | — | UNKNOWN |
| Docente 3 | No abierta; título sugiere serie docente (¿1 y 2 borrados?)[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21) | UNKNOWN | UNKNOWN | — | — | UNKNOWN |
| Transcriptor | No abierta; existe análisis de solapamiento con flujo Granola[[4]](https://app.notion.com/p/An-lisis-Transcriptor-Granola-vs-Docente-1ee25a9e5b2f41e3941e668a957b47d1?pvs=21) | UNKNOWN | UNKNOWN | — | — | UNKNOWN |
| Experto en Grasshopper | No abierta[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21) | UNKNOWN | UNKNOWN | — | — | UNKNOWN |
| Asesor Comercial | No abierta[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21) | UNKNOWN | UNKNOWN | — | — | UNKNOWN |
| Arquitecto de Workspace | Retirado del registry activo; archivado 2026-05-04, "nunca se activó como OpenClaw"[[5]](https://app.notion.com/p/ARCHIVADO-2026-05-04-Arquitecto-de-Workspace-34c5f443fb5c809e8c20f2976d1cd14f?pvs=21) | — | OFF | — | — | OBSOLETE |

Fuera de alcance Notion pero operando sobre el workspace: **Rick/OpenClaw** (worker VPS: escribe en Transcripciones Granola, Tareas, Bandejas, Dashboard; poller de comentarios en Control Room) y agentes de repo (Coordinador de Agentes, Operador OpenClaw VPS).[[6]](https://app.notion.com/p/Gobernanza-Notion-5b348139464b46fbb7f38c5a36f6c7d5?pvs=21)

## 2. Databases canónicas

| Nombre | Propósito | ~Filas | Última actividad visible | Quién alimenta | Etiqueta |
| --- | --- | --- | --- | --- | --- |
| Transcripciones Granola | Intake + clasificación + capitalización V2 de reuniones[[7]](https://app.notion.com/p/Sesiones-y-Transcripciones-3305f443fb5c809982ddfc62baafb770?pvs=21) | 133 | Creación 2026-07-16; ediciones hoy | Agente (pipeline) + humano | ACTIVE_HEALTHY |
| Registro de Tareas y Próximas Acciones | Capa de tareas operativas humana[[8]](https://app.notion.com/p/Tareas-y-Proximas-Acciones-3305f443fb5c80c8acc0de90ac349faf?pvs=21) | 33 | Creación 2026-07-17 (hoy) | Ambos | ACTIVE_HEALTHY |
| Publicaciones | Pipeline editorial con gates humanos, bajo hub Sistema Editorial Rick[[9]](https://app.notion.com/p/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a?pvs=21) | 12 | Creación 2026-07-08 | Ambos (rick-* vía repo + gates humanos) | ACTIVE_HEALTHY |
| Bandeja de revisión - Rick | Staging/revisión de outputs de Rick[[6]](https://app.notion.com/p/Gobernanza-Notion-5b348139464b46fbb7f38c5a36f6c7d5?pvs=21) | 25 | Última fila creada 2026-03-17; panel muestra 0 por revisar[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | Agente | ACTIVE_NOISY (4 meses sin filas nuevas) |
| Bandeja Puente | Coordinación cruzada entre frentes/agentes | 7 | Última fila 2026-05-19; 7 items "vivos" estancados[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | Agente | ACTIVE_NOISY |
| Tareas — Umbral Agent Stack | Eventos de ejecución del worker (capa técnica, no humana)[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | 22 | Última fila 2026-05-19 | Agente | ACTIVE_NOISY |
| Proyectos — Umbral | Proyectos técnicos del stack | 10 | Última fila 2026-04-13 | Ambos | UNKNOWN (poca rotación) |
| Registro de Sesiones y Transcripciones (V1) | Ex-registro de sesiones; retirada del flujo V2, solo validación defensiva[[11]](https://app.notion.com/p/Sesiones-y-Transcripciones-3305f443fb5c809982ddfc62baafb770?pvs=21) | UNKNOWN (base no accesible; docs indican retirada/en papelera) | Página-nota editada 2026-04-15 | Nadie (por contrato) | OBSOLETE |
| Control Room | No es DB: página de comentarios que el poller de Rick lee cada ciclo[[6]](https://app.notion.com/p/Gobernanza-Notion-5b348139464b46fbb7f38c5a36f6c7d5?pvs=21) | n/a | Referenciada como activa en Gobernanza (2026-07-14) | Humano (comentarios) + Rick (replies) | UNKNOWN (no localicé la página en sí) |

## 3. Vistas de revisión / dashboards

| Página | Ritual | ¿Se usa? | Etiqueta |
| --- | --- | --- | --- |
| OpenClaw (panel operativo)[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | Revisión humana: qué aprobar/destrabar; resumen ejecutivo | Sí — actualizado 2026-07-14 10:00 UTC por cron | ACTIVE_HEALTHY |
| Dashboard Rick[[12]](https://app.notion.com/p/Dashboard-Rick-3265f443fb5c816d9ce8c5d6cf075f9c?pvs=21) | Salud técnica del stack (cron.hourly: upd 24 · fail 0) | Sí — actualizado 2026-07-14 | ACTIVE_HEALTHY |
| Alertas del Supervisor[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | Alertas automáticas | No abierta | UNKNOWN |
| 📊 Pipeline Editorial — Métricas[[10]](https://app.notion.com/p/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca?pvs=21) | Métricas editoriales | No abierta | UNKNOWN |
| Dashboard Operativo — Umbral BOT & Multi-agente[[13]](https://app.notion.com/p/Dashboard-Operativo-Umbral-BOT-Multi-agente-3725f443fb5c8166babad6198933598c?pvs=21) | Gates del sistema umbral-bot-2 (frente distinto a OpenClaw) | Última edición 2026-06-01 | UNKNOWN — posible dashboard paralelo |
| Bitácora Plan Q2-2026[[14]](https://app.notion.com/p/Bit-cora-Plan-Q2-2026-0d4aa52277f1428f80026ee33082f69e?pvs=21) | Seguimiento OKR/objetivos Q2 | Última edición 2026-04-30; Q3 ya empezó | OBSOLETE como ritual (valor histórico) |

## 4. Páginas de automatización / instrucciones

| Página | Sirve a | Vigencia |
| --- | --- | --- |
| Analista[[2]](https://app.notion.com/p/Analista-3a05f443fb5c80dfaa46dd22b2552033?pvs=21) | Notion AI personal | Vigente |
| Claudio[[3]](https://app.notion.com/p/Claudio-3345f443fb5c8059b27ceb5e1dfb30fa?pvs=21) | Asistente Notion de edición local | Vigente |
| Gobernanza Notion[[6]](https://app.notion.com/p/Gobernanza-Notion-5b348139464b46fbb7f38c5a36f6c7d5?pvs=21) | Rick, Enlace, poller; matriz de superficies y reglas de escritura | Vigente (editada 2026-07-14) |
| Sesiones y Transcripciones (nota contrato V1→V2)[[11]](https://app.notion.com/p/Sesiones-y-Transcripciones-3305f443fb5c809982ddfc62baafb770?pvs=21) | Agentes que aún arrastren URLs legacy | Vigente como guardrail defensivo |
| Sistema Editorial Rick (hub)[[9]](https://app.notion.com/p/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a?pvs=21) | Flujo editorial + reglas DB Publicaciones | Vigente |
| Sistema Editorial Rick (en Proyectos técnicos - Rick)[[15]](https://app.notion.com/p/Sistema-Editorial-Rick-31e5f443fb5c8180bec7cbcda641b3b7?pvs=21) | Registro técnico del mismo sistema | Duplicado documentado; semi-legacy |
| [ARCHIVADO 2026-05-04] Arquitecto de Workspace[[5]](https://app.notion.com/p/ARCHIVADO-2026-05-04-Arquitecto-de-Workspace-34c5f443fb5c809e8c20f2976d1cd14f?pvs=21) | Ex-agente notion_governor | Legacy (bien archivado) |
| Asistentes restantes (Power BI, Docente 3, Transcriptor, Grasshopper, Asesor Comercial)[[1]](https://app.notion.com/p/Asistentes-Notion-2c05f443fb5c80639e8bca832cf07808?pvs=21) | Asistentes Notion | UNKNOWN (no abiertas) |

## 5. Legacy V1

| Superficie | Evidencia de abandono | Etiqueta |
| --- | --- | --- |
| Registro de Sesiones y Transcripciones (V1) | Página-nota la declara retirada del flujo V2; docs del repo la dan por retirada/en papelera[[11]](https://app.notion.com/p/Sesiones-y-Transcripciones-3305f443fb5c809982ddfc62baafb770?pvs=21) | OBSOLETE |
| Página "Analista" ×3: activa[[2]](https://app.notion.com/p/Analista-3a05f443fb5c80dfaa46dd22b2552033?pvs=21), copia 2026-05-19[[16]](https://app.notion.com/p/Analista-3655f443fb5c8082bf09de6e2dedd646?pvs=21), archivada 2026-03-31[[17]](https://app.notion.com/p/Analista-3345f443fb5c8036b2fbca699570c413?pvs=21) | Dos residuos idénticos de la instrucción activa | DUPLICATE |
| Sistema Editorial Rick ×2[[9]](https://app.notion.com/p/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a?pvs=21)[[15]](https://app.notion.com/p/Sistema-Editorial-Rick-31e5f443fb5c8180bec7cbcda641b3b7?pvs=21) | La propia página del hub reconoce la duplicación y declara canónico el hub | DUPLICATE |
| Cronograma Máster AEC 4.0 - V1 (base en zona cliente B.) | Sufijo "V1" sin V2 visible; contenido de 2025-11 a 2026-04 | UNKNOWN — verificar |
| Archivo legacy — entregables sueltos[[18]](https://app.notion.com/p/Archivo-legacy-entregables-sueltos-3245f443fb5c8163a23cfc092a03681f?pvs=21) | Ya consolidado en Archivo histórico | OBSOLETE (correctamente archivado) |

## 6. Créditos / uso

**UNKNOWN.** No tengo visibilidad del consumo de créditos Notion AI ni de un log de ejecuciones de agentes Notion. Señal indirecta (no es créditos Notion): Dashboard Rick reporta actividad del worker VPS — `upd 24 · skip 0 · fail 0 · reads 72 · writes 24 · cron.hourly`.[[12]](https://app.notion.com/p/Dashboard-Rick-3265f443fb5c816d9ce8c5d6cf075f9c?pvs=21)

---

## 5 oportunidades de limpieza/consolidación

1. **Bandeja de revisión - Rick estancada**: 25 filas, ninguna nueva desde 2026-03-17 y panel en "0 por revisar". Decidir: archivarla como gate o reactivar el flujo que la alimenta; hoy es superficie viva sin insumo.
2. **Items "Instrucción Notion: [n/n]…" varados**: 5+ items en Bandeja Puente y Tareas — UAS esperando desde mayo con la misma acción genérica ("Rick debe regularizar"). Limpiar el lote y endurecer el poller para no crear items por fragmento.
3. **Consolidar Sistema Editorial Rick**: dos páginas homónimas (hub canónico vs registro en Proyectos técnicos - Rick). Vaciar la segunda a un puntero simple para eliminar la ambigüedad que ya obligó a una nota de gobernanza.
4. **Purgar instrucciones "Analista" duplicadas**: mantener solo la activa; borrar la copia de mayo y la archivada de marzo, que pueden confundir búsquedas de agentes.
5. **Cerrar deuda de schema en Publicaciones**: 18 propiedades extra sin decisión y `Proyecto` como texto (pendiente convertir a relation) desde la auditoría del 2026-04-22, con 3 DBs candidatas de proyectos coexistiendo (Proyectos — Umbral, Proyectos técnicos - Rick, Asesorías & Proyectos) — esa triplicidad de "proyectos" es en sí candidata a consolidación.

## UNKNOWNS

- Triggers, modelo, estado ON/OFF y última ejecución de los asistentes Notion (no expuestos en las superficies visibles).
- Ubicación exacta de la página Control Room (referenciada en Gobernanza y repo; no la localicé por búsqueda).
- Contenido/uso real de Alertas del Supervisor y Pipeline Editorial — Métricas (no abiertas).
- Consumo de créditos Notion AI y volumen de ejecuciones de agentes.
- Vigencia de 5 asistentes Notion no abiertos y existencia de V2 para el cronograma "V1" del programa docente (cliente B.).
- Estado real de la base V1 de sesiones (¿en papelera o solo retirada del flujo?).
