#!/usr/bin/env python3
"""
OpenClaw — guardia de cuota Claude (preventivo).

Lee el estado de cuota de claude_pro desde Redis (QuotaTracker).
Si el uso >= OPENCLAW_QUOTA_SWITCH_THRESHOLD, ejecuta el cambio a modelo fallback
y reinicio del servicio (o solo imprime SWITCH_NEEDED para que cron ejecute el .sh).

Uso:
  # Solo comprobar (exit 0 = cambiar, exit 1 = no cambiar)
  OPENCLAW_QUOTA_SWITCH_THRESHOLD=0.75 REDIS_URL=redis://localhost:6379/0 python3 scripts/openclaw_quota_guard.py --check

  # Comprobar y si hace falta, cambiar modelo + reiniciar
  OPENCLAW_FALLBACK_MODEL=openai-codex/gpt-5.3-codex python3 scripts/openclaw_quota_guard.py

  # Forzar cambio (reactivo: OpenClaw congelado)
  OPENCLAW_FALLBACK_MODEL=openai-codex/gpt-5.3-codex python3 scripts/openclaw_quota_guard.py --force
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def get_quota_state(redis_url: str) -> float:
    """Estado de uso claude_pro 0.0–1.0 desde Redis (QuotaTracker)."""
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True)
        # QuotaTracker keys
        used = int(r.get("umbral:quota:claude_pro:used") or 0)
        # Limit from config; we don't have it in Redis, so load from YAML or use default
        try:
            import yaml
            policy_path = REPO_ROOT / "config" / "quota_policy.yaml"
            if policy_path.is_file():
                with open(policy_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                limit = int(data.get("providers", {}).get("claude_pro", {}).get("limit_requests", 200))
            else:
                limit = 200
        except Exception:
            limit = 200
        if limit <= 0:
            return 0.0
        return min(1.0, used / limit)
    except Exception as e:
        print(f"Warning: could not get quota state: {e}", file=sys.stderr)
        return 0.0


def switch_openclaw_to_fallback(
    fallback_model: str,
    config_path: str,
    model_key: str,
) -> bool:
    """Actualiza openclaw.json con el modelo fallback. Solo si la ruta existe (no crea claves)."""
    path = Path(config_path).expanduser()
    if not path.is_file():
        print(f"Config not found: {path}", file=sys.stderr)
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read config: {e}", file=sys.stderr)
        return False

    keys = model_key.split(".")
    d = data
    try:
        for k in keys[:-1]:
            d = d[k]
        if keys[-1] not in d:
            print(f"Key {model_key!r} not found in config. Set OPENCLAW_MODEL_JSON_KEY.", file=sys.stderr)
            return False
        d[keys[-1]] = fallback_model
    except KeyError as e:
        print(f"Key path {model_key!r} invalid in config: {e}", file=sys.stderr)
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to write config: {e}", file=sys.stderr)
        return False
    return True


def restart_openclaw_user_service() -> bool:
    """Reinicia systemd user service openclaw."""
    try:
        subprocess.run(
            ["systemctl", "--user", "restart", "openclaw"],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Restart failed: {e.stderr.decode() if e.stderr else e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw quota guard (Claude)")
    parser.add_argument("--check", action="store_true", help="Only check; exit 0 if switch needed")
    parser.add_argument("--force", action="store_true", help="Force switch (reactive: no quota check)")
    args = parser.parse_args()

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    threshold = float(os.environ.get("OPENCLAW_QUOTA_SWITCH_THRESHOLD", "0.75"))
    fallback_model = os.environ.get("OPENCLAW_FALLBACK_MODEL", "openai-codex/gpt-5.3-codex")
    config_path = os.environ.get("OPENCLAW_CONFIG_PATH", "~/.openclaw/openclaw.json")
    model_key = os.environ.get("OPENCLAW_MODEL_JSON_KEY", "agents.defaults.model.primary")

    if args.force:
        need_switch = True
    else:
        state = get_quota_state(redis_url)
        need_switch = state >= threshold
        if args.check:
            if need_switch:
                print("SWITCH_NEEDED")
                return 0
            return 1

    if not need_switch:
        return 0

    if not fallback_model:
        print("OPENCLAW_FALLBACK_MODEL not set", file=sys.stderr)
        return 2

    if not switch_openclaw_to_fallback(fallback_model, config_path, model_key):
        return 3
    if not restart_openclaw_user_service():
        return 4
    print("OpenClaw switched to fallback model and restarted.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
