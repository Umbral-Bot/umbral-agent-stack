# CAND-001 Fase 6 — handoff Codex (2026-06-29)

Estado: **CAND001_BLOG_PUBLISH_COMPLETE** (2026-06-29).

| Check | Resultado |
|-------|-----------|
| slug | `automatizar-sin-gobernanza-escala-el-desorden` |
| SWA smoke | 200 |
| Notion URL | escrita |
| Gates | intactos (`autorizar_publicacion` false) |

Live SWA: https://zealous-ground-0ef6aa910.7.azurestaticapps.net/noticias/automatizar-sin-gobernanza-escala-el-desorden

---

## Worktrees limpios (usar estos)

| Path | HEAD | Rol |
|------|------|-----|
| `C:\GitHub\_wt\cand001-f6-agent-stack` | `6d492d7` | copy YAML + smoke publish |
| `C:\GitHub\_wt\cand001-f6-blog` | `21a8bd7` | contrato SPA `/noticias` (lectura) |

Evidencia: `C:\coord-ag-evidence\cand-001-fase6-blog\` (carpeta creada, vacía)

## Megaprompt Codex

`C:\GitHub\_wt\cand001-f6-agent-stack\docs\ops\MEGAPROMPT-codex-windows-cand001-fase6-blog-publish.txt`

Copia espejo en `umbral-agent-stack/docs/ops/` (repo Cursor).

## Prompt de arranque (pegar en Codex)

```
Ejecuta Fase 6 CAND-001 blog-only siguiendo al pie de la letra:
C:\GitHub\_wt\cand001-f6-agent-stack\docs\ops\MEGAPROMPT-codex-windows-cand001-fase6-blog-publish.txt

Repo cwd: C:\GitHub\_wt\cand001-f6-agent-stack
Skill: umbral-repo-codex + azure si hace falta.
Preflight Notion + Azure antes de publicar. NO marcar autorizar_publicacion.
Veredicto final en una línea: CAND001_BLOG_PUBLISH_COMPLETE o _BLOCKED.
```

## No usar hoy

- `umbral-agent-stack-codex-coordinador` (127 behind, dirty)
- `umbral-bot-copilot` / `umbral-bot-codex-clean` (ramas sucias)
- `worker.tasks.editorial_publish` (gate autorizar_publicacion)

## Preflight Azure (Cursor ya verificó)

- `dm@umbralbim.cl` logueado
- `func-umbral-editorial-prod` Running
- `steditorialprod` en `rg-umbral-agents-prod`
- CDN index + SWA `/noticias` → 200

Pendiente Codex: read-back Notion (`Visual asset URL` HTTPS directa).

## Unblock 2026-06-29 (Codex preflight failed)

Notion real:
- `Selección imagen` = Pendiente
- `Estado imagen` = Listo para selección
- `Visual asset URL` = vacío

Causa: el Worker que copia `imagen_alt_N_url` → `Visual asset URL` **aún no está cableado**.
Elegir alt en Notion **no** rellena `Visual asset URL` solo.

### Paso A — David (Notion UI)

1. Abrir [CAND-001](https://www.notion.so/CAND-001-Automatizar-sin-gobernanza-escala-el-desorden-34b5f443fb5c81dd8338cb0b46699250)
2. Revisar `imagen_alt_1_url` … `imagen_alt_5_url` (preview)
3. Elegir **Selección imagen** = `Alt N`

### Paso B — Sync (Codex, NOTION_API_KEY)

```powershell
cd C:\GitHub\_wt\cand001-f6-agent-stack
$env:NOTION_API_KEY = "<key>"

# Ver estado + URLs disponibles
python scripts/editorial/sync_visual_asset_from_selection.py --report-only

# Opción 1: David ya puso Alt N en Notion
python scripts/editorial/sync_visual_asset_from_selection.py

# Opción 2: declarar elección + sync en un paso (ej. Alt 2)
python scripts/editorial/sync_visual_asset_from_selection.py --set-selection 2
```

Esperado: `SYNC_OK` + `Visual asset URL` HTTPS + `Estado imagen` = Seleccionada.

### Paso C — Rerun Fase 6

Re-ejecutar megaprompt Fase 6 (mismo archivo). Preflight Notion debe pasar.
