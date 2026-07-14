import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    script_path = REPO_ROOT / "scripts/vm/granola_mcp_ingest.py"
    spec = importlib.util.spec_from_file_location("granola_mcp_ingest_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["granola_mcp_ingest_test"] = module
    spec.loader.exec_module(module)
    return module


def test_parse_meeting_date_human_string():
    module = _load_module()
    assert module.parse_meeting_date("Jul 13, 2026 9:02 AM GMT-4") == "2026-07-13"


def test_parse_meeting_date_single_digit_day_is_zero_padded():
    module = _load_module()
    assert module.parse_meeting_date("Jun 5, 2026 1:00 PM") == "2026-06-05"


def test_parse_meeting_date_iso_prefix():
    module = _load_module()
    assert module.parse_meeting_date("2026-07-13T09:02:00-04:00") == "2026-07-13"


def test_parse_meeting_date_unknown_or_empty():
    module = _load_module()
    assert module.parse_meeting_date("someday soon") == ""
    assert module.parse_meeting_date("") == ""
    assert module.parse_meeting_date(None) == ""


def test_normalize_participants_strings_and_dicts_dedup():
    module = _load_module()
    meeting = {
        "participants": [
            "David Moreira <dm@umbralbim.cl>",
            {"name": "Nicolas", "email": "nico@x.cl"},
            {"email": "only@email.cl"},
            "David Moreira <dm@umbralbim.cl>",  # duplicate
            "",
        ]
    }
    assert module.normalize_participants(meeting) == [
        "David Moreira <dm@umbralbim.cl>",
        "Nicolas",
        "only@email.cl",
    ]


def test_normalize_participants_falls_back_to_attendees_key():
    module = _load_module()
    assert module.normalize_participants({"attendees": ["A", "B"]}) == ["A", "B"]


def test_build_content_includes_header_and_summary():
    module = _load_module()
    content = module.build_content({"summary": "## Puntos\n- uno"})
    assert content.startswith("> Captura via Granola MCP")
    assert "Sin transcripcion verbatim" in content
    assert "## Puntos\n- uno" in content


def test_build_content_header_only_when_no_summary():
    module = _load_module()
    content = module.build_content({})
    assert content == module._CONTENT_HEADER


def test_build_payload_full_mapping():
    module = _load_module()
    meeting = {
        "id": "ff1fbcb8-615a-49bc-9db3-eb75dbee99e5",
        "title": "BIM Forum - Automatizacion",
        "date": "Jul 13, 2026 9:02 AM GMT-4",
        "participants": ["David Moreira <dm@umbralbim.cl>"],
        "summary": "### Resumen\n- algo",
        "source_url": "https://notes.granola.ai/d/ff1fbcb8",
        "updated_at": "2026-07-13T13:02:00Z",
    }
    payload = module.build_payload(meeting)

    assert payload["title"] == "BIM Forum - Automatizacion"
    assert payload["source"] == module.CAPTURE_SOURCE == "granola_mcp"
    assert payload["granola_document_id"] == meeting["id"]
    assert payload["date"] == "2026-07-13"
    assert payload["attendees"] == ["David Moreira <dm@umbralbim.cl>"]
    assert payload["source_url"] == meeting["source_url"]
    assert payload["source_updated_at"] == "2026-07-13T13:02:00Z"
    assert payload["metadata"]["capture_mode"] == "mcp_summary_no_transcript"
    assert payload["metadata"]["source_updated_at"] == "2026-07-13T13:02:00Z"
    assert payload["notify_enlace"] is False
    assert "### Resumen\n- algo" in payload["content"]


def test_build_payload_requires_id():
    module = _load_module()
    with pytest.raises(ValueError):
        module.build_payload({"title": "no id"})


def test_build_payload_title_falls_back_to_id():
    module = _load_module()
    payload = module.build_payload({"id": "abc-123"})
    assert payload["title"] == "abc-123"
    # No date / attendees / source_url keys when absent.
    assert "date" not in payload
    assert "attendees" not in payload
    assert "source_url" not in payload


def test_build_payload_notify_enlace_opt_in():
    module = _load_module()
    payload = module.build_payload({"id": "x"}, notify_enlace=True)
    assert payload["notify_enlace"] is True


def test_build_payloads_skips_non_dicts():
    module = _load_module()
    payloads = module.build_payloads([{"id": "a"}, "nope", None, {"id": "b"}])
    assert [p["granola_document_id"] for p in payloads] == ["a", "b"]


def test_load_meetings_accepts_list_wrapper_and_single():
    module = _load_module()
    assert module._load_meetings('[{"id":"a"}]') == [{"id": "a"}]
    assert module._load_meetings('{"meetings":[{"id":"a"}]}') == [{"id": "a"}]
    assert module._load_meetings('{"id":"solo"}') == [{"id": "solo"}]


def test_load_meetings_rejects_bad_shape():
    module = _load_module()
    with pytest.raises(ValueError):
        module._load_meetings('"just a string"')
