"""
Tests for Google Calendar and Gmail worker task handlers,
including integration with the Granola follow-up pipeline.
"""

import base64
import io
import json
import os
import pytest
from http.client import HTTPResponse
from unittest.mock import patch, MagicMock

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.tasks.google_calendar import (
    handle_google_calendar_create_event,
    handle_google_calendar_list_events,
    _get_calendar_headers,
)
from worker.tasks.gmail import (
    handle_gmail_create_draft,
    handle_gmail_list_drafts,
    _get_gmail_headers,
    _build_rfc2822_message,
)
from worker.tasks.granola import handle_granola_create_followup


def _mock_urlopen(response_data: dict, status: int = 200):
    """Build a mock for urllib.request.urlopen that returns JSON."""
    response_body = json.dumps(response_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ===========================================================================
# Google Calendar tests
# ===========================================================================


class TestGoogleCalendarCreateEvent:

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_create_event_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "evt-123",
            "htmlLink": "https://calendar.google.com/event?eid=evt-123",
        })

        result = handle_google_calendar_create_event({
            "title": "Sprint Planning",
            "start": "2026-03-10T10:00:00",
            "end": "2026-03-10T11:00:00",
            "timezone": "America/Santiago",
        })

        assert result["ok"] is True
        assert result["event_id"] == "evt-123"
        assert "calendar.google.com" in result["html_link"]

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.method == "POST"
        assert "calendars/primary/events" in req.full_url
        body = json.loads(req.data.decode("utf-8"))
        assert body["summary"] == "Sprint Planning"
        assert body["start"]["dateTime"] == "2026-03-10T10:00:00"
        assert body["end"]["dateTime"] == "2026-03-10T11:00:00"

    @patch.dict(os.environ, {}, clear=False)
    def test_create_event_missing_token(self):
        env = os.environ.copy()
        env.pop("GOOGLE_CALENDAR_TOKEN", None)
        env.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_CALENDAR_TOKEN not set"):
                handle_google_calendar_create_event({
                    "title": "Test",
                    "start": "2026-03-10T10:00:00",
                    "end": "2026-03-10T11:00:00",
                })

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_create_event_all_day(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "evt-allday",
            "htmlLink": "https://calendar.google.com/event?eid=evt-allday",
        })

        result = handle_google_calendar_create_event({
            "title": "Deadline entrega",
            "start": "2026-03-15T00:00:00",
        })

        assert result["ok"] is True
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["start"] == {"date": "2026-03-15"}
        assert body["end"] == {"date": "2026-03-15"}
        assert "dateTime" not in body["start"]

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_create_event_with_attendees(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "evt-att",
            "htmlLink": "https://calendar.google.com/event?eid=evt-att",
        })

        result = handle_google_calendar_create_event({
            "title": "Kickoff meeting",
            "start": "2026-03-10T14:00:00",
            "end": "2026-03-10T15:00:00",
            "attendees": ["alice@example.com", "bob@example.com"],
        })

        assert result["ok"] is True
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert len(body["attendees"]) == 2
        assert body["attendees"][0]["email"] == "alice@example.com"
        assert body["attendees"][1]["email"] == "bob@example.com"

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    def test_create_event_missing_title(self):
        result = handle_google_calendar_create_event({
            "start": "2026-03-10T10:00:00",
            "end": "2026-03-10T11:00:00",
        })
        assert result["ok"] is False
        assert "title" in result["error"]

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    def test_create_event_missing_start(self):
        result = handle_google_calendar_create_event({"title": "Test"})
        assert result["ok"] is False
        assert "start" in result["error"]


class TestGoogleCalendarListEvents:

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_list_events_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "items": [
                {
                    "id": "evt-1",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-03-05T09:00:00-03:00"},
                    "end": {"dateTime": "2026-03-05T09:15:00-03:00"},
                    "htmlLink": "https://calendar.google.com/event?eid=evt-1",
                },
                {
                    "id": "evt-2",
                    "summary": "Sprint Review",
                    "start": {"dateTime": "2026-03-05T14:00:00-03:00"},
                    "end": {"dateTime": "2026-03-05T15:00:00-03:00"},
                    "htmlLink": "https://calendar.google.com/event?eid=evt-2",
                },
            ]
        })

        result = handle_google_calendar_list_events({
            "time_min": "2026-03-01T00:00:00Z",
            "max_results": 10,
        })

        assert result["ok"] is True
        assert len(result["events"]) == 2
        assert result["events"][0]["summary"] == "Standup"
        assert result["events"][1]["id"] == "evt-2"

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_list_events_empty(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"items": []})

        result = handle_google_calendar_list_events({
            "time_min": "2026-03-01T00:00:00Z",
        })

        assert result["ok"] is True
        assert result["events"] == []


# ===========================================================================
# Gmail tests
# ===========================================================================


class TestGmailCreateDraft:

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_create_draft_plain_text(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "draft-001",
            "message": {"id": "msg-001"},
        })

        result = handle_gmail_create_draft({
            "to": "recipient@example.com",
            "subject": "Follow-up meeting",
            "body": "Hello, this is a follow-up email.",
            "body_type": "plain",
        })

        assert result["ok"] is True
        assert result["draft_id"] == "draft-001"
        assert result["message_id"] == "msg-001"

        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert "users/me/drafts" in req.full_url
        body = json.loads(req.data.decode("utf-8"))
        assert "raw" in body["message"]

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_create_draft_html(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "draft-002",
            "message": {"id": "msg-002"},
        })

        result = handle_gmail_create_draft({
            "to": "recipient@example.com",
            "subject": "HTML Email",
            "body": "<h1>Hello</h1><p>This is HTML content.</p>",
            "body_type": "html",
        })

        assert result["ok"] is True
        assert result["draft_id"] == "draft-002"

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        raw_decoded = base64.urlsafe_b64decode(body["message"]["raw"])
        assert b"Content-Type: multipart/alternative" in raw_decoded
        assert b"text/html" in raw_decoded

    @patch.dict(os.environ, {}, clear=False)
    def test_gmail_create_draft_missing_token(self):
        env = os.environ.copy()
        env.pop("GOOGLE_GMAIL_TOKEN", None)
        env.pop("GOOGLE_GMAIL_REFRESH_TOKEN", None)
        env.pop("GOOGLE_GMAIL_CLIENT_ID", None)
        env.pop("GOOGLE_GMAIL_CLIENT_SECRET", None)
        env.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Gmail auth not configured"):
                handle_gmail_create_draft({
                    "to": "recipient@example.com",
                    "subject": "Test",
                    "body": "Test body",
                })

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_create_draft_with_cc(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "draft-003",
            "message": {"id": "msg-003"},
        })

        result = handle_gmail_create_draft({
            "to": "main@example.com",
            "subject": "CC Test",
            "body": "Testing CC recipients.",
            "cc": ["cc1@example.com", "cc2@example.com"],
            "reply_to": "noreply@example.com",
        })

        assert result["ok"] is True
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        raw_decoded = base64.urlsafe_b64decode(body["message"]["raw"])
        assert b"Cc: cc1@example.com, cc2@example.com" in raw_decoded
        assert b"Reply-To: noreply@example.com" in raw_decoded

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    def test_gmail_create_draft_missing_to(self):
        result = handle_gmail_create_draft({
            "subject": "Test",
            "body": "Body",
        })
        assert result["ok"] is False
        assert "to" in result["error"]

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    def test_gmail_create_draft_missing_subject(self):
        result = handle_gmail_create_draft({
            "to": "test@example.com",
            "body": "Body",
        })
        assert result["ok"] is False
        assert "subject" in result["error"]


class TestGmailListDrafts:

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_list_drafts_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({
            "drafts": [
                {"id": "d1", "message": {"id": "m1", "snippet": "Hello..."}},
                {"id": "d2", "message": {"id": "m2", "snippet": "Follow-up..."}},
            ]
        })

        result = handle_gmail_list_drafts({"max_results": 5})

        assert result["ok"] is True
        assert len(result["drafts"]) == 2
        assert result["drafts"][0]["id"] == "d1"
        assert result["drafts"][1]["snippet"] == "Follow-up..."

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_list_drafts_empty(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"drafts": []})

        result = handle_gmail_list_drafts({})

        assert result["ok"] is True
        assert result["drafts"] == []

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_gmail_list_drafts_with_query(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"drafts": []})

        handle_gmail_list_drafts({"q": "subject:test", "max_results": 3})

        req = mock_urlopen.call_args[0][0]
        assert "q=" in req.full_url
        assert "maxResults=3" in req.full_url


# ===========================================================================
# RFC 2822 message builder
# ===========================================================================


class TestBuildRFC2822Message:

    def test_plain_text_message(self):
        raw = _build_rfc2822_message(
            to="test@example.com",
            subject="Hello",
            body="World",
            body_type="plain",
        )
        decoded = base64.urlsafe_b64decode(raw)
        assert b"To: test@example.com" in decoded
        assert b"Subject: Hello" in decoded
        assert b"text/plain" in decoded

    def test_html_message(self):
        raw = _build_rfc2822_message(
            to="test@example.com",
            subject="HTML Test",
            body="<p>Hello</p>",
            body_type="html",
        )
        decoded = base64.urlsafe_b64decode(raw)
        assert b"text/html" in decoded
        assert b"Content-Type: multipart/alternative" in decoded


# ===========================================================================
# Auth helpers
# ===========================================================================


class TestAuthHelpers:

    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "bearer-cal-123"})
    def test_calendar_headers_bearer(self):
        headers = _get_calendar_headers()
        assert headers["Authorization"] == "Bearer bearer-cal-123"
        assert headers["Content-Type"] == "application/json"

    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "bearer-gmail-456"})
    def test_gmail_headers_bearer(self):
        headers = _get_gmail_headers()
        assert headers["Authorization"] == "Bearer bearer-gmail-456"
        assert headers["Content-Type"] == "application/json"


# ===========================================================================
# Granola integration tests
# ===========================================================================


class TestGranolaFollowupCalendar:

    @patch("worker.tasks.granola.notion_client")
    @patch.dict(os.environ, {"GOOGLE_CALENDAR_TOKEN": "test-cal-token"})
    @patch("worker.tasks.google_calendar.urllib.request.urlopen")
    def test_granola_followup_calls_calendar(self, mock_urlopen, mock_nc):
        mock_urlopen.return_value = _mock_urlopen({
            "id": "cal-evt-99",
            "htmlLink": "https://calendar.google.com/event?eid=cal-evt-99",
        })

        result = handle_granola_create_followup({
            "transcript_page_id": "page-001",
            "followup_type": "calendar_event",
            "title": "Sprint Retro",
            "date": "2026-03-04",
            "attendees": ["alice@example.com", "bob@example.com"],
            "start": "2026-03-10T14:00:00",
            "end": "2026-03-10T15:00:00",
        })

        assert result["followup_type"] == "calendar_event"
        assert result["result"]["calendar_event"]["ok"] is True
        assert result["result"]["calendar_event"]["event_id"] == "cal-evt-99"

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["summary"] == "Follow-up: Sprint Retro"
        assert len(body["attendees"]) == 2


class TestGranolaFollowupGmail:

    @patch("worker.tasks.granola.notion_client")
    @patch.dict(os.environ, {"GOOGLE_GMAIL_TOKEN": "test-gmail-token"})
    @patch("worker.tasks.gmail.urllib.request.urlopen")
    def test_granola_followup_calls_gmail(self, mock_urlopen, mock_nc):
        mock_nc.add_comment.return_value = {"comment_id": "c-1"}

        mock_urlopen.return_value = _mock_urlopen({
            "id": "draft-from-granola",
            "message": {"id": "msg-from-granola"},
        })

        result = handle_granola_create_followup({
            "transcript_page_id": "page-002",
            "followup_type": "email_draft",
            "title": "Budget Review",
            "date": "2026-03-04",
            "attendees": ["finance@example.com", "cfo@example.com"],
            "action_items": [{"text": "Send report", "assignee": "Ana", "due": "2026-03-06"}],
        })

        assert result["followup_type"] == "email_draft"
        assert result["result"]["posted_to_notion"] is True
        assert result["result"]["email_draft"] is not None
        assert result["result"]["email_draft"]["ok"] is True
        assert result["result"]["email_draft"]["draft_id"] == "draft-from-granola"

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert "raw" in body["message"]
