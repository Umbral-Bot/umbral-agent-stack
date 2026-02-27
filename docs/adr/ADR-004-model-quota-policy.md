# ADR-004: Política de Cuotas Multi-Modelo

## Estado
Aceptado — 2026-02-27

## Contexto
David tiene 5 suscripciones LLM con cuotas variables:
- Claude Pro: ~45 mensajes/5h (estimado)
- ChatGPT Plus: ~80 mensajes/3h (estimado)
- Gemini Pro: cuota diaria (alta)
- Copilot Pro: mensual (limitado)
- Notion AI: ilimitado dentro de workspace

Un sistema multi-agente que corre 24/7 agotará cuotas rápidamente sin control.

## Decisión
**Implementar política declarativa con 3 niveles: Auto, Review, Approval.**

### Niveles de control

| Nivel | Cuota | Decisión |
|-------|-------|----------|
| **Auto** | < warn threshold | Sistema elige modelo óptimo |
| **Review** | warn ≤ cuota < restrict | Rick limita a tareas high-priority + log |
| **Approval** | ≥ restrict threshold | Requiere aprobación explícita de David |

### Thresholds por proveedor

Definidos en `docs/15-model-quota-policy.md`.

### Contador de cuota

- Tipo: ponderado (no todas las interacciones consumen igual)
- Persistencia: Redis (key por proveedor + ventana temporal)
- Reset: automático al expirar la ventana del proveedor
- Estimación: dado que no todos los proveedores exponen API de cuota, se usa un contador local conservador

## Razones
1. Las cuotas no son observables programáticamente en todos los proveedores.
2. Un contador conservador es mejor que no contar.
3. Rotación automática por fallback chain mantiene servicio continuo.
4. David como gate de aprobación en nivel alto previene desperdicios.

## Consecuencias
- Se necesita un `QuotaTracker` persistente en Redis.
- El `ModelRouter` consulta QuotaTracker antes de cada request.
- Los contadores son estimaciones — pueden haber desviaciones vs cuota real.
- Se necesita calibración periódica comparando uso estimado vs real.

## Referencia
- Tabla completa de routing: `docs/15-model-quota-policy.md`
- Pseudocódigo ModelRouter: `docs/15-model-quota-policy.md` § Implementación Técnica
