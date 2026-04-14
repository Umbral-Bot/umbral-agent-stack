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


def test_extract_traceability_document_id():
    module = _load_script_module(
        "list_granola_raw_ingest_gap_traceability",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    document_id = module._extract_traceability_document_id(
        {
            "Trazabilidad": (
                "granola_document_id=doc-123\n"
                "source_updated_at=2026-03-31T12:00:00Z\n"
                "ingest_path=granola.process_transcript"
            )
        }
    )

    assert document_id == "doc-123"


def test_classify_gap_prefers_document_id_match():
    module = _load_script_module(
        "list_granola_raw_ingest_gap_classify",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    exports = [
        module.ExportItem(
            document_id="doc-123",
            title="Konstruedu",
            meeting_date="2026-03-30",
            notes_source="private_api_panels",
            transcript_source="cache",
            normalized_title=module._normalize_title("Konstruedu"),
        )
    ]
    raw_snapshot = {
        "real_items": [
            {
                "page_id": "raw-1",
                "url": "https://notion.so/raw-1",
                "title": "Konstruedu",
                "normalized_title": module._normalize_title("Konstruedu"),
                "granola_document_id": "doc-123",
                "properties": {"Fecha": {"start": "2026-03-30"}},
            }
        ],
        "smoke_items": [],
        "all_items": [],
    }

    result = module._classify_gap(exports, raw_snapshot, recent_days=7)

    assert result["gap_summary"]["likely_present_count"] == 1
    assert result["gap_summary"]["batch1_recent_ambiguous_count"] == 0
    assert result["likely_present"][0]["classification"] == "likely_present_document_id"


def test_classify_gap_matches_document_id_even_when_raw_row_is_smoke():
    module = _load_script_module(
        "list_granola_raw_ingest_gap_smoke_document_match",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    exports = [
        module.ExportItem(
            document_id="doc-smoke-1",
            title="Reunión de prueba",
            meeting_date="2026-04-02",
            notes_source="private_api_panels",
            transcript_source="private_api_transcript",
            normalized_title=module._normalize_title("Reunión de prueba"),
        )
    ]
    raw_snapshot = {
        "real_items": [],
        "smoke_items": [
            {
                "page_id": "raw-smoke-1",
                "url": "https://notion.so/raw-smoke-1",
                "title": "Reunión de prueba",
                "normalized_title": module._normalize_title("Reunión de prueba"),
                "granola_document_id": "doc-smoke-1",
                "properties": {"Fecha": {"start": "2026-04-02"}},
            }
        ],
        "all_items": [],
    }

    result = module._classify_gap(exports, raw_snapshot, recent_days=7)

    assert result["gap_summary"]["likely_present_count"] == 1
    assert result["gap_summary"]["batch1_recent_unique_count"] == 0
    assert result["likely_present"][0]["classification"] == "likely_present_document_id"
    assert result["likely_present"][0]["matched_raw_page_id"] == "raw-smoke-1"


def test_recent_gap_count_sums_recent_unique_and_ambiguous():
    module = _load_script_module(
        "list_granola_raw_ingest_gap_recent_count",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    report = {
        "gap_summary": {
            "batch1_recent_unique_count": 1,
            "batch1_recent_ambiguous_count": 2,
            "historic_unique_count": 3,
            "historic_ambiguous_count": 4,
            "recent_action_required_count": 3,
            "action_required_count": 10,
        }
    }

    assert module._recent_gap_count(report) == 3
    assert module._action_required_gap_count(report) == 10


def test_main_returns_nonzero_when_fail_on_recent_gaps(monkeypatch):
    module = _load_script_module(
        "list_granola_raw_ingest_gap_fail_recent",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    monkeypatch.setattr(
        module,
        "build_report",
        lambda **kwargs: {
            "gap_summary": {
                "likely_present_count": 0,
                "batch1_recent_unique_count": 0,
                "batch1_recent_ambiguous_count": 1,
                "historic_unique_count": 0,
                "historic_ambiguous_count": 0,
                "recent_action_required_count": 1,
                "action_required_count": 1,
            },
            "cache_summary": {
                "scanned": 1,
                "exportable_count": 1,
                "skipped_unusable": 0,
            },
            "raw_summary": {
                "raw_total_count": 0,
                "raw_real_count": 0,
                "raw_smoke_count": 0,
            },
            "batch1_recent_unique": [],
            "batch1_recent_ambiguous": [],
            "historic_unique": [],
            "historic_ambiguous": [],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["list_granola_raw_ingest_gap.py", "--fail-on-recent-gaps"],
    )

    assert module.main() == 2


def test_main_allows_historic_only_gaps_when_recent_flag_is_used(monkeypatch):
    module = _load_script_module(
        "list_granola_raw_ingest_gap_fail_recent_historic_only",
        "scripts/list_granola_raw_ingest_gap.py",
    )

    monkeypatch.setattr(
        module,
        "build_report",
        lambda **kwargs: {
            "gap_summary": {
                "likely_present_count": 0,
                "batch1_recent_unique_count": 0,
                "batch1_recent_ambiguous_count": 0,
                "historic_unique_count": 1,
                "historic_ambiguous_count": 0,
                "recent_action_required_count": 0,
                "action_required_count": 1,
            },
            "cache_summary": {
                "scanned": 1,
                "exportable_count": 1,
                "skipped_unusable": 0,
            },
            "raw_summary": {
                "raw_total_count": 0,
                "raw_real_count": 0,
                "raw_smoke_count": 0,
            },
            "batch1_recent_unique": [],
            "batch1_recent_ambiguous": [],
            "historic_unique": [],
            "historic_ambiguous": [],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["list_granola_raw_ingest_gap.py", "--fail-on-recent-gaps"],
    )

    assert module.main() == 0
