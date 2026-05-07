#!/usr/bin/env bash
# Discovery publish cron — task 027.
#
# Cadencia: cada 6h ("15 */6 * * *") via crontab user (rick).
#
# Pasos:
#   1. Prestep: backfill contenido_html de items YouTube promovidos sin contenido
#      (Data API v3). Si falla parcial → warning, no abort (D3).
#   2. Stage 4: push a Notion (DB Referentes). Items sin contenido_html quedan
#      marcados created_no_body por stage4 (downstream, no aborta acá).
#
# IDs vienen de ~/.config/openclaw/env (D4):
#   - UMBRAL_DISCOVERY_DATABASE_ID
#   - UMBRAL_DISCOVERY_DATA_SOURCE_ID
#   - UMBRAL_DISCOVERY_REFERENTES_DS_ID
#
# Sin --limit (D5): curaduría humana ocurre downstream en DB Publicaciones.
#
# Uso:
#   bash scripts/vps/discovery-publish-cron.sh             # full run con --commit
#   DISCOVERY_PUBLISH_DRYRUN=1 bash ...discovery-publish-cron.sh   # smoke (stage4 dry)

set -uo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
ENV_FILE="${ENV_FILE:-$HOME/.config/openclaw/env}"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] discovery-publish: $*"; }

log "start (repo=$REPO_DIR env=$ENV_FILE)"

if [[ ! -f "$ENV_FILE" ]]; then
  log "FATAL env file not found: $ENV_FILE"
  exit 2
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

cd "$REPO_DIR" || { log "FATAL cannot cd $REPO_DIR"; exit 2; }

# Activate venv (best-effort; cron has minimal PATH).
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || {
  log "FATAL .venv not found in $REPO_DIR"
  exit 2
}

: "${UMBRAL_DISCOVERY_DATABASE_ID:?missing in env}"
: "${UMBRAL_DISCOVERY_DATA_SOURCE_ID:?missing in env}"
: "${UMBRAL_DISCOVERY_REFERENTES_DS_ID:?missing in env}"

# ---------------------------------------------------------------------------
# Prestep: backfill_youtube_content (siempre --commit; D3 = continuar si falla)
# ---------------------------------------------------------------------------
log "prestep: backfill_youtube_content (commit)"
if python scripts/discovery/backfill_youtube_content.py --commit; then
  log "prestep: backfill OK"
else
  rc=$?
  log "WARN prestep backfill exited rc=$rc — continuando con stage4 (D3)"
fi

# ---------------------------------------------------------------------------
# Stage 4: push promovidos a Notion (Referentes)
# ---------------------------------------------------------------------------
STAGE4_FLAGS=(
  --database-id              "$UMBRAL_DISCOVERY_DATABASE_ID"
  --data-source-id           "$UMBRAL_DISCOVERY_DATA_SOURCE_ID"
  --referentes-data-source-id "$UMBRAL_DISCOVERY_REFERENTES_DS_ID"
)

if [[ "${DISCOVERY_PUBLISH_DRYRUN:-0}" == "1" ]]; then
  log "stage4: DRY-RUN (no --commit)"
else
  STAGE4_FLAGS+=(--commit)
  log "stage4: COMMIT"
fi

if python -m scripts.discovery.stage4_push_notion "${STAGE4_FLAGS[@]}"; then
  log "stage4: OK"
  log "done"
  exit 0
else
  rc=$?
  log "ERROR stage4 exited rc=$rc"
  exit "$rc"
fi
