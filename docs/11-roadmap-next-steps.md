# 11 — Roadmap y Próximos Pasos

## Prioridades

### P0 — Inmediato

- [ ] **Integrar OpenClaw → Worker para tareas reales**: Extender el handler del worker más allá de `ping` para ejecutar tareas mínimas reales (ej: file operations, shell commands controlados).
- [ ] **Health router / modo degradado**: Cuando la VM Windows esté apagada, OpenClaw debe detectarlo y operar en modo degradado (solo LLM, sin worker).
- [ ] **Monitoreo básico**: Script/cron que verifica worker health cada N minutos y alerta por Telegram si falla.

### P1 — Fase 2 (LangGraph + LiteLLM + Redis)

- [ ] **LangGraph**: Instalar en VPS (Docker). Orquestador de agentes con grafos.
  - Docker compose scaffold en `infra/docker/docker-compose.hostinger.yml`.
- [ ] **LiteLLM Proxy**: Instalar en VPS (Docker). Proxy unificado para LLMs.
  - Config scaffold en `infra/docker/litellm_config.yaml`.
- [ ] **Redis**: Instalar en VPS (Docker). State store para LangGraph.
  - Incluido en `docker-compose.hostinger.yml`.
- [ ] **Conectar OpenClaw → LangGraph → Worker**: Pipeline completo de orquestación.

### P2 — Fase 3 (Observabilidad + RAG + PAD)

- [ ] **Langfuse**: Instalar en VM local (Docker). Observabilidad y tracing de LLM calls.
  - Docker compose scaffold en `infra/docker/docker-compose.local.yml`.
- [ ] **ChromaDB**: Instalar en VM local (Docker). Vector store para RAG.
  - Incluido en `docker-compose.local.yml`.
- [ ] **PostgreSQL**: Backend para Langfuse.
  - Incluido en `docker-compose.local.yml`.
- [ ] **PAD (Process Automation & Deployment)**: Integración de automatización.
  - Diseño y planning por definir.

## Diagrama de Roadmap

```
Fase 1.0 ✅ ──► Fase 1.5 ✅ ──► Fase 2.0 📋 ──► Fase 3.0 📋
OpenClaw         Tailscale        LangGraph        Langfuse
Telegram         Worker HTTP      LiteLLM          ChromaDB
                 NSSM             Redis            PAD
                 Scripts
```

## Notas Técnicas para Fase 2

### Docker en VPS (Hostinger)

- Verificar que Docker está permitido en el plan.
- Considerar recursos (RAM, CPU) para Redis + LiteLLM.
- Si recursos son limitados, priorizar LiteLLM sobre Redis (Redis puede postergarse).

### LangGraph — Decisiones pendientes

- ¿Grafos estáticos o dinámicos?
- ¿Persistencia de estado en Redis o filesystem?
- ¿Qué tareas del worker se convierten en nodos del grafo?

### LiteLLM — Providers planificados

| Provider | Prioridad | Estado |
|----------|-----------|--------|
| OpenAI Codex | P0 | ✅ Via OpenClaw |
| Anthropic | P2 | ⚠️ Configurado, opcional |
| Local models | P2 | 📋 Pendiente |
