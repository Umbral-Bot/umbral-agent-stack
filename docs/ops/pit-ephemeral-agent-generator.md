# PIT — Generador de agentes efímeros (procedimiento Rick)

- **Status:** v1.1 (PIT-2b) — 2026-06-10. Procedimiento ejecutable: los pasos §2.2–§2.7 los automatiza `scripts/pit/pit_tournament_run.sh` ([`pit-2-runner-protocol.md`](pit-2-runner-protocol.md) §7); Rick deriva las identidades (§2.1) en un `lanes.yaml` y lanza el runner con el gate literal.
- **Decisión David:** cada torneo PIT usa **agentes efímeros nuevos** — Rick genera sus prompts, skills y accesos por torneo. No se reciclan agentes entre torneos (evita drift de contexto y privilegios acumulados).
- **Plantilla de rol:** [`openclaw/workspace-templates/pit-lane-agent/ROLE.template.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.template.md).

---

## 1. Por qué efímeros

| Riesgo con agentes persistentes | Cómo lo corta el efímero |
|---|---|
| Contexto de torneos anteriores contamina hipótesis nuevas | nace sin memoria de otros PIT |
| Privilegios acumulados (accesos que ya nadie recuerda) | accesos mínimos generados por torneo, revocados al cierre |
| Identidad ambigua en métricas/kanban | `lane_id` único ligado a un solo `pit_id` |

Los agentes **estables** (Rick, rick-delivery, …) no compiten en lanes PIT: Rick orquesta y hace de broker.

## 2. Procedimiento (Rick, por torneo)

Tras el gate `ok, arranca` con spec validado:

1. **Derivar identidades.** Por cada lane `i` de `lane_count`: `lane_id = lane-<slug-corto>` (ej. `lane-friccion`, `lane-nudges`, `lane-semaforo`) — el slug nombra el ángulo de exploración, no una tecnología.
2. **Render del rol.** Instanciar `ROLE.template.md` con las variables del spec (tabla en §3). El render es el system prompt del agente efímero.
3. **Skills mínimas.** Asignar solo: lectura del pit-vault + escritura en su subárbol, kanban, validador de spec/kpi-pack, y prototipado html. **Sin**: `github-ops`, publicación, Notion write, Magnific directo (el visual va vía Rick broker).
4. **Accesos.** Workspace OpenClaw efímero con `tools.profile` mínimo; presupuesto por lane = `budget_usd / lane_count` traducido a `runTimeoutSeconds`/límites de tokens igual que D3 (ADR §5). Sin tokens de servicios externos.
5. **Registro.** Anotar en `pit/<pit_id>/spec/` un `agents.yaml` con `lane_id → agent_id efímero, created_at, scope`. Es la evidencia de qué existió.
6. **Spawn.** `sessions_spawn` × N desde `main` standalone (mismas pre-conditions D3: `maxSpawnDepth >= 2`, G-D1b, ISSUE-001).
7. **Cierre.** Al terminar el torneo (outcome report escrito): kill de hijos vivos, desactivar/borrar los agentes efímeros del registro OpenClaw, dejar `agents.yaml` como histórico. Los artefactos de las lanes quedan en el vault.

## 3. Variables de render del ROLE.template.md

| Placeholder | Fuente |
|---|---|
| `{{pit_id}}`, `{{title}}`, `{{problem_statement}}` | pit_spec |
| `{{lane_id}}`, `{{lane_focus}}` | derivados por Rick (ángulo de exploración de la lane) |
| `{{iteration_count}}` | pit_spec (input David) |
| `{{budget_lane_usd}}` | `budget_usd / lane_count` |
| `{{research_profile}}` | pit_spec |
| `{{prototype_output}}` | pit_spec |
| `{{kpi_table}}` | render de `kpi_definitions` (kpi_id, unidad, objetivo, dirección, peso) |
| `{{hypothesis_seed}}` | pit_spec (puede ser vacío) |
| `{{visual_enabled}}`, `{{visual_aspect_ratio}}` | pit_spec.visual_generation (default 4:3) |
| `{{synthetic_enabled}}` | pit_spec.synthetic_personas |

## 4. Guardrails no negociables del agente efímero

Heredados al prompt vía plantilla; el generador **no** los puede omitir:

- Write scope: SOLO `pit/<pit_id>/lanes/{{lane_id}}/`.
- Cierre con las tres líneas literales `PROTOTYPE_URL=` / `KPI_PACK=` / `FULFILLMENT=`.
- Preview por túnel + Mission Control; **nunca** URL pública.
- Personas sintéticas siempre etiquetadas.
- **Magnific PROHIBIDO** (regla dura FASE 6, todos los modos): ni invocarlo ni pedirlo — pedirlo ⇒ `lane_blocked`. El registro añade `tools.deny` explícito.
- No merge, no publicar, no tocar Notion, no tocar otros lanes ni `templates/`/`archive/`.
- Sin secretos en el vault (reglas de `pit_vault_check.py`).
