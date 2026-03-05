# Prompt R18 — Codex: Dashboard Notion (094)

**Antes de empezar:** `git checkout main && git pull origin main`. Luego: `git checkout -b codex/094-dashboard-notion-seguimiento`.

---

## Para Codex — Tarea 094

```
Tarea 094: actualizar el dashboard de Notion (Dashboard Rick) con el seguimiento R16/R17. Sigue EXACTAMENTE .agents/tasks/2026-03-06-094-r18-codex-dashboard-notion-seguimiento.md.

Antes de empezar: git checkout main && git pull origin main. Luego: git checkout -b codex/094-dashboard-notion-seguimiento.

IMPORTANTE: Trabaja SOLO en la rama codex/094-dashboard-notion-seguimiento.

Haz solo:
1. Revisar docs/22-notion-dashboard-gerencial.md, worker/tasks/notion.py (handle_notion_update_dashboard) y worker/notion_client.py (update_dashboard_page). Revisar scripts/dashboard_report_vps.py si existe.
2. Añadir en la actualización del dashboard una sección o métricas con: R16 cerrada (PRs #85–#90), R17 cerrada (PRs #91–#96 mergeados), 900 tests, última actualización. Usar NOTION_DASHBOARD_PAGE_ID del entorno.
3. Si puedes ejecutar con NOTION_API_KEY y NOTION_DASHBOARD_PAGE_ID, verificar que el dashboard se actualiza; si no, documentar en el PR cómo ejecutarlo.
4. Abrir PR a main. Título: feat(R18-094): dashboard Notion con seguimiento R16/R17.

No quitar métricas existentes del dashboard. Solo añadir el bloque de seguimiento R16/R17.
```
