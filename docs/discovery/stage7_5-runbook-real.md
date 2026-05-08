# Stage 7.5 — Runbook real (end-to-end sobre una page)

Procedimiento exacto para correr `stage7_5_copy_writer.py` por primera vez
contra Notion live, sobre **una sola** propuesta. Todo en la VPS bajo el
usuario `rick`, con OpenClaw gateway corriendo en `127.0.0.1:18789`.

> Hilo D integration: el writer ya cablea `build_copy_prompt` al helper
> canónico de `scripts/discovery/eval_stage7_5_copy.py` (que carga
> `prompts/rick/linkedin-copy-{system,user}.md`). El mapeo de Estado se
> hace en código (`ESTADO_LIVE_MAP`): spec `En revisión` → live
> `Revisión pendiente`; spec `Rechazado` → live `Descartado`. **No** se
> renombra Notion UI.

## 0. Pre-flight

```bash
cd ~/umbral-agent-stack
set -a; source ~/.config/openclaw/env; set +a
source .venv/bin/activate

# Gateway debe estar arriba.
curl -fsS http://127.0.0.1:18789/healthz >/dev/null && echo OK

# NOTION_API_KEY tiene que estar exportado por el env file.
test -n "$NOTION_API_KEY" && echo NOTION_OK
```

Estado SQLite esperado para la propuesta target (`--proposal-id 1`):

```bash
python -c "
import sqlite3
c=sqlite3.connect('/home/rick/.cache/rick-discovery/state.sqlite')
c.row_factory=sqlite3.Row
print(dict(c.execute('SELECT id,titular,notion_page_id,image_status,copy_status FROM proposals WHERE id=1').fetchone()))
"
```

Debe mostrar: `image_status='ok'`, `notion_page_id` no nulo,
`copy_status=None`.

## 1. Dry-run (NO toca Notion, NO llama LLM)

```bash
python scripts/discovery/stage7_5_copy_writer.py --proposal-id 1 --dry-run
```

Output esperado (canónico):

```
stage7_5 dry-run: 1 candidate(s)
  id=1 status=(null) page=<page-id> titular='<titular>'
stage7_5: copy_ready=0 skipped_existing=0 failed=0 dry_run=True force=False
```

⚠️ **Parada de seguridad**: si aparece cualquier campo inesperado
(`failed=...>0`, candidatos múltiples, error de schema), abortar y pegar
output crudo al PR antes de seguir.

## 2. Smoke real (1 page, sin --dry-run)

Sólo después de OK humano explícito sobre el dry-run:

```bash
python scripts/discovery/stage7_5_copy_writer.py --proposal-id 1
```

Output esperado:

```
copy_ready proposal_id=1 chars=<N> cost_usd=<X.XXXXX>
stage7_5: copy_ready=1 skipped_existing=0 failed=0 dry_run=False force=False
```

## 3. Verificar Notion live

```bash
python - <<'PY'
import os, json, httpx
page_id = "<reemplazar con notion_page_id>"
r = httpx.get(
    f"https://api.notion.com/v1/pages/{page_id}",
    headers={
        "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
        "Notion-Version": "2025-09-03",
    },
    timeout=30.0,
)
r.raise_for_status()
props = r.json()["properties"]
copy_prop = props.get("Copy LinkedIn", {}).get("rich_text", [])
copy = "".join(s["plain_text"] for s in copy_prop)
estado = props.get("Estado", {})
print("Estado:", json.dumps(estado, ensure_ascii=False, indent=2))
print("Copy chars:", len(copy))
print("Copy preview:")
print(copy[:300])
PY
```

Esperado: `Estado.status.name == "Revisión pendiente"` y `Copy LinkedIn`
poblado con texto entre 400 y 3000 chars.

## 4. Verificar evento ops_log

```bash
tail -20 ~/.config/umbral/ops_log.jsonl \
  | jq 'select(.event=="stage7_5.copy_written")'
```

Debe haber un registro con `proposal_id=1`, `notion_page_id`, `copy_len`,
`model`, `cost_usd`.

## 5. Verificar dashboard "Copy review pending"

```bash
python scripts/discovery/stageX_pipeline_dashboard.py
```

La sección **Copy review pending** debe listar la page id 1.

## 6. Comentario @David (si está configurado)

Si `DAVID_NOTION_USER_ID` está seteado en el env, postear un comentario
de revisión idempotente sobre la page:

```bash
python -c "
import os
from scripts.discovery.stage7_5_post_review_comment import post_review_comment
from scripts.discovery.stage7_5_copy_writer import NotionClient
client = NotionClient(os.environ['NOTION_API_KEY'])
post_review_comment(client, '<page-id>', '<copy-text-preview>')
"
```

## 7. ⛔ NO seguir a Stage 9

Stage 9 (LinkedIn publish) sólo corre cuando David autoriza desde Notion
(Estado → `Autorizado`). Stage 7.5 termina aquí.

## Paradas de seguridad consolidadas

- Dry-run con campos inesperados → abort, pegar diff, pedir humano.
- Validation fail (length / URL / tokens prohibidos) → `copy_status=failed`,
  NO PATCH Notion, reportar.
- Notion 4xx → NO retry, log y pedir humano.
- NO mergear PR sin OK explícito de David post-review en Notion.
