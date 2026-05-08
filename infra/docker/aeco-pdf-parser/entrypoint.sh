#!/bin/sh
# O16.2/047 — entrypoint del Container Apps Job pdf-parser
# Lee config desde env vars (inyectadas por el Job ARM).
set -eu

echo "[entrypoint] aeco-pdf-parser starting at $(date -u +%FT%TZ)"
echo "[entrypoint] DI_ENDPOINT=${DI_ENDPOINT:-unset}"
echo "[entrypoint] STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-unset}"
echo "[entrypoint] INPUT_BLOB_PATH=${INPUT_BLOB_PATH:-unset}"
echo "[entrypoint] SOURCE_TYPE=${SOURCE_TYPE:-unset}"

exec python -m scripts.aeco_kb.pdf_parser "$@"
