"""
S5 — Tareas Windows (PAD/RPA, scripts).

- windows.pad.run_flow: ejecuta un flujo de Power Automate Desktop (si está en allowlist).
- windows.open_notepad: abre el Bloc de notas con un texto (prueba de conectividad VM).
"""

import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

from .. import tool_policy
from ..sanitize import sanitize_pad_flow_name

logger = logging.getLogger("worker.tasks.windows")


def handle_windows_pad_run_flow(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta un flujo de Power Automate Desktop.

    Input:
        flow_name (str, required): Nombre del flujo (debe estar en tool_policy allowlist).
        params (dict, optional): Parámetros para el flujo (futuro).

    Returns:
        {"ok": bool, "flow_name": str, "exit_code": int, "output": str, "error": str|None}
    """
    flow_name = input_data.get("flow_name") or input_data.get("flow")
    if not flow_name or not isinstance(flow_name, str):
        raise ValueError("'flow_name' (str) is required in input")

    flow_name = sanitize_pad_flow_name(flow_name)

    if not tool_policy.is_pad_flow_allowed(flow_name):
        return {
            "ok": False,
            "flow_name": flow_name,
            "exit_code": -1,
            "output": "",
            "error": f"Flow '{flow_name}' not in allowlist. Add to config/tool_policy.yaml",
        }

    timeout = tool_policy.get_pad_timeout_sec()

    # PAD Console Host: ejecutar flujo por nombre
    # https://learn.microsoft.com/power-automate/desktop-flows/run-from-command-line
    pad_exe = r"C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe"
    if sys.platform != "win32":
        return {
            "ok": False,
            "flow_name": flow_name,
            "exit_code": -1,
            "output": "",
            "error": "PAD only runs on Windows. This Worker is not on Windows.",
        }

    try:
        proc = subprocess.run(
            [pad_exe, "-run", flow_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=None,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return {
            "ok": proc.returncode == 0,
            "flow_name": flow_name,
            "exit_code": proc.returncode,
            "output": out or "(no stdout)",
            "error": err if proc.returncode != 0 else None,
        }
    except FileNotFoundError:
        logger.warning("PAD.Console.Host.exe not found at %s", pad_exe)
        return {
            "ok": False,
            "flow_name": flow_name,
            "exit_code": -1,
            "output": "",
            "error": f"Power Automate Desktop not found at {pad_exe}",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "flow_name": flow_name,
            "exit_code": -1,
            "output": "",
            "error": f"Flow timed out after {timeout}s",
        }
    except Exception as e:
        logger.exception("PAD run_flow failed: %s", e)
        return {
            "ok": False,
            "flow_name": flow_name,
            "exit_code": -1,
            "output": "",
            "error": str(e),
        }


def handle_windows_open_notepad(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Abre el Bloc de notas con el texto indicado en el próximo inicio de sesión (solo Windows).
    El Worker corre como servicio (antes de que nadie inicie sesión); esta tarea crea un
    archivo .txt y programa "al iniciar sesión" que se abra con Notepad, así al ingresar
    la contraseña en Hyper-V el usuario ya ve el Bloc de notas. Sirve para comprobar
    control VPS → VM sin tocar la VM.

    Input:
        text (str, optional): Texto a mostrar. Default: "hola".

    Returns:
        {"ok": bool, "path": str, "scheduled": bool, "error": str|None}
    """
    if sys.platform != "win32":
        return {"ok": False, "path": "", "scheduled": False, "error": "Solo disponible en Windows."}
    text = (input_data.get("text") or "hola").strip() or "hola"
    task_name = "UmbralOpenNotepad"
    try:
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="umbral_")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        # Programar "al iniciar sesión" para que Notepad se abra cuando el usuario entre
        dir_path = os.path.dirname(path)
        bat_path = os.path.join(dir_path, "umbral_open_notepad.bat")
        bat_content = f'@echo off\nstart "" notepad.exe "{path}"\ntimeout /t 2 /nobreak >nul\nschtasks /delete /tn {task_name} /f'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        r = subprocess.run(
            [
                "schtasks",
                "/create",
                "/tn", task_name,
                "/tr", bat_path,
                "/sc", "onlogon",
                "/f",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
        )
        if r.returncode != 0:
            logger.warning("schtasks create failed: %s %s", r.stdout, r.stderr)
            return {
                "ok": False,
                "path": path,
                "scheduled": False,
                "error": r.stderr or r.stdout or "schtasks failed",
            }
        return {"ok": True, "path": path, "scheduled": True, "error": None}
    except Exception as e:
        logger.exception("open_notepad failed: %s", e)
        return {"ok": False, "path": "", "scheduled": False, "error": str(e)}
