# 14 — Plan Maestro v2.8 (Codex Consolidado)

## Resumen Ejecutivo

Umbral Agent Stack evoluciona de una infraestructura gateway+worker a un **sistema multi-agente, multi-modelo** con orquestación jerárquica.

**Arquitectura oficial:**
- **Control Plane** (VPS): OpenClaw gateway, Dispatcher, LiteLLM, Redis, Health Monitor
- **Execution Plane** (VM Windows): LangGraph runtime, PAD/RPA adapters, ChromaDB, Langfuse

**Meta-orquestador:** Rick opera en el Control Plane, recibe instrucciones exclusivamente de David, y delega a equipos de agentes.

## Decisiones Cerradas

1. Arquitectura split: `Control Plane` (VPS) / `Execution Plane` (VM)
2. Rick = meta-orquestador en Control Plane
3. Notion = UI + auditoría + memoria declarativa; Redis = cola + estado transaccional
4. Todo request pasa por `ModelRouter` → `TeamRouter`
5. Hardening y reproducibilidad son P0 antes de expandir
6. Política de cuotas con aprobación humana para proveedores restringidos

## Equipos Iniciales

### Equipo de Marketing
| Rol | Función |
|-----|---------|
| Supervisor | Estrategia, priorización, reporta al meta-orquestador |
| Agente SEO | Keywords, competencia, optimización on-page |
| Agente Social Media | Calendario, engagement, tendencias |
| Agente Copywriting | Contenido, tono, A/B de titulares |

### Equipo de Asesoría Personal
| Rol | Función |
|-----|---------|
| Supervisor | Recibe consultas, delega según dominio |
| Agente Financiero | Gastos, planificación, alertas presupuesto |
| Agente Lifestyle | Recomendaciones, organización, productividad |

### Equipo de Mejora Continua
| Rol | Función |
|-----|---------|
| Supervisor | Ciclo OODA semanal/diario |
| Agente SoTA Research | Web, ArXiv, competidores, tendencias IA |
| Agente Self-Evaluation | Evals con Langfuse |
| Agente Implementación | Cambios de prompts, tests A/B, reportes |

## Flujo Canónico

```
Ingress (Telegram/Notion)
  → ModelRouter (selección LLM por task_type + cuotas)
    → TeamRouter (despacho al equipo correcto)
      → Queue (Redis)
        → Execution (VM: LangGraph + herramientas)
          → Audit (Notion + Langfuse)
```

## TaskEnvelope v0.1

Contrato mínimo para toda tarea en el sistema:

```json
{
  "schema_version": "0.1",
  "task_id": "uuid",
  "team": "marketing|advisory|improvement|lab",
  "task_type": "coding|writing|research|critical|ms_stack",
  "selected_model": "claude_pro|chatgpt_plus|gemini_pro|copilot_pro",
  "status": "queued|running|done|failed|degraded|blocked",
  "trace_id": "uuid",
  "created_at": "ISO-8601",
  "input": {}
}
```

Campos adicionales (v1.0 futuro): `idempotency_key`, `requested_by`, `channel`, `agent_role`, `fallback_chain`, `quota_state`, `capabilities_required`, `requires_approval`, `approval_status`, `artifacts[]`, `updated_at`.

## Modo Degradado

| Condición | Acción |
|-----------|--------|
| VM offline | Solo tareas LLM-only y coordinación Notion |
| Proveedor no disponible | Fallback chain automático |
| Cuota superada (warn) | Limitar a tareas de alto impacto |
| Cuota superada (restrict) | Aprobación David requerida |
| Sin respuesta | Reencolar con ETA + alerta a David |

## Roadmap por Sprint

| Sprint | Objetivo | Criterio de aceptación |
|--------|----------|----------------------|
| **S0** | Normalización docs/repo | Cero contradicciones, tests base verde |
| **S1** | TaskEnvelope + gobernanza | Toda ejecución usa envelope con trazabilidad |
| **S2** | Orquestación split | E2E con VM on/off |
| **S3** | Equipos + Notion operativo | Delegación paralela + loop Q&A |
| **S4** | ModelRouter + cuotas | Selección correcta por task_type + cuota |
| **S5** | Herramientas Windows/PAD | Ejecución segura con auditoría |
| **S6** | Observabilidad | Reporte semanal automático |
| **S7** | Hardening | Trazabilidad completa + controles seguridad |

## Recursos Disponibles

| Recurso | Tipo | Uso |
|---------|------|-----|
| Claude Pro | LLM suscripción | Escritura, síntesis, critical |
| ChatGPT Plus | LLM suscripción | Coding, general purpose |
| Gemini Pro | LLM suscripción | Research, análisis datos |
| GitHub Copilot Pro | LLM suscripción | Coding MS stack |
| Notion Business | Plataforma | Bus coordinación, auditoría |
| Power Automate Desktop | RPA | Automatización Windows |
| VPS Hostinger | Infra | Control Plane 24/7 |
| VM Windows (Hyper-V) | Infra | Execution Plane |

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| Drift repo/VPS/VM | Checklist automatizado + auditorías periódicas |
| Cuotas no observables real-time | Contador ponderado + política conservadora |
| Dependencia aprobaciones humanas | SLA + fallback predefinido |
| Complejidad PAD/RPA | ToolPolicy estricta + despliegue incremental |
