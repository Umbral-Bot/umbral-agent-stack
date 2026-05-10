# O16.2 — Execution plan (2026-05-10)

**Owner:** Copilot Chat (autonomous mandate, dm@umbralbim.cl)
**Hilo origen:** Coordinador de Agentes / Automatización Agentes
**Status:** PLAN. Pendiente ratificación + ejecución por David / Copilot-VPS.
**Deadline:** Friday retro 2026-06-26.
**Sponsorship:** $21,619 expira 2026-07-30.

## Acceptance criterion (no negociar)

> Bot Umbral en producción cita un párrafo buildingSMART/IFC con `aeco-kb-es-vYYYYMMDD`
> + URL fuente visible en la respuesta, durante el Friday retro 2026-06-26.

## Estado actual triple-check

| Componente | Repo dice | Azure deployed | VPS verifica |
|---|---|---|---|
| Bicep umbrella `aeco-kb-pipeline.bicep` | OK commit `0659b06b` | NO deployed (rg-umbral-agents-prod no tiene los 3 jobs aún) | n/a (es Azure, no VPS) |
| 3 imágenes ACA Jobs en GHCR | Dockerfiles OK | n/a | NO buildeadas todavía (bandwidth Docker pendiente) |
| RBAC UAMI cross-RG (Search Index Data Reader, Cognitive Services OpenAI User) | Documentado | ✅ Aplicado 2026-05-08 (audit `2026-05-08-o16-2-smoke-deploy.md`) | n/a |
| Foundry connection `aeco-kb-search` | Patch `foundry_connection.py` API nueva | ✅ Creada 2026-05-08 (PUT 200, AAD, isDefault=true) | n/a |
| Foundry project system-MI roles sobre Search | Documentado | ✅ Aplicado 2026-05-08 | n/a |
| Seeds `iram.yaml` + `nmx.yaml` con key `doc_id` | ✅ Branch `coord-o16/fix-o16-2-seed-doc-id-key` commit `3cc2cc5b` (2026-05-10) | n/a | n/a |
| Pipeline run buildingsmart | Script existe | NO corrido | n/a |
| File Search wiring `AgenteUB` → `aeco-kb-es-current` | Runbook NO existe aún | NO configurado en portal | n/a |
| Smoke `smoke_agenteub_kb.py` | Script existe | NO corrido | n/a |

**Net:** Blockers 1 (key fix) + 4 (RBAC) están cerrados. Quedan 3 (build+deploy infra),
5 (run+verify), 6 (portal wiring), 7 (smoke). El path crítico es **build+push 3 imágenes**.

## Cronograma propuesto (7 semanas hasta retro)

| Semana | Hito | Owner | Bandwidth |
|---|---|---|---|
| 2026-05-12 a 05-16 | Merge PR seed fix → main | David / Copilot Merge Master | 5 min review |
| 2026-05-12 a 05-16 | Verificar RBAC live (prompt 1) | Copilot-VPS | 10 min |
| 2026-05-19 a 05-23 | Build + push 3 imágenes GHCR (prompt 2) | David (Docker local) o GitHub Actions | 1-2 h |
| 2026-05-19 a 05-23 | `az deployment group create` Bicep umbrella | Copilot-VPS o David | 15 min |
| 2026-05-26 a 05-30 | Run pipeline buildingsmart (prompt 3) | Copilot-VPS | 30 min run + 15 min verify |
| 2026-06-02 a 06-06 | Portal Foundry File Search wiring | David (manual portal) | 1 h |
| 2026-06-09 a 06-13 | Smoke `AgenteUB` cita IFC con índice + URL | Copilot-VPS | 15 min |
| 2026-06-16 a 06-20 | Buffer / fixes / re-run si hace falta | David + agentes | flexible |
| 2026-06-26 (Friday) | Retro con demo live | David | 30 min |

## Plan de ejecución detallado

### FASE A — Branch hygiene (✅ HECHO esta sesión)

- [x] Commit `3cc2cc5b` en `coord-o16/fix-o16-2-seed-doc-id-key` (seed key fix).
- [x] Push origin.
- [ ] PR a main (manual o automatizado por David / Copilot Merge Master).
- [ ] Merge a main tras review (5 min).

### FASE B — Verificación RBAC live (NO ejecutar deploy)

Ejecutar **prompt VPS 1** para confirmar que el RBAC del 2026-05-08 sigue activo.
Si algo regresó a estado anterior, re-aplicar antes de seguir.

### FASE C — Build + push 3 imágenes a GHCR

Ejecutar **prompt VPS 2** (o GitHub Actions equivalente).

Imágenes:
- `ghcr.io/umbral-bot/aeco-source-crawler:latest`
- `ghcr.io/umbral-bot/aeco-pdf-parser:latest`
- `ghcr.io/umbral-bot/aeco-index-pipeline:latest`

Después: `az deployment group create` del Bicep umbrella con las 3 imágenes referenciadas.

### FASE D — Run pipeline buildingsmart-only

Ejecutar **prompt VPS 3** con scope acotado:

```bash
bash scripts/aeco-kb/run_pipeline.sh buildingsmart
python scripts/aeco-kb/verify_kb.py --min-chunks 150
```

Si verify falla con < 150 chunks, abortar y diagnosticar (probable: 1+ PDF IFC bajó URL
en el blob pero parser falló — revisar `crudos/aeco/parsed/buildingsmart/*.chunks.jsonl`).

### FASE E — Portal Foundry File Search

Acción manual de David. El runbook `runbooks/o16-2-agenteub-filesearch-wiring.md` debe
existir antes del 2026-06-02 (se crea en una iteración futura de este coordinador o se
delega a hilo notion-governance / docs).

Tarea high-level:
1. Portal Foundry → AgenteUB → Tools → File Search → Add data source.
2. Seleccionar connection `aeco-kb-search`.
3. Seleccionar index `aeco-kb-es-current` (alias actual al `aeco-kb-es-vYYYYMMDD` más reciente).
4. Save + verify en chat playground (no smoke automatizado todavía).

### FASE F — Smoke AgenteUB

Ejecutar **prompt VPS 4** (Friday retro gate).

Asserts:
- Respuesta del bot contiene cadena `aeco-kb-es-v\d{8}`.
- Respuesta del bot contiene URL `standards.buildingsmart.org`.
- Respuesta del bot cita un párrafo (no solo "according to IFC...").
- Latencia < 30 s.

Si los 4 asserts pasan: O16.2 closed. Si falta alguno: rollback Friday demo a "showing
infra ready, smoke pending" + recuperar en sponsorship buffer hasta 2026-07-30.

## Restricciones operativas

- NUNCA tocar archivos RRSS (ver [cross-thread-vps-concurrency.md](../runbooks/cross-thread-vps-concurrency.md) §R2).
- NUNCA escribir a Notion desde este hilo.
- NUNCA `--no-verify` en commits.
- NUNCA `git push --force` sobre main.
- Branch prefix obligatorio `coord-o16/*`.
- Si `git status --short` no está limpio en VPS: ABORTAR y reportar.

## Rollback paths por fase

| Fase | Rollback |
|---|---|
| A | `git revert 3cc2cc5b` (no toca infra ni Azure) |
| B | RBAC ya idempotente vía `az role assignment create` — re-aplicar si baja |
| C | `az deployment group delete` + borrar tags `:latest` en GHCR (no hay producción dependiendo aún) |
| D | Borrar blob `crudos/aeco/raw/buildingsmart/*` y `parsed/buildingsmart/*`; index `aeco-kb-es-vYYYYMMDD` queda hasta nuevo run |
| E | Portal: remove File Search data source — agente vuelve a stateless |
| F | Si smoke falla, no rollback necesario — solo no-promote a producción demo |

## Stop conditions (abortar todo el plan)

- Sponsorship credit drops a < $5,000 (revisar) antes del 2026-06-26.
- Foundry resource `umbralbim-resource` se vuelve no-disponible.
- Search service `srch-umbral-kb-prod` cambia tier o se borra.
- David da kill explícito al objetivo.

## Decisión pendiente (David)

- [ ] Aprobar este plan.
- [ ] Confirmar bandwidth Docker (1 sesión de 1-2h en próximas 2 semanas) o delegar a CI.
- [ ] Confirmar quién corre los 4 prompts VPS (Copilot-VPS por defecto).
- [ ] Confirmar agendar el portal wiring en calendario.

## Referencias

- Decisión scope: [2026-05-10-o16-2-buildingsmart-only-decision.md](2026-05-10-o16-2-buildingsmart-only-decision.md)
- Kill list: [2026-05-10-q2-runtime-focus-and-kill-list.md](2026-05-10-q2-runtime-focus-and-kill-list.md)
- Política cross-thread: [docs/runbooks/cross-thread-vps-concurrency.md](../runbooks/cross-thread-vps-concurrency.md)
- Audit previo: [2026-05-08-o16-2-smoke-deploy.md](2026-05-08-o16-2-smoke-deploy.md)
- Seed fix branch: `coord-o16/fix-o16-2-seed-doc-id-key` commit `3cc2cc5b`
