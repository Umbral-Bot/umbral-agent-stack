# docs/operations/ — ledgers de orquestación (SoT máquina)

Cada archivo `ledger-<programa>.jsonl` en esta carpeta es el ledger append-only
de un programa/frente coordinado por la skill `cursor-orchestrator`
(`umbral-skills-registry/skills/cursor-orchestrator/reference-bitacora.md`).
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
| `evento` | Uno de: `EMITIDO \| ACK \| REPORTADO \| PASS \| FAIL \| BLOCKED \| NO_ACK \| REEMISION`. `CERRADO` puede aparecer como cierre explícito de paquete. |
| `ev`     | Evidencia mínima: SHA / PR / run id / gate marker. Puede ser `""`.      |
| `nota`   | ≤120 chars, sin secretos.                                              |

Ciclo de vida del **paquete** (no son eventos, son estados narrados en la spec):
`PENDING → EMITIDO → ACK → EN-CURSO → REPORTADO → CERRADO`, con `SIN_ACK`/`BLOCKED`
como estados marcados explícitamente.

### Clasificación terminal/abierto en el generador (desviación deliberada del enum literal)

`scripts/ops_resume_board.py` trata `evento` así:

- **Terminal** (`[CERRADO]`, no cuenta como "abierta"): `PASS | FAIL | CERRADO`.
- **Abierto** (cuenta como pelota pendiente): `EMITIDO | ACK | REPORTADO | REEMISION | PENDING | DEPLOYED | BLOCKED | NO_ACK` (+ `PAUSED|RESUMED` propuestos).

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

## Extensión de schema propuesta (PROPUESTA, no vigente)

Estos campos/eventos aparecieron en discovery (Codex + Claude, PKG-OPS-RESUME,
2026-08-01) como útiles para el generador, pero **no están en la spec canónica**
de `cursor-orchestrator` todavía. Se documentan acá como propuesta; requieren
bump de versión y PR en `umbral-skills-registry` antes de considerarse parte
del contrato (este repo no edita ese registry):

- `event_id` — id único por línea, para deduplicar reemisiones.
- `thread` — hilo/conversación de origen, para trazar de vuelta al chat que emitió el evento.
- `tipo` — categoría del paquete (discovery / implementación / fix / diagnóstico).
- `gate_state` — estado del gate asociado, si el evento lo dispara.
- `next` — próxima acción explícita (hoy se infiere heurísticamente desde `nota`/`evento`).
- `links` — URLs (PR, doc) asociadas al evento.
- Eventos `PAUSED` / `RESUMED` — para paquetes suspendidos sin ser `BLOCKED` (propuesta original de Codex en discovery).

`scripts/ops_resume_board.py` ya reconoce `PAUSED`/`RESUMED` como eventos
"abiertos" de forma adelantada (no rompe si aparecen), pero no los emite ni
los exige.

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
