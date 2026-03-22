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


class _FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._json_data


class _FakeClient:
    def __init__(self, *, get_response=None, post_response=None, timeout=None):
        self.get_response = get_response
        self.post_response = post_response
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return self.get_response

    def post(self, url, headers=None, json=None):
        return self.post_response


def test_load_inventory_reads_health_tasks():
    module = _load_script_module("worker_inventory_smoke_inventory", "scripts/worker_inventory_smoke.py")
    target = module.TargetSpec(name="vm-headless", base_url="http://localhost:8088")
    client_factory = lambda timeout: _FakeClient(  # noqa: E731
        get_response=_FakeResponse(
            json_data={
                "version": "0.4.0",
                "tasks_registered": [
                    "ping",
                    "notion.upsert_deliverable",
                    "notion.upsert_bridge_item",
                ],
            },
            text="ok",
        ),
        timeout=timeout,
    )

    snapshot = module.load_inventory(target, client_factory=client_factory)

    assert snapshot.version == "0.4.0"
    assert snapshot.total_tasks == 3
    assert "notion.upsert_deliverable" in snapshot.tasks


def test_compare_inventory_detects_missing_and_extra_handlers():
    module = _load_script_module("worker_inventory_smoke_compare", "scripts/worker_inventory_smoke.py")
    reference = module.InventorySnapshot(
        target=module.TargetSpec(name="vps", base_url="http://127.0.0.1:8088"),
        version="0.4.0",
        tasks=frozenset(
            {
                "ping",
                "notion.upsert_deliverable",
                "notion.upsert_bridge_item",
            }
        ),
    )
    candidate = module.InventorySnapshot(
        target=module.TargetSpec(name="vm", base_url="http://100.109.16.40:8088"),
        version="0.4.0",
        tasks=frozenset({"ping", "custom.extra"}),
    )

    missing_required, missing_vs_reference, extra_vs_reference = module.compare_inventory(
        reference,
        candidate,
        module.DEFAULT_REQUIRED_TASKS,
    )

    assert missing_required == [
        "notion.upsert_bridge_item",
        "notion.upsert_deliverable",
    ]
    assert missing_vs_reference == [
        "notion.upsert_bridge_item",
        "notion.upsert_deliverable",
    ]
    assert extra_vs_reference == ["custom.extra"]


def test_smoke_task_accepts_handler_level_error_when_http_is_200():
    module = _load_script_module("worker_inventory_smoke_success", "scripts/worker_inventory_smoke.py")
    target = module.TargetSpec(name="vm-interactive", base_url="http://localhost:8089")
    client_factory = lambda timeout: _FakeClient(  # noqa: E731
        post_response=_FakeResponse(
            status_code=200,
            json_data={
                "ok": True,
                "result": {
                    "ok": False,
                    "error": "NOTION_DELIVERABLES_DB_ID not configured on server",
                },
            },
            text="ok",
        ),
        timeout=timeout,
    )

    result = module.smoke_task(
        target,
        "token-123",
        "notion.upsert_deliverable",
        client_factory=client_factory,
    )

    assert result.handled is True
    assert result.status_code == 200
    assert "NOTION_DELIVERABLES_DB_ID" in result.message


def test_smoke_task_flags_unknown_task_responses():
    module = _load_script_module("worker_inventory_smoke_fail", "scripts/worker_inventory_smoke.py")
    target = module.TargetSpec(name="vm-interactive", base_url="http://localhost:8089")
    client_factory = lambda timeout: _FakeClient(  # noqa: E731
        post_response=_FakeResponse(
            status_code=400,
            json_data={"detail": "Unknown task: notion.upsert_bridge_item"},
            text="bad request",
        ),
        timeout=timeout,
    )

    result = module.smoke_task(
        target,
        "token-123",
        "notion.upsert_bridge_item",
        client_factory=client_factory,
    )

    assert result.handled is False
    assert result.status_code == 400
    assert "Unknown task" in result.message
