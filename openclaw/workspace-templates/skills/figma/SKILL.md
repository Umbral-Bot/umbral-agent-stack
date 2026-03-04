---
name: figma
description: >-
  Interact with Figma REST API via Umbral Worker tasks to read file structures,
  export layers and components as images, and manage design comments.
  Use when "read figma file", "export figma frame", "figma comments",
  "check figma design", "get figma assets", "review design in figma".
metadata:
  openclaw:
    emoji: "\U0001F4D0"
    requires:
      env:
        - FIGMA_API_KEY
---

# Figma Skill

Rick puede interactuar con archivos de Figma a través de las Worker tasks del Umbral Agent Stack.

## Requisitos

- `FIGMA_API_KEY`: Personal Access Token de Figma (Settings → Security).
- El `file_key` se extrae de la URL: `figma.com/design/{file_key}/...`

## Tasks disponibles

### 1. Leer estructura de archivo

Task: `figma.get_file`

```json
{"file_key": "abc123XYZ", "depth": 2}
```

Devuelve: nombre del archivo, páginas, metadata, thumbnail.

### 2. Leer nodos específicos

Task: `figma.get_node`

```json
{"file_key": "abc123XYZ", "node_ids": ["1:2", "3:4"], "depth": 2}
```

Devuelve: detalle de cada nodo (nombre, tipo, hijos).

### 3. Exportar imagen

Task: `figma.export_image`

```json
{"file_key": "abc123XYZ", "node_ids": ["1:2"], "format": "png", "scale": 2}
```

Formatos: `png`, `svg`, `jpg`, `pdf`. Escala: 0.01–4.
Devuelve: URLs temporales de descarga de S3.

### 4. Agregar comentario

Task: `figma.add_comment`

```json
{"file_key": "abc123XYZ", "message": "Revisar este componente", "node_id": "1:2"}
```

### 5. Listar comentarios

Task: `figma.list_comments`

```json
{"file_key": "abc123XYZ"}
```

Devuelve: lista con id, mensaje, autor, fecha, estado de resolución.

## Notas

- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- La API de Figma tiene rate limit de 60 req/min.
- Figma API es de lectura; no puede crear ni modificar nodos de diseño.
