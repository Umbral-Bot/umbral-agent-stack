# G-D5.2 — Re-OAuth Rick (ADR-16 scopes)

- **Status:** Done — re-OAuth aplicado en VPS 2026-06-01 (Rick OpenClaw + scopes ADR-16)
- **Cuenta:** `rick.asistente@gmail.com`
- **Drift verificado (VPS tokeninfo):**
  - Gmail live: `gmail.compose` + `gmail.readonly` → target **`gmail.modify`**
  - Calendar live: `calendar` (full) → target **`calendar.events`**

---

## Scopes canónicos (ADR-16)

| Canal | Scope URL |
|---|---|
| Gmail | `https://www.googleapis.com/auth/gmail.modify` |
| Calendar | `https://www.googleapis.com/auth/calendar.events` |

**Un solo consent:** podés autorizar ambos scopes en **una** sesión OAuth Playground (recomendado).

---

## Checklist Google Cloud (browser)

### 1. Proyecto GCP

Proyecto: **`future-yeti-455715-u7`** (*My First Project*).

**No usar `Umbral-bot`** — ese client es de **Umbral BIM** (`umbralbim.io` + Supabase). Rick va en un client aparte.

Cliente Web para Rick (OAuth Playground): **`Rick OpenClaw`** — solo redirect:

```text
https://developers.google.com/oauthplayground
```

Sin redirects de `umbralbim.io`.

- [Gmail API — habilitar](https://console.cloud.google.com/apis/library/gmail.googleapis.com?project=future-yeti-455715-u7)
- [Google Calendar API — habilitar](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com?project=future-yeti-455715-u7)

### 2. OAuth consent screen (Auth Platform)

- [Pantalla de consentimiento / Branding](https://console.cloud.google.com/auth/branding)
- [Usuarios de prueba](https://console.cloud.google.com/auth/audience) — agregar **`rick.asistente@gmail.com`** si la app está en **Testing**
- [Acceso a datos / Scopes](https://console.cloud.google.com/auth/scopes) — agregar:
  - `.../auth/gmail.modify`
  - `.../auth/calendar.events`

### 3. Credenciales OAuth

- [Credenciales](https://console.cloud.google.com/apis/credentials)

**Opción recomendada (OAuth Playground):** cliente tipo **Web application** con redirect URI:

```text
https://developers.google.com/oauthplayground
```

Anotá **Client ID** y **Client secret** (no commitear).

**Alternativa:** Desktop app (script Python local) — ver `.env.example`.

### 4. Revocar consentimiento previo (David, browser)

Antes de re-consent, revocá acceso viejo:

- [Cuenta Google → Seguridad → Acceso de terceros](https://myaccount.google.com/permissions)

Buscá la app OAuth de Rick / Umbral → **Quitar acceso**.

---

## OAuth Playground — obtener refresh tokens

1. Abrir [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Engranaje ⚙ → **Use your own OAuth credentials** → pegar Client ID + Secret
3. Step 1 — pegar scopes (Input your own scopes):

```text
https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar.events
```

4. **Authorize APIs** → login **`rick.asistente@gmail.com`** → Allow
5. Step 2 → **Exchange authorization code for tokens**
6. Copiar **Refresh token** (y guardar Client ID/Secret si son nuevos)

> Si Gmail y Calendar usan **distintos** OAuth clients hoy en VPS, repetí el flow por canal con el client correspondiente. Si unificás a un solo Web client, un refresh token puede cubrir ambos scopes.

---

## Variables VPS (`~/.config/openclaw/env`)

```env
GOOGLE_GMAIL_CLIENT_ID=...
GOOGLE_GMAIL_CLIENT_SECRET=...
GOOGLE_GMAIL_REFRESH_TOKEN=...

GOOGLE_CALENDAR_CLIENT_ID=...
GOOGLE_CALENDAR_CLIENT_SECRET=...
GOOGLE_CALENDAR_REFRESH_TOKEN=...
```

**Handoff:** Copilot-VPS task `2026-06-01-015` (backup env → patch → re-smoke G-D5.1).

---

## Verificación post-rotación

Scripts VPS (evidencia en `~/.coord-ag-evidence/G-D5.2/`):

```bash
bash scripts/vps/smoke-gd52-oauth.sh
```

Copilot-VPS (read-only):

1. `tokeninfo` → scopes = `gmail.modify` + `calendar.events`
2. `gmail.list_drafts` + `google.calendar.list_events` → PASS
3. Actualizar log §6 ADR-16 en `notion-governance`

---

## Repo alineado (Cursor)

Worker constants actualizados a scopes ADR:

- `worker/tasks/gmail.py` → `gmail.modify`
- `worker/tasks/google_calendar.py` → `calendar.events`

Docs 35-* pendientes de alineación en follow-up (no bloquean re-OAuth).
