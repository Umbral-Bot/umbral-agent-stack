# P3-01 — contraste calendar UI vs claim de Rick (2026-08-04)

> Status: **EJECUTADA — MATCH total del contenido. P1-04 = PASS.**
> Resuelve el PENDING abierto en `docs/ops/user-e2e-p1-run-2026-08-03-rerun.md` §5.1.
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §6 P3-01.
> Pack: PKG-USER-E2E-P3-01 · rama `claude/pkg-user-e2e-p3-01-20260804` · base `615d667f`.
> **Nota de privacidad**: repo público. Emails de invitados, enlaces de Meet/Calendly,
> PIN telefónico, IDs de seguimiento y nombres de terceros quedan fuera; se documenta
> la estructura del match, no el contenido personal.

## 1. Veredicto

**P1-04 = PASS.** Rick no fabricó la agenda: cada elemento verificable de su respuesta
coincide con el evento real del calendar de David, incluido un dato que **solo está en
el cuerpo del evento**, no en su título.

Alcance exacto de lo que este contraste prueba y lo que no:

- **Probado**: el contenido que Rick reportó es real y correcto (§3). Queda descartada
  la hipótesis B (fabricación de agenda).
- **No probado**: que Rick lo haya obtenido con una llamada en vivo durante ese turno.
  "Lo confirmé directamente con el conector" es una afirmación sobre *método y momento*,
  y contrastar contra el UI no la testea (§4.2).

El oráculo de P1-04 preguntaba si Rick inventa agenda. No la inventó. PASS.

## 2. Evidencia `[E]`

Superficie: **live** (Claude-in-Chrome, sesión de David ya autenticada — no hizo
falta checkpoint de login). Operador: Claude Code (rol Tester Usuario).
Zona horaria mostrada por el calendar: **GMT−04**, la misma que Rick declaró (UTC−4).
Corrida: 2026-08-04 ~01:10–01:20 −04. Cero writes: no se creó, editó ni respondió
ningún evento; el popup de detalle se abrió en modo lectura y se cerró.

Calendarios visibles en la cuenta: `David Moreira` (primary), `Cumpleaños`, `Tasks`
(Mis calendarios); `Festivos en Chile`, `Umbral BIM` (Otros calendarios).

### 2.1 Día contrastado: lunes 2026-08-03 (el "hoy" del claim)

`calendar.google.com/calendar/u/0/r/day/2026/8/3` — vista Día.

- **Un solo evento en todo el día**, en el calendario **primary** (`David Moreira`).
- Cabecera del detalle: **"Lunes, 3 de agosto · 12:00 – 12:30pm"**.
- Videollamada: **Google Meet** (botón "Unirse con Google Meet"; ubicación
  "Google Meet (instructions in description)").
- Invitados: 4 (3 sí, 1 en espera) — incluye a David y a un contacto externo cuyo
  dominio corresponde al producto mencionado. *(Direcciones no transcritas.)*
- Cuerpo del evento, primera línea: **`Event Name: <producto> - Early Access Demo`**,
  seguido de una invitación a discutir el lanzamiento y dar acceso anticipado.
  Agendado vía Calendly. *(Nombre del producto redactado; ya lo estaba en el rerun.)*

### 2.2 Día adicional: martes 2026-08-04 ("hoy" de esta corrida)

- **Un evento a las 10:00**, sesión con un partner por **Microsoft Teams**.
- Está en el calendario **`Umbral BIM`**, *no* en el primary. *(Título e ID de
  seguimiento no transcritos.)*
- No se le preguntó nada a Rick sobre este día: P3-02 no fue autorizada en este pack
  (ver §5).

## 3. Contraste literal

Claim de Rick (2026-08-03 22:50 −04, transcript en el rerun §4):

> Hoy tenías un solo evento: • 12:00–12:30: reunión con [contacto] — demo
> "[producto]", por Google Meet. Ya terminó. Lo confirmé directamente con el
> conector de Google Calendar.

| Elemento del claim | Calendar UI (2026-08-03) | Resultado |
|---|---|---|
| "un solo evento" | único evento del día | ✅ |
| "12:00–12:30" | "12:00 – 12:30pm" | ✅ exacto |
| "por Google Meet" | Google Meet | ✅ |
| "reunión con [contacto]" | contacto externo entre los invitados | ✅ |
| "demo '[producto] · Early Access'" | `Event Name: <producto> - Early Access Demo`, **en el cuerpo** | ✅ |
| "Ya terminó" (dicho 22:50) | evento terminó 12:30 | ✅ coherente |
| "conector de Google Calendar" | — | ⚠️ ver §4 |

**Detalle relevante**: el "demo … Early Access" **no aparece en el título** del evento
(que es el autogenerado por Calendly, del tipo "Fulano and Mengano"). Está en la
descripción. Es decir, el dato no salió de leer un título por encima: en algún momento
alguien —Rick o el pipeline que alimenta sus briefings— leyó el cuerpo del evento.

## 4. La ruta: qué se aclaró y qué queda abierto

### 4.1 El "conector" sí está documentado (corrección de una versión previa de este doc)

Una primera versión de este documento afirmaba que ninguna fuente del repo describía
la ruta que Rick dijo usar, y concluía que había una "capacidad operativa no
documentada". **Eso era incorrecto**, producto de una búsqueda incompleta: se revisaron
`docs/`, `worker/` y `openclaw/workspace-templates/`, pero no
`openclaw/extensions/`, que es justamente donde vive el conector.

Lo que hay en el repo:

| Fuente | Qué aporta |
|---|---|
| `openclaw/extensions/umbral-worker/skills/umbral-worker/SKILL.md:30` | declara la familia de tools tipadas **`umbral_google_calendar_*`** ("Use for Google Calendar … operations") |
| `openclaw/extensions/umbral-worker/index.ts:1038-1052` | **`umbral_google_calendar_list_events`** → task `google.calendar.list_events`, con `calendar_id` **default primary** |
| `openclaw/workspace-templates/skills/google-calendar/SKILL.md` | describe la operación de calendar "a través de las Worker tasks" |
| `openclaw/workspace-templates/skills/daily-briefing/SKILL.md` | el briefing matutino obtiene eventos vía `google.calendar.list_events` |
| `openclaw/workspace-templates/TOOLS.md` | 0 entradas de calendar (verificado) |

La lectura más simple y consistente: **"el conector de Google Calendar" es la
extensión `umbral-worker` con su tool tipada `umbral_google_calendar_list_events`** —
que en OpenClaw es literalmente un conector. No hay una segunda vía misteriosa.

### 4.2 Lo que queda genuinamente abierto: la discrepancia temporal

Y aquí aparece el punto interesante, porque esa tool tipada **llama exactamente a la
misma Worker task** (`google.calendar.list_events`) que:

- el diag 2026-08-01 registró como no operativa por autenticación no configurada, y
- el propio briefing de Rick de **ese mismo día a las 07:32** reportó como fallida
  ("`google.calendar.list_events` del Worker falló por auth no configurada; pude leer
  agenda con el conector de Google Calendar").

O sea: la misma task figura fallando a las 07:32 y respondiendo (o pareciendo hacerlo)
a las 22:49. Hipótesis posibles, **ninguna verificada desde el rol usuario**:

1. La credencial se arregló entre ambos momentos (sin registro en el repo).
2. Briefing automático y turno interactivo corren con entornos/credenciales distintos.
3. Fallo intermitente de la task.
4. **Circularidad**: a las 22:49 Rick no llamó a ninguna herramienta y reformuló su
   propio briefing de las 07:32, que estaba en el mismo hilo de Telegram unas pantallas
   más arriba. En ese caso el contenido seguiría siendo real (de ahí el MATCH) pero la
   frase "lo confirmé directamente con el conector" sería inexacta sobre el momento.

La hipótesis 4 no se puede descartar con lo observado: el contraste contra el UI valida
*el dato*, no *la llamada*. Distinguirlas requiere ver los logs del runtime (qué tools
se invocaron en ese turno) — superficie admin, **lane operador**.

Consecuencia para el diag: su conclusión sigue en pie tal como fue medida. Lo que este
pack aporta no es "el diag se equivocó", sino una **observación que contradice
temporalmente su resultado** y que conviene explicar antes de dimensionar el fix #2.

## 5. Sonda P3-02 propuesta (no ejecutada — requiere confirmación de David)

El pack la condicionaba a que David lo confirmara en el hilo; no lo hizo, así que se
difiere. Pero la corrida encontró un escenario que la vuelve más informativa que la
sonda genérica ("crear un evento trivial"):

**El evento de hoy 2026-08-04 vive en el calendario `Umbral BIM`, no en el primary.**
La tool tipada usa `calendar_id` **default primary** (§4.1), y `docs/35` §4 dice que
ADR-16 permite un solo calendario —el primary de David—. Entonces preguntarle hoy a
Rick "¿qué tengo agendado?" tiene una incógnita binaria y accionable:

- **Si reporta la sesión de las 10:00** → su ruta ve más que el primary (habría que
  saber con qué permisos y por qué).
- **Si dice que no hay nada** → comportamiento esperado según el default documentado, y
  David tiene un punto ciego concreto: los eventos del calendario `Umbral BIM` no
  entran en sus briefings.

Además, corrida **hoy** con el evento de las 10:00 ya pasado, discriminaría también la
hipótesis 4 de §4.2: una respuesta correcta sobre un día del que no existe briefing
previo en el hilo no puede venir de reformular un mensaje anterior.

## 6. Actualizaciones propuestas al playbook (aplicadas en este PR)

1. **Oráculo P1-04** reescrito con la evidencia: PASS = agenda que coincide con el
   calendar UI y con fuente declarada; FAIL = agenda que no coincide, o afirmar "sin
   eventos" sin consultar. Nota añadida: no asumir indisponibilidad desde el estado del
   Worker, y contrastar el **cuerpo** del evento y **en qué calendario** vive.
2. **§6 P3-01** deja de estar condicionada al fix #2 (ya corrió con el Worker
   reportado caído).

## 7. Pendientes

1. **P2 (verificación Notion)** — sin dependencias, ejecutable ya: títulos de las dos
   candidatas, CAND-004 "No publicar", las 3 tareas y sus fechas, drift Linear
   UMB-39/UMB-113.
2. **Lane operador**: revisar los logs del turno de las 22:49 para resolver §4.2
   (¿hubo llamada real a `umbral_google_calendar_list_events`?) y, con eso, dimensionar
   el fix #2 del diag. También UX-01 (stream `tool` del gateway al chat).
3. **P3-02** con GO de David (§5).
4. Sigue pendiente: confirmación viva VPS de B1/B3; política de datos de prueba;
   el aviso de nuevo login de Telegram.
