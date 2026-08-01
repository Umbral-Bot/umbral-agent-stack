# Sistema de testing E2E en rol usuario — plan + investigación (2026-08-01)

> Status: **docs-only / diseño**. Este documento no implementa el tester, no crea skills,
> no escribe en Notion, no activa nada en VPS/n8n. Origen: PKG-USER-E2E-PLANNER
> (rama `claude/pkg-user-e2e-planner-20260801`).

## 0. Decisión LOCKED (David, 2026-08-01)

1. Esta etapa = **solo diseño + planificación + investigación**. Cero skill nueva en el
   registry. Cero automatización productiva. Cero writes en Notion "para simular al usuario".
2. Orden inmutable: **plan (este doc) → experiencia real (packs futuros, con GO) → recién
   entonces capitalizar en skill** (nueva o actualización). No invertir el orden.
3. El tester actúa **como el usuario (David)**: Telegram, Notion, fuentes. No inventa atajos
   por el Worker/MCP write "porque es más fácil".

Referencia de método: `cursor-orchestrator` ya manda "no reinventar E2E — heredar"
(`~/.cursor/skills/cursor-orchestrator/reference-e2e-reuse.md`, principio 6: primer prompt
PLAN = "map existing E2E assets to reuse"). Este doc es exactamente ese prompt PLAN.

---

## 1. F0 — Inventario: qué existe, qué cubre, qué hueco deja

### 1.1 Catálogo (paths verificados en disco 2026-08-01)

| # | Activo | Path real | Qué es |
|---|--------|-----------|--------|
| 1 | cursor-orchestrator v0.2.1 | `~/.cursor/skills/cursor-orchestrator/SKILL.md` (= canónico `C:\GitHub\umbral-skills-registry\skills\cursor-orchestrator\SKILL.md`) | Gobernanza de paquetes, gates `[E]`, roles, formato PKG |
| 2 | reference-e2e-reuse | `~/.cursor/skills/cursor-orchestrator/reference-e2e-reuse.md` | Patrones E2E cross-project: storageState, zero-credit smokes, agent browser + human OAuth checkpoints |
| 3 | umbral-rick-runtime | `C:\GitHub\umbral-skills-registry\skills\umbral-rick-runtime\SKILL.md` (= copia `~/.claude/skills/`) | Frontera de rol: nadie sustituye a Rick; ciclo adjust→test; superficies canónicas UAS |
| 4 | reference-gates (rick-runtime) | `~/.claude/skills/umbral-rick-runtime/references/reference-gates.md` | Marcadores `RICK_*`, evidencia de identidad del productor (2026-07-28), evidencia NO aceptable |
| 5 | umbral-bot-publish-qa | `~/.cursor/skills/umbral-bot-publish-qa/SKILL.md` | QA browser del producto Umbral Bot (Comet + checklist + gates encadenados). **Scope guard: prohibido usarla para UAS/OpenClaw** |
| 6 | umbral-chat-regression-loop | `~/.cursor/skills/umbral-chat-regression-loop/SKILL.md` | Loop de regresión por capas L0-L3, suite congelada, "sin transcript → sin PASS" (Umbral Bot) |
| 7 | openclaw-vps-operator | `.claude/skills/openclaw-vps-operator/SKILL.md` (repo) | Superficies VPS vivas, health checks, VPS-first/VM-opcional — todo **admin (SSH)** |
| 8 | notion-governance-runtime | `.claude/skills/notion-governance-runtime/SKILL.md` (repo) | Qué debe/no debe ver David en Notion; writes manuales exigen `notion.operation_trace` |
| 9 | /e2e command | `.claude/commands/e2e.md` (repo) | Diagnóstico técnico pytest/scripts. **No es rol usuario** — colisión de nombre, no de contenido |
| 10 | Contrato norte HITL | `docs/ops/editorial-norte-hitl-contract-2026-07-22.md` | Flujo A-I, D3 triple gate, Fila I=B, salidas HITL-1 |
| 11 | Matriz de brecha | `docs/ops/editorial-gap-matrix-norte-2026-07-22.md` | 0 OK / 10 PARCIAL / 1 ajustada — qué está cableado de verdad |
| 12 | Smoke E2E P3 | `docs/ops/editorial-smoke-e2e-p3-2026-07-23.md` | 8 tramos dry-run con mocks, 128 tests; **cero red real**; matriz de disposición §I |
| 13 | Runbook n8n N0 | `docs/ops/n8n-n0-foundations-runbook-2026-07-24.md` | B1/B3 TEST, allowlist, acceso UI solo por túnel SSH, anti-forja de webhooks |
| 13b | Estado n8n + exports | `infra/n8n/README.md`, `infra/n8n/workflows/telegram-ok-publica-b1.json` | Estado vigente: **B1/B3 ACTIVOS con bot TEST desde 2026-07-25 (smoke PASS)**; el sufijo "(INACTIVE)" en nombres quedó obsoleto; el export versionado es fuente de verdad e incluye los 3 replies de B1 |
| 14 | Flujo editorial canónico | `docs/ops/editorial-agent-flow.md` | Pasos 1-10 y responsabilidades por agente (curación → QA → gates humanos) |
| 15 | SOUL de Rick | `openclaw/workspace-templates/SOUL.md` | Reglas base (Personalidad + comunicación, sin numerar) + Reglas 4-21 (18 numeradas; R1-R3 no existen) — oráculos conversacionales observables |
| 16 | Deuda frescura / auth | `docs/35-google-calendar-token-setup.md`, `docs/ops/gd52-reoauth-runbook.md`, `docs/ops/auth-lifecycle-tracking.md`, `docs/ops/notion-poll-comments-sev1-triage-2026-05-05.md` | Ventanas de caducidad, SEV-1 de silencio, cadencias del runtime |
| 17 | Precedente browser | `docs/64-browser-automation-vm-plan.md`, `docs/audits/browser-vm-control-validation-2026-03-10.md` | Playwright validado en VM Worker (slice `browser.*`, 2026-03-10); jerarquía typed > GUI > PAD |
| 18 | test-incognitas-plantadas | `~/.claude/skills/test-incognitas-plantadas/` (+ registry) | Método para evaluar skills de proceso con incógnitas plantadas — relevante recién en la fase skill |
| 19 | pkg-receiver-protocol | `~/.claude/skills/pkg-receiver-protocol/` (+ registry) | Contrato ACK/REPORT que los packs del roadmap F3 reutilizan tal cual |

Informe E2E-Rick de otro hilo: **no existe en main** (grep en `docs/` sin hits; ramas remotas
revisadas). El insumo más cercano es la rama sin PR
`claude/plan-sys-diag-openclaw-worksystem-2026-07-17` (inventario sys-diag, 15 archivos).
Cuando ese informe aterrice, los packs F3 lo consumen como entrada de triage — no se duplica aquí.

### 1.2 Matriz cobertura vs hueco (para *este* proyecto: tester rol-usuario de Rick editorial + ops UAS)

| Activo | Ya cubre (reusar) | Hueco que deja |
|--------|-------------------|----------------|
| cursor-orchestrator + reference-e2e-reuse | Contrato de evidencia `[E]`; figura "verificador ≠ implementador" que cierra `X_PASS` live con checklist pre-escrita; formato PKG para los packs; principios storageState / human OAuth checkpoints / zero-credit | No existe rol "agente que emite inputs de usuario"; no regula qué superficies toca el verificador; sesión browser con identidad de David sin procedimiento |
| umbral-rick-runtime + reference-gates | Frontera dura (nadie escribe Publicaciones salvo Rick/Worker); taxonomía PASS/PARTIAL/BLOCKED; marcadores `RICK_*`; evidencia de identidad del productor (run id + lane + ventana temporal) | "Smoke runtime" es un trigger sin procedimiento; cero mención de Telegram/daemon/n8n/calendar; el rol tester-usuario no existe en su tabla |
| umbral-bot-publish-qa | Patrón de gates encadenados con markers greppables; disciplina screenshot/URL por paso; candado "el agente declara gate, David declara cierre" | Scope guard explícito la prohíbe para UAS ("Never mix them"); su tester escribe gates en Notion (contradice al tester-lector); herramienta = Comet, sin receta trasplantable |
| umbral-chat-regression-loop | Suite congelada de casos ID+prompt+esperado; "sin transcript → sin PASS"; 1 variable por ciclo; doble corrida anti-flaky; L3 = browser humano/storageState | L0-L2 son white-box (inutilizables sin bypass); pensada para el chat del producto, no para conversar con Rick; evidencia de sesión larga sin resolver |
| openclaw-vps-operator + /vps + /e2e | Catálogo de causas raíz para triage; SLAs implícitos; plantilla de cierre (estado real, drift, credencial vs bug) | Toda superficie es SSH/admin — nada de esto es rol usuario; /e2e es pytest, no experiencia |
| notion-governance-runtime | Checklist de lectura: qué debe ver David (sin trace_id, sin acuses vacíos, español natural) → oráculos de UX verificables leyendo | No define rol lector formal (token/alcance de un tester de solo-lectura) |
| Contrato norte + gap matrix + smoke P3 | Happy path A-I completo; nombres exactos de campos (`Resultado revisión`, gates, `Estado imagen`); qué es exclusivo de David; qué ya se probó dry-run (no re-probar lógica interna) | Todo fue mocks: nadie recorrió el sistema vivo como usuario; gate visual D3 sin ejercitar; Shortlist DB puede no existir aún; SLAs de espera sin definir |
| Runbook n8n N0 + `infra/n8n/README.md` | Contrato B1 exacto: `ok publica <publication_id>` desde chat allowlisted; los 3 replies documentados en el export JSON ("✅ Encolado publish. task_id: …", fallo de `/enqueue`, "formato no reconocido"); B3 = alerta única; estado vigente B1/B3 ACTIVO con bot TEST (2026-07-25, smoke PASS) | Handle del bot TEST no documentado (la credencial se nombra, el @handle no); el happy path no es ejercitable por el tester (la frase es el gate de David, §2.2/§3.1); verificación "se encoló" es admin (Executions) |
| SOUL.md (reglas base + R4-R21) | Oráculos conversacionales observables: ejecuta antes de excusarse (reglas base), honestidad ante errores de tools (R9), benchmark = artefacto persistido (R13), "verificado" solo con evidencia (R18), voz (R21) | Es contrato del lado Rick; no define qué pregunta el usuario para gatillar cada regla — la suite de sondas hay que diseñarla (F2) |
| Docs frescura/auth | Ventanas de caducidad (access ~1h; refresh app Testing ~7d); calendar único válido = primary de David; precedente de fallo silencioso (SEV-1 2026-05-05: silencio prolongado sin alarma); cadencias (poller Notion 60s, supervisor 5min, health 30min) | Síntoma lado-usuario de auth rota **indocumentado** (¿error, silencio o dato stale?); "memoria stale" conversacional sin baseline; sin alerta proactiva de expiry |
| Precedente browser | Playwright typed validado sobre web moderna real (2026-03-10); persistent context para sesiones; política CAPTCHA → pausa + David | Cero precedente de web.telegram.org / QR / 2FA; la infra validada es el plano de ejecución de Rick (usarla = bypass); tooling del tester local sin decidir |

**Conclusión F0:** el ecosistema tiene la *gramática* del testing (evidencia, gates, suites
congeladas, checkpoints humanos) pero **ningún activo cubre el rol "agente que actúa como el
usuario"**. El hueco es exactamente ese rol + sus superficies + sus oráculos; todo lo demás
se hereda, no se reinventa.

### 1.3 Anti-patrones prohibidos en el diseño (consolidado, con fuente)

1. **Bypass de Rick**: crear filas en Publicaciones o copy final desde el tester/orquestador
   (umbral-rick-runtime §Roles; cursor-orchestrator §Anti-patterns; ADR-011: monopolio de
   escritura del Worker).
2. **Docs fingiendo PASS**: cerrar un gate de experiencia con markdown sin runtime; PASS sin
   `[E]` = PENDING (cursor-orchestrator §Plans & gates).
3. **Inventar datos**: sin transcript → sin PASS; screenshots/salidas literales o nada
   (umbral-chat-regression-loop non-negotiable 2; reference-gates §Evidencia NO aceptable).
4. **Auto-marcar gates humanos**: `aprobado_contenido`, `autorizar_publicacion`,
   `Estado imagen=Seleccionada`, "ok publica" — solo David, ni siquiera "para probar"
   (contrato norte §5.H; reference-gates; human-review-contract).
5. **Forjar webhooks o llamar al Worker directo**: la ruta del webhook Telegram vive solo en
   el VPS a propósito; `/enqueue` no es superficie de usuario (runbook n8n §1.1 nota anti-forja).
6. **Escribir Notion desde el tester**: MCP Notion en agentes = lectura/diagnóstico; todo write
   manual exige `notion.operation_trace` que el rol usuario no tiene (propuesta n8n §4.2;
   notion-governance-runtime §Trazabilidad).
7. **Colar superficies admin en el rol usuario**: SSH, n8n UI (túnel + login owner), health
   endpoints, journalctl, Executions — son del *operador de contraste*, no del tester (§2.2).
8. **Activar/desactivar workflows n8n o flags de poller**: activación = GO David, una a la vez
   (smoke P3 §I; runbook §6 paso 5).
9. **Automatizar login/QR/2FA/OAuth/CAPTCHA o manejar secretos**: checkpoints humanos de David;
   el agente no posee credenciales (reference-e2e-reuse principio 3; plan browser §9;
   chat-regression: prohibido automatizar "Permitir" OAuth).
10. **Levantar una segunda instancia del bot de Rick** para "observarlo": 409 getUpdates
    (docs/04 §Troubleshooting). El tester observa como *cliente* (cuenta de David), jamás como bot.
11. **Mezclar superficies de Umbral Bot producto con UAS**: scope guard literal de
    umbral-bot-publish-qa ("Never mix them") — se heredan *patrones*, no superficies ni dashboards.
12. **Paralelo sobre la misma sesión browser persistente**: el estado Playwright se pisa
    (audit 2026-03-10 §2). Runner secuencial.
13. **Verificar contra el n8n Cloud MCP creyendo que es el runtime**: el MCP alcanzable es
    sandbox; el runtime de bordes vive en el VPS (runbook §0).
14. **Crear filas/datos de prueba sin GO**: precedente smoke P3 ("preferir no crear filas");
    política de datos de prueba = decisión explícita de David (§3.4).
15. **Dos autorizaciones excluyentes en un mismo pack**: regla 10 de cursor-orchestrator;
    el camino es uno.

---

## 2. F1 — Rol "Tester Usuario"

### 2.1 Persona

**Es**: un agente que reproduce la experiencia de David con sus superficies de usuario y reporta
lo observado con evidencia. Estructuralmente es el **"verificador distinto"** que
cursor-orchestrator ya define (verificador ≠ implementador, cierra contra estado live con
checklist pre-escrita), especializado en la superficie usuario. Su REPORT **aporta `[E]`**;
el cierre del gate lo hace el coordinador o David — el tester no cierra gates propios.

**Ve**: el chat de Telegram con Rick (y con el bot B1 TEST si entra en alcance), las DBs/páginas
Notion que David ve (Publicaciones, Shortlist si existe, Control Room, dashboard), Linear en
lectura (proyectos/issues que Rick cita), el calendar UI de David, las páginas públicas de
fuentes citadas por Rick y los perfiles públicos LinkedIn/X de Umbral (solo para verificar
que NO hubo autopublish).

**Puede**: enviar mensajes a Rick como David (sondas conversacionales); leer Notion (MCP lectura
o browser); leer calendar UI; comparar y cronometrar (SLAs §2.4); capturar evidencia; declarar
PASS/PARTIAL/FAIL/BLOCKED **por caso** con `[E]`.

**NUNCA** (además de §1.3): no es admin del Worker ni orquestador ni Rick; no abre gates; no
escribe Notion/Publicaciones; no toca n8n; no ejecuta smokes admin (`smoke-gd52-oauth.sh` etc.
— los cita como escalación); no maneja tokens/secretos; no publica ni envía la frase-gate
"ok publica" — jamás, ningún pack puede autorizárselo. Si algún día hace falta ejercitar la
frase-gate, la envía **David en persona** con un candidato desechable designado por él
(decisión y GO suyos, fuera de este diseño, coherente con §3.1 y §4).

### 2.2 Superficies (con frontera usuario/admin explícita)

| Superficie | Rol usuario (tester) | Rol admin (fuera del tester) |
|------------|----------------------|------------------------------|
| Telegram — bot de Rick (OpenClaw, polling) | ✅ conversar como David (web.telegram.org / Desktop con la sesión de David) | config `dm_policy`, journalctl, reinicios |
| Telegram — bot B1/B3 TEST (webhook n8n) | ✅ solo sondas *negativas* sintácticas (ver §3.1 fail-closed y §4 P1b, requiere GO): texto no-matching → esperar "formato no reconocido". El happy path "ok publica <id>" **queda fuera por defecto** — es la frase-gate de David (anti-patrón 4) | importar/activar workflows, ver Executions, credenciales de bots |
| Notion | ✅ lectura (MCP read o browser): estados, gates en false, campos del contrato, comentarios; ✅ cronometrar apariciones | cualquier write (Worker); cambios de schema (solo David) |
| Linear | ✅ lectura como David: contraste de sondas R4/R13 (¿existe el proyecto/issue que Rick cita?) | crear/editar issues, updates, estados |
| RRSS públicas (LinkedIn/X de Umbral) | ✅ lectura pública, solo para verificar **no-autopublish** (Fila I=B) | nada — no existe superficie admin legítima aquí (el post RRSS es manual de David) |
| Google Calendar | ✅ leer calendar UI de David y contrastar con lo que Rick afirma | rotación OAuth, scopes, env VPS |
| n8n UI | ❌ — es superficie admin por diseño (127.0.0.1 + túnel SSH + login owner). El tester no la mira | Executions, publish de versiones |
| Worker / VPS / health endpoints | ❌ el tester jamás llama al Worker ni entra por SSH | operador de contraste (lane separado) |
| M365 | ❌ default fuera de alcance (sin dependencia explícita en el flujo editorial norte) | — |

**Dos lanes, un contraste**: el diseño separa (a) el **tester usuario** (superficies ✅ de
arriba) y (b) el **operador de contraste** (Claude VPS por Remote-SSH, superficies admin),
que solo actúa *después* del REPORT del tester para explicar discrepancias (¿poller caído?
¿auth vencida? ¿código stale?). Nunca el mismo actor en el mismo pack — así el resultado del
tester es genuinamente "lo que viviría David".

### 2.3 Identidad y sesión (checkpoints humanos)

- Login de web.telegram.org (QR/2FA), Notion y Google del lado usuario = **David, manual, una
  vez** por entorno de tester; la sesión persiste vía patrón `storageState`/persistent context
  (reference-e2e-reuse principio 4; plan browser doc 64 §4.2). El agente nunca ve ni pega
  credenciales; expiración de sesión → pausa + aviso a David (política CAPTCHA/sesión del plan
  browser §9).
- La allowlist de B1 (chat/user ID de David) hace que operar "desde la cuenta de David" no sea
  un truco sino **la única forma válida** de ejercitar el borde — coherente con el rol.
- Nota de plataforma: usar la sesión de David como *cliente* Telegram no colisiona con el
  polling del bot en VPS (el 409 es entre instancias *bot*, no entre clientes).

### 2.4 Criterios de evidencia `[E]` del tester

Hereda el contrato de cursor-orchestrator y lo especializa:

- **Transcript verbatim** de la conversación Telegram (texto pegado + screenshot), con
  timestamp local y ventana de espera aplicada. Sin transcript → sin PASS.
- **Lecturas Notion**: URL de página/fila + campos observados literales + timestamp. Nada de
  "se ve bien": valores exactos (`Estado=Borrador`, `aprobado_contenido=false`…).
- **Contraste de fuentes**: captura del calendar UI / página fuente + la afirmación de Rick,
  lado a lado, con delta explícito.
- **Ventanas de espera pre-declaradas**, con la superficie correcta para cada cadencia:
  el chat Telegram de Rick es polling getUpdates del bot (entrega en segundos) — su ventana
  (propuesta: 3 min) es **decisión de diseño conservadora** que cubre latencia LLM/tools, no
  deriva de ningún poller; la cadencia de 60s es del **Notion poller** (Control Room,
  docs/rick-estado-y-capacidades) y aplica solo a efectos que cruzan Notion (comentarios,
  Control Room): ≥2 ciclos antes de FAIL; efectos vía supervisor hasta 5 min; dashboard hasta
  15 min. Cada caso declara su timeout antes de correr (anti-flaky).
- **Doble corrida** para FAIL intermitente: 1 fallo aislado = posible flaky; 2/2 = defecto
  (patrón chat-regression-loop).
- **Sin secretos/PII** en reportes; screenshots sensibles fuera de git con referencia.
- Veredictos por caso: `PASS | PARTIAL | FAIL | BLOCKED` + `[E]`; el REPORT del pack usa
  markers `USER_E2E_*` (propuestos en la tabla de §4) y nunca los `RICK_*` de runtime (esos
  son del lane operador) ni gates humanos.

---

## 3. F2 — Arquitectura del sistema de testing (diseño)

### 3.1 Flujo E2E típico

**Happy path (alineado al norte A-I, sin abrir gates):**

```text
1. [tester] sonda conversacional a Rick por Telegram (p.ej. pedir estado del pipeline
   editorial, pedir un resumen de candidatas, pedir estado de un proyecto)
2. [tester] cronometrar respuesta; evaluar contra oráculos SOUL (R9 honestidad, R18
   "verificado" con evidencia, español, sin razonamiento interno)
3. [tester] leer Notion: ¿lo que Rick afirma existe? ¿estados y gates coinciden?
   ¿campos del contrato presentes (arco narrativo, estructura de discurso, fuente=pieza)?
4. [tester] contrastar fuentes: calendar UI vs agenda que Rick reporta; URL de pieza
   citada vs contenido real
5. [tester] REPORT con tabla caso→veredicto + [E]
6. [coordinador/David] cierran gate del pack; discrepancias pasan al lane operador
```

**Fail-closed (el sistema debe negarse; el tester verifica la negativa):**

- Pedirle a Rick contenido publicado sin gates → esperar negativa/estado Borrador, gates false.
- (P1b, con GO) texto no-matching al bot B1 TEST → "formato no reconocido", y en Notion **nada
  cambió**.
- Verificar Fila I=B: tras un publish real (si alguna vez ocurre en ventana de observación),
  `listo_rrss=true` + `published_url` inyectado y **cero** post automático en LinkedIn/X.
- El caso límite "ok publica" real queda **excluido**: es la frase-gate de David. Si un pack
  futuro necesita ejercitarla, la envía David en persona con candidato desechable designado
  (decisión y GO suyos, fuera de este diseño).

### 3.2 Sondas de frescura (Rick dijo X vs fuentes muestran Y) — sin sustituir al runtime

Diseño de familia de sondas (se ejecutan en P3, no ahora):

| Sonda | Pregunta a Rick | Fuente de contraste | Señal |
|-------|-----------------|---------------------|-------|
| Agenda hoy/semana | "¿qué tengo agendado hoy/esta semana?" | calendar UI del primary de David | eventos faltantes/sobrantes/desfasados; **eventos que David no tiene = bug de identidad** (`primary` de Rick, docs/35 L94-95) |
| Evento fresco | David crea un evento trivial en calendar UI (acción de usuario real, suya) → minutos después el tester pregunta | calendar UI | mide frescura + auth viva; si auth caducó: documentar por fin el síntoma lado-usuario (error explícito vs silencio vs dato stale — hoy indocumentado) |
| Estado editorial | "¿cómo va el pipeline editorial / qué candidatas hay?" | Notion Publicaciones/Shortlist por lectura | drift entre lo narrado y las filas/estados reales |
| Proyecto activo | "¿en qué quedó <proyecto>?" | Notion proyecto + Linear (lectura) | R4/R13/R14 SOUL: trazabilidad real vs relato |
| Silencio | mensaje simple a Rick por Telegram y cronometrar | ventana de diseño §2.4 (Telegram ~3 min; para efectos vía Notion, ≥2 ciclos del poller de 60s) | exceder la ventana declarada de forma reproducible (doble corrida) = candidato a fallo silencioso (cf. SEV-1 2026-05-05, lado Notion); el lane operador triangula causa — no confundir con latencia LLM normal |

El tester **mide y reporta**; jamás "arregla" (no reinicia, no rota tokens, no toca env).

### 3.3 Dónde vive cada cosa

- **Playbook operativo del tester** (casos, oráculos, ventanas, plantilla de REPORT):
  `docs/ops/` de este repo — siguiente doc del roadmap (P0 lo instancia como
  `user-e2e-tester-playbook-<fecha>.md`). Es un runbook, no una skill: primero tiene que
  sobrevivir al contacto con la realidad.
- **Config/estado de sesión browser del tester**: fuera de git (perfil persistente local /
  storageState). Ningún artefacto con cookies/tokens entra al repo.
- **Qué quedaría para una skill FUTURA** (solo propuesta, ver §5): la *fachada* reutilizable —
  persona, fronteras, oráculos genéricos, formato de REPORT — una vez validada por ≥1 corrida
  real. La suite concreta de casos vive siempre en docs (cambia con el sistema).

### 3.4 Decisión documentada: experiencia primero → skill después

Criterios de GO para capitalizar en skill (todos, no alguno):

1. ≥1 corrida real completa del roadmap P0→P3 con REPORTs archivados en `docs/ops/` (evidencia,
   no memoria).
2. Los oráculos demostraron discriminar: al menos un hallazgo real (bug, drift o frescura) y al
   menos un PASS legítimo — una suite que todo lo aprueba o todo lo reprueba no se capitaliza.
3. Fronteras del rol estables tras la experiencia (ninguna violación de §1.3 ni ampliación
   improvisada de superficies durante las corridas).
4. Decisión crear-vs-actualizar tomada con la tabla de §5.
5. GO explícito de David (la capitalización pasa por `skills-capitalize`, que ya exige leer el
   canónico y clasificar solape antes de escribir).

Política de datos de prueba (pendiente de David en P1): las sondas de este diseño son
conversacionales/lectura y no crean filas; si una sonda futura indujera a Rick a crear
contenido (p.ej. candidata), el pack lo pide con GO previo, convención de nombre visible
(prefijo tipo `SMOKE-`) y limpieza a cargo del Worker/Rick — nunca del tester.

---

## 4. F3 — Roadmap de packs orquestables (post-GO, un gate por pack)

Formato: paquetes PKG estándar (meta block + ACK + REPORT), secuenciales, WIP=1.
Ningún pack se emite sin GO de David sobre este plan.

| Pack | Contenido | Ejecuta | David hace | Gate único |
|------|-----------|---------|------------|------------|
| **P0 — Smoke de lectura y precondiciones** | Confirmar estado real hoy: leer Publicaciones/Shortlist (¿existe la DB?), leer Control Room, verificar que el contrato de campos coincide con lo vivo; registrar en el playbook el estado B1/B3 documentado (**ACTIVO con bot TEST desde 2026-07-25**, `infra/n8n/README.md` — solo David confirma si el estado vivo cambió desde entonces); decidir herramienta de browser del tester (§6, pregunta 5); escribir el playbook v0 con casos+oráculos+ventanas | Claude local (MCP Notion lectura) | Confirmar handle del bot B1 TEST (el de Rick ya está documentado: `@Rick_lot_bot`) y que B1/B3 siguen como documenta el repo | `USER_E2E_P0_READ_PASS` |
| **P1 — Sondas Telegram a Rick** | Suite congelada de sondas conversacionales (SOUL R9/R13/R14/R18/R21, silencio, honestidad ante tool errors); transcripts verbatim; ventanas 60s×2 | Claude local con browser sobre web.telegram.org (sesión de David) | Login QR una vez; decidir política de datos de prueba | `USER_E2E_P1_TELEGRAM_PASS` |
| **P1b (opcional, GO aparte) — Sonda negativa B1 TEST** | Solo caso negativo sintáctico ("formato no reconocido"); verificación de no-efecto por lectura Notion | ídem P1 | GO explícito (toca un borde n8n activo); confirmar bot TEST | `USER_E2E_P1B_B1_NEG_PASS` |
| **P2 — Verificación Notion** | Contrastar cada afirmación de Rick de P1 contra filas/estados/gates reales; checklist del contrato norte §5/§6 por lectura; UX governance (sin trace_id, sin acuses vacíos) | Claude local (MCP lectura) | — | `USER_E2E_P2_NOTION_VERIFY_PASS` |
| **P3 — Contraste de fuentes** | Sondas de frescura §3.2 (calendar UI, piezas fuente); documentar el síntoma lado-usuario de auth rota si aparece | Claude local browser; evento fresco lo crea David | Crear 1 evento trivial; sesión Google ya logueada | `USER_E2E_P3_FRESHNESS_PASS` |
| **P4 — Retro + decisión skill** | Consolidar REPORTs, evaluar criterios §3.4, proponer crear-vs-actualizar (§5); si GO → `skills-capitalize` | Claude local | Decisión binaria crear/actualizar | `USER_E2E_P4_DECISION_PASS` (gate de decisión: su `[E]` son los REPORTs consolidados) |

**Lane operador (paralelo, packs propios, nunca mezclado):** Claude VPS por Remote-SSH
triangula discrepancias de P1-P3 (poller, auth lifecycle, código stale, Executions n8n).
Insumo: informe sys-diag cuando aterrice.

**Fuera de alcance explícito de todo el roadmap:** M365; publicar de verdad; ejercitar
"ok publica" (frase-gate de David); activar flags de poller o workflows; crear la DB Shortlist
(schema = solo David, P1 editorial pendiente); tocar el n8n Cloud sandbox; QA del producto
Umbral Bot (otra skill, otro scope); reimplementar lo ya cubierto por el smoke P3 dry-run
(lógica interna de handlers).

---

## 5. Skill: no ahora

**Decisión de esta etapa: no se crea ni actualiza ninguna skill.** El playbook nace y madura
en `docs/ops/`.

Cuándo conviene **crear** una skill nueva (`user-e2e-tester` o similar) — todos:
- Los criterios de GO de §3.4 se cumplieron.
- El rol se usó ≥2 veces con superficies distintas (p.ej. editorial y ops) — señal de que la
  fachada es reutilizable y no un runbook puntual.
- La frontera con `umbral-rick-runtime` quedó nítida: rick-runtime gobierna *operar* el runtime;
  la nueva skill gobernaría *vivirlo como usuario*. Si en la práctica ambos roles los ejerce el
  mismo actor en los mismos packs, la señal es actualizar, no crear.

Cuándo conviene **actualizar** una existente en su lugar:
- `umbral-rick-runtime`: si lo aprendido cabe como sección "verificación en rol usuario" +
  referencia (patrón ya usado: `references/reference-gates.md`). Es la opción por defecto si
  el tester queda acoplado al dominio Rick/editorial.
- `cursor-orchestrator` / `reference-e2e-reuse.md`: si lo aprendido es transversal
  (storageState Telegram, ventanas de espera, lane usuario vs operador) — una fila más en la
  tabla de reuse, no una skill.
- En ambos casos vía `skills-capitalize` (propose → GO → write), y la evaluación de la skill
  resultante puede usar `test-incognitas-plantadas` (método ya probado 2026-07-28).

Riesgo que esta sección previene: crear la skill *antes* de la experiencia produciría
exactamente el anti-patrón 2 (docs fingiendo capacidad) — una skill que describe un tester
que nunca corrió.

---

## 6. Preguntas abiertas para David (se resuelven en P0/P1, no bloquean este plan)

1. Handle del bot B1 TEST — no documentado en el repo (la credencial se nombra
   "Telegram Bot — Umbral Editorial (TEST)" pero no su @handle; el de Rick sí está
   documentado: `@Rick_lot_bot`, docs/ops/rick-voice-telegram-mvp-runbook.md).
2. Confirmar que B1/B3 siguen como documenta el repo (ACTIVOS con bot TEST desde 2026-07-25,
   `infra/n8n/README.md`) — confirmación de estado vivo, no conflicto documental.
3. Política de datos de prueba (§3.4) — única decisión de fondo.
4. ¿P1b (sonda negativa B1) entra en el primer ciclo o se difiere hasta migrar B1 a bot PROD?
5. Herramienta de browser del tester local (Claude in Chrome / Playwright local / otra) —
   se decide en P0, antes de P1; restricciones ya fijadas: sesión persistente tipo
   storageState, runner secuencial, logins solo humanos (§2.3).
