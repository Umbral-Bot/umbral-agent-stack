---
name: make-webhook
description: >-
  Send data to Make.com webhooks to trigger automation scenarios via the
  Umbral Worker task make.post_webhook. Supports JSON payloads with URL validation.
  Use when "trigger make scenario", "post to make", "webhook make.com",
  "send data to make", "automate with make", "make.com integration".
metadata:
  openclaw:
    emoji: "\U0001F517"
    requires:
      env: []
---

# Make Webhook Skill

Rick puede enviar datos a webhooks de Make.com para triggear escenarios de automatización a través de la task `make.post_webhook` del Umbral Worker.

## Requisitos

- **URL del webhook de Make.com**: cada webhook tiene su propia URL única. No requiere API key global.
- Las URLs deben comenzar con uno de los prefijos permitidos:
  - `https://hook.make.com/`
  - `https://hook.eu1.make.com/`
  - `https://hook.eu2.make.com/`
  - `https://hook.us1.make.com/`
  - `https://hook.us2.make.com/`

## Task

### `make.post_webhook`

Envía un POST con payload JSON a un webhook de Make.com.

**Input:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `webhook_url` | str | **Sí** | — | URL completa del webhook de Make.com |
| `payload` | dict | **Sí** | — | Datos a enviar como JSON body |
| `timeout` | int | No | 30 | Timeout en segundos (1–120) |

**Output (éxito):**

```json
{"ok": true, "status_code": 200, "response": "Accepted"}
```

**Output (error HTTP):**

```json
{"ok": false, "status_code": 400, "response": "Bad Request: missing field 'email'"}
```

## Ejemplos de uso

### Trigger básico con datos

```json
{
  "task_type": "make.post_webhook",
  "input": {
    "webhook_url": "https://hook.make.com/abc123xyz",
    "payload": {
      "event": "new_lead",
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "source": "umbral"
    }
  }
}
```

### Notificación de estado de tarea

```json
{
  "task_type": "make.post_webhook",
  "input": {
    "webhook_url": "https://hook.eu1.make.com/def456uvw",
    "payload": {
      "task_id": "task-2026-03-04-001",
      "status": "completed",
      "result_summary": "Análisis de mercado completado exitosamente",
      "timestamp": "2026-03-04T10:30:00Z"
    }
  }
}
```

### Envío con timeout extendido

```json
{
  "task_type": "make.post_webhook",
  "input": {
    "webhook_url": "https://hook.us1.make.com/ghi789rst",
    "payload": {
      "report_type": "weekly_ooda",
      "data": {"completed": 42, "failed": 3, "pending": 7}
    },
    "timeout": 60
  }
}
```

## Manejo de errores

| Escenario | Resultado |
|-----------|-----------|
| URL vacía | `ValueError: 'webhook_url' is required` |
| URL no es de Make.com | `ValueError: webhook_url must start with one of: https://hook.make.com/, ...` |
| Payload no es dict | `ValueError: 'payload' must be a dict` |
| Timeout fuera de rango | `ValueError: 'timeout' must be between 1 and 120 seconds` |
| HTTP error del webhook | `{"ok": false, "status_code": <code>, "response": "..."}` |
| Webhook inalcanzable | `RuntimeError: Webhook connection failed: ...` |
| Timeout excedido | `RuntimeError: Webhook timed out after Ns` |

## Notas

- El payload se serializa como JSON con `ensure_ascii=False` (soporta caracteres Unicode/español).
- El User-Agent enviado es `UmbralWorker/0.4.0`.
- La validación de URL es estricta: solo dominios de Make.com están permitidos (seguridad).
- La respuesta del webhook se trunca a 2000 caracteres máximo.
- Referencia: `worker/tasks/make_webhook.py`.
