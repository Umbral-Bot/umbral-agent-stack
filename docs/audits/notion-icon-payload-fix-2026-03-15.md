# Notion Icon Payload Fix - 2026-03-15

## Contexto

En Notion estaban apareciendo nombres con emoji prefijado en el texto (`📁 Proyectos — Umbral`, `📬 Entregables Rick — Revisión`, etc.), lo que mezclaba dos cosas distintas:

- icono real de la pagina
- emoji incrustado en el titulo

## Diagnostico

Habia dos causas:

1. Las tasks del Worker no exponian un campo `icon`, asi que Rick o las skills tendian a resolver iconografia poniendo emoji dentro del `title` o `name`.
2. Para bases de datos top-level, el tooling actual usado por el stack no expone un camino estable para setear icono de database/data source desde las herramientas que estamos usando. En esos casos, el emoji en el titulo era un workaround visual, no un icono real.

## Correccion aplicada

Se agrego soporte de `icon` a:

- `worker/notion_client.py`
  - `create_database_page`
  - `update_page_properties`
  - `create_report_page`
- `worker/tasks/notion.py`
  - `notion.create_database_page`
  - `notion.update_page_properties`
  - `notion.create_report_page`
  - `notion.upsert_project`
  - `notion.upsert_deliverable`
- `openclaw/extensions/umbral-worker/index.ts`
  - schemas de tools actualizados con `icon`

Tambien se actualizaron las skills:

- `openclaw/workspace-templates/skills/notion/SKILL.md`
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`

Regla nueva:

- si la task acepta `icon`, usar ese campo y no meter el emoji en `title` o `name`

## Validacion

Tests locales:

- `python -m pytest tests/test_notion_database_page.py tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_notion_report_page.py -q`
  - `19 passed`

Validacion visible en Notion:

- la pagina `Archivo legacy — entregables sueltos` quedo con icono real `🗃`
- su titulo ya no necesita el emoji como parte del texto

## Limite actual

Esto corrige el comportamiento para paginas y filas futuras creadas/actualizadas por las tasks del Worker.

No resuelve automaticamente iconos de bases de datos top-level creadas por otros caminos si el tooling actual no expone un campo `icon` para database/data source. Esas entradas deben:

- o mantenerse con emoji en el titulo como workaround visual,
- o renombrarse sin emoji si se prefiere limpieza textual sobre diferenciacion visual.
