import importlib.util
import json
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


def test_check_worker_preflight_success(monkeypatch):
    module = _load_script_module(
        "granola_vm_raw_intake_preflight_success",
        "scripts/vm/granola_vm_raw_intake.py",
    )

    class DummyResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: DummyResponse(200))
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: DummyResponse(200))

    result = module._check_worker_preflight(
        "http://127.0.0.1:8088",
        "token-123",
    )

    assert result["ok"] is True
    assert result["health_ok"] is True
    assert result["ping_ok"] is True


def test_run_vm_raw_intake_requires_healthy_worker_for_execute(monkeypatch, tmp_path):
    module = _load_script_module(
        "granola_vm_raw_intake_requires_worker",
        "scripts/vm/granola_vm_raw_intake.py",
    )

    monkeypatch.setattr(module, "build_report", lambda **kwargs: {"batch1_recent_unique": []})
    monkeypatch.setattr(module, "_select_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        module,
        "_prepare_batch_inputs",
        lambda **kwargs: {
            "prepared": [],
            "batch_dir": str(tmp_path / "batch"),
            "export_dir": str(tmp_path / "exports"),
            "processed_dir": str(tmp_path / "processed"),
            "manifest_path": str(tmp_path / "manifest.json"),
            "missing_document_ids": [],
        },
    )
    monkeypatch.setattr(
        module,
        "_check_worker_preflight",
        lambda *args, **kwargs: {
            "ok": False,
            "worker_url": "http://127.0.0.1:8088",
            "failure": "health_check_failed",
        },
    )

    try:
        module.run_vm_raw_intake(
            cache_path=tmp_path / "cache-v6.json",
            bucket="batch1_recent_unique",
            limit=5,
            execute=True,
            allow_ambiguous=False,
            notify_enlace=False,
            max_raw_items=200,
            recent_days=7,
            batch_dir=None,
            worker_url="http://127.0.0.1:8088",
            worker_token="token",
            enable_private_api_hydration=True,
            write_report=False,
            report_dir=tmp_path / "reports",
        )
    except RuntimeError as exc:
        assert "Worker preflight failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when worker preflight is unhealthy")


def test_run_vm_raw_intake_executes_through_worker_and_writes_report(monkeypatch, tmp_path):
    module = _load_script_module(
        "granola_vm_raw_intake_executes_worker",
        "scripts/vm/granola_vm_raw_intake.py",
    )

    monkeypatch.setattr(module, "build_report", lambda **kwargs: {"batch1_recent_unique": []})
    monkeypatch.setattr(
        module,
        "_select_candidates",
        lambda *args, **kwargs: [
            {
                "document_id": "doc-1",
                "title": "BIM Forum",
                "meeting_date": "2026-03-30",
                "classification": "missing_unique",
            }
        ],
    )
    monkeypatch.setattr(
        module,
        "_prepare_batch_inputs",
        lambda **kwargs: {
            "prepared": [{"document_id": "doc-1", "task_input": {"title": "BIM Forum"}}],
            "batch_dir": str(tmp_path / "batch"),
            "export_dir": str(tmp_path / "exports"),
            "processed_dir": str(tmp_path / "processed"),
            "manifest_path": str(tmp_path / "manifest.json"),
            "missing_document_ids": [],
        },
    )
    monkeypatch.setattr(
        module,
        "_check_worker_preflight",
        lambda *args, **kwargs: {
            "ok": True,
            "worker_url": "http://127.0.0.1:8088",
            "health_ok": True,
            "ping_ok": True,
            "failure": "",
        },
    )
    monkeypatch.setattr(
        module,
        "_execute_prepared",
        lambda prepared, **kwargs: [
            {
                "document_id": prepared[0]["document_id"],
                "title": "BIM Forum",
                "ok": True,
                "response": {"page_id": "page-1"},
            }
        ],
    )

    summary = module.run_vm_raw_intake(
        cache_path=tmp_path / "cache-v6.json",
        bucket="batch1_recent_unique",
        limit=5,
        execute=True,
        allow_ambiguous=False,
        notify_enlace=False,
        max_raw_items=200,
        recent_days=7,
        batch_dir=None,
        worker_url="http://127.0.0.1:8088",
        worker_token="token",
        enable_private_api_hydration=True,
        write_report=True,
        report_dir=tmp_path / "reports",
    )

    assert summary["execution_mode"] == "worker"
    assert summary["worker_preflight"]["ok"] is True
    assert summary["results"][0]["ok"] is True
    report_path = Path(summary["report_path"])
    assert report_path.exists()
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written["results"][0]["response"]["page_id"] == "page-1"


def test_run_vm_raw_intake_skips_prepare_when_no_selected_candidates(monkeypatch, tmp_path):
    module = _load_script_module(
        "granola_vm_raw_intake_skips_prepare",
        "scripts/vm/granola_vm_raw_intake.py",
    )

    monkeypatch.setattr(module, "build_report", lambda **kwargs: {"batch1_recent_unique": []})
    monkeypatch.setattr(module, "_select_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        module,
        "_check_worker_preflight",
        lambda *args, **kwargs: {
            "ok": True,
            "worker_url": "http://127.0.0.1:8088",
            "health_ok": True,
            "ping_ok": True,
            "failure": "",
        },
    )

    called = {"prepare": False}

    def _unexpected_prepare(**kwargs):
        called["prepare"] = True
        raise AssertionError("_prepare_batch_inputs should not be called")

    monkeypatch.setattr(module, "_prepare_batch_inputs", _unexpected_prepare)

    summary = module.run_vm_raw_intake(
        cache_path=tmp_path / "cache-v6.json",
        bucket="batch1_recent_unique",
        limit=5,
        execute=False,
        allow_ambiguous=False,
        notify_enlace=False,
        max_raw_items=200,
        recent_days=7,
        batch_dir=None,
        worker_url="http://127.0.0.1:8088",
        worker_token="token",
        enable_private_api_hydration=True,
        write_report=False,
        report_dir=tmp_path / "reports",
    )

    assert called["prepare"] is False
    assert summary["selected_count"] == 0
    assert summary["prepared_count"] == 0
