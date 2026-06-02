---
name: gmail-router
description: >-
  Gestionar Gmail de Rick con ADR-16: crear borradores y listar borradores de forma
  segura, sin envío directo.
metadata:
  openclaw:
    emoji: "📬"
    requires:
      env: []
---

# Gmail Router Skill

Skill para pedir y consultar borradores de Gmail en el canal de Rick.

## Alcance y límites

- Este skill **NUNCA** envía correo directamente. Solo usa:
  - `gmail.create_draft`
  - `gmail.list_drafts`
- Sigue ADR-16:
  - **D4**: scope mínimo `https://www.googleapis.com/auth/gmail.modify`.
  - **D5**: acciones con impacto a terceros usan `propose + confirm` en el flujo de Rick;
    aquí siempre es rascador de borradores.
  - **D6**: no hay bypass de whitelist de remitentes en este skill.

## Recomendación de gate humano

`create_draft` está pensado para revisión por David antes de enviar correo real
(outbound humano final por política de canal). `list_drafts` no requiere confirmación.

## Tasks soportadas

### 1) Crear borrador

Task: `gmail.create_draft`

Inputs sugeridos:

```json
{
  "to": "cliente@email.com",
  "subject": "Seguimiento reunión proyecto BIM",
  "body": "Resumen + próximos pasos.",
  "body_type": "plain",
  "cc": ["aliado@email.com"],
  "reply_to": "rick.asistente@gmail.com"
}
```

Retorna `{"ok": true, "draft_id": "...", "message_id": "..."}`.

### 2) Listar borradores

Task: `gmail.list_drafts`

```json
{
  "max_results": 10,
  "q": "subject:seguimiento"
}
```

Retorna `{"ok": true, "drafts": [{"id": "...", "message_id": "...", "snippet": "..."}]}`.

## Qué no hace este skill

- No envía (`send`) correos.
- No lee inbox completo (solo drafts).
- No cambia labels, adjunta archivos o borra mensajes.

## Notas de implementación

Usa worker tasks existentes en `worker/tasks/gmail.py` con auth de Rick (GOOGLE_GMAIL_*).
Consulta también:

- `docs/35-gmail-token-setup.md`
- `docs/external-context/adr-16-multichannel-rick-channels.md`
