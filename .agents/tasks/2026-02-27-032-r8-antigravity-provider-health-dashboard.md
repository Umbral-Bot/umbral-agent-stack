---
id: "032"
title: "Provider Health Dashboard + Multi-Model Status"
assigned_to: antigravity
branch: feat/antigravity-provider-health
round: 8
status: done
updated_at: "2026-03-22T19:04:21-03:00"
created: 2026-02-27
---

## Objetivo

Crear un dashboard de estado de providers que muestre qué modelos están configurados, su cuota actual, y el estado de salud de cada uno. Integrar con Notion para visualización.

## Contexto

- `dispatcher/model_router.py` — tiene `get_configured_providers()` que detecta qué providers tienen env vars
- `dispatcher/quota_tracker.py` — QuotaTracker con estado en Redis
- `worker/notion_client.py` — cliente para actualizar Notion
- `scripts/quota_usage_report.py` — reporte de cuotas existente

## Requisitos

### 1. Endpoint `/providers/status`

Agregar al Worker un endpoint GET que retorne el estado de todos los providers:

```json
{
  "timestamp": "2026-02-27T...",
  "configured": ["claude_pro", "claude_opus", "claude_haiku", "gemini_pro", "gemini_flash", "gemini_flash_lite", "gemini_vertex"],
  "unconfigured": ["azure_foundry"],
  "providers": {
    "claude_pro": {
      "configured": true,
      "model": "claude-sonnet-4-6",
      "quota_used": 0.15,
      "quota_status": "ok",
      "routing_preferred_for": ["coding", "general", "ms_stack", "writing"]
    },
    ...
  }
}
```

### 2. Notion Dashboard Block

Actualizar el dashboard de Rick en Notion con un bloque "Estado de Providers" que muestre:
- Providers activos (verde) vs no configurados (gris)
- Cuota por provider (barra visual)
- Routing actual (qué task_types van a qué provider)

### 3. Script de reporte

Actualizar `scripts/quota_usage_report.py` para usar `get_configured_providers()` y solo reportar providers que estén configurados.

### 4. Tests

- `tests/test_provider_status.py`:
  - Test endpoint retorna providers configurados correctamente
  - Test que providers sin env vars aparecen como "unconfigured"
  - Test formato de respuesta

## Archivos a crear/modificar

- `worker/app.py` — agregar endpoint `/providers/status`
- `scripts/quota_usage_report.py` — actualizar
- `tests/test_provider_status.py` (nuevo)

## Criterio de éxito

- `GET /providers/status` retorna JSON con estado correcto
- Providers sin env vars aparecen como unconfigured
- Script de reporte solo muestra providers activos

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
