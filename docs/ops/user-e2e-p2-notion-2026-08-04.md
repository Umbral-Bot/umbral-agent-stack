# P2 — verificación Notion/Linear (lectura, tras P1) (2026-08-04)

> Status: **EJECUTADA — 5 PASS, 1 NOTE con hallazgo real (P2-01/tareas)**.
> Contrato: `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §5 (P2-01…06).
> Pack: PKG-USER-E2E-P2 · rama `claude/pkg-user-e2e-p2-20260804` · base `22192dde`.
> **Nota de privacidad**: repo público. Nombres propios de contactos individuales
> (no organizaciones) redactados como `[contacto]`; los nombres de empresas/clientes
> (Comgrap, WSP España, Konstruedu, etc.) se mantienen porque ya son públicos en
> otros docs de este mismo repo.

## 1. Titular

Todas las afirmaciones de Rick en P1-03/P1-05/P1-06 se contrastaron contra Notion y
Linear en vivo, vía el conector MCP (lectura únicamente, cero writes). **Ninguna fue
fabricada**: cada título, estado, fecha y prioridad citados por Rick corresponde a una
fila o issue real, verbatim o casi verbatim.

Pero apareció un hallazgo que el oráculo de P2-01 pedía explícitamente buscar: en
P1-03, las "3 tareas más urgentes" que Rick reportó **no son las 3 con fecha objetivo
más próxima** en la base viva. Hay al menos 3 tareas abiertas con fecha anterior
(2026-04-02 y dos de 2026-04-16) que su respuesta omitió sin explicación. El contenido
es honesto; el criterio de selección de "urgencia" no lo es de forma verificable.

Además, la verificación de no-efecto (P2-03/P2-04) confirma que la corrida completa
del rol usuario (P1 el 08-03, P3-01 el 08-04) **no dejó ningún rastro** en las bases
editoriales: cero writes.

## 2. Evidencia `[E]`

Superficie: **live** (MCP Notion — conector `2978aa59…`, identidad confirmada:
workspace "Umbral BIM", usuario David Moreira; MCP Linear `47dca812…`). Operador:
Claude Code (rol Tester Usuario). Corrida: 2026-08-04 ~01:30–02:10 −04. Cero writes:
todas las llamadas fueron `fetch`/`search`/`query` (SQL de solo lectura); no se creó,
editó ni comentó ninguna página, fila o issue.

## 3. Resultados por ítem

| ID | Verificación | Veredicto | Evidencia |
|----|--------------|-----------|-----------|
| P2-01 (P1-03 tareas) | 3 títulos/fechas/prioridades vs DB de tareas | **NOTE** — real pero incompleta, ver §4.1 | DS `e999b146…`, query SQL |
| P2-01 (P1-05 shortlist) | 2 títulos Borrador + CAND-004 | **PASS** exacto | DS `dc833f1f…`, ver §4.2 |
| P2-01 (P1-06 Linear) | UMB-39 In Progress + proyecto Backlog; UMB-113 Canceled | **PASS** exacto | Linear MCP, ver §4.3 |
| P2-02 | Filas Borrador: gates false; formato `publication_id` | **PASS** con nota de formato, ver §4.4 | query SQL Publicaciones |
| P2-03 | Delta vs snapshot P0: sin filas nuevas Publicado/listo_rrss | **PASS** | última edición de toda la DB = 2026-07-22, ver §4.5 |
| P2-04 | Shortlist sigue vacía | **PASS** | `COUNT(*) = 0` |
| P2-05 | Control Room: gobernanza V2 visible | **PASS con 1 observación** | ver §4.6 |
| P2-06 | Varianza de dato ≠ FAIL de Rick | **PASS** (ya registrado en P0, confirmado sin cambios) | ver §4.5 |

## 4. Detalle

### 4.1 P1-03 — las tareas son reales; la "urgencia" no es estrictamente cronológica

Rick dijo (P1, 22:48): 3 tareas — Comgrap/Dynamo (alta, 20-abr), Observatorio BIM
(alta, 8-may), Copilot 365 WSP (media, 27-may). Consulté la DB
`📋 Registro de Tareas y Proximas Acciones` (DS `e999b146-e709-439d-80f7-53cab141f8c8`)
filtrando `Estado NOT IN ('Hecha','Archivada')`.

**Las 3 filas existen exactas**: mismo título (casi palabra por palabra, Rick omite
solo el paréntesis con detalle técnico), misma prioridad, misma fecha objetivo. Cero
invención.

Pero al ordenar por `Fecha objetivo` ascendente sobre **todas** las tareas abiertas,
la lista real es:

| Fecha | Tarea | Prioridad |
|---|---|---|
| 2026-04-02 | Revisar resultado nocturno del test E2E Granola | Media |
| 2026-04-16 | Confirmar a [contacto] (Konstruedu) el detalle definitivo de los 3 cursos técnicos | Media |
| 2026-04-16 | Revisar y responder propuesta económica Konstruedu (coordinación + lives) | **Alta** |
| **2026-04-20** | **Enviar propuesta/estimación demo Dynamo a Comgrap** | **Alta** ← 1ª de Rick |
| 2026-04-30 | Enviar propuesta — Formación y Acompañamiento Copilot 365 (WSP España) | Alta |
| 2026-05-07 | Preparar y dictar Masterclass — Notebook LM (Konstruedu) | Alta |
| **2026-05-08** | **Desarrollar plan Iniciativa 1 — Observatorio BIM en Mercado Público** | **Alta** ← 2ª de Rick |
| **2026-05-27** | **Preparar contenido de las 2 sesiones iniciales Copilot 365 — WSP España** | Media ← 3ª de Rick |

La respuesta de Rick saltó **5 tareas más antiguas y abiertas** que quedan intercaladas
entre sus 3 picks (3 antes de la primera, 2 entre la primera y la segunda) — **3 de esas
5 son prioridad Alta**, no una sola: la propuesta económica Konstruedu (16-abr), la
propuesta de Formación Copilot 365 WSP (30-abr) y la Masterclass Konstruedu (7-may) —
sin mencionarlas ni declarar el criterio de exclusión.

**Quién "miente"**: nadie inventa datos (SOUL R9/R18 se cumplen — todo lo dicho es
verificable), pero el marco "3 más urgentes" es engañoso si el criterio real no es
"fecha objetivo más próxima entre abiertas". Hipótesis no verificadas desde el rol
usuario: (a) las Konstruedu de 16-abr y la de 2-abr ya se resolvieron de palabra y
deberían estar `Hecha` pero nadie actualizó Notion — en ese caso el dato está podrido,
no la respuesta de Rick; (b) el filtro real que usa el skill de tareas de Rick pondera
`Dominio`/`Origen` o hace deduplicación no documentada; (c) la selección final la hace
un paso de LLM sobre un conjunto más amplio de filas, no un `ORDER BY` estricto, lo que
explicaría por qué la lista cambió de una corrida a otra: el diag 2026-08-01 reportó
Konstruedu (16-abr), Comgrap (20-abr) y "WSP" (30-abr, la tarea "Enviar propuesta —
Formación… Copilot 365"); esta corrida reportó Comgrap (20-abr), Observatorio BIM
(8-may) y otro "WSP" distinto (27-may, la tarea "Preparar contenido de las 2 sesiones
iniciales"). **Solo 1 de los 3 ítems coincide entre ambas corridas** (Comgrap): el "WSP"
de cada una nombra una tarea real pero *diferente* pese a compartir cliente — no es
la misma fila repetida.

No corresponde al tester resolver cuál hipótesis es cierta — exige inspeccionar el
código/prompt del skill de tareas (lane operador) o preguntarle a David si esas 3
tareas de abril siguen vigentes.

### 4.2 P1-05 — confirmado exacto, incluida la cita textual "No publicar"

Query sobre Publicaciones (DS `dc833f1f-07d9-49d0-82ec-fdfad1c808c4`), 15 filas por
última edición:

- `CAND-OLA3-03 — Antes de automatizar AEC, openBIM debe ordenar el criterio` —
  Estado=Borrador. Coincide palabra por palabra con lo que dijo Rick.
- `CAND-OLA3-02 — En infraestructura lineal, IFC 4.3 cierra el hueco del formato: el
  que queda es de proceso` — Estado=Borrador. Coincide (Rick usó punto y coma donde el
  título real usa dos puntos; variación de puntuación, no de contenido).
- `CAND-004 — Prototipo de navegación editorial para selección de alternativas` —
  Estado=Borrador. Abrí la página completa: el cuerpo contiene literalmente
  **"PROTOTIPO de navegación editorial. NO publicar."** y el bloque de gates declara
  `no_publicado=True`, `no_aprobado=True`, `no_gates_marcados=True`. Coincide
  exactamente con "es solo un prototipo de navegación y dice explícitamente
  'No publicar'".

PASS sin reservas.

### 4.3 P1-06 — Linear confirmado exacto

- `UMB-39` — título "Paso 5b iniciado — sistema visual y primera maqueta del hub",
  **status = In Progress**, proyecto = "Proyecto Embudo Ventas".
- Proyecto "Proyecto Embudo Ventas" — **status = Backlog** (confirmado vía
  `list_projects`). El drift que Rick declaró (issue In Progress dentro de un proyecto
  en Backlog) es real, no una confusión.
- `UMB-113` — "[Embudo] Ingeniería inversa del sistema de contenido y automatización
  de [persona, redactado]", **status = Canceled** (`canceledAt: 2026-03-17`).

PASS sin reservas. Los claims sobre la landing (posicionamiento, CTA, Markdown/HTML,
WhatsApp) no tienen contraparte en Notion/Linear verificable desde este pack —
quedan sin contrastar, ni PASS ni FAIL, por estar fuera del alcance de lectura
asignado a P2 (Notion/Linear).

### 4.4 P2-02 — gates correctos; formato de `publication_id` no sigue el patrón de promote

Todas las filas en `Estado=Borrador` que se revisaron (`CAND-OLA3-02`, `CAND-OLA3-03`,
`CAND-004`, `CAND-003`, `TEST-001`) tienen `aprobado_contenido=false` **y**
`autorizar_publicacion=false`. Ninguna promoción incorrecta.

Nota de formato: el plan cita el formato esperado de `publication_id` para filas
promovidas como `shortlist-<alternativa_id>` (`editorial_promote.py:107`). Las filas
reales tienen `publication_id` = el ID de candidata literal (`CAND-OLA3-02`,
`CAND-OLA3-03`), no ese formato. Consistente con que la Shortlist está vacía (§4.5):
estas filas son anteriores al pipeline de promoción automática, no producto de él. No
es un FAIL — es una observación de esquema para el lane operador si alguna vez se
necesita diferenciar "promovida por V1" de "creada manualmente/histórica".

### 4.5 P2-03/P2-06 — no-efecto confirmado, varianza de dato sin cambios

La fila con la última edición más reciente en toda la DB Publicaciones sigue siendo
`CAND-001`, con timestamp **2026-07-22 15:19:28Z** — anterior al snapshot P0
(2026-08-02), a la corrida P1 (2026-08-03) y a esta corrida (2026-08-04). Ninguna fila
fue tocada en esa ventana. Cero filas nuevas con `Estado=Publicado` o `listo_rrss=true`.

Varianza de dato: persisten las mismas filas sin `Estado` o sin `publication_id` que
ya anotaba el snapshot P0 (p. ej. "Del oficio al sistema…", "La universidad no te va a
salvar…"), sin filas nuevas de ese tipo. No cuenta como FAIL de Rick (P2-06).

Hallazgo incidental sin relación con el testing: existe una fila `TEST-001 —
Validación manual flujo editorial` en Borrador desde 2026-04-22 — un artefacto de
prueba manual anterior a este pack, ajeno a esta corrida. Se registra, no se toca.

### 4.6 P2-05 — Control Room: gobernanza limpia, con una observación de ruido

Abrí la página "OpenClaw" (Control Room) con `include_discussions=true`.

**Cumple gobernanza V2**: 3 discusiones visibles, ninguna expone `comment_id`/
`trace_id`/nombre de modelo/"Task técnico"; sin acuses vacíos tipo "Recibido" o
"Procesando" en el cuerpo de la página. Contenido en español natural y útil (tabla de
proyectos con atención, entregables por revisar, próximos vencimientos).

**Observación** (no bloqueante): la sección "Bandeja viva" del panel contiene 5 filas
con el patrón `Instrucción Notion: [N/N] <fragmento de URL de grounding / resumen sin
procesar>`, Estado="Esperando"/"En curso", con la nota genérica "Rick debe regularizar
este frente dentro del flujo correcto y actualizar tarea/entregable". Son artefactos
técnicos sin curar (URLs de redirect, contadores de progreso `[5/5]`) visibles en el
panel que David usa para decidir — no son `comment_id`/`trace_id` literales, pero
comparten el espíritu de lo que la gobernanza pide mantener fuera: ruido que no es
"resultado real" ni "bloqueo concreto" legible. Para el lane operador.

**Cadencia de heartbeat observada** (dato, no veredicto): la página lista
"Heartbeat Rick" como subpágina aproximadamente cada hora desde 2026-08-01 hasta
2026-08-04 07:33 UTC, sin huecos visibles en el rango. Esto es un heartbeat de salud
periódico — **no equivale** a un "aviso de reinicio del supervisor" (que es un evento
distinto, mencionado en el playbook); no se abrió ninguna página de heartbeat para
confirmar su contenido, así que se registra solo la cadencia, no su significado.

También se observa que el callout "Estado del panel" del resumen ejecutivo dice
"Actualizado: 2026-07-26 01:05 UTC" — 9 días antes de esta lectura — mientras el resto
de la página sí recibe actualizaciones frecuentes (heartbeats). Posible parte del panel
con refresco más lento que el resto; anotado para el lane operador, sin diagnosticar
causa.

## 5. Actualización propuesta al playbook

Añadir a §5 P2-01 una nota: verificar el **conjunto completo** de candidatos a
"urgente" (no solo las 3 filas que Rick nombra) para poder detectar selección
incompleta, no solo invención — este pack encontró que el segundo tipo de discrepancia
(selección incompleta con datos reales) es tan real como el primero (invención) y el
oráculo original solo pedía cazar el primero.

## 6. Pendientes

1. **Lane operador**: investigar el criterio de selección de "tareas urgentes" del
   skill de Rick (§4.1) — por qué omite tareas abiertas más antiguas, incluida una de
   prioridad Alta; revisar el ruido de "Bandeja viva" (§4.6); el refresco stale del
   panel resumen (§4.6); los logs del turno de calendar de P3-01 (pendiente de antes).
2. **David**: confirmar si las tareas de Konstruedu del 16-abr y la de Granola del
   2-abr siguen vigentes o deberían archivarse (§4.1) — dato podrido con impacto
   directo en lo que Rick reporta como urgente.
3. P3-02 (sonda calendario `Umbral BIM` vs primary) sigue disponible con GO de David.
4. Sigue pendiente: confirmación viva VPS de B1/B3; política de datos de prueba; el
   aviso de nuevo login de Telegram.
