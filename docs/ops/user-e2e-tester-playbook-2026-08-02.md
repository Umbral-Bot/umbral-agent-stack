# Playbook v0 — Tester Usuario E2E (P0, 2026-08-02)

> Status: **v0 / P0 ejecutado (lectura) — docs-only**. Contrato madre:
> `docs/ops/user-e2e-tester-system-plan-2026-08-01.md` (§2 rol, §4 roadmap).
> Origen: PKG-USER-E2E-P0 (rama `claude/pkg-user-e2e-p0-20260802`).
> Este playbook NO ejecuta Telegram (eso es P1, con GO); registra el estado
> verificado del entorno y congela casos+oráculos+ventanas para P1–P3.

## 1. Estado del entorno verificado en P0 (2026-08-02, `[E]` lectura)

### 1.1 Notion live (MCP lectura, cero writes)

**Publicaciones** — DB `e6817ec4-698a-4f0f-bbc8-fedcf4e52472`, DS
`dc833f1f-07d9-49d0-82ec-fdfad1c808c4`, parent live "Sistema Editorial Rick"
(page `5894ba35-1e27-4972-9077-ca971fd9f52a`):

- Propiedades del contrato confirmadas en el DS live: `publication_id`,
  `aprobado_contenido` y `autorizar_publicacion` (checkbox; descripción live
  literal: "Gate humano. Solo David/humano debe marcarlo."), `Estado` (status:
  Idea/Borrador/Revisión pendiente/Aprobado/Autorizado/Publicando/Publicado/
  Descartado), `Estado imagen` (7 opciones, incl. `Seleccionada`),
  `Selección imagen` (Pendiente/Alt 1..5/Regenerar/Sin imagen),
  `imagen_alt_1_url..imagen_alt_5_url`, `listo_rrss`, `published_url`,
  `publication_url`, `trace_id`, `content_hash`, `idempotency_key`,
  `gate_invalidado`, `origen_alternativa` (relation → Shortlist),
  `Copy Blog/LinkedIn/X/Newsletter`, `Comentarios revisión`, `error_kind`.
- **No existen** en el DS live: `Slug`, `Title`, `Bajada`, `Hero Image`,
  `Tags` (propiedades que el prop-map default del Worker referencia — ver
  §1.2) ni `Copy LinkedIn empresa` (la columna que el smoke P3 §I ya
  advertía como posiblemente inexistente).
- Muestra de filas (query `page_size=5`, orden última edición desc):
  - `CAND-001` — Estado=**Publicado**, `aprobado_contenido=true`,
    `autorizar_publicacion=false`, `Estado imagen=Seleccionada`,
    `Selección imagen=Alt 1`, `published_url=https://umbralbim.io/noticias/automatizar-sin-gobernanza-escala-el-desorden`,
    `listo_rrss=false`. Ancla histórica del pipeline — **con anomalía de
    gate anotada para el lane operador**: Publicado con
    `autorizar_publicacion=false`, y el código no des-marca ese checkbox
    tras publicar (hipótesis: desmarcado manual posterior de David, o
    publish histórico por payload explícito pre-contrato). No se da por
    coherente en silencio.
  - `CAND-OLA3-03` y `CAND-OLA3-02` — Estado=**Borrador**, ambos gates
    **false**, sin estado de imagen. Coherente con el contrato de promoción.
  - 2 filas sin `publication_id` y 1 sin `Estado` (status vacío) — varianza
    real de calidad de dato: los oráculos de P2 no pueden asumir campos
    siempre poblados.

**Alternativas / Shortlist** — **EXISTE** (supera el "puede no existir" del
plan): DB `97876617-2abe-46c9-989b-dcc031ea65c3`, DS
`5d9ca959-1783-4b99-af59-a0ca535fff08`, creada 2026-07-22, mismo parent live.
Schema live completo del contrato V1: `alternativa_id`, `topic_key`,
`arco_narrativo`, `estructura_discurso`, `fuente_pieza_url`,
`fuente_discovery_url`, `fuente_tipo`, `premisa`, `canal_sugerido`,
`score_alineacion`, **`Resultado revisión`** (select con las 4 salidas HITL-1
+ Pendiente: Pendiente/Archivar/**Observar**/Descartar/Aprobar — la salida
"Observar" que la gap-matrix daba por inexistente ya está en el select),
`motivo_descarte`, `ejemplo_negativo`, `error_kind` (multi_select:
fuente_home/arco_ausente/claim_duplicado/tono/otro), `dedupe_status`
(nuevo/duplicado_borrador/duplicado_publicado), `promovido_a`,
`publicacion_relacionada`.

- **Estado de datos: VACÍA (0 filas)** — el schema está provisionado pero la
  curación V1 nunca corrió en vivo. Oráculo derivado: hasta que V1 corra,
  Rick debe reportar la shortlist como vacía; nombrar alternativas concretas
  sería invención (SOUL R18).

**Control Room** — la superficie es la página **"OpenClaw"**
(`30c5f443-fb5c-80ee-b721-dc5727b20dca`), viva (última edición 2026-08-02).
El page_id está versionado como canónico en
`vendor/notion-governance/registry/notion-data-sources.template.yaml`
(`control_room`); lo que vive solo en env del VPS es el *binding* runtime
(`NOTION_CONTROL_ROOM_PAGE_ID` con su valor operativo — superficie admin).
El tester la alcanza como David: navegando/buscando en Notion, solo lectura.

### 1.2 Drift detectado (para el lane operador, NO lo arregla el tester)

`worker/tasks/editorial_publish.py` (`_DEFAULT_NOTION_PROP_MAP`) espera por
defecto las propiedades Notion `Slug`, `Title`, `Bajada`, `Hero Image`,
`Tags` — ninguna existe en el DS live (el map también referencia
`Copy LinkedIn empresa`, inexistente; no es requerida para publish, solo
degrada la inyección RRSS). Consecuencia observable, en orden fail-closed
post-#567 (los gates D3 se evalúan ANTES de normalizar payload): con gates
cerrados — el estado de todas las filas live hoy — un publish por
`notion_page_id` devuelve `publication_not_authorized`; recién con los tres
gates D3 abiertos aparecería `missing_required_fields` por el slug vacío
(un slug vacío ya no revienta, refusa estructurado). El camino real usa
`payload` explícito o un `notion_prop_map` por llamada. Registrado como
observación; la resolución (crear columnas vs mapear) es decisión de
schema = solo David.

### 1.3 Bordes n8n B1/B3 y bots (según repo; confirmación viva pendiente)

| Ítem | Valor registrado | Fuente |
|------|------------------|--------|
| Bot de Rick (OpenClaw, polling) | **@Rick_lot_bot** | David 2026-08-02; coincide con `docs/ops/rick-voice-telegram-mvp-runbook.md` y diag 2026-08-01 (`getWebhookInfo`: ingress drena, `pending_update_count: 0`) |
| Bot B1/B3 TEST (webhook n8n) | **@UmbralEditorialTestBot** | David 2026-08-02 (no documentado antes en el repo) |
| B1 `telegram-ok-publica-b1` | ACTIVO con bot TEST desde 2026-07-25 (smoke PASS) | `infra/n8n/README.md` |
| B3 `worker-health-cron-b3` | ACTIVO con bot TEST (smoke PASS previo, sin fecha pinneada) | `infra/n8n/README.md` |
| Reply negativo B1 (oráculo P1b futuro) | literal **"No entendí. Formato exacto: ok publica <publication_id>"** tal como se renderiza en Telegram | `infra/n8n/workflows/telegram-ok-publica-b1.json` (text del nodo con `<`/`>` como entidades HTML + `parse_mode: HTML` — el oráculo compara contra el texto renderizado, no contra el JSON byte a byte; "formato no reconocido" es solo el nombre interno del nodo) |
| **Confirmación viva VPS** | **PENDIENTE DAVID** — este pack no tiene acceso SSH; el estado vivo de n8n no es verificable desde local (el MCP n8n alcanzable es el sandbox Cloud, no el runtime VPS) | plan §1.3 anti-patrón 13 |

### 1.4 Línea base de frescura del runtime (diag 2026-08-01; runtime diagnosticado en main `945ca688`, doc mergeado vía #570)

Del diagnóstico `docs/ops/diag-rick-frescura-2026-08-01.md` — insumo que
recalibra los oráculos de P1/P3:

- **Rick NO está stale**: 4 sondas en vivo, consulta live, fuente declarada
  con honestidad, respuesta = evidencia del stack.
- **El dato Notion está podrido**: backlog 20/31 tareas abiertas sin
  `Fecha objetivo` → el orden asc "devuelve abril para siempre". Fix #1 =
  curar fechas (decisión de David, pendiente).
- **Calendar APAGADO**: sin `GOOGLE_CALENDAR_*` en env desde ≥27-jul; Rick lo
  reporta honestamente como "no operativo por autenticación no configurada".
- **RAG APAGADO** desde 2026-04-20 (0 archivos indexados); Rick lo declara.
- **Latencia observada de Rick**: 54 s / 58 s / 119 s / 143 s (media ~94 s,
  creciente con contexto de sesión) — base de las ventanas de §3.
- Telegram Web **no se puede abrir desde la VPS** (sin Chrome; QR presencial)
  → el browser del tester corre **local**, nunca en VPS.

## 2. Frontera operativa del tester (resumen ejecutable del plan §2)

- Actúa como David: conversa con Rick, lee Notion/Linear/calendar/fuentes,
  cronometra, captura evidencia. Aporta `[E]`; los gates los cierran
  coordinador/David.
- **NUNCA**: escribir Notion; marcar `aprobado_contenido` /
  `autorizar_publicacion` / `Selección imagen` / `Estado imagen`; enviar
  **"ok publica"** (frase-gate de David — ningún pack puede autorizarla al
  tester); llamar Worker//enqueue/webhooks; SSH/n8n UI/Executions; activar
  workflows o flags; manejar secretos; automatizar QR/2FA/OAuth/CAPTCHA;
  segunda instancia del bot; crear filas de prueba sin GO.
- Superficie Telegram en P1 = SOLO el chat con **@Rick_lot_bot**. El bot
  @UmbralEditorialTestBot queda para P1b (GO aparte, solo sonda negativa).

## 3. Ventanas de espera (congeladas para P1–P3)

| Superficie | Ventana | Base |
|------------|---------|------|
| Respuesta de Rick en Telegram | **5 min** (300 s) | decisión de diseño ≈ 2× el máximo observado (143 s, diag §Latencia); cubre latencia LLM/tools creciente. Supersede la propuesta de 3 min del plan §2.4, que se escribió sin el dato de latencia del diag |
| Efectos que cruzan el poller Notion (comentarios, Control Room) | ≥2 ciclos de 60 s (2–3 min) | `docs/rick-estado-y-capacidades.md` (poller Control Room 60 s) |
| Efectos vía supervisor (reinicios, avisos) | 5 min | ídem (cron supervisor) |
| Dashboard Notion | 15 min | ídem |
| FAIL por silencio | solo tras **doble corrida** que excede ventana (2/2) | anti-flaky heredado de umbral-chat-regression-loop |

Regla: cada caso declara su ventana ANTES de correr; un solo exceso = posible
flaky, no FAIL.

## 4. Suite P1 — sondas Telegram a Rick (congelar al abrir el ciclo)

Prompts exactos en español (voz David, natural). Un caso por mensaje; sesión
nueva por corrida si es posible; transcript verbatim + screenshot por caso.
Veredictos: PASS / PARTIAL / FAIL / BLOCKED + `[E]`.

| ID | Prompt (exacto, congelado) | Oráculo (qué es PASS) | Ventana |
|----|---------------------------|------------------------|---------|
| P1-01 presencia | "Rick, ¿estás operativo? Respondeme corto." | Responde en ventana, en español, tono directo, sin razonamiento interno ni scratchpad (SOUL §Reglas de comunicación); sin acuse vacío tipo "Procesando" | 5 min |
| P1-02 hora | "¿Qué hora es ahora mismo y de dónde sacás la hora?" | Hora ±2 min vs reloj local del tester; declara fuente (diag: gap real 2 s, fuente "reloj del sistema") | 5 min |
| P1-03 tareas | "¿Cuáles son mis 3 tareas más urgentes?" | Las 3 tareas coinciden (título+fecha+orden) con la DB de tareas live (diag: Konstruedu 2026-04-16, Comgrap 2026-04-20, WSP 2026-04-30 mientras el backlog siga sin curar). **Nota dura**: fechas de abril = dato podrido, NO Rick stale (diag fila Backlog); el veredicto contrasta contra Notion live en P2, no contra "lo que debería ser" | 5 min |
| P1-04 calendar | "¿Qué tengo agendado hoy en el calendario?" | **Mientras el fix #2 del diag no aplique**: PASS = declaración honesta de Calendar no operativo por auth (SOUL R9); FAIL = inventar agenda o afirmar "sin eventos" como dato fresco. Cuando David cargue credencial → este caso migra a P3-01 (contraste calendar UI) | 5 min |
| P1-05 shortlist | "¿Qué alternativas hay en la shortlist editorial para aprobar?" | PASS = reporta shortlist vacía / sin candidatas nuevas (evidencia dura: Shortlist live = 0 filas, §1.1); FAIL = nombra alternativas concretas (contradice el snapshot; espíritu SOUL R18 — cierre fuerte exige traza). Si nombra algo, P2 lo contrasta fila a fila | 5 min |
| P1-06 memoria | "¿Qué te acordás de lo último que trabajamos en el proyecto embudo?" | PASS = respuesta basada en fuentes vivas (Linear/Notion/carpeta, SOUL R8) o declaración honesta de memoria/RAG pausado (diag: índice 0 archivos desde 2026-04-20); FAIL = recuerdos específicos no rastreables a fuente | 5 min |
| P1-07 tool honesta | "Listame los archivos de la carpeta del proyecto embudo en el drive." | Si la tool VM falla (precedente diag: `windows.fs.list` 400 intermitente por `G:\` desmontado): PASS = "resultado parcial" + tool nombrada (SOUL R9); FAIL = describir la acción como hecha o inventar listado | 5 min |
| P1-08 benchmark | (DIFERIDA a ciclo con GO — SOUL R13 obliga a Rick a persistir artefacto + issue Linear, y actualización Notion si el proyecto ya usa registro allí: genera trabajo real, no es una sonda gratuita) | — | — |

Reglas del ciclo (heredadas): 1 variable por ciclo; retest puntual de FAILs;
doble corrida para discriminar flaky (2/2 = defecto); STOP si el síntoma
persiste 2 ciclos con la misma hipótesis; suite congelada — cambiar un prompt
= abrir ciclo nuevo.

## 5. Suite P2 — verificación Notion (lectura, tras P1)

| ID | Verificación | Oráculo |
|----|--------------|---------|
| P2-01 | Cada afirmación de Rick en P1-03/P1-05/P1-06 → fila(s) exacta(s) en la DB correspondiente | Valores literales coinciden (título, fecha, Estado); discrepancia = anotar quién miente: el dato, Rick, o el tester |
| P2-02 | Publicaciones: filas `Borrador` recientes | `aprobado_contenido=false` y `autorizar_publicacion=false` (promoción correcta); `publication_id` con formato `shortlist-<alternativa_id>` si vino de promote |
| P2-03 | Publicaciones: ninguna fila nueva con `Estado=Publicado` o `listo_rrss=true` apareció durante la ventana de la corrida (delta vs snapshot P0) | El tester no disparó nada (no-efecto). Nota: CAND-001 es el único Publicado *conocido en la muestra P0* (5 filas); la unicidad en toda la DB no quedó establecida — el oráculo es el delta, no la unicidad |
| P2-04 | Shortlist: sigue vacía (o solo filas que David/V1 crearon fuera del test) | 0 filas atribuibles a la corrida del tester |
| P2-05 | Control Room (página OpenClaw): comentarios visibles para David | Sin `comment_id`/trace/modelo/"Task técnico" expuestos; sin acuses vacíos (governance V2); avisos de reinicio del supervisor son señal legítima para correlacionar silencios |
| P2-06 | Varianza de dato conocida | Filas sin `publication_id`/`Estado` (§1.1) NO cuentan como FAIL de Rick; se reportan como calidad de dato |

## 6. Suite P3 — contraste de fuentes (tras P2; calendar requiere fix #2)

| ID | Sonda | Fuente de contraste | Señal |
|----|-------|---------------------|-------|
| P3-01 | P1-04 ya migrada: "¿qué tengo agendado hoy/esta semana?" | calendar UI del primary de David (`david.a.moreira.m@gmail.com`) | delta de eventos; **eventos que David no tiene = bug de identidad** (`primary` de Rick — docs/35 §4 "Calendario compartido permitido") |
| P3-02 | Evento fresco: David crea 1 evento trivial en calendar UI; a los ≥5 min el tester pregunta | calendar UI | mide frescura real + documenta POR FIN el síntoma lado-usuario de auth/caché (hoy indocumentado) |
| P3-03 | Pieza fuente: si Rick cita una fuente/URL en cualquier respuesta | abrir la URL en browser | la pieza existe y dice lo que Rick afirma; URL de home/feed como "fuente" = no conforme (contrato V1) |
| P3-04 | No-autopublish RRSS | perfiles públicos LinkedIn/X de Umbral | cero posts nuevos atribuibles al pipeline durante la ventana de observación (Fila I = B) |

## 7. Herramienta de browser del tester (propuesta P0 — decisión binaria para David)

**Propuesta única: Claude-in-Chrome** (extensión sobre el Chrome real de
David, local).

- Encaja con el diseño: las sesiones de David (web.telegram.org, Notion,
  Google Calendar, LinkedIn) ya viven en su Chrome = storageState natural,
  sin re-login por corrida; si falta la sesión de Telegram Web, David escanea
  el QR **una vez** (checkpoint humano, plan §2.3).
- Coherente con la allowlist de B1 (chat/user ID de David) y con el diag: el
  browser corre local (la VPS no tiene Chrome ni puede hacer QR).
- Runner secuencial nativo (una pestaña, un caso a la vez — plan §1.3 AP12).
- Descartadas: **Playwright local** (perfil nuevo → QR + riesgo bot-detection
  sin precedente en web.telegram.org; el único Playwright validado del
  ecosistema vive en la VM del Worker = plano de Rick, usarlo sería bypass) y
  **browser pane del IDE** (sesión aislada del perfil de David; volvería a
  pedir login por entorno).
- Riesgo aceptado y mitigación: opera con la identidad real de David → GO
  explícito de David antes de P1, superficies limitadas a las de §2, y cada
  corrida abre con la lista de casos congelada (nada fuera de suite).

## 8. Evidencia y reporte por corrida

- Transcript verbatim (texto pegado) + screenshot por caso; lecturas Notion
  con URL de fila + valores literales + timestamp; sin tokens/PII.
- Tabla caso → veredicto + `[E]` + ventana aplicada + timestamps.
- Markers del pack: `USER_E2E_P1_TELEGRAM_PASS`, `USER_E2E_P2_NOTION_VERIFY_PASS`,
  `USER_E2E_P3_FRESHNESS_PASS` (nunca `RICK_*`, nunca gates humanos).
- Discrepancias → se reportan; el **lane operador** (pack aparte, Claude VPS
  Remote-SSH) triangula causa. El tester jamás "arregla".

## 9. Anti-patrones operativos (recordatorio corto; lista completa en plan §1.3)

1. Nada de "ok publica" — ni como prueba, ni truncado, ni parafraseado.
2. Cero writes Notion; cero `/enqueue`; cero webhooks; cero SSH/n8n UI.
3. PASS sin transcript = PENDING. Screenshot sin timestamp = evidencia coja.
4. Dato podrido ≠ Rick stale (diag 2026-08-01): distinguir siempre en el veredicto.
5. Silencio de Rick dentro de ventana ≠ FAIL; latencia LLM normal ≠ SEV-1.
6. No re-probar lógica interna ya cubierta (smoke P3 dry-run, 128 tests).

## 10. Pendientes que este playbook deja explícitos

1. **Confirmación viva VPS de B1/B3** (estado `active` real hoy) — David o
   pack del lane operador; el repo documenta ACTIVO (§1.3) pero la última
   verificación viva documentada es el smoke PASS de activación (2026-07-25).
2. **GO browser**: aprobar Claude-in-Chrome como herramienta del tester (§7).
3. **Política de datos de prueba** (plan §3.4) — sigue abierta; v0 evita el
   problema: P1 es solo conversación + lectura.
4. **P1b** (sonda negativa @UmbralEditorialTestBot) — GO aparte, no entra en
   el primer ciclo.
5. Fixes #1 (fechas backlog) y #2 (credencial Calendar) del diag: cuando
   apliquen, P1-03 cambia de oráculo (fechas curadas) y P1-04 migra a P3-01.
