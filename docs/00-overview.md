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

## Estado Actual

| Componente | Fase | Estado |
|-----------|------|--------|
| OpenClaw Gateway | 1.0 | ✅ Operativo |
| Telegram Bot | 1.0 | ✅ Operativo |
| Tailscale VPN | 1.5 | ✅ Operativo |
| Worker FastAPI | 1.5 | ✅ Operativo |
| NSSM Service | 1.5 | ✅ Operativo |
| Notion Bridge | 1.7 | ✅ Código listo |
| Plan Maestro v2.8 | S0 | ✅ Documentado |
| ADRs (4) | S0 | ✅ Documentados |
| TaskEnvelope v0.1 | S1 | 📋 Diseñado |
| ModelRouter + Cuotas | S4 | 📋 Planificado |
| Equipos + Supervisores | S3 | 📋 Planificado |
| LangGraph | S2 | 📋 Scaffolding |
| LiteLLM | S2 | 📋 Scaffolding |
| Redis | S2 | 📋 Scaffolding |
| Langfuse | S6 | 📋 Planificado |
| PAD/RPA | S5 | 📋 Planificado |

## Documentos de Referencia
- [Plan Maestro v2.8](14-codex-plan.md)
- [Política Multi-Modelo](15-model-quota-policy.md)
- [ADRs](adr/)
