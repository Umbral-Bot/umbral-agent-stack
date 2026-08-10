# Heartbeat de rick-tracker: fin de la publicación a Notion (2026-08-10)

> **Pack:** PKG-UAS-HEARTBEAT-STOP-NOTION · rama `claude/pkg-uas-heartbeat-stop-notion-20260810` ·
> base `8b15789` (`origin/main`, tip = PR #618)
> **GO horneado (citado, no reabierto):** *"opción a — heartbeat de rick-tracker DEJA DE
> publicar a Notion; solo local (reports/)"* (David, 2026-08-10). El cleanup del panel
> cada 6h queda como red de seguridad, no como solución.
> **Evidencia:** `~/.coord-ag-evidence/uas-heartbeat-stop-notion-20260810/` (AUTHZ +
> backups con md5 verificado).

## 1. Productor localizado

No hay script ni cron que cree las páginas: el productor es **conductual** — las
instrucciones de heartbeat del agente. El diagnóstico previo
([uas-panel-residual-diag-20260809.md](uas-panel-residual-diag-20260809.md)) ya había
probado la mecánica (bash + heredoc Python importando `worker.notion_client` in-process,
desde la sesión persistente de `rick-tracker`). Este pack cierra la fuente:

**Paths (par SoT, byte-idénticos entre sí antes del edit — md5 `663e71a8…` los tres,
incluido el backup):**
- Live: `~/.openclaw/workspaces/rick-tracker/HEARTBEAT.md`
- Repo (lo que un sync restaura): `openclaw/workspace-agent-overrides/rick-tracker/HEARTBEAT.md`

**Contenido original (5 líneas, completo):**
```
# Heartbeat

- Resuelve primero el estado oficial en Linear y Notion antes de narrar progreso.
- No cierres items sin issue, update, artefacto o trazabilidad proporcional.
- Si detectas drift entre repo, Notion, carpeta o estado oficial, intenta corregirlo en la misma iteracion.
```

La combinación "estado oficial en… Notion" + "trazabilidad proporcional" + "intenta
corregirlo en la misma iteración" es lo que el agente interpretó (desde 2026-08-01) como
mandato de publicar un reporte de heartbeat a Control Room cada hora, además del reporte
local que ya escribía desde junio.

## 2. Edit aplicado (ambas copias, live y repo — un sync ya no revierte)

Diff sanitizado (completo):

```diff
-- Resuelve primero el estado oficial en Linear y Notion antes de narrar progreso.
+- Resuelve primero el estado oficial en Linear y Notion antes de narrar progreso — Notion en modo SOLO LECTURA durante el heartbeat.
-- Si detectas drift entre repo, Notion, carpeta o estado oficial, intenta corregirlo en la misma iteracion.
+- Si detectas drift entre repo, Notion, carpeta o estado oficial, corrígelo en Linear/repo si es tu charter, o escálalo al orchestrator; NO lo "corrijas" creando contenido en Notion.
+- Trazabilidad del heartbeat: SOLO el reporte local (`reports/heartbeat-rick-*.md`). PROHIBIDO crear páginas, reportes o cualquier escritura en Notion desde el heartbeat — ni con tools `umbral_notion_*` ni importando `worker.notion_client` por bash. Control Room es superficie de David, no de telemetría (decisión David 2026-08-10, PKG-UAS-HEARTBEAT-STOP-NOTION; contexto: docs/ops/uas-panel-residual-diag-20260809.md).
```

La prohibición nombra explícitamente **ambas vías** observadas (tools `umbral_notion_*`
y el bypass `worker.notion_client` por bash), porque la evidencia del diagnóstico mostró
que el agente usaba la segunda.

Post-edit: live y repo-override quedan md5-idénticos (`f885419b…`). No se tocó
`openclaw.json`, ni el gateway, ni las 4 páginas de contenido, ni el cleanup del panel.

## 3. Plan de verify (próximo :33 — PARTIAL hasta entonces)

El heartbeat corre cada hora al :33. No se fuerza una corrida como "dry-run": invocar al
agente no es un dry-run seguro (gasta un turno real y podría escribir). Verify vivo:

```bash
# 1. Cero páginas Heartbeat nuevas en Control Room (conteo read-only, mismos helpers del panel):
set -a; source ~/.config/openclaw/env; set +a
cd ~/umbral-agent-stack && PYTHONPATH=. python3 - <<'PY'
import sys; sys.path.insert(0, '.')
from scripts.openclaw_panel_vps import OPENCLAW_PAGE_ID, _list_children, _is_residual_child_page
res = [b for b in _list_children(OPENCLAW_PAGE_ID) if _is_residual_child_page(b)]
print('paginas Heartbeat sin archivar:', len(res))  # esperado: 0
PY

# 2. El reporte local sigue apareciendo (el heartbeat en sí no se rompió):
ls -t ~/umbral-agent-stack/reports/heartbeat-rick-* | head -1  # esperado: timestamp nuevo
```

Baseline al momento del edit: último report local `heartbeat-rick-2026-08-10-1633.md`
(16:33 UTC); próximo heartbeat 17:33 UTC.

**Plan B si el hábito de la sesión persiste sobre la instrucción nueva:** la sesión
persistente de `rick-tracker` (`bd35d75c…`) acumula ~100 publicaciones previas como
contexto. Si tras 2 heartbeats siguen apareciendo páginas, el paso siguiente es
compactar/rotar esa sesión (`openclaw sessions compact` o reset) para que el historial
no compita con la instrucción — mutación aparte, con su propio GO. Mientras tanto el
cleanup del panel archiva cualquier página que se escape, cada 6h.

## Gate

**`UAS_HEARTBEAT_STOP_NOTION_PASS = PARTIAL`** — productor localizado con cita,
backup verificado (md5), edit aplicado en live + repo (sync-safe), docs/PR. El verify
vivo queda pendiente del próximo :33 (criterio explícito del pack para PARTIAL).
Pasa a **Y** cuando dos heartbeats consecutivos no produzcan páginas nuevas y el
reporte local siga generándose.
