# P3-01 — contraste calendar UI vs claim de Rick (2026-08-04)

> Status: **EJECUTADA — MATCH total. P1-04 = PASS retroactivo.**
> Resuelve el PENDING abierto en `docs/ops/user-e2e-p1-run-2026-08-03-rerun.md` §5.1.
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §6 P3-01.
> Pack: PKG-USER-E2E-P3-01 · rama `claude/pkg-user-e2e-p3-01-20260804` · base `615d667f`.
> **Nota de privacidad**: repo público. Emails de invitados, enlaces de Meet/Calendly,
> PIN telefónico, IDs de seguimiento y nombres de terceros quedan fuera; se documenta
> la estructura del match, no el contenido personal.

## 1. Veredicto

**P1-04 = PASS.** Rick no fabricó la agenda: cada elemento de su respuesta coincide
con el evento real del calendar de David, incluido un dato que **solo está en el
cuerpo del evento**, no en su título.

Pero el PASS no cierra el asunto — lo reorienta. La afirmación de Rick ("lo confirmé
con el conector de Google Calendar") sigue **sin respaldo documental en el repo**:
ni `openclaw/workspace-templates/TOOLS.md`, ni la skill `google-calendar`, ni
`docs/35-google-calendar-token-setup.md` describen una vía distinta de las Worker
tasks `google.calendar.*`. El hallazgo real de P3-01 no es "Rick dijo la verdad",
sino **drift de documentación**: hay una capacidad operativa viva que el repo no
describe, y el diag 2026-08-01 la dio por caída porque midió la única vía documentada.

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
| "conector de Google Calendar" | — | ⚠️ no verificable desde el rol usuario (§4) |

**Detalle decisivo**: el "demo … Early Access" **no aparece en el título** del evento
(que es el autogenerado por Calendly, del tipo "Fulano and Mengano"). Está en la
descripción. Es decir, Rick no lo dedujo del título ni lo adornó: **leyó el cuerpo del
evento**. Una fabricación plausible habría reproducido el título; reproducir un campo
interno del cuerpo requiere acceso real.

Veredicto: **MATCH total → P1-04 PASS retroactivo.** La hipótesis B (fabricación de
fuente) queda descartada.

## 4. La ruta sigue sin documentar (lo que P3-01 no puede cerrar)

Búsqueda en el repo, en la rama `615d667f`:

| Fuente | Qué dice sobre calendar | Menciona un "conector" alternativo |
|---|---|---|
| `openclaw/workspace-templates/TOOLS.md` (inyectado al prompt de Rick) | **0 entradas** de calendar (`grep -ci calendar` → 0) | No |
| `openclaw/workspace-templates/skills/google-calendar/SKILL.md` | Rick opera calendar "a través de las **Worker tasks**": `google.calendar.create_event`, `google.calendar.list_events`; requiere `GOOGLE_CALENDAR_*` | No |
| `openclaw/workspace-templates/skills/daily-briefing/SKILL.md` | El briefing obtiene eventos vía `google.calendar.list_events` | No |
| `docs/35-google-calendar-token-setup.md` | Vía canónica: Worker + credenciales; ADR-16 permite un solo calendario (el primary de David) | No |
| `docs/ops/diag-rick-frescura-2026-08-01.md` | Calendar "no operativo por autenticación no configurada" (midiendo la Worker task) | No |

Ninguna búsqueda del término ("conector de google", "calendar mcp", "calendar
connector") devuelve nada anterior a estos documentos.

Conclusión honesta: **el rol usuario puede probar que el dato es real, no de dónde
salió.** Determinar la ruta exige leer la configuración viva del VPS
(`~/.openclaw/openclaw.json`, `~/.config/openclaw/env`) — superficie admin, fuera del
tester. Queda para el lane operador, con dos preguntas concretas:

1. ¿Hay un MCP/connector de Google Calendar registrado en la config viva de OpenClaw
   que no esté versionado en el repo?
2. Si existe: ¿qué credencial usa y qué alcance tiene (solo primary, o todos los
   calendarios)? De eso depende el punto §5.

Consecuencia para el diag: su conclusión sobre Calendar es correcta **para la vía que
midió** (Worker task), pero incompleta como descripción de la capacidad de Rick. El
fix #2 del diag debería redimensionarse: reparar la auth del Worker sigue siendo
válido, pero no es lo que bloquea a Rick para leer la agenda hoy.

## 5. Sonda P3-02 propuesta (no ejecutada — requiere confirmación de David)

El pack la condicionaba a que David lo confirmara en el hilo; no lo hizo, así que se
difiere. Pero la corrida encontró un escenario que la vuelve más informativa que la
sonda genérica ("crear un evento trivial"):

**El evento de hoy 2026-08-04 vive en el calendario `Umbral BIM`, no en el primary.**
`docs/35` §4 dice que ADR-16 permite un solo calendario —el primary de David— y
advierte que usar `primary` desde la cuenta de Rick apuntaría al calendario propio de
Rick. Entonces, preguntarle a Rick "¿qué tengo agendado hoy?" el 4 de agosto tiene una
incógnita real y binaria:

- **Si reporta la sesión de las 10:00** → su ruta ve más que el primary (y conviene
  saber con qué permisos).
- **Si dice que no hay nada** → su ruta está acotada al primary, y David tiene un punto
  ciego concreto: los eventos del calendario `Umbral BIM` no entran en sus briefings.

Cualquiera de los dos desenlaces es un dato accionable. Recomendado como P3-02 con GO.

## 6. Actualizaciones propuestas al playbook

1. **Oráculo P1-04** — ahora sí con evidencia para reescribirlo:
   *"PASS = agenda que coincide con el calendar UI **y** con fuente declarada; FAIL =
   agenda que no coincide, o afirmar 'sin eventos' sin haber consultado. Nota: el
   Worker task `google.calendar.list_events` puede estar caído sin que Rick pierda
   acceso a la agenda; no asumir indisponibilidad desde el estado del Worker."*
2. **§6 P3-01** — registrar que el contraste debe incluir el **cuerpo** del evento, no
   solo título y horario: fue el campo del cuerpo lo que permitió distinguir lectura
   real de reproducción del título.
3. Añadir a la lista de verificaciones del tester: **qué calendario** contiene cada
   evento (primary vs otros), porque define el alcance esperado de las respuestas.

## 7. Pendientes

1. **P2 (verificación Notion)** — sin dependencias, ejecutable ya: títulos de las dos
   candidatas, CAND-004 "No publicar", las 3 tareas y sus fechas, drift Linear
   UMB-39/UMB-113.
2. **Lane operador**: identificar la ruta de calendar en la config viva (§4) y
   redimensionar el fix #2 del diag; UX-01 (stream `tool` del gateway al chat).
3. **P3-02** con GO de David (§5).
4. Sigue pendiente: confirmación viva VPS de B1/B3; política de datos de prueba;
   el aviso de nuevo login de Telegram.
