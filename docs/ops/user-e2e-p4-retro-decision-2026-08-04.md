# P4 — Retro + decisión de capitalización (2026-08-04)

> Status: **EJECUTADA — evaluación honesta de §3.4; recomendación: DIFERIR el GO**
> (con ruta corta y acotada para revertir esa recomendación si David lo prefiere).
> Contrato: `docs/ops/user-e2e-tester-system-plan-2026-08-01.md` §3.4 + §5, §4 (P4).
> Pack: PKG-USER-E2E-P4 · rama `claude/pkg-user-e2e-p4-20260804` · base `e4450320`.
> Este doc no crea, actualiza ni sincroniza ninguna skill; no toca Notion/Telegram/n8n.

## 1. Titular

Cinco packs de experiencia (P0, P1 —dos intentos—, P2, P3-01) corrieron, se
documentaron y pasaron `/code-review` con hallazgos reales corregidos en cada uno.
Los criterios de GO del plan §3.4 se evalúan con honestidad en §3: **4 de 5 se
cumplen con holgura; el criterio 1 ("roadmap P0→P3 completo") es PARCIAL** — el gate
único que el roadmap definió (`USER_E2E_P3_FRESHNESS_PASS`) está satisfecho, pero 3 de
las 4 sub-sondas que el playbook desarrolló operacionalmente para esa suite (P3-02,
P3-03, P3-04) no corrieron.

El plan es explícito: los criterios de GO son "todos, no alguno" (§3.4). Por eso la
recomendación de este doc es **diferir el GO de capitalización** hasta cerrar como
mínimo P3-02 —la sonda más barata y más informativa de las tres pendientes—, dejando
lista la decisión crear-vs-actualizar (§5) para cuando ese criterio se cierre. Si
David prefiere capitalizar ahora igual, la recomendación secundaria de este doc
(§4) es clara: **actualizar `umbral-rick-runtime`**, no crear una skill nueva.

## 2. Matriz consolidada: pack → gate → hallazgo principal → `[E]`

| Pack | PR (mergeado) | Gate | Resultado | Hallazgo principal | `[E]` |
|------|------|------|-----------|---------------------|-------|
| P0 — Smoke lectura | [#573](https://github.com/Umbral-Bot/umbral-agent-stack/pull/573) | `USER_E2E_P0_READ_PASS` | PASS | Shortlist **existe y vacía** (no "puede no existir"); anomalía CAND-001 (`Publicado` con `autorizar_publicacion=false`) | `docs/ops/user-e2e-tester-playbook-2026-08-02.md` §1 |
| P1 (intento 1) — Telegram | [#574](https://github.com/Umbral-Bot/umbral-agent-stack/pull/574) | `USER_E2E_P1_TELEGRAM_PASS` | **BLOCKED** (correcto, no forzado) | Checkpoint humano respetado: sin sesión Telegram, cero mensajes enviados | `docs/ops/user-e2e-p1-run-2026-08-03.md` |
| P1 (rerun) — Telegram | [#575](https://github.com/Umbral-Bot/umbral-agent-stack/pull/575) | `USER_E2E_P1_TELEGRAM_PASS` | 7/7 PASS (1 quedó PENDING hasta P3-01) | **UX-01**: Rick vuelca errores crudos de herramienta al canal del usuario (2 veces); Rick se niega a sustituir el Drive caído por la copia local (conducta correcta) | `docs/ops/user-e2e-p1-run-2026-08-03-rerun.md` §3–§5 |
| P3-01 — Calendar | [#576](https://github.com/Umbral-Bot/umbral-agent-stack/pull/576) | (sub-ítem de `USER_E2E_P3_FRESHNESS_PASS`) | PASS (contenido) | MATCH total incluido un dato solo en el *cuerpo* del evento (no el título) → descarta fabricación; pero queda abierta una **discrepancia temporal** no resuelta (la misma task de calendar figura fallida a las 07:32 y respondiendo a las 22:49 — circularidad no descartada) | `docs/ops/user-e2e-p3-01-calendar-2026-08-04.md` §3–§4 |
| P2 — Notion/Linear | [#578](https://github.com/Umbral-Bot/umbral-agent-stack/pull/578) | `USER_E2E_P2_NOTION_VERIFY_PASS` | 5 PASS + 1 hallazgo real | Las "3 tareas más urgentes" de Rick son reales (cero invención) pero **no son las 3 con fecha objetivo más próxima** — 5 tareas abiertas más antiguas quedaron fuera, 3 de ellas prioridad Alta | `docs/ops/user-e2e-p2-notion-2026-08-04.md` §3–§4 |
| P3-02/03/04 | — | (sub-ítems de `USER_E2E_P3_FRESHNESS_PASS`) | **NO EJECUTADOS** — diferidos por instrucción explícita de este pack | — | — |

Insumo transversal usado por todos los packs: `docs/ops/diag-rick-frescura-2026-08-01.md`
(línea base de frescura: Rick sano, dato Notion podrido, Calendar/RAG apagados).

## 3. Evaluación honesta de los criterios de GO (§3.4)

### Criterio 1 — "≥1 corrida real completa del roadmap P0→P3" → **PARCIAL**

Dos lecturas posibles, con implicaciones distintas:

- **Lectura estricta (gate único del roadmap §4 original)**: el roadmap definió un
  solo gate para P3, `USER_E2E_P3_FRESHNESS_PASS`, con contenido "sondas de frescura
  §3.2 (calendar UI, piezas fuente); documentar el síntoma lado-usuario de auth rota
  si aparece". P3-01 ejecutó la sonda de calendar UI con evidencia completa. Bajo
  esta lectura, el gate **se cumplió** (aunque "piezas fuente" y "síntoma de auth
  rota" no se ejercitaron porque Calendar resultó operativo, no roto).
- **Lectura completa (las 4 sondas que el playbook desarrolló operacionalmente)**:
  el playbook §6, escrito durante P0 con más detalle que el plan original, definió
  P3-01 (calendar hoy), P3-02 (evento fresco — mide frescura real, no solo un
  snapshot), P3-03 (pieza fuente citada por Rick) y P3-04 (no-autopublish RRSS). Bajo
  esta lectura, el roadmap está **incompleto**: 1 de 4 corrió.

Este doc adopta la lectura completa como la más honesta, porque es la que el propio
playbook —escrito por el mismo proceso que este— consideró necesaria para cerrar el
tema frescura con solidez. Los criterios de GO dicen "todos, no alguno": con esa
letra, el criterio 1 no está cumplido al 100%.

**Implicación**: no es un fallo del diseño ni de la ejecución — es que el plan original
subestimó cuántas sondas de contraste hacían falta, y el playbook las agregó
correctamente sobre la marcha. La implicación práctica es acotada: P3-02 es barata
(un evento trivial + una pregunta, ya diseñada) y cierra dos pendientes de una vez
(alcance del calendar de Rick + la hipótesis de circularidad de §4.2 de P3-01); P3-03
depende de que Rick cite una URL de fuente concreta en una respuesta futura (no
totalmente bajo control del tester); P3-04 es casi trivial (mirar perfiles públicos)
pero no se ejecutó porque el pack lo prohibió explícitamente en esta sesión.

### Criterio 2 — "≥1 hallazgo real y ≥1 PASS legítimo" → **CUMPLIDO, con holgura**

Hallazgos reales (no invención, no ruido — todos con `[E]` y corrección post-review
donde aplicó):

1. **UX-01**: errores crudos de herramienta al canal de David (P1 rerun §5.3).
2. **Selección de "urgencia" incompleta**: P1-03 nombra 3 tareas reales pero omite 5
   abiertas más antiguas, 3 de ellas Alta (P2 §4.1).
3. **Anomalía CAND-001**: `Publicado` con `autorizar_publicacion=false`, y su Decision
   Brief pedía explícitamente no marcar `aprobado_contenido` (que sí quedó en `true`)
   (P0 §1.1; ampliada en P1 rerun §6).
4. **Discrepancia temporal de calendar**: la misma task figura fallida y respondiendo
   el mismo día sin explicación verificada (P3-01 §4.2).
5. **Drift Linear**: UMB-39 `In Progress` dentro de un proyecto en `Backlog` — real,
   no una confusión de Rick (P2 §4.3).

PASS legítimos con evidencia dura:

1. Rick honesto ante degradaciones (RAG caído, Drive desmontado) sin que se le
   pregunte — declarado y no inventado (P1 rerun, 4 de 7 sondas).
2. Rick se niega a sustituir una fuente caída por una parecida (P1-07, "no voy a
   confundirte...").
3. Calendar UI confirma un dato que solo vivía en el *cuerpo* del evento, no en el
   título — descarta fabricación de forma no trivial (P3-01 §3).
4. Shortlist vacía confirmada por dos fuentes independientes (lo que Rick dijo + la
   lectura directa por MCP) (P2 §4.2).

No es una suite que todo lo aprueba ni todo lo reprueba: hay PASS con reservas
explícitas (P1-04 pasó de PENDING a PASS solo tras P3-01, no por default) y NOTE que
no son ni PASS limpio ni FAIL (P1-03/P2-01). Esa granularidad es, en sí, señal de que
los oráculos discriminan.

### Criterio 3 — "Fronteras del rol estables" → **CUMPLIDO**

Repasadas las 5 corridas contra §1.3 del plan (las 15 prohibiciones): ninguna
violación. El tester nunca escribió Notion, nunca tocó n8n/VPS, nunca usó el bot
TEST, nunca envió "ok publica", nunca hizo login por sí mismo (esperó el QR de
David), nunca ejecutó smokes admin.

Dos notas operativas menores, **fuera del dominio protegido**, sin relación con la
frontera usuario/admin que el plan cuida:

- El MCP de Notion usado en P2 (`2978aa59…`) fue distinto del mencionado en P0 (el
  original se desconectó entre sesiones); la *acción* siguió siendo lectura MCP, ya
  autorizada por F1 §2.2 — no es una ampliación de superficie, es un cambio de
  implementación del mismo acceso.
- Un sub-agente de `/code-review` en el pack P2 ejecutó `git checkout main` en el
  working tree al terminar su revisión; se detectó y se volvió a la rama del pack
  antes de tocar el archivo, sin pérdida de trabajo. Es un incidente de higiene git
  del tooling, no una violación del rol tester (no tocó ninguna superficie del
  ecosistema Rick).

### Criterio 4 — "Decisión crear-vs-actualizar tomada con los criterios de §5" → se resuelve en §4 de este doc

### Criterio 5 — "GO explícito de David" → pendiente, es la decisión de cierre de este pack

## 4. Recomendación crear-vs-actualizar (§5 del plan)

**Si el criterio 1 se cerrara hoy** (hipotético, para que la recomendación quede
lista sin reabrir este análisis), la evaluación de §5 sería:

- **Crear una skill nueva** exige, entre otras cosas, "el rol se usó ≥2 veces con
  superficies distintas (p. ej. editorial y ops)". No se cumple: las 5 corridas
  vivieron enteramente dentro del mismo dominio — Rick + Telegram + Notion editorial
  + Calendar + Linear del mismo proyecto (Embudo/Sistema Editorial). No hubo una
  segunda superficie categóricamente distinta (p. ej. ops UAS, otro producto).
- El plan también dice: "si en la práctica ambos roles los ejerce el mismo actor en
  los mismos packs, la señal es actualizar, no crear". Es exactamente lo que pasó:
  Claude Code opera a Rick en otros packs de este mismo programa (activación,
  monitoreo) y testeó como usuario en este — mismo actor, mismo dominio.

**Recomendación**: si/cuando se decida capitalizar, **actualizar `umbral-rick-runtime`**
con una sección "verificación en rol usuario" + una referencia nueva (patrón ya usado:
`references/reference-gates.md`), no crear `user-e2e-tester` como skill separada.

Complementaria, de menor alcance: proponer —no ejecutar— una fila nueva en
`reference-e2e-reuse.md` (cursor-orchestrator) citando este programa, porque algunos
patrones sí son transversales y reutilizables fuera de Rick: sesión persistente tipo
storageState para canales de chat, ventanas de espera honestidad-first, separación
lane-usuario/lane-operador, y la regla de redacción de PII en transcripts para repos
públicos (aprendida a la fuerza en los code-reviews de P1/P3-01/P2).

Ambas acciones (actualizar rick-runtime, agregar fila a reference-e2e-reuse) pasarían
por `skills-capitalize` — propuesta, no ejecución, y solo con GO explícito.

## 5. Backlog priorizado post-experiencia

| # | Ítem | Para quién | Por qué importa | Costo |
|---|------|-----------|-------------------|-------|
| 1 | Curar tareas de abril (Konstruedu ×2, Granola) — ¿siguen vigentes? | David | Afecta directamente lo que Rick reporta como "urgente" (P2 §4.1) — impacto en producción, no solo en el test | Bajo |
| 2 | P3-02 (evento fresco en calendar `Umbral BIM`) | Claude local (con GO) | Cierra el criterio 1 de §3.4 y resuelve la hipótesis de circularidad de P3-01 §4.2 en una sola sonda | Bajo |
| 3 | Investigar el stream `tool` del gateway → por qué llega crudo al canal | Lane operador | UX-01; afecta la experiencia de David hoy, no solo en tests | Medio |
| 4 | Logs del turno 22:49 (P1) — ¿hubo llamada real a `umbral_google_calendar_list_events`? | Lane operador | Cierra definitivamente la duda de P3-01 §4.2 (dato real vs. reformulación de briefing) | Bajo-Medio |
| 5 | Anomalía CAND-001 (`autorizar_publicacion=false` + Decision Brief contradicho por `aprobado_contenido=true`) | David / lane operador | Fila de producción con estado inconsistente hace 2 semanas, nadie la ha revisado | Bajo |
| 6 | 2 stashes de higiene con eventos de ledger de otra sesión, sin recuperar en el clone receptor | David | Housekeeping — riesgo de pérdida si se descartan sin mirar | Bajo |
| 7 | `publication_id` de filas históricas no sigue el formato `shortlist-<alternativa_id>` | Lane operador | Nota de esquema, sin impacto funcional confirmado | Bajo |
| 8 | P3-03 (pieza fuente) / P3-04 (no-autopublish RRSS) | Claude local (con GO) | Cierran el criterio 1 al 100%; menor urgencia que P3-02 | Bajo |

## 6. Lo que esta retro no hace

No crea, actualiza ni sincroniza ninguna skill (ni en disco ni en el registry). No
llama a `skills-capitalize`. No escribe en Notion. No abre Telegram. No ejecuta
P3-02/03/04 ni el pack de logs del lane operador — quedan en el backlog de §5,
diferidos por instrucción explícita de este pack.
