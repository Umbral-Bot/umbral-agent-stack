"""
Tasks: Google Calendar integration handlers.

- google.calendar.create_event: Create an event in Google Calendar.
- google.calendar.list_events: List upcoming events from Google Calendar.

Auth: GOOGLE_CALENDAR_TOKEN (OAuth Bearer) or GOOGLE_SERVICE_ACCOUNT_JSON (service account file).
Docs: https://developers.google.com/calendar/api/v3/reference
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker.tasks.google_calendar")

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
DEFAULT_TIMEZONE = "America/Santiago"


def _get_calendar_headers() -> Dict[str, str]:
    """Build authorization headers for Google Calendar API.

    Tries GOOGLE_CALENDAR_TOKEN (Bearer) first. Falls back to
    GOOGLE_SERVICE_ACCOUNT_JSON (service account key file) with
    google-auth (lazy import).
    """
    token = os.environ.get("GOOGLE_CALENDAR_TOKEN")
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
                scopes=["https://www.googleapis.com/auth/calendar"],
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
        "GOOGLE_CALENDAR_TOKEN not set. Provide a Bearer token via "
        "GOOGLE_CALENDAR_TOKEN or a service account key file via "
        "GOOGLE_SERVICE_ACCOUNT_JSON."
    )


def _api_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Perform an HTTP request to the Google Calendar API."""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Google Calendar API %s %s → %s: %s", method, url, exc.code, error_body)
        raise ValueError(f"Google Calendar API error {exc.code}: {error_body}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_google_calendar_create_event(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an event in Google Calendar.

    Input:
        title (str, required): Event summary/title.
        description (str, optional): Event description.
        start (str, required): Start datetime ISO 8601 (e.g. "2026-03-10T10:00:00").
        end (str, optional): End datetime ISO 8601. If omitted, creates an all-day event
            using the date portion of start.
        timezone (str, optional): IANA timezone. Default "America/Santiago".
        attendees (list[str], optional): List of attendee email addresses.
        calendar_id (str, optional): Calendar ID. Default "primary".

    Returns:
        {"ok": True, "event_id": "...", "html_link": "..."}
    """
    headers = _get_calendar_headers()

    title = (input_data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "'title' is required"}

    start_raw = (input_data.get("start") or "").strip()
    if not start_raw:
        return {"ok": False, "error": "'start' is required"}

    end_raw = (input_data.get("end") or "").strip()
    tz = input_data.get("timezone", DEFAULT_TIMEZONE)
    calendar_id = input_data.get("calendar_id", "primary")
    description = input_data.get("description", "")
    attendees: List[str] = input_data.get("attendees") or []

    event_body: Dict[str, Any] = {
        "summary": title,
    }
    if description:
        event_body["description"] = description

    if end_raw:
        event_body["start"] = {"dateTime": start_raw, "timeZone": tz}
        event_body["end"] = {"dateTime": end_raw, "timeZone": tz}
    else:
        date_part = start_raw[:10]
        event_body["start"] = {"date": date_part}
        event_body["end"] = {"date": date_part}

    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    url = f"{CALENDAR_API_BASE}/calendars/{urllib.request.quote(calendar_id, safe='')}/events"
    logger.info("[google.calendar.create_event] Creating event '%s' on calendar '%s'", title, calendar_id)

    result = _api_request("POST", url, headers, event_body)

    return {
        "ok": True,
        "event_id": result.get("id", ""),
        "html_link": result.get("htmlLink", ""),
    }


def handle_google_calendar_list_events(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    List events from a Google Calendar.

    Input:
        calendar_id (str, optional): Calendar ID. Default "primary".
        time_min (str, optional): Lower bound (RFC 3339) for filtering.
        time_max (str, optional): Upper bound (RFC 3339) for filtering.
        max_results (int, optional): Maximum events to return. Default 10.

    Returns:
        {"ok": True, "events": [{"id", "summary", "start", "end", "html_link"}, ...]}
    """
    headers = _get_calendar_headers()

    calendar_id = input_data.get("calendar_id", "primary")
    max_results = input_data.get("max_results", 10)

    params: List[str] = [
        f"maxResults={max_results}",
        "singleEvents=true",
        "orderBy=startTime",
    ]
    time_min = input_data.get("time_min")
    if time_min:
        params.append(f"timeMin={urllib.request.quote(time_min, safe='')}")
    time_max = input_data.get("time_max")
    if time_max:
        params.append(f"timeMax={urllib.request.quote(time_max, safe='')}")

    url = (
        f"{CALENDAR_API_BASE}/calendars/{urllib.request.quote(calendar_id, safe='')}/events"
        f"?{'&'.join(params)}"
    )
    logger.info("[google.calendar.list_events] Listing events from '%s'", calendar_id)

    result = _api_request("GET", url, headers)

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        events.append({
            "id": item.get("id", ""),
            "summary": item.get("summary", ""),
            "start": start.get("dateTime") or start.get("date", ""),
            "end": end.get("dateTime") or end.get("date", ""),
            "html_link": item.get("htmlLink", ""),
        })

    return {"ok": True, "events": events}
