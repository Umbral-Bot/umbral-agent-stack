# Plan híbrido de capitalización Granola — Notion agent (cirujano) + UAS (motor determinista)

Fecha: 2026-07-16
Rama: `claude/plan-granola-capitalization-hybrid`
Estado: PLAN — nada de este documento está implementado. No se tocó código de capitalización, no se hizo deploy, no se gastaron créditos Notion, no se reactivó ningún trigger.

Gate de este documento: **`CAP_HYBRID_PLAN_READY`**

---

## 0. Pregunta que responde este plan

Tras el piloto V2.1/V2.1.1 (notion-governance PR #16, squash `ebf7d417`):

- Kimi K2.7 Code en el agente Notion "Transcriptor Granola": 3/3 limpio (0 fixes, 0 "log miente"), pero el workspace se quedó sin créditos a mitad de la comparación.
- Límite operativo declarado: el agente Notion es viable solo como **cirujano manual de bajo volumen** (~300 créditos/mes), no como motor de batch sobre las ~95 filas raw.

¿Conviene replicar la capitalización en el stack (Worker/Rick/OpenClaw) para no quemar créditos Notion?

**Respuesta corta: sí al híbrido, no al clon.** El Worker ya tiene el 70-80% de las primitivas deterministas necesarias (escritura schema-driven a la DB humana de tareas, preservación de Trazabilidad, gates de clasificación, dedup por título). Lo que falta es un slice determinista raw→Tarea con verify-after-write. Lo que NO conviene es clonar el prompt del agente Notion dentro de OpenClaw: eso replicaría el modo de fallo "log miente" de Haiku en otro chat-LLM, sin ganar las garantías que da el código.

---

## 1. As-is — mapa de responsabilidades hoy

Convención de este documento: **[VPS]** = evidencia observada en runtime el 2026-07-16 (SSH read-only, usuario `rick@srv1431451`); **[repo]** = inferencia desde código/docs en `main` (`3244916a`); **[gov]** = contrato en notion-governance (`origin/main` `ebf7d41`).

### 1.1 Notion agent "Transcriptor Granola" (juicio)

- **[gov]** Modelo live: Kimi K2.7 Code. Enmienda V2.1.1. Triggers OFF (ambos). Solo ejecución manual.
- Qué hace bien (juicio): clasificación Dominio/Tipo/Destino 8/8 correcta entre ambos pilotos; aplica la Enmienda Proyecto-vs-Tarea; matching Cliente/Partner con evidencia; recomendaciones de revisión accionables.
- Qué hace (mecánico, con riesgo en Haiku, limpio en Kimi n=3): escribir la tarea en Registro de Tareas, URL artefacto, Trazabilidad append, resets de flags, relecturas de verificación.
- Alcance de escritura real: solo el raw + Registro de Tareas y Próximas Acciones. Todo lo demás lookup.
- Costo: ~7 corridas agotaron los créditos del workspace. **No es motor de batch.**

### 1.2 Worker UAS (mecánico determinista)

Salud: **[VPS]** `umbral-worker.service` activo (uvicorn :8088, health OK, 100+ tasks registradas, incluidas todas las `granola.*`).

| Capacidad | Estado | Evidencia |
|---|---|---|
| `granola.process_transcript` — ingest raw + reconciliación finality + Trazabilidad de ingest + verificación de bloques (`_verify_raw_page_persistence`) | vivo, probado a escala (95 filas P1.1b, 0 FAIL) | [VPS]+[repo] `worker/tasks/granola.py:1671` |
| `granola.classify_raw` — clasificador LLM (gemini_flash → fallback gemini_pro) que escribe los 4 campos V2 + Estado agente | desplegado pero **roto**: sin proveedor LLM vivo (ver 1.5) | [VPS] journalctl: `GOOGLE_API_KEY not configured` (2026-07-16) |
| `granola.capitalize_raw` — capitalización explícita a superficies **técnicas del stack** (Proyectos técnicos - Rick, Bandeja de revisión, bridge items, follow-ups) con `_classify_gate` que bloquea Programa/Recurso e Ignorar | vivo; **no escribe** a Registro de Tareas humano | [repo] `granola.py:2291` |
| `granola.create_human_task_from_curated_session` — escritura schema-driven a la DB humana de tareas: dedup por título exacto, relaciones solo explícitas/heredadas, trace comments, `dry_run` | código vivo y binding configurado, pero exige como evidencia una **sesión curada V1** (capa retirada) — hoy efectivamente inerte | [repo] `granola.py:2982`; [VPS] `NOTION_HUMAN_TASKS_DB_ID=517bfeb9…` set, `NOTION_CURATED_SESSIONS_DB_ID` **comentado** en env |
| Guardrails G1-G7 (Trazabilidad append-only, project-first comercial, datos fonéticos) | normativos en skill/doc; **no ejecutados por código** en el camino raw→Tarea (no existe ese camino aún) | [repo] `docs/54` §6.1, `granola-pipeline/SKILL.md` |
| Acceso Notion: la integración Rick LEE Registro de Tareas (517bfeb9), Transcripciones Granola, Asesorías & Proyectos y Clientes y Partners | verificado (GET database OK en los 4) | [VPS] prueba read-only 2026-07-16. La nota de `docs/54` §7 ("Rick no ve la DB humana de tareas") está **obsoleta** |

### 1.3 Poller (`dispatcher/notion_poller.py`)

- **[VPS]** No hay unidad `notion-poller.service`: corre por cron `notion-poller-cron.sh` cada 5 min (coincide con registry).
- Qué polla hoy: comentarios de Control Room + review targets (deliverables/projects; la rama `session_capitalizable` está muerta porque el env var está comentado) + **scan V2 de clasificación**: lee las primeras 10 filas de la DB Granola y llama `granola.classify_raw` hasta 3 por ciclo.
- **Gap grave observado [VPS]:** el scan V2 **no respeta `Procesar con agente`** (clasifica lo que encuentre sin gate humano), y el 2026-07-16 ~01:07 "clasificó" varias filas del lote P1.1b como `?/?/?`: el LLM está caído, `classify_raw` devolvió clasificación vacía **sin** clave `error` (rama "sin contenido"/"JSON inválido"), y el poller las marcó como clasificadas en Redis (TTL 24h). No corrompió Notion (esas ramas no escriben propiedades), pero es un **falso "hecho"** silencioso.
- El poller no escribe canónico (correcto per registry `notion_poller.writes: []`).

### 1.4 Rick / OpenClaw

- **[VPS]** Gateway `2026.6.10` activo, 8 agentes, Telegram ON. Modelo default `openai/gpt-5.5` (fallback `gpt-5.4`) vía **OAuth OpenAI (codex-app-server)**, cuota 92% disponible (ventana 168h). Anthropic: token manual presente pero **`UMBRAL_DISABLE_CLAUDE=true`** (docs/19 vigente). Google/Vertex: api-keys en el auth store del gateway. **Kimi/Azure NO está en los modelos configurados del gateway** (los 5 configurados son `openai/*`) — el provider `azure-openai-responses` de docs es histórico/para Worker-scripts, no un modelo elegible de Rick hoy.
- **Drift de skills [VPS vs repo]:** en `~/.openclaw/workspace/skills/` está desplegada **`granola-meeting-capitalization`** (instruye a Rick a capitalizar reuniones usando `notion.upsert_*` directos), que **no existe** en `openclaw/workspace-templates/`; y `granola-pipeline` (la del repo, con guardrails G1-G7) **no está desplegada**. Repo=intent, VPS=reality: hoy la "reality" le dice a Rick que capitalice por chat-LLM con upserts directos — exactamente el patrón que este plan quiere retirar para el flujo V2.
- ISSUE-001 (sessions_* filtradas en nested) sigue vigente: Rick orquestador nested no puede spawnear — otra razón para no montar el batch sobre cadenas de agentes OpenClaw.

### 1.5 Proveedores LLM reales del Worker

**[VPS]** El proceso vivo del Worker no tiene NINGÚN proveedor LLM utilizable:

- `GOOGLE_API_KEY` ausente (el clasificador gemini_flash/gemini_pro falla desde al menos el 2026-07-16).
- `AZURE_OPENAI_ENDPOINT/API_KEY` y `OPENAI_API_KEY` ausentes (`llm.generate model=azure_foundry` → task_failed en ops_log).
- `ANTHROPIC_API_KEY` ausente del proceso + `UMBRAL_DISABLE_CLAUDE=true`.
- La cuota OAuth Codex del gateway NO es accesible desde el Worker (nota explícita en `worker/tasks/llm.py`).

Consecuencia: hoy el "camino barato" de clasificación en VPS **no existe operativamente**, aunque el código esté desplegado. Cualquier paquete que dependa de LLM en VPS tiene este pre-requisito.

### 1.6 Gaps consolidados

1. **Clasificación libre**: `_CLASSIFY_SYSTEM_PROMPT` del Worker dice "Si hay action items claros → Tarea", que **contradice** la Enmienda V2.1.1 (cliente+oportunidad → Proyecto aunque haya action items). Si se reactivara el LLM del Worker hoy, clasificaría reuniones comerciales como Tarea (el error que la Enmienda vino a corregir).
2. **Verify-after-write**: existe para bloques de ingest, **no existe** para capitalización (propiedades, URL artefacto, Trazabilidad, relaciones). El patrón "log miente" de Haiku (3/5) es exactamente lo que un verify determinista en código elimina.
3. **Append de Trazabilidad preservando ingest**: normativo (G1 + Enmienda V2.1.1) pero sin implementación de código en el camino de capitalización; además hay un **conflicto de contrato**: G1 de UAS permite anexar `canonical_target_url`, mientras el prompt V2.1 lo **prohíbe absolutamente** (Notion convierte URLs en mentions y rompe `clave=valor`). Debe ganar la regla de gobernanza: URL solo en `URL artefacto`.
4. **Resets de flags**: `Procesar con agente=false`, `Estado`, `Estado agente`, `Accion agente`, `Estado revisión` — el Worker no tiene un cierre de fila raw coherente con `docs/databases/02`.
5. **Relaciones Cliente/Partner**: solo el agente Notion las resuelve hoy (con matching por juicio). El Worker puede propagar relaciones ya existentes pero no tiene matcher (y no debe inventarlo en V1 del slice).
6. **Poller**: scan V2 sin gate humano + falso "classified" con LLM caído (1.3).
7. **Bindings con drift** entre registry y VPS: `NOTION_TASKS_DB_ID` en VPS = `afda99a3…` (DB operativa del stack), no `517bfeb9…` como declara el registry; la DB humana real se binda por `NOTION_HUMAN_TASKS_DB_ID`. `NOTION_COMMERCIAL_PROJECTS_DB_ID` **sí existe** en el env de la VPS (la corrección `corrected_2026_04_11` del registry quedó obsoleta). Para P4.

---

## 2. To-be — arquitectura híbrida propuesta

Principio rector: **Notion agent = cirujano manual de bajo volumen (juicio); UAS = motor determinista de ejecución (mecánica). Ningún LLM de chat escribe canónico en batch.**

```
                       ┌──────────────────────────────────────────────┐
raw (Transcripciones   │ (A) CLASIFICACIÓN                            │
 Granola, ya ingerido  │  A1 barato: Worker classify_raw V2.1.1-sync  │
 por process_transcript│     (LLM VPS restaurado) — solo propone      │
 con Trazabilidad      │  A2 duro:  Notion agent (Kimi) MANUAL,       │
 de ingest)            │     1 fila a la vez                          │
                       │  A3 humano: David/Rick setean Destino a mano │
                       └──────────────┬───────────────────────────────┘
                                      │  Destino canonico queda seteado en el raw
                                      ▼
             ┌────────────────────────┴─────────────────────────┐
             │ Rick/David marcan Procesar con agente = true     │   ← gate humano, sin trigger Notion
             └────────────────────────┬─────────────────────────┘
                                      ▼
         ┌────────────────────────────┴──────────────────────────────┐
         │ (B) Destino=Tarea → Worker granola.capitalize_task_from_raw│
         │  determinista, 0 LLM:                                      │
         │   dedup por título → create/update en Registro de Tareas   │
         │   → URL artefacto → Trazabilidad APPEND (ingest intacto)   │
         │   → resets de flags → VERIFY-AFTER-WRITE (relectura campo  │
         │     a campo) → si falla: Revision requerida + comentario   │
         └────────────────────────────┬──────────────────────────────┘
                                      ▼
         ┌────────────────────────────┴──────────────────────────────┐
         │ (C) Destino=Proyecto/Entregable/Programa/Recurso o duda    │
         │  → Revisión requerida EN EL RAW (Motivo, Pregunta,         │
         │    Recomendación) — sin LLM Notion en batch.               │
         │  Casos de alto valor: David dispara Kimi manual (cirujano) │
         └─────────────────────────────────────────────────────────────┘
```

### Decisiones de diseño (con justificación)

**¿Quién clasifica en el camino barato?** Híbrido A1/A2/A3. El clasificador del Worker (una vez sincronizado con V2.1.1 y con proveedor LLM restaurado) propone `Dominio/Tipo/Destino/Resumen` a costo ~despreciable (Gemini Flash, ~3K chars por fila). Pero **la clasificación propuesta nunca habilita escritura por sí sola**: la escritura B exige el gate humano (`Procesar con agente=true`) sobre un `Destino canonico` ya visible en la fila. Heurística determinista pura se descarta como clasificador primario (los títulos/keywords no capturan "cliente+oportunidad"; el piloto demostró que esa distinción necesita juicio), pero sí se usa como **red de seguridad**: si el transcript menciona cliente conocido del CRM y el destino propuesto es Tarea, el Worker degrada a Revisión requerida (regla anti-Comgrap en código).

**¿Rick orquesta o Worker task nuevo?** Worker task nuevo (`granola.capitalize_task_from_raw`). Razones: (a) el patrón de fallo del piloto es de integridad de ejecución, y eso se resuelve con código, no con otro prompt; (b) SOUL regla 18 exige evidencia observable — un task determinista devuelve verificación estructurada; (c) ISSUE-001 hace frágil cualquier cadena nested de OpenClaw; (d) Rick queda como **disparador e informador** (puede invocar el task y reportar), nunca como escritor canónico de este flujo.

**¿OpenClaw llama al Worker o el poller lee `Procesar con agente=true`?** Ambos convergen en el mismo task, pero el camino canónico de batch es el **poller** (fase 2 de P1): query determinista `Procesar con agente=true AND Estado agente ∈ {Pendiente, Revision requerida+Reprocesar} AND Destino canonico=Tarea` → encola el task. Es el contrato ya documentado en `docs/databases/02` §flujo, paso 4. La fase 1 de P1 es invocación **manual** (CLI/`run_worker_task.py`) para el lote piloto. OpenClaw puede llamar al Worker ad-hoc (cirugía asistida por Rick), pero no se agrega trigger Notion nativo.

**¿Dónde vive verify-after-write?** En el Worker, dentro del task, como paso final bloqueante (no opcional, no en prompt): relee la tarea creada y el raw, compara campo a campo (título, URL artefacto == URL real de la tarea, Destino, las 4 propiedades obligatorias, claves de ingest de Trazabilidad todas presentes, flags reseteados). Devuelve `verification: {ok, mismatches[]}`. Si `ok=false`: revierte el cierre (deja `Revision requerida` + `Motivo revisión=Bloqueo técnico` + comentario) y **no** declara Capitalizado. Es la traducción a código de la "Prohibición de declaración falsa de éxito" del prompt V2.1.

---

## 3. Fronteras duras (no negociables, ya vigentes en el contrato)

1. **Programa/Recurso jamás cierran como capitalización exitosa** — `_classify_gate` ya lo bloquea; el task nuevo lo hereda (`Estado=Pendiente`, `Estado agente=Revision requerida`, `URL artefacto` vacía).
2. **`URL artefacto` solo apunta al canónico final** — y nunca se escribe URL dentro de `Trazabilidad` (gana la regla V2.1/gobernanza sobre el G1 de UAS; reconciliar en P4).
3. **Trazabilidad: preservar claves de ingest; append `clave=valor` línea a línea** — el writer nuevo parsea el bloque existente, valida superset post-write, y si una clave de ingest desaparece es fallo de verificación.
4. **`Registro de Sesiones y Transcripciones` no es puente V2** — ninguna parte del flujo B/C lo toca; el binding V1 sigue comentado en la VPS y así se queda.
5. **OpenClaw no es almacén canónico de conocimiento** — Rick coordina y dispara; los artefactos viven en las superficies canónicas de Notion.
6. **Repo = intent, VPS = reality** — todo cambio de skill/worker se declara verificado solo con evidencia de runtime (SOUL 18); el drift de skills detectado (1.4) se corrige vía repo→deploy, no editando el workspace a mano.

---

## 4. Economía / créditos

| Vía | Costo por fila | Viabilidad batch (95 filas) | Rol |
|---|---|---|---|
| Notion agent (Kimi) | ~créditos de 1 corrida de agente custom (7 corridas agotaron el saldo del plan actual) | **Inviable** — se estima capacidad total del plan en el orden de decenas de corridas/mes | Cirujano manual: casos duros, remediaciones, matching Cliente/Partner con juicio. Presupuesto operativo sugerido: **≤20-30 corridas/mes**, una a la vez, revisando resultado |
| Worker clasificación (Gemini Flash, prompt ~3K chars + 300 tokens out) | fracciones de centavo USD (token real del provider) | Trivial — las 95 filas costarían centavos | Camino barato A1 (cuando se restaure proveedor) |
| Worker capitalización determinista | **0 tokens LLM** (solo llamadas Notion API) | Total | Motor B |
| Cuota OAuth Codex del gateway | "gratis" pero es la cuota operativa de Rick/chat | No usar para batch | Solo conversación/orquestación de Rick |

**Política operativa recomendada:**

- **NUNCA** más batch por el agente Notion (ni triggers, ni lotes de 10+, ni "reprocesar todo").
- Notion agent (Kimi) **solo manual** y solo donde el juicio paga: reuniones comerciales ambiguas, decisión Proyecto-vs-Tarea límite, remediación de falsos éxitos legacy, matching CRM sin match exacto.
- Todo lo mecánico y repetible (escritura de tarea, trazabilidad, flags, verificación) va por el Worker.
- Los items 4-5 pendientes de la comparación Kimi (`39f5f443…290e`, `…3.17ee`) se retoman solo cuando David lo decida y haya créditos; no son bloqueo de este plan.

---

## 5. Plan por paquetes (secuencial)

> Ningún paquete se implementa bajo este encargo. Cada uno se emite como misión aparte con su propio gate. Orden estricto: P0 → P1 → P2 → P3 → P4 (P4 puede adelantarse en paralelo si David libera el working tree de notion-governance).

### P0 — Trazabilidad append + verify-after-write en el Worker (sin LLM)

- **Objetivo:** helpers deterministas reutilizables: `append_capitalization_traceability()` (parse del bloque existente, preservación de claves de ingest, append del bloque de capitalización SIN URLs, relectura y comparación) y `verify_task_capitalization()` (relectura campo a campo de tarea + raw). Corrige además el G1 de `granola-pipeline/SKILL.md` y `docs/54` §6.1.1 para eliminar `canonical_target_url` de las claves anexables (alineación con V2.1).
- **Repo(s):** umbral-agent-stack.
- **Superficie de riesgo:** baja — código nuevo + tests; sin deploy en este paquete; no cambia comportamiento de tasks existentes.
- **Dependencias:** ninguna.
- **Gate:** `CAP_P0_VERIFY_APPEND_PASS` — tests unitarios verdes incluyendo caso de regresión "Trazabilidad de ingest P1.1b intacta tras append" y caso "clave de ingest perdida → verification.ok=false".
- **GO de David:** no para el código; sí para el deploy a VPS (que puede diferirse a P1).

### P1 — Task determinista `granola.capitalize_task_from_raw`

- **Objetivo:** el motor B. Precondiciones duras en el input: raw existe, `Destino canonico=Tarea` ya seteado, `Procesar con agente=true` (o invocación manual explícita con page_id). Lógica: dedup por título en Registro de Tareas (0→crear, 1→actualizar, 2+→Revisión requerida), escritura schema-driven (reutiliza el patrón de `create_human_task_from_curated_session` pero con el **raw** como evidencia), `URL artefacto`, Trazabilidad append (P0), relaciones **solo** las ya presentes en el raw o pasadas explícitas (sin matching nuevo), resets de flags per `docs/databases/02`, verify-after-write bloqueante, salida Error/Revisión con comentario si algo no verifica. Red de seguridad anti-Comgrap: si detecta señal comercial fuerte (Cliente/Partner relacionado seteado + `Tipo propuesto=Reunión` + organización detectada) degrada a Revisión requerida en vez de capitalizar, aunque Destino diga Tarea.
  - Fase 1: invocación manual (`run_worker_task.py`) sobre lote piloto de 5-10 filas elegidas por David.
  - Fase 2: el poller encola el task con la query gated (sin LLM, sin clasificar).
- **Repo(s):** umbral-agent-stack.
- **Superficie de riesgo:** media-alta — primera escritura runtime del stack a `Registro de Tareas y Proximas Acciones` desde raw V2. El contrato lo permite (`tasks.default_modes.umbral_agent_stack: edit_structured`, binding y sharing verificados [VPS]), pero es superficie humana.
- **Dependencias:** P0.
- **Gate:** `CAP_P1_TASK_SLICE_PASS` — lote piloto con verificación campo a campo vía lectura directa API (mismo estándar que el piloto Notion), 0 escrituras fuera de raw+tareas, ingest keys intactas en el 100%.
- **GO de David:** **sí, obligatorio** antes del primer write live (elige el lote piloto y autoriza deploy+restart del worker).

### P2 — Clasificador barato sincronizado con gobernanza + fixes de poller

- **Objetivo:** (a) reescribir `_CLASSIFY_SYSTEM_PROMPT` para encodear la Enmienda V2.1.1 (cliente+oportunidad → Proyecto aunque haya action items; duda → Revisión) y datos fonéticos; (b) `classify_raw`: clasificación vacía o parse fallido → resultado con `error` explícito (elimina el falso "classified" `?/?/?`); (c) poller scan V2: respetar `Procesar con agente` o, mínimo, excluir filas con `Estado agente` ya trabajado y registrar métricas honestas; (d) restaurar UN proveedor LLM del Worker (recomendado: `GOOGLE_API_KEY` para Gemini Flash — requiere que David provisione la key en `~/.config/openclaw/env`).
- **Repo(s):** umbral-agent-stack (+ runbook de env en docs).
- **Superficie de riesgo:** media — el clasificador escribe propiedades del raw (no canónico); el riesgo real es clasificar mal → mitigado porque B sigue gated por humano.
- **Dependencias:** P1 (para que una clasificación `Tarea` tenga camino de cierre); la key es decisión de David (Decisión abierta #1).
- **Gate:** `CAP_P2_CLASSIFIER_PASS` — batch dry-run sobre ≥10 filas ya clasificadas por Kimi/Haiku como golden set; concordancia de `Destino` ≥8/10 y 0 casos "comercial→Tarea".
- **GO de David:** sí para la key del proveedor y para activar el scan gated.

### P3 — Skill OpenClaw/Rick solo-orquestación + cierre del drift de skills

- **Objetivo:** actualizar `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md` (o una sección V2 nueva) para que Rick: dispare `granola.capitalize_task_from_raw`/`classify_raw` vía Worker, reporte resultados con la verificación estructurada, y tenga **prohibido** capitalizar el flujo V2 con `notion.upsert_*` directos. Reconciliar el drift: decidir el destino de la skill live `granola-meeting-capitalization` (retirarla o reescribirla desde template) y desplegar desde repo (`sync_skills_to_vps.py`).
- **Repo(s):** umbral-agent-stack (templates) + deploy de workspace VPS.
- **Superficie de riesgo:** baja-media — cambia instrucciones de Rick, no código; el deploy toca `~/.openclaw/workspace` (no `openclaw.json`, no restart del gateway).
- **Dependencias:** P1 (la task debe existir antes de instruir a Rick a usarla).
- **Gate:** `CAP_P3_ORCHESTRATION_SYNC_PASS` — skill desplegada == template del repo (diff vacío) + smoke conversacional: Rick responde a "capitaliza la fila X" invocando el task del Worker y reportando `verification.ok`.
- **GO de David:** sí para el deploy del workspace (toca la superficie viva de Rick).

### P4 — Registro en notion-governance (rama limpia)

- **Objetivo:** en una rama nueva de notion-governance (sin tocar el working tree sucio actual): (a) registrar el modelo Kimi K2.7 Code del agente "Transcriptor Granola" y el límite de créditos como restricción operativa (los 2 TODO del closeout); (b) registrar la decisión híbrida: agente Notion = manual-only, motor batch = umbral_agent_stack con task determinista; (c) declarar el write-path runtime raw→`Registro de Tareas` (actor `umbral_agent_stack`, task `granola.capitalize_task_from_raw`, verify-after-write obligatorio) en `registry/runtime-bridge-contract.yaml`; (d) corregir claims obsoletos detectados: `NOTION_TASKS_DB_ID` (VPS apunta a `afda99a3…`, la DB humana se binda por `NOTION_HUMAN_TASKS_DB_ID`), `NOTION_COMMERCIAL_PROJECTS_DB_ID` (sí existe en env desde ~P1.1b), y el conflicto `canonical_target_url` (G1 UAS vs prohibición V2.1).
- **Repo(s):** notion-governance.
- **Superficie de riesgo:** baja (docs/registry), pero el working tree local tiene cambios sin commitear de D-19/QW-2/P10-SEC63 en `docs/policies/05` y `registry/*.yaml` — **este paquete no puede arrancar hasta que David resuelva ese tree** (commit, stash o rama aparte).
- **Dependencias:** P1 ejecutado (para registrar realidad, no intención) o, si se adelanta, registrar como `designed_not_yet_live`.
- **Gate:** `CAP_P4_GOVERNANCE_SYNC_PASS` — PR de solo-docs/registry en notion-governance, diff limpio, sin mezclar con los cambios locales ajenos.
- **GO de David:** sí (es su registry y su tree sucio).

---

## 6. Decisiones abiertas (máx 5, con recomendación)

1. **Proveedor LLM para el clasificador VPS.** Opciones: restaurar `GOOGLE_API_KEY` (Gemini Flash) / configurar Azure OpenAI keys / dejar P2 sin LLM (solo clasificación manual+Kimi). **Recomendación: restaurar `GOOGLE_API_KEY`** — ya integrado en `llm.py`, costo por fila despreciable, y desbloquea también `composite.research_report` que hoy falla por lo mismo.
2. **¿P1 escribe relaciones Cliente/Partner en el raw?** **Recomendación: no** — P1 solo propaga relaciones ya presentes; el matching CRM queda en Kimi manual (donde demostró 0 errores) o en un P2+ con match exacto-único por nombre y fallback a vacío.
3. **Disparador de P1 fase 2.** ¿Poller gated automático o solo manual indefinidamente? **Recomendación: manual hasta cerrar `CAP_P1_TASK_SLICE_PASS`, luego poller gated** (la query respeta `Procesar con agente=true`, que sigue siendo un click humano por fila — el volumen lo pone David/Rick, no un trigger).
4. **Destino=Proyecto en el motor UAS.** El binding a Asesorías & Proyectos existe en la VPS y hay un slice update-only (`update_commercial_project_from_curated_session`), pero el registry declara `verified_live_no_runtime_write_path`. **Recomendación: fuera de alcance de este plan** — todo Destino=Proyecto queda en Revisión requerida (camino C); si más adelante duele, se diseña un paquete propio con su gate y cambio de registry primero (registry antes que código, no al revés).
5. **Créditos Notion.** ¿Subir de plan/comprar créditos para ampliar el cirujano? **Recomendación: no por ahora** — con el motor UAS cubriendo el batch, 20-30 corridas manuales/mes de Kimi bastan para los casos duros; re-evaluar solo si la cola de Revisión requerida con juicio comercial crece de forma sostenida.

---

## 7. Anti-recomendaciones explícitas

- **No clonar el prompt V2.1.1 dentro de OpenClaw.** El prompt Notion es un contrato para un agente que *escribe por juicio*; portarlo a Rick produciría otro chat-LLM escribiendo canónico con el mismo modo de fallo "log miente" (y peor: Rick tiene más superficies de escritura). Las reglas del prompt que importan (append de Trazabilidad, verificación, resets) van a **código** en P0/P1; a la skill de Rick solo van instrucciones de orquestación.
- **No poner en el poller:** LLM inline, escrituras canónicas, lógica de capitalización, ni ampliar el scan V2 actual antes de arreglar su falso-éxito (1.3). El poller es dispatcher determinista: query gated → encolar task → nada más.
- **No usar la VM Windows** para nada de este flujo. La capitalización es Notion API pura desde la VPS; la VM es ingest/watcher/GUI y es el componente más frágil del stack (regla 11 del SOUL, skill vps-operator: VM = recurso opcional).
- **No pedir Perplexity/Codex research todavía.** No hay incógnita externa que lo amerite: las decisiones pendientes son de configuración propia (key de Gemini, gates). Cuándo sí: si en P2 el golden set diera concordancia <8/10 y hubiera que evaluar modelos/proveedores baratos alternativos con benchmark — eso sería un encargo puntual con pregunta cerrada.
- **No reactivar los triggers del agente Notion** ("Propiedad actualizada" / menciones), ni siquiera después de P1: cada disparo quema créditos y el motor batch ya vive en UAS.
- **No usar la cuota OAuth de Codex (gateway) como backend de clasificación batch** — es la cuota operativa de Rick y el Worker ni siquiera puede consumirla (llm.py); no montar proxies para forzarlo.
- **No editar a mano `~/.openclaw/workspace/skills/` ni `~/.openclaw/openclaw.json`** para este plan; skills se corrigen repo→sync (P3) y la config del gateway no necesita cambios.

---

## 8. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El write del Worker a Registro de Tareas falla por sharing de escritura (solo verificamos lectura) | media | bajo (falla limpia) | P1 fase 1 arranca con `dry_run=true` + 1 fila sacrificable; verify-after-write reporta el 403/404 como Error honesto |
| Clasificador VPS reactivado clasifica comercial→Tarea (regresión Comgrap) | media | alto | Prompt V2.1.1-sync (P2) + red de seguridad anti-Comgrap en el task (P1) + gate humano siempre |
| Dedup por título crea duplicados o pisa tarea equivocada | media | medio | Regla 2+ matches → Revisión requerida; update solo con match único exacto; piloto pequeño |
| Drift de skills reaparece (alguien redeploya la skill vieja) | media | medio | P3 deja diff-cero repo↔workspace y el snapshot cron `openclaw-runtime-snapshot` lo evidencia |
| Poller marca filas como clasificadas sin clasificar (ya ocurre) | alta (ocurre hoy) | medio | Fix en P2(b/c); mientras tanto, el TTL de 24h limita el daño y el gate humano impide escrituras derivadas |
| Créditos Notion se gastan por costumbre (alguien corre batch con Kimi) | baja | medio | Política §4 registrada en P4; triggers OFF se mantienen |

---

## 9. Pendientes de gobernanza (registry / policy 05) — NO ejecutados aquí

Todos van en P4, en rama limpia de notion-governance, tras resolución del working tree sucio:

1. Registrar modelo **Kimi K2.7 Code** del agente "Transcriptor Granola" (TODO del closeout de la comparación de modelos).
2. Documentar el **límite de créditos Notion** como restricción operativa de agentes nativos en `docs/policies/05` (TODO del closeout).
3. Declarar el nuevo write-path `umbral_agent_stack → Registro de Tareas` (task determinista + verify-after-write) en `registry/runtime-bridge-contract.yaml` — hoy el contrato lo permite por modo (`edit_structured`) pero no lo nombra.
4. Corregir claims obsoletos: mapeo real de `NOTION_TASKS_DB_ID` vs `NOTION_HUMAN_TASKS_DB_ID` en la VPS; existencia actual de `NOTION_COMMERCIAL_PROJECTS_DB_ID` en env.
5. Resolver el conflicto **`canonical_target_url`**: prohibido en Trazabilidad por V2.1 (gana), permitido por G1 de UAS (se corrige en P0 del lado UAS; registrar la lectura en gobernanza).
6. Anotar el drift de skill OpenClaw (`granola-meeting-capitalization` live sin template en repo) y su resolución P3, per "Repo = intent, VPS = reality".

---

## 10. Veredicto

- **Sí híbrido:** Worker como motor determinista raw→Tarea con verify-after-write (P0+P1); clasificador barato en VPS solo como propositor gated (P2); Rick solo orquesta (P3); Notion agent (Kimi) queda como cirujano manual de casos duros con presupuesto ≤20-30 corridas/mes.
- **No clonar el agente Notion en OpenClaw:** la mejora de Kimi vs Haiku no cambia la conclusión de fondo — lo que falló (integridad de autoverificación) se garantiza con código, no con mejores prompts en otro chat-LLM.

**Gate: `CAP_HYBRID_PLAN_READY`** — diagnóstico as-is con evidencia VPS read-only (2026-07-16), to-be con fronteras Notion/Worker/Rick, paquetes P0-P4 con gates y GO explícitos, decisiones abiertas ≤5 con recomendación.
