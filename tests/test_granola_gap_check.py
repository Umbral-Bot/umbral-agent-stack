import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    script_path = REPO_ROOT / "scripts/granola_gap_check.py"
    spec = importlib.util.spec_from_file_location("granola_gap_check_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["granola_gap_check_test"] = module
    spec.loader.exec_module(module)
    return module


def _fixed_now():
    return datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def test_flattened_read_database_date_shape_detects_recent_gap():
    module = _load_module()
    raw = {
        "schema": {
            "Fecha": "date",
            "Trazabilidad": "rich_text",
            "Estado": "status",
        },
        "items": [
            {
                "page_id": "page-1",
                "title": "Reunion sin trazabilidad",
                "properties": {
                    "Fecha": {"start": "2026-06-04", "end": None},
                    "Trazabilidad": "",
                    "Estado": "Pendiente",
                },
            }
        ],
    }

    report = module.build_gap_report(raw, now=_fixed_now())

    assert report["total_pages"] == 1
    assert report["recent_issues"] == 1
    assert report["skipped_no_date"] == 0
    assert report["issues"][0]["date"] == "2026-06-04"
    assert report["issues"][0]["reasons"] == [
        "no_traceability",
        "still_pending",
    ]


def test_flattened_read_database_traceability_string_accepts_document_id():
    module = _load_module()
    raw = {
        "schema": {
            "Fecha": "date",
            "Trazabilidad": "rich_text",
            "Estado": "select",
        },
        "items": [
            {
                "page_id": "page-2",
                "title": "Reunion OK",
                "properties": {
                    "Fecha": {"start": "2026-06-04T09:00:00.000-03:00"},
                    "Trazabilidad": "granola_document_id=doc-123\nsource=granola",
                    "Estado": "Procesado",
                },
            }
        ],
    }

    report = module.build_gap_report(raw, now=_fixed_now())

    assert report["recent_issues"] == 0
    assert report["skipped_no_date"] == 0


def test_raw_notion_property_shape_still_supported():
    module = _load_module()
    raw = {
        "schema": {
            "Fecha": "date",
            "Trazabilidad": "rich_text",
            "Estado": "status",
        },
        "items": [
            {
                "page_id": "page-3",
                "title": "Raw shape",
                "properties": {
                    "Fecha": {
                        "type": "date",
                        "date": {"start": "2026-06-03", "end": None},
                    },
                    "Trazabilidad": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "source=granola"}],
                    },
                    "Estado": {
                        "type": "status",
                        "status": {"name": "Pendiente"},
                    },
                },
            }
        ],
    }

    report = module.build_gap_report(raw, now=_fixed_now())

    assert report["recent_issues"] == 1
    assert report["issues"][0]["date"] == "2026-06-03"
    assert report["issues"][0]["reasons"] == [
        "missing_granola_document_id",
        "still_pending",
    ]


def test_old_items_without_date_are_not_counted_as_recent_but_are_reported():
    module = _load_module()
    raw = {
        "schema": {
            "Fecha": "date",
            "Trazabilidad": "rich_text",
            "Estado": "status",
        },
        "items": [
            {
                "page_id": "page-4",
                "title": "Sin fecha",
                "properties": {
                    "Fecha": None,
                    "Trazabilidad": "",
                    "Estado": "Pendiente",
                },
            }
        ],
    }

    report = module.build_gap_report(raw, now=_fixed_now())

    assert report["recent_issues"] == 0
    assert report["skipped_no_date"] == 1
