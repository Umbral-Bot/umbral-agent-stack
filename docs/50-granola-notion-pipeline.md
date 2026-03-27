# Granola -> Notion Pipeline

> Documento de diseño del pipeline de reuniones de Granola para Rick. Este flujo debe convivir con el modo manual actual de David y evolucionar hacia una arquitectura estable `raw -> curado -> destino`.

## 0. Resumen ejecutivo

Hoy coexisten dos modos:

1. **Modo actual manual**
   - David copia manualmente la nota desde Granola.
   - La pega a Notion AI.
   - Si la reunión impacta operación, capitaliza en `Asesorías & Proyectos`.

2. **Modo objetivo con Rick**
   - Rick lee el raw de Granola.
   - Lo guarda en una DB raw exclusiva (`NOTION_GRANOLA_DB_ID`).
   - Solo después promueve lo relevante a la capa curada humana y a los destinos operativos.

La decisión de arquitectura es:

- **Raw**: DB exclusiva de Rick en Notion (`NOTION_GRANOLA_DB_ID`)
- **Curado**: DB humana separada de sesiones/transcripciones clasificadas
- **Destino**: proyectos, tareas, recursos y follow-ups

Rick no debe escribir directamente a la DB curada humana como intake bruto.

## 1. Hallazgos actuales de Granola

### 1.1 Realidad observada en marzo 2026

- El cache observado en Windows fue `%APPDATA%\Granola\cache-v6.json`
- La estructura observada fue `cache.state.documents`
- Había 41 reuniones en el cache local
- El contenido principal estaba en **ProseMirror JSON**
- `notes_markdown` estaba vacío
- Varias reuniones no tenían transcripción de audio; eran notas de reunión estructuradas

Implicancia:

- Granola no debe modelarse solo como "pipeline de transcript"
- el intake real es **notas o transcripciones**, según disponibilidad
- hace falta un exportador previo a Markdown para reutilizar el watcher actual

### 1.2 Capacidades relevantes

| Característica | Estado |
|---|---|
| Notas de reunión | Sí |
| Transcripción de audio | Parcial / depende del caso |
| Export automático nativo a carpeta | No |
| API pública estable | No |
| Cache local utilizable | Sí |
| Formato raw listo para el watcher actual | No |

## 2. Arquitectura recomendada

### 2.1 Tres capas

#### Capa raw

Owner: Rick  
Superficie: `NOTION_GRANOLA_DB_ID`

Debe almacenar:

- título
- cuerpo bruto de la nota/transcripción
- fecha
- fuente
- attendees si están disponibles
- action items detectados
- timestamps de importación/procesamiento

No necesita relaciones ricas.

#### Capa curada

Owner: David / gobernanza humana  
Superficie: DB humana de sesiones y transcripciones

Debe almacenar solo lo relevante:

- dominio
- tipo de sesión
- programa o proyecto relacionado
- fecha
- URL fuente
- recurso relacionado
- si hay transcripción disponible
- notas de capitalización

Aquí sí convienen relaciones y clasificación.

#### Capa destino

Superficies:

- proyectos
- tareas
- recursos
- follow-ups

Un ítem raw o curado solo debe llegar a destino cuando haya señal suficiente.

## 3. Flujo objetivo

```text
Granola cache-v6.json
    -> granola_cache_exporter.py
    -> archivos .md estructurados
    -> granola_watcher.py
    -> Worker
    -> DB raw de Rick en Notion
    -> promoción selectiva a capa curada
    -> proyectos / tareas / recursos / follow-up
```

## 4. Componentes

### 4.1 Exporter nuevo

Componente faltante:

- lee `cache-v6.json`
- detecta reuniones nuevas o modificadas
- convierte ProseMirror JSON a Markdown
- exporta `.md` a `GRANOLA_EXPORT_DIR`

Este componente es el puente entre la realidad actual de Granola y el watcher ya previsto en el repo.

### 4.2 Watcher existente

`granola_watcher.py` sigue siendo válido si recibe `.md` bien formado.

### 4.3 Worker existente

Las tasks `granola.*` siguen siendo válidas para:

- crear página raw
- extraer action items
- crear follow-ups
- notificar a Enlace

## 5. Variables de entorno relevantes

| Variable | Dónde | Uso |
|---|---|---|
| `GRANOLA_EXPORT_DIR` | VM | carpeta monitoreada por el watcher |
| `GRANOLA_PROCESSED_DIR` | VM | archivos ya procesados |
| `WORKER_URL` | VM | endpoint local del Worker |
| `WORKER_TOKEN` | VM + Worker | autenticación |
| `NOTION_GRANOLA_DB_ID` | Worker | DB raw de Granola Inbox |
| `NOTION_TASKS_DB_ID` | Worker | opcional; tareas derivadas |
| `ENLACE_NOTION_USER_ID` | Worker | opcional; comentarios para Enlace |

## 6. Contrato del raw

### 6.1 Qué va al raw

- contenido bruto de la reunión
- metadata básica
- action items detectados
- señales para follow-up

### 6.2 Qué no va directo al curado

- notas sin clasificar
- reuniones ambiguas
- contenido aún no validado
- action items sin contexto suficiente

## 7. Promoción a curado

Promover a la capa curada cuando:

- la sesión tiene valor de trazabilidad
- el dominio es claro
- el programa o proyecto es identificable
- hay una razón humana para consultarla después

No promover automáticamente todo el raw.

## 8. Compatibilidad con el modo manual actual

Mientras el pipeline automático no exista, el modo manual sigue siendo válido:

1. David copia desde Granola
2. pega a Notion AI
3. capitaliza en proyectos o sesiones según corresponda

El pipeline de Rick no reemplaza ese flujo de un día para otro. Debe coexistir con él.

## 9. Recomendaciones de implementación

1. Mantener `NOTION_GRANOLA_DB_ID` como DB raw canónica de Rick.
2. No reutilizar la DB curada humana como intake bruto.
3. Implementar primero el exporter de `cache-v6.json`.
4. Mantener el watcher actual.
5. Diseñar después una promoción explícita `raw -> curado -> destino`.

## 10. Referencias

- `worker/notion_client.py`
- `worker/tasks/granola.py`
- `scripts/vm/granola_watcher.py`
- `docs/18-notion-enlace-rick-convention.md`
- `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md`
