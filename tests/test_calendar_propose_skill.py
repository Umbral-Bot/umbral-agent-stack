from unittest.mock import Mock


def test_create_event_proposal_adds_prefix_and_delegates():
    """Proposal wrapper must prefix title and forward to google.calendar.create_event."""
    from scripts.google_calendar import calendar_propose

    david_calendar_id = calendar_propose.DAVID_PRIMARY_CALENDAR_ID
    wc = Mock()
    wc.run.return_value = {"ok": True, "event_id": "e1", "html_link": "https://calendar.google.com"}

    result = calendar_propose.create_event_proposal(
        title="Reunión semanal",
        start="2026-03-10T10:00:00",
        end="2026-03-10T11:00:00",
        attendees=["a@example.com"],
        description="Agenda",
        wc=wc,
    )

    assert result["ok"] is True
    wc.run.assert_called_once_with(
        "google.calendar.create_event",
        {
            "title": "[PROPUESTA] Reunión semanal",
            "description": "Agenda",
            "start": "2026-03-10T10:00:00",
            "calendar_id": david_calendar_id,
            "timezone": "America/Santiago",
            "end": "2026-03-10T11:00:00",
            "attendees": ["a@example.com"],
        },
    )


def test_create_event_proposal_blocks_disallowed_calendar():
    """Wrapper blocks calendar ids outside whitelist."""
    from scripts.google_calendar import calendar_propose

    result = calendar_propose.create_event_proposal(
        title="Reunión",
        start="2026-03-10T10:00:00",
        calendar_id="other@group.calendar.google.com",
    )
    assert result["ok"] is False
    assert result["error"] == "calendar_id not in whitelist"


def test_list_events_forward():
    """Wrapper forwards list_events payload."""
    from scripts.google_calendar import calendar_propose

    david_calendar_id = calendar_propose.DAVID_PRIMARY_CALENDAR_ID
    wc = Mock()
    wc.run.return_value = {"ok": True, "events": []}
    result = calendar_propose.list_events(
        calendar_id=david_calendar_id,
        time_min="2026-03-01T00:00:00Z",
        max_results=12,
        wc=wc,
    )

    assert result["ok"] is True
    wc.run.assert_called_once_with(
        "google.calendar.list_events",
        {
            "calendar_id": david_calendar_id,
            "max_results": 12,
            "time_min": "2026-03-01T00:00:00Z",
        },
    )


def test_list_events_blocks_disallowed_calendar():
    """Wrapper blocks calendar listing outside allowed calendar whitelist."""
    from scripts.google_calendar import calendar_propose

    result = calendar_propose.list_events(
        calendar_id="other@group.calendar.google.com",
    )
    assert result["ok"] is False
    assert result["error"] == "calendar_id not in whitelist"
