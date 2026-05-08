#!/usr/bin/env bash
# O16.2/050 — orquestador secuencial Q2 del pipeline AECO KB.
#
# Arranca los 3 ACA Jobs (crawler → parser → publisher) por cada source_type
# y espera a que cada execution complete antes de continuar.
#
# Uso:
#   bash scripts/aeco-kb/run_pipeline.sh buildingsmart minvu iram nmx
#   bash scripts/aeco-kb/run_pipeline.sh --skip-crawl iram
#
# Pre-req: az login + sub correcta + az containerapp ext.
# Pendiente UAMI: Cognitive Services OpenAI User en umbralbim-resource RG.

set -euo pipefail

RG="${RG:-rg-umbral-agents-prod}"
CRAWLER_JOB="${CRAWLER_JOB:-aeco-source-crawler}"
PARSER_JOB="${PARSER_JOB:-aeco-pdf-parser}"
PUBLISHER_JOB="${PUBLISHER_JOB:-aeco-index-pipeline}"
POLL_INTERVAL="${POLL_INTERVAL:-30}"
TIMEOUT_PER_STAGE="${TIMEOUT_PER_STAGE:-3600}"

SKIP_CRAWL=false
if [[ "${1:-}" == "--skip-crawl" ]]; then
    SKIP_CRAWL=true
    shift
fi

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 [--skip-crawl] <source_type1> [source_type2 ...]" >&2
    exit 2
fi

SOURCES=("$@")

log() { echo "[$(date -u +%FT%TZ)] $*"; }

start_job_and_wait() {
    local job="$1"
    shift
    local args=("$@")

    log "Starting job '$job' with args: ${args[*]}"
    local exec_name
    exec_name=$(az containerapp job start \
        --name "$job" \
        --resource-group "$RG" \
        --args "${args[@]}" \
        --query name -o tsv)
    log "Execution: $exec_name"

    local elapsed=0
    while true; do
        local status
        status=$(az containerapp job execution show \
            --name "$job" \
            --resource-group "$RG" \
            --job-execution-name "$exec_name" \
            --query properties.status -o tsv 2>/dev/null || echo "Unknown")

        case "$status" in
            Succeeded) log "  -> $job/$exec_name SUCCEEDED"; return 0 ;;
            Failed|Degraded|Canceled) log "  -> $job/$exec_name $status"; return 1 ;;
            Running|Processing|Pending|"") sleep "$POLL_INTERVAL" ;;
            *) log "  -> unexpected status '$status', polling"; sleep "$POLL_INTERVAL" ;;
        esac

        elapsed=$((elapsed + POLL_INTERVAL))
        if [[ $elapsed -ge $TIMEOUT_PER_STAGE ]]; then
            log "  -> TIMEOUT after ${elapsed}s on $job/$exec_name"
            return 1
        fi
    done
}

log "Pipeline start. RG=$RG sources=${SOURCES[*]} skip_crawl=$SKIP_CRAWL"

# Stage 1 — crawler (per source)
if [[ "$SKIP_CRAWL" == "false" ]]; then
    for src in "${SOURCES[@]}"; do
        start_job_and_wait "$CRAWLER_JOB" --source-type "$src"
    done
else
    log "Skipping crawler stage."
fi

# Stage 2 — parser (per source — Q2 enumera blobs internamente o procesa todos los pendientes)
for src in "${SOURCES[@]}"; do
    start_job_and_wait "$PARSER_JOB" --source-type "$src"
done

# Stage 3 — publisher (single run, todas las sources juntas para alias swap único)
start_job_and_wait "$PUBLISHER_JOB" publish --source-types "${SOURCES[@]}"

log "Pipeline complete. Run verify_kb.py para validar gate ≥500 chunks."
