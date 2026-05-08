# syntax=docker/dockerfile:1.7
# O16.2/047 — pdf-parser Container Apps Job image
# Build context: repo root
# Build: docker build -f infra/docker/aeco-pdf-parser/Dockerfile -t ghcr.io/umbral-bot/aeco-pdf-parser:latest .
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Sólo dependencias del parser — NO instalamos el repo entero para mantener imagen lean
RUN pip install --no-cache-dir \
        "azure-ai-documentintelligence>=1.0.0,<2.0.0" \
        "azure-storage-blob>=12.19.0,<13.0.0" \
        "azure-identity>=1.15.0,<2.0.0"

# Copiar sólo el script + entrypoint
COPY scripts/aeco-kb/__init__.py /app/scripts/aeco_kb/__init__.py
COPY scripts/aeco-kb/pdf_parser.py /app/scripts/aeco_kb/pdf_parser.py
COPY infra/docker/aeco-pdf-parser/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Container Apps Jobs corren como UID dinámico — asegurar permisos lectura
RUN chmod -R a+r /app

# UAMI inyecta token vía AZURE_CLIENT_ID + IMDS (no requiere config adicional)
ENTRYPOINT ["/app/entrypoint.sh"]
