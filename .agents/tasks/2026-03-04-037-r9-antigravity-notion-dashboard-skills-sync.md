---
id: "037"
title: "Notion Dashboard: Tools Inventory + Skills Sync"
assigned_to: antigravity
branch: feat/antigravity-dashboard-tools-sync
round: 9
status: assigned
created: 2026-03-04
---

## Objetivo

Actualizar el Notion Dashboard de Rick con un inventario completo de tools disponibles y crear un script que sincronice los skills del workspace.

## Contexto

- `openclaw/workspace-templates/TOOLS.md` — acaba de ser actualizado con 23 tasks
- `openclaw/workspace-templates/skills/` — directorio de skills (figma ya creado, otros en progreso por otros agentes)
- `worker/tasks/__init__.py` — TASK_HANDLERS dict con todas las tasks registradas
- `worker/app.py` — ya tiene `/providers/status` y `/health`

## Requisitos

### 1. Script `scripts/sync_tools_to_notion.py`

Script que lee `TASK_HANDLERS` del Worker y actualiza una página de Notion con la tabla de tools:

- Leer las tasks registradas programáticamente (importar TASK_HANDLERS o parsear __init__.py)
- Para cada task, extraer: nombre, módulo de origen, si requiere env vars específicas
- Escribir en Notion Dashboard una tabla con: Task | Estado (✅ configurado / ⚠️ falta env) | Módulo
- Usar `NOTION_API_KEY` y `NOTION_DASHBOARD_PAGE_ID`

### 2. Script `scripts/sync_skills_to_vps.py`

Script que copia los skills del repo a la VPS:

- Lee `openclaw/workspace-templates/skills/*/SKILL.md`
- Los copia a `~/.openclaw/workspace/skills/` en la VPS vía SCP o genera instrucciones
- Lista los skills disponibles con nombre y descripción (parseando frontmatter YAML)
- Modo `--dry-run` que solo muestra qué haría sin ejecutar

### 3. Endpoint `/tools/inventory` en Worker

Agregar un endpoint GET al Worker que retorne:

```json
{
  "timestamp": "2026-03-04T...",
  "total_tasks": 23,
  "tasks": [
    {"name": "figma.get_file", "module": "figma", "category": "figma"},
    {"name": "llm.generate", "module": "llm", "category": "ai"},
    ...
  ],
  "skills": ["figma", "azure-audio", ...],
  "categories": {"figma": 5, "notion": 6, "linear": 3, ...}
}
```

### 4. Tests

`tests/test_tools_inventory.py`:
- Test endpoint `/tools/inventory` retorna todas las tasks
- Test categorización correcta
- Test formato de respuesta

## Instrucciones

```bash
git pull origin main
git checkout -b feat/antigravity-dashboard-tools-sync

# ... hacer cambios ...

python -m pytest tests/test_tools_inventory.py -v -p no:cacheprovider

git add .
git commit -m "feat: tools inventory endpoint + notion sync scripts"
git push -u origin feat/antigravity-dashboard-tools-sync
gh pr create --title "feat: tools inventory + notion dashboard sync" --body "GET /tools/inventory + sync scripts for notion dashboard and VPS skills"
```

## Criterio de éxito

- `/tools/inventory` retorna JSON con todas las tasks registradas
- `scripts/sync_skills_to_vps.py --dry-run` lista skills correctamente
- Tests pasan
- No se rompen tests existentes
