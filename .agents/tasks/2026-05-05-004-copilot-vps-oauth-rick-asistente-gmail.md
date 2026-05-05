# Task: OAuth setup for `rick.asistente@gmail.com` (Rick multi-canal Ola 1b)

- **Created**: 2026-05-05
- **Created by**: Copilot Chat (notion-governance / umbral-agent-stack-copilot workspace)
- **Assigned to**: Copilot VPS (acceso SSH real a `rick@hostinger`) + David (acciones manuales en Google + Notion)
- **Type**: provisioning (mixed: console manual + VPS storage + smoke test)
- **Blocking**: Ola 1b del modelo organizacional (`notion-governance/docs/architecture/15-rick-organizational-model.md` §3.5 + §6) y §O15.1b del plan Q2 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`).
- **Depends on**: O15.0 ✅ (Ola 0 cleanup completada commit `45ff7e1`).
- **Decision reference**: §3.5 del modelo organizacional v1.1 → multi-canal real con cuenta `rick.asistente@gmail.com` propia, política Calendar `propose+confirm`, no bypass.

---

## Contexto

Rick (agente `main` en OpenClaw) hoy solo tiene canal Telegram. Para cumplir §3.1 (Rick = único punto de contacto humano) en todos los canales que David usa diariamente, necesita identidad real y OAuth en:

| Canal | Cuenta | Permiso necesario | Política |
|---|---|---|---|
| Notion | `rick.asistente@gmail.com` invitado al workspace | guest con acceso a páginas relevantes | watcher por menciones `@Rick` |
| Gmail | `rick.asistente@gmail.com` | OAuth read+send (scope: `gmail.modify` o `gmail.readonly` + `gmail.send`) | Rick lee y responde desde su propia dirección, NO desde la de David |
| Calendar | calendar de David compartido con `rick.asistente@gmail.com` permiso edit | OAuth `calendar.events` | `propose+confirm`: Rick crea eventos `tentative` o con título `[PROPUESTA] ...`, David confirma manualmente |

WhatsApp queda fuera de scope (Q3 condicional).

---

## Acciones requeridas (en orden)

### 1. Acciones manuales de David (FUERA de VPS — bloqueante)

**1.1 Crear cuenta Google `rick.asistente@gmail.com`** (si no existe).
- Verificar 2FA habilitado.
- Anotar contraseña en password manager personal de David (NO commitear, NO pegar en chat).

**1.2 Notion guest invite**
- Workspace David Moreira → Settings → Members → Invite guest → `rick.asistente@gmail.com`.
- Permisos: empezar con acceso a páginas hub raíz que David quiera que Rick monitoree (NO full workspace). Refinar después.
- Confirmar que Rick aparece como guest en `Configuración del workspace`.

**1.3 Calendar share**
- Calendar principal de David → Settings → Share with specific people → agregar `rick.asistente@gmail.com` con permission **"Make changes to events"** (necesario para crear propuestas tentativas).
- NO darle "Make changes and manage sharing".

**1.4 Google Cloud Console — OAuth client**
- Proyecto: `umbral-rick-channels` (crear nuevo si no existe).
- Habilitar APIs: **Gmail API**, **Google Calendar API**.
- Pantalla de consentimiento OAuth: tipo `External`, app name `Rick Asistente`, user support email = David, scopes:
  - `https://www.googleapis.com/auth/gmail.modify`
  - `https://www.googleapis.com/auth/gmail.send`
  - `https://www.googleapis.com/auth/calendar.events`
- Test users: agregar `rick.asistente@gmail.com` y `david@umbralbim.cl` (o el que David use).
- Crear OAuth client ID tipo **Desktop app** (más simple para flow CLI).
- Descargar JSON `credentials.json`. **NO commitear.** Pasar a David por canal seguro (no Telegram, no email).

**1.5 Notion integration token (para watcher API)**
- notion.so/profile/integrations → New integration → name `Rick Watcher` → workspace David Moreira → tipo `Internal`.
- Capabilities: `Read content`, `Update content`, `Insert content` (mínimo). NO User information sin restricción.
- Copiar `Internal Integration Token` (`secret_xxx...`). **NO commitear.**
- En cada página/database que Rick deba monitorear: `Connect to integration` → `Rick Watcher`.

---

### 2. Acciones VPS (Copilot VPS, después de que David entregue credenciales)

**2.1 Verificar pre-requisitos**

```bash
ssh rick@<vps-host>
ls -la ~/.config/openclaw/env  # verificar que existe (Telegram token ya está acá)
ls -la ~/.config/openclaw/secrets/ 2>/dev/null || mkdir -p ~/.config/openclaw/secrets && chmod 700 ~/.config/openclaw/secrets
```

**2.2 Almacenar credenciales (David las pasa por canal seguro a Copilot VPS)**

Estructura esperada en `~/.config/openclaw/secrets/`:

```
secrets/
├── google-oauth-client.json       # credentials.json descargado (chmod 600)
├── google-oauth-token.json        # generado por flow OAuth en 2.3 (chmod 600)
└── notion-rick-watcher.token      # token Notion integration (chmod 600, contenido único = secret_xxx)
```

```bash
chmod 600 ~/.config/openclaw/secrets/*.json ~/.config/openclaw/secrets/*.token
ls -la ~/.config/openclaw/secrets/
```

**2.3 Ejecutar OAuth flow Google (genera `google-oauth-token.json`)**

Crear script helper `~/umbral-agent-stack/scripts/oauth/google-rick-bootstrap.py`:

```python
#!/usr/bin/env python3
"""One-shot OAuth bootstrap for rick.asistente@gmail.com.
Reads google-oauth-client.json, opens device flow URL, writes google-oauth-token.json.
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]
SECRETS = Path.home() / ".config/openclaw/secrets"
flow = InstalledAppFlow.from_client_secrets_file(
    str(SECRETS / "google-oauth-client.json"), SCOPES
)
# Use console flow (no browser on VPS)
creds = flow.run_console()
(SECRETS / "google-oauth-token.json").write_text(creds.to_json())
print("OK token saved")
```

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
pip install google-auth-oauthlib google-api-python-client
python scripts/oauth/google-rick-bootstrap.py
# David sigue el URL en su navegador, loguea como rick.asistente@gmail.com,
# acepta scopes, copia código de vuelta al terminal.
chmod 600 ~/.config/openclaw/secrets/google-oauth-token.json
```

**2.4 Smoke tests (read-only, NO mutar nada todavía)**

```bash
# Gmail: leer último mensaje en INBOX
python -c "
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file(
    str(Path.home() / '.config/openclaw/secrets/google-oauth-token.json'))
svc = build('gmail', 'v1', credentials=creds)
r = svc.users().messages().list(userId='me', maxResults=1).execute()
print('Gmail OK, last msg id:', r.get('messages', [{}])[0].get('id', 'NONE'))
"

# Calendar: listar próximos 3 eventos
python -c "
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timezone
creds = Credentials.from_authorized_user_file(
    str(Path.home() / '.config/openclaw/secrets/google-oauth-token.json'))
svc = build('calendar', 'v3', credentials=creds)
now = datetime.now(timezone.utc).isoformat()
r = svc.events().list(calendarId='primary', timeMin=now, maxResults=3, singleEvents=True, orderBy='startTime').execute()
for e in r.get('items', []):
    print('Cal:', e['start'].get('dateTime', e['start'].get('date')), '-', e.get('summary', '(no title)'))
"

# Notion: ping integration (lista usuarios accesibles → debe incluir rick.asistente)
TOKEN=$(cat ~/.config/openclaw/secrets/notion-rick-watcher.token)
curl -s -H "Authorization: Bearer $TOKEN" -H "Notion-Version: 2022-06-28" \
  https://api.notion.com/v1/users | python -c "import sys, json; d = json.load(sys.stdin); print('Notion OK, users:', [u['name'] for u in d.get('results', [])])"
```

**2.5 Registrar canales en `~/.config/openclaw/env`** (NO commitear este archivo, está en VPS solamente)

Agregar al final de `~/.config/openclaw/env`:

```bash
# Multi-canal Rick — añadido 2026-05-05 (task 004)
GOOGLE_OAUTH_CLIENT_FILE=/home/rick/.config/openclaw/secrets/google-oauth-client.json
GOOGLE_OAUTH_TOKEN_FILE=/home/rick/.config/openclaw/secrets/google-oauth-token.json
NOTION_RICK_WATCHER_TOKEN_FILE=/home/rick/.config/openclaw/secrets/notion-rick-watcher.token
```

(Las skills `gmail-router`, `calendar-propose`, `notion-mention-router` se crearán en task 005 y leerán de estas env vars.)

---

### 3. Reportar (append al final de este archivo)

Agregar sección `## Resultado OAuth setup 2026-05-05` con:

1. Confirmación 1.1-1.5 hechos por David (sí/no por ítem).
2. Output de los 3 smoke tests (Gmail msg id, Calendar próximos 3, Notion users) — **redactar ID/email sensibles si aparecen**.
3. Permisos finales de `~/.config/openclaw/secrets/*` (`ls -la`).
4. Confirmación de que `~/.config/openclaw/env` quedó actualizado con las 3 nuevas vars.
5. Cualquier blocker (ej. scope OAuth rechazado, integration Notion sin acceso a página esperada, etc.).

Commit como `report(.agents/004): OAuth rick.asistente@gmail.com setup completed`.

---

## Anti-patterns prohibidos

- ❌ NO commitear `credentials.json`, `token.json`, ni el integration token Notion. **Aplicar `secret-output-guard` skill antes de cada commit/output.**
- ❌ NO darle a Rick permission "Make changes and manage sharing" en Calendar (solo "Make changes to events").
- ❌ NO pedirle a David `gmail.modify` + `gmail.send` en una segunda app si ya están en este OAuth client (un solo client cubre ambos scopes).
- ❌ NO crear skills/agents OpenClaw todavía (eso es task 005). Esta task es 100 % provisioning + smoke test.
- ❌ NO probar escritura (send email, create event, edit Notion page) hasta que David apruebe explícitamente. Smoke tests son read-only.
- ❌ NO automatizar refresh del OAuth token con cron en esta task (Google token refresh es automático vía librería; manual rotation va en task de runbook).

---

## Notas

- Una vez completada esta task, Rick tiene **identidad y permisos** en los 3 canales pero todavía NO sabe usarlos. La activación real (skills + handlers + binding al agente `main`) va en task 005.
- Si OAuth se atasca por aprobación Google (scopes sensibles requieren verificación de la app), se puede mantener `Testing` mode con max 100 test users — suficiente para 2 (David + Rick).
- Refresh token Google expira a los 7 días en `Testing` mode. Para uso continuado >7 días sin re-auth manual, hay que mover la app a `In production` (NO requiere verificación si test users ≤100 y no hay scopes restricted, pero validar antes).
