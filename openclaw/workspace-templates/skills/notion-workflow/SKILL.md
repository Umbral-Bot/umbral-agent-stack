---
name: notion-workflow
description: >-
  Flujos de trabajo con Notion: API REST (bases de datos, paginas, bloques),
  automatizaciones nativas, integracion con Make/n8n via webhook, templates
  para consultores y comandos frecuentes de la API.
  Use when "notion database", "crear pagina notion", "automatizar notion",
  "notion API", "notion workflow", "base de datos notion", "notion webhook".
metadata:
  openclaw:
    emoji: "\U0001F5C2"
    requires:
      env:
        - NOTION_API_KEY
---

# Notion Workflow — Skill de Automatizacion

Rick usa este skill para interactuar con la API de Notion, construir automatizaciones y ayudar a David a gestionar su workspace de Notion como sistema de operaciones del negocio.

## Requisitos

| Variable | Descripcion | Donde obtener |
|----------|-------------|---------------|
| `NOTION_API_KEY` | Token de integracion de Notion | Settings → My Connections → Develop your own integrations |
| `NOTION_CONTROL_ROOM_PAGE_ID` | ID de la pagina de Control Room | Extraer de la URL de la pagina |
| `NOTION_GRANOLA_DB_ID` | ID de la DB de transcripciones Granola (usa `NOTION_API_KEY` Rick) | Extraer de la URL de la DB |

### Extraer un Page ID o Database ID de la URL

```
https://notion.so/mi-workspace/Nombre-de-Pagina-{PAGE_ID}
https://notion.so/mi-workspace/{DATABASE_ID}?v=...
```

El ID tiene formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (32 caracteres hexadecimales con guiones).

## API de Notion — Referencia Esencial

**Base URL:** `https://api.notion.com/v1/`
**Autenticacion:** `Authorization: Bearer {NOTION_API_KEY}`
**Version header:** `Notion-Version: 2022-06-28`

### Endpoints principales

| Recurso | Metodo | Endpoint | Accion |
|---------|--------|----------|--------|
| Paginas | POST | `/pages` | Crear pagina |
| Paginas | GET | `/pages/{page_id}` | Leer pagina |
| Paginas | PATCH | `/pages/{page_id}` | Actualizar propiedades |
| Bases de datos | POST | `/databases` | Crear base de datos |
| Bases de datos | GET | `/databases/{database_id}` | Leer esquema |
| Bases de datos | POST | `/databases/{database_id}/query` | Consultar entradas |
| Bloques | GET | `/blocks/{block_id}/children` | Leer bloques hijo |
| Bloques | PATCH | `/blocks/{block_id}/children` | Agregar bloques |
| Busqueda | POST | `/search` | Buscar en workspace |
| Usuarios | GET | `/users` | Listar usuarios |

## Crear una Pagina en Notion

### Dentro de una pagina padre

```json
POST /v1/pages
{
  "parent": { "page_id": "PARENT_PAGE_ID" },
  "properties": {
    "title": {
      "title": [{ "text": { "content": "Titulo de la pagina" } }]
    }
  },
  "children": [
    {
      "object": "block",
      "type": "paragraph",
      "paragraph": {
        "rich_text": [{ "text": { "content": "Contenido inicial de la pagina." } }]
      }
    }
  ]
}
```

### Dentro de una base de datos

```json
POST /v1/pages
{
  "parent": { "database_id": "DATABASE_ID" },
  "properties": {
    "Nombre": {
      "title": [{ "text": { "content": "Nueva tarea" } }]
    },
    "Estado": {
      "select": { "name": "Pendiente" }
    },
    "Fecha": {
      "date": { "start": "2026-03-04" }
    }
  }
}
```

## Consultar una Base de Datos

### Query basica con filtro

```json
POST /v1/databases/{DATABASE_ID}/query
{
  "filter": {
    "property": "Estado",
    "select": { "equals": "Pendiente" }
  },
  "sorts": [
    { "property": "Fecha", "direction": "ascending" }
  ],
  "page_size": 20
}
```

### Filtros combinados (AND / OR)

```json
{
  "filter": {
    "and": [
      { "property": "Estado", "select": { "equals": "En progreso" } },
      { "property": "Responsable", "people": { "contains": "USER_ID" } }
    ]
  }
}
```

### Tipos de filtro disponibles

| Tipo de propiedad | Filtro |
|------------------|--------|
| Texto | `"rich_text": { "contains": "valor" }` |
| Numero | `"number": { "greater_than": 100 }` |
| Select | `"select": { "equals": "opcion" }` |
| Checkbox | `"checkbox": { "equals": true }` |
| Fecha | `"date": { "on_or_after": "2026-01-01" }` |
| Relacion | `"relation": { "contains": "PAGE_ID" }` |

## Agregar Bloques a una Pagina Existente

```json
PATCH /v1/blocks/{BLOCK_ID}/children
{
  "children": [
    {
      "object": "block",
      "type": "heading_2",
      "heading_2": {
        "rich_text": [{ "text": { "content": "Nueva seccion" } }]
      }
    },
    {
      "object": "block",
      "type": "bulleted_list_item",
      "bulleted_list_item": {
        "rich_text": [{ "text": { "content": "Elemento de lista" } }]
      }
    },
    {
      "object": "block",
      "type": "code",
      "code": {
        "rich_text": [{ "text": { "content": "print('Hola Notion')" } }],
        "language": "python"
      }
    }
  ]
}
```

### Tipos de bloques disponibles

| Tipo | Descripcion |
|------|-------------|
| `paragraph` | Texto normal |
| `heading_1/2/3` | Titulos H1, H2, H3 |
| `bulleted_list_item` | Lista con viñeta |
| `numbered_list_item` | Lista numerada |
| `to_do` | Checkbox |
| `toggle` | Toggle/desplegable |
| `code` | Bloque de codigo |
| `quote` | Cita |
| `divider` | Linea divisoria |
| `callout` | Recuadro destacado |
| `image` | Imagen (via URL) |
| `table` | Tabla (con `table_row` hijos) |

## Automatizaciones Nativas de Notion

### Automatizaciones disponibles (sin API externa)

Notion ofrece automatizaciones nativas en bases de datos:

| Disparador | Accion disponible |
|-----------|------------------|
| Cuando se crea una pagina | Asignar propiedad, agregar a DB, enviar a Slack |
| Cuando cambia una propiedad | Actualizar otra propiedad, cambiar estado |
| Cuando llega una fecha | Notificacion, cambio de estado |
| Periodicamente | Crear pagina recurrente (ej: reunion semanal) |

### Configurar una automatizacion nativa

1. Abrir una base de datos en Notion
2. Click en `...` (menu superior derecho) → Automatize
3. Seleccionar disparador (trigger)
4. Seleccionar accion
5. Guardar

## Integracion con Make (ex Integromat)

### Webhook desde Notion a Make

```
Notion DB (cambio de estado)
    → Notion trigger en Make
    → Filtro: Estado = "Completado"
    → Accion: Enviar email / Crear tarea en Linear / Postear en Slack
```

### Modulos de Notion en Make

| Modulo | Descripcion |
|--------|-------------|
| Watch Database Items | Detecta cambios en una DB |
| Create a Page | Crea pagina o entrada en DB |
| Update a Page | Actualiza propiedades |
| Search Objects | Busca paginas o DBs |
| Get a Page | Obtiene contenido de pagina |
| Append a Block | Agrega bloques a pagina |

### Autenticacion en Make

1. En Make: Connections → Add → Notion
2. Autorizar con tu cuenta de Notion
3. La integracion se instala como una conexion reutilizable

## Integracion con n8n

### Nodo de Notion en n8n

n8n tiene un nodo nativo de Notion con estas operaciones:

**Database:**
- Get Many, Search

**Database Pages (entradas de DB):**
- Create, Get, Get Many, Update

**Blocks:**
- Get Child Blocks, Append After Block

**Pages:**
- Archive, Create, Get, Search, Update

### Ejemplo de workflow n8n

```
Webhook (POST externo)
    → Set node (extraer datos)
    → Notion: Create Database Page
        parent: { database_id: "DB_ID" }
        properties: { Nombre: webhook.body.nombre, Estado: "Nuevo" }
    → Slack: Notificar
```

### Autenticacion n8n con Notion

1. En n8n: Credentials → Add Credential → Notion API
2. Pegar el `NOTION_API_KEY` del integration token
3. Asegurarse de que la integracion tenga acceso a las paginas necesarias (Share en Notion)

## Templates Utiles para Consultores

### Template 1: Kanban de proyectos

Base de datos con propiedades:
- `Nombre` (title)
- `Cliente` (text)
- `Estado` (select: Propuesta / En progreso / Completado / Pausado)
- `Valor` (number)
- `Fecha inicio` (date)
- `Fecha entrega` (date)
- `Responsable` (person)
- `Notas` (text)

Vista: Kanban agrupado por `Estado`

### Template 2: CRM simple para consultor

Base de datos con propiedades:
- `Empresa` (title)
- `Contacto` (text)
- `Email` (email)
- `Etapa` (select: Lead / Reunion / Propuesta / Contrato / Inactivo)
- `Valor estimado` (number)
- `Ultimo contacto` (date)
- `Siguiente accion` (text)
- `Origen` (select: LinkedIn / Referencia / Web / Evento)

Automatizacion: Cuando `Etapa` cambia a "Propuesta" → agregar fecha en `Ultimo contacto`

### Template 3: Control Room Rick-David

Base de datos para tareas del agente:
- `Tarea` (title)
- `Tipo` (select: ping / notion.* / research.web / llm.generate)
- `Estado` (select: Pendiente / En progreso / Completado / Error)
- `Input` (text)
- `Resultado` (text)
- `Fecha` (date)
- `Task ID` (text)

## Comandos Frecuentes (Python con requests)

```python
import os, requests

API_KEY = os.environ["NOTION_API_KEY"]
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_database(db_id, filter_obj=None, sorts=None):
    payload = {}
    if filter_obj:
        payload["filter"] = filter_obj
    if sorts:
        payload["sorts"] = sorts
    r = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=HEADERS, json=payload
    )
    r.raise_for_status()
    return r.json()["results"]

def create_page(parent_id, is_db, title, extra_props=None):
    parent = {"database_id": parent_id} if is_db else {"page_id": parent_id}
    props = {"title": {"title": [{"text": {"content": title}}]}} if not is_db else {
        "Nombre": {"title": [{"text": {"content": title}}]}
    }
    if extra_props:
        props.update(extra_props)
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS, json={"parent": parent, "properties": props}
    )
    r.raise_for_status()
    return r.json()

def append_blocks(block_id, blocks):
    r = requests.patch(
        f"https://api.notion.com/v1/blocks/{block_id}/children",
        headers=HEADERS, json={"children": blocks}
    )
    r.raise_for_status()
    return r.json()
```

## Troubleshooting Comun

| Error | Causa | Solucion |
|-------|-------|----------|
| `401 Unauthorized` | Token invalido o expirado | Verificar `NOTION_API_KEY` en la integracion |
| `404 Not Found` | La pagina no fue compartida con la integracion | Share la pagina con la integracion en Notion |
| `400 validation_error` | Propiedad no existe en el esquema de la DB | Verificar nombres exactos de propiedades |
| `409 conflict_error` | Actualizacion concurrente | Retry con backoff exponencial |
| `429 rate_limited` | Demasiadas requests | Respetar 3 req/seg; agregar `time.sleep(0.35)` |

## Limites de la API

| Limite | Valor |
|--------|-------|
| Rate limit | 3 requests/segundo por integracion |
| Tamano maximo de request | 1000 bloques por request |
| Profundidad de bloques | 3 niveles maximos via API |
| Tamano de DB recomendado | <50KB para performance optima |
| Paginacion | Cursor-based; `page_size` max 100 |
