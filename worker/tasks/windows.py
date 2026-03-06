"""
S5 — Tareas Windows (PAD/RPA, scripts).

- windows.pad.run_flow: ejecuta un flujo de Power Automate Desktop (si está en allowlist).
- windows.open_notepad: abre el Bloc de notas con un texto (prueba de conectividad VM).
"""

import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict

from .. import tool_policy
from ..sanitize import sanitize_pad_flow_name

logger = logging.getLogger("worker.tasks.windows")
_SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _validate_safe_name(value: str, max_len: int = 64) -> str:
    """Validate Windows-facing identifiers before interpolating them into commands or paths."""
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    candidate = value.strip()
    if not candidate:
        raise ValueError("value must be a non-empty string")
    if len(candidate) > max_len:
        raise ValueError(f"value too long (max {max_len})")
    if not _SAFE_NAME_PATTERN.fullmatch(candidate):
        raise ValueError("value contains invalid characters")
    return candidate


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
    Abre el Bloc de notas con el texto indicado (solo Windows).
    - Si OPENCLAW_INTERACTIVE_SESSION=1 (Worker en puerto 8089/sesión usuario): abre Notepad
      directamente en la sesión actual (Session 1).
    - Si no: usa tarea programada (schtasks). El Worker como servicio (SYSTEM) ejecuta en
      sesión 0; para ver el Bloc en la sesión del usuario hay que usar el Worker interactivo (8089).

    Input:
        text (str, optional): Texto a mostrar. Default: "hola".
        run_now (bool, optional): Si true, abre Notepad inmediatamente (default: false).
        run_as_user (str, optional): Usuario con el que ejecutar al logon (solo si no es interactivo).
        run_as_password no se acepta por HTTP. Configurar `SCHTASKS_PASSWORD` en la VM si hace falta.

    Returns:
        {"ok": bool, "path": str, "scheduled": bool, "error": str|None}
    """
    if sys.platform != "win32":
        return {"ok": False, "path": "", "scheduled": False, "error": "Solo disponible en Windows."}
    text = (input_data.get("text") or "hola").strip() or "hola"
    run_now = bool(input_data.get("run_now", False))
    interactive = os.environ.get("OPENCLAW_INTERACTIVE_SESSION", "").strip() == "1"
    try:
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="umbral_")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        logger.exception("open_notepad temp file failed: %s", e)
        return {"ok": False, "path": "", "scheduled": False, "error": str(e)}
    if interactive:
        # Worker en sesión de usuario (8089): abrir Notepad directamente en esta sesión
        try:
            subprocess.Popen(
                ["notepad.exe", path],
                cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"ok": True, "path": path, "scheduled": False, "interactive": True, "error": None}
        except Exception as e:
            logger.exception("open_notepad interactive failed: %s", e)
            return {"ok": False, "path": path, "scheduled": False, "error": str(e)}
    task_name = "UmbralOpenNotepad"
    run_as_user = (input_data.get("run_as_user") or "").strip()
    run_as_password = os.environ.get("SCHTASKS_PASSWORD", "").strip() or os.environ.get("OPENCLAW_NOTEPAD_RUN_AS_PASSWORD", "").strip()
    try:
        dir_path = os.path.dirname(path)
        bat_path = os.path.join(dir_path, "umbral_open_notepad.bat")
        bat_content = f'@echo off\nstart "" notepad.exe "{path}"\ntimeout /t 2 /nobreak >nul\nschtasks /delete /tn {task_name} /f'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True,
            timeout=5,
            cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
        )
        cmd = [
            "schtasks",
            "/create",
            "/tn", task_name,
            "/tr", bat_path,
            "/sc", "onlogon",
            "/ru", "SYSTEM",
            "/f",
        ]
        if run_as_user:
            cmd.extend(["/ru", run_as_user])
            if run_as_password:
                cmd.extend(["/rp", run_as_password])
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
        )
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "schtasks failed").strip()
            logger.warning("schtasks create failed: %s", err)
            for fallback_sc in (["onstart"] if not run_as_user else []):
                cmd_fb = ["schtasks", "/create", "/tn", task_name, "/tr", bat_path, "/sc", fallback_sc, "/f"]
                r2 = subprocess.run(cmd_fb, capture_output=True, text=True, timeout=10, cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"))
                if r2.returncode == 0:
                    return {"ok": True, "path": path, "scheduled": True, "session_zero": True, "trigger": fallback_sc, "error": None}
            if run_as_user:
                cmd_fb = ["schtasks", "/create", "/tn", task_name, "/tr", bat_path, "/sc", "onlogon", "/f"]
                r2 = subprocess.run(cmd_fb, capture_output=True, text=True, timeout=10, cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"))
                if r2.returncode == 0:
                    return {"ok": True, "path": path, "scheduled": True, "session_zero": True, "error": None}
            return {"ok": False, "path": path, "scheduled": False, "error": err}
        if run_now:
            subprocess.run(
                ["schtasks", "/run", "/tn", task_name],
                capture_output=True,
                timeout=10,
                cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
            )
        return {"ok": True, "path": path, "scheduled": True, "run_now": run_now, "error": None}
    except Exception as e:
        logger.exception("open_notepad failed: %s", e)
        return {"ok": False, "path": "", "scheduled": False, "error": str(e)}


def handle_windows_write_worker_token(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Escribe el WORKER_TOKEN del entorno en C:\\openclaw-worker\\worker_token
    para que el Worker interactivo (sesión 1) pueda leerlo al arrancar.
    Solo Windows; el Worker debe tener WORKER_TOKEN en env (NSSM).
    """
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo Windows."}
    token = os.environ.get("WORKER_TOKEN", "").strip()
    if not token:
        return {"ok": False, "error": "WORKER_TOKEN no definido en el entorno."}
    path = r"C:\openclaw-worker\worker_token"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(token)
        return {"ok": True, "path": path, "error": None}
    except Exception as e:
        logger.exception("write_worker_token failed: %s", e)
        return {"ok": False, "path": path, "error": str(e)}


def handle_windows_firewall_allow_port(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Añade regla de firewall en la VM para permitir inbound en un puerto.
    Input: port (int), name (str, opcional). Solo Windows.
    """
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo Windows."}
    port = input_data.get("port")
    if port is None:
        port = 8089
    port = int(port)
    name = _validate_safe_name(input_data.get("name") or f"OpenClaw-Worker-{port}")
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"],
            capture_output=True,
            timeout=5,
        )
        r = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={name}",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                f"localport={port}",
                "profile=any",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
        )
        if r.returncode != 0 and "already exists" not in (r.stderr or "").lower():
            return {"ok": False, "port": port, "error": (r.stderr or r.stdout or "netsh failed").strip()}
        return {"ok": True, "port": port, "name": name, "error": None}
    except Exception as e:
        logger.exception("firewall_allow_port failed: %s", e)
        return {"ok": False, "port": port, "error": str(e)}


def handle_windows_start_interactive_worker(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Arranca el Worker interactivo (uvicorn puerto 8089) en segundo plano.
    Ejecuta scripts/vm/start_interactive_worker.bat; el proceso queda en sesión 0
    salvo que se haya arrancado por logon de Rick. Útil para tener 8089 escuchando.
    """
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo Windows."}
    repo = os.environ.get("PYTHONPATH", "").strip() or r"C:\GitHub\umbral-agent-stack"
    bat = os.path.join(repo, "scripts", "vm", "start_interactive_worker.bat")
    if not os.path.isfile(bat):
        return {"ok": False, "error": f"No existe {bat}"}
    try:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        subprocess.Popen(
            ["cmd", "/c", "start", "/b", "", bat],
            cwd=repo,
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "bat": bat, "error": None}
    except Exception as e:
        logger.exception("start_interactive_worker failed: %s", e)
        return {"ok": False, "error": str(e)}


def handle_windows_add_interactive_worker_to_startup(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un acceso directo en la carpeta Inicio de Windows para que el Worker
    interactivo (start_interactive_worker.bat) se ejecute al iniciar sesión el usuario.
    Solo Windows. El Worker debe poder escribir en la carpeta del usuario (ej. ejecutar
    como SYSTEM con acceso a C:\\Users\\<user>).
    Input: username (str, opcional). Default: "Rick".
    """
    if sys.platform != "win32":
        return {"ok": False, "error": "Solo Windows."}
    username = _validate_safe_name(input_data.get("username") or "Rick")
    repo = os.environ.get("PYTHONPATH", "").strip() or r"C:\GitHub\umbral-agent-stack"
    bat = os.path.join(repo, "scripts", "vm", "start_interactive_worker.bat")
    if not os.path.isfile(bat):
        return {"ok": False, "error": f"No existe {bat}"}
    startup = os.path.join("C:\\Users", username, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    link_path = os.path.join(startup, "StartInteractiveWorker.lnk")
    try:
        os.makedirs(startup, exist_ok=True)
        ps = (
            f'$w = New-Object -ComObject WScript.Shell; '
            f'$s = $w.CreateShortcut("{link_path}"); '
            f'$s.TargetPath = "{bat}"; '
            f'$s.WorkingDirectory = "{repo}"; '
            f'$s.Save()'
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.environ.get("SYSTEMROOT", "C:\\Windows"),
        )
        if r.returncode != 0:
            return {"ok": False, "error": (r.stderr or r.stdout or "PowerShell failed").strip()}
        return {"ok": True, "startup": startup, "link": link_path, "error": None}
    except Exception as e:
        logger.exception("add_interactive_worker_to_startup failed: %s", e)
        return {"ok": False, "error": str(e)}
