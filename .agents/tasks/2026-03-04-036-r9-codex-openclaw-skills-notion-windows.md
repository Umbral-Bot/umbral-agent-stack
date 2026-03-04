---
id: "036"
title: "OpenClaw Skills: Notion + Windows"
assigned_to: codex
branch: feat/codex-skills-notion-windows
round: 9
status: done
created: 2026-03-04
---

## Objetivo

Crear OpenClaw workspace skills para las familias de tasks de Notion y Windows, para que Rick las descubra automáticamente.

## Contexto

- Los skills se colocan en `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
- Referencia de formato: `openclaw/workspace-templates/skills/figma/SKILL.md`
- Cada skill tiene YAML frontmatter (name, description, metadata) + Markdown con instrucciones
- Los skills se copian a `~/.openclaw/workspace/skills/` en la VPS

## Skills a crear

### 1. `openclaw/workspace-templates/skills/notion/SKILL.md`

Tasks que documenta:

| Task | Input clave | Descripción |
|------|-------------|-------------|
| `notion.write_transcript` | `page_id`, `content` | Escribe transcripción en página Notion |
| `notion.add_comment` | `page_id`, `comment` | Agrega comentario a página |
| `notion.poll_comments` | `page_id` | Lee comentarios de Control Room |
| `notion.upsert_task` | `title`, `status`, `db_id` | Crea/actualiza tarea en DB Notion |
| `notion.update_dashboard` | `data` | Actualiza dashboard de Rick |
| `notion.create_report_page` | `title`, `content`, `parent_id` | Crea página de reporte |

- Requiere: `NOTION_API_KEY`
- Referencia: `worker/tasks/notion.py`, `worker/notion_client.py`
- Triggers: "write to notion", "notion comment", "update dashboard", "create report"

### 2. `openclaw/workspace-templates/skills/windows/SKILL.md`

Tasks que documenta:

| Task | Input clave | Descripción |
|------|-------------|-------------|
| `windows.pad.run_flow` | `flow_name` | Ejecuta flujo de Power Automate Desktop |
| `windows.open_notepad` | - | Abre Bloc de notas en la VM |
| `windows.write_worker_token` | `token` | Escribe WORKER_TOKEN en la VM |
| `windows.firewall_allow_port` | `port` | Permite puerto en firewall Windows |
| `windows.start_interactive_worker` | - | Inicia Worker interactivo en :8089 |
| `windows.add_interactive_worker_to_startup` | - | Agrega Worker al startup |
| `windows.fs.ensure_dirs` | `paths` | Crea directorios en la VM |
| `windows.fs.list` | `path` | Lista archivos en directorio |
| `windows.fs.read_text` | `path` | Lee archivo de texto |
| `windows.fs.write_text` | `path`, `content` | Escribe archivo de texto |
| `windows.fs.write_bytes_b64` | `path`, `data_b64` | Escribe archivo binario (base64) |

- Requiere: `WORKER_URL_VM` (accesible vía Tailscale)
- Referencia: `worker/tasks/windows.py`, `worker/tasks/windows_fs.py`, `worker/tasks/windows_fs_bin.py`
- Triggers: "run pad flow", "open notepad", "write file on vm", "list files on windows"
- Nota: mencionar que estas tasks solo funcionan cuando el Worker corre en la VM Windows

## Instrucciones

```bash
git pull origin main
git checkout -b feat/codex-skills-notion-windows

# Crear los 2 skills
# Verificar YAML frontmatter válido con:
python -c "import yaml; yaml.safe_load(open('openclaw/workspace-templates/skills/notion/SKILL.md').read().split('---')[1])"
python -c "import yaml; yaml.safe_load(open('openclaw/workspace-templates/skills/windows/SKILL.md').read().split('---')[1])"

git add .
git commit -m "feat: openclaw skills for notion and windows tasks"
git push -u origin feat/codex-skills-notion-windows
gh pr create --title "feat: openclaw skills — notion + windows" --body "SKILL.md for notion.* and windows.* task families"
```

## Criterio de éxito

- 2 SKILL.md creados con frontmatter YAML válido
- Formato consistente con `skills/figma/SKILL.md`
- Todas las tasks listadas con input/output documentado

## Log

### [codex] 2026-03-04 17:43
- Creado `openclaw/workspace-templates/skills/notion/SKILL.md` con frontmatter YAML y documentacion completa de tasks `notion.*` (inputs, ejemplos JSON, outputs, triggers, requisitos y referencias).
- Creado `openclaw/workspace-templates/skills/windows/SKILL.md` con frontmatter YAML y documentacion completa de tasks `windows.*` y `windows.fs.*` (inputs, ejemplos JSON, outputs, triggers, requisitos y notas de VM Windows).
- Formato tomado de referencia `openclaw/workspace-templates/skills/figma/SKILL.md`.
- Validacion de YAML ejecutada:
  - `python -c "import yaml; yaml.safe_load(open('openclaw/workspace-templates/skills/notion/SKILL.md', encoding='utf-8').read().split('---')[1]); print('notion frontmatter ok')"`
  - `python -c "import yaml; yaml.safe_load(open('openclaw/workspace-templates/skills/windows/SKILL.md', encoding='utf-8').read().split('---')[1]); print('windows frontmatter ok')"`
