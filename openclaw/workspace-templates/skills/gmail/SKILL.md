---
name: gmail
description: >-
  Crear borradores de email en Gmail. Usa cuando el usuario diga
  "redactar email", "guardar borrador", "email borrador", "Gmail draft".
metadata:
  openclaw:
    emoji: "\U0001F4E7"
    requires:
      env:
        - GOOGLE_GMAIL_TOKEN
---

# Gmail Skill

Rick puede crear y listar borradores de email en Gmail a través de las Worker tasks del Umbral Agent Stack.

## Requisitos

- `GOOGLE_GMAIL_TOKEN`: OAuth2 Bearer token con scope `gmail.compose`.
- Alternativa: `GOOGLE_SERVICE_ACCOUNT_JSON` (ruta al archivo JSON de service account con scope gmail).

## Tasks disponibles

### 1. Crear borrador

Task: `gmail.create_draft`

```json
{
  "to": "destinatario@email.com",
  "subject": "Seguimiento reunión proyecto BIM",
  "body": "Estimado equipo,\n\nAdjunto los compromisos de la reunión...",
  "body_type": "plain",
  "cc": ["copia@email.com"],
  "reply_to": "responder@email.com"
}
```

Devuelve: `{"ok": true, "draft_id": "...", "message_id": "..."}`

**Con HTML:**

```json
{
  "to": "cliente@email.com",
  "subject": "Propuesta adjunta",
  "body": "<h1>Propuesta</h1><p>Detalle del proyecto...</p>",
  "body_type": "html"
}
```

### 2. Listar borradores

Task: `gmail.list_drafts`

```json
{
  "max_results": 10,
  "q": "subject:seguimiento"
}
```

Devuelve: `{"ok": true, "drafts": [{"id": "...", "message_id": "...", "snippet": "..."}, ...]}`

## Integración con Granola Pipeline

Cuando `granola.create_followup` se llama con `followup_type: "email_draft"` y los
attendees incluyen direcciones de email, se crea automáticamente un borrador en Gmail
además de registrarlo en Notion.

## Notas

- El email se codifica en base64 formato RFC 2822.
- Soporta tanto OAuth Bearer como Service Account (con lazy import de `google-auth`).
- El parámetro `q` usa la misma sintaxis de búsqueda de Gmail.
