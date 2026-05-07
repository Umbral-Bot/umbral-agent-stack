# Task O17 — ADR-008 Orquestación Editorial: Agent Stack core + n8n bordes + Make stand-by

**Owner**: Claude Code
**Branch**: `claude/adr-orquestacion-editorial`
**Tipo**: ADR escrito, NO implementación.
**Output esperado**: `docs/adr/ADR-008-orquestacion-editorial.md`
**Plan ref**: O17 del plan Q2-2026 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`).

## Contexto

Hoy hay 3 motores de orquestación disponibles para el Sistema Editorial Rick:

1. **Agent Stack core** (Python custom) — `dispatcher/`, `worker/tasks/*`, ya
   en producción VPS, dueño de Notion writes, Granola pipeline, OpenClaw
   gateway.
2. **n8n** — instalado en VPS desde 2026-03-03, `worker/n8n_client.py` existe,
   N8N_API_KEY en gateway env, 0 workflows productivos hoy.
3. **Make.com** — stand-by, no operativo, no API key activa.

Sin ADR explícita, futuras integraciones (LinkedIn auto-poster, multi-canal
publish, monitoreo competidores, etc.) van a caer "donde sea más fácil al
momento", produciendo arquitectura accidental.

## Alcance del ADR

Decidir, con criterios duros:

1. **¿Cuándo Agent Stack core?**
   - Orchestración stateful con SQLite/Postgres.
   - Tasks que tocan Notion API (auth ya resuelto).
   - Tasks que necesitan ejecutar Python custom (markdown→blocks, ML, etc.).
   - Granola pipeline V2.

2. **¿Cuándo n8n?**
   - Bordes: ingesta webhooks externos, scheduled triggers simples,
     transformaciones JSON sin estado.
   - Integraciones SaaS donde n8n ya tiene nodo oficial (Slack, Discord,
     Google Sheets, etc.) y no vale la pena implementar handler custom.
   - Prototipos rápidos antes de "promover" a Agent Stack core.

3. **¿Cuándo Make stand-by?**
   - Casos donde n8n no tiene nodo y Agent Stack es over-engineering.
   - Marcar criterio de "activación" (qué tendría que pasar para sacarlo de
     stand-by).

4. **Reglas de promoción / migración**:
   - Workflow n8n → Agent Stack core: cuándo y cómo.
   - Anti-patrones: NO duplicar lógica entre los 3, NO escribir Notion desde
     n8n (Agent Stack es dueño único de Notion writes).

5. **Topología de comunicación**:
   - n8n llama a Agent Stack vía HTTP worker (existe).
   - Agent Stack llama a n8n vía `worker/n8n_client.py` (existe).
   - Bordes externos (LinkedIn API webhooks, etc.) → n8n primero.

## Deliverables del ADR

Estructura mínima:

- **Status**: Proposed.
- **Context**: 3 motores, riesgo de drift, plan Q2-2026 referencia.
- **Decision**: matriz de 3 columnas (motor, casos de uso, casos NO).
- **Consequences**:
  - Positive: arquitectura clara, onboarding más rápido.
  - Negative: requiere disciplina, n8n agrega 1 punto de mantenimiento.
- **Alternatives considered**:
  - Solo Agent Stack core (rechazado: bordes simples no valen el ceremonia).
  - Solo n8n (rechazado: Notion auth + Python custom + stateful no escala).
  - Solo Make (rechazado: vendor lock-in, costo, lejos del runtime VPS).
- **Migration path**: si hoy hay workflow n8n que viola la decisión, cómo se
  migra (ninguno hoy, pero documentar el patrón).
- **Open questions**: marcar lo que queda fuera (multi-tenant, auth federada,
  observability cross-motor).

## Reglas duras

- ADR escrito en español, igual estilo que ADR-005/006/007.
- Máximo 600 líneas.
- 0 código, 0 implementación, solo decisión documentada.
- Branch `claude/adr-orquestacion-editorial` desde `main`.
- PR base = `main`.
- NO modificar `worker/n8n_client.py` ni nada en runtime — esto es solo el
  documento.

## Aceptación

- PR abierto contra main con el ADR.
- Referenciado desde `docs/adr/README.md` (si existe).
- Owner (David) revisa, aprueba o pide cambios.
