#!/usr/bin/env bash
# quota-guard-cron.sh â€” protege OpenClaw del freeze por cuota Anthropic.
# Corre cada 15 min. Si claude_pro >= 75%, cambia OpenClaw a gpt-5.3-codex.
set -euo pipefail

REPO="$HOME/umbral-agent-stack"

# Cargar env (REDIS_URL, OPENCLAW_CONFIG_PATH, etc.)
if [[ -f "$HOME/.config/openclaw/env" ]]; then
    # shellcheck disable=SC1091
    source "$HOME/umbral-agent-stack/scripts/vps/load-openclaw-env.sh"
    load_openclaw_env "$HOME/.config/openclaw/env"
fi

cd "$REPO"
source .venv/bin/activate 2>/dev/null || true

export OPENCLAW_QUOTA_SWITCH_THRESHOLD="${OPENCLAW_QUOTA_SWITCH_THRESHOLD:-0.75}"
export OPENCLAW_FALLBACK_MODEL="${OPENCLAW_FALLBACK_MODEL:-openai-codex/gpt-5.3-codex}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
export OPENCLAW_MODEL_JSON_KEY="${OPENCLAW_MODEL_JSON_KEY:-agents.defaults.model.primary}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export PYTHONPATH="$REPO"

echo "[quota-guard $(date -u '+%Y-%m-%d %H:%M UTC')] Checking claude_pro quota..."
python3 "$REPO/scripts/openclaw_quota_guard.py"
echo "[quota-guard] Done."
