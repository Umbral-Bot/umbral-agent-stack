#!/usr/bin/env bash
# G-D5.2 — patch ~/.config/openclaw/env from /tmp/rick-oauth.pending (no stdout secrets)
set -euo pipefail

ENV="${HOME}/.config/openclaw/env"
PATCH="${1:-/tmp/rick-oauth.pending}"

if [[ ! -f "$PATCH" ]]; then
  echo "ABORT: missing $PATCH" >&2
  exit 1
fi

cp "$ENV" "${ENV}.bak.gd52.$(date +%Y%m%d%H%M%S)"
chmod 600 "${ENV}.bak.gd52."* 2>/dev/null || true

patch_var() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "$ENV"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV"
  else
    echo "${key}=${val}" >> "$ENV"
  fi
}

while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  case "$line" in
    GOOGLE_GMAIL_*|GOOGLE_CALENDAR_*|GOOGLE_CLOUD_LOCATION|GCLOUD_LOCATION)
      key="${line%%=*}"
      val="${line#*=}"
      patch_var "$key" "$val"
      ;;
  esac
done < "$PATCH"

chmod 600 "$ENV"
# Confirm client id prefix only (no secrets)
grep '^GOOGLE_GMAIL_CLIENT_ID=' "$ENV" | cut -d= -f2 | sed 's/.apps.googleusercontent.com//' | cut -c1-30
echo PATCH_OK
