# syntax=docker/dockerfile:1.7
# O16.2/049 — aeco-index-pipeline image (version-detector + index-publisher)
# Build: docker build -f infra/docker/aeco-index-pipeline/Dockerfile -t ghcr.io/umbral-bot/aeco-index-pipeline:latest .
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install --no-cache-dir \
        "httpx>=0.25.0,<1.0.0" \
        "azure-storage-blob>=12.19.0,<13.0.0" \
        "azure-identity>=1.15.0,<2.0.0"

COPY scripts/aeco-kb/__init__.py /app/scripts/aeco_kb/__init__.py
COPY scripts/aeco-kb/version_detector.py /app/scripts/aeco_kb/version_detector.py
COPY scripts/aeco-kb/index_publisher.py /app/scripts/aeco_kb/index_publisher.py
COPY infra/docker/aeco-index-pipeline/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && chmod -R a+r /app

ENTRYPOINT ["/app/entrypoint.sh"]
