import importlib.util
import os
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


# --- Freshness guard (spec b0004): catch a silently dead intake ---------------


def _fresh_now():
    return datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)


def _raw_with_dates(dates):
    """Build a raw DB where every row is otherwise healthy, so only the
    freshness of MAX(Fecha) is under test (recent_issues stays 0)."""
    return {
        "schema": {
            "Fecha": "date",
            "Trazabilidad": "rich_text",
            "Estado": "status",
        },
        "items": [
            {
                "page_id": f"page-{i}",
                "title": f"Reunion {i}",
                "properties": {
                    "Fecha": {"start": d},
                    "Trazabilidad": "granola_document_id=doc\nsource=granola",
                    "Estado": "Procesado",
                },
            }
            for i, d in enumerate(dates)
        ],
    }


def test_fresh_intake_is_not_stale():
    module = _load_module()
    report = module.build_gap_report(_raw_with_dates(["2026-06-14"]), now=_fresh_now())

    assert report["max_date"] == "2026-06-14"
    assert report["freshness_days"] == 1
    assert report["stale"] is False
    assert report["stale_reason"] == ""
    assert report["recent_issues"] == 0
    assert module.exit_code_for_report(report) == 0


def test_stale_intake_beyond_threshold_exits_3():
    module = _load_module()
    report = module.build_gap_report(_raw_with_dates(["2026-06-01"]), now=_fresh_now())

    assert report["max_date"] == "2026-06-01"
    assert report["freshness_days"] == 14
    assert report["stale"] is True
    assert report["stale_reason"] == "max_date_older_than_threshold"
    assert module.exit_code_for_report(report) == 3


def test_freshness_border_exactly_threshold_is_not_stale():
    module = _load_module()
    # 2026-06-05 is exactly 10 days before 2026-06-15 (default threshold = 10).
    report = module.build_gap_report(_raw_with_dates(["2026-06-05"]), now=_fresh_now())

    assert report["freshness_days"] == 10
    assert report["stale"] is False
    assert module.exit_code_for_report(report) == 0


def test_freshness_border_one_day_past_threshold_is_stale():
    module = _load_module()
    report = module.build_gap_report(_raw_with_dates(["2026-06-04"]), now=_fresh_now())

    assert report["freshness_days"] == 11
    assert report["stale"] is True
    assert report["stale_reason"] == "max_date_older_than_threshold"


def test_freshness_uses_newest_date_across_items():
    module = _load_module()
    report = module.build_gap_report(
        _raw_with_dates(["2026-05-01", "2026-06-14", "2026-05-20"]), now=_fresh_now()
    )

    assert report["max_date"] == "2026-06-14"
    assert report["stale"] is False


def test_custom_stale_after_days_threshold():
    module = _load_module()
    report = module.build_gap_report(
        _raw_with_dates(["2026-06-10"]), now=_fresh_now(), stale_after_days=3
    )

    assert report["freshness_days"] == 5
    assert report["stale_after_days"] == 3
    assert report["stale"] is True
    assert report["stale_reason"] == "max_date_older_than_threshold"


def test_no_dated_items_is_stale_not_vacuous_ok():
    module = _load_module()
    raw = {
        "schema": {"Fecha": "date"},
        "items": [
            {"page_id": "p", "title": "Sin fecha", "properties": {"Fecha": None}}
        ],
    }
    report = module.build_gap_report(raw, now=_fresh_now())

    assert report["max_date"] == ""
    assert report["freshness_days"] is None
    assert report["stale"] is True
    assert report["stale_reason"] == "no_dated_items"
    assert module.exit_code_for_report(report) == 3


def test_recent_issues_take_precedence_over_stale_in_exit_code():
    module = _load_module()
    # A recent content gap (exit 2) outranks staleness (exit 3) when mapping.
    assert module.exit_code_for_report({"recent_issues": 2, "stale": True}) == 2


def test_exit_code_healthy_report_is_zero():
    module = _load_module()
    assert module.exit_code_for_report({"recent_issues": 0, "stale": False}) == 0


def test_stale_after_days_env_override_parsing():
    module = _load_module()
    key = module.STALE_ENV_VAR
    prev = os.environ.get(key)
    try:
        os.environ[key] = "3"
        assert module._stale_after_days_from_env() == 3
        os.environ[key] = "not-an-int"
        assert module._stale_after_days_from_env() == module.DEFAULT_STALE_AFTER_DAYS
        os.environ[key] = "0"
        assert module._stale_after_days_from_env() == module.DEFAULT_STALE_AFTER_DAYS
        os.environ.pop(key, None)
        assert module._stale_after_days_from_env() == module.DEFAULT_STALE_AFTER_DAYS
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev
