# Propuesta de integración n8n ↔ Notion — post-smoke P3 (2026-07-24)

> **Estado:** Proposed — **docs-only**. Este documento NO crea ni activa
> workflows en n8n (Cloud ni VPS), NO escribe Notion, NO abre gates, NO
> publica y NO modifica código del Worker/poller (solo lo cita). Toda
> implementación queda condicionada a GO explícito de David por paquete (§6).
> **Precede:** `EDITORIAL_SMOKE_E2E_READY`
> ([editorial-smoke-e2e-p3-2026-07-23.md](editorial-smoke-e2e-p3-2026-07-23.md))
> y `N8N_NOTION_RADAR_READY` (radar Perplexity, ver §0).
> **Marco vinculante:** [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)
> (n8n NUNCA escribe Notion directo; Worker/core es único escritor) +
> [norte HITL](editorial-norte-hitl-contract-2026-07-22.md) (Fila I = B,
> Telegram duro D3).

---

## 0. Fuentes y método

| Fuente | Qué aporta |
|--------|------------|
| Smoke P3 §I ([editorial-smoke-e2e-p3-2026-07-23.md](editorial-smoke-e2e-p3-2026-07-23.md)) | Matriz de disposición: qué falta para activar (gaps que esta propuesta cruza en §1) |
| [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) + [ADR-008](../adr/ADR-008-orquestacion-editorial.md) | Árbol de decisión por motor, anti-patrones, topología n8n↔core |
| [Norte HITL](editorial-norte-hitl-contract-2026-07-22.md) | D3 triple gate, Fila I = B, roles (Worker único escritor) |
| Radar Perplexity `radar n8n y notion.md` (G:\Mi unidad\04_Recursos\Referencias e Investigacion\Investigacion\Perplexity\Umbral Agent Stack\, marcador `N8N_NOTION_RADAR_READY`) — leído completo | Novedades 2025–2026: webhooks oficiales Notion (GA mar-2025), MCP n8n de instancia con creación de workflows, Data Tables, límites API Notion, riesgos de doble escritura |
| Snapshot local `docs/external-context/n8n-llms-full.txt` (commit 2026-05-08; documenta stable 2.19.5 / beta 2.20.5) | Hechos verificables de docs oficiales n8n: nodos Webhook/Telegram/Schedule/Notion/MCP, Data Tables, error handling, Cloud vs self-host. Citas por línea aproximada `[llms ~NNNN]` |
| Repo (solo lectura) | `worker/n8n_client.py` (dirección core→n8n, existente); `POST /enqueue` en `worker/app.py:756` (borde genérico para que n8n dispare tasks, anticipado por P2.6); `.env.example:157-158` (`N8N_URL=http://127.0.0.1:5678`, loopback VPS); `infra/n8n/workflows/` **no existe aún** (0 workflows productivos, consistente con ADR-011 §Migration path) |

**Nota de endpoint:** ADR-011 usa la notación `POST /v1/tasks`; el endpoint
real del Worker es `POST /enqueue` (`worker/app.py:756`). Esta propuesta usa
`/enqueue`. No se cambia código aquí; si se quisiera alinear la notación,
sería un PR docs aparte sobre ADR-011.

**Nota de frescura:** el snapshot llms-full (2026-05-08) ya cubre el MCP de
instancia con `create_workflow_from_code` (disponible desde v2.12.0, edición
de workflows vía MCP desde v2.13 `[llms ~4549, ~5286]`) — es decir, cubre la
funcionalidad que el radar reporta como "v2.14.0 beta (marzo 2026)". Donde
radar y snapshot difieren en madurez, §2.B5 lo señala explícitamente.

---

## 1. Cruce: gaps del smoke §I vs lo que n8n puede aportar

Lectura honesta primero: **n8n no es un atajo de activación**. De los 9 gaps
de la matriz §I del smoke, n8n cierra **1 completo** (Telegram) y
**1 parcial** (poller/event-driven); los otros 7 son credenciales/schema que
solo David o el VPS proveen y donde n8n no tiene ningún rol (dos de ellos van
fusionados en una fila de la tabla). Adicionalmente — fuera de la matriz §I —
n8n apoya el procedimiento "GO David paso 6" del smoke (activar una flag por
vez y observar), fila marcada como *extra* abajo.

| Gap (smoke §I) | ¿n8n aporta? | Cómo / por qué no |
|---|---|---|
| Webhook Telegram entrante (greenfield; `telegram_confirmed` nunca se infiere) | **SÍ — cierre completo** | Es exactamente el "lane n8n/operador" que el smoke dejó fuera de alcance. Telegram Trigger es nodo oficial GA con allowlist de chat/user IDs `[llms ~78518]`. Borde **B1** (§2). |
| Flags poller todas OFF (`NOTION_POLLER_ENABLE_*`) | **Parcial** | Los webhooks oficiales de Notion (GA mar-2025, radar §2) + nodo Webhook n8n ofrecen una vía **event-driven** que reduce la dependencia del polling para detectar transiciones HITL. NO reemplaza las flags: cada acción del Worker sigue detrás de su flag fail-closed; el poller queda como barrido de reconciliación (B2, §2). |
| *(extra, no-§I)* "Activar una flag por vez y observar" (smoke §GO David, paso 6) | **Apoyo transversal** | Cron de operación + alertas Telegram (B3, §2) dan el canal de observación que ese procedimiento pide. |
| `WORKER_URL` / `WORKER_TOKEN` | No | Config VPS. n8n los **consume** como credencial (Header/Bearer auth del nodo HTTP Request) — es dependencia de B1/B2/B3, no algo que n8n resuelva. |
| `NOTION_API_KEY` (Worker) | No | Credencial del Worker. n8n no debe tenerla (§4.3). |
| `MAGNIFIC_API_KEY` | No | Credencial del Worker; GO David pendiente desde P2.2. n8n irrelevante. |
| `NOTION_PUBLICACIONES_DB_ID` / `NOTION_SHORTLIST_DS_ID` (la DB Shortlist puede no existir) | No | Schema/P1 = solo David (ADR-007 §44). Prerequisito de cualquier borde que reaccione a Shortlist. |
| Columna `Copy LinkedIn empresa` | No | Solo David. |
| `EDITORIAL_BLOG_FUNCTION_URL` | No | Config Azure/VPS. |

---

## 2. Bordes propuestos (evaluación aceptar/rechazar)

Contrato común a TODO borde aceptado (invariante, no negociable):

1. n8n **nunca** escribe Notion (ninguna propiedad, comentario ni block) —
   ADR-011 anti-patrón #1. Su única salida hacia el dominio es
   `POST /enqueue` al Worker con `Authorization: Bearer $WORKER_TOKEN`.
2. El Worker **re-verifica todo lo que puede verificar**: los dos legs
   Notion del D3 (`autorizar_publicacion` + gate visual, leyendo Notion él
   mismo) y la idempotencia `content_hash`. Ningún payload proveniente de
   n8n se trata como estado Notion. **Excepción estructural asumida:** el
   tercer leg (`telegram_confirmed`) es por diseño una **atestación
   externa** que el Worker no puede re-derivar — el propio handler lo
   documenta: nada en este repo parsea Telegram entrante, el puente que
   verificó la respuesta es quien lo afirma
   (`worker/tasks/editorial_publish.py:837-845`). La frontera de seguridad
   de ese leg no es el Worker: es la allowlist de Telegram + la doble
   validación en el workflow (B1) + la custodia del `WORKER_TOKEN`.
3. Peor caso de un workflow n8n mal configurado = el Worker bloquea los
   legs que sí verifica (fail-closed demostrado en el smoke G.1): sin
   `autorizar_publicacion` y gate visual en Notion, un `telegram_confirmed`
   espurio no publica nada.
4. Todo workflow productivo se exporta a `infra/n8n/workflows/*.json`
   (anti-patrón #5) y referencia credenciales por nombre, jamás embebidas
   (anti-patrón #6).

### B1 — Telegram "ok publica" → n8n → Worker (`telegram_confirmed`) — **ACEPTAR, prioridad 1**

- **Qué cierra:** el gap greenfield exacto del smoke §I. P2.6 dejó el gate
  `telegram_confirmed` fail-closed esperando precisamente "un workflow n8n
  que verificó la respuesta de Telegram"
  ([editorial-hitl2-publish-bridge-p26-2026-07-23.md](editorial-hitl2-publish-bridge-p26-2026-07-23.md) §1).
  `POST /enqueue` ya existe como transporte para ese borde; lo que **no**
  existe aún es la correlación mensaje↔página (ver diseño abajo) — único
  delta de código Worker posible de N1, y solo si se elige la vía (a).
- **Árbol ADR-011:** regla #4 (webhook entrante puro, sin estado, sin Notion
  write) + regla #6 (Telegram tiene nodo oficial maduro). Cae en n8n sin
  debate.
- **Diseño propuesto (contrato, no implementación):**
  - Telegram Trigger, evento `Message`, con `Restrict to Chat IDs` +
    `Restrict to User IDs` = solo David `[llms ~78518]`. La doc no garantiza
    que ese filtro sea frontera de seguridad → **doble validación**: un nodo
    IF re-verifica `chat_id`/`from.id` contra la allowlist antes de seguir
    `[llms caveat ~78518]`.
  - **Correlación mensaje↔página** (P2.6 señala que hoy no existe, y el
    código lo confirma: `handle_web_publish_editorial_post` acepta solo
    `payload` o `notion_page_id` — no acepta `publication_id` ni tiene
    resolver alguno, `worker/tasks/editorial_publish.py:733-791`; además el
    `publication_id` que escribe promote tiene formato
    `shortlist-<alternativa_id>`, `worker/tasks/editorial_promote.py:107`).
    Dos vías, a elegir en N1:
    - **(a) Resolver en Worker (preferida):** David escribe
      `ok publica <publication_id>` y N1 agrega al Worker un lookup
      read-only `publication_id → notion_page_id` (query a Publicaciones
      por la propiedad `publication_id`). Es el **único código Worker nuevo
      de N1** — pequeño, read-only, testeable.
    - **(b) Botones inline (sin código Worker):** la alerta de B3 llega con
      botón "Publicar" cuyo `callback_data` ya trae el `notion_page_id`;
      el Telegram Trigger en `Callback Query` lo extrae
      `[llms ~78487, ~44101]`. David nunca tipea ids.
    Sin match/callback válido → el workflow termina sin llamar al Worker
    (a lo sumo responde "formato no reconocido").
  - n8n → `POST /enqueue` con el shape real de `EnqueueRequest`
    (`worker/app.py:112-125` — los campos de la task van DENTRO de `input`):

    ```json
    {"task": "web.publish_editorial_post",
     "input": {"notion_page_id": "<page-id>", "telegram_confirmed": true}}
    ```

    El Worker aplica el resto del D3: `telegram_confirmed` solo aporta el
    tercer leg (atestado, ver invariante 2); si `autorizar_publicacion` o
    el gate visual no están en Notion, bloquea igual (smoke G.1/G.2).
  - HTTP Request node con `Retry On Fail` acotado (Max Tries + Wait Between
    Tries `[llms ~60736]`) — seguro porque el publish del Worker es
    idempotente (`content_hash` vs `published_history`). Error Workflow con
    Error Trigger → aviso Telegram a David si el Worker no responde
    `[llms ~17108]`.
- **Caveats operativos:** Telegram admite **un solo webhook por bot** → bot
  separado para pruebas vs producción `[llms ~78553]`; URL pública HTTPS
  obligatoria (en VPS: `WEBHOOK_URL` + TLS en reverse proxy + websockets
  habilitados) `[llms ~78545, ~20284]`.
- **Qué NO hace:** no publica RRSS (Fila I = B intacta), no escribe Notion,
  no marca gates en Notion, no infiere confirmación de nada que no sea el
  patrón exacto.

### B2 — Webhooks oficiales de Notion → n8n → HTTP al Worker — **ACEPTAR condicionado, prioridad 2**

- **Qué cierra (parcial):** dependencia del polling para detectar
  transiciones HITL (ej. `Resultado revisión` → `Aprobar`, gates marcados,
  `Selección imagen` elegida). Los webhooks de Notion son GA desde marzo
  2025 (radar §2) y eliminan la necesidad de polling para eventos de página
  y base de datos.
- **Hecho clave de la doc n8n:** el **Notion Trigger nativo de n8n es
  polling puro** (dos eventos: page added / page updated in database)
  `[llms ~76956, ~85812]` — NO es receptor de los webhooks oficiales de
  Notion. La recepción correcta es el **nodo Webhook genérico** (Header
  auth + verificación del token de suscripción de Notion, respuesta 200
  inmediata) `[llms ~61352]`. Usar el Notion Trigger de n8n además haría
  que cada ejecución disparada por su polling cuente contra la cuota de
  ejecuciones (planes de pago, Cloud o self-host `[llms ~99852]`) y
  duplicaría el Notion Poller del core (mismo espíritu que el anti-patrón
  #3 de Make).
- **Árbol ADR-011:** regla #4 — webhook entrante puro que delega por HTTP.
- **Diseño propuesto:** Webhook node (path manual, Header auth, IP
  whitelist si aplica) → filtro de `event type` → `POST /enqueue` con el
  `page_id` afectado y el tipo de evento → **el Worker re-lee Notion** y
  decide (nunca confía en el payload del webhook). Respuesta 200 inmediata
  (`Respond: Immediately`) para no rozar timeouts.
- **Condiciones para aceptarlo (por eso "condicionado"):**
  1. El radar §6 advierte que Notion **no documenta entrega ordenada ni
     exactly-once** → la idempotencia del Worker es obligatoria (ya existe)
     y el webhook es *hint*, no verdad.
  2. n8n caído = eventos perdidos sin recuperación (la doc n8n es explícita:
     ejecuciones de webhook perdidas durante downtime no son recuperables
     `[llms ~24735]`) → el **poller del core queda como barrido de
     reconciliación**, no se elimina. Webhook-first, poller-fallback.
  3. **Precondición de implementación (hoy NO se cumple):** las flags
     `NOTION_POLLER_ENABLE_*` se chequean **solo** en el poller
     (`dispatcher/notion_poller.py`) — ningún handler del Worker las
     consulta, así que una task encolada vía `/enqueue` las bypasea por
     construcción (ej.: `editorial.promote_shortlist_approval` con
     `dry_run` default `False`, `worker/tasks/editorial_promote.py:157`,
     ejecutaría la promoción real aunque la flag del poller esté OFF).
     Por tanto N2 **exige antes** uno de estos dos cierres, con tests:
     (a) gates fail-closed equivalentes a nivel handler, o (b) una
     allowlist en `/enqueue` de qué tasks puede encolar el rol n8n (y con
     qué inputs, ej. `dry_run` forzado). Hasta entonces, la matriz
     evento→task de N2 se limita a tasks read-only/log-only.
  4. La suscripción del webhook en Notion la crea David (admin de la
     integración), apuntando al endpoint público del n8n del VPS.

### B3 — Schedule + alertas de estado HITL (cron de operación, read-only + notify) — **ACEPTAR, prioridad 2 (puede ir con B1)**

- **Qué aporta:** el canal de observación para el procedimiento GO-David
  "activar una flag por vez y observar" (smoke, paso 6). Ejemplos concretos:
  - Cron (Schedule Trigger, GA `[llms ~61119]`) → `GET /health` del Worker →
    si no responde, alerta Telegram a David. Esto es realizable hoy sin
    ningún código nuevo.
  - Alerta de filas HITL-2 listas: **precisión sobre lo que existe** — el
    scan de P2.6 (`_scan_hitl2_publish_readiness`) es una **función privada
    del poller** (`dispatcher/notion_poller.py:1182`), corre bajo la flag
    `NOTION_POLLER_ENABLE_HITL2_SCAN` en la cadencia del poller y **no** es
    una task encolable por `/enqueue` (además `/enqueue` es asíncrono:
    devuelve `task_id`, no el resultado). Dos mecanismos reales, a elegir
    en N3:
    - **(a) Poller emite, n8n solo transporta (preferida, sin código
      Worker nuevo):** activar la flag del scan (log-only, ya fail-closed)
      y que el poller/scan notifique — n8n queda únicamente como canal
      Telegram saliente (webhook n8n entrante ← poller, o directamente el
      poller escribe a Telegram y n8n ni participa; decidir en N3).
    - **(b) Task Worker nueva read-only** (`editorial.scan_hitl2_readiness`)
      invocable por `/enqueue` + polling de `GET /tasks/{task_id}` desde
      n8n para armar la alerta. Más control desde n8n, pero es código
      Worker nuevo y debe nombrarse como tal.
    Nótese la simetría con B1: la alerta empuja (idealmente con botón
    inline, variante B1-b), B1 recibe la respuesta.
- **Árbol ADR-011:** regla #5 — "cron de operación" → n8n; el "cron de
  dominio" (Notion Poller, Granola) queda en core.
- **Caveats:** timezone del VPS: default de n8n self-host es
  `America/New_York`; fijar `GENERIC_TIMEZONE` o timezone por workflow
  `[llms ~61123, ~20914]`. Cron missed durante restart no se recupera
  `[llms ~24735]` — aceptable para alertas (la siguiente corrida cubre).
  Telegram saliente vía nodo oficial (el bot debe estar en el chat; quitar
  la atribución "sent with n8n" si molesta `[llms ~44280]`).
- **Qué NO hace:** no lee Notion directo en v1 (pregunta al Worker, que ya
  sabe leer y tiene la API key); no escribe nada; no toca gates. Si algún
  día conviene lectura Notion directa desde n8n (permitida por ADR-011
  matriz "Notion *lectura*"), sería una integración Notion **separada,
  read-only en la práctica y con acceso solo a las páginas compartidas
  mínimas** — decisión aparte, no incluida aquí.

### B4 — Data Tables como estado HITL en n8n — **RECHAZAR**

- **Por qué se rechaza (arquitectura, no madurez):** ADR-011 criterio #2 —
  estado persistente entre ejecuciones vive en core (SQLite/Redis); la
  fuente de verdad del estado HITL es Notion + Worker. Un Data Table con
  estado HITL sería una **segunda fuente de verdad** que diverge en
  silencio — exactamente el anti-patrón #2 (lógica/estado duplicado en dos
  motores). La madurez no salva esto: Data Tables es GA en todos los planes
  desde v1.113.1 (radar §1; `[llms ~91336]`) y aun así la respuesta es no.
- **Límites que lo confirman como no-canónico:** cap 50 MB por instancia
  (fijo en Cloud), columnas solo number/string/datetime (sin JSON), sin
  permisos granulares (visible a todo el proyecto), el Code node no puede
  accederlo `[llms ~10676-10680, ~91349]`.
- **Uso residual tolerado (opcional, no requerido):** marcador efímero
  interno de n8n para dedupe de entregas de webhook (operación upsert /
  "If Row Exists" `[llms ~59944]`) — cache descartable cuya pérdida total no
  afecta nada, porque la idempotencia real está en el Worker. Si genera
  cualquier fricción, se elimina sin duelo.

### B5 — MCP de instancia n8n (`create_workflow_from_code`) — **ACEPTAR solo como tooling de agentes, nunca pipeline prod, prioridad 3**

- **Qué es:** crear/editar los workflows B1–B3 desde Cursor/Claude vía el
  MCP oficial de n8n (flujo `get_sdk_reference` → `search_nodes` →
  `get_node_types` → `validate_workflow` → `create_workflow_from_code`,
  radar §1). Reduce click-work de autoría; el runtime del pipeline jamás
  depende de MCP.
- **Madurez (radar vs snapshot):** el radar lo reporta como **beta**
  (anuncio comunidad v2.14, mar-2026); el snapshot llms-full documenta
  `create_workflow_from_code`/`update_workflow` desde v2.12.0 y edición vía
  MCP desde v2.13 **sin** label beta `[llms ~5286, ~4549]`. Tratarlo como
  **beta operativa**: funcional pero con guardrails.
- **Limitaciones confirmadas por el snapshot (no solo rumor de radar):**
  - `create_workflow_from_code` **no** configura credenciales de nodos HTTP
    Request — quedan sin credencial hasta vinculación manual
    `[llms ~5313]`. Como B1–B3 son esencialmente HTTP Request → Worker,
    **todo** workflow creado por MCP requiere paso manual de credencial
    (WORKER_TOKEN) antes de servir. Bien: eso es un HITL natural.
  - Marca `availableInMCP=true` automáticamente en el workflow creado
    `[llms ~5317]` → **desactivarlo** tras crear, salvo intención explícita.
  - La exposición del MCP de instancia **no se puede acotar por cliente**:
    todo cliente MCP conectado ve todos los workflows habilitados
    `[llms ~4551]` (coincide con radar §3 riesgos).
- **Guardrails obligatorios:** (1) solo contra proyecto/espacio de staging o
  con revisión humana previa a publicar; (2) export inmediato a
  `infra/n8n/workflows/*.json` y PR (anti-patrón #5); (3) el pipeline
  productivo nunca invoca herramientas MCP en runtime; (4) si no se usa, el
  VPS puede apagar el módulo entero con `N8N_DISABLED_MODULES=mcp`
  `[llms ~4572]`; (5) token de acceso MCP personal, rotado, nunca en repo.
- **Nota operativa:** el MCP `user-n8n` configurado en Cursor puede estar en
  error — ninguna automatización debe depender de él; el camino soportado es
  el MCP de instancia oficial (`/settings/mcp` + OAuth/token).

---

## 3. Tabla comparativa de bordes

Contexto de la columna Cloud vs VPS — el dato que decide casi todo: el
Worker escucha en loopback (`127.0.0.1:8088`; `.env.example` asume n8n
co-localizado: `N8N_URL=http://127.0.0.1:5678`). **n8n Cloud no puede
alcanzar ese Worker sin exponerlo públicamente**, lo cual es un costo de
seguridad que ningún borde de esta propuesta justifica. n8n Cloud es más
cómodo para *ingress* (URL webhook HTTPS gestionada; la doc solo exige
`WEBHOOK_URL`/proxy/TLS cuando self-hosteás detrás de reverse proxy
`[llms ~20284, ~78545]` — en Cloud eso viene resuelto), pero el *egress* al
Worker manda: **runtime
de bordes = n8n VPS** (desplegado desde 2026-03, ADR-008), con
`WEBHOOK_URL` + TLS + websockets en el reverse proxy `[llms ~20284, ~78537]`.
n8n Cloud queda como **sandbox/lab opcional** sin `WORKER_TOKEN` ni
credenciales productivas. Cloudflare-524 (100 s) solo aplicaría a Cloud
`[llms ~61555]` — irrelevante si los bordes responden inmediato, como se
propone.

| Borde | Cloud vs VPS | Madurez | Riesgo ADR-011 | Prioridad | Dependencias |
|---|---|---|---|---|---|
| **B1** Telegram "ok publica" → Worker | **VPS** (loopback al Worker). Cloud: solo demo sin Worker real | Telegram Trigger GA (node 1.3) | **Bajo** — webhook entrante puro (regla #4); gate real vive en Worker (D3) | **1** | Bot Telegram (+ bot de test), chat_id David, `WEBHOOK_URL` HTTPS en VPS, `WORKER_TOKEN` como credencial n8n, export a git, GO David |
| **B2** Notion webhooks → Worker dispatch | **VPS** (mismo motivo). La suscripción Notion apunta al endpoint público del VPS | Webhooks Notion GA (mar-2025); nodo Webhook n8n GA. Semántica de entrega sin garantías documentadas (radar §6) | **Medio-bajo** — n8n solo lee/delega; riesgo real es tratar el payload como verdad (mitigado: Worker re-lee) o retirar el poller (mitigado: queda como reconciliación) | **2** | B1-infra (proxy/HTTPS), creación de suscripción por David, flags Worker correspondientes, verificación de token de suscripción |
| **B3** Cron + alertas HITL | **VPS** (llama `GET /health` y `/enqueue` en loopback) | Schedule Trigger GA; Telegram saliente GA | **Mínimo** — read-only + notify (regla #5, cron de operación) | **2** (empaquetable con B1: comparten bot y credencial) | Bot de B1, `WORKER_TOKEN`, `GENERIC_TIMEZONE`, mecanismo de scan a elegir en N3 (§2.B3: flag del poller o task Worker nueva) |
| **B4** Data Tables como estado HITL | n/a | GA (v1.113.1) — irrelevante | **Alto** — segunda fuente de verdad (criterios #2, anti-patrón #2) | **Rechazado** | n/a (uso residual de cache de dedupe: opcional, no canónico) |
| **B5** MCP `create_workflow_from_code` | Ambos sirven para *autoría*; el resultado se importa/exporta a VPS vía git. VPS puede apagar el módulo (`N8N_DISABLED_MODULES=mcp`) | Beta operativa (radar: beta v2.14; snapshot: disponible desde v2.12/2.13 sin label) | **Medio** — no toca Notion, pero sin aislación por cliente MCP y con `availableInMCP=true` auto | **3** (tooling) | Guardrails §2.B5, token MCP personal, revisión humana + export git antes de publicar |

---

## 4. Qué NO hacer (lista negativa explícita)

1. **n8n MCP Client Tool → servidor MCP de Notion (escritura).** Radar §5:
   delega la decisión de escritura a un LLM dentro del workflow — es
   funcionalmente "n8n escribe Notion" con un modelo en el medio. Viola
   ADR-011 #1. Prohibido.
2. **Doble escritura por agentes:** un agente (Cursor/Claude/Codex) con MCP
   Notion de escritura **y** acceso a n8n simultáneos puede escribir Notion
   por fuera del Worker (radar §3 riesgos). Regla de gobernanza: los writes
   editoriales de agentes van siempre vía Worker; el MCP Notion en IDEs se
   usa para lectura/diagnóstico, no para escribir superficies editoriales.
3. **Nodo nativo Notion de n8n en operaciones de escritura** (Database Page
   Create/Update, Page Create/Archive, Block Append `[llms ~43209]`) — y en
   particular **nunca adjuntar el nodo Notion como AI-agent tool** (expone
   los writes al LLM `[llms ~43205]`). Mitigación ya prevista en ADR-011
   §Riesgos: grep de CI sobre los JSON exportados buscando
   `n8n-nodes-base.notion` con operación de escritura.
4. **Notion Trigger nativo de n8n (polling) en producción** — duplica el
   Notion Poller del core y sus ejecuciones cuentan contra la cuota en
   planes de pago `[llms ~76956, ~99852]`. La vía event-driven correcta es
   B2 (webhook oficial → Webhook node).
5. **Data Tables como fuente de verdad de nada** (§2.B4).
6. **`create_workflow_from_code` en el camino productivo** — tooling de
   autoría solamente (§2.B5).
7. **Autopublish RRSS desde n8n** — Fila I = B es contrato (norte §5.I,
   LinkedIn ToS §3.1.26). n8n no postea a LinkedIn/X; a lo sumo avisa a
   David que hay `listo_rrss`.
8. **Exponer el Worker públicamente para que n8n Cloud lo alcance.** El
   Worker permanece en loopback; el motor de bordes se acerca al Worker
   (VPS), no al revés.
9. **Workflows sin export a git o con credenciales embebidas** (anti-patrones
   #5/#6). `infra/n8n/workflows/` debe nacer con el primer workflow.
10. **Make para cualquiera de estos bordes.** Sigue en stand-by formal; todos
    los bordes propuestos tienen nodo/camino n8n maduro, así que el árbol #7
    de ADR-011 nunca llega a Make. Y Make poll-eando Notion sigue prohibido
    (anti-patrón #3).
11. **Confiar en payloads de webhooks (Telegram o Notion) como estado.** El
    Worker re-lee Notion y re-aplica gates siempre; los webhooks solo
    despiertan.

---

## 5. Roadmap de paquetes orquestables post-GO (sin implementar nada aquí)

Cada paquete: PR propio, dry-run primero, gates=false, GO David explícito,
una flag/credencial a la vez (mismo protocolo que el smoke §GO David).

| Paquete | Contenido | Depende de | Entregable de cierre |
|---|---|---|---|
| **N0 — Fundaciones de gobernanza** | Crear `infra/n8n/workflows/` + runbook de export (cron nocturno o manual documentado); backup verificado de `N8N_ENCRYPTION_KEY` fuera del VPS (riesgo crítico ya listado en ADR-011); `WEBHOOK_URL` + TLS + websockets en reverse proxy; alta de `WORKER_TOKEN` como credencial n8n (nombre, no valor, en repo); decidir `GENERIC_TIMEZONE` | Acceso VPS; GO David | Runbook + primer export vacío o de prueba en git |
| **N1 — Puente Telegram (B1)** | Bot prod + bot test; workflow Telegram Trigger → validación doble chat_id → correlación (elegir §2.B1: **(a)** resolver Worker `publication_id→notion_page_id`, único código Worker de N1, o **(b)** botones inline con `callback_data`) → `POST /enqueue` con `input:{notion_page_id, telegram_confirmed:true}`; Error Workflow de aviso; smoke dry-run: Worker con `dry_run=true` responde `would_publish` sin red (patrón smoke G.2) | N0 | Export JSON en git + evidencia dry-run + marcador propio |
| **N2 — Webhooks Notion (B2)** | **Primero el cierre de la precondición §2.B2.3** (gates a nivel handler o allowlist de tasks en `/enqueue`, con tests — código Worker); luego: suscripción Notion (David) → Webhook node (Header auth + verificación token) → filtro eventos → `/enqueue`; poller documentado como reconciliación; matriz evento→task (read-only/log-only hasta el cierre) | N0 (+ idealmente N1 ya observado); flags Worker del caso | Export JSON + evidencia de evento sintético en dry-run |
| **N3 — Cron + alertas HITL (B3)** | Health-check Worker → alerta (sin código nuevo); alerta HITL-2: elegir mecanismo §2.B3 (**(a)** flag `NOTION_POLLER_ENABLE_HITL2_SCAN` + n8n solo canal saliente, o **(b)** task Worker nueva read-only `editorial.scan_hitl2_readiness` + polling `GET /tasks/{task_id}`); cadencias con `GENERIC_TIMEZONE` correcto | N0 + bot de N1 | Export JSON + primera alerta real recibida por David |
| **N4 — Tooling MCP (B5)** | Habilitar MCP de instancia (o decidir mantener `N8N_DISABLED_MODULES=mcp`); token personal; probar ciclo `validate_workflow`→`create_workflow_from_code` contra staging; documentar guardrails §2.B5 como checklist de PR | N0; independiente de N1–N3 | Nota ops con el ciclo probado + checklist en CONTRIBUTING o runbook |

Secuencia recomendada: **N0 → N1 → N3 → N2 → N4**. N1 es el de mayor valor
inmediato (cierra el único gap §I que es 100% de este carril y completa el
tercer leg del D3 end-to-end); N3 reusa su infraestructura con riesgo
mínimo; N2 es el de más cuidado semántico (entrega no garantizada); N4 es
tooling y puede esperar o descartarse sin afectar el pipeline.

**Lo que este roadmap NO desbloquea** (sigue siendo GO-David puro, fuera del
carril n8n): `MAGNIFIC_API_KEY`, creación de la DB Shortlist (P1),
`Copy LinkedIn empresa`, `EDITORIAL_BLOG_FUNCTION_URL`, y el encendido de
cada flag de poller.

---

## 6. Decisión solicitada a David

- [ ] GO/NO-GO **N0** (fundaciones — sin esto no hay carril n8n)
- [ ] GO/NO-GO **N1** (puente Telegram / B1)
- [ ] GO/NO-GO **N3** (alertas / B3)
- [ ] GO/NO-GO **N2** (webhooks Notion / B2)
- [ ] GO/NO-GO **N4** (tooling MCP / B5) — o mantener módulo MCP apagado
- [ ] Confirmar **rechazo de B4** (Data Tables como estado HITL)
- [ ] Confirmar **n8n VPS como runtime de bordes** (Cloud solo sandbox)

---

## Referencias

- [editorial-smoke-e2e-p3-2026-07-23.md](editorial-smoke-e2e-p3-2026-07-23.md) — smoke P3 y matriz §I
- [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) — norte, D3, Fila I = B
- [editorial-hitl2-publish-bridge-p26-2026-07-23.md](editorial-hitl2-publish-bridge-p26-2026-07-23.md) — gate `telegram_confirmed` (P2.6)
- [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) · [ADR-008](../adr/ADR-008-orquestacion-editorial.md) · [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) · [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md) · [ADR-005](../adr/ADR-005-publicacion-multicanal.md)
- Radar Perplexity: `radar n8n y notion.md` (Drive, ruta en §0) — leído completo
- Snapshot docs n8n: [docs/external-context/n8n-llms-full.txt](../external-context/n8n-llms-full.txt) (las citas `[llms ~NNNN]` son líneas aproximadas de ese archivo)
- `worker/n8n_client.py` · `worker/app.py:756` (`POST /enqueue`) · `.env.example:157-158`

---

**Marcador:** `N8N_NOTION_INTEGRATION_PROPOSAL_READY`
