---
id: "2026-03-23-004"
title: "UMB-148: retirar Google Custom Search como path primario de discovery web"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-23T20:55:00-03:00
updated_at: 2026-03-23T21:34:00-03:00
---

## Objetivo
Capitalizar el hallazgo de que Google Custom Search no ha sido un backend operativo real para este stack y dejar Tavily como camino primario explícito en scripts, docs y tests.

## Contexto
- `scripts/web_discovery.py` seguía presentando Google Custom Search como motor primario y Tavily como fallback, aunque los diagnósticos históricos repetidos devolvieron 403.
- `scripts/diagnose_google_cloud_apis.py` seguía sugiriendo habilitar Custom Search como ruta normal.
- El issue de seguimiento en Linear es `UMB-148`.

## Criterios de aceptación
- [x] `scripts/web_discovery.py` usa Tavily por defecto y deja Google solo como opt-in legado.
- [x] `scripts/diagnose_google_cloud_apis.py` deja de presentar Custom Search como ruta operativa recomendada.
- [x] `.env.example` y docs relevantes quedan alineados con Tavily como backend operativo.
- [x] Hay tests unitarios nuevos que fijan el contrato Tavily-first.

## Log
### [codex] 2026-03-23 21:20
- Actualicé `scripts/web_discovery.py` para usar Tavily como primario y Google Custom Search solo con `--allow-google-legacy` o `WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1`.
- Actualicé `scripts/diagnose_google_cloud_apis.py`, `.env.example`, `docs/35-rick-google-cloud-apis.md` y `docs/36-rick-embudo-capabilities.md` para reflejar que Custom Search es legado/experimental.
- Agregué `tests/test_web_discovery.py` para fijar el comportamiento Tavily-first.
- Validación real:
  - `python -m pytest tests/test_web_discovery.py tests/test_research_handler.py tests/test_sim_daily_report.py -q` → `11 passed`
  - `WORKER_TOKEN=test python -m pytest tests -q` → `1193 passed, 4 skipped, 1 warning`
  - `git diff --check` → OK (solo warnings CRLF del checkout Windows)
