# 26 — S7 Hardening

## Implementado

- **Rate limiting**: `worker/rate_limit.py` — 120 req/min por IP (configurable con `WORKER_RATE_LIMIT_PER_MIN`).
- **Sanitización**: `worker/sanitize.py` — límites en task name, flow_name, tamaño de input (256 KB).
- **Integración**: Worker valida task e input antes del dispatch.

## Secretos

**Implementado**: `infra/secrets.py` — `SecretStore` con prioridad:
1. Variables de entorno (siempre disponible).
2. Archivo cifrado `secrets.enc` (Fernet, requiere `UMBRAL_SECRETS_KEY`).
3. Archivo plano `secrets.json` (solo dev local).

**CLI**: `scripts/manage_secrets.py` — genkey, encrypt, audit, list.

Para migrar a archivo cifrado:
```bash
python scripts/manage_secrets.py genkey
export UMBRAL_SECRETS_KEY=<clave-generada>
python scripts/manage_secrets.py encrypt --input ~/.config/umbral/secrets.json
```

Opciones futuras:
- **HashiCorp Vault** o **Azure Key Vault** para rotación automática.
- Mantener SecretStore como wrapper unificado.

## ACL Tailscale

Restringir acceso por nodo:

1. [Tailscale Admin Console](https://login.tailscale.com/admin/acls) → Access Controls.
2. Definir tags o grupos (ej: `tag:umbral-vps`, `tag:umbral-vm`).
3. ACL ejemplo:
   ```json
   {
     "acls": [
       {
         "action": "accept",
         "src": ["tag:umbral-vps"],
         "dst": ["tag:umbral-vm:8088"]
       }
     ]
   }
   ```
4. Ver `docs/05-setup-tailscale.md`.

## Trazabilidad end-to-end

- `trace_id` en TaskEnvelope se propaga en logs y resultados.
- Langfuse (S6) añade tracing LLM.
- Para correlación completa: pasar `trace_id` a LiteLLM como metadata (user/session).
