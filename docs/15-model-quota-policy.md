# 15 — Política Multi-Modelo y Cuotas

## Principio

Cada tarea usa el LLM óptimo según su tipo. Las cuotas protegen suscripciones con límites estrictos. Fallback automático garantiza continuidad.

## Dos sistemas en paralelo

| Sistema | Modelos simultáneos | Selección |
|---------|--------------------|-----------| 
| **OpenClaw** (bot Telegram) | **Solo 1** modelo activo | Manual vía bot, o automática por quota-guard |
| **Rick** (Agent Stack, VPS) | **Todos simultáneamente** | Automática por ModelRouter + task_type |

Rick no requiere selección manual — cada tarea recibe el modelo óptimo en el momento de despacho.

## Modelos reales disponibles (2026-03-04)

| Provider alias | Modelo real | Acceso |
|----------------|-------------|--------|
| `openai_codex` | `gpt-5.3-codex` | GITHUB_TOKEN (ChatGPT Plus / OAuth) — **PRIORIDAD 1** |
| `claude_pro` | `claude-sonnet-4-6` | ANTHROPIC_API_KEY o GITHUB_TOKEN |
| `claude_opus` | `claude-opus-4-6` | ANTHROPIC_API_KEY (tareas críticas) |
| `gemini_pro` | `gemini-3.1-pro-preview-customtools` | GOOGLE_API_KEY |
| `gemini_flash` | `gemini-flash-latest` | GOOGLE_API_KEY (rápido/económico) |
| `copilot_pro` | `gpt-4o-mini` | GITHUB_TOKEN (fallback) |

## Routing por task_type

| task_type | Preferido | Fallback chain |
|-----------|-----------|----------------|
| `coding` | **openai_codex** | claude_pro → gemini_pro → gemini_flash |
| `general` | **openai_codex** | claude_pro → gemini_pro → gemini_flash |
| `ms_stack` | **openai_codex** | copilot_pro → claude_pro → gemini_pro |
| `writing` | claude_pro | openai_codex → gemini_pro |
| `research` | gemini_pro | openai_codex → claude_pro → gemini_flash |
| `critical` | claude_opus | claude_pro → openai_codex |
| `light` | gemini_flash | openai_codex → gemini_pro |

## Umbrales de Cuota

| Proveedor | Ventana | Warn | Restrict | Acción |
|-----------|---------|------|----------|--------|
| openai_codex | 3h | 75% | 90% | fallback a claude_pro |
| claude_pro | 5h | 80% | 90% | fallback a openai_codex |
| claude_opus | 5h | 60% | 80% | fallback a claude_pro |
| gemini_pro | diario | 80% | 95% | fallback a openai_codex |
| gemini_flash | diario | 85% | 97% | no hay fallback |
| copilot_pro | mensual | 70% | 85% | fallback a openai_codex |

## Capacidades por Proveedor

| Proveedor | Fortalezas | Mejor para |
|-----------|-----------|------------|
| OpenAI Codex (gpt-5.3-codex) | Razonamiento, código, general | coding, general, ms_stack |
| Claude Sonnet 4.6 | Escritura, análisis, síntesis | writing, summaries |
| Claude Opus 4.6 | Razonamiento profundo, crítico | critical, auditoría |
| Gemini Pro (customtools) | Research, contexto largo, web tools | research, SIM, grounding |
| Gemini Flash | Velocidad, volumen alto | tareas ligeras, polling |

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

## Referencia de implementación (S4)

- **ModelRouter**: `dispatcher/model_router.py` — selección por `task_type`, fallback chain, umbrales warn/restrict.
- **QuotaTracker**: `dispatcher/quota_tracker.py` — contador por proveedor en Redis, ventanas configurables.
- **Config**: `config/quota_policy.yaml` — `providers` (limit_requests, window_seconds, warn, restrict) y `routing` (preferido + fallback_chain).
- El Dispatcher inyecta `selected_model` en el input de cada tarea; si `requires_approval` bloquea con `quota_exceeded_approval_required`.
- Registrar uso real (`QuotaTracker.record_usage`) cuando se invoque un LLM (p. ej. desde Worker o LiteLLM).

**Mapeo sugerido de nombres (Rick → proveedores reales):**

- `gemini_pro` → `google/gemini-3.1-pro-preview-customtools` (Pro 3.1 con tools, estable en tus pruebas).
- \"Gemini rápido\" → `google/gemini-flash-latest`.

## OpenClaw y cuota Claude

Cuando OpenClaw usa Anthropic (Claude) y se agotan los tokens, el gateway puede **congelarse**. Conviene cambiar de modelo **antes** del límite (preventivo) y tener un script que cambie a fallback y reinicie cuando ya ocurrió (reactivo). Ver [docs/19-openclaw-claude-quota.md](19-openclaw-claude-quota.md) y `scripts/openclaw_quota_guard.py`.
