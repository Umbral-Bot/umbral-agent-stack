---
id: "2026-05-19-001"
title: "Runtime check: sistema-editorial-rick, bandeja-de-revisión-rick, Granola V2 (CORE-Q2 sistemas)"
status: done
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: "2026-05-19"
updated_at: "2026-05-20"
---

## Contexto previo

`notion-governance@agents/governance-personal-david-2026-05-18` (commit
`b3efe03`) ejecutó O16.5 + O16.6 y consolidó en
`docs/audits/2026-05-19-O16.6-governed-reading.md` 3 grupos cuya situación
runtime no se puede verificar desde el repo de governance:

1. **sistema-editorial-rick** (O14) — 4 nodos
2. **bandeja-de-revision-rick** (O14 writer activo) — 3 nodos
3. **transcripciones-granola** (O8e cron) — 3 nodos

Releé la regla **VPS Reality Check Rule** en
`.github/copilot-instructions.md` (commit `fbc5dae`, 2026-05-04) antes de
empezar.

## Objetivo

Reportar para cada uno de los 3 sistemas:

- ¿Sigue activo el cron/writer/loop en la VPS? (`systemctl status`,
  `crontab -l`, `journalctl --since "7 days ago"`)
- ¿Está escribiendo a Notion (DB target) en los últimos 7 días?
- ¿Hay drift entre código en repo y proceso corriendo (PID start time vs git
  log)?

## Procedimiento mínimo

```bash
cd ~/umbral-agent-stack && git pull origin main

# 1. sistema-editorial-rick
systemctl status sistema-editorial-rick 2>/dev/null || systemctl --user status sistema-editorial-rick
journalctl -u sistema-editorial-rick --since "7 days ago" --no-pager | tail -60

# 2. bandeja-de-revision-rick (writer)
crontab -l | grep -i "bandeja\|revision\|rick"
ls -lat ~/umbral-agent-stack/logs/bandeja-revision-rick/ 2>/dev/null | head -10

# 3. Granola V2 cron
crontab -l | grep -i "granola\|transcripcion"
journalctl --user --since "7 days ago" --no-pager | grep -i granola | tail -40
```

## Criterios de aceptación

- [x] Para cada uno de los 3 sistemas: bloque "Repo dice X" + "VPS muestra Y"
      explícito.
- [x] Si alguno no está activo, anotar última escritura conocida (fecha + log
      file) ANTES de proponer reinicio.
- [x] **NO** reiniciar nada en este pase. Sólo diagnóstico.

## Antipatrones prohibidos

- Hacer `grep` al repo y declarar "está activo" sin journalctl.
- Asumir cron está corriendo porque el archivo systemd existe.
- Decir "todo OK" sin evidencia de escritura a Notion en últimos 7d.

## Referencias

- Trigger: `notion-governance@agents/governance-personal-david-2026-05-18` commit `b3efe03`
- Governed reading: `docs/audits/2026-05-19-O16.6-governed-reading.md` §C
- Governed outcome: `docs/audits/2026-05-19-O16.6-governed-outcome.md`
- Skill aplicada: `notion-governance/.agents/skills/delegate-to-copilot-vps/SKILL.md`

## Log

### 2026-05-20T19:10Z — Diagnóstico (sin reinicio)

Operador: Copilot-VPS. Host: `srv1431451` (VPS Hostinger), user `rick`.
Repo HEAD: `git pull origin main` → "Already up to date".
Servicios core corroborados antes del análisis (no se reinicia nada):

- `umbral-worker.service` — active (since 2026-05-08T02:10:55-04, PID 144470, `uvicorn worker.app:app --host 127.0.0.1 --port 8088`).
- `openclaw-dispatcher.service` — active (since 2026-05-19T10:40:39-04, PID 472894).
- `openclaw-gateway.service` — active.
- No existe ninguna unidad systemd llamada `sistema-editorial-rick`, `bandeja-de-revision-rick` ni `granola*` (ni `--user` ni system). Esos sistemas son cron-driven o vía worker tasks, no servicios dedicados.

---

#### Sistema 1 — `sistema-editorial-rick` (O14)

**Repo dice (intención):**
- Spec en [docs/specs/sistema-editorial-rick-v1.md](docs/specs/sistema-editorial-rick-v1.md), ADR-007/008.
- Runtime real implementado como pipeline de stages: `scripts/discovery/stage4_push_notion.py`, `stage6_llm_combinator.py`, `stageX_pipeline_dashboard.py`, etc.
- Orquestador VPS: [scripts/vps/discovery-publish-cron.sh](scripts/vps/discovery-publish-cron.sh), planeado para `15 */6 * * *`.

**VPS muestra (realidad):**
- `crontab -l` confirma: `15 */6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1` — **cron activo**.
- `/tmp/discovery_publish.log` última corrida exitosa **2026-05-20T16:15:35Z**:
  - `stage4: COMMIT` → `pending_total=0, processed=0` (DB Publicaciones `b9d3d8677b1e4247bafdcb0cc6f53024`, datasource `9d4dbf65-664f-41b4-a7f6-ce378c274761`).
  - `stage6: COMMIT (real LLM call)` → `proposals_generated=4, persisted ids=[202, 203, 204, 205]`.
  - `stageX: pipeline_dashboard` → `dashboard updated: page_id=35a5f443-fb5c-8195-9d7f-d87fa96e36d1`.
- Corrida anterior 2026-05-20T10:15:31Z también OK (`ids=[198, 199, 200, 201]`).
- Sin errores ni drift PID/git: el cron ejecuta repo HEAD vivo (`735b0ba`).

**Conclusión:** ✅ **ACTIVO**. Última escritura conocida a Notion: 2026-05-20T16:15:35Z (Publicaciones row IDs 202-205 + dashboard page `35a5f443-fb5c-8195-9d7f-d87fa96e36d1`). Sin acción requerida.

---

#### Sistema 2 — `bandeja-de-revision-rick` (O14 writer activo)

**Repo dice (intención):**
- DB target: `Bandeja de revisión - Rick` (`NOTION_DELIVERABLES_DB_ID`).
- Writer canónico = task del worker `notion.upsert_deliverable`, declarado en:
  - [docs/07-worker-api-contract.md:320](docs/07-worker-api-contract.md#L320)
  - [openclaw/workspace-templates/SOUL.md:131](openclaw/workspace-templates/SOUL.md#L131), [L144](openclaw/workspace-templates/SOUL.md#L144)
  - [openclaw/workspace-templates/skills/granola-pipeline/SKILL.md:367](openclaw/workspace-templates/skills/granola-pipeline/SKILL.md#L367)
  - [.env.example:41](.env.example#L41)

**VPS muestra (realidad):**
- `grep -c '"task": "notion.upsert_deliverable"' ~/.config/umbral/ops_log.jsonl` → **`0`** en la historia completa del ops_log (322 MB, ~10M eventos).
- El worker en runtime **no expone** la task `notion.upsert_deliverable`. Lista oficial reportada por el propio worker en errores `unknown_task` (último 2026-05-20T01:33:48Z, trace `127f1da3-6461-4d38-8fbe-df37505b7456`):
  ```
  ['ping', 'notion.write_transcript', 'notion.add_comment', 'notion.poll_comments',
   'notion.read_page', 'notion.read_database', 'notion.search_databases',
   'notion.create_database_page', 'notion.update_page_properties',
   'notion.upsert_task', 'notion.update_dashboard', 'windows.pad.run_flow', ...]
  ```
  → `upsert_deliverable` **ausente del registry**.
- Único rastro del label: 5 eventos `system_activity` de `openclaw_panel` con `"trigger": "notion.upsert_deliverable"` (texto descriptivo, no ejecución), último **2026-05-15T07:38:53.362687+00:00**.
- No existe `~/umbral-agent-stack/logs/bandeja-revision-rick/`.
- No hay cron ni proceso (`ps -ef | grep bandeja` → vacío).

**Conclusión:** ⚠️ **WRITER NO IMPLEMENTADO EN RUNTIME**. Drift duro entre doc y código: la API contract declara `notion.upsert_deliverable` como task oficial; el worker corriendo en VPS no la registra. Última actividad con ese label en cualquier forma: **2026-05-15T07:38:53Z** (y era un string descriptivo de `openclaw_panel`, no una escritura real a Bandeja). Nunca se observó una ejecución `task_completed` con `task == "notion.upsert_deliverable"` en el ops_log.

**Propuesta (NO ejecutada — requiere aprobación humana explícita):**
- No corresponde reiniciar nada (no hay daemon caído). Lo que requiere decisión es:
  1. ¿Restaurar `notion.upsert_deliverable` en `worker/tasks/notion.py` y registrarla? — O —
  2. Aceptar como deprecated y actualizar docs/SOUL/SKILLs para apuntar al writer real (¿`notion.create_database_page` con parent = bandeja DB id?).
- Antes de cualquier deploy: confirmar con David qué writer es canónico.

---

#### Sistema 3 — `transcripciones-granola` (O8e cron)

**Repo dice (intención):**
- Pipeline en [docs/50-granola-notion-pipeline.md](docs/50-granola-notion-pipeline.md), [docs/54-granola-capitalize-raw-slice.md](docs/54-granola-capitalize-raw-slice.md), [openclaw/workspace-templates/skills/granola-pipeline/SKILL.md](openclaw/workspace-templates/skills/granola-pipeline/SKILL.md).
- Raw intake declarado en **VM Windows**: `scripts/vm/granola_watcher.py`, `granola_vm_raw_intake.py`, `granola_api_ingest.py`.
- Procesamiento via worker tasks: `granola.classify_raw`, `granola.capitalize_raw`, `granola.process_transcript`, `granola.promote_curated_session`, `granola.promote_operational_slice`, `granola.promote_session_capitalizable`, `granola.read_session_capitalizable`.
- VPS cron declarado: [scripts/vps/granola-gap-check.sh](scripts/vps/granola-gap-check.sh) — header comment dice `Cron: 0 8 * * * bash ~/umbral-agent-stack/scripts/vps/granola-gap-check.sh`.
- Clasificación V2 corre dentro del poller: `dispatcher/notion_poller.py::_classify_pending_granola_pages` (línea 414).

**VPS muestra (realidad):**
- **`granola-gap-check.sh` NO está en `crontab -l`** — el header del script declara intent pero no hay entrada real. `/tmp/granola_gap_check.log` **no existe**.
- `ps -ef | grep -iE "granola|raw_intake"` → **vacío**. No hay loop de intake en VPS (consistente con que raw intake era responsabilidad de la VM).
- DB Granola (`3265f443-fb5c-81d7-89b9-e16eacb0082d`) **sí está siendo leída** continuamente: 22 508 ocurrencias en ops_log, última `notion.read_database` 2026-05-20T19:04:23Z (poller V2).
- **Última actividad real de cada task `granola.*`** (count, last_ts):
  - `granola.classify_raw`: count=19, last **2026-05-11T22:22:58+00:00**.
  - `granola.capitalize_raw`: count=4, last **2026-04-13T17:14:39+00:00**.
  - `granola.process_transcript`: count=3, last **2026-04-14T04:18:40+00:00**.
  - `granola.promote_curated_session`: count=5, last **2026-03-31T08:16:08+00:00**.
  - `granola.promote_operational_slice`: count=10, last **2026-03-31T08:15:31+00:00**.
  - `granola.promote_session_capitalizable`: count=2, last **2026-03-31T08:09:21+00:00**.
  - `granola.read_session_capitalizable`: count=3, last **2026-03-31T08:07:09+00:00**.
- **`_classify_pending_granola_pages` está ROTO**: cada ciclo del poller dispara HTTP 500 desde el worker. Tail de [/tmp/notion_poller.log line 974731+](file:///tmp/notion_poller.log):
  ```
  2026-05-20 14:03:34,407 [WARNING] dispatcher.notion_poller: V2 classify: failed to read Granola DB
    File "dispatcher/notion_poller.py", line 414, in _classify_pending_granola_pages
      resp = wc.run(...)
    File "client/worker_client.py", line 147, in run
      resp.raise_for_status()
  httpx.HTTPStatusError: Server error '500 Internal Server Error' for url 'http://127.0.0.1:8088/run'
  ```
  Errores recurrentes: 2026-05-17T04:23:44, 2026-05-18T01:24:34, 2026-05-20T14:03:34. El poller también falla "Failed to resolve session_capitalizable review targets" (mismo trace, línea ~siguiente).
- Drift PID vs git: `umbral-worker` corre desde 2026-05-08T02:10:55-04 (12 días); HEAD del repo `735b0ba`. Posible drift de código no reiniciado afectando endpoints `granola.*`.

**Conclusión:** ❌ **PIPELINE DE PROCESAMIENTO GRANOLA INACTIVO desde 2026-05-11**.
- Última escritura/clasificación confirmada: **2026-05-11T22:22:58+00:00** (`granola.classify_raw`).
- Lecturas siguen pero la rama de clasificación V2 dentro del poller devuelve 500 del worker → ningún paginado nuevo se clasifica.
- VM raw intake: no verificable desde VPS (fuera de scope de este pase).

**Propuesta (NO ejecutada — requiere aprobación humana explícita):**
1. **Diagnóstico del 500** del worker en `granola.*` antes de cualquier reinicio: capturar el stack del lado worker (`journalctl --user -u umbral-worker --since "1 day ago" | grep -i granola`) — pendiente segundo pase.
2. Si el problema fuese código vivo viejo (worker corriendo desde 2026-05-08 + posibles commits posteriores que tocan `worker/tasks/granola*` o `worker/notion_client.py`): se propone `systemctl --user restart umbral-worker` **previa aprobación de David**.
3. Decidir si `granola-gap-check.sh` debe agregarse al crontab real o si su comentario es legacy aspiracional.
4. Auditar si la VM Windows aún corre `granola_watcher.py` (handoff a Copilot-Windows según skill `windows-vps-execution-split`).

---

### Resumen ejecutivo

| Sistema | Estado runtime | Última escritura confirmada | Acción propuesta |
|---|---|---|---|
| sistema-editorial-rick | ✅ activo (cron `15 */6 * * *`) | 2026-05-20T16:15:35Z (page `35a5f443-…e36d1`, rows 202-205) | ninguna |
| bandeja-de-revision-rick | ⚠️ writer no registrado en worker | 2026-05-15T07:38:53Z (solo label `trigger`, no escritura real) | decidir writer canónico antes de tocar nada |
| transcripciones-granola | ❌ procesamiento inactivo + classify V2 con HTTP 500 | 2026-05-11T22:22:58Z (`granola.classify_raw`) | diagnóstico worker + autorización para restart |

**Reglas respetadas:** no reinicié servicios, no edité Notion, no toqué config ni código fuera de este Log. Cualquier restart de `umbral-worker` o cambio de crontab queda explícitamente pendiente de autorización humana.
