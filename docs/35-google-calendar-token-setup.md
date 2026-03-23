# 35 - Como obtener acceso persistente a Google Calendar para Rick

El Worker usa Google Calendar con una de estas opciones:

1. **Access token solo** (`GOOGLE_CALENDAR_TOKEN`) - caduca en ~1 h.
2. **Refresh token** (`GOOGLE_CALENDAR_REFRESH_TOKEN` +
   `GOOGLE_CALENDAR_CLIENT_ID` + `GOOGLE_CALENDAR_CLIENT_SECRET`) -
   **recomendado**: el Worker renueva el access token solo.
3. **Service account** (`GOOGLE_SERVICE_ACCOUNT_JSON`) - util para
   calendarios de servicio o Workspace, no suele ser la mejor opcion para un
   calendario personal compartido.

---

## Opcion A - Rapido (access token, caduca en ~1 h)

1. Crea un cliente OAuth en Google Cloud.
2. Usa OAuth Playground con tus credenciales OAuth propias.
3. Scope:

   ```text
   https://www.googleapis.com/auth/calendar
   ```

4. Autoriza con la cuenta de Google de Rick.
5. Copia el `access_token` a la VPS:

   ```env
   GOOGLE_CALENDAR_TOKEN=ya29....
   ```

---

## Opcion B - Persistente (refresh token)

El Worker ya soporta refresh token para Calendar. Si configuras los tres env,
obtiene y renueva el access token solo.

### 1. Crear credenciales OAuth en Google Cloud

1. Habilita **Google Calendar API** en tu proyecto.
2. Configura Google Auth Platform:
   - `Branding`
   - `Audience`
   - `Data Access`
3. Agrega el scope:

   ```text
   https://www.googleapis.com/auth/calendar
   ```

4. Si la app esta en modo testing, agrega la cuenta de Rick como `Test user`.
5. Crea un cliente OAuth tipo **Web application** si vas a usar OAuth
   Playground y agrega este redirect URI:

   ```text
   https://developers.google.com/oauthplayground
   ```

### 2. Obtener el refresh token

1. Abre <https://developers.google.com/oauthplayground/>.
2. Activa `Use your own OAuth credentials`.
3. Pega `Client ID` y `Client secret`.
4. Usa el scope `https://www.googleapis.com/auth/calendar`.
5. Autoriza con la cuenta de Google de Rick.
6. Haz `Exchange authorization code for tokens`.
7. Copia:
   - `refresh_token`
   - `client_id`
   - `client_secret`

### 3. Configurar en el Worker

En `.env` o `~/.config/openclaw/env`:

```env
GOOGLE_CALENDAR_REFRESH_TOKEN=1//0abc...
GOOGLE_CALENDAR_CLIENT_ID=123456-xxx.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-...
```

No hace falta `GOOGLE_CALENDAR_TOKEN` si usas refresh token.

### 4. Calendarios compartidos

Si Rick debe operar sobre un calendario compartido:

1. Comparte el calendario con la cuenta de Google de Rick.
2. Usa el `calendar_id` explicito del calendario compartido.
3. **No** uses `primary` si quieres leer o escribir en ese calendario
   compartido.

Ejemplo:

```json
{
  "calendar_id": "david.a.moreira.m@gmail.com",
  "time_min": "2026-03-22T00:00:00Z",
  "max_results": 10
}
```

---

## Donde configurarlo

- **Local / desarrollo:** `.env` en la raiz del repo (gitignored).
- **VPS (Rick):** `~/.config/openclaw/env`.

---

## Verificacion recomendada

1. Listar calendarios visibles por Rick:

   ```bash
   source ~/.config/openclaw/env
   python - <<'PY'
   import os, json, urllib.request
   req = urllib.request.Request(
       "https://www.googleapis.com/calendar/v3/users/me/calendarList",
       headers={"Authorization": f"Bearer {os.environ['GOOGLE_CALENDAR_TOKEN']}"}
   )
   with urllib.request.urlopen(req, timeout=30) as resp:
       print(resp.read().decode("utf-8"))
   PY
   ```

2. Luego probar `google.calendar.list_events` con `calendar_id` explicito.

---

## Nota sobre testing mode

Si tu app OAuth sigue en modo `Testing`, Google puede expirar el refresh token
en ~7 dias. Para un setup realmente estable, cambia el publishing status cuando
corresponda o recrea el token despues de publicar.
