# 11 — Roadmap y Próximos Pasos

> Plan detallado: [docs/14-codex-plan.md](14-codex-plan.md)
> Política de cuotas: [docs/15-model-quota-policy.md](15-model-quota-policy.md)

## Roadmap por Sprint

| Sprint | Objetivo | Estado |
|--------|----------|--------|
| **S0** | Normalización docs/repo | ✅ Completado |
| **S1** | TaskEnvelope + gobernanza | 🔄 En progreso |
| **S2** | Orquestación split (Dispatcher + Redis + VM runtime) | 📋 |
| **S3** | Equipos + Notion operativo (Marketing, Asesoría, Mejora) | 📋 |
| **S4** | ModelRouter + cuotas (5 proveedores LLM) | 📋 |
| **S5** | Herramientas Windows (PAD/RPA + MCP tools) | 📋 |
| **S6** | Observabilidad (Langfuse + evals + ciclo OODA) | 📋 |
| **S7** | Hardening (secretos, ACL Tailscale, sanitización) | 📋 |

## S0 — Normalización (✅ Completado)

- [x] Plan maestro v2.8 → `docs/14-codex-plan.md`
- [x] Política multi-modelo → `docs/15-model-quota-policy.md`
- [x] ADR-001: Ubicación de Rick
- [x] ADR-002: Notion vs Queue
- [x] ADR-003: Modo Degradado
- [x] ADR-004: Política de Cuotas
- [x] Actualizar `00-overview.md` con split Control/Execution Plane
- [x] Actualizar `01-architecture-v2.3.md` con arquitectura objetivo
- [x] Auditoría VPS (`docs/12-vps-audit-2026-02-26.md`)
- [x] Auditoría VM (`docs/13-vm-audit-2026-02-26.md`)

## S1 — TaskEnvelope + Gobernanza (🔄 En progreso)

- [ ] Definir schema TaskEnvelope v0.1 (8 campos core)
- [ ] Crear `worker/models/envelope.py`
- [ ] Refactorizar `worker/app.py` para aceptar envelope
- [ ] Backward compat con formato actual `{task, input}`
- [ ] Endpoint `GET /tasks/{task_id}` para consultar estado
- [ ] Tests actualizados
- [ ] Deploy a VM

## S2 — Orquestación Split

- [ ] Dispatcher en VPS (recibe TaskEnvelope, enruta a equipo)
- [ ] Redis queue en VPS (Docker)
- [ ] LangGraph runtime en VM (Docker)
- [ ] Modo degradado implementado (ADR-003)
- [ ] Health Monitor con alertas a Telegram

## S3 — Equipos + Notion ✅

- [x] TeamRouter (despacho por `team` field)
- [x] Loop bidireccional Notion ↔ Rick (polling + dispatch): `dispatcher/notion_poller.py` — poll Control Room vía Worker, encola tarea por comentario nuevo, responde con `notion.add_comment`; horario XX:10 (doc 18)
- [x] Definición de supervisores (config YAML): `config/teams.yaml` + `dispatcher/team_config.py` (supervisor, roles, requires_vm, notion_page_id por equipo)
- [x] Canales Notion por equipo: `notion_page_id` en `config/teams.yaml` por equipo; poller puede extenderse a múltiples páginas
- [x] Delegación paralela: Dispatcher con N workers (`DISPATCHER_WORKERS`, default 2), cada uno con su conexión Redis y WorkerClient

## S4 — ModelRouter + Cuotas

- [ ] ModelRouter engine (selección por `task_type`)
- [ ] QuotaTracker persistente en Redis
- [ ] Fallback chain automático
- [ ] Umbrales warn/restrict por proveedor
- [ ] Aprobación humana vía Telegram/Notion

## S5 — Herramientas Windows

- [ ] ToolPolicy con allowlist
- [ ] Conector PAD (Power Automate Desktop)
- [ ] MCP tools para Windows
- [ ] Artifacts y auditoría de ejecución

## S6 — Observabilidad

- [ ] Langfuse en VM (Docker)
- [ ] Tracing de todas las LLM calls
- [ ] Evals automáticos (Self-Evaluation agent)
- [ ] Reporte semanal automático (OODA)

## S7 — Hardening

- [ ] Gestión de secretos (vault o equivalente)
- [ ] ACL Tailscale (restricción por nodo)
- [ ] Sanitización de inputs
- [ ] Rate limiting en Worker
- [ ] Trazabilidad completa end-to-end
