"""
Tasks: Gmail integration handlers.

- gmail.create_draft: Create an email draft in Gmail.
- gmail.list_drafts: List existing drafts.

Auth: GOOGLE_GMAIL_TOKEN (OAuth Bearer) or GOOGLE_SERVICE_ACCOUNT_JSON (service account file).
Docs: https://developers.google.com/gmail/api/reference/rest
"""

import base64
import json
import logging
import os
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker.tasks.gmail")

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def _get_gmail_headers() -> Dict[str, str]:
    """Build authorization headers for Gmail API.

    Tries GOOGLE_GMAIL_TOKEN (Bearer) first. Falls back to
    GOOGLE_SERVICE_ACCOUNT_JSON with google-auth (lazy import).
    """
    token = os.environ.get("GOOGLE_GMAIL_TOKEN")
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_path:
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            creds = service_account.Credentials.from_service_account_file(
                sa_path,
                scopes=["https://www.googleapis.com/auth/gmail.compose"],
            )
            creds.refresh(Request())
            return {
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            }
        except ImportError:
            raise ValueError(
                "google-auth package is required when using GOOGLE_SERVICE_ACCOUNT_JSON. "
                "Install with: pip install google-auth"
            )
        except Exception as exc:
            raise ValueError(f"Failed to load service account credentials: {exc}")

    raise ValueError(
        "GOOGLE_GMAIL_TOKEN not set. Provide a Bearer token via "
        "GOOGLE_GMAIL_TOKEN or a service account key file via "
        "GOOGLE_SERVICE_ACCOUNT_JSON."
    )


def _api_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Perform an HTTP request to the Gmail API."""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Gmail API %s %s → %s: %s", method, url, exc.code, error_body)
        raise ValueError(f"Gmail API error {exc.code}: {error_body}")


def _build_rfc2822_message(
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
) -> str:
    """Build an RFC 2822 email and return it as a base64url-encoded string."""
    if body_type == "html":
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to

    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_gmail_create_draft(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an email draft in Gmail.

    Input:
        to (str, required): Recipient email address.
        subject (str, required): Email subject line.
        body (str, required): Email body (plain text or HTML).
        body_type (str, optional): "plain" or "html". Default "plain".
        cc (list[str], optional): CC recipients.
        reply_to (str, optional): Reply-To address.

    Returns:
        {"ok": True, "draft_id": "...", "message_id": "..."}
    """
    headers = _get_gmail_headers()

    to = (input_data.get("to") or "").strip()
    if not to:
        return {"ok": False, "error": "'to' is required"}

    subject = (input_data.get("subject") or "").strip()
    if not subject:
        return {"ok": False, "error": "'subject' is required"}

    body = input_data.get("body", "")
    body_type = input_data.get("body_type", "plain")
    cc = input_data.get("cc") or []
    reply_to = input_data.get("reply_to")

    raw = _build_rfc2822_message(
        to=to,
        subject=subject,
        body=body,
        body_type=body_type,
        cc=cc,
        reply_to=reply_to,
    )

    url = f"{GMAIL_API_BASE}/users/me/drafts"
    logger.info("[gmail.create_draft] Creating draft to='%s' subject='%s'", to, subject)

    result = _api_request("POST", url, headers, {"message": {"raw": raw}})

    draft_id = result.get("id", "")
    message_id = result.get("message", {}).get("id", "")

    return {"ok": True, "draft_id": draft_id, "message_id": message_id}


def handle_gmail_list_drafts(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    List drafts from Gmail.

    Input:
        max_results (int, optional): Maximum drafts to return. Default 10.
        q (str, optional): Gmail search query to filter drafts.

    Returns:
        {"ok": True, "drafts": [{"id": "...", "snippet": "..."}, ...]}
    """
    headers = _get_gmail_headers()

    max_results = input_data.get("max_results", 10)
    query = input_data.get("q", "")

    params: List[str] = [f"maxResults={max_results}"]
    if query:
        params.append(f"q={urllib.request.quote(query, safe='')}")

    url = f"{GMAIL_API_BASE}/users/me/drafts?{'&'.join(params)}"
    logger.info("[gmail.list_drafts] Listing drafts (max=%d)", max_results)

    result = _api_request("GET", url, headers)

    drafts = []
    for item in result.get("drafts", []):
        msg = item.get("message", {})
        drafts.append({
            "id": item.get("id", ""),
            "message_id": msg.get("id", ""),
            "snippet": msg.get("snippet", ""),
        })

    return {"ok": True, "drafts": drafts}
