---
id: "025"
title: "Quota Dashboard — Reporte de uso multi-modelo en Notion"
assigned_to: antigravity
branch: feat/antigravity-quota-dashboard
round: 6
status: done
updated_at: "2026-03-22T19:04:21-03:00"
created: 2026-03-04
---

## Objetivo

Crear un reporte visual de uso de cuotas por proveedor LLM que se postee en Notion, permitiendo a David ver de un vistazo cuánto se ha usado de cada suscripción.

## Contexto

- `dispatcher/quota_tracker.py` — `QuotaTracker.get_all_quota_states()` devuelve `{provider: usage_fraction}` para todos los proveedores.
- `config/quota_policy.yaml` — límites y ventanas por proveedor.
- `scripts/daily_digest.py` — ejemplo de script que postea a Notion diariamente.
- `worker/tasks/notion.py` — handlers existentes para Notion.

## Requisitos

### 1. Script `scripts/quota_report.py`

- Conectar a Redis y leer estado de cuota de cada proveedor
- Generar un bloque visual con barras de progreso:
  ```
  📊 Quota Report — 2026-03-04 14:00 UTC
  
  gemini_pro:    ████████░░ 82% (410/500) ⚠️ WARN
  chatgpt_plus:  ██░░░░░░░░ 23% (69/300) ✅ OK
  claude_pro:    ░░░░░░░░░░  5% (10/200) ✅ OK
  copilot_pro:   █░░░░░░░░░ 12% (48/400) ✅ OK
  ```
- Incluir: provider, used/limit, porcentaje, estado (OK/WARN/RESTRICT/EXCEEDED)
- Postear como comentario en Notion Control Room via Worker API

### 2. Integrar con el Daily Digest

Modificar `scripts/daily_digest.py` para incluir la sección de quota al final del digest diario.

### 3. Endpoint `/quota/status` en Worker

Agregar un endpoint GET al Worker que devuelva el estado de cuotas en JSON:

```json
{
  "providers": {
    "gemini_pro": {"used": 410, "limit": 500, "fraction": 0.82, "status": "warn"},
    "chatgpt_plus": {"used": 69, "limit": 300, "fraction": 0.23, "status": "ok"}
  },
  "timestamp": "2026-03-04T14:00:00Z"
}
```

### 4. Tests

- Test `quota_report.py` con mock de Redis
- Test endpoint `/quota/status` responses
- Test formato visual con distintos niveles (ok, warn, restrict, exceeded)

## Entregable

PR a `main` desde `feat/antigravity-quota-dashboard` con todos los tests pasando.

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
