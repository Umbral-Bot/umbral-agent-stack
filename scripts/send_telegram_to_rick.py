#!/usr/bin/env python3
"""
Envia un mensaje al chat de Telegram donde David habla con Rick.
Asi el mensaje queda en el historial de Telegram (visible para David).

Requiere: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el entorno
(o en .env en la raiz del repo). TELEGRAM_CHAT_ID suele ser el user id
del allowlist (ej. 1813248373).

Uso (en la VPS, donde esta el token de OpenClaw):
  export $(grep -v '^#' ~/.config/openclaw/env | xargs)
  python scripts/send_telegram_to_rick.py "Fix listo. En la VM: git pull, nssm restart. Re-proba linear.list_teams."

Uso (local con .env):
  python scripts/send_telegram_to_rick.py "Mensaje para Rick"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Cargar .env si existe (local o VPS)
repo_root = Path(__file__).resolve().parent.parent
env_file = repo_root / ".env"
if not os.environ.get("TELEGRAM_BOT_TOKEN") and env_file.exists():
    raw = env_file.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'").replace("\x00", "")
        if k and k not in os.environ:
            os.environ.setdefault(k, v)

def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or os.environ.get("TELEGRAM_ALLOWLIST_ID", "1813248373")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN en el entorno o .env", file=sys.stderr)
        return 1
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    if not text:
        print("Indica el mensaje como argumento o por stdin.", file=sys.stderr)
        return 1

    try:
        import urllib.request
        import json
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            if not data.get("ok"):
                print("Telegram API error:", data, file=sys.stderr)
                return 1
        print("Enviado al chat de Telegram.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
