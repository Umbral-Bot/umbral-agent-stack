# 15 — Política Multi-Modelo y Cuotas

## Principio

Cada tarea usa el LLM óptimo según su tipo. Las cuotas protegen suscripciones con límites estrictos. Fallback automático garantiza continuidad.

## Dos sistemas en paralelo

| Sistema | Modelos simultáneos | Selección |
|---------|--------------------|-----------| 
| **OpenClaw** (bot Telegram) | **Solo 1** modelo activo | Manual vía bot, o automática por quota-guard |
| **Rick** (Agent Stack, VPS) | **Todos simultáneamente** | Automática por ModelRouter + task_type |

Rick no requiere selección manual — cada tarea recibe el modelo óptimo en el momento de despacho.

## Modelos reales disponibles (2026-02-27)

### Acceso vía OpenClaw (bot Telegram — OAuth/Token sesión)

| Modelo | Acceso |
|--------|--------|
| `gpt-5.3-codex` (predeterminado) | OAuth ChatGPT Plus |
| `gpt-5.2` | OAuth ChatGPT Plus |
| `claude-haiku-4-5`, `claude-opus-4-6`, `claude-sonnet-4-6` | Token sesión cuenta Pro |
| `gemini-3.1-pro-preview` | API Vertex AI |
| `gemini-flash-lite-latest`, `gemini-flash-latest`, `gemini-3.1-pro-preview-customtools`, `gemini-3.1-pro-preview` | API Google AI Studio |

### Acceso vía Worker (sistema multiagente — API keys directas)

| Provider alias | Modelo real | Autenticación |
|----------------|-------------|---------------|
| `azure_foundry` | `gpt-5.3-codex` | AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY — **CAPACIDAD DEDICADA** |
| `claude_pro` | `claude-sonnet-4-6` | ANTHROPIC_API_KEY (token sesión Pro) |
| `claude_opus` | `claude-opus-4-6` | ANTHROPIC_API_KEY (tareas críticas) |
| `claude_haiku` | `claude-haiku-4-5` | ANTHROPIC_API_KEY (tareas rápidas) |
| `gemini_pro` | `gemini-3.1-pro-preview-customtools` | GOOGLE_API_KEY (AI Studio) |
| `gemini_flash` | `gemini-flash-latest` | GOOGLE_API_KEY (AI Studio) |
| `gemini_flash_lite` | `gemini-flash-lite-latest` | GOOGLE_API_KEY (AI Studio) |
| `gemini_vertex` | `gemini-3.1-pro-preview` | GOOGLE_API_KEY_RICK_UMBRAL + GOOGLE_CLOUD_PROJECT_RICK_UMBRAL |

> **GITHUB_TOKEN** es exclusivamente para git (pull/push). NO se usa para acceso a modelos LLM.

## Routing por task_type

| task_type | Preferido | Fallback chain |
|-----------|-----------|----------------|
| `coding` | **claude_pro** | gemini_pro → azure_foundry* → gemini_flash |
| `general` | **claude_pro** | gemini_pro → azure_foundry* → gemini_flash |
| `ms_stack` | **claude_pro** | gemini_pro → azure_foundry* |
| `writing` | **claude_pro** | claude_opus → gemini_pro |
| `research` | **gemini_pro** | gemini_vertex → claude_pro → gemini_flash |
| `critical` | **claude_opus** | claude_pro → gemini_pro |
| `light` | **gemini_flash** | gemini_flash_lite → claude_haiku → gemini_pro |

> *azure_foundry solo se usa si `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` están configurados. Si no, se salta automáticamente.

## Umbrales de Cuota

| Proveedor | Ventana | Warn | Restrict | Acción |
|-----------|---------|------|----------|--------|
| azure_foundry | 1h | 80% | 95% | fallback a claude_pro |
| claude_pro | 5h | 80% | 90% | fallback a azure_foundry |
| claude_opus | 5h | 60% | 80% | fallback a claude_pro |
| claude_haiku | 5h | 85% | 95% | fallback a gemini_flash_lite |
| gemini_pro | diario | 80% | 95% | fallback a azure_foundry |
| gemini_flash | diario | 85% | 97% | fallback a gemini_flash_lite |
| gemini_flash_lite | diario | 90% | 98% | no hay fallback |
| gemini_vertex | diario | 80% | 95% | fallback a gemini_pro |

## Capacidades por Proveedor

| Proveedor | Fortalezas | Mejor para |
|-----------|-----------|------------|
| Azure Foundry (gpt-5.3-codex) | Cuota dedicada, código, razonamiento | coding, general, ms_stack |
| Claude Sonnet 4.6 | Escritura, análisis, síntesis | writing, summaries |
| Claude Opus 4.6 | Razonamiento profundo, crítico | critical, auditoría |
| Claude Haiku 4.5 | Velocidad, costo bajo | tareas rápidas, clasificación |
| Gemini Pro (customtools) | Research, contexto largo, web tools | research, SIM, grounding |
| Gemini Vertex (3.1 Pro) | Cuota dedicada GCP, estabilidad | backup research, pipelines |
| Gemini Flash | Velocidad, volumen alto | tareas ligeras, polling |
| Gemini Flash Lite | Ultra rápido, mínimo costo | clasificación, routing |

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

## Detección automática de providers

El `ModelRouter` detecta qué providers tienen sus env vars configuradas al arrancar.
Si un provider no tiene sus credenciales, se salta automáticamente en la selección:

| Provider | Variables requeridas |
|----------|---------------------|
| `azure_foundry` | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` |
| `claude_pro/opus/haiku` | `ANTHROPIC_API_KEY` |
| `gemini_pro/flash/flash_lite` | `GOOGLE_API_KEY` |
| `gemini_vertex` | `GOOGLE_API_KEY_RICK_UMBRAL` + `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` |

Cuando se configura un nuevo provider (ej. Azure Foundry), solo hay que agregar las env vars y reiniciar el Dispatcher. El router lo detecta solo.

## Escalación automática a Linear

Cuando una tarea falla, el Dispatcher crea automáticamente un issue en Linear con:
- Titulo, task_id, equipo, tipo de tarea, error
- Prioridad mapeada del task_type (critical=1, coding=2, etc.)
- Labels del equipo inferidos por el `LinearTeamRouter`

Controlado por `ESCALATE_FAILURES_TO_LINEAR=true|false` (default: true).
No crea duplicados si el envelope ya tiene `linear_issue_id`.

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
