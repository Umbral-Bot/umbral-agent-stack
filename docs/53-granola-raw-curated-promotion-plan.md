# 53 - Granola raw -> curado -> destino

> Plan de implementación para llevar el intake real de Granola al stack de Rick sin mezclar la capa raw con la capa humana curada.

## 1. Objetivo

Implementar un flujo compatible con la realidad operativa actual:

- **hoy**: David copia manualmente notas desde Granola y las capitaliza con Notion AI
- **objetivo**: Rick automatiza el intake raw y luego promueve selectivamente a la capa curada y a los destinos operativos

## 2. Capas

### 2.1 Raw

Owner: Rick  
Superficie: `NOTION_GRANOLA_DB_ID`

Contenido esperado:

- título
- contenido bruto de la reunión
- fecha
- fuente
- attendees si existen
- action items si existen
- timestamps de importación/procesamiento

### 2.2 Curado

Owner: David  
Superficie: DB humana de sesiones/transcripciones

Contenido esperado:

- dominio
- tipo
- programa o proyecto relacionado
- fecha
- URL fuente
- recurso relacionado
- transcripción disponible
- notas

### 2.3 Destino

Superficies:

- proyectos
- tareas
- recursos
- follow-ups

## 3. Componentes a implementar

### 3.1 Exporter de cache

Entrada:

- `%APPDATA%\Granola\cache-v6.json`

Responsabilidad:

- leer documentos nuevos o modificados
- convertir ProseMirror JSON a Markdown
- generar `.md` en `GRANOLA_EXPORT_DIR`

No debe:

- escribir directo en la DB curada
- decidir por sí solo relaciones complejas

### 3.2 Watcher existente

Reutilizar `scripts/vm/granola_watcher.py`.

### 3.3 Worker existente

Reutilizar:

- `granola.process_transcript`
- `granola.create_followup`

## 4. Regla de promoción

Promover de raw a curado solo cuando:

- el dominio sea claro
- exista programa o proyecto identificable
- la reunión tenga valor de trazabilidad
- no sea duplicado obvio

Promover de curado a destino solo cuando:

- haya action items claros
- haya impacto operativo real
- exista una actualización concreta para proyecto, tarea o recurso

## 5. Lotes sugeridos

### Lote 1

- 3 a 5 reuniones claras
- foco en baja ambigüedad
- validar exporter + watcher + DB raw

### Lote 2

- promoción manual o semi-asistida a la capa curada

### Lote 3

- follow-ups y tareas derivadas

## 6. Riesgos

- asumir que toda nota de Granola es transcripción
- contaminar la DB curada con intake bruto
- crear tareas desde reuniones ambiguas
- perder trazabilidad entre raw y curado
- automatizar antes de tener codec ProseMirror -> Markdown estable

## 7. Siguiente paso recomendado

1. implementar `granola_cache_exporter.py`
2. validar un lote pequeño hacia la DB raw de Rick
3. recién después diseñar la promoción automatizada o semi-automatizada a la capa curada
