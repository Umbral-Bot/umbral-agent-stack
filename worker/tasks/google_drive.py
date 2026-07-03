"""Tasks: Google Drive upload handlers (PIT-TG-DRIVE).

- google_drive.upload_file: upload a local file to the shared PIT Drive folder
  and return the shareable links (webViewLink / webContentLink).
- google_drive.upload_presentation: optional build step (delegates to
  document.create_presentation) + upload in one call.

Auth (OAuth refresh token, cuenta Rick — scope drive.file recomendado):
  GOOGLE_DRIVE_OAUTH_CLIENT_ID + GOOGLE_DRIVE_OAUTH_CLIENT_SECRET +
  GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN

Folder guard: uploads go ONLY to GOOGLE_DRIVE_PIT_FOLDER_ID (env). If the
caller passes a drive_folder_id it must match the configured folder — no
arbitrary destinations from task input.

Optional post-upload share: GOOGLE_DRIVE_SHARE_WITH (email David) gets a
reader permission, idempotently (no re-share, no notification email).

Secrets NEVER live in the repo — see
docs/ops/pit-telegram-drive-deliverables-runbook.md for setup.
"""

from __future__ import annotations

import importlib
import logging
import mimetypes
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger("worker.tasks.google_drive")

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

_UPLOAD_FIELDS = "id,name,size,parents,webViewLink,webContentLink"


# ---------------------------------------------------------------------------
# Auth + service (module-level indirections so tests can monkeypatch them)
# ---------------------------------------------------------------------------


def _get_drive_credentials() -> Any:
    """Build OAuth credentials from env (refresh-token flow, cuenta Rick).

    Raises ``ValueError`` with a setup hint when env or deps are missing.
    """
    client_id = os.environ.get("GOOGLE_DRIVE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        raise ValueError(
            "Google Drive auth not configured. Set GOOGLE_DRIVE_OAUTH_CLIENT_ID + "
            "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET + GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN. "
            "See docs/ops/pit-telegram-drive-deliverables-runbook.md."
        )
    try:
        credentials_mod = importlib.import_module("google.oauth2.credentials")
        credentials_cls = credentials_mod.Credentials
    except (ImportError, AttributeError) as exc:
        raise ValueError(
            "google-auth is required for Google Drive upload. "
            "Install with: pip install google-auth google-api-python-client"
        ) from exc
    return credentials_cls(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=DRIVE_SCOPES,
    )


def _build_drive_service(creds: Any) -> Any:
    """Return a Drive v3 service client (lazy import, mockable in tests)."""
    try:
        discovery = importlib.import_module("googleapiclient.discovery")
    except ImportError as exc:
        raise ValueError(
            "google-api-python-client is required for Google Drive upload. "
            "Install with: pip install google-api-python-client"
        ) from exc
    return discovery.build("drive", "v3", credentials=creds, cache_discovery=False)


def _media_file_upload(local_path: str, mime_type: str) -> Any:
    """Wrap ``MediaFileUpload`` (lazy import, mockable in tests)."""
    try:
        http_mod = importlib.import_module("googleapiclient.http")
    except ImportError as exc:
        raise ValueError(
            "google-api-python-client is required for Google Drive upload. "
            "Install with: pip install google-api-python-client"
        ) from exc
    return http_mod.MediaFileUpload(local_path, mimetype=mime_type, resumable=False)


# ---------------------------------------------------------------------------
# Folder guard + share
# ---------------------------------------------------------------------------


def _resolve_folder_id(requested: Optional[str]) -> str:
    """Resolve the destination folder, enforcing the PIT-folder-only guard."""
    configured = (os.environ.get("GOOGLE_DRIVE_PIT_FOLDER_ID") or "").strip()
    if not configured:
        raise ValueError(
            "GOOGLE_DRIVE_PIT_FOLDER_ID is not set — uploads are restricted to the "
            "shared PIT folder. See docs/ops/pit-telegram-drive-deliverables-runbook.md."
        )
    requested = (requested or "").strip()
    if requested and requested != configured:
        raise ValueError(
            "drive_folder_id does not match GOOGLE_DRIVE_PIT_FOLDER_ID — uploads are "
            "restricted to the configured shared PIT folder."
        )
    return configured


def _ensure_reader_permission(service: Any, file_id: str, email: str) -> Dict[str, Any]:
    """Grant ``email`` reader access to ``file_id`` idempotently."""
    email_lc = email.strip().lower()
    existing = (
        service.permissions()
        .list(fileId=file_id, fields="permissions(id,emailAddress,role,type)")
        .execute()
    )
    for perm in existing.get("permissions", []) or []:
        if (perm.get("emailAddress") or "").lower() == email_lc:
            logger.info("[google_drive] %s already has %s access — no re-share", email_lc, perm.get("role"))
            return {"shared": False, "already_had_access": True, "role": perm.get("role")}
    service.permissions().create(
        fileId=file_id,
        body={"type": "user", "role": "reader", "emailAddress": email},
        sendNotificationEmail=False,
    ).execute()
    logger.info("[google_drive] shared %s with %s (reader)", file_id, email_lc)
    return {"shared": True, "already_had_access": False, "role": "reader"}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_google_drive_upload_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Upload a local file to the shared PIT Google Drive folder.

    Input:
        local_path (str, required): path to the file on disk.
        drive_folder_id (str, optional): must match GOOGLE_DRIVE_PIT_FOLDER_ID;
            defaults to it.
        filename (str, optional): name in Drive; defaults to basename.
        mime_type (str, optional): defaults to a guess from the extension.

    Returns:
        ok, file_id, web_view_link, web_content_link, name, size_bytes, share
    """
    local_path = (input_data.get("local_path") or "").strip()
    if not local_path:
        return {"ok": False, "error": "'local_path' is required"}
    if not os.path.isfile(local_path):
        return {"ok": False, "error": f"local file not found: {local_path}"}

    folder_id = _resolve_folder_id(input_data.get("drive_folder_id"))
    filename = (input_data.get("filename") or "").strip() or os.path.basename(local_path)
    mime_type = (input_data.get("mime_type") or "").strip() or (
        mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )

    creds = _get_drive_credentials()
    service = _build_drive_service(creds)
    media = _media_file_upload(local_path, mime_type)

    logger.info("[google_drive.upload_file] uploading %s → folder %s", filename, folder_id)
    created = (
        service.files()
        .create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields=_UPLOAD_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )

    file_id = created.get("id", "")
    parents = created.get("parents") or []
    if parents and folder_id not in parents:
        # Defensa en profundidad: el archivo debe colgar de la carpeta PIT.
        raise ValueError(
            f"upload landed outside the PIT folder (parents={parents}) — aborting share"
        )

    share: Dict[str, Any] = {"shared": False, "already_had_access": False}
    share_with = (os.environ.get("GOOGLE_DRIVE_SHARE_WITH") or "").strip()
    if share_with and file_id:
        share = _ensure_reader_permission(service, file_id, share_with)

    try:
        size_bytes = int(created.get("size") or os.path.getsize(local_path))
    except (TypeError, ValueError):
        size_bytes = os.path.getsize(local_path)

    return {
        "ok": True,
        "file_id": file_id,
        "web_view_link": created.get("webViewLink", ""),
        "web_content_link": created.get("webContentLink", ""),
        "name": created.get("name", filename),
        "size_bytes": size_bytes,
        "folder_id": folder_id,
        "share": share,
    }


def handle_google_drive_upload_presentation(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build (optional) + upload a .pptx to the shared PIT folder.

    Input (one of):
        local_pptx_path (str): existing .pptx to upload as-is.
        slides (list[dict]): delegated to document.create_presentation
            ({'title','content',['notes']}); output_path optional (temp file
            by default).

    Plus the optional upload fields of google_drive.upload_file
    (drive_folder_id, filename, mime_type).
    """
    local_pptx_path = (input_data.get("local_pptx_path") or "").strip()
    slides = input_data.get("slides")
    if not local_pptx_path and not slides:
        return {"ok": False, "error": "provide 'local_pptx_path' or 'slides'"}

    build_result: Optional[Dict[str, Any]] = None
    if not local_pptx_path:
        from .document_generator import handle_document_create_presentation

        output_path = (input_data.get("output_path") or "").strip()
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".pptx", prefix="pit-deck-")
            os.close(fd)
        build_result = handle_document_create_presentation(
            {"slides": slides, "output_path": output_path}
        )
        if not build_result.get("ok"):
            return {"ok": False, "error": "presentation build failed", "build": build_result}
        local_pptx_path = output_path

    upload_input = {
        "local_path": local_pptx_path,
        "drive_folder_id": input_data.get("drive_folder_id"),
        "filename": input_data.get("filename"),
        "mime_type": input_data.get("mime_type") or DEFAULT_PPTX_MIME,
    }
    result = handle_google_drive_upload_file(upload_input)
    if build_result is not None:
        result["build"] = {
            "slide_count": build_result.get("slide_count"),
            "path": build_result.get("path"),
        }
    return result
