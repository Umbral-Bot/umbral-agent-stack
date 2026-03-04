# 00 — Visión General del Sistema

## Objetivo

**Umbral Agent Stack** es un sistema multi-agente, multi-modelo que opera como una organización de agentes AI bajo el control de David.

**Rick** (meta-orquestador) recibe instrucciones exclusivamente de David y gestiona 3 equipos de agentes especializados, aprovechando 5 suscripciones LLM (Claude Pro, ChatGPT Plus, Gemini Pro, Copilot Pro, Notion Business).

## Arquitectura: Control Plane + Execution Plane

```
David ──► Telegram/Notion ──► VPS (Control Plane) ──Tailscale──► VM Windows (Execution Plane)
                                    │                                    │
                                    ├── Rick (meta-orquestador)          ├── LangGraph (runtime)
                                    ├── OpenClaw Gateway 24/7            ├── Worker FastAPI :8088
                                    ├── Dispatcher + ModelRouter         ├── PAD/RPA adapters
                                    ├── LiteLLM (proxy multi-LLM)       ├── ChromaDB (vector store)
                                    ├── Redis (cola + estado)            └── Langfuse (observabilidad)
                                    └── Health Monitor
```

### Control Plane (VPS Hostinger, Ubuntu 24 LTS)
- **Rick**: Meta-orquestador 24/7, recibe instrucciones vía Telegram y Notion
- **OpenClaw Gateway**: Telegram bot + Control UI
- **Dispatcher**: ModelRouter → TeamRouter → Redis queue
- **LiteLLM**: Proxy unificado para 5 proveedores LLM
- **Redis**: Cola de tareas + estado transaccional
- **Health Monitor**: Vigila Execution Plane cada 60s

### Execution Plane (VM Windows, Hyper-V)
- **Worker FastAPI**: Ejecutor de tareas vía HTTP :8088
- **LangGraph**: Runtime de grafos para orquestación de agentes
- **PAD Adapters**: Puente a Power Automate Desktop / RPA
- **ChromaDB**: Vector store para RAG
- **Langfuse**: Observabilidad y tracing de LLM calls

### Bus de Coordinación
- **Notion**: UI humana, instrucciones, reportes, auditoría (declarativo)
- **Redis**: Cola de tareas, estado de ejecución, reintentos (transaccional)
- **Tailscale**: Red privada mesh VPS ↔ VM (sin puertos públicos)

## Equipos

| Equipo | Supervisor | Agentes | Función |
|--------|-----------|---------|---------|
| **Marketing** | Sí | SEO, Social Media, Copywriting | Estrategia y ejecución digital |
| **Asesoría Personal** | Sí | Financiero, Lifestyle | Consultas y planificación personal |
| **Mejora Continua** | Sí (OODA) | SoTA Research, Self-Eval, Implementación | Mejora del propio sistema |

## Principios

1. **Solo David manda**: Rick no acepta instrucciones de otros agentes
2. **Seguridad**: Nunca versionar secretos. Todo por Tailscale o SSH tunnel
3. **Resiliencia**: Modo degradado cuando la VM está offline
4. **Multi-modelo**: Cada tarea usa el LLM óptimo según tipo y cuota
5. **Auditable**: Toda ejecución deja traza en Notion + Langfuse
6. **Extensible**: Equipos y agentes se definen como config, no como código

## Estado Actual (actualizado 2026-03-04)

| Componente | Fase | Estado |
|-----------|------|--------|
| OpenClaw Gateway | 1.0 | ✅ Operativo |
| Telegram Bot | 1.0 | ✅ Operativo |
| Tailscale VPN | 1.5 | ✅ Operativo |
| Worker FastAPI | 1.5 | ✅ Operativo (22 task handlers, auth, rate limit, sanitización) |
| NSSM Service | 1.5 | ✅ Operativo |
| Notion Bridge | 1.7 | ✅ Implementado (comments, transcripts, dashboard, kanban) |
| Plan Maestro v2.8 | S0 | ✅ Documentado |
| ADRs (4) | S0 | ✅ Documentados |
| TaskEnvelope v0.1 | S1 | ✅ Implementado (con backward compat legacy) |
| Dispatcher + Redis | S2 | ✅ Implementado (queue, health monitor, N workers) |
| Equipos + Supervisores | S3 | ✅ Implementado (5 equipos, team routing, Notion poller) |
| ModelRouter + Cuotas | S4 | ✅ Implementado (QuotaTracker Redis, fallback chain) |
| PAD/RPA | S5 | ⚠️ Parcial (conector listo, PAD no instalado en VM) |
| Observabilidad | S6 | ✅ Código implementado (OpsLogger, OODA, self-eval) |
| Hardening | S7 | ✅ Implementado (rate limit, sanitización, tool policy) |
| LiteLLM | S2 | ⚠️ Config lista, no desplegado |
| Langfuse | S6 | ⚠️ Docker compose listo, no desplegado |
| n8n | — | ✅ Instalado en VPS (2026-03-03) |

## Documentos de Referencia
- [Plan Maestro v2.8](14-codex-plan.md)
- [Política Multi-Modelo](15-model-quota-policy.md)
- [ADRs](adr/)
