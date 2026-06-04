#!/bin/sh
# O16.2/049 — entrypoint del Container Apps Job aeco-index-pipeline
# Subcomandos: detect | publish | verify
set -eu

if [ "$#" -gt 0 ]; then
    CMD="$1"
    shift
else
    CMD="publish"
fi

echo "[entrypoint] aeco-index-pipeline starting at $(date -u +%FT%TZ)"
echo "[entrypoint] CMD=${CMD}"
echo "[entrypoint] STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-unset} SEARCH_SERVICE=${SEARCH_SERVICE:-unset}"

case "${CMD}" in
    detect)
        exec python -m scripts.aeco_kb.version_detector "$@"
        ;;
    publish)
        exec python -m scripts.aeco_kb.index_publisher "$@"
        ;;
    verify)
        exec python -m scripts.aeco_kb.verify_kb "$@"
        ;;
    *)
        echo "[entrypoint] Unknown subcommand '${CMD}'. Use 'detect', 'publish' or 'verify'." >&2
        exit 2
        ;;
esac
