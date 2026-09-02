"""Tasks and helpers for guarded Google Drive uploads.

- google_drive.upload_file: upload a local file to the shared PIT Drive folder
  and return the shareable links (webViewLink / webContentLink).
- google_drive.upload_presentation: optional build step (delegates to
  document.create_presentation) + upload in one call.
- Editorial HITL helpers: preflight the separately allowlisted editorial root,
  create a ``publication_id/YYYYMMDD-HHmm`` hierarchy, and persist five PNGs.

Auth (OAuth refresh token, cuenta Rick — scope drive.file recomendado):
  GOOGLE_DRIVE_OAUTH_CLIENT_ID + GOOGLE_DRIVE_OAUTH_CLIENT_SECRET +
  GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN

Folder guard: every destination has its own configured root. Public PIT tasks
always use ``GOOGLE_DRIVE_PIT_FOLDER_ID``; editorial helpers always use
``GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID``. A caller cannot cross those roots,
and editorial uploads only use child IDs created or resolved by this module.

Optional post-upload share: GOOGLE_DRIVE_SHARE_WITH (email David) gets a
reader permission, idempotently (no re-share, no notification email).

Secrets NEVER live in the repo — see
docs/ops/pit-telegram-drive-deliverables-runbook.md for setup.
"""

from __future__ import annotations

import importlib
import io
import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Sequence
from urllib.parse import urlparse

logger = logging.getLogger("worker.tasks.google_drive")

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
PNG_MIME = "image/png"

_UPLOAD_FIELDS = "id,name,size,parents,webViewLink,webContentLink"
_FOLDER_FIELDS = "id,name,mimeType,parents,webViewLink,trashed"
_DRIVE_DESTINATION_ENVS = {
    "pit": "GOOGLE_DRIVE_PIT_FOLDER_ID",
    "editorial_hitl": "GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID",
}
_DRIVE_OAUTH_ENVS = (
    "GOOGLE_DRIVE_OAUTH_CLIENT_ID",
    "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET",
    "GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN",
)
_PUBLICATION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_RUN_STAMP_RE = re.compile(r"\d{8}-\d{4}")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True, repr=False)
class EditorialHitlDriveContext:
    """Prepared Drive service and its verified editorial root.

    ``repr=False`` deliberately keeps the allowlisted folder ID out of routine
    diagnostics. Instances are created only by :func:`prepare_editorial_hitl_drive`.
    """

    service: Any
    root_folder_id: str


# ---------------------------------------------------------------------------
# Auth + service (module-level indirections so tests can monkeypatch them)
# ---------------------------------------------------------------------------


def _get_drive_credentials() -> Any:
    """Build OAuth credentials from env (refresh-token flow, cuenta Rick).

    Raises ``ValueError`` with a setup hint when env or deps are missing.
    """
    client_id = (os.environ.get("GOOGLE_DRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    refresh_token = (os.environ.get("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN") or "").strip()
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


def _media_bytes_upload(data: bytes, mime_type: str) -> Any:
    """Wrap ``MediaIoBaseUpload`` for an in-memory binary payload."""
    try:
        http_mod = importlib.import_module("googleapiclient.http")
    except ImportError as exc:
        raise ValueError(
            "google-api-python-client is required for Google Drive upload. "
            "Install with: pip install google-api-python-client"
        ) from exc
    return http_mod.MediaIoBaseUpload(
        io.BytesIO(data), mimetype=mime_type, resumable=False
    )


# ---------------------------------------------------------------------------
# Folder guard + share
# ---------------------------------------------------------------------------


def _resolve_folder_id(
    requested: Optional[str], *, destination: str = "pit"
) -> str:
    """Resolve one configured root without allowing cross-destination writes.

    The default remains ``pit`` for backward compatibility with the public
    ``google_drive.upload_*`` task handlers. Editorial callers must opt into
    the separate, fixed ``editorial_hitl`` destination.
    """
    env_name = _DRIVE_DESTINATION_ENVS.get(destination)
    if env_name is None:
        raise ValueError("unknown Google Drive destination")
    configured = (os.environ.get(env_name) or "").strip()
    if not configured:
        if destination == "pit":
            raise ValueError(
                "GOOGLE_DRIVE_PIT_FOLDER_ID is not set - uploads are restricted "
                "to the shared PIT folder. See "
                "docs/ops/pit-telegram-drive-deliverables-runbook.md."
            )
        raise ValueError(
            f"{env_name} is not set - uploads are restricted to its configured root."
        )
    requested = str(requested or "").strip()
    if destination == "editorial_hitl":
        pit_root = (os.environ.get("GOOGLE_DRIVE_PIT_FOLDER_ID") or "").strip()
        if pit_root and configured == pit_root:
            raise ValueError(
                "Editorial HITL Drive root must differ from GOOGLE_DRIVE_PIT_FOLDER_ID"
            )
    if requested and requested != configured:
        if destination == "pit":
            raise ValueError(
                "drive_folder_id does not match GOOGLE_DRIVE_PIT_FOLDER_ID - uploads "
                "are restricted to the configured shared PIT folder."
            )
        raise ValueError(
            f"drive_folder_id does not match {env_name} - uploads are restricted "
            "to the configured destination root."
        )
    return configured


def editorial_hitl_drive_readiness(publication_id: str) -> Dict[str, Any]:
    """Return a dry-run-safe readiness summary without contacting Drive.

    Only variable *names* are returned when configuration is incomplete. No
    OAuth values or folder IDs are exposed.
    """
    clean_publication_id = str(publication_id or "").strip()
    missing = [
        name
        for name in (
            "GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID",
            *_DRIVE_OAUTH_ENVS,
        )
        if not (os.environ.get(name) or "").strip()
    ]
    editorial_root = (
        os.environ.get("GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID") or ""
    ).strip()
    pit_root = (os.environ.get("GOOGLE_DRIVE_PIT_FOLDER_ID") or "").strip()
    roots_are_distinct = not pit_root or editorial_root != pit_root
    return {
        "ready": (
            not missing
            and roots_are_distinct
            and bool(_PUBLICATION_ID_RE.fullmatch(clean_publication_id))
        ),
        "missing": missing,
        "configuration_error": (
            None if roots_are_distinct else "editorial_root_reuses_pit_root"
        ),
        "logical_path": f"{clean_publication_id or '<publication_id>'}/YYYYMMDD-HHmm",
    }


def _validate_drive_item(
    item: Any,
    *,
    expected_parent_id: str,
    expected_name: str,
    expected_mime_type: Optional[str] = None,
    require_web_view_link: bool = True,
) -> Dict[str, Any]:
    """Validate Drive metadata without echoing IDs or links in errors."""
    if not isinstance(item, dict):
        raise ValueError("Google Drive returned invalid item metadata")
    item_id = str(item.get("id") or "").strip()
    parents = item.get("parents")
    if not item_id:
        raise ValueError("Google Drive item metadata is missing an id")
    if not isinstance(parents, list) or parents != [expected_parent_id]:
        raise ValueError("Google Drive item landed outside its guarded parent")
    if str(item.get("name") or "") != expected_name:
        raise ValueError("Google Drive item name does not match the requested name")
    if expected_mime_type and item.get("mimeType") != expected_mime_type:
        raise ValueError("Google Drive item has an unexpected mime type")
    if item.get("trashed") is True:
        raise ValueError("Google Drive item is trashed")
    if require_web_view_link:
        _validate_web_view_link(item.get("webViewLink"))
    return item


def _validate_web_view_link(value: Any) -> str:
    """Require the HTTPS browser-view link returned by Drive itself."""
    link = str(value or "").strip()
    parsed = urlparse(link)
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() != "drive.google.com":
        raise ValueError("Google Drive item is missing a valid webViewLink")
    return link


def _escape_drive_query_literal(value: str) -> str:
    """Escape a value embedded in a Drive v3 ``q`` string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _find_or_create_child_folder(
    service: Any, *, parent_id: str, name: str
) -> Dict[str, Any]:
    """Resolve one app-visible child folder or create it under ``parent_id``."""
    escaped_parent = _escape_drive_query_literal(parent_id)
    escaped_name = _escape_drive_query_literal(name)
    try:
        found = (
            service.files()
            .list(
                q=(
                    f"'{escaped_parent}' in parents and name = '{escaped_name}' "
                    f"and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false"
                ),
                spaces="drive",
                fields=f"files({_FOLDER_FIELDS})",
                pageSize=2,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        raise ValueError("Editorial HITL Drive folder lookup failed") from exc

    if not isinstance(found, dict):
        raise ValueError("Google Drive returned invalid folder lookup metadata")
    matches = found.get("files", [])
    if not isinstance(matches, list):
        raise ValueError("Google Drive returned invalid folder lookup metadata")
    if len(matches) > 1:
        raise ValueError("Editorial HITL Drive folder path is ambiguous")
    if matches:
        return _validate_drive_item(
            matches[0],
            expected_parent_id=parent_id,
            expected_name=name,
            expected_mime_type=DRIVE_FOLDER_MIME,
        )

    try:
        created = (
            service.files()
            .create(
                body={
                    "name": name,
                    "mimeType": DRIVE_FOLDER_MIME,
                    "parents": [parent_id],
                },
                fields=_FOLDER_FIELDS,
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        raise ValueError("Editorial HITL Drive folder creation failed") from exc
    return _validate_drive_item(
        created,
        expected_parent_id=parent_id,
        expected_name=name,
        expected_mime_type=DRIVE_FOLDER_MIME,
    )


def prepare_editorial_hitl_drive() -> EditorialHitlDriveContext:
    """Build credentials/service and probe the allowlisted root read-only.

    Call this before spending Magnific credits. The probe refreshes OAuth as
    needed and proves the configured item exists and is a non-trashed folder;
    it does not create, share, or modify anything.
    """
    root_folder_id = _resolve_folder_id(None, destination="editorial_hitl")
    creds = _get_drive_credentials()
    service = _build_drive_service(creds)
    try:
        root = (
            service.files()
            .get(
                fileId=root_folder_id,
                fields="id,mimeType,trashed,capabilities(canAddChildren)",
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        raise ValueError("Editorial HITL Drive root preflight failed") from exc
    if not isinstance(root, dict) or str(root.get("id") or "").strip() != root_folder_id:
        raise ValueError("Editorial HITL Drive root preflight returned unexpected metadata")
    if root.get("mimeType") != DRIVE_FOLDER_MIME or root.get("trashed") is True:
        raise ValueError("Editorial HITL Drive root is not an active folder")
    capabilities = root.get("capabilities")
    if not isinstance(capabilities, dict) or capabilities.get("canAddChildren") is not True:
        raise ValueError("Editorial HITL Drive root does not allow creating child folders")
    return EditorialHitlDriveContext(service=service, root_folder_id=root_folder_id)


def _validate_editorial_path(publication_id: str, run_stamp: str) -> tuple[str, str]:
    clean_publication_id = str(publication_id or "").strip()
    clean_run_stamp = str(run_stamp or "").strip()
    if not _PUBLICATION_ID_RE.fullmatch(clean_publication_id):
        raise ValueError("publication_id is not safe for an editorial Drive folder")
    if not _RUN_STAMP_RE.fullmatch(clean_run_stamp):
        raise ValueError("run_stamp must use YYYYMMDD-HHmm")
    try:
        datetime.strptime(clean_run_stamp, "%Y%m%d-%H%M")
    except ValueError as exc:
        raise ValueError("run_stamp must be a valid YYYYMMDD-HHmm timestamp") from exc
    return clean_publication_id, clean_run_stamp


def persist_editorial_hitl_images(
    context: EditorialHitlDriveContext,
    *,
    publication_id: str,
    run_stamp: str,
    png_images: Sequence[bytes],
) -> Dict[str, Any]:
    """Persist exactly five PNG variants under the guarded editorial root.

    The returned links are Drive-provided ``webViewLink`` values. Permissions
    are inherited from the editorial root; this helper never creates direct
    file or folder permissions.
    """
    if not isinstance(context, EditorialHitlDriveContext):
        raise ValueError("editorial Drive context must come from preflight")
    _resolve_folder_id(context.root_folder_id, destination="editorial_hitl")
    clean_publication_id, clean_run_stamp = _validate_editorial_path(
        publication_id, run_stamp
    )
    if isinstance(png_images, (str, bytes, bytearray)):
        images: list[Any] = []
    else:
        try:
            images = list(png_images)
        except TypeError as exc:
            raise ValueError("editorial HITL image batch must be iterable") from exc
    if len(images) != 5:
        raise ValueError("editorial HITL persistence requires exactly 5 PNG images")

    normalized_images: list[bytes] = []
    for image in images:
        try:
            data = bytes(image)
        except (TypeError, ValueError) as exc:
            raise ValueError("editorial HITL image payload must be bytes") from exc
        if not data.startswith(_PNG_SIGNATURE):
            raise ValueError("editorial HITL image payload is not a PNG")
        normalized_images.append(data)

    publication_folder = _find_or_create_child_folder(
        context.service,
        parent_id=context.root_folder_id,
        name=clean_publication_id,
    )
    run_folder = _find_or_create_child_folder(
        context.service,
        parent_id=publication_folder["id"],
        name=clean_run_stamp,
    )
    run_folder_id = run_folder["id"]

    persisted: list[Dict[str, Any]] = []
    seen_file_ids: set[str] = set()
    for index, data in enumerate(normalized_images, start=1):
        filename = f"alt-{index}.png"
        media = _media_bytes_upload(data, PNG_MIME)
        try:
            created = (
                context.service.files()
                .create(
                    body={"name": filename, "parents": [run_folder_id]},
                    media_body=media,
                    fields=_UPLOAD_FIELDS,
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            raise ValueError(f"Editorial HITL Drive upload failed for alt-{index}") from exc
        created = _validate_drive_item(
            created,
            expected_parent_id=run_folder_id,
            expected_name=filename,
        )
        file_id = created["id"]
        if file_id in seen_file_ids:
            raise ValueError("Google Drive returned duplicate file metadata")
        seen_file_ids.add(file_id)
        persisted.append(
            {
                "name": filename,
                "web_view_link": _validate_web_view_link(created.get("webViewLink")),
                "web_content_link": str(created.get("webContentLink") or "").strip(),
                "size_bytes": len(data),
            }
        )

    logger.info("[google_drive.editorial_hitl] persisted 5 PNG variants")
    return {
        "ok": True,
        "logical_path": f"{clean_publication_id}/{clean_run_stamp}",
        "folder_web_view_link": _validate_web_view_link(run_folder.get("webViewLink")),
        "files": persisted,
    }


# ---------------------------------------------------------------------------
# Download (editorial hero) — the mirror of persist_editorial_hitl_images
# ---------------------------------------------------------------------------

# The HITL-2 winner lives in Drive as ``.../file/d/<id>/view``: a viewer page,
# not an image. Publishing that link as a blog hero renders nothing, so the
# publish path has to fetch the actual bytes. Everything here is read-only and
# fail-closed: an id it cannot parse, a body that is not a PNG, or a file over
# the cap raises instead of returning something half-usable.
MAX_EDITORIAL_HERO_PNG_BYTES = 12 * 1024 * 1024

_DRIVE_FILE_PATH_RE = re.compile(r"/file/d/([A-Za-z0-9_-]{10,})")
_DRIVE_ID_QUERY_RE = re.compile(r"[?&]id=([A-Za-z0-9_-]{10,})")
_DRIVE_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


def extract_drive_file_id(file_ref: str) -> str:
    """Return the Drive file id behind a share URL, or the bare id itself.

    Accepts ``https://drive.google.com/file/d/<id>/view?usp=drivesdk``,
    ``https://drive.google.com/uc?id=<id>`` and a raw id. Anything else raises:
    guessing an id from an unknown shape is how a publish ends up fetching the
    wrong file.
    """
    ref = str(file_ref or "").strip()
    if not ref:
        raise ValueError("Drive file reference is empty")
    if _DRIVE_BARE_ID_RE.match(ref):
        return ref
    for pattern in (_DRIVE_FILE_PATH_RE, _DRIVE_ID_QUERY_RE):
        match = pattern.search(ref)
        if match:
            return match.group(1)
    raise ValueError("Unrecognized Google Drive file reference")


def download_drive_png(
    file_ref: str, *, max_bytes: int = MAX_EDITORIAL_HERO_PNG_BYTES
) -> bytes:
    """Download one Drive file and return its bytes, PNG-validated.

    Uses the same OAuth app that created the HITL batch, so it can only reach
    files that app owns — the ``drive.file`` scope that already governs
    ``persist_editorial_hitl_images``.
    """
    file_id = extract_drive_file_id(file_ref)
    service = _build_drive_service(_get_drive_credentials())
    try:
        data = (
            service.files()
            .get_media(fileId=file_id, supportsAllDrives=True)
            .execute()
        )
    except Exception as exc:
        raise ValueError("Google Drive download failed for the editorial hero") from exc
    try:
        payload = bytes(data)
    except (TypeError, ValueError) as exc:
        raise ValueError("Google Drive returned a non-binary body") from exc
    if not payload:
        raise ValueError("Google Drive returned an empty file")
    if not payload.startswith(_PNG_SIGNATURE):
        raise ValueError("Downloaded editorial hero is not a PNG")
    if len(payload) > max_bytes:
        raise ValueError(
            f"Editorial hero PNG is {len(payload)} bytes, over the {max_bytes} cap"
        )
    logger.info("[google_drive.editorial_hero] downloaded %d bytes", len(payload))
    return payload


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
