---
name: provider-status
description: >-
  Query LLM provider status, quota usage, and routing configuration from the
  Worker API. Use when "check providers", "provider status", "quota usage",
  "which models available", "LLM routing", "model status".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env:
        - WORKER_TOKEN
---

# Provider Status Skill

Rick puede consultar el estado de los providers LLM configurados, su uso de cuota y la configuración de routing del Worker.

## Requisitos

- `WORKER_TOKEN`: Token de autenticación del Worker API (Bearer auth).

## Endpoint disponible

### Consultar estado de providers

**Endpoint:** `GET /providers/status`

```bash
curl -H "Authorization: Bearer $WORKER_TOKEN" http://localhost:8088/providers/status
```

### Respuesta

```json
{
  "timestamp": "2026-03-04T10:00:00Z",
  "configured": ["azure_foundry", "claude_pro", "gemini_pro"],
  "unconfigured": ["claude_opus", "gemini_vertex"],
  "providers": {
    "azure_foundry": {
      "configured": true,
      "model": "gpt-5.3-codex",
      "quota_used": 42,
      "quota_limit": 500,
      "quota_fraction": 0.084,
      "quota_status": "ok",
      "routing_preferred_for": ["llm.generate", "composite.research_report"]
    },
    "claude_pro": {
      "configured": true,
      "model": "claude-sonnet-4-6",
      "quota_used": 120,
      "quota_limit": 200,
      "quota_fraction": 0.6,
      "quota_status": "ok",
      "routing_preferred_for": []
    }
  }
}
```

### Campos por provider

| Campo | Tipo | Descripción |
|---|---|---|
| `configured` | bool | Si las env vars del provider están seteadas |
| `model` | str | Nombre del modelo asociado |
| `quota_used` | int | Requests usados en el período actual |
| `quota_limit` | int | Límite de requests configurado |
| `quota_fraction` | float | Fracción de cuota consumida (0.0–1.0) |
| `quota_status` | str | `"ok"`, `"warn"`, `"restrict"` o `"exceeded"` |
| `routing_preferred_for` | list[str] | Task types que prefieren este provider |

### Quota status

| Status | Significado |
|---|---|
| `ok` | Uso normal, por debajo del umbral de warning |
| `warn` | Uso por encima del 80% (configurable) |
| `restrict` | Uso por encima del 95% — se restringe a tareas esenciales |
| `exceeded` | Cuota superada — el provider no acepta más requests |

## Notas

- Este endpoint está en el Worker API (puerto 8088 por defecto).
- Requiere Redis disponible para consultar datos de cuota. Si Redis no está disponible, retorna HTTP 503.
- Los datos de cuota se resetean periódicamente según la política configurada en `config/quota_policy.yaml`.
- Los providers no configurados aparecen en `unconfigured` con `quota_status: "unknown"`.
