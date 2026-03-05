---
name: ping
description: >-
  Health check del Worker API. Devuelve pong con timestamp para verificar
  conectividad y latencia. Usa cuando necesites "ping", "health check",
  "verificar Worker", "comprobar conexión", "¿está vivo el worker?".
metadata:
  openclaw:
    emoji: "🏓"
    requires:
      env:
        - WORKER_TOKEN
---

# Ping

Task de health check básico del Worker. Retorna `"pong"` con timestamp para verificar que la API está activa y respondiendo.

## Worker Task

`ping`

## Parámetros

Ninguno requerido. Acepta un `input` vacío `{}`.

## Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `message` | string | `"pong"` |
| `timestamp` | string | ISO 8601 del momento de respuesta |

## Ejemplo

```json
{
  "task": "ping",
  "input": {}
}
```

Respuesta:

```json
{
  "status": "ok",
  "result": {
    "message": "pong",
    "timestamp": "2026-03-04T12:00:00Z"
  }
}
```
