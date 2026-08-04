# P3-02 — sonda de frescura y alcance del calendar de Rick (2026-08-04)

> Status: **EJECUTADA — sub-sonda P3-02 en PASS, código `B_PRIMARY_ONLY`.**
> Cierra la sonda que P3-01 §5 dejó propuesta y **avanza** —no cierra— el criterio 1
> PARCIAL de la retro P4 §3: quedan 2 de 4 sondas P3 sin correr (P3-03, P3-04).
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §6 P3-02, §8 evidencia.
> Pack: PKG-USER-E2E-P3-02 · rama `claude/pkg-user-e2e-p3-02-20260804` · base `492aecc1`.
> **GO**: el pack PKG-USER-E2E-P3-02, emitido por David, es la confirmación que
> P3-01 §5 y P4 §5 exigían para correr esta sonda. Ordena el procedimiento paso a
> paso, incluida la creación del evento de contraste **por el tester** (ver §2.4).
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
**imposible crear el evento fresco ahí**, como pedía el procedimiento del pack — no es
una cuestión de permisos mal configurados sino de la naturaleza del objeto. El diseño
se adaptó (§2.4) sin perder ninguno de los dos ejes de medición.

| Gate | Alcance | Resultado |
|---|---|---|
| `USER_E2E_P3_FRESHNESS_PASS` | **sólo la sub-sonda P3-02** | **PASS** — código `B_PRIMARY_ONLY`, sin `D`, sin `C`, sin `E` |

**Advertencia sobre el marcador.** El playbook §8 define
`USER_E2E_P3_FRESHNESS_PASS` como el marcador **único de toda la suite P3**, y la
retro P4 §3 adoptó explícitamente la "lectura completa" (las 4 sub-sondas). Este doc
aporta `[E]` para **una** de ellas. Quien consolide no debe leer este PASS como cierre
del gate de suite: **P3-03 y P3-04 siguen sin correr**. El cierre del gate lo hace el
coordinador o David, no el tester (plan §2.1).

## 2. Evidencia `[E]` — fase A (oráculo Calendar UI)

Superficie: **live**, Claude-in-Chrome sobre el Chrome real de David, sesión ya
autenticada (sin checkpoint de login). Cuenta `david.a.moreira.m@gmail.com`,
zona horaria mostrada por el calendar: **GMT−04**. Operador: Claude Code, rol
Tester Usuario.

Formato de evidencia: transcript verbatim + lecturas literales del UI (texto del
árbol de accesibilidad y de los popups de detalle). **Sin screenshots adjuntos**, por
la misma razón que en P3-01: una captura cruda del calendar y del chat publicaría en
un repo público justo lo que §Nota de privacidad redacta (IDs de seguimiento, datos
de conexión de Teams, terceros). Se privilegia la cita literal redactada sobre la
imagen sin redactar.

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

### 2.3 Hallazgo bloqueante: `Umbral BIM` es de solo lectura

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

### 2.4 Dos desviaciones respecto del plan madre, ambas declaradas

**(a) Quién crea el evento.** El plan `user-e2e-tester-system-plan-2026-08-01.md`
asigna esa acción a David en persona (§3.2 "David crea un evento trivial en calendar
UI (acción de usuario real, suya)"; §4 P3 "evento fresco lo crea David") y la tabla de
superficies §2.2 le da al tester **solo lectura** sobre Google Calendar. **En esta
corrida lo creó el tester**, porque el pack PKG-USER-E2E-P3-02 lo ordena explícitamente
como paso A.3 del procedimiento, con título, duración, calendario destino y descripción
fijados por David. Es una ampliación de superficie **autorizada por escrito y acotada
a un evento propio de David**, no una decisión del tester — pero es una desviación y se
registra como tal, no se disuelve en la voz pasiva. Alcance real del write: un evento
en el calendario personal de David, que sigue ahí (§8). Cero writes en Notion, n8n,
Worker o VPS.

**(b) Dónde se crea.** Con la creación en `Umbral BIM` imposible (§2.3), la sonda se
reorganizó para conservar los **dos** ejes que el pack quería medir, usando dos
observables distintos:

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
2. Rick **declara** dos rutas distintas: la herramienta interna
   `umbral_google_calendar_list_events`, que dice **fallida por auth**, y un
   *"conector de Google Calendar alternativo"* con el que sí lee. La misma distinción
   aparece, con distintas palabras, en los briefings de **5 días**: 24-jul ("la
   integración Worker… falló…; pude leer la agenda usando el conector Google Calendar
   alternativo"), 29-jul, 31-jul ("el worker OpenClaw… falló por auth, pero pude leer
   el calendario por el conector Google Calendar MCP"), 3-ago y hoy 4-ago.

   **Qué prueba y qué no.** Prueba que la frase del turno de las 22:49 que P3-01 §4.2
   dejó en duda **no era un desliz aislado**: es una autodescripción estable. **No**
   prueba que existan dos rutas a nivel de mecanismo — sigue siendo Rick hablando de sí
   mismo, exactamente el tipo de evidencia que `user-e2e-p1-run-2026-08-03-rerun.md`
   §5.1 declaró **no corroborante**. Y **contradice en apariencia** la conclusión de
   P3-01 §4.1 ("el conector … es la extensión `umbral-worker` con su tool tipada …
   **No hay una segunda vía misteriosa**"), que se apoyaba en lo que hay en el repo.
   Las dos cosas pueden ser ciertas a la vez —una sola familia de tools en el código y
   dos caminos efectivos en runtime (p. ej. credenciales o entornos distintos para el
   briefing automático y el turno interactivo)— pero **decidirlo requiere logs del
   runtime**: es del lane operador (§7), no del rol usuario. Este doc no cierra esa
   pregunta; sólo la deja mejor acotada.

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
| `B_PRIMARY_ONLY` | **Sí** | listó exactamente los 2 eventos del primary y omitió el de `Umbral BIM`. El **comportamiento** observado es el de una ruta acotada a un solo calendario; **qué** ruta fue no es observable desde el rol usuario (§7). No se atribuye al default `calendar_id=primary` de `umbral_google_calendar_list_events`: esa es justamente la tool que el briefing de hoy declara fallida (§3.1) |
| `C_STALE_OR_CIRCULAR` | **No** | citó un evento y una descripción que no existían al momento del briefing de las 07:31 y que nunca estuvieron en el chat |
| `D_FABRICATED` | **No** | todo lo afirmado coincide con el UI |
| `E_TOOL_ERROR_UX` | **No en este turno** | ninguna volcada cruda de error; UX-01 sigue registrado por los turnos del 3-ago (22:54 y 22:59), no se reproduce aquí |

**Procedencia de la tabla A–E.** No la escribió esta corrida: viene **pre-escrita en
el pack** que David emitió antes de ejecutar, junto con la regla del gate. Cumple así
el requisito del plan §2.1 (el verificador cierra "contra estado live con checklist
pre-escrita"). Lo que este doc agrega es su aplicación; se versiona aquí porque el
pack vive en el bus humano (chat), no en el repo — por eso hasta hoy los códigos
`A_SEES_UMBRAL`…`E_TOOL_ERROR_UX` no aparecían en git.

**Nota sobre la letra de la tabla.** Tal como venía redactada, `A_SEES_UMBRAL` decía
"menciona el evento fresco `E2E-P3-02-…`", porque el pack asumía que ese evento viviría
en `Umbral BIM`. Como ese calendario resultó no escribible (§2.3), el evento fresco
quedó en el primary y **mencionarlo ya no prueba alcance ampliado**. Leída al pie de la
letra la fila daría `A`; leída por su intención —*"¿ve más que primary?"*— da `B`. Este
doc clasifica por intención y deja la lectura literal explícita para que nadie tenga
que adivinar cuál se aplicó.

**Un descarte adicional, gratis.** `docs/35` §4 (ADR-16) advierte que un `primary`
resuelto con la credencial del Worker sería *el calendario propio de Rick*, no el de
David — el "bug de identidad" que el playbook §6 anota en la fila P3-01. Esta corrida
lo descarta para la ruta que respondió: los eventos reportados son los de **David**,
con horarios y descripción correctos. Sea cual sea el camino, resuelve a la cuenta
correcta.

### 4.3 Aplicación del gate

Regla del pack: `USER_E2E_P3_FRESHNESS_PASS` = PASS si (`A` o `B`) y no `D`.
Resultado: **`B` y no `D` → PASS**, con el alcance acotado que declara §1: este `[E]`
cubre la sub-sonda P3-02, no las cuatro de la suite. `C` queda descartado por evidencia
positiva, no por ausencia de prueba: la descripción textual del evento es el
discriminador duro.

## 5. Relación con P3-01 §5 y con la retro P4

| Pregunta abierta | Estado tras esta corrida |
|---|---|
| P3-01 §5 — *"¿si reporta la sesión de las 10:00, ve más que el primary?"* | **Respondida: no la reporta.** Rick es ciego al calendario `Umbral BIM`; David tiene un punto ciego concreto y diario en sus briefings |
| P3-01 §4.2 hipótesis 4 — *circularidad (reformular el briefing previo)* | **Descartada para este turno.** La descripción del evento fresco no existía en el hilo; sólo se obtiene leyendo el cuerpo del evento en vivo |
| P3-01 §4.2 hipótesis 1/2/3 — *credencial arreglada / entornos distintos / intermitencia* | **Sigue abierta, mejor acotada**: el briefing de hoy 07:31 vuelve a declarar `umbral_google_calendar_list_events` fallida por auth **y** vuelve a decir que leyó por el "conector alternativo" — autodescripción estable en 5 días (§3.1), no un desliz. Sigue sin corroboración independiente, y convive con la conclusión opuesta de P3-01 §4.1 ("no hay una segunda vía"): resolverlo es del lane operador |
| P4 §3 criterio 1 (PARCIAL: 1 de 4 sondas P3) | **Avanza a 2 de 4.** Quedan P3-03 (pieza fuente) y P3-04 (no-autopublish RRSS) |

Lectura de fondo para el sistema, no sólo para el test: **el fix #2 del diag
(credencial Calendar del Worker) por sí solo no le devolvería a David el evento de
`Umbral BIM`.** Aunque la tool tipada vuelva a funcionar, su `calendar_id` por defecto
es `primary` (P3-01 §4.1), y `Umbral BIM` es una suscripción importada aparte que hay
que pedir por su propio id. Son dos problemas distintos y sólo uno de ellos es de
autenticación.

## 6. Actualización propuesta al playbook §6 P3-02 (aplicada en este PR)

1. La fila P3-02 registra la mecánica realmente ejecutable: **el evento fresco va al
   primary** —único calendario escribible— y el **alcance se discrimina con eventos
   que ya viven** en el calendario no-primary. Se mantiene explícito **quién** crea el
   evento: por defecto David (plan §3.2/§4); si lo crea el tester, hace falta orden
   escrita en el pack, como ocurrió aquí (§2.4a).
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
