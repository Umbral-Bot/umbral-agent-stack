---
name: provider-status
description: >-
  Query LLM provider status, quota usage, and model routing configuration from
  the Worker API. Use when "check providers", "quota status", "which models",
  "provider health", "LLM status", "routing config", "API usage".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env:
        - WORKER_TOKEN
---

# Provider Status Skill

Rick puede consultar el estado de los providers LLM configurados, su cuota de uso y la configuración de routing de modelos.

## Requisitos

- `WORKER_TOKEN`: Token de autenticación del Worker API (Bearer token).
- Worker corriendo y accesible.
- Redis disponible (el endpoint consulta cuota en Redis).

## Endpoint disponible

### Consultar estado de providers

**Endpoint:** `GET /providers/status`

**Auth:** Bearer token en header `Authorization`.

```bash
curl -s -H "Authorization: Bearer $WORKER_TOKEN" \
  http://localhost:8088/providers/status | jq .
```

### Respuesta

```json
{
  "timestamp": "2026-03-04T15:30:00Z",
  "configured": ["gemini_flash", "openai_gpt41", "azure_foundry"],
  "unconfigured": ["anthropic_claude"],
  "providers": {
    "gemini_flash": {
      "configured": true,
      "model": "gemini-2.5-flash",
      "quota_used": 42,
      "quota_limit": 500,
      "quota_fraction": 0.084,
      "quota_status": "ok",
      "routing_preferred_for": ["general", "research"]
    },
    "openai_gpt41": {
      "configured": true,
      "model": "gpt-4.1",
      "quota_used": 120,
      "quota_limit": 200,
      "quota_fraction": 0.6,
      "quota_status": "ok",
      "routing_preferred_for": ["coding", "critical"]
    }
  }
}
```

### Campos de cada provider

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `configured` | bool | Si las env vars requeridas están presentes |
| `model` | str | Nombre del modelo asociado |
| `quota_used` | int | Requests consumidos en el periodo actual |
| `quota_limit` | int | Límite máximo de requests por periodo |
| `quota_fraction` | float | Fracción de cuota consumida (0.0–1.0) |
| `quota_status` | str | `"ok"`, `"warn"`, `"restrict"`, `"exceeded"`, `"unknown"` |
| `routing_preferred_for` | list[str] | Task types para los que este provider es preferido |

### Valores de quota_status

| Estado | Significado |
|--------|-------------|
| `ok` | Cuota dentro de límites normales |
| `warn` | Cuota por encima del umbral de advertencia (≥80%) |
| `restrict` | Cuota por encima del umbral restrictivo (≥95%) |
| `exceeded` | Cuota excedida (≥100%) |
| `unknown` | No se pudo determinar (provider no configurado o sin datos) |

## Notas

- Este endpoint es de solo lectura; no modifica configuración.
- La cuota se trackea por periodo (configurable en `config/quota_policy.yaml`).
- El routing de modelos se configura en `config/quota_policy.yaml` bajo la clave `routing`.
- Requiere Redis activo; si Redis no está disponible, devuelve HTTP 503.
