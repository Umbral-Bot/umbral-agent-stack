---
name: notion-workflow
description: >-
  API de Notion, automatizaciones, templates y workflows via Make/n8n/webhooks
  para consultores. Requiere NOTION_API_KEY.
  Usar cuando: "notion database", "crear pagina notion", "automatizar notion",
  "notion API", "webhook notion", "base de datos notion", "filtrar notion".
metadata:
  openclaw:
    emoji: "\U0001F5C3"
    requires:
      env:
        - NOTION_API_KEY
---

# Notion Workflow — Skill para David Moreira

Rick usa este skill para operar la API de Notion, automatizar flujos de trabajo, construir templates utiles para consultores e integrar Notion con Make/n8n via webhooks.

## Requisitos y configuracion

| Variable | Descripcion |
|---------|------------|
| `NOTION_API_KEY` | Token de integracion de Notion (requerido) |
| `NOTION_CONTROL_ROOM_PAGE_ID` | ID de la pagina Control Room de David |
| `NOTION_GRANOLA_DB_ID` | ID de la base de datos Granola |
| `NOTION_DASHBOARD_PAGE_ID` | ID del dashboard principal |

### Como obtener el NOTION_API_KEY

1. Ir a https://www.notion.so/my-integrations
2. Crear una nueva integracion (nombre: "Rick" o "Umbral Worker")
3. Copiar el "Internal Integration Token"
4. Compartir las bases de datos relevantes con la integracion en Notion

## Conceptos fundamentales de la API

### Jerarquia de objetos

```
Workspace
  └── Page (pagina)
        └── Block (bloque de contenido)
              └── Block hijo (anidado)
  └── Database (base de datos)
        └── Page (fila = pagina con propiedades)
```

### Tipos de objetos principales

| Tipo | Descripcion | Endpoint base |
|------|------------|---------------|
| `page` | Pagina o fila de DB | `/pages` |
| `database` | Base de datos con esquema | `/databases` |
| `block` | Unidad de contenido (texto, imagen, etc.) | `/blocks` |
| `user` | Usuario de Notion | `/users` |

## API: Operaciones con bases de datos

### Consultar una base de datos (filtrar y ordenar)

```python
import requests

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Filtrar filas donde Status = "En progreso" y ordenar por fecha
payload = {
    "filter": {
        "property": "Status",
        "status": {"equals": "En progreso"}
    },
    "sorts": [
        {"property": "Fecha", "direction": "descending"}
    ],
    "page_size": 10
}

response = requests.post(
    f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
    headers=headers,
    json=payload
)
results = response.json().get("results", [])
```

### Crear una nueva fila en una base de datos

```python
payload = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "Name": {
            "title": [{"text": {"content": "Nueva tarea"}}]
        },
        "Status": {
            "status": {"name": "Sin empezar"}
        },
        "Fecha": {
            "date": {"start": "2026-03-04"}
        },
        "Tags": {
            "multi_select": [{"name": "BIM"}, {"name": "Automatizacion"}]
        }
    }
}

response = requests.post(
    "https://api.notion.com/v1/pages",
    headers=headers,
    json=payload
)
```

### Actualizar propiedades de una fila existente

```python
# Solo enviar las propiedades que cambian
payload = {
    "properties": {
        "Status": {"status": {"name": "Completado"}},
        "Resultado": {
            "rich_text": [{"text": {"content": "Tarea completada con exito"}}]
        }
    }
}

response = requests.patch(
    f"https://api.notion.com/v1/pages/{PAGE_ID}",
    headers=headers,
    json=payload
)
```

## API: Operaciones con paginas y bloques

### Crear una pagina hija

```python
payload = {
    "parent": {"page_id": PARENT_PAGE_ID},
    "properties": {
        "title": [{"text": {"content": "Reporte semanal 2026-03-04"}}]
    },
    "children": [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"text": {"content": "Resumen"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Contenido del reporte..."}}]
            }
        }
    ]
}
```

### Tipos de bloques soportados

| Tipo de bloque | Nombre en API |
|---------------|---------------|
| Parrafo | `paragraph` |
| Titulo H1 | `heading_1` |
| Titulo H2 | `heading_2` |
| Titulo H3 | `heading_3` |
| Lista con bullets | `bulleted_list_item` |
| Lista numerada | `numbered_list_item` |
| To-do (checkbox) | `to_do` |
| Toggle | `toggle` |
| Codigo | `code` |
| Callout | `callout` |
| Divider | `divider` |
| Tabla | `table` |
| Imagen | `image` |
| Bookmark (URL) | `bookmark` |

### Agregar bloques a una pagina existente

```python
payload = {
    "children": [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": "Actualizado por Rick — 2026-03-04"}}],
                "icon": {"emoji": "✅"},
                "color": "green_background"
            }
        }
    ]
}

response = requests.patch(
    f"https://api.notion.com/v1/blocks/{BLOCK_ID}/children",
    headers=headers,
    json=payload
)
```

## Automatizaciones nativas de Notion

Notion tiene automatizaciones nativas (sin API externa) disponibles en bases de datos:

### Tipos de triggers disponibles

| Trigger | Descripcion |
|---------|------------|
| Cuando se agrega una pagina | Se ejecuta al crear una nueva fila |
| Cuando una propiedad cambia | Se ejecuta al modificar un campo especifico |
| Cuando una fecha llega | Se ejecuta en una fecha/hora programada |

### Tipos de acciones disponibles

| Accion | Descripcion |
|--------|------------|
| Editar propiedad | Cambiar el valor de un campo |
| Agregar una pagina a... | Crear una entrada en otra base de datos |
| Enviar notificacion Slack | Integra con Slack directamente |
| Enviar email | Notifica por correo a miembros del workspace |

**Limitacion importante**: Las automatizaciones nativas de Notion NO tienen webhook saliente. Para notificar a sistemas externos (Make, n8n, Zapier), se necesita polling o un servicio intermediario.

## Integracion con Make y n8n

### Por que se necesita una capa intermedia

Notion no emite webhooks nativos. El workaround mas confiable es **polling cada N minutos** usando la propiedad `last_edited_time` como marcador de cambios.

### Arquitectura recomendada

```
Notion (base de datos) → n8n/Make (polling cada 1-5 min)
                      → Detecta cambios por last_edited_time
                      → Ejecuta accion externa (Slack, email, Worker)
```

### Configuracion en n8n

**Modulo Notion disponible en n8n**:

1. Instalar n8n (o usar n8n Cloud)
2. Crear credencial Notion con el `NOTION_API_KEY`
3. Usar el nodo "Notion" con operaciones:
   - `Database: Get Many` (listar filas)
   - `Page: Create` (crear pagina)
   - `Page: Update` (actualizar pagina)
   - `Block: Append` (agregar bloques)

**Template n8n: Polling de Notion con filtro**:

```json
{
  "trigger": {"type": "Schedule", "interval": 5, "unit": "minutes"},
  "nodes": [
    {
      "type": "Notion",
      "operation": "Database: Get Many",
      "databaseId": "{{NOTION_DB_ID}}",
      "filter": {
        "last_edited_time": {"after": "{{$now.minus(5, 'minutes')}}"}
      }
    },
    {
      "type": "IF",
      "condition": "{{$json.results.length > 0}}"
    },
    {
      "type": "HTTP Request",
      "url": "http://localhost:8088/enqueue",
      "method": "POST",
      "body": {"task": "notion.upsert_task", "input": "{{$json}}"}
    }
  ]
}
```

### Configuracion en Make (ex Integromat)

1. Crear escenario con modulo "Notion → Watch Database Items"
2. Configurar filtro por `last_edited_time`
3. Conectar con modulo HTTP Request al Worker de Umbral

## Templates de Notion para consultores

### 1. CRM simple para David

**Estructura de la base de datos**:

| Propiedad | Tipo | Descripcion |
|-----------|------|------------|
| Nombre | Title | Nombre del prospecto/cliente |
| Estado | Status | Nuevo / En contacto / Propuesta enviada / Cliente / Perdido |
| Empresa | Text | Nombre de la empresa |
| Servicio | Multi-select | Consultoria BIM / Automatizacion / Formacion / BI |
| Valor estimado | Number | En USD o CLP |
| Fecha proximo contacto | Date | Para seguimiento |
| Notas | Text | Contexto de la relacion |

**Automatizacion nativa sugerida**: Cuando Estado cambia a "Propuesta enviada" → Crear recordatorio en 5 dias.

### 2. Gestor de proyectos BIM

| Propiedad | Tipo | Descripcion |
|-----------|------|------------|
| Proyecto | Title | Nombre del proyecto |
| Cliente | Relation | Enlace al CRM |
| Fase | Status | Diagnostico / Diseno / Implementacion / Cierre |
| Herramientas | Multi-select | Revit / Power Automate / Dynamo / Power BI |
| % Avance | Number | 0-100 |
| Fecha inicio | Date | Inicio del proyecto |
| Fecha entrega | Date | Deadline comprometido |
| Entregables | Files | PDFs, modelos, documentacion |

### 3. Content Calendar LinkedIn

| Propiedad | Tipo | Descripcion |
|-----------|------|------------|
| Titulo | Title | Descripcion del post |
| Formato | Select | Carrusel / Texto / Imagen / Video |
| Pilar | Select | Automatizacion / BIM+IA / Docencia / Marca Personal |
| Estado | Status | Idea / En borrador / Listo / Publicado |
| Fecha publicacion | Date | Cuando publicar |
| Alcance | Number | Impresiones reales del post |
| Engagement | Number | Comentarios + reactions |
| URL post | URL | Link al post publicado |

## Comandos frecuentes del Worker de Umbral para Notion

Estas son las tasks `notion.*` disponibles en el Worker de Umbral (ver skill `notion` para detalle):

| Task | Descripcion |
|------|------------|
| `notion.write_transcript` | Crea pagina con transcript en base de datos Granola |
| `notion.add_comment` | Agrega comentario a una pagina |
| `notion.poll_comments` | Lee comentarios recientes de Control Room |
| `notion.upsert_task` | Crea o actualiza una tarea en la DB de Notion |
| `notion.update_dashboard` | Actualiza el dashboard con metricas |
| `notion.create_report_page` | Crea pagina de reporte con fuentes |

## Errores comunes y soluciones

| Error | Causa | Solucion |
|-------|-------|---------|
| `401 Unauthorized` | Token invalido o vencido | Regenerar token en notion.so/my-integrations |
| `404 Not Found` | ID de pagina/DB incorrecto | Verificar que la integracion tenga acceso a esa pagina |
| `400 validation_error` | Propiedad con formato incorrecto | Revisar tipo de propiedad (title, rich_text, status, etc.) |
| `409 conflict_error` | Actualizacion concurrente | Reintentar despues de 1-2 segundos |
| Sin resultados en query | Integracion no tiene acceso a la DB | Compartir la DB con la integracion en Notion |

## Limitaciones conocidas

- **No hay webhooks nativos**: Notion no envia eventos cuando cambia algo. Requiere polling.
- **Rate limit**: 3 requests por segundo por integracion
- **Linked databases**: No soportadas por la API publica
- **Bases de datos wiki**: No soportadas por la API publica
- **Tiempo de refresh**: `last_edited_time` actualiza con hasta 1 minuto de delay
