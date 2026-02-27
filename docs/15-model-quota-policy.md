# 15 — Política Multi-Modelo y Cuotas

## Principio

Cada tarea usa el LLM óptimo según su tipo. Las cuotas protegen suscripciones con límites estrictos. Fallback automático garantiza continuidad.

## Routing por task_type

| task_type | Preferido | Fallback chain | Regla |
|-----------|-----------|----------------|-------|
| `coding` | chatgpt_plus | copilot_pro → claude_pro → gemini_pro | Copilot para MS stack |
| `ms_stack` | copilot_pro | chatgpt_plus → claude_pro → gemini_pro | Copilot en tareas MS alto ROI |
| `writing` | claude_pro | chatgpt_plus → gemini_pro | Claude para síntesis/entrega final |
| `research` | gemini_pro | chatgpt_plus → claude_pro | Claude para consolidación final |
| `critical` | claude_pro | chatgpt_plus | Requiere evidencia y trazabilidad |

## Umbrales de Cuota

| Proveedor | Ventana | Warn | Restrict | Acción |
|-----------|---------|------|----------|--------|
| claude_pro | 5h | 80% | 90% | >80%: solo critical/final; >90%: aprobación David; cap → rotación |
| copilot_pro | mensual | 70% | 85% | >70%: solo alto impacto; >85%: aprobación David; fallback chatgpt_plus |
| chatgpt_plus | 3h | 70% | 90% | >70%: priorizar; >90%: rotar a gemini_pro |
| gemini_pro | diario | 80% | 95% | >80%: reservar para research; >95%: fallback chatgpt_plus |

## Capacidades por Proveedor

| Proveedor | Fortalezas | Limitaciones |
|-----------|-----------|-------------|
| Claude Pro | Razonamiento profundo, escritura, análisis largo | Cuota 5h estricta |
| ChatGPT Plus | General purpose, coding, multimodal | Rate limits variables |
| Gemini Pro | Research, grounding, contexto largo | Menos preciso en código |
| Copilot Pro | MS stack, código, integración VS Code | Solo coding tasks |
| Notion AI | Resúmenes, Q&A sobre workspace | Solo dentro de Notion |

## Implementación Técnica

### ModelRouter (pseudocódigo)

```python
def select_model(task_type: str, quota_state: dict) -> ModelSelectionDecision:
    preferred = ROUTING_TABLE[task_type]["preferred"]
    fallback_chain = ROUTING_TABLE[task_type]["fallback_chain"]
    
    if quota_state[preferred] < WARN_THRESHOLD:
        return ModelSelectionDecision(model=preferred, reason="under_quota")
    
    if quota_state[preferred] < RESTRICT_THRESHOLD:
        if task_type in ["critical", "final"]:
            return ModelSelectionDecision(model=preferred, reason="high_priority_override")
        return select_from_fallback(fallback_chain, quota_state)
    
    # Restrict threshold exceeded
    if requires_approval(preferred):
        return ModelSelectionDecision(
            model=preferred, 
            requires_approval=True,
            reason="quota_exceeded"
        )
    return select_from_fallback(fallback_chain, quota_state)
```

### QuotaTracker

```python
class QuotaTracker:
    """Contador ponderado por proveedor. Persiste en Redis."""
    
    def record_usage(self, provider: str, tokens: int, duration_ms: int)
    def get_quota_state(self, provider: str) -> float  # 0.0 - 1.0
    def reset_window(self, provider: str)  # llamado por cron o al expirar ventana
```

## Política de Aprobación

| Nivel | Condición | Aprobador |
|-------|-----------|-----------|
| Auto | Cuota < warn | Sistema |
| Review | Cuota entre warn y restrict | Rick (log + notify) |
| Approval | Cuota > restrict | David (vía Telegram/Notion) |

## Defaults Explícitos

- Si no se especifica `task_type`: usar `coding` como default
- Si no hay cuota disponible en ningún proveedor: encolar con status `blocked` + alerta
- Si un proveedor no responde en 30s: fallback automático sin esperar
- Idioma de logs y trazas: español
