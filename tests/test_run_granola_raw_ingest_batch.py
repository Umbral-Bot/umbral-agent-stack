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


def test_select_candidates_rejects_ambiguous_bucket_without_flag():
    module = _load_script_module(
        "run_granola_raw_ingest_batch_rejects_ambiguous",
        "scripts/run_granola_raw_ingest_batch.py",
    )

    report = {
        "batch1_recent_ambiguous": [
            {"document_id": "doc-1", "title": "Konstruedu", "classification": "ambiguous"}
        ]
    }

    try:
        module._select_candidates(report, bucket="batch1_recent_ambiguous")
    except ValueError as exc:
        assert "--allow-ambiguous" in str(exc)
    else:
        raise AssertionError("Expected ValueError for ambiguous bucket")


def test_select_candidates_filters_document_ids_and_limit():
    module = _load_script_module(
        "run_granola_raw_ingest_batch_filters",
        "scripts/run_granola_raw_ingest_batch.py",
    )

    report = {
        "batch1_recent_unique": [
            {"document_id": "doc-1", "title": "A", "classification": "missing_unique"},
            {"document_id": "doc-2", "title": "B", "classification": "missing_unique"},
            {"document_id": "doc-3", "title": "C", "classification": "missing_unique"},
        ]
    }

    selected = module._select_candidates(
        report,
        bucket="batch1_recent_unique",
        document_ids=["doc-2", "doc-3"],
        limit=1,
    )

    assert len(selected) == 1
    assert selected[0]["document_id"] == "doc-2"


def test_resolve_execution_mode_prefers_worker_when_creds_exist():
    module = _load_script_module(
        "run_granola_raw_ingest_batch_mode_worker",
        "scripts/run_granola_raw_ingest_batch.py",
    )

    mode = module._resolve_execution_mode(
        "auto",
        worker_url="http://localhost:8088",
        worker_token="test-token",
    )

    assert mode == "worker"


def test_build_task_input_disables_notifications_and_legacy_writes():
    module = _load_script_module(
        "run_granola_raw_ingest_batch_build_input",
        "scripts/run_granola_raw_ingest_batch.py",
    )

    parsed = {
        "title": "BIM Forum",
        "content": "Notes",
        "date": "2026-03-30",
        "source": "granola",
        "granola_document_id": "",
    }
    export_item = {
        "document_id": "doc-123",
        "title": "BIM Forum",
        "meeting_date": "2026-03-30",
    }

    task_input = module._build_task_input(parsed, export_item, notify_enlace=False)

    assert task_input["notify_enlace"] is False
    assert task_input["allow_legacy_raw_task_writes"] is False
    assert task_input["granola_document_id"] == "doc-123"
