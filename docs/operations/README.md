# docs/operations/ — ledgers de orquestación (SoT máquina)

Cada archivo `ledger-<programa>.jsonl` en esta carpeta es el ledger append-only
de un programa/frente coordinado por la skill `cursor-orchestrator`
(`umbral-skills-registry/skills/cursor-orchestrator/reference-bitacora.md`).
Una línea = un evento. Nunca se edita ni se reordena una línea existente;
solo se agregan líneas nuevas al final.

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
