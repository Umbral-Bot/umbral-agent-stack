# 07 — Worker API Contract

## Base URL

```
http://WINDOWS_TAILSCALE_IP:8088
```

## Endpoints

---

### `GET /health`

Health check. No requiere autenticación.

**Request:**
```
GET /health HTTP/1.1
```

**Response (200):**
```json
{
  "ok": true,
  "ts": 1740600000
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ok` | bool | Siempre `true` si el worker está operativo |
| `ts` | int | Unix timestamp del servidor |

---

### `POST /run`

Ejecuta una tarea. Requiere autenticación Bearer.

**Request:**
```
POST /run HTTP/1.1
Content-Type: application/json
Authorization: Bearer <WORKER_TOKEN>
```

**Body:**
```json
{
  "task": "ping",
  "input": {}
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `task` | string | ✅ | Nombre de la tarea a ejecutar |
| `input` | object | ✅ | Datos de entrada para la tarea |

**Response (200) — Tarea `ping`:**
```json
{
  "ok": true,
  "task": "ping",
  "result": {
    "echo": {
      "task": "ping",
      "input": {}
    }
  }
}
```

---

## Tareas Disponibles

| Task | Descripción | Input |
|------|-------------|-------|
| `ping` | Echo de prueba | `{}` (cualquier input) |

> Más tareas se agregarán en futuras fases. El worker usa un diccionario de handlers extensible.

---

## Errores

### 401 Unauthorized

```json
{
  "detail": "Invalid or missing token"
}
```

**Causa**: Falta el header `Authorization: Bearer <token>` o el token no coincide.

### 500 Internal Server Error

```json
{
  "detail": "WORKER_TOKEN not configured on server"
}
```

**Causa**: La variable de entorno `WORKER_TOKEN` no está definida en el proceso del worker.

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "task"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Causa**: El body JSON es inválido o le faltan campos requeridos (`task`, `input`).

---

## Ejemplos curl

### Desde bash (VPS)

```bash
# Health check
curl http://WINDOWS_TAILSCALE_IP:8088/health

# Run — IMPORTANTE: usar comillas simples si el token contiene "!"
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer CHANGE_ME_WORKER_TOKEN' \
  -d '{"task":"ping","input":{"msg":"hello"}}'
```

### Desde PowerShell (Windows)

```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8088/health

# Run
$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer CHANGE_ME_WORKER_TOKEN"
}
$body = '{"task":"ping","input":{"msg":"hello"}}'
Invoke-RestMethod -Uri http://localhost:8088/run -Method POST -Headers $headers -Body $body
```
