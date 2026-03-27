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


def test_load_plan_file_accepts_object_with_plans(tmp_path):
    module = _load_script_module(
        "run_granola_operational_batch_load",
        "scripts/run_granola_operational_batch.py",
    )
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(
        json.dumps({"plans": [{"transcript_page_id": "raw-1", "curated_payload": {"session_name": "X"}, "human_task_payload": {"task_name": "Y"}}]}),
        encoding="utf-8",
    )

    plans = module._load_plan_file(str(plan_file))

    assert isinstance(plans, list)
    assert plans[0]["transcript_page_id"] == "raw-1"


def test_normalize_plan_defaults_to_dry_run():
    module = _load_script_module(
        "run_granola_operational_batch_normalize",
        "scripts/run_granola_operational_batch.py",
    )

    plan = module._normalize_plan(
        {
            "label": "konstruedu",
            "transcript_page_id": "raw-1",
            "curated_payload": {"session_name": "Sesion X"},
            "human_task_payload": {"task_name": "Follow-up X"},
        },
        True,
    )

    assert plan["label"] == "konstruedu"
    assert plan["dry_run"] is True
    assert plan["transcript_page_id"] == "raw-1"


def test_normalize_plan_rejects_missing_destination():
    module = _load_script_module(
        "run_granola_operational_batch_missing_destination",
        "scripts/run_granola_operational_batch.py",
    )

    try:
        module._normalize_plan(
            {
                "transcript_page_id": "raw-1",
                "curated_payload": {"session_name": "Sesion X"},
            },
            True,
        )
    except ValueError as exc:
        assert "at least one destination payload" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for missing destination payload")


def test_select_plans_can_filter_by_label():
    module = _load_script_module(
        "run_granola_operational_batch_select",
        "scripts/run_granola_operational_batch.py",
    )
    plans = [
        {"label": "a", "transcript_page_id": "raw-1"},
        {"label": "b", "transcript_page_id": "raw-2"},
    ]

    selected = module._select_plans(plans, only_label="b")

    assert len(selected) == 1
    assert selected[0]["transcript_page_id"] == "raw-2"
