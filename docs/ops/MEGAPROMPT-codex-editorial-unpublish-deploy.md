# Codex handoff — editorial unpublish (mismo repo)

> **Repo único:** `Umbral-Bot/umbral-agent-stack`  
> **Clone Windows:** `C:\GitHub\umbral-agent-stack-copilot`  
> **NO usar:** `C:\GitHub\_wt\*`, `umbral-agent-stack-codex-coordinador`, `umbral-bot-*`

## Estado (2026-07-02) — CERRADO

| Item | Estado |
|------|--------|
| PR [#494](https://github.com/Umbral-Bot/umbral-agent-stack/pull/494) | ✅ **merged** → `main` @ `1660538` |
| Deploy Function prod | ✅ |
| Fixture smoke eliminado | ✅ (`criterios-de-aceptacion-antes-de-automatizar-bim` → 404) |
| CAND-001 intacto | ✅ SWA 200 — único post en índice |
| Evidencia | `C:\coord-ag-evidence\cand-001-unpublish-fixture\` |
| Bitácora | `docs/ops/cand-001-closeout-2026-07-02.md` |

## Prompt de arranque (pegar en Codex)

```
Trabaja SOLO en el repo umbral-agent-stack:
  C:\GitHub\umbral-agent-stack-copilot
Rama: codex/feat-editorial-unpublish (ya tiene el código unpublish en 761f6ec)

NO uses worktrees _wt ni otros clones.

Tareas en orden:
1) pytest tests/test_editorial_function_shared.py tests/test_editorial_unpublish.py tests/test_editorial_publish.py -v
2) Deploy Function:
   cd functions/editorial-publish
   func azure functionapp publish func-umbral-editorial-prod --python
3) Smoke unpublish fixture (NO tocar CAND-001):
   $env:EDITORIAL_BLOG_FUNCTION_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/unpublish-editorial-post"
   $env:EDITORIAL_BLOG_FUNCTION_KEY = "<az keys list publish_editorial_post o unpublish>"
   $env:WORKER_TOKEN = "<app setting WORKER_TOKEN>"
   ./scripts/smoke-unpublish-editorial-post.ps1 -Slug criterios-de-aceptacion-antes-de-automatizar-bim
4) Verificar CDN index + SWA /noticias solo CAND-001
5) Evidencia en C:\coord-ag-evidence\cand-001-unpublish-fixture\

Veredicto: EDITORIAL_UNPUBLISH_DEPLOY_COMPLETE | fixture_removed=yes | cand001_intact=yes

Si falta function key para unpublish, registrar key en Azure Portal o reutilizar la del publish si comparten authLevel FUNCTION.
Crear PR a main solo si David lo pide.
```

## Fixture a eliminar

`criterios-de-aceptacion-antes-de-automatizar-bim`

## Conservar

`automatizar-sin-gobernanza-escala-el-desorden` (CAND-001)
