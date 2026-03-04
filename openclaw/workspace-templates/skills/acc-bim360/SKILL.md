---
name: acc-bim360
description: >-
  API de Autodesk Construction Cloud (ACC) y BIM 360 para gestión de issues,
  RFIs, submittals, documentos y modelos en la nube mediante APS.
  Use when "ACC", "BIM360", "BIM 360", "Autodesk Construction Cloud",
  "issues ACC", "RFI BIM360", "submittals", "ACC API", "APS construction",
  "documentos ACC", "Autodesk Build", "ACC project", "BIM360 docs".
metadata:
  openclaw:
    emoji: "\U0001F3D7\uFE0F"
    requires:
      env:
        - APS_CLIENT_ID
        - APS_CLIENT_SECRET
---

# ACC / BIM 360 Skill — Autodesk Construction Cloud API

Rick usa este skill para interactuar con la API de Autodesk Construction Cloud (ACC) y BIM 360: issues, RFIs, submittals, documentos y gestión de proyectos.

## Plataformas y productos

| Producto | Descripción |
|----------|-------------|
| **ACC (Autodesk Construction Cloud)** | Plataforma unificada: Build, Design, Cost, Ops |
| **Autodesk Build** | Gestión de campo: issues, RFIs, submittals, Daily Logs |
| **BIM 360 Docs** | Gestión documental (migrado a ACC) |
| **BIM 360 Design** | Colaboración de diseño con Revit (BIM Collaborate) |
| **APS (Autodesk Platform Services)** | Layer de APIs que expone ACC/BIM360 |

## Autenticación — OAuth 2.0

### 2-Legged (Server-to-Server)

```python
import requests, os

def get_2legged_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        "https://developer.api.autodesk.com/authentication/v2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "data:read data:write account:read"
        }
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

TOKEN = get_2legged_token(
    os.environ["APS_CLIENT_ID"],
    os.environ["APS_CLIENT_SECRET"]
)
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
```

### 3-Legged (User OAuth)

Para operaciones en nombre de un usuario:
- Redirect URL: `https://developer.api.autodesk.com/authentication/v2/authorize`
- Scopes requeridos: `data:read data:write account:read`
- Callback → intercambiar code por access_token + refresh_token

## Data Management — Proyectos y Hubs

```python
BASE = "https://developer.api.autodesk.com"

# Listar hubs (BIM 360 cuentas / ACC orgs)
hubs = requests.get(f"{BASE}/project/v1/hubs", headers=HEADERS).json()

# Listar proyectos de un hub
hub_id = hubs["data"][0]["id"]
projects = requests.get(f"{BASE}/project/v1/hubs/{hub_id}/projects", headers=HEADERS).json()

# Listar contenidos de una carpeta (top-level)
project_id = projects["data"][0]["id"]
top_folder = requests.get(
    f"{BASE}/project/v1/hubs/{hub_id}/projects/{project_id}/topFolders",
    headers=HEADERS
).json()
```

## Issues API (ACC Issues v2)

### Listar issues

```python
# ACC Issues v2
project_id = "b.xxx"  # Sin prefijo "b."

issues = requests.get(
    f"https://developer.api.autodesk.com/construction/issues/v2/projects/{project_id}/issues",
    headers=HEADERS,
    params={"limit": 100, "status": "open"}
).json()

for issue in issues.get("results", []):
    print(f"[{issue['displayId']}] {issue['title']} | Status: {issue['status']}")
```

### Crear issue

```python
new_issue = requests.post(
    f"https://developer.api.autodesk.com/construction/issues/v2/projects/{project_id}/issues",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "title": "Viga no coincide con plano",
        "description": "Discrepancia en nivel 3 eje C-5",
        "status": "open",
        "issueTypeId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "issueSubtypeId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "dueDate": "2026-04-15",
        "assignedTo": "user@example.com"
    }
).json()

print(f"Issue creado: {new_issue['displayId']}")
```

## RFI API v3 (ACC Build)

La API RFI v3 reemplaza a la consolidada BIM 360 RFI API.

### Buscar RFIs

```python
# POST /search:rfis (nueva sintaxis v3)
rfis = requests.post(
    f"https://developer.api.autodesk.com/construction/rfis/v3/projects/{project_id}/rfis/search",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "filter": {
            "status": ["open", "answered"],
            "discipline": ["Structural"]
        },
        "pagination": {"limit": 50, "offset": 0}
    }
).json()

for rfi in rfis.get("results", []):
    print(f"RFI {rfi['number']}: {rfi['title']} | Estado: {rfi['status']}")
    print(f"  Asignados: {[a['name'] for a in rfi.get('assignedTo', [])]}")
```

### Crear RFI

```python
new_rfi = requests.post(
    f"https://developer.api.autodesk.com/construction/rfis/v3/projects/{project_id}/rfis",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "title": "Aclaración especificación hormigón",
        "question": "¿Cuál es la resistencia de diseño para fundaciones?",
        "status": "draft",
        "assignedTo": [{"userId": "xxx", "roleId": "projectCoordinator"}],
        "dueDate": "2026-04-01",
        "discipline": "Structural"
    }
).json()
```

## Submittals API

### Listar submittals

```python
submittals = requests.get(
    f"https://developer.api.autodesk.com/construction/submittals/v2/projects/{project_id}/items",
    headers=HEADERS
).json()

for item in submittals.get("results", []):
    print(f"Submittal {item['number']}: {item['title']} | Estado: {item['status']}")
```

### Crear submittal item

```python
new_submittal = requests.post(
    f"https://developer.api.autodesk.com/construction/submittals/v2/projects/{project_id}/items",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "title": "Muestra pintura fachada",
        "specSectionNumber": "09900",
        "specSectionTitle": "Pintura",
        "dueDate": "2026-03-20",
        "assignedToId": "user-uuid"
    }
).json()
```

## Document Management — Subir archivo

```python
# 1. Crear storage location
storage = requests.post(
    f"{BASE}/data/v1/projects/{project_id}/storage",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "jsonapi": {"version": "1.0"},
        "data": {
            "type": "objects",
            "attributes": {"name": "planos_estructura.pdf"},
            "relationships": {
                "target": {"data": {"type": "folders", "id": folder_id}}
            }
        }
    }
).json()

object_id = storage["data"]["id"]
upload_url = storage["data"]["links"]["upload"]["href"]

# 2. Upload con PUT
with open("planos_estructura.pdf", "rb") as f:
    requests.put(upload_url, data=f)

# 3. Crear versión del ítem
# ... (POST /data/v1/projects/{id}/items)
```

## Modelos y Viewer (Model Derivative)

```python
# Traducir modelo a SVF2 para Viewer
urn = "dXJuOmFkc2sub2JqZWN0czpvcy5vYmplY3Q6..."  # Base64 del object ID

translation = requests.post(
    f"{BASE}/modelderivative/v2/designdata/job",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={
        "input": {"urn": urn},
        "output": {
            "formats": [{"type": "svf2", "views": ["2d", "3d"]}]
        }
    }
).json()

# Verificar estado
status = requests.get(
    f"{BASE}/modelderivative/v2/designdata/{urn}/manifest",
    headers=HEADERS
).json()
print(status["progress"])
```

## Scopes por operación

| Operación | Scopes requeridos |
|-----------|------------------|
| Listar proyectos | `data:read` |
| Crear issue | `data:write` |
| Leer documentos | `data:read` |
| Subir archivos | `data:write` |
| Ver info de cuenta | `account:read` |
| Traducir modelos | `data:read data:write` |

## Ejemplos de uso con Rick

- **Rick: "Listame todos los issues abiertos de un proyecto ACC"** → Issues v2 API con `status=open`.
- **Rick: "Creá un RFI en BIM 360 desde una observación de campo"** → POST `/construction/rfis/v3/projects/{id}/rfis`.
- **Rick: "Cuántos submittals están pendientes de revisión?"** → GET submittals, filtrar por `status=pending_review`.
- **Rick: "Subí este PDF a la carpeta de planos en ACC Docs"** → Storage + PUT upload + crear item versión.
- **Rick: "Traducí el RVT a SVF2 para visualizarlo en el Viewer"** → Model Derivative API job.

## Recursos oficiales

- APS Developer Portal: https://aps.autodesk.com/developer/overview/bim-360
- ACC Issues v2 API: https://aps.autodesk.com/en/docs/acc/v1/reference/http/issues-v2/
- ACC RFI v3 API: https://aps.autodesk.com/blog/autodesk-build-rfi-v3-api-released
- ACC Submittals API: https://aps.autodesk.com/blog/autodesk-construction-cloud-submittals-write-api-and-updates
- Data Management API: https://aps.autodesk.com/en/docs/data/v2/

## Notas

- `project_id` siempre tiene prefijo `b.` en proyectos BIM 360/ACC (e.g. `b.abc123`).
- La API RFI v3 usa `POST /search:rfis` en lugar de `GET /rfis` de la API anterior.
- Los tokens 2-legged expiran en 3600s; implementar refresh automático.
- BIM 360 Docs está siendo migrado a ACC; usar APIs ACC cuando sea posible.
- `APS_CLIENT_ID` y `APS_CLIENT_SECRET` se obtienen en https://aps.autodesk.com/myapps/.
