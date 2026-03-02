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
    else:
        raw = sys.stdin.read().strip()
    if not raw and task in defaults:
        input_data = defaults[task]
    else:
        if not raw:
            raw = "{}"
        if raw:
            try:
                input_data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"JSON inválido: {e}", file=sys.stderr)
                sys.exit(2)
    url = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("WORKER_TOKEN", "")
    if not url or not token:
        print("Defina WORKER_URL y WORKER_TOKEN.", file=sys.stderr)
        sys.exit(3)
    try:
        wc = WorkerClient(base_url=url, token=token)
        out = wc.run(task, input_data)
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()
