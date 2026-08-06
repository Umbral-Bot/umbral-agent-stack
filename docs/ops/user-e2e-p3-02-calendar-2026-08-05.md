# P3-02 — re-corrida de la sonda de calendar (2026-08-05)

> Status: **BLOCKED.** No es un fallo de la sonda ni del calendario: **el turno
> interactivo de Rick está caído** por expiración del login de modelo en el gateway.
> La sonda no llegó a ejecutarse; el discriminador de frescura es inalcanzable
> mientras Rick no pueda responder nada.
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §6 P3-02, §8 evidencia.
> Pack: PKG-USER-E2E-P3-02 (re-emisión) · rama `claude/pkg-user-e2e-p3-02-20260804`
> · base `ddfd4201`.
> **Nota de privacidad**: repo público. Quedan fuera nombres de terceros, correos de
> invitados, enlaces de reunión y cualquier valor de credencial. Se citan **nombres**
> de variables y comandos (no sus valores) porque son parte del síntoma.

## 1. Titular

La corrida anterior (2026-08-04, `user-e2e-p3-02-freshness-2026-08-04.md`, PR #580
mergeado) cerró la sub-sonda en PASS `B_PRIMARY_ONLY`. Esta re-corrida **no reproduce
aquel resultado y tampoco lo contradice**: no pudo medir nada, porque hoy hay **dos
fallos de autenticación independientes**, y el segundo impide toda interacción.

| # | Fallo | Superficie donde se observa | Efecto | Calidad de la evidencia |
|---|---|---|---|---|
| 1 | Lectura de Calendar caída — **causa declarada por Rick**: auth ausente/expirada | briefing automático 07:31 | el briefing sale **sin agenda** | **débil**: autodescripción (§1.1) |
| 2 | **Login de modelo expirado en el gateway** (proveedor `openai`) | turno interactivo, 22:53–23:01 | **cualquier** mensaje de texto libre devuelve error; 6/6 intentos | **fuerte**: error de sistema (§1.1) |

El fallo 2 es el bloqueante. El fallo 1 es, por sí solo, una **regresión** respecto de
ayer (§3).

### 1.1 Los dos fallos NO tienen el mismo respaldo probatorio

Distinción que este doc no puede difuminar, porque la regla de la casa es que **lo que
Rick diga de sí mismo nunca prueba mecanismo**:

- **Fallo 2 está probado.** El texto de las 22:59 es un **error de sistema**
  —plantilla fija, con remediación de CLI— y por su propia naturaleza ("login de modelo
  expirado") se emite **antes** de que haya modelo que redacte nada. No es Rick
  hablando de Rick.
- **Fallo 1 NO está probado.** Que Calendar esté caído es un **efecto observado**
  (el briefing salió sin agenda: verificable). Pero la **causa** —"auth no configurada,
  `GOOGLE_CALENDAR_TOKEN` faltante"— sale de una frase que Rick compuso dentro de su
  propio briefing, en el mismo párrafo conversacional que su recomendación del día.
  Podría ser exacta o ser la excusa genérica que Rick da ante cualquier fallo de tool
  (timeout, id equivocado, cuota, otra excepción). **No se corroboró de forma
  independiente**, y el oráculo de §3.1 no sirve para eso (usa otra credencial, §3.1
  nota de método).

Consecuencia práctica: el punto 2 de §7 manda a restaurar la auth de Calendar **sobre
una hipótesis, no sobre un hecho**. El operador debería confirmar la causa en logs
antes de rotar nada.

| Gate | Resultado |
|---|---|
| `USER_E2E_P3_02_CALENDAR_PASS` (nombre fijado por el pack) | **BLOCKED** — capa `runtime/gateway del modelo`, no `preflight del modelo` ni `permiso cliente` (§4) |

**Nota de nomenclatura.** El marcador canónico de la suite P3 en el repo es
`USER_E2E_P3_FRESHNESS_PASS` (plan §8, playbook §8), y es el único registrado. El pack
de esta re-corrida fijó `USER_E2E_P3_02_CALENDAR_PASS`, que no existe en ese registro y
se usa aquí para responderle al orquestador en sus términos. Ambos apuntan al mismo
objeto: **quien consolide la suite debe buscar los dos**. Este BLOCKED no cierra ni
abre `USER_E2E_P3_FRESHNESS_PASS`; lo deja donde estaba.

## 2. Qué se ejecutó y qué no

| Paso de la misión | Estado |
|---|---|
| 1. Preflight canal Rick | **hecho — PASS**: sesión de Telegram viva, chat alcanzable, bot responde a comandos |
| 2. Checkpoint David (evento nuevo con dato sólo en el cuerpo) | **NO solicitado — deliberadamente** (§6) |
| 3. Preguntar a Rick agenda hoy/semana | **hecho — 5 envíos de agenda, todos fallidos** (§4) |
| 4. Oráculo Calendar UI vs Rick | **imposible**: no hay respuesta de Rick que contrastar |
| 5. Autodescripción no cierra PASS | **respetado en el gate**: el BLOCKED se apoya en un error de sistema y en una sonda de control, no en lo que Rick diga de sí mismo. **No** se extiende al fallo 1, cuya causa es autodescripción y está marcada como tal (§1.1) |
| 6. Documentar síntoma lado-usuario sin rotar OAuth | **hecho** (§4, §7); cero remediación ejecutada |

**Orden invertido a propósito.** El pack pone el checkpoint de David antes de la
pregunta. Se probó primero el canal porque hoy ya había **un** evento en el primary que
servía de oráculo, y porque si Rick no responde, crear un evento no cambia el
resultado. La inversión ahorró el checkpoint; se declara aquí, no se disuelve.

## 3. Evidencia `[E]` — fallo 1: briefing sin agenda (y regresión vs 2026-08-04)

Lo que esta sección prueba es que **el briefing salió sin agenda**. La *causa* que se
cita es la que Rick declara, y vale lo que vale una autodescripción (§1.1).

Superficie: **live**, `web.telegram.org`, chat con el bot de producción. Briefing
automático de hoy, 07:31. Extracto verbatim de las partes de agenda y alertas (la lista
de tareas Notion se omite: contiene nombres de terceros):

```
Briefing matutino — miércoles 5 de agosto

Agenda del día: no pude leer Google Calendar porque la integración no tiene auth
configurada (GOOGLE_CALENDAR_TOKEN o refresh credentials faltantes).

[...]

Alertas:

• Google Calendar no está operativo para Rick; el briefing queda incompleto por agenda.
• Hay tareas Notion antiguas en estado queued / running dentro de "Tareas — Umbral
Agent Stack", algunas desde mayo. Conviene auditar esa cola para separar pendientes
reales de residuos.

Recomendación:
Priorizar hoy una limpieza rápida: restaurar auth de Calendar y cerrar/actualizar las
tareas vencidas de WSP y Observatorio BIM, porque son las que más distorsionan el
estado operativo.
```

**Por qué esto es una regresión.** Durante 5 días (24-jul, 29-jul, 31-jul, 3-ago,
4-ago) el patrón fue: la herramienta interna falla por auth **pero** el briefing
igualmente lee la agenda por un *"conector de Google Calendar alternativo"*
(`user-e2e-p3-02-freshness-2026-08-04.md` §3.1). **Hoy ese respaldo no aparece**: no hay
mención de conector alternativo y el briefing sale explícitamente incompleto. Sea que el
respaldo se cayó o que nunca fue una segunda ruta real, **el efecto para David es
nuevo**: hoy su briefing no tiene agenda.

Esto tiene una consecuencia directa sobre la pregunta que §5 del acta del 4-ago dejó
abierta —en sus términos, si hay una sola familia de tools en el código pero dos caminos
efectivos en runtime, algo que «decidirlo requiere logs del runtime»—: hoy, con la ruta
interna caída,
**no hubo lectura**. Es un dato a favor de que no había dos rutas independientes — pero
sigue sin ser prueba de mecanismo, y sigue siendo del lane operador.

### 3.1 Oráculo Calendar de hoy (lectura, sin escritura)

Leído por conector MCP de Google Calendar sobre la cuenta de David, ventana
2026-08-05 00:00 → 2026-08-06 00:00 (−04):

| Calendario | `accessRole` | Eventos hoy |
|---|---|---|
| `david.a.moreira.m@gmail.com` (primary) | `owner` | **1** — `Coordinación David Moreira`, 12:00–12:30 (−04), **sin descripción** *(invitados y enlace de reunión no transcritos)* |
| `…@import.calendar.google.com` (el `Umbral BIM` del acta anterior; el conector lo expone con summary genérico `Calendar`, TZ `UTC`) | **`reader`** | 0 |

Dos cosas quedan corroboradas de paso:

1. **`accessRole: reader` confirma por API** lo que el 4-ago se probó sólo por UI: ese
   calendario es de **solo lectura**. Ya no depende de una lectura de pantalla.
2. El calendario importado **sí es enumerable** por un conector con la credencial
   adecuada. Eso **descarta una** explicación del punto ciego —"ese calendario es
   inalcanzable para cualquier cliente"— pero **no elige** entre las que quedan: puede
   ser qué calendarios pide Rick, o que su credencial no tenga acceso a ése en
   particular. Refuerza §7.2 del acta anterior (¿enumera `calendarList` o va directo a
   `primary`?) sin resolverlo: distinguirlas necesita logs del runtime.

**Nota de método:** este conector MCP **no es el de Rick**. Sirve como oráculo de "qué
eventos existen", no como prueba de qué puede leer Rick.

## 4. Evidencia `[E]` — fallo 2: el turno interactivo está caído

Superficie: **live**, mismo chat. Cronología completa, 2026-08-05 (−04). **Siete**
mensajes enviados en total: **seis de texto libre** (5 de agenda + 1 de control), que
fallaron **6/6**, y **un comando** (`/new`), que sí respondió — esa asimetría es
justamente el discriminador de §4.1:

| # | Hora | Enviado | Respuesta de Rick |
|---|---|---|---|
| 1 | 22:53 | `¿qué tengo agendado hoy? ¿y el resto de la semana?` | ⚠️ error genérico |
| 2 | 22:54 | `¿qué tengo agendado hoy?` | ⚠️ error genérico |
| 3 | 22:54 | `/new` | ✅ **`New session started.`** |
| 4 | 22:55 | `¿qué tengo agendado hoy?` | ⚠️ error genérico |
| 5 | 22:56 | `hola` *(sonda de control, sin tools)* | ⚠️ error genérico |
| 6 | 22:59 | `¿qué tengo agendado hoy?` | ⚠️ **error específico** (abajo) |
| 7 | 23:01 | `¿qué tengo agendado hoy?` | ⚠️ error genérico |

Error genérico, verbatim:

```
⚠️ Something went wrong while processing your request.
Please try again, or use /new to start a fresh session.
```

Error específico del intento de las 22:59, verbatim — **este es el que nombra la causa**:

```
⚠️ Model login expired on the gateway for openai. Send /login codex from a private chat
or Web UI session to pair a new Codex login, or re-auth with
openclaw models auth login --provider openai in a terminal, then try again.
```

### 4.1 Aislamiento de capa

La sonda que distingue una capa de las otras es el **mensaje de control `hola`**: no
toca Calendar, no toca Notion, no necesita ninguna tool.

| Capa | Estado | Prueba |
|---|---|---|
| Transporte Telegram | **OK** | los 6 mensajes salen con doble check; llegan respuestas |
| Handler de comandos del bot | **OK** | `/new` responde `New session started.` (intento 3) |
| Job programado (briefing) | **OK** a las 07:31 | produjo texto y **dice** haber leído Notion (no verificado contra la API: es autodescripción, §1.1). Lo verificable es que el turno se ejecutó y salió sin agenda |
| **Turno de agente / modelo** | **CAÍDO** | `hola` falla igual que las preguntas de agenda → **no es específico de Calendar** |
| Auth del proveedor de modelo en el gateway | **EXPIRADA** | el error de las 22:59 lo dice con nombre de proveedor |

Conclusión de capa: **`runtime/gateway del modelo`**. No es `preflight` (el canal está
vivo y el bot responde comandos), no es `permiso cliente` (el navegador ejecutó todo lo
pedido), y **no es la auth de Calendar** (el control sin tools falla igual).

### 4.2 Estabilidad del veredicto

Se reverificó en pasadas separadas —22:53, 22:54, 22:55, 22:56, 22:59, 23:01, con una
sesión fresca de por medio— por la regla de no declarar `N` con una sola lectura.
El fallo es **consistente 6/6 en ~8 minutos**. No es un blip.

### 4.3 Hallazgos de UX (lado usuario, sin entrar al runtime)

1. **El error accionable llega tarde y de forma intermitente.** 5 de 6 respuestas fueron
   `Something went wrong`, que no permite hacer nada; sólo el 6.º intento reveló la
   causa real. Un usuario que reintenta una vez y se rinde nunca ve el mensaje útil.
2. **`/new` "funciona" y no arregla nada.** El error genérico recomienda `/new`; `/new`
   responde OK; el siguiente mensaje vuelve a fallar. El remedio sugerido es un callejón
   sin salida que refuerza la impresión de que el problema es del usuario.
3. **Los errores están en inglés** en un canal donde Rick le habla a David en castellano,
   y **filtran interna** (gateway, nombre de proveedor, comandos de CLI) a la superficie
   de usuario. Es de la misma familia que UX-01 (stream `tool` crudo al canal) abierto
   desde P1.
4. **El briefing degradó en silencio para el usuario final**: dice que no pudo leer
   Calendar, pero igual se envía como "Briefing matutino" con su recomendación del día.
   La agenda simplemente no está.

## 5. Contraste contra el oráculo — no aplicable

La tabla A–E del pack (`A_SEES_UMBRAL` … `E_TOOL_ERROR_UX`) clasifica **el contenido de
una respuesta de Rick sobre la agenda**. Hoy no hay ninguna. Aplicar cualquier código
sería inventar. En particular:

- **No** se marca `C_STALE_OR_CIRCULAR`: no hubo respuesta que pudiera ser circular.
- **No** se marca `D_FABRICATED`: no hubo afirmación que contrastar.
- `E_TOOL_ERROR_UX` **no se usa como gate** aquí. Los errores de §4 no son una volcada
  cruda de tool dentro de una respuesta —que es lo que ese código describe— sino la
  ausencia total de turno. Se registran como hallazgos de UX (§4.3), no como código de
  la tabla.

El gate queda **BLOCKED**, no `N`: no se midió y falló, no se pudo medir.

## 6. Por qué no se pidió el checkpoint a David

El pack pide que David cree un evento nuevo con un dato sólo en el cuerpo. **No se
solicitó**, y la razón es de diseño de prueba, no de comodidad: con el turno interactivo
caído, Rick no puede responder ni a `hola`. Un evento nuevo no cambiaría el resultado —
se gastaría una acción de David para volver a obtener el mismo error.

El checkpoint queda **pendiente y sin consumir**, listo para dispararse en cuanto el
fallo 2 esté resuelto. Sigue vigente la mecánica que el playbook §6 ya registra: **lo
crea David** en el primary, con el dato discriminante **sólo en el cuerpo**, y el tester
pregunta ≥5 min después.

## 7. Pendientes para el lane operador (NO ejecutados aquí)

Ninguna de estas acciones se ejecutó: el pack prohíbe SSH/VPS/n8n y rotar OAuth, y la
remediación que el propio error propone es exactamente eso.

1. **Restaurar el login de modelo en el gateway** (proveedor `openai`/Codex). Es el
   bloqueante único de esta sonda. El error sugiere dos vías —`/login codex` desde un
   chat privado o Web UI, o `openclaw models auth login --provider openai` en terminal—;
   cuál corresponde es decisión del operador.
2. **Confirmar en logs por qué no se leyó Calendar** (fallo 1) **antes** de rotar nada:
   la causa "auth faltante" la declara Rick, no está corroborada (§1.1). Si se confirma,
   restaurarla. Se **presume** independiente del fallo 1 al 2 —son subsistemas
   distintos: OAuth de Google vs login de proveedor en el gateway— pero eso es
   inferencia, no contrafactual probado: no se arregló ninguno para observar el efecto
   sobre el otro.
3. **Averiguar por qué desapareció el "conector alternativo"** que sostuvo la lectura de
   agenda 5 días seguidos (§3). Si nunca fue una ruta independiente, la conclusión de
   P3-01 §4.1 ("no hay una segunda vía") queda reforzada y hay que corregir el texto de
   los briefings, que lo anuncian como si existiera.
4. **Alcance de calendarios** (heredado, mejor acotado): §3.1 prueba que el calendario
   importado es enumerable por API. Queda decidir si el briefing debe pedir
   `calendarList` completo o quedarse en `primary` por diseño — decisión de producto.
5. **Monitoreo de expiración**: hoy dos credenciales distintas expiraron y **David se
   entera usando el producto**, no por una alerta. Vale evaluar un chequeo previo al
   briefing que avise antes de degradar.
6. UX §4.3 (1–4) y UX-01 siguen abiertos.

## 8. Higiene y limpieza

- **Cero escrituras** en Calendar, Notion, n8n, Worker o VPS. Cero gates humanos. Cero
  publicaciones. La única acción saliente fueron los 7 mensajes de §4 al bot de David.
- El evento `E2E-P3-02-20260804-1103` de la corrida anterior era del 2026-08-04 y no
  aparece en la ventana de hoy; su limpieza sigue siendo decisión de David
  (`user-e2e-p3-02-freshness-2026-08-04.md` §8).
- **Aviso de seguridad de Telegram, no accionado.** La portada de Telegram Web mostraba
  una alerta de nuevo inicio de sesión en la cuenta de David, con los dos botones de
  confirmación/negación. *(Texto y huella del login —navegador, versión, ubicación— no
  transcritos: es la clase de dato que la disciplina de redacción del repo público
  excluye.)*
  **No se pulsó ninguno**: es una decisión de seguridad de la cuenta de David. Lo más
  probable es que corresponda a esta misma sesión de navegador, pero confirmarlo o
  negarlo le toca a él.
