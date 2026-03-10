import json

from scripts.vm.granola_api_ingest import (
    choose_document,
    load_granola_access_token,
    render_transcript_markdown,
)


def test_load_granola_access_token_from_supabase_payload(tmp_path):
    payload = {
        "workos_tokens": json.dumps(
            {
                "access_token": "granola-token-123",
                "refresh_token": "refresh-token",
            }
        )
    }
    path = tmp_path / "supabase.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_granola_access_token(str(path)) == "granola-token-123"


def test_choose_document_prefers_latest():
    docs = [
        {"id": "a", "title": "Vieja", "updated_at": "2026-03-01T10:00:00Z"},
        {"id": "b", "title": "Nueva", "updated_at": "2026-03-02T10:00:00Z"},
    ]

    selected = choose_document(docs, latest=True)

    assert selected["id"] == "b"


def test_choose_document_by_title_query():
    docs = [
        {"id": "a", "title": "Kickoff de proyecto", "updated_at": "2026-03-01T10:00:00Z"},
        {"id": "b", "title": "Granola BIM implementación", "updated_at": "2026-03-02T10:00:00Z"},
    ]

    selected = choose_document(docs, title_query="implementación")

    assert selected["id"] == "b"


def test_render_transcript_markdown_formats_turns():
    items = [
        {
            "source": "microphone",
            "text": "Hola, avancemos con el piloto.",
            "start_timestamp": "2026-03-06T18:01:16.878Z",
        },
        {
            "source": "system",
            "text": "Perfecto, revisemos los conectores.",
            "start_timestamp": "2026-03-06T18:01:21.848Z",
        },
    ]

    content = render_transcript_markdown(items)

    assert content.startswith("## Transcripción")
    assert "**David/host:** [18:01:16]" in content
    assert "**Interlocutor:** [18:01:21]" in content
    assert "Hola, avancemos con el piloto." in content
