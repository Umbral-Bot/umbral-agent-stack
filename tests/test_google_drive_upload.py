"""Tests — worker google_drive.upload_file / upload_presentation (PIT-TG-DRIVE).

Sin red real: credenciales, service y MediaFileUpload se mockean a nivel de
módulo (indirecciones ``_get_drive_credentials`` / ``_build_drive_service`` /
``_media_file_upload``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from worker.tasks import TASK_HANDLERS
from worker.tasks import google_drive as gd

FOLDER = "folder-pit-123"


class _Call:
    def __init__(self, result: dict[str, Any]):
        self._result = result

    def execute(self) -> dict[str, Any]:
        return self._result


class FakeFiles:
    def __init__(self, response: dict[str, Any]):
        self.response = response
        self.create_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Call:
        self.create_calls.append(kwargs)
        return _Call(self.response)


class FakePermissions:
    def __init__(self, listing: dict[str, Any] | None = None):
        self.listing = listing or {"permissions": []}
        self.list_calls: list[dict[str, Any]] = []
        self.create_calls: list[dict[str, Any]] = []

    def list(self, **kwargs: Any) -> _Call:
        self.list_calls.append(kwargs)
        return _Call(self.listing)

    def create(self, **kwargs: Any) -> _Call:
        self.create_calls.append(kwargs)
        return _Call({"id": "perm-new"})


class FakeService:
    def __init__(self, files: FakeFiles, permissions: FakePermissions):
        self._files = files
        self._permissions = permissions

    def files(self) -> FakeFiles:
        return self._files

    def permissions(self) -> FakePermissions:
        return self._permissions


@pytest.fixture()
def drive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_PIT_FOLDER_ID", FOLDER)
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "refresh-token")
    monkeypatch.delenv("GOOGLE_DRIVE_SHARE_WITH", raising=False)


@pytest.fixture()
def local_file(tmp_path: Path) -> Path:
    path = tmp_path / "deck.pptx"
    path.write_bytes(b"fake-pptx-bytes")
    return path


def _wire_fake_service(
    monkeypatch: pytest.MonkeyPatch,
    response: dict[str, Any] | None = None,
    permissions: FakePermissions | None = None,
) -> tuple[FakeFiles, FakePermissions]:
    files = FakeFiles(
        response
        or {
            "id": "file-1",
            "name": "deck.pptx",
            "size": "1234",
            "parents": [FOLDER],
            "webViewLink": "https://drive.google.com/file/d/file-1/view",
            "webContentLink": "https://drive.google.com/uc?id=file-1",
        }
    )
    perms = permissions or FakePermissions()
    service = FakeService(files, perms)
    monkeypatch.setattr(gd, "_get_drive_credentials", lambda: object())
    monkeypatch.setattr(gd, "_build_drive_service", lambda creds: service)
    monkeypatch.setattr(gd, "_media_file_upload", lambda p, m: ("media", p, m))
    return files, perms


# ---------------------------------------------------------------------------
# upload_file — validación de input y guard de carpeta
# ---------------------------------------------------------------------------


def test_upload_file_requires_local_path() -> None:
    result = gd.handle_google_drive_upload_file({})
    assert result["ok"] is False
    assert "local_path" in result["error"]


def test_upload_file_missing_file(tmp_path: Path) -> None:
    result = gd.handle_google_drive_upload_file({"local_path": str(tmp_path / "nope.pptx")})
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_upload_file_requires_folder_env(
    monkeypatch: pytest.MonkeyPatch, local_file: Path
) -> None:
    monkeypatch.delenv("GOOGLE_DRIVE_PIT_FOLDER_ID", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_DRIVE_PIT_FOLDER_ID"):
        gd.handle_google_drive_upload_file({"local_path": str(local_file)})


def test_upload_file_folder_guard_mismatch(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    with pytest.raises(ValueError, match="restricted"):
        gd.handle_google_drive_upload_file(
            {"local_path": str(local_file), "drive_folder_id": "otra-carpeta"}
        )


def test_upload_file_requires_auth_env(
    monkeypatch: pytest.MonkeyPatch, local_file: Path
) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_PIT_FOLDER_ID", FOLDER)
    monkeypatch.delenv("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError, match="auth not configured"):
        gd.handle_google_drive_upload_file({"local_path": str(local_file)})


# ---------------------------------------------------------------------------
# upload_file — happy path + share
# ---------------------------------------------------------------------------


def test_upload_file_happy_path(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    files, perms = _wire_fake_service(monkeypatch)
    result = gd.handle_google_drive_upload_file({"local_path": str(local_file)})

    assert result["ok"] is True
    assert result["file_id"] == "file-1"
    assert result["web_view_link"].startswith("https://drive.google.com/")
    assert result["size_bytes"] == 1234
    assert result["folder_id"] == FOLDER

    assert len(files.create_calls) == 1
    call = files.create_calls[0]
    assert call["body"]["parents"] == [FOLDER]
    assert call["body"]["name"] == "deck.pptx"
    assert "webViewLink" in call["fields"]
    # Sin GOOGLE_DRIVE_SHARE_WITH no se toca permissions.
    assert perms.list_calls == []
    assert result["share"]["shared"] is False


def test_upload_file_share_creates_permission(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_SHARE_WITH", "david@example.com")
    _, perms = _wire_fake_service(monkeypatch)
    result = gd.handle_google_drive_upload_file({"local_path": str(local_file)})

    assert result["share"]["shared"] is True
    assert len(perms.create_calls) == 1
    body = perms.create_calls[0]["body"]
    assert body == {"type": "user", "role": "reader", "emailAddress": "david@example.com"}
    assert perms.create_calls[0]["sendNotificationEmail"] is False


def test_upload_file_share_idempotent(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_SHARE_WITH", "David@Example.com")
    perms = FakePermissions(
        {"permissions": [{"id": "p1", "emailAddress": "david@example.com", "role": "reader"}]}
    )
    _wire_fake_service(monkeypatch, permissions=perms)
    result = gd.handle_google_drive_upload_file({"local_path": str(local_file)})

    assert result["share"]["shared"] is False
    assert result["share"]["already_had_access"] is True
    assert perms.create_calls == []


def test_upload_file_aborts_if_parent_mismatch(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    _wire_fake_service(
        monkeypatch,
        response={
            "id": "file-x",
            "name": "deck.pptx",
            "parents": ["carpeta-ajena"],
            "webViewLink": "https://drive.google.com/x",
        },
    )
    with pytest.raises(ValueError, match="outside the PIT folder"):
        gd.handle_google_drive_upload_file({"local_path": str(local_file)})


# ---------------------------------------------------------------------------
# upload_presentation
# ---------------------------------------------------------------------------


def test_upload_presentation_requires_input() -> None:
    result = gd.handle_google_drive_upload_presentation({})
    assert result["ok"] is False


def test_upload_presentation_existing_pptx(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, local_file: Path
) -> None:
    _wire_fake_service(monkeypatch)
    result = gd.handle_google_drive_upload_presentation(
        {"local_pptx_path": str(local_file)}
    )
    assert result["ok"] is True
    assert result["file_id"] == "file-1"
    assert "build" not in result


def test_upload_presentation_from_slides(
    monkeypatch: pytest.MonkeyPatch, drive_env: None, tmp_path: Path
) -> None:
    pytest.importorskip("pptx")
    _wire_fake_service(monkeypatch)
    output = tmp_path / "built.pptx"
    result = gd.handle_google_drive_upload_presentation(
        {
            "slides": [
                {"title": "Torneo", "content": "Resumen"},
                {"title": "Winner", "content": "lane-a"},
            ],
            "output_path": str(output),
        }
    )
    assert result["ok"] is True
    assert result["build"]["slide_count"] == 2
    assert output.is_file()


# ---------------------------------------------------------------------------
# registro en TASK_HANDLERS
# ---------------------------------------------------------------------------


def test_registered_in_task_handlers() -> None:
    assert TASK_HANDLERS["google_drive.upload_file"] is gd.handle_google_drive_upload_file
    assert (
        TASK_HANDLERS["google_drive.upload_presentation"]
        is gd.handle_google_drive_upload_presentation
    )
