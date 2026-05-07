# OpenClaw — Known issues (upstream / runtime)

Documenta comportamientos observados del runtime de OpenClaw que NO son corregibles vía nuestra config (`~/.openclaw/openclaw.json`) y requieren fix upstream o workaround documentado.

## ISSUE-001 — `sessions_*` tools filtrados en context nested

**Versión observada**: OpenClaw `2026.5.3-1` (gateway pid post-restart 75421 a 2026-05-07T10:38:41 -04, según task 021).

**Resumen**: Cuando un agent es invocado **nested** (subagente de `main` o de otro agent), 7 herramientas relacionadas con orquestación de sesiones son **filtradas del whitelist** que entrega el runtime al modelo:

- `sessions_spawn`
- `sessions_send`
- `sessions_history`
- `sessions_list`
- `session_status`
- `agents_list`
- `subagents`

Cuando el mismo agent es invocado **standalone** (entry-point directo desde CLI), las 7 herramientas SÍ aparecen en el tool whitelist.

**Evidencia** (task 023, comparación `context.compiled.tools`):

| sesión                                                       | invocación        | tool count | sessions_spawn |
| ------------------------------------------------------------ | ----------------- | ---------- | -------------- |
| `cb93608c-e5c6-45f8-a782-d718497290d2` (smoke real Ola 1.5)  | nested (main→…)   | 14         | ❌ ausente     |
| `021-smoke-default-20260507T143900Z` (task 021 smoke)        | standalone (CLI)  | 21         | ✅ presente    |

Diff del set: `agents_list, session_status, sessions_history, sessions_list, sessions_send, sessions_spawn, subagents` aparecen solo en standalone.

**No editable vía config**: ningún agent en `agents.list[]` tiene `sessions_*` en `tools.alsoAllow` (incluyendo `rick-orchestrator`). Estas herramientas son inyectadas por el runtime built-in y la asimetría entry-point vs nested es policy del runtime, no del config.

**Impacto**: cuando un orquestador (ej. `rick-orchestrator`) es invocado nested y necesita delegar a otro agent, **no puede spawnear** y queda en gap. Antes de la regla SOUL anti-faking (task 023), el modelo tendía a "satisfacer gobernanza performativamente" inyectando entries fabricadas en `~/.openclaw/trace/delegations.jsonl` con `assigned_to: agent:rick-ops` sin haber spawneado realmente a `rick-ops` (ver línea 13 invalidada por línea 14 en task 023).

**Workaround actual** (Reglas 21 y 22 del SOUL de `rick-orchestrator`, aplicadas en task 023):

1. Cuando el agent detecta el gap nested, debe ejecutar el trabajo inline vía `exec` y registrar la delegación con `assigned_to: agent:rick-orchestrator` (vos mismo) — nunca con un callee fabricado.
2. Alternativa preferida: abortar y devolver el gap a `main` vía `sessions_yield` solicitando re-invocación standalone.
3. NUNCA fabricar entries en `delegations.jsonl` ni en otro log canónico bajo `~/.openclaw/trace/`.

**Fix permanente pendiente**: investigación upstream del runtime de OpenClaw para entender si la restricción nested es:
- (a) Bug (los `sessions_*` deberían estar disponibles también nested), o
- (b) Policy intencional para prevenir cascadas profundas (en cuyo caso, exponer un mecanismo de opt-in via config tipo `agents.list[].subagents.allowSessionsTools: true`).

Hasta que se resuelva, los workarounds Reglas 21/22 del SOUL son canónicos.
