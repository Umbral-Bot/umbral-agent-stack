# 24 — S6 Langfuse y Observabilidad

## Resumen

- **Langfuse**: plataforma de observabilidad LLM (traces, métricas).
- **LiteLLM**: callbacks `langfuse_otel` para enviar traces automáticamente.
- **Despliegue**: VM con Docker (infra/docker/docker-compose.langfuse.yml).

## Levantar Langfuse en VM

```bash
cd infra/docker
export LANGFUSE_DB_PASSWORD=<contraseña-segura>
export LANGFUSE_NEXTAUTH_SECRET=<secret-aleatorio>
export LANGFUSE_SALT=<salt-aleatorio>
docker compose -f docker-compose.langfuse.yml up -d
```

Acceder a `http://localhost:3000`, crear proyecto y obtener claves.

## Activar tracing en LiteLLM

1. Añadir variables de entorno (OpenClaw / LiteLLM):

   ```bash
   export LANGFUSE_PUBLIC_KEY=pk-lf-...
   export LANGFUSE_SECRET_KEY=sk-lf-...
   export LANGFUSE_OTEL_HOST=https://us.cloud.langfuse.com   # Cloud EU/US
   # O self-hosted: http://<langfuse-vm>:4318  # endpoint OTEL
   ```

2. En `infra/docker/litellm_config.yaml`:

   ```yaml
   litellm_settings:
     callbacks: ["langfuse_otel"]
     # ... resto
   ```

3. Reiniciar LiteLLM / OpenClaw.

Todas las llamadas LLM pasarán a Langfuse como traces.

## Pendiente

- Evals automáticos (Self-Evaluation agent).
- Reporte semanal OODA (scripts/ooda_report.py).
