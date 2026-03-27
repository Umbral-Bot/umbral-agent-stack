import json
from pathlib import Path

from scripts.vm.granola_cache_exporter import (
    export_cache_once,
    render_prosemirror_markdown,
    render_panels_markdown,
    _split_action_items,
)
from scripts.vm.granola_watcher import parse_granola_markdown


def _write_cache(
    path: Path,
    *,
    documents: dict[str, dict],
    transcripts: dict[str, list[dict]] | None = None,
) -> None:
    payload = {
        "cache": {
            "state": {
                "documents": documents,
                "transcripts": transcripts or {},
            }
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_document(document_id: str, **overrides) -> dict:
    doc = {
        "id": document_id,
        "title": "Reunión de prueba",
        "type": "meeting",
        "valid_meeting": True,
        "created_at": "2026-03-24T13:43:00Z",
        "updated_at": "2026-03-24T14:10:00Z",
        "notes": {"type": "doc", "content": [{"type": "paragraph"}]},
        "notes_markdown": "",
        "notes_plain": "",
        "summary": None,
        "overview": None,
        "people": {
            "creator": {"name": "David Moreira"},
            "attendees": [{"name": "Ana Pérez"}],
        },
        "google_calendar_event": None,
    }
    doc.update(overrides)
    return doc


class _StubGranolaApiClient:
    def __init__(
        self,
        *,
        panels: dict[str, list[dict]] | None = None,
        transcripts: dict[str, list[dict]] | None = None,
    ) -> None:
        self.panels = panels or {}
        self.transcripts = transcripts or {}

    def fetch_panels(self, document_id: str, *, workspace_id: str = "") -> list[dict]:
        return self.panels.get(document_id, [])

    def fetch_transcript_segments(
        self, document_id: str, *, workspace_id: str = ""
    ) -> list[dict]:
        return self.transcripts.get(document_id, [])


def test_render_prosemirror_markdown_supports_headings_lists_and_action_items():
    notes = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Resumen"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Avance general."}],
            },
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Action Items"}],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Enviar propuesta"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Agendar seguimiento"}],
                            }
                        ],
                    },
                ],
            },
        ],
    }

    rendered = render_prosemirror_markdown(notes)
    cleaned_notes, action_items = _split_action_items(rendered)

    assert "### Resumen" in rendered
    assert "Avance general." in cleaned_notes
    assert action_items == [
        "- [ ] Enviar propuesta",
        "- [ ] Agendar seguimiento",
    ]


def test_render_panels_markdown_ignores_empty_and_duplicate_panels():
    panels = [
        {
            "title": "Summary",
            "content": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Hallazgo 1"}],
                    }
                ],
            },
        },
        {
            "title": "Summary",
            "content": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Hallazgo 1"}],
                    }
                ],
            },
        },
        {
            "title": "Summary",
            "content": {"type": "doc", "content": [{"type": "paragraph"}]},
        },
    ]

    rendered = render_panels_markdown(panels)

    assert rendered == "### Summary\n\nHallazgo 1"


def test_export_cache_once_renders_transcript_and_stays_watcher_compatible(tmp_path):
    document_id = "doc-123"
    cache_path = tmp_path / "cache-v6.json"
    export_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    transcripts = {
        document_id: [
            {
                "document_id": document_id,
                "start_timestamp": "2026-03-24T13:43:27.095Z",
                "text": "Hola equipo",
                "source": "microphone",
                "is_final": True,
            },
            {
                "document_id": document_id,
                "start_timestamp": "2026-03-24T13:43:28.095Z",
                "text": "revisemos avances",
                "source": "microphone",
                "is_final": True,
            },
            {
                "document_id": document_id,
                "start_timestamp": "2026-03-24T13:43:35.095Z",
                "text": "De acuerdo",
                "source": "system",
                "is_final": True,
            },
        ]
    }
    documents = {
        document_id: _base_document(document_id, title="Sesión con cliente"),
    }
    _write_cache(cache_path, documents=documents, transcripts=transcripts)

    summary = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )

    assert summary["exported_count"] == 1
    exported_file = next(export_dir.glob("*.md"))
    exported_text = exported_file.read_text(encoding="utf-8")

    assert "# Sesión con cliente" in exported_text
    assert "**Date:** 2026-03-24" in exported_text
    assert "**Attendees:** David Moreira, Ana Pérez" in exported_text
    assert "## Transcript" in exported_text
    assert "- **David Moreira:** [13:43:27] Hola equipo revisemos avances" in exported_text
    assert "- **Interlocutor:** [13:43:35] De acuerdo" in exported_text
    assert "## Metadata" in exported_text

    parsed = parse_granola_markdown(exported_text, exported_file.name)
    assert parsed["title"] == "Sesión con cliente"
    assert parsed["date"] == "2026-03-24"
    assert parsed["attendees"] == ["David Moreira", "Ana Pérez"]
    assert "Hola equipo revisemos avances" in parsed["content"]


def test_export_cache_once_skips_documents_without_usable_content(tmp_path):
    document_id = "doc-empty"
    cache_path = tmp_path / "cache-v6.json"
    export_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    documents = {
        document_id: _base_document(document_id, people={"creator": {"name": "David"}, "attendees": []}),
    }
    _write_cache(cache_path, documents=documents)

    summary = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )

    assert summary["exported_count"] == 0
    assert summary["skipped_unusable"] == 1
    assert summary["skipped_reason_counts"] == {"metadata_only": 1}
    assert not list(export_dir.glob("*.md"))


def test_export_cache_once_uses_manifest_to_skip_unchanged_documents(tmp_path):
    document_id = "doc-stable"
    cache_path = tmp_path / "cache-v6.json"
    export_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    documents = {
        document_id: _base_document(
            document_id,
            notes_markdown="## Summary\n\nMaterial estable.",
        )
    }
    _write_cache(cache_path, documents=documents)

    first = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )
    assert first["exported_count"] == 1

    exported_file = next(export_dir.glob("*.md"))
    processed_dir.mkdir(parents=True, exist_ok=True)
    exported_file.rename(processed_dir / exported_file.name)

    second = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )

    assert second["exported_count"] == 0
    assert second["skipped_unchanged"] == 1


def test_export_cache_once_reexports_when_signature_changes(tmp_path):
    document_id = "doc-changing"
    cache_path = tmp_path / "cache-v6.json"
    export_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    documents = {
        document_id: _base_document(
            document_id,
            notes_markdown="## Summary\n\nVersión uno.",
        )
    }
    _write_cache(cache_path, documents=documents)

    first = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )
    assert first["exported_count"] == 1

    documents[document_id]["notes_markdown"] = "## Summary\n\nVersión dos."
    documents[document_id]["updated_at"] = "2026-03-24T14:20:00Z"
    _write_cache(cache_path, documents=documents)

    second = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        enable_private_api_hydration=False,
    )

    assert second["exported_count"] == 1
    exported_text = next(export_dir.glob("*.md")).read_text(encoding="utf-8")
    assert "Versión dos." in exported_text


def test_export_cache_once_hydrates_panels_and_transcript_via_private_api(tmp_path):
    document_id = "doc-api"
    cache_path = tmp_path / "cache-v6.json"
    export_dir = tmp_path / "exports"
    processed_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    documents = {
        document_id: _base_document(
            document_id,
            title="Reunión API",
            workspace_id="ws-123",
        )
    }
    _write_cache(cache_path, documents=documents)

    api_client = _StubGranolaApiClient(
        panels={
            document_id: [
                {
                    "title": "Summary",
                    "content": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Acuerdo principal"}
                                ],
                            }
                        ],
                    },
                }
            ]
        },
        transcripts={
            document_id: [
                {
                    "document_id": document_id,
                    "start_timestamp": "2026-03-24T13:43:27.095Z",
                    "text": "Hola equipo",
                    "source": "microphone",
                    "is_final": True,
                }
            ]
        },
    )

    summary = export_cache_once(
        cache_path=cache_path,
        export_dir=export_dir,
        processed_dir=processed_dir,
        manifest_path=manifest_path,
        api_client=api_client,
        enable_private_api_hydration=True,
    )

    assert summary["exported_count"] == 1
    assert summary["exports"][0]["notes_source"] == "private_api_panels"
    assert summary["exports"][0]["transcript_source"] == "private_api_transcript"

    exported_text = next(export_dir.glob("*.md")).read_text(encoding="utf-8")
    assert "### Summary" in exported_text
    assert "Acuerdo principal" in exported_text
    assert "- **David Moreira:** [13:43:27] Hola equipo" in exported_text
