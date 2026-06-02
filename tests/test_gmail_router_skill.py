from unittest.mock import Mock


def test_create_draft_returns_validation_error_without_to():
    """Create draft requires recipient."""
    from scripts.gmail import gmail_router

    result = gmail_router.create_draft(to="", subject="Hola", body="Texto")
    assert result["ok"] is False
    assert result["error"] == "to is required"


def test_create_draft_delegates_to_worker_with_expected_payload():
    """Wrapper forwards required payload to gmail.create_draft."""
    from scripts.gmail import gmail_router

    wc = Mock()
    wc.run.return_value = {"ok": True, "draft_id": "d1", "message_id": "m1"}

    result = gmail_router.create_draft(
        to="dest@mail.com",
        subject="Asunto",
        body="<h1>Hi</h1>",
        body_type="html",
        cc=["a@mail.com"],
        reply_to="r@mail.com",
        wc=wc,
    )

    assert result["ok"] is True
    wc.run.assert_called_once_with(
        "gmail.create_draft",
        {
            "to": "dest@mail.com",
            "subject": "Asunto",
            "body": "<h1>Hi</h1>",
            "body_type": "html",
            "cc": ["a@mail.com"],
            "reply_to": "r@mail.com",
        },
    )


def test_list_drafts_defaults_and_filters_query():
    """list_drafts sends max_results and optional q to gmail.list_drafts."""
    from scripts.gmail import gmail_router

    wc = Mock()
    wc.run.return_value = {
        "ok": True,
        "drafts": [],
    }

    result = gmail_router.list_drafts(max_results=5, q="inbox", wc=wc)

    assert result["ok"] is True
    wc.run.assert_called_once_with(
        "gmail.list_drafts",
        {"max_results": 5, "q": "inbox"},
    )
