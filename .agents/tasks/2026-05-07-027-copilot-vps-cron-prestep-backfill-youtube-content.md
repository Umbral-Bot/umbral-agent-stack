# Task 027 — Cron prestep: backfill youtube content antes de stage4

- **id**: 2026-05-07-027-copilot-vps-cron-prestep-backfill-youtube-content
- **assigned_to**: copilot-vps
- **status**: DONE — implementado 2026-05-08 (ver sección "Implementado" abajo)
- **created_by**: rick
- **created_at**: 2026-05-07
- **audited_by**: copilot-vps (sesión Claude Opus 4.7)
- **audited_at**: 2026-05-08

## Intent original

Agregar un "prestep" al cron que corre `stage4_push_notion.py` para que ANTES
ejecute `scripts/discovery/backfill_youtube_content.py --commit`, garantizando
que cada item promovido `canal=youtube` tenga `contenido_html` poblado antes de
que stage4 cree la page en Notion (evitando `created_no_body`).

Premisa de la consigna: "cambios chicos, idealmente 1 línea en el wrapper o en
la cron line".

## VPS Reality Check (auditoría 2026-05-08)

Comandos ejecutados sobre el repo en `/home/rick/umbral-agent-stack` (HEAD=`main`)
y sobre el cron del usuario `rick` en la VPS.

### Repo dice X

- Existe `scripts/discovery/backfill_youtube_content.py` (mergeado en PR #343).
- Existe `scripts/discovery/stage4_push_notion.py` (preexistente).
- Hay reports recientes de stage4: `reports/stage4-push-20260507T170310Z-commit.json`
  (started 17:02:43Z, processed=13, created=13, errors=0).
- La consigna asume que existe **un wrapper** o **una línea de cron** que invoca
  stage4 a la cual se le antepone el backfill.

### VPS muestra Y

1. **El task file `.agents/tasks/2026-05-07-027-...md` no existía** al iniciar
   la sesión (este archivo se creó como output de la auditoría):
   ```bash
   ls .agents/tasks/2026-05-07-027*  # No such file
   git log --all -- '.agents/tasks/*027-cron*'  # 0 commits
   ```
2. **No hay cron de stage4 ni de discovery.** `crontab -l` lista 15 entradas:
   `health-check, supervisor, sim-daily, notion-poller, sim-report,
   daily-digest, sim-to-make, e2e-validation, ooda-report, scheduled-tasks,
   quota-guard, notion-curate, openclaw-runtime-snapshot, dashboard-rick,
   openclaw-panel`. Ninguna invoca `stage2_ingest`, `stage3_promote`,
   `stage4_push_notion`, ni `backfill_*`.
3. **No hay timers user systemd** que matcheen stage/discovery/youtube/backfill:
   `systemctl --user list-timers --all | grep -iE "stage|discov|youtube|backfill"`
   → vacío.
4. **No hay wrapper bash** en `scripts/vps/*.sh` que llame a las stage scripts:
   `grep -lE "stage4|discovery|backfill" scripts/vps/*.sh` → vacío.
   `grep -rE "stage4_push_notion" --include='*.sh' .` → 0 hits.
5. **Las últimas corridas de stage4 fueron manuales** (Rick desde shell). No hay
   wrapper de invocación reproducible.
6. **Las IDs requeridas por stage4 (`--database-id`, `--data-source-id`,
   `--referentes-data-source-id`) no están en `~/.config/openclaw/env`** ni
   en ningún archivo del repo. Rick las pasa manualmente cada vez.

## Bloqueo / decisión requerida

"Agregar 1 línea al wrapper / cron line" no aplica: hay que **crear la
infraestructura completa** desde cero. Eso son varias decisiones de runtime
que exceden el alcance "cambios chicos" de la consigna y que no debo tomar
solo:

- **D1 — ¿Stage4 debería tener cron?** Hoy es manual. Que sea cron es una
  decisión operativa.
- **D2 — Cadencia.** ¿Cada hora? ¿cada 6h? ¿solo a horarios específicos?
- **D3 — Gating.** Si el backfill falla parcial (algunos videos sin contenido),
  ¿stage4 corre igual y los marca `created_no_body`, o aborta?
- **D4 — Storage de IDs.** ¿`database-id`, `data-source-id`,
  `referentes-data-source-id` se mueven a env (`~/.config/openclaw/env`)
  o quedan hardcoded en el wrapper?
- **D5 — Rate / cuotas.** ¿Cap de items por corrida (`--limit`)?

## Recomendación (cuando se desbloquee)

Implementación mínima sugerida una vez decidido lo anterior:

1. Agregar a `~/.config/openclaw/env`:
   ```
   UMBRAL_DISCOVERY_DATABASE_ID=b9d3d8677b1e4247bafdcb0cc6f53024
   UMBRAL_DISCOVERY_DATA_SOURCE_ID=9d4dbf65-664f-41b4-a7f6-ce378c274761
   UMBRAL_DISCOVERY_REFERENTES_DS_ID=<TBD por Rick>
   ```
2. Crear `scripts/vps/discovery-publish-cron.sh`:
   ```bash
   #!/usr/bin/env bash
   set -uo pipefail
   set -a; source ~/.config/openclaw/env; set +a
   cd ~/umbral-agent-stack
   source .venv/bin/activate
   # Prestep: backfill contenido_html para promovidos YouTube
   python scripts/discovery/backfill_youtube_content.py --commit || \
     echo "[$(date -Iseconds)] backfill_youtube_content failed (continuando con stage4)" >&2
   # Stage 4: push a Notion
   exec python -m scripts.discovery.stage4_push_notion \
     --database-id  "$UMBRAL_DISCOVERY_DATABASE_ID" \
     --data-source-id "$UMBRAL_DISCOVERY_DATA_SOURCE_ID" \
     --referentes-data-source-id "$UMBRAL_DISCOVERY_REFERENTES_DS_ID" \
     --commit
   ```
3. Crontab line (cadencia a definir por Rick):
   ```
   15 * * * * bash ~/umbral-agent-stack/scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1
   ```

## Quality gates (cuando se desbloquee)

- 0 secrets en logs (`grep AIza /tmp/discovery_publish.log` debe ser vacío).
- Smoke run dry-run primero (sin `--commit`) para validar IDs.
- Verificar `journalctl -t cron --since '15 min'` muestra ejecución.

## Output de esta sesión

- Branch: `copilot-vps/027-cron-prestep-backfill-youtube`
- Único cambio: este task file (auditoría + bloqueo formal).
- 0 cambios a runtime, 0 cambios a crontab, 0 cambios a env.

## Próximo agente

Cuando Rick responda D1–D5, cualquier agente puede implementar el wrapper +
crontab line en una PR de seguimiento usando la "Recomendación" de arriba como
referencia.

---

## Implementado 2026-05-08

Rick respondió D1–D5; implementación delivered en esta misma branch.

### Decisiones aplicadas

| Decisión | Respuesta de Rick | Implementación |
|---|---|---|
| **D1** Automatizar | Sí, cron user-level rick | `crontab -e` para `rick`, no systemd |
| **D2** Cadencia | `15 */6 * * *` (cada 6h) | Línea agregada |
| **D3** Si backfill falla parcial | Continuar con stage4 (warning) | `if python ... ; then OK ; else WARN` (no `set -e` global) |
| **D4** Storage IDs | `~/.config/openclaw/env` | 3 vars `UMBRAL_DISCOVERY_*` agregadas (chmod 600 preservado) |
| **D5** Cap (`--limit`) | Sin tope | Wrapper no pasa `--limit` |

### Cambios entregados

1. **`~/.config/openclaw/env`** (no en repo, fuera de git):
   ```
   UMBRAL_DISCOVERY_DATABASE_ID=b9d3d8677b1e4247bafdcb0cc6f53024
   UMBRAL_DISCOVERY_DATA_SOURCE_ID=9d4dbf65-664f-41b4-a7f6-ce378c274761
   UMBRAL_DISCOVERY_REFERENTES_DS_ID=afc8d960-086c-4878-b562-7511dd02ff76
   ```
   Validado vía `GET /v1/data_sources/<ds>` → HTTP 200, title="Referentes".
   Backup: `~/.config/openclaw/env.bak.027`.

2. **`scripts/vps/discovery-publish-cron.sh`** (chmod +x): wrapper bash que
   - source env
   - activa `.venv`
   - corre `backfill_youtube_content.py --commit` (continúa on failure, D3)
   - corre `python -m scripts.discovery.stage4_push_notion ... --commit`
   - soporta `DISCOVERY_PUBLISH_DRYRUN=1` para smoke

3. **Crontab user `rick`** (línea agregada):
   ```
   15 */6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1
   ```

### Verificación VPS Reality Check (2026-05-08)

```bash
$ crontab -l | grep discovery-publish
15 */6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1

$ DISCOVERY_PUBLISH_DRYRUN=1 bash scripts/vps/discovery-publish-cron.sh
[2026-05-07T18:24:35Z] discovery-publish: start ...
[2026-05-07T18:24:35Z] discovery-publish: prestep: backfill_youtube_content (commit)
pending=0 ok=0 not_found=0 extraction_error=0 skipped_no_video_id=0 commit=True
[2026-05-07T18:24:35Z] discovery-publish: prestep: backfill OK
[2026-05-07T18:24:35Z] discovery-publish: stage4: DRY-RUN (no --commit)
... pending_total: 0, processed: 0, errors: 0 ...
[2026-05-07T18:24:37Z] discovery-publish: stage4: OK
[2026-05-07T18:24:37Z] discovery-publish: done

$ bash scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1   # full --commit
$ tail /tmp/discovery_publish.log   # report stage4-push-20260507T182513Z-commit.json, errors=0
$ grep -E "AIza|api_key|secret_|Bearer |ntn_" /tmp/discovery_publish.log
$ echo $?   # 1 → 0 secrets
```

Backlog estaba vacío (0 pending) en esta primera corrida — esperado (drenado en
sesiones previas, PR #343). Próxima corrida scheduled: `00:15 UTC`. Cuando
nuevos items YouTube se promuevan a candidato, esta cadencia los procesará
sin requerir intervención manual.

### Reversibilidad

Para revertir:
- `crontab -e` → eliminar la línea `discovery-publish-cron.sh`.
- `cp ~/.config/openclaw/env.bak.027 ~/.config/openclaw/env`.
- `git revert <commit-impl>` para sacar el wrapper.
