# ADR-011: Orquestación Editorial — Criterios Duros, Matriz y Reglas de Promoción

## Estado

Proposed — 2026-05-08

> **Relación con ADR-008**: ADR-008 (`ADR-008-orquestacion-editorial.md`, Accepted 2026-04-21) estableció la arquitectura macro: **Agent Stack core + n8n self-hosted como capa de bordes + Make como lab/stand-by**. Este ADR-011 no la revisa: la complementa. ADR-008 respondió *"¿qué motor coordina el flujo editorial?"*. ADR-011 responde *"frente a una integración nueva, ¿cómo decide el equipo en qué motor cae, sin debate caso por caso?"*. ADR-011 agrega: matriz operativa, criterios duros de decisión, anti-patrones explícitos, reglas de promoción n8n→core y topología de comunicación entre los tres motores.

## Contexto

A 2026-05-08 hay tres motores de orquestación disponibles para el Sistema Editorial Rick y para el resto de la plataforma Umbral:

1. **Agent Stack core** (Python custom) — `dispatcher/`, `worker/tasks/*`, en producción VPS desde 2026-02. Dueño actual de Notion writes, Granola pipeline, OpenClaw gateway, supervisores, gates humanos e idempotencia (`content_hash`). Es el único motor con estado persistente sobre SQLite/Redis y trazabilidad estructurada (OpsLogger).
2. **n8n self-hosted** — desplegado en VPS desde 2026-03-03. `worker/n8n_client.py` existe y el gateway tiene `N8N_API_KEY` activa. **Workflows productivos hoy: 0**. n8n está "enchufado pero sin carga": la decisión de ADR-008 quedó documentada pero todavía no hubo una integración nueva que la ejercite.
3. **Make.com** — stand-by formal. Suscripción de David activa, sin API key cargada en runtime, sin workflows críticos.

Sin un ADR operativo, cada nueva integración (LinkedIn auto-poster, monitoreo de competidores, recordatorios de auth expiry, ingesta de webhooks de Ghost o Linear, scheduling de cadencias editoriales, conectores SaaS adicionales) se decide ad-hoc *"donde sea más fácil al momento"*. El resultado previsible es **arquitectura accidental**: lógica editorial duplicada entre n8n y core, escrituras a Notion fragmentadas en dos dueños, workflows huérfanos en Make sin runbook, y debates recurrentes en cada PR sobre "esto va en n8n o en worker?".

Este ADR cierra ese debate con criterios verificables.

### Ámbito y supuestos

- **Ámbito**: orquestación de tareas asincrónicas, scheduling, ingesta de eventos externos y coordinación multi-step para Sistema Editorial Rick, Granola Pipeline V2, Discovery Pipeline y futuras integraciones de la plataforma Umbral.
- **Fuera de ámbito**: ejecución de LLMs (eso es OpenClaw + worker handlers), generación visual (ADR-006), almacenamiento canónico de contenido (ADR-007 + ADR-002), publicación multicanal (ADR-005). Esos ADRs definen *qué se hace*; ADR-011 define *quién lo orquesta*.
- **Supuesto duro**: David sigue siendo el único humano operador. No hay equipo. Cualquier criterio que requiera "training del equipo en n8n" pesa más que en una organización con plantilla.

## Decisión

### Resumen ejecutivo (2 frases)

**Agent Stack core es el dueño único de la orquestación stateful, los Notion writes y todo lo que toque dominio interno (auth lifecycle, gates humanos, idempotencia, trazabilidad). n8n es la capa de bordes para webhooks entrantes, scheduling con UI, conectores SaaS con nodo oficial maduro y prototipado rápido; Make permanece en stand-by hasta que aparezca un caso donde n8n no tenga nodo y Agent Stack sea over-engineering verificable.**

### Matriz de decisión por motor

| Motor | Casos de uso (SÍ) | Casos NO (anti-uso) |
|-------|-------------------|---------------------|
| **Agent Stack core** | Notion writes (dueño único). Tareas con estado persistente en SQLite/Redis. Granola Pipeline V2. Discovery Pipeline. Handlers que ejecutan Python custom (markdown→Notion blocks, parsing de transcripts, ML, regex de dominio). Gates humanos con `content_hash` / idempotencia. Auth lifecycle tracking (tokens, re-auth alerts) cuyo estado vive en Notion. Cualquier flujo que invoque OpenClaw gateway. Cualquier flujo cuya falla deba quedar en OpsLogger estructurado. | Webhooks entrantes que solo necesitan transformación JSON sin estado. Cron simples sin lógica de negocio (eso es scheduling). Prototipos exploratorios (eso es n8n). Conectores SaaS donde n8n ya tiene nodo oficial mantenido (Slack, Discord, Google Sheets, Telegram, Notion *lectura*). |
| **n8n self-hosted** | Webhooks entrantes (Ghost `post.published`, Linear webhooks, LinkedIn callbacks, eventos de SaaS externos). Scheduled triggers simples sin estado (cron visual con UI). Wait nodes / HITL flows con pausa temporal. Transformaciones JSON sin estado (mapeo, filtrado, fan-out). Integraciones SaaS donde n8n ya tiene nodo oficial **maduro y mantenido** (Slack, Discord, Google Sheets, Telegram, Notion *lectura*, Airtable). Prototipos rápidos antes de promover a core. Backup/export de datos a destinos secundarios. MCP Server Trigger para exponer flujos a OpenClaw. | **Notion writes** (regla absoluta — siempre delega a worker vía HTTP). Cualquier escritura a `discovered_items`, `discovery_state`, `referentes` u otras DBs canónicas del Agent Stack. Lógica de negocio compleja con ramificaciones (>5 nodos condicionales). Llamadas a OpenClaw gateway (eso lo hace worker). Tareas que necesitan idempotencia con `content_hash`. Procesamiento de markdown→blocks (handler dedicado en worker). Cualquier flujo cuya falla silenciosa deje datos inconsistentes. |
| **Make.com** | Stand-by hasta que se cumpla **simultáneamente**: (1) n8n no tiene nodo oficial maduro para el SaaS objetivo, (2) construir el adapter en Agent Stack supera 1 día de trabajo (over-engineering verificable), (3) David ya tiene el conector Make instalado y el flujo es de bajo volumen (<200 ejecuciones/día). | Polling Notion productivo (quema créditos y duplica Notion Poller del core). Core crítico de publicación (sin acceso SSH para repair, créditos limitados, state management pobre). Cualquier flujo que tenga equivalente directo en n8n. Cualquier flujo que escriba a Notion (regla absoluta). |

### Criterios duros — el árbol de decisión

Cuando aparece una integración nueva, el orden de evaluación es **estricto y secuencial**. La primera regla que matchea define el motor. No se vuelve atrás.

1. **¿El flujo escribe en Notion (cualquier propiedad, comentario o block)?**
   → **Agent Stack core, sin excepciones.** No importa cuán simple sea el write. Aunque el resto del flujo sea webhook-only, el write se ejecuta en worker y n8n lo invoca por HTTP. Esto preserva la única fuente de idempotencia (`content_hash`), el OpsLogger estructurado y los gates humanos.

2. **¿El flujo necesita estado persistente entre ejecuciones (más allá del log/audit que el motor te da gratis)?**
   → **Agent Stack core.** SQLite/Redis están en core, no en n8n. Ejemplos: cursores de poller, contadores de quota, registros de items procesados, locks distribuidos.

3. **¿El flujo invoca OpenClaw gateway o requiere un handler Python custom (markdown→blocks, transcript parsing, regex de dominio, ML, validación con pydantic)?**
   → **Agent Stack core.** n8n puede llamar a worker para eso, pero la lógica vive en core.

4. **¿El flujo es un webhook entrante puro (sin estado, sin Notion write, sin lógica >5 nodos)?**
   → **n8n.** Es el caso de uso para el cual n8n existe en este stack. Si el webhook después necesita disparar trabajo de core, n8n hace `POST /v1/tasks` al worker.

5. **¿El flujo es un scheduled trigger simple (cron) sin lógica de negocio o con ramificación trivial?**
   → **n8n** si vale agregar UI/visualización. **Agent Stack core** si la cadencia es del dominio (ej. Notion Poller, Granola schedule). Default: n8n para "cron de operación", core para "cron de dominio".

6. **¿El flujo es una integración SaaS donde n8n tiene nodo oficial mantenido (Slack, Discord, Google Sheets, Telegram, Airtable, Notion *lectura*)?**
   → **n8n.** Implementar handler custom en worker es re-trabajo evitable. Excepción: si la integración va a evolucionar a flujo stateful complejo en <3 meses, ir directo a core.

7. **¿El SaaS no tiene nodo en n8n, no tiene API HTTP cómoda, y David ya tiene el conector en Make?**
   → **Make.** Documentar el caso, abrir issue para evaluar promoción a n8n o core en cuanto el flujo madure. Volumen máximo aceptable: <200 ejecuciones/día.

8. **Default si nada matchea:** abrir issue de discusión, **no improvisar**. Default tentativo: Agent Stack core, porque es donde la deuda técnica es manejable con el tooling existente.

### Anti-patrones (regla negativa explícita)

Estos patrones están **prohibidos** independientemente de cuán convenientes parezcan en el momento. Cualquier PR que los introduzca debe ser rechazado.

1. **n8n escribe a Notion directamente.** Aunque el nodo oficial de Notion en n8n existe y funciona. Razones:
   - Rompe la idempotencia basada en `content_hash` (worker la garantiza, n8n no).
   - Los writes no aparecen en OpsLogger estructurado (pierde trazabilidad).
   - Duplica la lógica de retries, rate limit y manejo de 409 Conflict que vive en `worker/tasks/notion_*.py`.
   - Hace que cualquier debug de "¿quién escribió esto?" sea adivinanza.

   **Sustituto correcto:** n8n hace `POST http://127.0.0.1:8088/v1/tasks` al worker con un task type `notion.update_page` (o equivalente). El worker es el único proceso que toca la Notion API.

2. **Hay lógica equivalente en dos motores.** Ej. la misma regla de "si referente_id es de tier A, promover automáticamente" implementada en un workflow n8n y también en un handler de worker. Mantener dos implementaciones siempre divergen y la divergencia se descubre en producción.

   **Sustituto correcto:** elegir un dueño único, eliminar la otra copia y dejar un comentario en el código del perdedor referenciando este ADR.

3. **Make poll-eando Notion en producción.** Make poll = créditos quemados + duplicación del Notion Poller. Si Make necesita reaccionar a Notion, el patrón correcto es: Notion Poller del core detecta el evento → emite webhook a Make.

4. **Workflow n8n que llama a otro workflow n8n para lógica compleja.** Si un flujo necesita ramificación >5 nodos condicionales, llamadas a sub-workflows, manejo de errores granular y reintentos con backoff, **ya no es un flujo de bordes**. Promoverlo a core (ver §Reglas de promoción).

5. **Workflow n8n sin export en Git.** Cualquier workflow productivo en n8n debe estar exportado al repo bajo `infra/n8n/workflows/*.json` por cron nocturno. Un workflow que existe solo en la VPS no existe (un disk crash lo borra).

6. **Workflow n8n con credentials embebidas en JSON.** Las credenciales viven cifradas con `N8N_ENCRYPTION_KEY` en Postgres y se referencian por nombre, nunca se hardcodean. La pérdida de `N8N_ENCRYPTION_KEY` sin backup fuera de la VPS es un evento crítico documentado en runbook (heredado de ADR-008).

7. **Hardcodear `localhost:8088` o IPs en workflows n8n y workers.** Las URLs de comunicación entre motores viven en variables de entorno (`WORKER_URL`, `N8N_BASE_URL`) y se documentan en `.env.example`.

### Reglas de promoción n8n → Agent Stack core

Un workflow n8n se **promueve** (migra) a Agent Stack core cuando se cumple **al menos uno** de los siguientes triggers:

| Trigger de promoción | Razón |
|----------------------|-------|
| El workflow ahora necesita escribir a Notion (no solo leer). | Anti-patrón #1: Notion writes son monopolio del core. |
| El workflow ahora necesita estado persistente entre ejecuciones (cursor, contador, lock). | n8n no tiene SQLite/Redis nativo accesible al workflow; cualquier hack con n8n variables/static data es frágil. |
| La lógica creció a >5 nodos condicionales con ramificación no trivial, o requiere manejo granular de errores con reintentos. | n8n se vuelve ilegible y los reintentos con backoff exponencial son nativos en core (`tenacity`/handler retry). |
| El workflow se vuelve crítico (su falla bloquea publicación o pierde datos). | Core tiene supervisor, OpsLogger estructurado, alertas. n8n self-hosted no tiene equivalente operacional integrado al stack. |
| El workflow necesita invocar OpenClaw gateway o un handler Python custom. | Esa lógica vive en core; mantenerla en n8n vía HTTP loops fuerza arquitectura inversa. |
| El workflow ya supera las 1000 ejecuciones/día. | Por encima de ese umbral, conviene observabilidad estructurada y la latencia añadida por n8n→worker→n8n empieza a notarse. |

**Procedimiento de promoción** (no es código, es disciplina):

1. Issue en repo con label `promotion-n8n-to-core` referenciando el workflow exportado en `infra/n8n/workflows/*.json`.
2. Spike de 1 día para diseñar el handler equivalente en `worker/tasks/`.
3. PR que implementa el handler y agrega tests.
4. Deploy del handler. El workflow n8n queda **deshabilitado pero exportado** en n8n (se mantiene como snapshot histórico).
5. 7 días de observación dual-write apagado (solo core ejecuta).
6. Eliminación del workflow de n8n (export en Git permanece como artefacto).

**Reglas de promoción inversa (core → n8n)**: existen pero son raras. Ejemplo: un handler custom resulta ser exactamente lo que un nodo oficial de n8n hace gratis y mejor. En ese caso, el patrón es: deprecar el handler, exportar el workflow n8n equivalente al repo, y dejar comentario en el código del handler con la referencia al workflow n8n.

### Topología de comunicación entre motores

```
Eventos externos (webhooks SaaS, callbacks, etc.)
        │
        ▼
┌─────────────────────┐         HTTP POST /v1/tasks
│       n8n           │ ─────────────────────────────┐
│ (capa de bordes)    │                              │
│  webhooks, cron,    │ ◄────── HTTP API/webhook ──┐ │
│  conectores SaaS    │                            │ │
└─────────────────────┘                            │ │
        ▲                                          │ │
        │ HTTP API (worker/n8n_client.py)          │ │
        │ ej: trigger workflow desde core          │ ▼ ▼
        │                                       ┌──────────────────────────┐
        │                                       │   Agent Stack core       │
        │                                       │   (dueño de dominio)     │
        │                                       │  ┌──────────────────┐    │
        │                                       │  │  Dispatcher      │    │
        │                                       │  │  Worker (8088)   │    │
        │                                       │  │  Notion Poller   │    │
        │                                       │  │  OpsLogger       │    │
        │                                       │  └──────────────────┘    │
        │                                       └──────────────────────────┘
        │                                                   │
        │                                                   │ Notion API
        │                                                   ▼
        │                                            ┌─────────────┐
        │                                            │   Notion    │
        │                                            └─────────────┘
        │
        │  (Make stand-by, fuera del flujo productivo)
        ▼
┌─────────────────────┐
│      Make.com       │
│  lab / stand-by     │
└─────────────────────┘
```

**Reglas de comunicación**:

- **Bordes externos (LinkedIn callback, Ghost webhook, eventos SaaS) → n8n primero.** n8n recibe, valida, transforma y delega.
- **n8n → Agent Stack core**: HTTP `POST http://127.0.0.1:8088/v1/tasks` con `Authorization: Bearer $WORKER_TOKEN`. Esta es la única vía por la cual n8n dispara trabajo de dominio (Notion writes, OpenClaw calls, handlers custom).
- **Agent Stack core → n8n**: vía `worker/n8n_client.py`. Casos típicos: trigger de un workflow n8n desde un handler de core (ej. "fan-out a 5 conectores SaaS que ya están en n8n") o consulta de estado de un workflow.
- **Agent Stack core → Notion**: directo, único dueño. Ningún otro motor escribe.
- **Make → cualquier motor**: solo si está documentado en este ADR como excepción aprobada. Por defecto, Make no participa del flujo productivo.

## Alternativas consideradas

### A. Solo Agent Stack core (sin n8n)

Rechazada. Para los bordes simples (webhooks entrantes, cron visual, conectores SaaS con nodo n8n maduro) implementar todo en Python es ceremonia innecesaria: Wait nodes, listeners HTTP genéricos, parser de payloads de SaaS, UI de scheduling. n8n ya está desplegado, ya tiene `worker/n8n_client.py`, ya tiene API key activa: no usarlo es desperdicio. Coincide con el rechazo de la alternativa "D. Solo Agent Stack" en ADR-008.

### B. Solo n8n (reemplazando Agent Stack core)

Rechazada. n8n no tiene el modelo dispatcher/worker, ni los handlers especializados, ni OpsLogger estructurado, ni la integración nativa con Linear/Redis/OpenClaw. Notion auth + idempotencia con `content_hash` + Python custom + estado persistente sobre SQLite no escalan en n8n sin construir, dentro de n8n, una réplica imperfecta de lo que ya hay en core. Coincide con el rechazo de la alternativa "B. n8n como core" en ADR-008.

### C. Solo Make como core

Rechazada. Vendor lock-in (workflows no portables fuera de Make). Costo creciente con volumen (modelo basado en operaciones). Sin acceso SSH a la VPS para debugging. State management limitado vs Agent Stack + Redis. Polling Notion quema créditos. Coincide con el rechazo en ADR-008.

### D. Stack completamente nuevo (Temporal.io, Inngest, AWS Step Functions)

Rechazada. Volumen actual (~20-40 posts/mes editorial, ~15 items/día discovery, ~5 reuniones/día Granola) no justifica una plataforma de orquestación cloud nueva. Introduce dependencia adicional, costo recurrente, curva de aprendizaje y migración de los handlers existentes. El patrón Agent Stack + n8n cubre el caso de uso sin infraestructura nueva. Si en algún momento el volumen se multiplica por 10x o aparece multi-tenancy real, esta alternativa puede revisarse.

### E. Decidir caso por caso sin ADR

Rechazada explícitamente. Es lo que viene pasando hoy y produce arquitectura accidental. ADR-011 existe para eliminar este modo.

## Consecuencias

### Positivas

- **Decisión sin debate por integración nueva**: el árbol de §Criterios duros es ejecutable en minutos. Sin reuniones de arquitectura por feature.
- **Notion writes monopolizados**: trazabilidad e idempotencia preservadas. Los logs estructurados de OpsLogger son la única narrativa de "qué pasó con esta página".
- **n8n empieza a justificar su deploy**: hoy son 0 workflows; con el árbol claro, las próximas integraciones de bordes caen ahí naturalmente y el motor entra en uso productivo.
- **Anti-patrones nombrados**: PR review tiene checklist verificable (no debate de gusto).
- **Reglas de promoción claras**: evita que workflows n8n se conviertan en monstruos de 30 nodos por inercia.
- **Make no quema créditos en background**: queda formalmente en stand-by con criterio de activación explícito.

### Negativas

- **Requiere disciplina de PR review**: si nadie verifica el árbol, el ADR es decoración. Mitigación: agregar al checklist de `CONTRIBUTING.md` un ítem "¿la integración respeta ADR-011?".
- **n8n agrega un punto de mantenimiento real**: Postgres, encryption key, export nocturno, monitoreo de la propia salud de n8n. Los costos operativos heredados de ADR-008 siguen vigentes.
- **Topología n8n ↔ core duplica saltos de red**: un webhook que termina escribiendo a Notion atraviesa n8n → worker → Notion (vs n8n → Notion). Latencia adicional baja (~100ms loopback) pero existe.
- **Reglas de promoción tienen costo**: cada migración n8n → core es un día de trabajo. Hay que aceptar que algunos workflows que crecieron en n8n van a vivir un período "incómodo" antes de la promoción.
- **Decisiones empotradas en árbol**: si las prioridades cambian (ej. Notion deja de ser hub canónico), el árbol completo se revisa. Es un acoplamiento aceptado a las decisiones de ADR-002, ADR-005, ADR-007 y ADR-008.

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Equipo improvisa y escribe a Notion desde n8n "porque era más rápido" | Media | Alto | Checklist en `CONTRIBUTING.md` + grep en CI buscando nodos `n8n-nodes-base.notion` con operación de escritura. Rechazo automático en PR. |
| Workflow n8n crece a monstruo sin promoverse | Alta | Medio | Auditoría trimestral de workflows productivos contadores de nodos. Cualquier workflow >10 nodos abre issue de promoción. |
| Pérdida de `N8N_ENCRYPTION_KEY` (heredado ADR-008) | Baja | Crítico | Backup fuera de VPS documentado en runbook. Procedimiento de restore probado. |
| Make sale de stand-by sin actualizar este ADR | Baja | Medio | Cualquier activación de Make requiere PR de update a ADR-011 con justificación del árbol §7. |
| Topología n8n → worker → Notion satura el worker bajo carga (HITL approvals masivos) | Baja | Medio | Worker tiene rate limit configurable; medir antes de agregar workflows que generen ráfagas. |
| Postgres de n8n no se backupea (heredado ADR-008) | Baja | Alto | Backup diario + export nocturno de workflows a Git como segunda red de seguridad. |
| Drift entre la matriz documentada y la realidad de motores | Alta a 6 meses | Bajo | Revisión obligatoria de este ADR cada 6 meses o cada vez que se promueva un workflow. |

## Migration path

A 2026-05-08 hay **0 workflows productivos en n8n** y **0 workflows productivos en Make**. No hay nada que migrar. Toda la lógica editorial / discovery / Granola vive en Agent Stack core. La situación es ideal para empezar a aplicar el árbol desde la próxima integración sin deuda heredada.

**Si en el futuro aparece un workflow que viola este ADR**, el patrón es:

1. **Crítico (escribe a Notion / produce inconsistencia)**: deshabilitar inmediatamente el workflow infractor. Migrar la lógica a core en el próximo ciclo. Documentar el incidente en `runbooks/`.
2. **No crítico (anti-patrón #2 a #7)**: abrir issue con label `tech-debt-adr-011`, priorizar en backlog. Tolerable hasta el siguiente trimestre.
3. **Caso de borde no contemplado**: actualizar este ADR con la nueva regla. No improvisar.

## Open questions

Lo que este ADR **no resuelve** y queda explícitamente fuera de alcance. Cada una merece su propio ADR/spike cuando aparezca demanda real.

1. **Multi-tenant**: si aparece un segundo cliente además de Rick (otro consultor con Sistema Editorial propio), ¿cómo se separa la orquestación? ¿Instancias separadas de Agent Stack, o tenancy lógica con `client_id`? ADR-011 asume single-tenant.
2. **Auth federada entre motores**: hoy worker tiene `WORKER_TOKEN` simple, n8n tiene credenciales propias por integración, Make tendría OAuth si se activa. No hay un identity provider común. Si crece la cantidad de integraciones, evaluar IdP central (probable: tu propio identity service, ver `identity/`).
3. **Observability cross-motor**: OpsLogger estructurado es de core; n8n tiene su propio log de ejecuciones; Make tiene history en su UI. No hay vista unificada de "qué pasó en el flujo end-to-end que cruza los tres". Posible solución futura: shipping de logs a un backend común (Loki, Datadog, Langfuse extendido).
4. **Backpressure y rate limiting cross-motor**: n8n puede generar ráfagas hacia worker que saturen el handler de Notion. No hay un control de admisión global. Mitigación actual: rate limit en worker + monitoreo. Pendiente: queue compartida con prioridades.
5. **Disaster recovery formal**: si la VPS se cae, hoy se restaura del último snapshot. n8n agrega complejidad: además del snapshot necesitás `N8N_ENCRYPTION_KEY` y export de workflows. Pendiente: documentar runbook DR completo cubriendo Agent Stack + Postgres de n8n + workflows exportados.
6. **Deprecación de Make**: si en 12 meses Make sigue en stand-by sin uso, ¿se mantiene la suscripción o se cancela? Decisión a revisar en planning Q1-2027.
7. **Promoción inversa core → n8n**: el patrón existe pero no hay caso real para validarlo. Cuando aparezca el primer caso, validar el procedimiento y actualizar este ADR.
8. **Integración con OpenClaw como motor de orquestación**: OpenClaw tiene capacidades de routing y workflow-like. Hoy se trata como gateway de modelos, no como motor de orquestación. ¿Cuándo (si alguna vez) OpenClaw entra en este árbol? Pendiente de ADR separado.

## Fuentes y referencias

- **ADR-008** (`ADR-008-orquestacion-editorial.md`, Accepted 2026-04-21): arquitectura macro Agent Stack core + n8n bordes + Make stand-by. ADR-011 la complementa con criterios operativos.
- **ADR-002** (`ADR-002-notion-vs-queue.md`): por qué Notion es la queue/hub canónico de tareas, lo que justifica el monopolio de writes en core.
- **ADR-005** (`ADR-005-publicacion-multicanal.md`): qué canales se publican y con qué HITL, alimenta los casos del árbol §Criterios duros.
- **ADR-007** (`ADR-007-notion-como-hub-editorial.md`): estructura de Notion como hub editorial, refuerza la regla "Notion writes son monopolio core".
- **Plan Q2-2026 O17** (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`): item raíz que originó esta tarea.
- **`worker/n8n_client.py`** (en runtime): cliente HTTP que core usa para invocar workflows n8n. No se modifica en este ADR; solo se documenta su rol.
- **UA-14** (`Perplexity/Umbral Agent Stack/14_ Orquestación Editorial con Make n8n y Cron/UA-14-orquestacion-editorial.md`): investigación previa que sustentó ADR-008.
