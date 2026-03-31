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
