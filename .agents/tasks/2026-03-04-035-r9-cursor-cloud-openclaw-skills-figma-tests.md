---
id: "035"
title: "OpenClaw Skills + Figma Tests"
assigned_to: cursor-agent-cloud
branch: feat/cursor-cloud-skills-figma
round: 9
status: assigned
created: 2026-03-04
---

## Objetivo

1. Crear tests completos para el handler `worker/tasks/figma.py`.
2. Crear OpenClaw workspace skills para las tools que aún no tienen SKILL.md.

## Contexto

- `worker/tasks/figma.py` — 5 handlers de Figma recién creados (get_file, get_node, export_image, add_comment, list_comments). No tienen tests.
- `openclaw/workspace-templates/skills/figma/SKILL.md` — ya creado como referencia de formato.
- Patrón de tests: ver `tests/test_azure_audio.py` o `tests/test_linear_webhooks.py` como ejemplo.
- Los skills se copian a `~/.openclaw/workspace/skills/` en la VPS para que Rick los descubra.

## Parte 1: Tests de Figma

Crear `tests/test_figma.py` con al menos estos tests:

### figma.get_file
- Test OK: mock de requests.get retorna estructura válida → devuelve pages
- Test sin FIGMA_API_KEY → devuelve `{"ok": false, "error": "FIGMA_API_KEY not configured"}`
- Test sin file_key → devuelve error
- Test HTTP error (403, 404) → devuelve error legible

### figma.get_node
- Test OK con un node_id string
- Test OK con lista de node_ids
- Test sin node_ids → error

### figma.export_image
- Test OK con formato png
- Test formato inválido → error
- Test sin node_ids → error

### figma.add_comment
- Test OK → devuelve comment id
- Test sin message → error
- Test con node_id adjunta client_meta

### figma.list_comments
- Test OK → devuelve count y lista
- Test sin file_key → error

Patron: usar `@patch("worker.tasks.figma.requests.get")` y `@patch("worker.tasks.figma.requests.post")`.
Setear `os.environ.setdefault("WORKER_TOKEN", "test")` al inicio.
Mockear `config.FIGMA_API_KEY = "figd_test123"` con `@patch("worker.tasks.figma.config")`.

## Parte 2: OpenClaw Skills

Crear SKILL.md para cada tool en `openclaw/workspace-templates/skills/<nombre>/SKILL.md`.
Seguir el formato exacto de `openclaw/workspace-templates/skills/figma/SKILL.md` como referencia.

### Skills a crear:

1. **`openclaw/workspace-templates/skills/azure-audio/SKILL.md`**
   - Task: `azure.audio.generate`
   - Descripción: TTS audio generation via Azure OpenAI Realtime API
   - Requiere: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
   - Documentar las 8 voces (alloy, ash, ballad, coral, echo, sage, shimmer, verse)
   - Referencia: `worker/tasks/azure_audio.py`, `docs/42-azure-foundry-audio-tool.md`

2. **`openclaw/workspace-templates/skills/research/SKILL.md`**
   - Tasks: `research.web`, `composite.research_report`
   - Descripción: web search via Google CSE/Tavily + LLM report generation
   - Requiere: GOOGLE_CSE_API_KEY_RICK_UMBRAL o TAVILY_API_KEY
   - Referencia: `worker/tasks/research.py`, `worker/tasks/composite.py`

3. **`openclaw/workspace-templates/skills/linear/SKILL.md`**
   - Tasks: `linear.create_issue`, `linear.list_teams`, `linear.update_issue_status`
   - Descripción: gestión de issues en Linear con routing automático de equipos
   - Requiere: LINEAR_API_KEY
   - Documentar team_key, priority, labels
   - Referencia: `worker/tasks/linear.py`

4. **`openclaw/workspace-templates/skills/provider-status/SKILL.md`**
   - Endpoint: GET `/providers/status`
   - Descripción: consultar estado de providers LLM, cuota, routing
   - Requiere: WORKER_TOKEN (auth del Worker)
   - Referencia: `worker/app.py` (buscar `/providers/status`)

## Instrucciones de ejecución

```bash
git pull origin main
git checkout -b feat/cursor-cloud-skills-figma

# ... hacer cambios ...

python -m pytest tests/test_figma.py -v -p no:cacheprovider
# Todos deben pasar

git add .
git commit -m "feat: figma tests + openclaw workspace skills"
git push -u origin feat/cursor-cloud-skills-figma
gh pr create --title "feat: figma tests + openclaw workspace skills" --body "Tests para handler figma.py + SKILL.md para azure-audio, research, linear, provider-status"
```

## Criterio de éxito

- `python -m pytest tests/test_figma.py -v` → al menos 15 tests pasan
- 4 SKILL.md nuevos creados con frontmatter YAML correcto
- Skills siguen el formato de referencia (`skills/figma/SKILL.md`)
- No se rompen tests existentes
