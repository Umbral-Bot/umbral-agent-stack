"""Focused tests for the durable Drive visual-selection sync."""

from __future__ import annotations

import sys
from unittest.mock import patch

from scripts.editorial import sync_visual_asset_from_selection as sync


DRIVE_ALT = "https://drive.google.com/file/d/durable-file/view"
MAGNIFIC_LOCATOR = "https://app.magnific.com/example-only"
EPHEMERAL_CDN = "https://cdn.example.test/image.png"


def _select(name: str):
    return {"type": "select", "select": {"name": name}}


def _url(value: str | None):
    return {"type": "url", "url": value}


def _checkbox(value: bool):
    return {"type": "checkbox", "checkbox": value}


def _page(*, alt_url: str, state: str, visual_url: str | None = None):
    return {
        "properties": {
            "Selección imagen": _select("Alt 2"),
            "Estado imagen": _select(state),
            "Visual asset URL": _url(visual_url),
            "imagen_alt_2_url": _url(alt_url),
            "imagen_alt_2_magnific_url": _url(MAGNIFIC_LOCATOR),
            "imagen_cantidad": {"type": "number", "number": 5},
            "aprobado_contenido": _checkbox(True),
            "autorizar_publicacion": _checkbox(False),
        }
    }


def test_valid_https_accepts_only_drive_web_view_links():
    assert sync._valid_https(DRIVE_ALT) is True
    assert sync._valid_https(EPHEMERAL_CDN) is False
    assert sync._valid_https("https://APP.MAGNIFIC.COM/creation/example") is False
    assert sync._valid_https("http://drive.google.com/file/d/example/view") is False
    assert sync._valid_https("https://drive.google.com.evil.test/file/view") is False
    assert sync._valid_https("https://drive.google.com/") is False
    assert sync._valid_https("https://user@drive.google.com/file/view") is False
    assert sync._valid_https("https://drive.google.com:444/file/view") is False


def test_selected_alt_copies_durable_drive_url_and_ignores_magnific_locator(
    monkeypatch, capsys
):
    before = _page(alt_url=DRIVE_ALT, state="Listo para selección")
    after = _page(alt_url=DRIVE_ALT, state="Seleccionada", visual_url=DRIVE_ALT)
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    pages = iter([before, after])
    monkeypatch.setattr(sync, "_get_page", lambda *_args: next(pages))
    captured_patch = {}

    def _capture_patch(_api_key, _page_id, properties):
        captured_patch.update(properties)
        return {}

    monkeypatch.setattr(sync, "_patch_page", _capture_patch)
    with patch.object(sys, "argv", ["sync_visual_asset_from_selection.py"]):
        assert sync.main() == 0

    assert captured_patch["Visual asset URL"] == {"url": DRIVE_ALT}
    assert captured_patch["Estado imagen"] == {"select": {"name": "Seleccionada"}}
    assert MAGNIFIC_LOCATOR not in repr(captured_patch)
    output = capsys.readouterr().out
    assert "durable-file" not in output
    assert "example-only" not in output
    assert "https://" not in output


def test_ephemeral_cdn_alt_is_blocked_without_patch(monkeypatch, capsys):
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    monkeypatch.setattr(
        sync,
        "_get_page",
        lambda *_args: _page(
            alt_url=EPHEMERAL_CDN,
            state="Listo para selección",
        ),
    )
    with patch.object(sync, "_patch_page") as patch_page, patch.object(
        sys, "argv", ["sync_visual_asset_from_selection.py"]
    ):
        assert sync.main() == 4
    patch_page.assert_not_called()
    captured = capsys.readouterr()
    assert "image.png" not in captured.out
    assert "image.png" not in captured.err
    assert "https://" not in captured.out
    assert "https://" not in captured.err


def test_dry_run_reports_action_without_url_or_page_id(monkeypatch, capsys):
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    monkeypatch.setattr(
        sync,
        "_get_page",
        lambda *_args: _page(alt_url=DRIVE_ALT, state="Listo para selección"),
    )
    sensitive_page_id = "sensitive-page-id-example"

    with patch.object(sync, "_patch_page") as patch_page, patch.object(
        sys,
        "argv",
        [
            "sync_visual_asset_from_selection.py",
            "--page-id",
            sensitive_page_id,
            "--dry-run",
        ],
    ):
        assert sync.main() == 0

    patch_page.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY_RUN alt=2" in captured.out
    assert "https://" not in captured.out
    assert "durable-file" not in captured.out
    assert sensitive_page_id not in captured.out


def test_report_only_outputs_redacted_useful_summary(monkeypatch, capsys):
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    monkeypatch.setattr(
        sync,
        "_get_page",
        lambda *_args: _page(alt_url=DRIVE_ALT, state="Listo para selección"),
    )

    with patch.object(
        sys,
        "argv",
        ["sync_visual_asset_from_selection.py", "--report-only"],
    ):
        assert sync.main() == 0

    output = capsys.readouterr().out
    assert '"selection_alt": 2' in output
    assert '"imagen_cantidad": 5' in output
    assert '"available_drive_alts"' in output
    assert "durable-file" not in output
    assert "example-only" not in output
    assert "https://" not in output


def test_sync_rejects_a_different_drive_asset_after_patch(monkeypatch, capsys):
    before = _page(alt_url=DRIVE_ALT, state="Listo para selección")
    after = _page(
        alt_url=DRIVE_ALT,
        state="Seleccionada",
        visual_url="https://drive.google.com/file/d/different-file/view",
    )
    pages = iter([before, after])
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    monkeypatch.setattr(sync, "_get_page", lambda *_args: next(pages))
    monkeypatch.setattr(sync, "_patch_page", lambda *_args: {})

    with patch.object(sys, "argv", ["sync_visual_asset_from_selection.py"]):
        assert sync.main() == 6

    captured = capsys.readouterr()
    assert "different-file" not in captured.out
    assert "different-file" not in captured.err
    assert "https://" not in captured.out
    assert "https://" not in captured.err


def test_notion_error_does_not_echo_page_id_or_url(monkeypatch, capsys):
    sensitive_page_id = "sensitive-page-id-example"
    monkeypatch.setenv("NOTION_API_KEY", "not-a-real-key")
    monkeypatch.setattr(
        sync,
        "_get_page",
        lambda *_args: (_ for _ in ()).throw(
            RuntimeError(f"failed https://api.notion.com/pages/{sensitive_page_id}")
        ),
    )

    with patch.object(
        sys,
        "argv",
        ["sync_visual_asset_from_selection.py", "--page-id", sensitive_page_id],
    ):
        assert sync.main() == 6

    captured = capsys.readouterr()
    assert sensitive_page_id not in captured.out
    assert sensitive_page_id not in captured.err
    assert "https://" not in captured.out
    assert "https://" not in captured.err
