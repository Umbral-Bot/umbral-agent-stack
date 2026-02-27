# ADR-001: Ubicación de Rick (Meta-Orquestador)

## Estado
Aceptado — 2026-02-27

## Contexto
Rick es el meta-orquestador del sistema. Necesitamos decidir dónde corre:
- VPS (24/7, recursos limitados: 2 vCPU, 2GB RAM)
- VM Windows (más recursos pero no siempre encendida)
- Híbrido

## Decisión
**Rick opera en el Control Plane (VPS)** como parte de OpenClaw.

La lógica de orquestación (routing, dispatch, coordinación) corre en el VPS 24/7. La ejecución pesada (LangGraph, herramientas, PAD) se delega al Execution Plane (VM).

## Razones
1. El orquestador DEBE estar disponible 24/7 — solo el VPS cumple esto.
2. OpenClaw ya corre en VPS y provee interfaz Telegram + LLM.
3. Si la VM está offline, Rick sigue operando en modo degradado (LLM-only).
4. La lógica de routing/dispatch es ligera y cabe en 2GB RAM.

## Consecuencias
- El VPS NO ejecuta tareas pesadas (LangGraph, ChromaDB, Langfuse).
- Tareas que requieren VM se encolan en Redis cuando la VM está offline.
- Rick necesita health checks periódicos al Execution Plane.
