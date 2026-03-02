#!/usr/bin/env python3
"""Ejecuta una tarea en el Worker (para pruebas desde VPS contra VM).

Uso:
  export WORKER_URL=http://100.109.16.40:8088 WORKER_TOKEN=xxx
  echo '{\"text\": \"hola\"}' | python scripts/run_worker_task.py windows.open_notepad
  python scripts/run_worker_task.py ping
"""
import json
import os
import sys

# Añadir repo al path para importar client
repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo)

from client.worker_client import WorkerClient

def main():
    if len(sys.argv) < 2:
        print("Uso: run_worker_task.py <task> [input_json]", file=sys.stderr)
        print("  Ejemplo: run_worker_task.py windows.open_notepad '{\"text\": \"hola\"}'", file=sys.stderr)
        sys.exit(1)
    task = sys.argv[1]
    # Default input para pruebas comunes
    defaults = {"windows.open_notepad": {"text": "hola"}, "ping": {}}
    input_data = {}
    if len(sys.argv) > 2:
        raw = sys.argv[2]
    elif task in defaults:
        raw = ""
    else:
        raw = sys.stdin.read().strip()
    if not raw and task in defaults:
        input_data = defaults[task]
    elif task == "windows.open_notepad" and raw and not raw.strip().startswith("{"):
        input_data = {"text": raw}
    if "--run-now" in sys.argv:
        input_data["run_now"] = True
    if "--session" in sys.argv:
        idx = sys.argv.index("--session")
        if idx + 1 < len(sys.argv):
            input_data["session"] = sys.argv[idx + 1]
    if not input_data and raw:
        if not raw.strip().startswith("{"):
            raw = "{}"
        if raw:
            try:
                input_data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"JSON inválido: {e}", file=sys.stderr)
                sys.exit(2)
    url = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("WORKER_TOKEN", "")
    session = input_data.get("session", "")
    if not url or not token:
        env_vars = {}
        env_path = os.path.expanduser("~/.config/openclaw/env")
        if os.path.isfile(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k] = v.strip().strip('"').strip("'")
            if not url:
                session = input_data.get("session", "")
                if session == "interactive" and env_vars.get("WORKER_URL_VM_INTERACTIVE"):
                    url = env_vars["WORKER_URL_VM_INTERACTIVE"]
                elif task.startswith("windows.") and env_vars.get("WORKER_URL_VM"):
                    url = env_vars["WORKER_URL_VM"]
                else:
                    url = env_vars.get("WORKER_URL_VM_INTERACTIVE") or env_vars.get("WORKER_URL_VM") or env_vars.get("WORKER_URL") or ""
            if not token:
                token = env_vars.get("WORKER_TOKEN", "")
            url = (url or "").rstrip("/")
        if not url or not token:
            print("Defina WORKER_URL y WORKER_TOKEN (o ~/.config/openclaw/env).", file=sys.stderr)
            sys.exit(3)
    if session == "interactive":
        url_interactive = os.environ.get("WORKER_URL_VM_INTERACTIVE") or ""
        if not url_interactive and os.path.isfile(os.path.expanduser("~/.config/openclaw/env")):
            with open(os.path.expanduser("~/.config/openclaw/env"), encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("WORKER_URL_VM_INTERACTIVE="):
                        url_interactive = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if url_interactive:
            url = url_interactive.rstrip("/")
    timeout = 60.0 if session == "interactive" else 30.0
    timeout = float(os.environ.get("WORKER_TIMEOUT", timeout))
    try:
        wc = WorkerClient(base_url=url, token=token, timeout=timeout)
        out = wc.run(task, input_data)
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()
