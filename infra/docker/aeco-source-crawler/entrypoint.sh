#!/bin/sh
# O16.2/048 — entrypoint del Container Apps Job aeco-source-crawler
set -eu

echo "[entrypoint] aeco-source-crawler starting at $(date -u +%FT%TZ)"
echo "[entrypoint] STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-unset}"
echo "[entrypoint] SOURCE_TYPE=${SOURCE_TYPE:-unset}"
echo "[entrypoint] MAX_DOCS=${MAX_DOCS:-unset}"

exec python -m scripts.aeco_kb.source_crawler "$@"
