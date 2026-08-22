# docs/operations/ — ledgers de orquestación (SoT máquina)

Cada archivo `ledger-<programa>.jsonl` en esta carpeta es el ledger append-only
de un programa/frente coordinado por la skill `cursor-orchestrator`
(`umbral-skills-registry/skills/cursor-orchestrator/references/reference-bitacora.md`).
Una línea = un evento. Nunca se edita ni se reordena una línea existente;
solo se agregan líneas nuevas al final.

**Regla dura:** todo `ledger-*.jsonl` de un programa coordinado por
`cursor-orchestrator` debe estar **trackeado en git** (commiteado) en el
repo de ese programa. Un ledger que solo vive en el filesystem local no es
SoT — es un archivo que un `git clean`, una reinstalación de máquina, o un
worktree nuevo pueden perder sin aviso. Ver "Deuda conocida" al final de
este documento para los ledgers hermanos que hoy violan esta regla (viven
en otros repos, no se tocan desde acá).

## Qué NO es esta carpeta

- No es un dashboard ni una UI. Es el dato crudo que lee
  [`scripts/ops_resume_board.py`](../../scripts/ops_resume_board.py) para
  generar el tablero de reingreso on-demand (ver runbook
  [`docs/ops/ops-resume-reentry-2026-08-02.md`](../ops/ops-resume-reentry-2026-08-02.md)).
- No reemplaza `.agents/board.md` ni Mission Control (`mission_control/`) —
  ver la sección "Delimitación" del runbook.
- No debe contener secretos, tokens, credenciales ni PII. El campo `nota`
  es texto libre corto (≤120 chars): pensalo como un commit message, no como
  un lugar para pegar payloads.

## Schema (v1, spec vigente)

Una línea JSON por evento:

```json
{"ts":"2026-08-01T19:14","pkg":"PKG-OPS-RESUME","frente":"ops-resume","dest":"claude","evento":"PASS","ev":"OPS_RESUME_CLAUDE_DISCOVERY_PASS","nota":"wf_519726f3; NO_PUSH"}
```

| Campo    | Qué es                                                                 |
|----------|-------------------------------------------------------------------------|
| `ts`     | Timestamp del evento. En la práctica conviven ISO con y sin segundos/zona (`2026-08-01T12:40` y `2026-08-01T04:55:00Z`) — el generador tolera ambos. |
| `pkg`    | Id del paquete (`PKG-…`).                                              |
| `frente` | Slug del frente/programa.                                              |
| `dest`   | Destinatario del evento (`cursor`, `claude`, `codex`, `notion-ai`, …). En la práctica también aparece `"claude+codex"` para paquetes con fan-out paralelo a un solo destinatario compuesto. |
| `evento` | Uno de: `EMITIDO \| ACK \| REPORTADO \| PASS \| FAIL \| BLOCKED \| NO_ACK \| REEMISION \| PAUSED \| RESUMED` (`PAUSED`/`RESUMED` desde cursor-orchestrator 0.11.0, 2026-08-20). `CERRADO` puede aparecer como cierre explícito de paquete. |
| `ev`     | Evidencia mínima: SHA / PR / run id / gate marker. Puede ser `""`.      |
| `nota`   | ≤120 chars, sin secretos.                                              |

Ciclo de vida del **paquete** (no son eventos, son estados narrados en la spec):
`PENDING → EMITIDO → ACK → EN-CURSO → REPORTADO → CERRADO`, con `SIN_ACK`/`BLOCKED`
como estados marcados explícitamente.

### Clasificación terminal/abierto en el generador (desviación deliberada del enum literal)

`scripts/ops_resume_board.py` trata `evento` así:

- **Terminal** (`[CERRADO]`, no cuenta como "abierta"): `PASS | FAIL | CERRADO`.
- **Abierto** (cuenta como pelota pendiente): `EMITIDO | ACK | REPORTADO | REEMISION | PENDING | DEPLOYED | BLOCKED | NO_ACK | PAUSED | RESUMED`.

Esto **no** coincide con una lectura literal del enum que trae la misión
PKG-OPS-RESUME-A1 (`terminal = PASS|FAIL|BLOCKED|NO_ACK`). Se corrigió a propósito
tras un `/code-review` sobre el propio PR: `reference-bitacora.md`
(`umbral-skills-registry/skills/cursor-orchestrator`) es explícito en que
`SIN_ACK`/`BLOCKED` son "estados marcados, **no como silencio**" — la intención
de la spec es que un paquete bloqueado siga visible como algo que necesita
decisión, no que desaparezca del conteo de abiertas ni se pinte como cerrado.
Tratarlos como terminales volvía invisible exactamente el caso de uso que este
generador existe para resolver ("pelota de David"). Si Cursor/David prefieren
la lectura literal del enum original, es un cambio de una línea en
`TERMINAL_EVENTS`/`OPEN_EVENTS` — señalarlo explícitamente en vez de reabrir
el paquete.

## Drift real observado (por qué el generador es tolerante)

Los ledgers reales de otros programas (`umbral-bot-cursor`, `visor-ifc`, `PruebaBack`)
ya usan valores fuera de este enum: `PENDING`, `DEPLOYED`, `DEPLOY_STARTED`,
`MERGED`, `MERGED_DEPLOYED`. `scripts/ops_resume_board.py` no falla ante esto:
los trata como eventos "abiertos" y los marca `DRIFT` en el tablero en vez de
descartarlos. También hay líneas malformadas (comillas escapadas rotas) en al
menos un ledger real — el generador las cuenta y las salta, nunca aborta.

## Campos opcionales por línea (contrato cursor-orchestrator 0.11.0, 2026-08-20)

> Antes esta sección era § «Extensión de schema propuesta (PROPUESTA, no
> vigente)» — el registry la cita con ese nombre como origen del contrato.
> Renombrada 2026-08-21 (PKG-OPS-RESUME-GEN) al quedar adoptada.

Estos campos nacieron como propuesta en el discovery de PKG-OPS-RESUME
(Codex + Claude, 2026-08-01; `PAUSED`/`RESUMED` fue propuesta original de
Codex) y fueron **adoptados como contrato vigente** en `cursor-orchestrator`
0.11.0 (PREP-B, `umbral-skills-registry`, GO David). Son opcionales y
backward-compatible: una línea vieja sin ellos sigue siendo válida.
Definición canónica en
`umbral-skills-registry/skills/cursor-orchestrator/references/reference-bitacora.md`;
cualquier cambio al contrato es bump de versión + PR en ese registry — este
repo no lo edita. Este README solo describe cómo los trata el generador.

| Campo | Tipo | Qué es (según el contrato) |
|---|---|---|
| `event_id` | string | id único por línea; dedupe de reemisiones. |
| `thread` | string | hilo/conversación de origen. |
| `tipo` | string (enum corto) | `discovery` / `implementación` / `fix` / `diagnóstico` — vocabulario del evento, **no** la propiedad Notion `Tipo`. |
| `gate_state` | string | estado del gate que el evento dispara (p. ej. `X_CODE_PASS`). |
| `next` | string | próxima acción **emitida por la fuente**. |
| `links` | lista de strings | URLs (PR, doc, evidencia) asociadas al evento. |

Eventos `PAUSED` / `RESUMED` (paquete suspendido sin ser `BLOCKED`) también
entraron al enum en 0.11.0; el generador los trata como abiertos.

### Cómo los trata `scripts/ops_resume_board.py` (PKG-OPS-RESUME-GEN, 2026-08-21; ajustado en PKG-OPS-RESUME-GEN2, 2026-08-22)

**Passthrough literal: el generador los pasa si vienen, no los exige ni los
infiere.** Cada pelota del `--json` trae **siempre** las 6 claves
`event_id`, `thread`, `tipo`, `gate_state`, `next`, `links`:

- Se copian desde la **línea vigente** por `(frente, pkg, dest)`: la de `ts`
  mayor; a `ts` igual (ACK y REPORTADO en el mismo minuto es común), la leída
  después — más abajo en el archivo. No se heredan ni se mezclan opcionales
  de líneas anteriores del mismo paquete.
- String: se copia **tal cual, sin recortar**, si la fuente trae un string no
  vacío ni solo-espacios. Ausente, `null`, en blanco o de otro tipo → `""`.
  No se coacciona (un número no se convierte en string) ni se inventa.
- `links`: forma válida = string único, o lista donde **todos** los ítems
  son strings (puede ser `[]`). Con forma válida: se conservan los strings no
  vacíos, **recortados** (son URLs); string único no vacío → lista de 1.
- **"No vino" y "vino mal" se distinguen.** Si un opcional viene con tipo que
  el contrato no admite (p. ej. `next` como lista — caso real en
  `ledger-n8n-chile-community.jsonl`; o `links` con **cualquier** ítem
  no-string, que invalida todo el campo, sin keep parcial), se descarta a
  vacío **y** se nombra en `opcionales_descartados` (lista por pelota,
  normalmente `[]`); `meta.optionals_type_mismatch` suma esos descartes solo
  de las **pelotas vigentes** del tablero — a diferencia de `events_total` /
  `events_skipped_malformed`, que sí cubren el histórico completo de líneas
  leídas. Misma filosofía que `DRIFT`: marcar, nunca esconder.
- `next` (emitido por la fuente) y `next_inferido` (heurística local: `nota` si
  hay, si no una frase genérica por `evento`) son **campos separados**. El
  generador nunca copia `next_inferido` a `next`; un `next` vacío se queda
  vacío. El espejo Notion (`Next`) consume `next`, no `next_inferido` — por
  eso sigue vacío mientras los ledgers no lo emitan.
- El **tablero humano** (sin `--json`) sigue mostrando solo `next_inferido`;
  los 6 opcionales viven en `--json`, que es lo que consume el espejo.
- Un ledger con bytes no-UTF-8 (writer ANSI) ya no aborta el tablero: se
  decodifica con reemplazo (`U+FFFD`, que varios ledgers reales ya traen).

## Ledgers de otros repos

Esta carpeta solo trackea el ledger del programa `ops-resume` (coordinado
desde este repo). Los ledgers de otros programas (`umbral-bot-cursor`,
`visor-ifc`, `PruebaBack`, …) viven en `docs/operations/` de sus propios
repos y **no se mueven ni se copian acá** — `scripts/ops_resume_board.py`
los lee in-place en runtime, barriendo `<root>/*/docs/operations/ledger-*.jsonl`.

## Deuda conocida: ledgers hermanos sin trackear (2026-08-04)

Inventario de solo lectura hecho en PKG-OPS-RESUME-A2 sobre los repos
hermanos en `C:\GitHub` (`git status --porcelain docs/operations/` en cada
uno). Estos ledgers existen en disco pero no están commiteados en su propio
repo — violan la "Regla dura" de arriba. No se tocan desde este PR (son de
otros repos, fuera de alcance de PKG-OPS-RESUME-A2 que es UAS-only); se
documentan acá como deuda visible para que no quede solo en la memoria de
una sesión.

> **Actualización 2026-08-20:** esta tabla quedó parcialmente superada — 2 de
> los 5 ya están trackeados en su repo y aparecieron deudores nuevos. Estado
> vivo: ver el re-inventario al final de la sección.

| Repo | Ledger | Estado git (2026-08-04) |
|---|---|---|
| `umbral-bot-cursor` | `docs/operations/ledger-microsoft-marketplace-2026-08.jsonl` | untracked (`??`) |
| `umbral-bot-cursor` | `docs/operations/ledger-msft-partner.jsonl` | untracked (`??`) |
| `umbral-bot-cursor` | `docs/operations/ledger-n8n-chile-community.jsonl` | untracked (`??`) |
| `umbral-bot-cursor` | `docs/operations/ledger-workshop-n8n-usm.jsonl` | untracked (`??`) |
| `visor-ifc` | `docs/operations/ledger-visor-ifc.jsonl` | untracked — toda la carpeta `docs/operations/` es `??` en ese repo |

`PruebaBack/docs/operations/ledger-pruebaback.jsonl` sí está trackeado — no
es deuda, se lista arriba en el schema como referencia de drift, no acá.

**Recomendación:** trackear cada uno en un PR aparte, en su propio repo — no
en este. Mientras tanto `scripts/ops_resume_board.py` los sigue leyendo bien
(barre el filesystem, no `git ls-files`), así que el tablero de reingreso no
pierde visibilidad hoy; el riesgo es silencioso a futuro — un
`git clean -fdx`, una reinstalación de máquina, o un worktree nuevo los
borra sin aviso porque git no los está cuidando.

### Re-inventario 2026-08-20 (solo lectura, censo completo)

A diferencia del inventario original, este censo barre **todos** los repos de
`C:\GitHub` con `docs/operations/ledger-*.jsonl` y cruza cada archivo contra
el remoto de su repo (refs `origin/*` locales del día) — un re-chequeo
limitado a los 5 originales nunca podría ver deudores nuevos. Resultado: de
los 5 originales, 2 ya están trackeados; hay 4 deudores nuevos que la tabla
de 2026-08-04 no cubría.

| Repo (remoto) | Ledger | Estado (2026-08-20) |
|---|---|---|
| `umbral-bot-2` | `docs/operations/ledger-microsoft-marketplace-2026-08.jsonl` | **tracked** en `origin/main`; el clone cursor acumula semanas de líneas sin commitear (` M`) |
| `umbral-bot-2` | `docs/operations/ledger-sii-tributario-2026-08.jsonl` | **tracked** en `origin/main`; el clone cursor mantiene una copia `??` divergente (124 líneas de diferencia) — split-brain a reconciliar |
| `umbral-bot-2` | `docs/operations/ledger-msft-partner.jsonl` | untracked (`??`, solo working tree del clone cursor) |
| `umbral-bot-2` | `docs/operations/ledger-n8n-chile-community.jsonl` | untracked (`??`, solo working tree del clone cursor) |
| `umbral-bot-2` | `docs/operations/ledger-workshop-n8n-usm.jsonl` | untracked (`??`, solo working tree del clone cursor) |
| `umbral-bot-2` | `docs/operations/ledger-postulaciones-2026-08.jsonl` | untracked (`??`) — **nuevo** desde 2026-08-04 |
| `visor-ifc` | `docs/operations/ledger-visor-ifc.jsonl` | **tracked** en `origin/master`; el clone acumula semanas de líneas sin commitear (` M`), una de ellas con schema ajeno (`actor`/`event`) |
| `dynamo-mcp` | `docs/operations/ledger-dyn-mcp-tester.jsonl` | untracked — **nuevo**; la carpeta entera es `??` y el ledger está activo (líneas de hoy) |
| `umbral-agent-stack` | `docs/operations/ledger-macro-hygiene-2026-08-11.jsonl` | untracked (`??`) en el working tree del clone canónico — deuda en el propio repo que define esta regla |

La recomendación de arriba sigue vigente para los 6 untracked, cada uno en su
propio repo. Dos avisos que no son "mitad de ciclo": los backlogs locales de
`marketplace` y `visor-ifc` abarcan semanas y ciclos ya cerrados; y antes de
commitear el de `visor-ifc`, revisar su línea de schema ajeno — el ledger es
append-only, una vez commiteada no se corrige.
