# 00 — Visión General del Sistema

## Objetivo

**Umbral Agent Stack** es un sistema de agentes AI que opera como gateway 24/7 en un VPS, conectado a un worker local en Windows para ejecución de tareas.

### Componentes activos (Fase 1 / 1.5 — ✅ Hecho)

1. **VPS (Hostinger, Ubuntu 24 LTS)**: OpenClaw Gateway corriendo 24/7 como servicio systemd.
2. **Telegram**: Bot integrado en OpenClaw para interacción con el usuario.
3. **LLM Backend**: OpenAI Codex (`openai-codex/gpt-5.3-codex`) como provider principal.
4. **Tailscale**: Red privada mesh que conecta VPS ↔ Windows sin exponer puertos públicos.
5. **Worker HTTP (FastAPI)**: Servicio en Windows (`0.0.0.0:8088`) que recibe tareas desde el VPS.
6. **NSSM**: Worker ejecutado como servicio de Windows para persistencia.
7. **Scripts utilitarios**: `worker-run` / `worker-call` en el VPS para invocar el worker.

### Componentes planificados (Fase 2 / 3 — 📋 Planificado)

- **LangGraph**: Orquestación de agentes con grafos.
- **LiteLLM**: Proxy unificado para múltiples LLMs.
- **Redis**: Cache y state store para LangGraph.
- **Langfuse**: Observabilidad y tracing de LLM calls.
- **ChromaDB**: Vector store para RAG.
- **PAD (Process Automation & Deployment)**: Integración de automatización (Fase 3).

## Principios

1. **Seguridad**: Nunca versionar secretos. Nunca exponer paneles a internet. Todo por SSH tunnel o Tailscale.
2. **Simplicidad operativa**: Cada componente debe poder verificarse con un solo comando.
3. **Documentación primero**: Todo lo implementado se documenta con comandos exactos reproducibles.
4. **Extensibilidad**: El worker soporta handlers por tarea, preparado para crecer.

## Estado Actual

| Componente | Fase | Estado |
|-----------|------|--------|
| OpenClaw Gateway | 1.0 | ✅ Operativo |
| Telegram Bot | 1.0 | ✅ Operativo |
| Tailscale VPN | 1.5 | ✅ Operativo |
| Worker FastAPI | 1.5 | ✅ Operativo |
| NSSM Service | 1.5 | ✅ Operativo |
| LangGraph | 2.0 | 📋 Scaffolding |
| LiteLLM | 2.0 | 📋 Scaffolding |
| Redis | 2.0 | 📋 Scaffolding |
| Langfuse | 3.0 | 📋 Planificado |
| ChromaDB | 3.0 | 📋 Planificado |
| PAD | 3.0 | 📋 Planificado |
