"""Tests for scripts/editorial/apply_publication_copy.py V2 (P2.3).

Covers: Copy LinkedIn empresa property, the rich_text overflow guard, and the
two documented escape hatches for the Copy Blog property limit (page-body
blocks + explicit Worker payload). Gates must stay untouched in every path;
no test performs a real Notion network call (dry-run / pure functions only).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.editorial import apply_publication_copy as apc

_REPO = Path(__file__).resolve().parent.parent
_CAND001 = _REPO / "evals" / "editorial" / "cand-001-final-copy.yaml"


def _load_cand001() -> dict:
    return yaml.safe_load(_CAND001.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# _chunks overflow guard
# ---------------------------------------------------------------------------


def test_chunks_no_guard_never_raises():
    chunks = apc._chunks("x" * 5000, size=10)
    assert len(chunks) == 500  # would overflow the 100-item property limit


def test_chunks_guard_raises_when_over_property_limit():
    with pytest.raises(apc.RichTextOverflowError, match="rich_text chunks"):
        apc._chunks("x" * 5000, size=10, guard_property_limit=True)


def test_chunks_guard_passes_within_property_limit():
    chunks = apc._chunks("x" * 500, size=10, guard_property_limit=True)
    assert len(chunks) == 50


def test_build_properties_cand001_does_not_overflow():
    payload = _load_cand001()
    props = apc.build_properties(payload)
    assert "Copy Blog" in props
    assert "Copy LinkedIn" in props
    assert "Copy X" in props


def test_build_properties_raises_on_oversized_blog():
    payload = _load_cand001()
    payload = dict(payload, copy_blog="x" * 300_000)
    with pytest.raises(apc.RichTextOverflowError):
        apc.build_properties(payload)


def test_build_properties_skip_oversized_omits_copy_blog_instead_of_raising():
    # The whole point of --write-body / --emit-worker-payload is to still
    # succeed when Copy Blog overflows the property limit — this must not
    # raise, and must simply leave "Copy Blog" out of the property patch
    # (the full body is delivered via the escape hatch instead).
    payload = dict(_load_cand001(), copy_blog="x" * 300_000)
    props = apc.build_properties(payload, skip_oversized_copy_blog=True)
    assert "Copy Blog" not in props
    assert "Copy LinkedIn" in props
    assert "Copy X" in props


def test_build_properties_skip_oversized_keeps_copy_blog_when_it_fits():
    payload = _load_cand001()
    props = apc.build_properties(payload, skip_oversized_copy_blog=True)
    assert "Copy Blog" in props


# ---------------------------------------------------------------------------
# Copy LinkedIn empresa (P2.3)
# ---------------------------------------------------------------------------


def test_build_properties_omits_linkedin_empresa_when_absent():
    payload = _load_cand001()
    assert "copy_linkedin_empresa" not in payload
    props = apc.build_properties(payload)
    assert "Copy LinkedIn empresa" not in props


def test_build_properties_includes_linkedin_empresa_when_present():
    payload = dict(_load_cand001(), copy_linkedin_empresa="Texto sugerido para compartir el post de la empresa.")
    props = apc.build_properties(payload)
    assert "Copy LinkedIn empresa" in props
    text = props["Copy LinkedIn empresa"]["rich_text"][0]["text"]["content"]
    assert text == "Texto sugerido para compartir el post de la empresa."


# ---------------------------------------------------------------------------
# Escape hatch #1 — page body blocks
# ---------------------------------------------------------------------------


def test_build_copy_blog_body_blocks_structure():
    text = "Primer párrafo.\n\nSegundo párrafo.\n\nTercer párrafo."
    marker = "Copy Blog (V2 canonical body) — trace_id: TEST-1"
    blocks = apc.build_copy_blog_body_blocks(text, marker)

    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["rich_text"][0]["text"]["content"] == marker
    assert blocks[1]["type"] == "divider"

    paragraph_blocks = blocks[2:]
    assert len(paragraph_blocks) == 3
    assert all(b["type"] == "paragraph" for b in paragraph_blocks)
    assert paragraph_blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Primer párrafo."
    assert paragraph_blocks[2]["paragraph"]["rich_text"][0]["text"]["content"] == "Tercer párrafo."


def test_build_copy_blog_body_blocks_never_overflows_property_limit():
    # A body long enough to overflow the Copy Blog *property* must still
    # convert cleanly to blocks (no guard_property_limit applied per-block).
    text = "\n\n".join(f"Párrafo {i}." for i in range(500))
    marker = "Copy Blog (V2 canonical body) — trace_id: TEST-2"
    blocks = apc.build_copy_blog_body_blocks(text, marker)
    assert len(blocks) == 2 + 500


def test_body_marker_present_detects_callout():
    marker = "Copy Blog (V2 canonical body) — trace_id: TEST-3"
    children = [
        {
            "type": "callout",
            "callout": {"rich_text": [{"plain_text": marker}]},
        },
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "otro texto"}]}},
    ]
    assert apc.body_marker_present(children, marker) is True


def test_body_marker_absent_when_not_present():
    children = [{"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "sin marcador"}]}}]
    assert apc.body_marker_present(children, "Copy Blog (V2 canonical body) — trace_id: TEST-4") is False


# ---------------------------------------------------------------------------
# Escape hatch #2 — explicit Worker payload
# ---------------------------------------------------------------------------


def test_build_worker_copy_payload_keeps_gates_false():
    payload = _load_cand001()
    result = apc.build_worker_copy_payload(payload, "some-page-id")
    assert result["autorizar_publicacion"] is False
    assert result["aprobado_contenido"] is False
    assert result["notion_page_id"] == "some-page-id"
    assert result["body_markdown"] == payload["copy_blog"].strip()
    assert result["trace_id"] == payload["trace_id"]


def test_build_worker_copy_payload_defaults_missing_metadata_to_empty():
    payload = _load_cand001()
    result = apc.build_worker_copy_payload(payload, "page-id")
    assert result["slug"] == ""
    assert result["title"] == ""
    assert result["excerpt"] == ""


# ---------------------------------------------------------------------------
# main() — dry-run end to end (no network)
# ---------------------------------------------------------------------------


def test_main_dry_run_cand001(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "sys.argv",
        ["apply_publication_copy.py", "--publication-id", "CAND-001", "--dry-run", "--skip-model-verify"],
    )
    exit_code = apc.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "VALIDATION_OK" in out
    assert "DRY_RUN" in out
    assert "gates=unchanged" in out


def test_main_dry_run_write_body_reports_block_count(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "apply_publication_copy.py",
            "--publication-id", "CAND-001",
            "--dry-run",
            "--skip-model-verify",
            "--write-body",
        ],
    )
    exit_code = apc.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "DRY_RUN write_body blocks=" in out
    assert "no Notion call" in out


def test_main_dry_run_emits_worker_payload(monkeypatch, capsys, tmp_path):
    out_path = tmp_path / "cand-001-worker-payload.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "apply_publication_copy.py",
            "--publication-id", "CAND-001",
            "--dry-run",
            "--skip-model-verify",
            "--emit-worker-payload", str(out_path),
        ],
    )
    exit_code = apc.main()
    assert exit_code == 0
    assert out_path.is_file()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["autorizar_publicacion"] is False
    assert data["aprobado_contenido"] is False
    assert data["body_markdown"]
    out = capsys.readouterr().out
    assert "WORKER_PAYLOAD_WRITTEN" in out


def _write_oversized_copy_yaml(tmp_path) -> Path:
    # Keeps the closing contract (hyperlinked source + slogan alone, 2026-09-02)
    # so this exercises the rich_text overflow path and nothing else.
    base = _load_cand001()
    body = "x " * 200_000 + (
        "\n\nFuente: [buildingSMART, IDS](https://example.org/ids)"
        "\n\nPrimero claridad. Después velocidad."
    )
    oversized = dict(base, copy_blog=body)
    copy_dir = tmp_path
    (copy_dir / "cand-oversize-final-copy.yaml").write_text(
        yaml.safe_dump(oversized, allow_unicode=True), encoding="utf-8"
    )
    return copy_dir


def test_main_dry_run_rejects_oversized_blog_without_escape_hatch(monkeypatch, capsys, tmp_path):
    copy_dir = _write_oversized_copy_yaml(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "apply_publication_copy.py",
            "--publication-id", "CAND-OVERSIZE",
            "--copy-dir", str(copy_dir),
            "--dry-run",
            "--skip-model-verify",
        ],
    )
    exit_code = apc.main()
    assert exit_code == 5
    err = capsys.readouterr().err
    assert "rich_text chunks" in err


def test_main_dry_run_oversized_blog_succeeds_with_write_body(monkeypatch, capsys, tmp_path):
    # Regression: build_properties() used to run its property-limit guard
    # unconditionally before main() ever looked at --write-body, so an
    # oversized body always failed with exit 5 even with the escape hatch
    # requested — defeating the whole point of --write-body. This must now
    # succeed: the oversized Copy Blog property is skipped, not raised.
    copy_dir = _write_oversized_copy_yaml(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "apply_publication_copy.py",
            "--publication-id", "CAND-OVERSIZE",
            "--copy-dir", str(copy_dir),
            "--dry-run",
            "--skip-model-verify",
            "--write-body",
        ],
    )
    exit_code = apc.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "NOTE: Copy Blog property skipped" in out
    assert "DRY_RUN write_body blocks=" in out


def test_main_dry_run_oversized_blog_succeeds_with_emit_worker_payload(monkeypatch, capsys, tmp_path):
    copy_dir = _write_oversized_copy_yaml(tmp_path)
    out_path = tmp_path / "worker-payload.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "apply_publication_copy.py",
            "--publication-id", "CAND-OVERSIZE",
            "--copy-dir", str(copy_dir),
            "--dry-run",
            "--skip-model-verify",
            "--emit-worker-payload", str(out_path),
        ],
    )
    exit_code = apc.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "NOTE: Copy Blog property skipped" in out
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(data["body_markdown"]) > 190_000  # full, untruncated body
