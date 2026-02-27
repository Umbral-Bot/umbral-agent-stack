# ADR-002: Notion vs Queue para Coordinación

## Estado
Aceptado — 2026-02-27

## Contexto
El sistema necesita dos tipos de comunicación:
1. **Coordinación declarativa**: instrucciones, reportes, Q&A entre David/Rick/agentes
2. **Coordinación transaccional**: colas de tareas, estado, reintentos, idempotencia

¿Usamos Notion para todo, Redis para todo, o un modelo híbrido?

## Decisión
**Modelo híbrido: Notion para declarativo, Redis para transaccional.**

| Tipo | Canal | Ejemplo |
|------|-------|---------|
| Instrucciones humanas | Notion (comentarios) | David → Rick: "Investiga X" |
| Reportes y entregas | Notion (páginas/DBs) | Rick → David: informe de marketing |
| Cola de tareas | Redis (queue) | Rick → Worker: ejecutar tarea |
| Estado de ejecución | Redis (state) | task_id → {status, result} |
| Auditoría | Notion + Langfuse | Trazabilidad completa |

## Razones
1. Notion es excelente como UI humana pero malo como cola transaccional (latencia API ~500ms, no garantiza orden, no tiene ACK).
2. Redis es excelente como cola (sub-ms, FIFO, pub/sub) pero malo como interfaz humana.
3. Los agentes de Notion ya usan comentarios como canal — usamos lo que existe.
4. David interactúa naturalmente con Notion — no necesita aprender herramientas nuevas.

## Consecuencias
- Toda tarea en Redis tiene un reflejo eventual en Notion (auditoría async).
- Los comentarios de Notion se pollan periódicamente y se traducen a TaskEnvelopes.
- Si Redis falla, se puede operar en modo degradado solo con Notion (más lento).
