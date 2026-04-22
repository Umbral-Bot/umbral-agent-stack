# ADR-008: Orquestación Editorial — Agent Stack Core + n8n Bordes + Make Lab

## Estado

Accepted — 2026-04-21

## Contexto

El sistema editorial de Rick necesita coordinar un flujo multi-step: generación de borradores, revisión humana (HITL), scheduling, publicación multi-canal, alertas de auth expiry, y webhooks entrantes. La investigación UA-14 evaluó tres arquitecturas posibles: Make como core, n8n como core, y Agent Stack core + n8n como capa de bordes.

El Agent Stack ya tiene: Dispatcher, Worker, Notion Poller, OpsLogger, gates humanos, idempotencia (`content_hash`), y supervisor. n8n ya está desplegado en la VPS. David ya tiene suscripción a Make.

La decisión es: ¿qué capa coordina el flujo editorial?

## Decisión

**Arquitectura C (UA-14): Agent Stack core + n8n self-hosted como capa de bordes + Make como lab/stand-by.**

### Agent Stack core — dominio crítico

El Agent Stack mantiene el dominio de las operaciones que requieren estado, trazabilidad y gobernanza:

- Notion Poller (lectura de tareas y estados)
- Dispatcher (enrutamiento de tareas)
- Worker (ejecución de handlers: `llm.generate`, `research.web`, `composite.research_report`, `notion.*`)
- OpsLogger (eventos operativos, trazabilidad)
- Gates humanos (`aprobado_contenido`, `autorizar_publicacion`)
- Idempotencia (`content_hash` en Notion)
- Auth lifecycle tracking (tokens, re-auth alerts)
- Supervisor (health, auto-restart)

### n8n self-hosted — capa de bordes

n8n cubre los bordes que requieren Wait nodes, webhooks entrantes, conectores secundarios y scheduling con UI:

- **Webhooks entrantes**: Ghost `post.published`, `post.edited`; LinkedIn callback; eventos externos
- **Alertas de auth expiry**: cron que verifica tokens y emite alerta a Notion/Telegram
- **Wait/HITL flows**: Wait node para aprobaciones que requieren pausa temporal
- **MCP Server Trigger**: n8n puede ser MCP server para Rick/OpenClaw
- **Conectores secundarios**: Telegram, email (SMTP/SendGrid), calendar
- **Scheduling con UI**: programación visual de publicaciones, cadencias editoriales
- **Export n8n → Git**: backup nocturno de workflows (`n8n export:workflow --all`)

### Make — lab/stand-by/puente MCP

Make se mantiene disponible porque David ya tiene suscripción, pero no como capa crítica:

- **Lab**: prototipar flujos antes de implementar en Agent Stack o n8n
- **Puente MCP**: Make como gateway MCP para servicios que solo tienen conector Make
- **Stand-by**: fallback humano si n8n o Agent Stack están caídos

### Lo que Make NO debe hacer

- **No polling Notion productivo**: quema créditos Make y duplica el Notion Poller del Agent Stack
- **No core crítico**: Make no debe ser la capa que coordina publicación real, porque:
  - Créditos limitados por suscripción
  - Sin acceso SSH a la VPS para repair
  - State management limitado vs Agent Stack + Redis

## Backlog técnico (requisitos de producción n8n)

| Item | Razón | Cuándo |
|------|-------|--------|
| **Postgres desde día 1** | No usar SQLite para n8n producción. SQLite no soporta concurrencia y corrompe bajo carga | Antes de cualquier workflow productivo |
| **Backup `N8N_ENCRYPTION_KEY`** | Fuera de VPS. Si se pierde, todas las credenciales encriptadas se pierden | Inmediato al configurar n8n con Postgres |
| **Export nocturno n8n → Git** | `n8n export:workflow --all --output=./backups/` + commit al repo | Cron nocturno |
| **Notion webhooks beta PoC** | Mantener Notion Poller como fallback hasta validar webhooks beta | Cuando Notion webhooks salgan de beta |
| **Outbox/DLQ PoC** | Patrón outbox o dead-letter queue para publicaciones fallidas que necesitan retry estructurado | Antes de E5 (LinkedIn HITL) |

## Restricciones operativas

- **No usar nodo LinkedIn directo de n8n** mientras exista bug de `LinkedIn-Version` header; si se prueba, usar HTTP Request con versión explícita.
- **No publicar en X/LinkedIn personal sin preview y consentimiento explícito registrado** (HITL obligatorio).
- **Mantener Notion Poller del Agent Stack como fuente primaria de lectura Notion**; n8n puede leer Notion para webhooks secundarios pero no como polling productivo.

## Alternativas consideradas

### A. Make como core

Rechazada. Créditos limitados por suscripción. Sin acceso SSH a VPS para debugging. Polling Notion consume créditos innecesariamente. State management limitado.

### B. n8n como core (reemplazando Agent Stack)

Rechazada. n8n no tiene el modelo de dispatcher/worker del Agent Stack, ni los handlers especializados (43 handlers), ni el OpsLogger, ni la integración con Linear/Redis. Duplicar esa infraestructura en n8n sería retroceso.

### D. Solo Agent Stack (sin n8n)

Rechazada para v1. El Agent Stack no tiene Wait nodes ni webhooks entrantes nativos. Construir Wait/HITL y webhook listener en Python es viable pero duplica lo que n8n ya resuelve. n8n ya está desplegado.

### E. Temporal.io / Inngest / cloud orchestration

Rechazada. Overengineering para el volumen actual (~20-40 posts/mes). Introduce dependencia cloud adicional. El patrón Agent Stack + n8n cubre el caso de uso sin infraestructura nueva.

## Consecuencias

### Positivas

- Agent Stack conserva control de estado, trazabilidad y gobernanza.
- n8n resuelve bordes (webhooks, Wait, scheduling) sin duplicar Agent Stack.
- Make disponible como lab sin quema de créditos en producción.
- Separación clara de responsabilidades: core vs bordes vs lab.

### Negativas

- Dos sistemas (Agent Stack + n8n) a mantener en VPS.
- Requiere Postgres para n8n (vs SQLite default).
- Requiere backup strategy para `N8N_ENCRYPTION_KEY`.
- Coordinación entre Agent Stack y n8n workflows necesita interfaz clara (webhooks o Redis).

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| n8n Postgres corrompe/pierde datos | Baja | Alto | Backup diario + export nocturno a Git |
| `N8N_ENCRYPTION_KEY` perdida | Baja | Crítico | Backup fuera de VPS (documentado en runbook) |
| Notion webhooks beta rompen flujo | Media | Medio | Mantener Poller como fallback hasta validar |
| n8n nodo LinkedIn bug `LinkedIn-Version` | Conocido | Medio | Usar HTTP Request node con versión explícita |
| Make créditos se agotan durante lab | Baja | Bajo | Make no es crítico; lab puede pausarse |

## Fuentes Perplexity

- **UA-14**: `Perplexity/Umbral Agent Stack/14_ Orquestación Editorial con Make n8n y Cron/UA-14-orquestacion-editorial.md` — comparativa de arquitecturas, backlog técnico, restricciones operativas
- **UA-10**: `Perplexity/Umbral Agent Stack/10_…/informe-publicacion-editorial.md` — endpoints y auth lifecycle por canal (feeds into orchestration requirements)
