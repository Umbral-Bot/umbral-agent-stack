---
name: acc-bim360
description: >-
  Autodesk Construction Cloud (ACC) y BIM 360 API via APS (Autodesk Platform Services):
  gestión de proyectos, issues, RFIs, submittals, archivos y reportes de coordinación.
  Use when "ACC", "BIM 360", "Autodesk Construction Cloud", "APS API", "BIM360 issues",
  "RFI BIM360", "ACC API", "Forge BIM360", "archivos ACC", "submittals ACC".
metadata:
  openclaw:
    emoji: "\U0001F3D7\uFE0F"
    requires:
      env:
        - APS_CLIENT_ID
        - APS_CLIENT_SECRET
---

# ACC / BIM 360 Skill — Autodesk Platform Services API

Rick usa este skill para interactuar con la API de Autodesk Construction Cloud (ACC) y BIM 360 via APS (antes llamado Forge), incluyendo gestión de issues, RFIs, archivos y reportes.

## Autenticación APS

### Credenciales requeridas

- `APS_CLIENT_ID`: Client ID de la app registrada en APS portal
- `APS_CLIENT_SECRET`: Client Secret correspondiente

### Obtener token 2-legged (Client Credentials)

```python
import requests

def get_token_2legged(client_id: str, client_secret: str) -> str:
    url = "https://developer.api.autodesk.com/authentication/v2/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials",
        "scope": "data:read data:write bucket:read bucket:create"
    }, auth=(client_id, client_secret))
    resp.raise_for_status()
    return resp.json()["access_token"]

token = get_token_2legged(APS_CLIENT_ID, APS_CLIENT_SECRET)
headers = {"Authorization": f"Bearer {token}"}
```

### Token 3-legged (Authorization Code — requiere usuario)

```
1. Redirigir usuario a:
   https://developer.api.autodesk.com/authentication/v2/authorize
   ?response_type=code
   &client_id={CLIENT_ID}
   &redirect_uri={CALLBACK_URL}
   &scope=data:read data:write

2. Recibir code en callback
3. POST a /authentication/v2/token con grant_type=authorization_code
```

## Data Management API — Archivos y Hubs

### Listar hubs (cuentas)

```python
resp = requests.get(
    "https://developer.api.autodesk.com/project/v1/hubs",
    headers=headers
)
hubs = resp.json()["data"]
for hub in hubs:
    print(f"Hub: {hub['attributes']['name']} — ID: {hub['id']}")
```

### Listar proyectos de un hub

```python
hub_id = "b.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
resp = requests.get(
    f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects",
    headers=headers
)
projects = resp.json()["data"]
```

### Listar contenido de una carpeta

```python
project_id = "b.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
folder_urn = "urn:adsk.wipprod:fs.folder:co.xxxxxxxx"

resp = requests.get(
    f"https://developer.api.autodesk.com/data/v1/projects/{project_id}"
    f"/folders/{folder_urn}/contents",
    headers=headers
)
items = resp.json()["data"]
for item in items:
    print(f"{item['type']}: {item['attributes']['displayName']}")
```

### Subir archivo a ACC

```python
import base64

# 1. Crear storage location (OSS)
resp = requests.post(
    f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/storage",
    headers={**headers, "Content-Type": "application/vnd.api+json"},
    json={
        "jsonapi": {"version": "1.0"},
        "data": {
            "type": "objects",
            "attributes": {"name": "modelo.rvt"},
            "relationships": {
                "target": {
                    "data": {"type": "folders", "id": folder_urn}
                }
            }
        }
    }
)
object_id = resp.json()["data"]["id"]

# 2. Subir contenido al OSS bucket
bucket_key, object_name = object_id.split(":")[-1].split("/", 1)
with open("modelo.rvt", "rb") as f:
    requests.put(
        f"https://developer.api.autodesk.com/oss/v2/buckets/{bucket_key}/objects/{object_name}",
        headers={**headers, "Content-Type": "application/octet-stream"},
        data=f
    )
```

## Issues API (ACC)

### Listar issues de un proyecto

```python
project_id_acc = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # sin prefijo "b."

resp = requests.get(
    f"https://developer.api.autodesk.com/construction/issues/v1/projects/{project_id_acc}/issues",
    headers=headers,
    params={
        "limit": 100,
        "offset": 0,
        "filter[status]": "open"  # open, in_review, closed
    }
)
issues = resp.json()["results"]
for issue in issues:
    print(f"Issue #{issue['displayId']}: {issue['title']} — {issue['status']}")
```

### Crear un issue

```python
resp = requests.post(
    f"https://developer.api.autodesk.com/construction/issues/v1/projects/{project_id_acc}/issues",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "title": "Clash entre estructura y ducto HVAC - Nivel 3",
        "description": "Viga V-305 intersecta con ducto de ventilación DAL-12",
        "status": "open",
        "issueTypeId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "issueSubtypeId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "dueDate": "2025-04-30",
        "assignedTo": "user@empresa.com",
        "rootCauseId": None
    }
)
new_issue = resp.json()
print(f"Issue creado: #{new_issue['displayId']}")
```

### Actualizar estado de issue

```python
issue_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
resp = requests.patch(
    f"https://developer.api.autodesk.com/construction/issues/v1/projects/{project_id_acc}/issues/{issue_id}",
    headers={**headers, "Content-Type": "application/json"},
    json={"status": "closed"}
)
```

## RFIs API (ACC)

### Listar RFIs

```python
resp = requests.get(
    f"https://developer.api.autodesk.com/construction/rfis/v1/projects/{project_id_acc}/rfis",
    headers=headers,
    params={"limit": 50, "filter[status]": "open"}
)
rfis = resp.json()["results"]
for rfi in rfis:
    print(f"RFI #{rfi['displayId']}: {rfi['title']} — Due: {rfi['dueDate']}")
```

### Crear RFI

```python
resp = requests.post(
    f"https://developer.api.autodesk.com/construction/rfis/v1/projects/{project_id_acc}/rfis",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "title": "Aclaración de detalle de armadura en losa L-12",
        "question": "¿Cuál es el diámetro de barras longitudinales en losa L-12, ejes D-E/3-4?",
        "dueDate": "2025-04-15",
        "assignedTo": "estructura@empresa.com",
        "locationId": None
    }
)
```

## Webhooks — Notificaciones en tiempo real

```python
# Crear webhook para notificación de nuevo issue
resp = requests.post(
    "https://developer.api.autodesk.com/webhooks/v1/systems/construction/events/issues.created/hooks",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "callbackUrl": "https://mi-servidor.com/webhook/issues",
        "scope": {
            "project": f"b.{project_id_acc}"
        }
    }
)
```

## Endpoints clave por módulo

| Módulo | Endpoint base |
|--------|--------------|
| Autenticación | `/authentication/v2/token` |
| Hubs y proyectos | `/project/v1/hubs/{hub_id}/projects` |
| Data Management | `/data/v1/projects/{proj_id}/...` |
| Issues | `/construction/issues/v1/projects/{proj_id}/issues` |
| RFIs | `/construction/rfis/v1/projects/{proj_id}/rfis` |
| Submittals | `/construction/submittals/v1/projects/{proj_id}/...` |
| Transmittals | `/construction/transmittals/v1/projects/{proj_id}/...` |
| Reportes | `/construction/reports/v1/projects/{proj_id}/...` |
| Webhooks | `/webhooks/v1/systems/construction/events/...` |

## Scopes de OAuth requeridos

| Acción | Scope |
|--------|-------|
| Leer archivos | `data:read` |
| Subir archivos | `data:write` |
| Leer/escribir issues | `data:read data:write` |
| Administrar proyectos | `account:read account:write` |
| Webhooks | `data:read` |

## Errores comunes

| Error HTTP | Causa | Solución |
|-----------|-------|----------|
| `401 Unauthorized` | Token expirado o inválido | Renovar token (expira en 3600s) |
| `403 Forbidden` | Falta scope o acceso | Verificar scopes del token y permisos del usuario |
| `404 Not Found` | ID de proyecto/folder incorrecto | Verificar IDs con list endpoints |
| `429 Too Many Requests` | Rate limit superado | Implementar backoff exponencial |

## Links oficiales

- [APS Developer Portal](https://aps.autodesk.com/) — Registro de apps y documentación
- [APS BIM 360 Overview](https://aps.autodesk.com/developer/overview/bim-360) — Guía de integración
- [APS API Reference](https://aps.autodesk.com/en/docs/acc/v1/reference/http/) — Referencia completa ACC
- [Data Management API](https://aps.autodesk.com/en/docs/data/v2/reference/http/) — Archivos y carpetas
- [Issues API](https://aps.autodesk.com/en/docs/acc/v1/reference/http/construction-issues-v1-issues-GET/) — Issues ACC
