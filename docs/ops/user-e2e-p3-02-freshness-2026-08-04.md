# P3-02 — sonda de frescura y alcance del calendar de Rick (2026-08-04)

> Status: **EJECUTADA — `USER_E2E_P3_FRESHNESS_PASS` = PASS, código `B_PRIMARY_ONLY`.**
> Cierra la sonda que P3-01 §5 dejó propuesta y el criterio 1 PARCIAL de la retro P4 §3.
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §6 P3-02, §8 evidencia.
> Pack: PKG-USER-E2E-P3-02 · rama `claude/pkg-user-e2e-p3-02-20260804` · base `492aecc1`.
> **Nota de privacidad**: repo público. Quedan fuera IDs de seguimiento, URLs de
> suscripción con token, enlaces/ID/passcode de reuniones y nombres de terceros.

## 1. Titular y veredicto

Las dos preguntas que abría P3-01 §5 quedan respondidas, y en direcciones distintas:

- **Frescura: demostrada.** Rick reportó un evento creado 7 min 42 s antes de la
  pregunta, con su horario exacto **y su descripción textual** — un dato que nunca
  apareció en el chat. Eso no se puede reformular desde un briefing anterior: obliga a
  una lectura en vivo del cuerpo del evento. La **hipótesis 4 de P3-01 §4.2
  (circularidad) queda descartada para este turno.**
- **Alcance: confirmado el punto ciego.** El calendar UI tenía **3 eventos** hoy; Rick
  reportó **2**. El que falta es exactamente el que vive en el calendario
  **`Umbral BIM`**. Rick ve el primary y nada más.

Y aparece un hallazgo estructural que el pack no anticipaba: **el calendario
`Umbral BIM` no es un calendario de Google que David posea, sino una suscripción ICS
de solo lectura a un calendario publicado de Outlook/Office 365** (§2.3). Por eso fue
**imposible crear el evento fresco ahí**, como pedía el procedimiento §A.3 — no es una
cuestión de permisos mal configurados sino de la naturaleza del objeto. El diseño se
adaptó (§2.4) sin perder ninguno de los dos ejes de medición.

| Gate | Resultado |
|---|---|
| `USER_E2E_P3_FRESHNESS_PASS` | **PASS** — código `B_PRIMARY_ONLY`, sin `D`, sin `C`, sin `E` |

## 2. Evidencia `[E]` — fase A (oráculo Calendar UI)

Superficie: **live**, Claude-in-Chrome sobre el Chrome real de David, sesión ya
autenticada (sin checkpoint de login). Cuenta `david.a.moreira.m@gmail.com`,
zona horaria `America/Santiago` (**GMT−04**), literal leído del DOM de la app.
Operador: Claude Code, rol Tester Usuario.

### 2.1 Calendarios visibles

| Sección | Calendarios |
|---|---|
| Mis calendarios | **David Moreira** (primary), Cumpleaños, Tasks |
| Otros calendarios | Festivos en Chile, **Umbral BIM** |

En Configuración aparece además **Familia** (oculto en la grilla). `Tasks` es la capa
de tareas, no un calendario de eventos.

### 2.2 Inventario del día — martes 2026-08-04

Vista Día, `calendar.google.com/calendar/u/0/r/day/2026/8/4`. Encabezado accesible
literal antes de la sonda: *"martes, 4 de agosto de 2026, hoy, 2 eventos"*; tras crear
el evento fresco, 3.

| # | Título | Hora (−04) | Calendario | Un detalle del cuerpo |
|---|---|---|---|---|
| 1 | `Umbral BIM - Marketplace` | 10:00–11:00 | **David Moreira (primary)** | sin descripción, sin ubicación, sin invitados; recordatorio 30 min antes |
| 2 | `MPS session – Umbralbim – TrackingID#…` *(ID redactado)* | 10:00–11:00 | **Umbral BIM** | ubicación "Microsoft Teams Meeting"; cuerpo = datos de conexión Teams *(no transcritos)*; visibilidad "Público" |
| 3 | `E2E-P3-02-20260804-1103` | 13:00–13:30 | **David Moreira (primary)** | descripción: `PKG-USER-E2E-P3-02 freshness probe - no borrar hasta REPORT` |

Ojo con la ambigüedad de nombres: el evento **1** *se llama* "Umbral BIM - Marketplace"
pero **vive en el primary**; el evento **2** es el que vive en el **calendario**
`Umbral BIM`. Confundirlos invierte la conclusión.

### 2.3 Hallazgo bloqueante de §A.3: `Umbral BIM` es de solo lectura

El procedimiento pedía crear el evento fresco en `Umbral BIM`. No se pudo, y la causa
es estructural, no de configuración:

- En el editor completo de evento, el selector de calendario **no ofrece ninguna
  alternativa**: el árbol de accesibilidad expone `combobox "Calendar"` con un único
  valor (`David Moreira`) y ni el clic ni la tecla ↓ despliegan opciones. Cuando la
  cuenta tiene un solo calendario escribible, Google no ofrece destino alternativo.
- Configuración → `Umbral BIM` lo confirma literalmente:
  - **Configuración de permisos** → *"Cualquiera puede: No ver nada"* ·
    **"Puedes: Ver todos los detalles de los eventos"** → sin permiso de escritura.
  - **URL**: una suscripción ICS a un calendario **publicado de Outlook/Office 365**
    del dominio corporativo *(URL no transcrita: incluye el token de publicación)*.
  - El identificador del calendario termina en **`@import.calendar.google.com`** y el
    menú lateral ofrece *"Anular suscripción al calendario"* — es una importación por
    feed, no un calendario compartido de Google.

Consecuencia práctica: **nadie —ni el tester, ni David, ni Rick— puede escribir en
`Umbral BIM` desde la cuenta de Google.** Es un espejo de un calendario que vive en
M365. Esto reencuadra el punto ciego de P3-01 §5: no es solo el default
`calendar_id=primary` de la tool tipada; es que además ese calendario es un objeto
importado, con su propia zona horaria (UTC) y sin escritura.

### 2.4 Adaptación del diseño (declarada, no silenciosa)

Con la creación en `Umbral BIM` imposible, la sonda se reorganizó para conservar los
**dos** ejes que el pack quería medir, usando dos observables distintos:

| Eje | Cómo se midió |
|---|---|
| **Frescura** (¿lee en vivo o reformula el briefing?) | evento nuevo `E2E-P3-02-20260804-1103` creado en el **primary** —el único destino escribible— a las 11:05, es decir **después** del briefing de las 07:31 |
| **Alcance** (¿ve más que el primary?) | evento **ya existente** `MPS session…` que vive en `Umbral BIM` y ocurrió hoy 10:00–11:00 |

El eje de alcance no necesitaba un evento nuevo: bastaba con contrastar si Rick nombra
lo que ya está ahí. Ese es el ajuste que se propone incorporar al playbook (§6).

### 2.5 Cronología

| Marca | Hora local (−04) | Qué |
|---|---|---|
| — | 10:55–11:04 | inventario UI + verificación de permisos de `Umbral BIM` |
| **t0** | **11:05:27** | evento fresco guardado (toast "Evento guardado") |
| — | 11:06 | apertura del chat con Rick, **sin enviar nada**; se detecta briefing de agenda de hoy a las 07:31 → se activa la 2.ª pregunta del mismo turno |
| **t1** | **11:13:09** | sonda enviada (sello Telegram 11:13) |
| — | **11:14** | respuesta completa de Rick |

**Δ (t1 − t0) = 7 min 42 s** — cumple el mínimo de ≥5 min del procedimiento.
**Latencia de Rick ≈ 1 min**, holgadamente dentro de la ventana de 5 min del playbook §3.

## 3. Evidencia `[E]` — fase B (sonda a Rick)

Superficie: `web.telegram.org`, chat con **@Rick_lot_bot** (bot de producción; el bot
editorial TEST no se tocó). **Un solo mensaje enviado en toda la corrida.**

### 3.1 Contexto previo del hilo — briefing automático de hoy (07:31)

Relevante porque es el candidato natural a "reformulación circular". Extracto literal
de la parte de agenda y de la alerta técnica:

```
Briefing matutino — martes 4 de agosto

Agenda del día

• 10:00–11:00 — Umbral BIM - Marketplace.
[...]
Alertas

• Hay varias tareas antiguas aún en Pendiente; conviene cerrar, reprogramar o archivar
para limpiar foco.
• La herramienta interna umbral_google_calendar_list_events falló por auth de Google
Calendar no configurada; pude leer el evento usando el conector de Google Calendar
alternativo.
```

Dos cosas quedan registradas de aquí, ambas útiles para el lane operador:

1. **El briefing de las 07:31 ya omitía el evento de `Umbral BIM`** — el punto ciego no
   lo introdujo la sonda; es el comportamiento diario.
2. Rick distingue **dos rutas**: la herramienta interna
   `umbral_google_calendar_list_events` (que declara **fallida por auth**) y un
   *"conector de Google Calendar alternativo"* que sí funciona. Esa distinción se
   repite, con distintas palabras, en los briefings del 24-jul, 29-jul, 31-jul
   ("el worker OpenClaw de Google Calendar falló por auth, pero pude leer el calendario
   por el conector Google Calendar MCP") y 3-ago. **No es una frase suelta del turno de
   las 22:49 que P3-01 §4.2 dejó en duda: es un patrón sostenido de ≥6 días.**

### 3.2 Transcript verbatim de la sonda

**Tester → Rick** — 11:13

```
¿qué tengo agendado hoy? ¿y el evento E2E-P3-02-20260804-1103?
```

**Rick → Tester** — 11:14

```
Hoy tienes dos eventos:

• 10:00–11:00 — Umbral BIM - Marketplace (ya terminó).
• 13:00–13:30 — E2E-P3-02-20260804-1103.

El evento E2E sí existe. Su descripción dice: "PKG-USER-E2E-P3-02 freshness probe - no
borrar hasta REPORT". Por ahora, no hay que borrarlo.
```

No se enviaron más mensajes. No se declaró rol de tester. No se pidieron logs ni tools.
Un borrador residual quedó en el compositor por un reintento de tipeo y **se borró sin
enviarlo** (verificado: compositor vacío, un solo mensaje saliente en el hilo).

## 4. Contraste contra el oráculo

### 4.1 Evento por evento

| Evento del UI | Calendario | ¿Rick lo nombró? | Lectura |
|---|---|---|---|
| `Umbral BIM - Marketplace` 10:00–11:00 | primary | **Sí**, con horario exacto y "(ya terminó)" — correcto a las 11:14 | ✅ |
| `MPS session – Umbralbim – TrackingID#…` 10:00–11:00 | **Umbral BIM** | **No** | ⛔ punto ciego confirmado |
| `E2E-P3-02-20260804-1103` 13:00–13:30 | primary | **Sí**, horario exacto **+ descripción textual** | ✅ frescura probada |

Rick no nombró ningún evento inexistente: **cero fabricación**.

### 4.2 Tabla de códigos del pack

| Código | ¿Aplica? | Fundamento |
|---|---|---|
| `A_SEES_UMBRAL` | **No** (ver nota) | no mencionó el único evento que vive en `Umbral BIM` |
| `B_PRIMARY_ONLY` | **Sí** | listó exactamente los 2 eventos del primary y omitió el de `Umbral BIM`; coherente con el default `calendar_id=primary` de `umbral_google_calendar_list_events` (P3-01 §4.1) y con ADR-16 |
| `C_STALE_OR_CIRCULAR` | **No** | citó un evento y una descripción que no existían al momento del briefing de las 07:31 y que nunca estuvieron en el chat |
| `D_FABRICATED` | **No** | todo lo afirmado coincide con el UI |
| `E_TOOL_ERROR_UX` | **No en este turno** | ninguna volcada cruda de error; UX-01 sigue registrado por los turnos del 3-ago (22:54 y 22:59), no se reproduce aquí |

**Nota sobre la letra de la tabla.** Tal como estaba redactada, `A_SEES_UMBRAL` decía
"menciona el evento fresco `E2E-P3-02-…`", porque el pack asumía que ese evento viviría
en `Umbral BIM`. Como ese calendario resultó no escribible (§2.3), el evento fresco
quedó en el primary y **mencionarlo ya no prueba alcance ampliado**. Leída al pie de la
letra la fila daría `A`; leída por su intención —*"¿ve más que primary?"*— da `B`. Este
doc clasifica por intención y deja la lectura literal explícita para que nadie tenga
que adivinar cuál se aplicó.

### 4.3 Aplicación del gate

`USER_E2E_P3_FRESHNESS_PASS` = PASS si (`A` o `B`) y no `D`.
Resultado: **`B` y no `D` → PASS.** `C` queda descartado por evidencia positiva, no por
ausencia de prueba: la descripción textual del evento es el discriminador duro.

## 5. Relación con P3-01 §5 y con la retro P4

| Pregunta abierta | Estado tras esta corrida |
|---|---|
| P3-01 §5 — *"¿si reporta la sesión de las 10:00, ve más que el primary?"* | **Respondida: no la reporta.** Rick es ciego al calendario `Umbral BIM`; David tiene un punto ciego concreto y diario en sus briefings |
| P3-01 §4.2 hipótesis 4 — *circularidad (reformular el briefing previo)* | **Descartada para este turno.** La descripción del evento fresco no existía en el hilo; sólo se obtiene leyendo el cuerpo del evento en vivo |
| P3-01 §4.2 hipótesis 1/2/3 — *credencial arreglada / entornos distintos / intermitencia* | **Sigue abierta, pero mejor acotada**: el briefing de hoy 07:31 vuelve a declarar `umbral_google_calendar_list_events` fallida por auth **y** vuelve a leer la agenda por el "conector alternativo". Convivencia sostenida de las dos rutas, no un evento aislado |
| P4 §3 criterio 1 (PARCIAL: 1 de 4 sondas P3) | **Avanza a 2 de 4.** Quedan P3-03 (pieza fuente) y P3-04 (no-autopublish RRSS) |

Lectura de fondo para el sistema, no sólo para el test: **el fix #2 del diag
(credencial Calendar del Worker) no le devolvería a David el evento de `Umbral BIM`.**
Aunque la tool tipada vuelva a funcionar, su `calendar_id` por defecto es `primary`;
el calendario `Umbral BIM` es una suscripción importada aparte. Son dos problemas
distintos y sólo uno de ellos es de autenticación.

## 6. Actualización propuesta al playbook §6 P3-02 (aplicada en este PR)

1. La fila P3-02 pasa de "David crea 1 evento trivial" a la mecánica realmente
   ejecutable: **el evento fresco va al primary** —único calendario escribible— y el
   **alcance se discrimina con eventos que ya viven** en el calendario no-primary.
2. Se registra que **`Umbral BIM` es una suscripción ICS de solo lectura** (Outlook/
   O365, id `@import.calendar.google.com`): ningún pack futuro debe volver a intentar
   crear ahí ni interpretar el fallo como permiso mal configurado.
3. Se anota el discriminador duro de frescura: **pedir un dato que sólo esté en el
   cuerpo del evento** y contrastarlo verbatim; el título y el horario no bastan para
   descartar reformulación.

## 7. Pendientes para el lane operador (NO ejecutados aquí)

1. **¿Qué se invocó en el turno de las 11:13–11:14?** Desde el rol usuario no es
   observable. La pregunta concreta ya no es "¿hubo llamada?" —la descripción textual
   prueba que hubo lectura en vivo— sino **cuál de las dos rutas la hizo**:
   `umbral_google_calendar_list_events` (que el briefing de las 07:31 declara fallida
   por auth) o el "conector de Google Calendar alternativo". Superficie admin.
2. **Alcance del conector alternativo**: ¿enumera `calendarList` o va directo a
   `primary`? Si enumera, el evento de `Umbral BIM` estaba disponible y no se reportó
   (sería un filtro, no una ceguera). Determina si el punto ciego se arregla con
   configuración o requiere código.
3. **Dimensionar el fix #2 con este dato**: reparar la credencial del Worker no cubre
   `Umbral BIM` (§5). Decidir si el norte es "briefing con todos los calendarios
   suscritos" o "sólo primary, por diseño" es una decisión de producto de David.
4. UX-01 (stream `tool` crudo al canal) sigue abierto del ciclo P1; no se reprodujo hoy.

## 8. Limpieza

El evento `E2E-P3-02-20260804-1103` **sigue en el calendario de David** (13:00–13:30
del 2026-08-04), tal como pide su descripción. Borrarlo es decisión de David: el tester
no borra datos. Sugerencia: eliminarlo cuando este PR esté revisado.
