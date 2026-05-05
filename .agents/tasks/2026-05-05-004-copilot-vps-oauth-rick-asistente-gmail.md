# Task: audit OAuth + multi-canal Rick state, close gaps only

- **Created**: 2026-05-05 (rev 2 — supersede de la versión inicial)
- **Created by**: Copilot Chat
- **Assigned to**: Copilot VPS (acceso SSH real a `rick@hostinger`)
- **Type**: audit (read-only) → gap-closure (write only si hace falta)
- **Blocking**: Ola 1b del modelo organizacional.
- **Depends on**: O15.0 ✅ commit `45ff7e1`.

---

## Contexto

Audit de repo local 2026-05-05 reveló que **mucho del setup OAuth multi-canal ya existe** (commits firmados con `rick.asistente@gmail.com`, `GOOGLE_CALENDAR_*` operativo en `.env`/`env.rick`, `NOTION_API_KEY` activo, `docs/35-gmail-token-setup.md` documentado). David confirma que pasos 1-6 de la versión inicial de esta task ya estaban hechos de antes.

**Esta task ya NO es "setup from scratch", es "verificar qué hay en VPS y completar SOLO lo que falta"**.

---

## Acciones requeridas (en orden)

### 1. Inventory state actual en VPS (read-only, NO mutar)

Antes de empezar: `cd ~/umbral-agent-stack && git pull origin main` para tener esta versión rev 2 de la task.

```bash
ssh rick@<vps-host>

# 1.1 Env vars relevantes (REDACTAR valores en el reporte; solo confirmar presencia/ausencia)
for var in NOTION_API_KEY NOTION_CONTROL_ROOM_PAGE_ID NOTION_GRANOLA_DB_ID \
           GOOGLE_CALENDAR_REFRESH_TOKEN GOOGLE_CALENDAR_CLIENT_ID GOOGLE_CALENDAR_CLIENT_SECRET \
           GOOGLE_GMAIL_REFRESH_TOKEN GOOGLE_GMAIL_CLIENT_ID GOOGLE_GMAIL_CLIENT_SECRET GOOGLE_GMAIL_TOKEN; do
  if grep -q "^${var}=" ~/.config/openclaw/env 2>/dev/null; then
    echo "$var=PRESENT"
  else
    echo "$var=MISSING"
  fi
done

# 1.2 Lista de archivos en secrets/ (si existe)
ls -la ~/.config/openclaw/secrets/ 2>/dev/null || echo "no secrets/ dir"

# 1.3 Verificar si Notion integration tiene acceso al workspace de David
set -a; source ~/.config/openclaw/env; set +a
curl -s -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2022-06-28" \
  https://api.notion.com/v1/users/me | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('NOTION_BOT_NAME=', d.get('name', 'N/A'))
print('NOTION_BOT_TYPE=', d.get('type', 'N/A'))
print('NOTION_BOT_OWNER=', d.get('bot', {}).get('owner', {}).get('type', 'N/A'))
"

# 1.4 Smoke test Calendar (read próximos 3 eventos) — usa el refresh token existente
cd ~/umbral-agent-stack
source .venv/bin/activate
python3 -c "
import os, requests
r = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': os.environ['GOOGLE_CALENDAR_CLIENT_ID'],
    'client_secret': os.environ['GOOGLE_CALENDAR_CLIENT_SECRET'],
    'refresh_token': os.environ['GOOGLE_CALENDAR_REFRESH_TOKEN'],
    'grant_type': 'refresh_token',
})
access = r.json()['access_token']
ev = requests.get('https://www.googleapis.com/calendar/v3/calendars/primary/events',
    headers={'Authorization': f'Bearer {access}'},
    params={'maxResults': 3, 'orderBy': 'startTime', 'singleEvents': 'true',
            'timeMin': '2026-05-05T00:00:00Z'}).json()
print('CAL_EVENT_COUNT=', len(ev.get('items', [])))
for e in ev.get('items', []):
    title = e.get('summary', '(sin título)')
    print('CAL', e.get('start', {}).get('dateTime', e.get('start', {}).get('date')), '-', title[:20] + '...')
" 2>&1 | head -10

# 1.5 Smoke test Gmail (SOLO si GOOGLE_GMAIL_REFRESH_TOKEN está presente)
if grep -q '^GOOGLE_GMAIL_REFRESH_TOKEN=' ~/.config/openclaw/env; then
  python3 -c "
import os, requests
r = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': os.environ['GOOGLE_GMAIL_CLIENT_ID'],
    'client_secret': os.environ['GOOGLE_GMAIL_CLIENT_SECRET'],
    'refresh_token': os.environ['GOOGLE_GMAIL_REFRESH_TOKEN'],
    'grant_type': 'refresh_token',
})
access = r.json()['access_token']
m = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',
    headers={'Authorization': f'Bearer {access}'}, params={'maxResults': 1}).json()
mid = m.get('messages', [{}])[0].get('id', 'NONE')
print('GMAIL last_msg_id=', mid[:6] + '...' if mid != 'NONE' else 'NONE')
ti = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={access}').json()
print('GMAIL scopes=', ti.get('scope', 'N/A'))
print('GMAIL email=', (ti.get('email', 'N/A')[:4] + '...' + ti.get('email', '')[-10:]) if ti.get('email') else 'N/A')
"
else
  echo "GMAIL_SKIP — no GOOGLE_GMAIL_REFRESH_TOKEN configured"
fi
```

### 2. Identificar gaps (en el reporte, NO ejecutar)

Con el output de paso 1, clasificar cada uno:

| Componente | Estado esperado | Acción si falta |
|---|---|---|
| `NOTION_API_KEY` válido + bot reconocido por API | PRESENT + NOTION_BOT_NAME no vacío | David crea/renueva integration Notion en notion.so/my-integrations |
| Notion integration conectada a páginas | (no testeable vía API directa, requiere intentar fetch de page conocida) | David conecta integration a páginas/databases en Notion UI |
| `GOOGLE_CALENDAR_*` refresh token operativo | smoke test devuelve CAL_EVENT_COUNT >= 0 sin error | David regenera refresh token siguiendo `docs/35-gmail-token-setup.md` (mismo patrón) |
| `GOOGLE_GMAIL_*` refresh token + scope `gmail.send` | smoke test devuelve last_msg_id + scopes incluyen `gmail.send` (o `gmail.modify`) | David genera siguiendo `docs/35-gmail-token-setup.md` opción B |

### 3. NO ejecutar gap-closure aún

**STOP después del audit.** Reportá hallazgos. David decide qué cerrar y cómo (algunos requieren acciones manuales en consolas Google/Notion que Copilot VPS no puede hacer).

### 4. Reportar (append al final de este archivo)

Sección `## Resultado audit 2026-05-05`:
1. Tabla de env vars con `PRESENT` / `MISSING` (NO dump de valores).
2. Output del NOTION_BOT_NAME + type.
3. Resultado smoke test Calendar (cantidad de eventos devueltos, **redactar títulos sensibles** — primeros 20 chars max).
4. Resultado smoke test Gmail si aplica (last_msg_id truncado, scopes, email truncado).
5. Tabla de gaps identificados con acción recomendada.
6. Confirmación: NO mutaste nada.

Commit: `report(.agents/004): audit OAuth multi-canal Rick state — gaps identified`. Push a `main`.

---

## Anti-patterns prohibidos

- ❌ NO commitear ningún valor de env var (tokens, secrets, IDs sensibles). Aplicar `secret-output-guard`.
- ❌ NO crear OAuth client nuevo, NO regenerar refresh tokens, NO modificar `~/.config/openclaw/env`. Esta task es **read-only**.
- ❌ NO crear `~/.config/openclaw/secrets/` si no existe. Por ahora la convención es env vars en `~/.config/openclaw/env`.
- ❌ NO probar escritura (send email, create event, edit Notion page).
- ❌ NO redactar el reporte mostrando email completo o ID de página Notion completo. Truncar.

---

## Notas

Versión rev 1 de esta task pedía setup completo de cero. Eso era incorrecto: la cuenta Rick ya existe, los tokens Calendar ya operan, integration Notion ya tiene `NOTION_API_KEY`. Esta rev 2 audita el delta real y reporta. La task 005 (re-prompt `main` + orchestrator + `subagents.allowAgents`) es independiente y puede ir en paralelo.
