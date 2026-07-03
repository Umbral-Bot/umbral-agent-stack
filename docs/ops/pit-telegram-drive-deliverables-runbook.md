# PIT — Entrega Telegram vía Google Drive (runbook PIT-TG-DRIVE)

- **Status:** v1 — 2026-07-03. Implementa la entrega ejecutiva post-torneo: deck `.pptx` en Drive compartido Rick↔David + link por Telegram (NUNCA el archivo adjunto).
- **Piezas:** Worker [`google_drive.upload_file` / `upload_presentation`](../../worker/tasks/google_drive.py) · builder [`pit_build_outcome_deck.py`](../../scripts/pit/pit_build_outcome_deck.py) · orquestador [`pit_deliver_telegram_pack.py`](../../scripts/pit/pit_deliver_telegram_pack.py) · skill [PIT §Entrega Telegram](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md).
- **Relacionados:** [pit-process-index.md](pit-process-index.md) (paso 8b) · [diagnóstico 2026-07-03](../audits/agent-tournament-pit-deep-diagnosis-2026-07-03.md) · formato Telegram [queue-002 §9](pit-tournament-queue-002-sharepoint-acc-umbral-bim.md).

---

## 1. Setup OAuth Google (cuenta Rick) — una sola vez

> Todo esto ocurre FUERA del repo. Jamás commitear client secret, refresh token ni IDs sensibles.

1. **Proyecto Google Cloud** (cuenta Rick): <https://console.cloud.google.com> → crear/reusar proyecto (p.ej. `umbral-rick-drive`).
2. **Habilitar API:** APIs & Services → Library → **Google Drive API** → Enable.
3. **OAuth consent screen:** tipo *External* (o *Internal* si Workspace), scope `.../auth/drive.file` (mínimo suficiente: solo archivos creados por la app). Agregar la cuenta Rick como test user si queda en Testing.
4. **Credenciales:** APIs & Services → Credentials → *Create credentials* → **OAuth client ID** → tipo *Desktop app*. Guardar `client_id` y `client_secret`.
5. **Refresh token** (flow local con `google-auth-oauthlib`, correr una vez en cualquier máquina con browser):

   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_config(
       {"installed": {"client_id": "<CLIENT_ID>", "client_secret": "<CLIENT_SECRET>",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"}},
       scopes=["https://www.googleapis.com/auth/drive.file"],
   )
   creds = flow.run_local_server(port=0)   # login con la CUENTA RICK
   print(creds.refresh_token)
   ```

   Autorizar con la **cuenta de Rick** (la dueña de la carpeta). Copiar el refresh token.

## 2. Carpeta compartida + FOLDER_ID

1. En el Drive de Rick crear la carpeta (p.ej. `PIT — decks Umbral`).
2. Compartir con la cuenta de David (rol *Lector* alcanza; *Editor* si David quiere mover archivos).
3. **Obtener el FOLDER_ID desde la URL**: abrir la carpeta en el browser —

   ```text
   https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv
                                          └────────── FOLDER_ID ─┘
   ```

   Todo lo que está después de `folders/` (hasta `?` si hay query string).

> Nota scope: con `drive.file` la app solo ve archivos que ella creó. La carpeta destino se referencia por ID como `parents` del upload — no hace falta scope `drive` completo.

## 3. Env vars (VPS)

Añadir a `~/.config/openclaw/env` (misma topología del runbook 62 §1.4.1; placeholders en [`openclaw/env.template`](../../openclaw/env.template)):

```bash
export GOOGLE_DRIVE_PIT_FOLDER_ID="<folder id §2>"
export GOOGLE_DRIVE_OAUTH_CLIENT_ID="<client id §1>"
export GOOGLE_DRIVE_OAUTH_CLIENT_SECRET="<client secret §1>"
export GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN="<refresh token §1>"
export GOOGLE_DRIVE_SHARE_WITH="<email David>"   # opcional: re-share reader post-upload
```

```bash
chmod 600 ~/.config/openclaw/env
```

Dependencias Python (VPS, dentro del venv del stack):

```bash
pip install google-api-python-client google-auth google-auth-oauthlib
```

(En el repo: `worker/requirements.txt` y extra `drive` de `pyproject.toml`.)

## 4. Smoke manual

```bash
cd ~/umbral-agent-stack && source .venv/bin/activate && source ~/.config/openclaw/env

# 1) Dry-run (sin red): deck + telegram_pack.json a partir de un outcome cerrado
python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id> --dry-run
# → PIT_DELIVER_PACK_DRY_OK | deck=... | pack=...

# 2) Upload real de un archivo dummy vía el handler Worker
python - <<'PY'
from worker.tasks.google_drive import handle_google_drive_upload_file
import tempfile, os
fd, p = tempfile.mkstemp(suffix=".txt"); os.write(fd, b"pit drive smoke"); os.close(fd)
print(handle_google_drive_upload_file({"local_path": p, "filename": "pit-drive-smoke.txt"}))
PY
# → ok: True + web_view_link
```

**Verificación David:** abrir el `web_view_link` desde la cuenta de David (o ver la carpeta compartida) — el archivo debe ser visible sin pedir acceso.

## 5. Integración post-torneo (orden)

1. Judge + winner con gate David → Rick escribe `pit/<pit_id>/outcome/pit_outcome_report.yaml` (con `winner.david_gate` ≠ pending).
2. `python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id>` → `PIT_DELIVER_PACK_OK | drive_url=…`.
3. Rick envía por Telegram la plantilla de `summary_lines` (≤12 líneas + link) — skill §Entrega Telegram.
4. Rick completa `deliverables:` en el outcome (`drive_deck_url`, `drive_file_id`, `telegram_sent_at`).
5. Continúa el post-torneo normal: handoff mejora continua → archive.

Opcionalmente el deck se puede regenerar solo: `python scripts/pit/pit_build_outcome_deck.py --outcome <path>` → `PIT_DECK_BUILD_OK`.

## 6. Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `PIT_DELIVER_PACK_FAIL \| reason=drive_not_configured` | faltan env vars §3 | completar env + `source` |
| `PIT_DELIVER_PACK_FAIL \| reason=winner_pending` | outcome sin winner o `david_gate` pending | cerrar judge con gate David primero |
| `403 insufficientPermissions` / `insufficient authentication scopes` | refresh token emitido sin `drive.file` | regenerar token §1.5 con el scope correcto |
| `404 File not found` sobre el folder | FOLDER_ID mal copiado o carpeta de otra cuenta | re-copiar de la URL §2; el token debe ser de la cuenta dueña |
| `invalid_grant` al refrescar | refresh token revocado/expirado (app en Testing expira a los 7 días) | publicar la OAuth app o regenerar token |
| David no puede abrir el link | carpeta no compartida / permiso no propagado | compartir carpeta §2 o setear `GOOGLE_DRIVE_SHARE_WITH` |
| `drive_folder_id does not match` | task input intentó otra carpeta | por diseño: solo `GOOGLE_DRIVE_PIT_FOLDER_ID` |
| Deck sin datos ("—") | outcome con placeholders `<...>` de la plantilla | completar el outcome real |

## 7. Reglas duras (v1)

- NUNCA `sendDocument` del `.pptx` por Telegram — solo link Drive.
- Sin Drive configurado: fallback texto + MC judge hint; Rick no inventa links.
- Uploads SOLO a `GOOGLE_DRIVE_PIT_FOLDER_ID` (guard en el handler + verificación de `parents` post-upload).
- El prototipo HTML sigue en túnel + Mission Control — nunca URL pública.
- Alternativa documentada (NO implementar en v1 salvo bloqueo OAuth): `rclone copy` al mount `G:\` — solo Windows; la VPS usa API.
