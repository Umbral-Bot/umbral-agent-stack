import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_worker_url_prefers_local_worker_for_general_tasks():
    module = _load_script_module("run_worker_task_general", "scripts/run_worker_task.py")
    env_vars = {
        "WORKER_URL": "http://127.0.0.1:8088",
        "WORKER_URL_VM": "http://100.109.16.40:8088",
        "WORKER_URL_VM_INTERACTIVE": "http://100.109.16.40:8089",
    }

    url = module._resolve_worker_url("gmail.list_drafts", {}, env_vars, "")

    assert url == "http://127.0.0.1:8088"


def test_resolve_worker_url_prefers_vm_for_windows_tasks():
    module = _load_script_module("run_worker_task_windows", "scripts/run_worker_task.py")
    env_vars = {
        "WORKER_URL": "http://127.0.0.1:8088",
        "WORKER_URL_VM": "http://100.109.16.40:8088",
        "WORKER_URL_VM_INTERACTIVE": "http://100.109.16.40:8089",
    }

    url = module._resolve_worker_url("windows.open_url", {}, env_vars, "")

    assert url == "http://100.109.16.40:8088"


def test_resolve_worker_url_prefers_interactive_when_session_requests_it():
    module = _load_script_module("run_worker_task_interactive", "scripts/run_worker_task.py")
    env_vars = {
        "WORKER_URL": "http://127.0.0.1:8088",
        "WORKER_URL_VM": "http://100.109.16.40:8088",
        "WORKER_URL_VM_INTERACTIVE": "http://100.109.16.40:8089",
    }

    url = module._resolve_worker_url("gui.desktop_status", {"session": "interactive"}, env_vars, "")

    assert url == "http://100.109.16.40:8089"
