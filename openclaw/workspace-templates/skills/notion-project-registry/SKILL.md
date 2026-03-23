---
name: notion-project-registry
description: >-
  Operar el registro canonico de proyectos en Notion de forma registry-first.
  Usar cuando haya que crear, auditar, actualizar o regularizar proyectos,
  entregables, tareas o paginas sueltas para que el estado quede coherente entre
  Notion, Linear, Drive y el trabajo real del stack.
metadata:
  openclaw:
    always: true
    emoji: "\U0001F4C1"
    requires:
      env: []
---

# Notion Project Registry

Esta skill evita page sprawl, comentarios ambiguos y estados oficiales
atrasados. La regla base es: primero el registro canonico, despues las paginas
sueltas.

## Flujo registry-first

1. Resolver el proyecto canonico.
2. Actualizar la fila del proyecto.
3. Si el output es revisable por David, crear o actualizar un entregable canonico.
4. Si tambien existe tarea operativa, enlazarla a proyecto y entregable.
5. Solo despues dejar comentarios, reportes o paginas auxiliares.

## Cuando usarla

- crear o actualizar un proyecto en Notion
- regularizar una pagina suelta
- alinear proyecto, entregable y tarea
- enlazar Notion con Linear y Drive
- auditar si el estado oficial esta en drift
- operar payloads low-level sin perder el esquema canonico

## Secuencia correcta por objeto

### Proyecto

Usa `notion.upsert_project` para el estado maestro.

```json
{
  "name": "Proyecto Embudo Ventas",
  "estado": "Activo",
  "icon": "\U0001F4C1",
  "linear_project_url": "https://linear.app/umbral/project/...",
  "shared_path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas\\",
  "responsable": "David Moreira",
  "agentes": "Rick, Codex",
  "sprint": "R23",
  "open_issues": 3,
  "next_action": "Cerrar decision sobre CTA y captura"
}
```

### Entregable

Si David debe revisar algo, no lo dejes solo como child page en Control Room.
Usa `notion.upsert_deliverable`.

Reglas:

- titulo natural en espanol;
- sin fecha en el titulo;
- fecha y fecha limite en columnas;
- pagina con cuerpo util, no vacia.

### Tarea

Si el trabajo tambien tiene task operativa, usa `notion.upsert_task` y enlazala
al proyecto y al entregable cuando ya existan.

## Comentarios y naming no ambiguos

No hables de un benchmark, entregable o caso usando solo un nombre propio si
eso puede sonar como una persona del equipo.

Preferir:

- `caso Kris`
- `benchmark de Kris Wojslaw`
- `entregable CTA Embudo`

Evitar:

- `agrega comentario a Kris`
- `cierra lo de Ruben`

Los comentarios deben dejar claro:

- que objeto se actualizo;
- que estado cambio;
- y que falta realmente.

## Cuando si usar `notion.create_report_page`

Solo para:

- coordinacion transversal;
- alertas;
- borradores temporales fuera de un proyecto activo;
- reportes que no tienen todavia contenedor canonico.

No usarla como cierre final de un proyecto activo si ya existe registro de
proyecto y base de entregables.

## Regularizacion de paginas sueltas

Si encuentras una pagina suelta project-scoped:

1. identifica el proyecto canonico;
2. crea o actualiza el entregable canonico;
3. enlaza la tarea si existe;
4. mueve el contenido util al contenedor correcto;
5. archiva la pagina suelta con `notion.update_page_properties(archived=true)`.

## Esquema minimo recomendado

Prioriza tipos compatibles con API:

- `title`
- `select`
- `rich_text`
- `multi_select`
- `url`
- `date`

Usa `relation` o `people` solo si el tool resuelve ids de forma confiable.

## Anti-patrones

- Crear una pagina y olvidar la fila del proyecto.
- Marcar una tarea `done` sin `Proyecto` ni `Entregable`.
- Poner emojis o fechas en el titulo cuando existe `icon` y columnas.
- Duplicar estados entre varias columnas ambiguas.
- Usar Control Room como deposito final de entregables.

## Cierre esperado

Un trabajo bien cerrado con esta skill deja:

- proyecto canonico actualizado;
- entregable canonico si David debe revisar algo;
- tarea enlazada cuando corresponde;
- y ningun comentario ambiguo sobre que objeto cambio.
