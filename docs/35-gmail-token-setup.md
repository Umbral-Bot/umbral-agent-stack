# 35 — Cómo obtener GOOGLE_GMAIL_TOKEN (y que no expire)

El Worker usa Gmail con una de estas opciones:

1. **Access token solo** (`GOOGLE_GMAIL_TOKEN`) — caduca en ~1 h; hay que renovarlo a mano.
2. **Refresh token** (`GOOGLE_GMAIL_REFRESH_TOKEN` + `GOOGLE_GMAIL_CLIENT_ID` + `GOOGLE_GMAIL_CLIENT_SECRET`) — **recomendado**: el Worker renueva el access token solo; no expira en la práctica.

---

## Opción A: Rápido (access token, caduca en ~1 h)

1. **Página:** https://developers.google.com/oauthplayground/
2. Step 1: **Gmail API v1** → scope `https://www.googleapis.com/auth/gmail.compose` (y opcional `gmail.readonly` para listar borradores).
3. **Authorize APIs** → iniciar sesión → Allow.
4. Step 2: **Exchange authorization code for tokens**.
5. Copiá el **Access token** a tu `.env`:
   ```env
   GOOGLE_GMAIL_TOKEN=ya0.a0AfB_byC...
   ```

---

## Opción B: Que no expire (refresh token)

El Worker ya soporta refresh token: si configurás los tres env, obtiene y renueva el access token solo.

### 1. Crear credenciales OAuth en Google Cloud

1. https://console.cloud.google.com/ → tu proyecto.
2. **APIs y servicios** → **Biblioteca** → **Gmail API** → Habilitar.
3. **Credenciales** → **Crear credenciales** → **ID de cliente de OAuth**.
4. Tipo: **Aplicación de escritorio**. Nombre ej. `Umbral Gmail`.
5. **Crear** → Descargar JSON. Guardá el **Client ID** y **Client secret** (o el JSON).

### 2. Obtener el refresh token (una sola vez)

**Opción B1 — OAuth Playground con tus credenciales**

1. https://developers.google.com/oauthplayground/
2. Icono de **engranaje** (arriba derecha) → **Use your own OAuth credentials** → pegar Client ID y Client secret.
3. Step 1: scope `https://www.googleapis.com/auth/gmail.compose` (y si querés `gmail.readonly`).
4. **Authorize APIs** → iniciar sesión con la cuenta Gmail (rick.asistente@gmail.com) → Allow.
5. Step 2: **Exchange authorization code for tokens**.
6. Copiá el **Refresh token** (no el Access token). Ese no lo revoca Google a las 24 h porque son *tus* credenciales.

**Opción B2 — Script Python**

Mismo proyecto: creá `credentials.json` con el JSON descargado. En la misma carpeta:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]
creds = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES).run_local_server(port=0)
print("GOOGLE_GMAIL_REFRESH_TOKEN=" + creds.refresh_token)
print("GOOGLE_GMAIL_CLIENT_ID=" + creds.client_id)
print("GOOGLE_GMAIL_CLIENT_SECRET=" + creds.client_secret)
```

`pip install google-auth-oauthlib` y ejecutá; se abre el navegador, autorizás, y se imprimen los valores.

### 3. Configurar en el Worker

En `.env` o `~/.config/openclaw/env` (VPS):

```env
GOOGLE_GMAIL_REFRESH_TOKEN=1//0abc...
GOOGLE_GMAIL_CLIENT_ID=123456-xxx.apps.googleusercontent.com
GOOGLE_GMAIL_CLIENT_SECRET=GOCSPX-...
```

No hace falta `GOOGLE_GMAIL_TOKEN`: el Worker usa el refresh token para obtener un access token nuevo cuando haga falta.

**Dependencia:** `pip install google-auth` (el Worker ya lo usa para service account; mismo paquete).

---

## Dónde configurarlo

- **Local / desarrollo:** `.env` en la raíz del repo (gitignored).
- **VPS (Rick):** `~/.config/openclaw/env` y `source` antes de scripts que usen Gmail.

## Referencias

- **Google Calendar** (mismo patrón OAuth/refresh en el Worker): [35-google-calendar-token-setup.md](./35-google-calendar-token-setup.md)
- Gmail API sending: https://developers.google.com/workspace/gmail/api/guides/sending
- Quickstart Python: https://developers.google.com/gmail/api/quickstart/python
- Skill Gmail en el repo: `openclaw/workspace-templates/skills/gmail/SKILL.md`
