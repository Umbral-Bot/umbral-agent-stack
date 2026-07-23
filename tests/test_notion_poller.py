from unittest.mock import MagicMock, patch

from dispatcher.notion_poller import (
    _collect_candidate_comments,
    _do_poll,
    _extract_poll_comments_result,
)


def test_extract_poll_comments_result_supports_worker_envelope():
    response = {
        "ok": True,
        "result": {
            "comments": [
                {"id": "c-1", "created_time": "2026-03-16T21:00:00.000Z", "text": "Hola Rick"}
            ]
        },
    }
    comments = _extract_poll_comments_result(response)
    assert len(comments) == 1
    assert comments[0]["id"] == "c-1"


def test_control_room_target_resolves_page_id_from_env():
    wc = MagicMock()
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-control",
                    "created_time": "2026-05-07T18:44:00.000Z",
                    "created_by": "user-1",
                    "text": "@Rick ping worker /health",
                }
            ]
        },
    }
    queue = MagicMock()
    scheduler = MagicMock()
    r = MagicMock()
    r.get.return_value = "2026-05-07T18:40:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_CONTROL_ROOM_PAGE_ID": "control-room-page",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        with patch("dispatcher.rick_mention._david_allowlist", return_value={"user-1"}):
            with patch("dispatcher.rick_mention.is_rick_mention", return_value=True):
                with patch("dispatcher.rick_mention.handle_rick_mention") as mock_handle_rick:
                    _do_poll(wc, queue, r, scheduler)

    wc.notion_poll_comments.assert_called_once_with(
        since="2026-05-07T18:35:00+00:00",
        limit=20,
        page_id="control-room-page",
    )
    mock_handle_rick.assert_called_once()
    assert mock_handle_rick.call_args.kwargs["page_id"] == "control-room-page"
    assert mock_handle_rick.call_args.kwargs["page_kind"] == "control_room"


def test_control_room_target_no_env_keeps_none_with_warning(caplog):
    wc = MagicMock()
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-control",
                    "created_time": "2026-05-07T18:44:00.000Z",
                    "text": "@Rick ping worker /health",
                }
            ]
        },
    }

    with patch.dict(
        "os.environ",
        {
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            comments = _collect_candidate_comments(wc, "2026-05-07T18:40:00+00:00", 20)

    wc.notion_poll_comments.assert_called_once_with(
        since="2026-05-07T18:35:00+00:00",
        limit=20,
        page_id=None,
    )
    assert comments[0]["page_kind"] == "control_room"
    assert "page_id" not in comments[0]
    assert "NOTION_CONTROL_ROOM_PAGE_ID" in caplog.text


def test_control_room_target_no_env_logs_warning_no_silent_none(caplog):
    wc = MagicMock()
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-control",
                    "created_time": "2026-05-07T18:44:00.000Z",
                    "created_by": "user-1",
                    "text": "@Rick ping worker /health",
                }
            ]
        },
    }
    queue = MagicMock()
    scheduler = MagicMock()
    r = MagicMock()
    r.get.return_value = "2026-05-07T18:40:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            with patch("dispatcher.rick_mention._david_allowlist", return_value={"user-1"}):
                with patch("dispatcher.rick_mention.is_rick_mention", return_value=True):
                    with patch("dispatcher.rick_mention.handle_rick_mention") as mock_handle_rick:
                        _do_poll(wc, queue, r, scheduler)

    assert "NOTION_CONTROL_ROOM_PAGE_ID" in caplog.text
    mock_handle_rick.assert_called_once()
    assert mock_handle_rick.call_args.kwargs["page_id"] is None
    assert mock_handle_rick.call_args.kwargs["page_kind"] == "control_room"


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_advances_last_ts_from_worker_envelope(mock_handle_smart_reply):
    wc = MagicMock()
    wc.run.side_effect = [
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": []}},
    ]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-1",
                    "created_time": "2026-03-16T21:00:00.000Z",
                    "text": "Hola Rick revisa esto",
                },
                {
                    "id": "c-2",
                    "created_time": "2026-03-16T21:05:00.000Z",
                    "text": "Rick: eco propio",
                },
            ]
        },
    }
    queue = MagicMock()
    scheduler = MagicMock()
    r = MagicMock()
    r.get.return_value = "2026-03-16T20:00:00+00:00"
    r.set.side_effect = [True, "OK"]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    wc.notion_poll_comments.assert_called_once_with(
        since="2026-03-16T19:55:00+00:00",
        limit=20,
        page_id=None,
    )
    mock_handle_smart_reply.assert_called_once()
    assert mock_handle_smart_reply.call_args[0][0] == "Hola Rick revisa esto"
    r.set.assert_any_call(
        "umbral:notion_poller:processed_comment:c-1",
        "1",
        nx=True,
        ex=86400,
    )
    r.set.assert_any_call(
        "umbral:notion_poller:last_ts",
        "2026-03-16T21:05:00+00:00",
    )


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_accepts_direct_comments_shape(mock_handle_smart_reply):
    wc = MagicMock()
    wc.run.side_effect = [
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": []}},
    ]
    wc.notion_poll_comments.return_value = {
        "comments": [
            {
                "id": "c-1",
                "created_time": "2026-03-16T21:00:00.000Z",
                "text": "mensaje externo",
            }
        ],
        "count": 1,
    }
    queue = MagicMock()
    scheduler = MagicMock()
    r = MagicMock()
    r.get.return_value = "2026-03-16T20:00:00+00:00"
    r.set.side_effect = [True, "OK"]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    mock_handle_smart_reply.assert_called_once()
    r.set.assert_any_call(
        "umbral:notion_poller:last_ts",
        "2026-03-16T21:00:00+00:00",
    )


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_skips_already_processed_comment(mock_handle_smart_reply):
    wc = MagicMock()
    wc.run.side_effect = [
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": []}},
    ]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "dup-1",
                    "created_time": "2026-03-16T21:00:00.000Z",
                    "text": "mensaje repetido",
                }
            ]
        },
    }
    queue = MagicMock()
    scheduler = MagicMock()
    r = MagicMock()
    r.get.return_value = "2026-03-16T20:00:00+00:00"
    r.set.side_effect = [False, "OK"]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    mock_handle_smart_reply.assert_not_called()
    r.set.assert_any_call(
        "umbral:notion_poller:last_ts",
        "2026-03-16T21:00:00+00:00",
    )


def test_collect_candidate_comments_includes_review_targets_and_deduplicates():
    wc = MagicMock()
    wc.run.side_effect = [
        {
            "ok": True,
            "result": {
                "items": [
                    {"page_id": "deliverable-1", "properties": {"Estado revision": "Pendiente revision"}},
                    {"page_id": "deliverable-2", "properties": {"Estado revision": "Pendiente revision"}},
                ]
            },
        },
        {
            "ok": True,
            "result": {
                "items": [
                    {"page_id": "project-1"},
                ]
            },
        },
    ]
    wc.notion_poll_comments.side_effect = [
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-1",
                        "created_time": "2026-03-16T21:00:00.000Z",
                        "text": "mensaje control room",
                    }
                ]
            },
        },
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-2",
                        "created_time": "2026-03-16T21:02:00.000Z",
                        "text": "trabajo incompleto",
                    }
                ]
            },
        },
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-2",
                        "created_time": "2026-03-16T21:02:00.000Z",
                        "text": "trabajo incompleto",
                    }
                ]
            },
        },
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-3",
                        "created_time": "2026-03-16T21:03:00.000Z",
                        "text": "no se entiende",
                    }
                ]
            },
        },
    ]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "control-room-page",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert [comment["id"] for comment in comments] == ["c-1", "c-2", "c-3"]
    assert comments[0]["page_id"] == "control-room-page"
    assert comments[0]["page_kind"] == "control_room"
    assert comments[1]["page_id"] == "deliverable-1"
    assert comments[1]["page_kind"] == "deliverable"
    assert comments[2]["page_id"] == "project-1"
    assert comments[2]["page_kind"] == "project"
    expected_calls = [
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "control-room-page"},
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "deliverable-1"},
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "deliverable-2"},
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "project-1"},
    ]
    assert [call.kwargs for call in wc.notion_poll_comments.call_args_list] == expected_calls


def test_collect_candidate_comments_includes_session_capitalizable_targets():
    wc = MagicMock()
    wc.run.side_effect = [
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": [{"page_id": "session-1"}]}},
    ]
    wc.notion_poll_comments.side_effect = [
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-1",
                        "created_time": "2026-03-16T21:00:00.000Z",
                        "text": "mensaje control room",
                    }
                ]
            },
        },
        {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-2",
                        "created_time": "2026-03-16T21:01:00.000Z",
                        "text": "revisar sesion",
                    }
                ]
            },
        },
    ]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "curated-db",
            "NOTION_CONTROL_ROOM_PAGE_ID": "control-room-page",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert [comment["id"] for comment in comments] == ["c-1", "c-2"]
    assert comments[0]["page_id"] == "control-room-page"
    assert comments[0]["page_kind"] == "control_room"
    assert comments[1]["page_id"] == "session-1"
    assert comments[1]["page_kind"] == "session_capitalizable"
    expected_calls = [
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "control-room-page"},
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "session-1"},
    ]
    assert [call.kwargs for call in wc.notion_poll_comments.call_args_list] == expected_calls


def test_collect_candidate_comments_falls_back_when_deliverable_filter_fails():
    """When the deliverables DB query fails, it is caught and projects still resolve."""
    wc = MagicMock()
    wc.run.side_effect = [
        RuntimeError("500 from deliverables query"),
        {"ok": True, "result": {"items": [{"page_id": "project-1"}]}},
    ]
    wc.notion_poll_comments.return_value = {
        "ok": True, "result": {"comments": []},
    }

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert comments == []
    # Deliverables call raised, projects call succeeded
    assert wc.run.call_count == 2
    # poll_comments called for control room + project-1 (deliverables skipped)
    assert wc.notion_poll_comments.call_count == 2

# ---------------------------------------------------------------------------
# B2 Fase 2: anti-loop author.id guard tests
# ---------------------------------------------------------------------------

import pytest

from dispatcher.notion_poller import (
    _resolve_bot_user_id,
    _reset_bot_user_id_cache,
)


@pytest.fixture(autouse=False)
def _clear_bot_cache():
    _reset_bot_user_id_cache()
    yield
    _reset_bot_user_id_cache()


def test_resolve_bot_user_id_env_override_no_http(_clear_bot_cache, caplog):
    """B2: NOTION_BOT_USER_ID env var takes precedence and skips HTTP entirely."""
    with patch.dict("os.environ", {"NOTION_BOT_USER_ID": "bot-from-env"}, clear=False):
        with patch("dispatcher.notion_poller.httpx.Client") as mock_client:
            result = _resolve_bot_user_id()
    assert result == "bot-from-env"
    mock_client.assert_not_called()


def test_resolve_bot_user_id_falls_back_to_users_me(_clear_bot_cache):
    """B2: with no env override, GET /v1/users/me resolves bot id and caches it."""
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = b'{"id":"bot-from-api"}'
    fake_resp.json.return_value = {"id": "bot-from-api", "type": "bot"}

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value.get.return_value = fake_resp

    with patch.dict(
        "os.environ",
        {"NOTION_BOT_USER_ID": "", "NOTION_API_KEY": "secret_xxx"},
        clear=False,
    ):
        with patch("dispatcher.notion_poller.httpx.Client", return_value=mock_ctx) as mock_client:
            first = _resolve_bot_user_id()
            second = _resolve_bot_user_id()

    assert first == "bot-from-api"
    assert second == "bot-from-api"
    # Cached: HTTP client constructed only once.
    assert mock_client.call_count == 1


def test_resolve_bot_user_id_no_token_returns_none_and_warns(_clear_bot_cache, caplog):
    """B2: if NOTION_API_KEY missing, return None and log a single warning."""
    with patch.dict(
        "os.environ",
        {"NOTION_BOT_USER_ID": "", "NOTION_API_KEY": ""},
        clear=False,
    ):
        with patch("dispatcher.notion_poller.httpx.Client") as mock_client:
            with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
                result = _resolve_bot_user_id()
    assert result is None
    assert "ECHO_PREFIX" in caplog.text
    mock_client.assert_not_called()


def test_resolve_bot_user_id_http_error_returns_none(_clear_bot_cache, caplog):
    """B2: 4xx from /v1/users/me leaves us with None, no exception leaks."""
    fake_resp = MagicMock()
    fake_resp.status_code = 401
    fake_resp.content = b''
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value.get.return_value = fake_resp

    with patch.dict(
        "os.environ",
        {"NOTION_BOT_USER_ID": "", "NOTION_API_KEY": "secret_xxx"},
        clear=False,
    ):
        with patch("dispatcher.notion_poller.httpx.Client", return_value=mock_ctx):
            with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
                result = _resolve_bot_user_id()
    assert result is None
    assert "ECHO_PREFIX" in caplog.text


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_skips_bot_reply_without_rick_prefix(mock_smart, _clear_bot_cache):
    """B2 critical: a bot reply that does NOT start with 'Rick:' is still ignored
    by the author.id guard (this is the gap that ECHO_PREFIX alone did not cover)."""
    wc = MagicMock()
    wc.run.side_effect = [{"ok": True, "result": {"items": []}}, {"ok": True, "result": {"items": []}}]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-bot-1",
                    "created_time": "2026-05-15T10:00:00.000Z",
                    "created_by": "bot-from-env",
                    "text": "Worker /health response:\n{\"status\":\"ok\"}",
                }
            ]
        },
    }
    queue = MagicMock(); scheduler = MagicMock(); r = MagicMock()
    r.get.return_value = "2026-05-15T09:00:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_BOT_USER_ID": "bot-from-env",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    mock_smart.assert_not_called()
    queue.enqueue.assert_not_called()


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_skips_bot_reply_with_rick_prefix(mock_smart, _clear_bot_cache):
    """B2: a bot reply that DOES start with 'Rick:' is skipped by the author guard
    (would also be caught by ECHO_PREFIX; both layers active)."""
    wc = MagicMock()
    wc.run.side_effect = [{"ok": True, "result": {"items": []}}, {"ok": True, "result": {"items": []}}]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-bot-2",
                    "created_time": "2026-05-15T10:00:00.000Z",
                    "created_by": "bot-from-env",
                    "text": "Rick: Tarea registrada para equipo [research].",
                }
            ]
        },
    }
    queue = MagicMock(); scheduler = MagicMock(); r = MagicMock()
    r.get.return_value = "2026-05-15T09:00:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_BOT_USER_ID": "bot-from-env",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    mock_smart.assert_not_called()


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_fallback_echo_prefix_when_bot_id_unresolvable(mock_smart, _clear_bot_cache):
    """B2: with no bot_user_id env and no NOTION_API_KEY, the author guard returns None
    and ECHO_PREFIX fallback still skips 'Rick:'-prefixed comments. No regression."""
    wc = MagicMock()
    wc.run.side_effect = [{"ok": True, "result": {"items": []}}, {"ok": True, "result": {"items": []}}]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-fallback",
                    "created_time": "2026-05-15T10:00:00.000Z",
                    "created_by": "some-author",
                    "text": "Rick: legacy echo",
                }
            ]
        },
    }
    queue = MagicMock(); scheduler = MagicMock(); r = MagicMock()
    r.get.return_value = "2026-05-15T09:00:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_BOT_USER_ID": "",
            "NOTION_API_KEY": "",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
        },
        clear=False,
    ):
        _do_poll(wc, queue, r, scheduler)

    mock_smart.assert_not_called()


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_processes_authorized_david_mention(mock_smart, _clear_bot_cache):
    """B2 regression: David's @rick mention is still routed (author guard does not block
    non-bot authors). Bot id is set; David's author id differs from bot id."""
    wc = MagicMock()
    wc.run.side_effect = [{"ok": True, "result": {"items": []}}, {"ok": True, "result": {"items": []}}]
    wc.notion_poll_comments.return_value = {
        "ok": True,
        "result": {
            "comments": [
                {
                    "id": "c-david",
                    "created_time": "2026-05-15T10:00:00.000Z",
                    "created_by": "user-david",
                    "text": "@rick /health",
                }
            ]
        },
    }
    queue = MagicMock(); scheduler = MagicMock(); r = MagicMock()
    r.get.return_value = "2026-05-15T09:00:00+00:00"
    r.set.return_value = True

    with patch.dict(
        "os.environ",
        {
            "NOTION_BOT_USER_ID": "bot-from-env",
            "DAVID_NOTION_USER_ID": "user-david",
            "NOTION_CONTROL_ROOM_PAGE_ID": "",
            "NOTION_DELIVERABLES_DB_ID": "",
            "NOTION_PROJECTS_DB_ID": "",
            "NOTION_CURATED_SESSIONS_DB_ID": "",
            "NOTION_GRANOLA_DB_ID": "",
        },
        clear=False,
    ):
        with patch("dispatcher.rick_mention.handle_rick_mention") as mock_rick:
            _do_poll(wc, queue, r, scheduler)

    mock_rick.assert_called_once()
    mock_smart.assert_not_called()


def test_resolve_bot_user_id_malformed_json_returns_none(_clear_bot_cache, caplog):
    """B2: 200 OK with non-JSON body \u2192 None + warning, no exception leaks."""
    import json as _json

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = b"not json"
    fake_resp.json.side_effect = _json.JSONDecodeError("Expecting value", "doc", 0)

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value.get.return_value = fake_resp

    with patch.dict(
        "os.environ",
        {"NOTION_BOT_USER_ID": "", "NOTION_API_KEY": "secret_xxx"},
        clear=False,
    ):
        with patch("dispatcher.notion_poller.httpx.Client", return_value=mock_ctx):
            with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
                result = _resolve_bot_user_id()

    assert result is None
    assert "ECHO_PREFIX" in caplog.text
    # Token MUST NOT appear in the log message under any circumstance.
    assert "secret_xxx" not in caplog.text


# ---------------------------------------------------------------------------
# P2a: V2 classify isolation — default-off flag, human gate, strict validation
# ---------------------------------------------------------------------------

from dispatcher.notion_poller import (  # noqa: E402
    CLASSIFIED_TTL_SEC,
    _classification_result_complete,
    _classify_pending_granola_pages,
    _reset_v2_disabled_log,
    _v2_classify_enabled,
    _v2_row_eligible,
)

_P2A_BASE_ENV = {
    "NOTION_CONTROL_ROOM_PAGE_ID": "",
    "NOTION_DELIVERABLES_DB_ID": "",
    "NOTION_PROJECTS_DB_ID": "",
    "NOTION_CURATED_SESSIONS_DB_ID": "",
    "NOTION_GRANOLA_DB_ID": "granola-db",
}


def _gated_row(page_id="row-1", **props):
    base = {
        "Procesar con agente": True,
        "Estado": "Pendiente",
        "Estado agente": "Pendiente",
    }
    base.update(props)
    return {"page_id": page_id, "properties": base}


def _redis_mock():
    r = MagicMock()
    r.exists.return_value = False
    r.set.return_value = True
    return r


def _complete_classify_result():
    return {
        "ok": True,
        "result": {
            "classification": {
                "dominio": "Operacion",
                "tipo": "Reunión",
                "destino": "Tarea",
                "resumen": "Resumen corto valido.",
            }
        },
    }


class TestV2FlagParsing:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_explicit_truthy_enables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_V2_CLASSIFY": value}, clear=False):
            assert _v2_classify_enabled() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "junk", "enable", "si"])
    def test_everything_else_disables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_V2_CLASSIFY": value}, clear=False):
            assert _v2_classify_enabled() is False

    def test_absent_flag_disables(self, monkeypatch):
        monkeypatch.delenv("NOTION_POLLER_ENABLE_V2_CLASSIFY", raising=False)
        assert _v2_classify_enabled() is False


class TestV2DefaultOffInDoPoll:
    def _run_do_poll(self, wc, env_extra):
        queue = MagicMock()
        scheduler = MagicMock()
        r = _redis_mock()
        r.get.return_value = "2026-07-17T09:00:00+00:00"
        env = dict(_P2A_BASE_ENV)
        env.update(env_extra)
        with patch.dict("os.environ", env, clear=False):
            _do_poll(wc, queue, r, scheduler)
        return r

    def test_flag_absent_no_granola_read_no_classify(self, monkeypatch, caplog):
        monkeypatch.delenv("NOTION_POLLER_ENABLE_V2_CLASSIFY", raising=False)
        _reset_v2_disabled_log()
        wc = MagicMock()
        wc.notion_poll_comments.return_value = {"ok": True, "result": {"comments": []}}
        with caplog.at_level("INFO", logger="dispatcher.notion_poller"):
            self._run_do_poll(wc, {})
        # No wc.run at all: review targets empty AND granola scan disabled.
        assert wc.run.call_count == 0
        assert "V2 classify scan disabled" in caplog.text

    def test_flag_false_zero_query_zero_classify(self):
        wc = MagicMock()
        wc.notion_poll_comments.return_value = {"ok": True, "result": {"comments": []}}
        self._run_do_poll(wc, {"NOTION_POLLER_ENABLE_V2_CLASSIFY": "false"})
        for call in wc.run.call_args_list:
            task = call.args[0] if call.args else call.kwargs.get("task", "")
            assert task != "granola.classify_raw"
            assert task != "notion.read_database"

    @patch("dispatcher.notion_poller.handle_smart_reply")
    def test_control_room_still_processed_with_v2_off(self, mock_smart):
        wc = MagicMock()
        wc.notion_poll_comments.return_value = {
            "ok": True,
            "result": {
                "comments": [
                    {
                        "id": "c-p2a",
                        "created_time": "2026-07-17T10:00:00.000Z",
                        "created_by": "user-x",
                        "text": "hola necesito ayuda con un reporte",
                    }
                ]
            },
        }
        self._run_do_poll(wc, {"NOTION_POLLER_ENABLE_V2_CLASSIFY": "false"})
        mock_smart.assert_called_once()

    def test_p11b_rows_never_touched_with_flag_off(self):
        """Regression: with the flag off the Granola DB is never even read,
        so no P1.1b raw row can be scanned/classified/marked."""
        wc = MagicMock()
        wc.notion_poll_comments.return_value = {"ok": True, "result": {"comments": []}}
        r = self._run_do_poll(wc, {"NOTION_POLLER_ENABLE_V2_CLASSIFY": "0"})
        assert wc.run.call_count == 0
        for call in r.set.call_args_list:
            key = call.args[0] if call.args else ""
            assert not str(key).startswith("umbral:notion_poller:classified:")

    def test_classify_exception_does_not_break_cycle(self):
        """With the flag ON, a scan blow-up must not stop the general cycle."""
        wc = MagicMock()
        wc.notion_poll_comments.return_value = {"ok": True, "result": {"comments": []}}
        wc.run.side_effect = RuntimeError("granola read exploded")
        r = self._run_do_poll(wc, {"NOTION_POLLER_ENABLE_V2_CLASSIFY": "true"})
        # last_ts checkpoint logic still ran (cycle completed).
        assert r.get.called


class TestV2RowEligibility:
    def test_gate_unticked_skips(self):
        ok, reason = _v2_row_eligible(_gated_row(**{"Procesar con agente": False}))
        assert ok is False and reason == "gate_unticked"

    def test_gated_pending_is_eligible(self):
        ok, reason = _v2_row_eligible(_gated_row())
        assert ok is True

    @pytest.mark.parametrize("estado", ["Procesada", "Archivada", "Error"])
    def test_terminal_estado_skips(self, estado):
        ok, reason = _v2_row_eligible(_gated_row(Estado=estado))
        assert ok is False and reason == "estado_terminal"

    def test_archived_page_skips(self):
        row = _gated_row()
        row["archived"] = True
        ok, reason = _v2_row_eligible(row)
        assert ok is False and reason == "archived"

    def test_estado_agente_procesada_skips(self):
        ok, reason = _v2_row_eligible(_gated_row(**{"Estado agente": "Procesada"}))
        assert ok is False and reason == "estado_agente_not_pending"

    def test_revision_requerida_needs_reprocesar(self):
        ok, _ = _v2_row_eligible(_gated_row(**{"Estado agente": "Revision requerida"}))
        assert ok is False
        ok, _ = _v2_row_eligible(
            _gated_row(**{"Estado agente": "Revision requerida", "Reprocesar tras revisión": True})
        )
        assert ok is True

    def test_already_classified_fields_skip(self):
        ok, reason = _v2_row_eligible(
            _gated_row(
                **{
                    "Dominio propuesto": "Operacion",
                    "Tipo propuesto": "Reunión",
                    "Destino canonico": "Tarea",
                    "Resumen agente": "ya clasificada",
                }
            )
        )
        assert ok is False and reason == "already_classified"


class TestV2StrictValidation:
    def test_complete_result_is_success(self):
        ok, _ = _classification_result_complete(_complete_classify_result())
        assert ok is True

    @pytest.mark.parametrize(
        "result",
        [
            None,
            {},
            {"error": "LLM call failed: GOOGLE_API_KEY not configured"},
            {"ok": True, "result": {"classification": {}}},
            {"ok": True, "result": {"classification": {"dominio": "Operacion"}}},
            {"ok": True, "result": {"classification": {
                "dominio": "?", "tipo": "?", "destino": "?", "resumen": "?"}}},
            {"ok": True, "result": {"classification": {
                "dominio": "Operacion", "tipo": "Reunión", "destino": "Tarea", "resumen": ""}}},
            {"ok": True, "result": {"error": "boom", "classification": {
                "dominio": "Operacion", "tipo": "Reunión", "destino": "Tarea", "resumen": "x"}}},
        ],
    )
    def test_incomplete_or_error_is_failure(self, result):
        ok, reason = _classification_result_complete(result)
        assert ok is False
        assert reason


class TestV2ScanBehavior:
    def _run_scan(self, items, classify_result=None, classify_exc=None):
        wc = MagicMock()

        def _run(task, payload):
            if task == "notion.read_database":
                return {"ok": True, "result": {"items": items}}
            if task == "granola.classify_raw":
                if classify_exc:
                    raise classify_exc
                return classify_result
            raise AssertionError(f"unexpected task {task}")

        wc.run.side_effect = _run
        r = _redis_mock()
        with patch.dict("os.environ", {"NOTION_GRANOLA_DB_ID": "granola-db"}, clear=False):
            _classify_pending_granola_pages(wc, r)
        return wc, r

    def _classify_calls(self, wc):
        return [c for c in wc.run.call_args_list if c.args and c.args[0] == "granola.classify_raw"]

    def test_ungated_rows_never_classified(self):
        wc, r = self._run_scan([_gated_row(**{"Procesar con agente": False})])
        assert self._classify_calls(wc) == []
        r.set.assert_not_called()

    def test_gated_pending_row_is_classified_and_checkpointed(self):
        wc, r = self._run_scan([_gated_row()], classify_result=_complete_classify_result())
        assert len(self._classify_calls(wc)) == 1
        r.set.assert_called_once_with(
            "umbral:notion_poller:classified:row-1", "1", ex=CLASSIFIED_TTL_SEC
        )

    @pytest.mark.parametrize(
        "bad_result",
        [
            {"error": "no provider"},
            {"ok": True, "result": {"classification": {}}},
            {"ok": True, "result": {"classification": {
                "dominio": "?", "tipo": "?", "destino": "?", "resumen": "?"}}},
        ],
    )
    def test_incomplete_result_no_success_checkpoint(self, bad_result, caplog):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            wc, r = self._run_scan([_gated_row()], classify_result=bad_result)
        # Only the fail/backoff key — NEVER the classified key.
        assert r.set.call_count == 1
        key = r.set.call_args.args[0]
        assert key.startswith("umbral:notion_poller:classify_fail:")
        assert "did NOT classify" in caplog.text

    def test_classify_exception_sets_backoff_not_success(self):
        wc, r = self._run_scan([_gated_row()], classify_exc=RuntimeError("timeout"))
        assert r.set.call_count == 1
        assert r.set.call_args.args[0].startswith("umbral:notion_poller:classify_fail:")

    def test_metrics_line_logged(self, caplog):
        items = [_gated_row("row-a"), _gated_row("row-b", **{"Procesar con agente": False})]
        with caplog.at_level("INFO", logger="dispatcher.notion_poller"):
            self._run_scan(items, classify_result=_complete_classify_result())
        assert (
            "v2_classify_enabled=True scanned=2 eligible=1 classified=1 skipped_gate=1 errors=0"
            in caplog.text
        )


# ---------------------------------------------------------------------------
# P2.1: promote scan isolation — default-off flag, Aprobar/promovido_a gate,
# idempotent hand-off to editorial.promote_shortlist_approval (Worker/core).
# See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.1.
# ---------------------------------------------------------------------------

from dispatcher.notion_poller import (  # noqa: E402
    PROMOTE_FAIL_TTL_SEC,
    PROMOTED_TTL_SEC,
    _promote_approved_shortlist_rows,
    _promote_enabled,
    _reset_promote_disabled_log,
)


def _approved_row(page_id="shortlist-1", **props):
    base = {
        "Resultado revisión": "Aprobar",
        "promovido_a": [],
    }
    base.update(props)
    return {"page_id": page_id, "properties": base}


class TestPromoteFlagParsing:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_explicit_truthy_enables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_PROMOTE": value}, clear=False):
            assert _promote_enabled() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "junk", "enable", "si"])
    def test_everything_else_disables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_PROMOTE": value}, clear=False):
            assert _promote_enabled() is False

    def test_absent_env_disables(self, monkeypatch):
        monkeypatch.delenv("NOTION_POLLER_ENABLE_PROMOTE", raising=False)
        assert _promote_enabled() is False


class TestPromoteScanBehavior:
    def _run_scan(self, items, promote_result=None, promote_exc=None, shortlist_ds_id="shortlist-ds"):
        wc = MagicMock()

        def _run(task, payload):
            if task == "notion.read_database":
                return {"ok": True, "result": {"items": items}}
            if task == "editorial.promote_shortlist_approval":
                if promote_exc:
                    raise promote_exc
                return promote_result
            raise AssertionError(f"unexpected task {task}")

        wc.run.side_effect = _run
        r = _redis_mock()
        with patch.dict("os.environ", {"NOTION_SHORTLIST_DS_ID": shortlist_ds_id or ""}, clear=False):
            _promote_approved_shortlist_rows(wc, r)
        return wc, r

    def _promote_calls(self, wc):
        return [
            c for c in wc.run.call_args_list if c.args and c.args[0] == "editorial.promote_shortlist_approval"
        ]

    def test_no_shortlist_ds_id_configured_is_noop(self):
        wc, r = self._run_scan([_approved_row()], shortlist_ds_id="")
        assert wc.run.call_count == 0
        r.set.assert_not_called()

    def test_pending_rows_are_never_promoted(self):
        wc, r = self._run_scan([_approved_row(**{"Resultado revisión": "Pendiente"})])
        assert self._promote_calls(wc) == []
        r.set.assert_not_called()

    def test_already_promoted_rows_are_skipped(self):
        wc, r = self._run_scan([_approved_row(promovido_a=["pub-1"])])
        assert self._promote_calls(wc) == []
        r.set.assert_not_called()

    def test_approved_unpromoted_row_is_promoted_and_checkpointed(self):
        wc, r = self._run_scan(
            [_approved_row()],
            promote_result={"ok": True, "created": True, "publicacion_page_id": "pub-new"},
        )
        assert len(self._promote_calls(wc)) == 1
        assert self._promote_calls(wc)[0].args[1] == {"shortlist_page_id": "shortlist-1"}
        r.set.assert_called_once_with(
            "umbral:notion_poller:promoted:shortlist-1", "1", ex=PROMOTED_TTL_SEC
        )

    def test_worker_reported_failure_sets_backoff_not_success(self, caplog):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            wc, r = self._run_scan(
                [_approved_row()],
                promote_result={"ok": False, "error": "not_approved"},
            )
        assert r.set.call_count == 1
        key = r.set.call_args.args[0]
        assert key.startswith("umbral:notion_poller:promote_fail:")
        assert r.set.call_args.kwargs == {"ex": PROMOTE_FAIL_TTL_SEC}
        assert "did NOT promote" in caplog.text

    def test_promote_call_exception_sets_backoff(self):
        wc, r = self._run_scan([_approved_row()], promote_exc=RuntimeError("worker unreachable"))
        assert r.set.call_count == 1
        assert r.set.call_args.args[0].startswith("umbral:notion_poller:promote_fail:")

    def test_already_checkpointed_row_is_skipped_without_recall(self):
        wc = MagicMock()
        wc.run.side_effect = lambda task, payload: (
            {"ok": True, "result": {"items": [_approved_row()]}}
            if task == "notion.read_database"
            else (_ for _ in ()).throw(AssertionError("should not call promote"))
        )
        r = _redis_mock()
        r.exists.return_value = True
        with patch.dict("os.environ", {"NOTION_SHORTLIST_DS_ID": "shortlist-ds"}, clear=False):
            _promote_approved_shortlist_rows(wc, r)
        assert self._promote_calls(wc) == []

    def test_batch_limit_caps_promotions_per_cycle(self):
        rows = [_approved_row(page_id=f"row-{i}") for i in range(5)]
        wc, r = self._run_scan(
            rows,
            promote_result={"ok": True, "created": True, "publicacion_page_id": "pub-new"},
        )
        assert len(self._promote_calls(wc)) == 3  # PROMOTE_BATCH_LIMIT

    def test_disabled_log_helper_resets_without_error(self):
        _reset_promote_disabled_log()


# ---------------------------------------------------------------------------
# P2.2 — Magnific scan (Publicaciones rows promoted by P2.1 -> 5 image variants)
# See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.2.
# ---------------------------------------------------------------------------

from dispatcher.notion_poller import (  # noqa: E402
    MAGNIFIC_CALL_TIMEOUT_SEC,
    MAGNIFIC_FAIL_TTL_SEC,
    MAGNIFIC_TTL_SEC,
    _generate_magnific_variants_for_pending_rows,
    _magnific_enabled,
    _reset_magnific_disabled_log,
)


def _promoted_row(page_id="pub-1", **props):
    base = {
        "origen_alternativa": ["shortlist-1"],
        "Estado imagen": "No aplica",
    }
    base.update(props)
    return {"page_id": page_id, "properties": base}


class TestMagnificFlagParsing:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_explicit_truthy_enables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_MAGNIFIC": value}, clear=False):
            assert _magnific_enabled() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "junk", "enable", "si"])
    def test_everything_else_disables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_MAGNIFIC": value}, clear=False):
            assert _magnific_enabled() is False

    def test_absent_env_disables(self, monkeypatch):
        monkeypatch.delenv("NOTION_POLLER_ENABLE_MAGNIFIC", raising=False)
        assert _magnific_enabled() is False


class TestMagnificScanBehavior:
    def _run_scan(self, items, magnific_result=None, magnific_exc=None, publicaciones_db_id="pub-db"):
        wc = MagicMock()

        def _run(task, payload, timeout=None):
            if task == "notion.read_database":
                return {"ok": True, "result": {"items": items}}
            if task == "magnific.generate_variants":
                if magnific_exc:
                    raise magnific_exc
                return magnific_result
            raise AssertionError(f"unexpected task {task}")

        wc.run.side_effect = _run
        r = _redis_mock()
        with patch.dict("os.environ", {"NOTION_PUBLICACIONES_DB_ID": publicaciones_db_id or ""}, clear=False):
            _generate_magnific_variants_for_pending_rows(wc, r)
        return wc, r

    def _magnific_calls(self, wc):
        return [
            c for c in wc.run.call_args_list if c.args and c.args[0] == "magnific.generate_variants"
        ]

    def test_no_publicaciones_db_id_configured_is_noop(self):
        wc, r = self._run_scan([_promoted_row()], publicaciones_db_id="")
        assert wc.run.call_count == 0
        r.set.assert_not_called()

    def test_rows_without_origen_alternativa_are_never_generated(self):
        wc, r = self._run_scan([_promoted_row(**{"origen_alternativa": []})])
        assert self._magnific_calls(wc) == []
        r.set.assert_not_called()

    @pytest.mark.parametrize("estado", ["Listo para selección", "Seleccionada", "Generando"])
    def test_already_done_states_are_skipped(self, estado):
        wc, r = self._run_scan([_promoted_row(**{"Estado imagen": estado})])
        assert self._magnific_calls(wc) == []
        r.set.assert_not_called()

    def test_error_state_is_never_auto_retried_by_the_scan(self):
        """Regression guard: Error must require an explicit human/system
        action to leave (e.g. Selección imagen = Regenerar -> Regeneración
        pedida), never the automatic scan on its flat 30-min backoff — else a
        persistently-failing prompt burns credits forever."""
        wc, r = self._run_scan([_promoted_row(**{"Estado imagen": "Error"})])
        assert self._magnific_calls(wc) == []
        r.set.assert_not_called()

    def test_regeneracion_pedida_is_scan_eligible(self):
        wc, r = self._run_scan(
            [_promoted_row(**{"Estado imagen": "Regeneración pedida"})],
            magnific_result={"ok": True, "generated": 5, "requested": 5},
        )
        assert len(self._magnific_calls(wc)) == 1

    def test_eligible_row_is_generated_and_checkpointed(self):
        wc, r = self._run_scan(
            [_promoted_row()],
            magnific_result={"ok": True, "generated": 5, "requested": 5},
        )
        calls = self._magnific_calls(wc)
        assert len(calls) == 1
        assert calls[0].args[1] == {"publicacion_page_id": "pub-1"}
        assert calls[0].kwargs["timeout"] == MAGNIFIC_CALL_TIMEOUT_SEC
        r.set.assert_called_once_with(
            "umbral:notion_poller:magnific:pub-1", "1", ex=MAGNIFIC_TTL_SEC
        )

    def test_handler_noop_skip_does_not_checkpoint_as_generated(self):
        wc, r = self._run_scan(
            [_promoted_row()],
            magnific_result={"ok": True, "skipped": True, "reason": "in_progress"},
        )
        assert len(self._magnific_calls(wc)) == 1
        r.set.assert_not_called()

    def test_worker_reported_failure_sets_backoff_not_success(self, caplog):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            wc, r = self._run_scan(
                [_promoted_row()],
                magnific_result={"ok": False, "error": "estado_imagen_not_eligible"},
            )
        assert r.set.call_count == 1
        key = r.set.call_args.args[0]
        assert key.startswith("umbral:notion_poller:magnific_fail:")
        assert r.set.call_args.kwargs == {"ex": MAGNIFIC_FAIL_TTL_SEC}
        assert "did NOT generate" in caplog.text

    def test_magnific_call_exception_sets_backoff(self):
        wc, r = self._run_scan([_promoted_row()], magnific_exc=RuntimeError("worker unreachable"))
        assert r.set.call_count == 1
        assert r.set.call_args.args[0].startswith("umbral:notion_poller:magnific_fail:")

    def test_already_checkpointed_row_is_skipped_without_recall(self):
        wc = MagicMock()
        wc.run.side_effect = lambda task, payload, timeout=None: (
            {"ok": True, "result": {"items": [_promoted_row()]}}
            if task == "notion.read_database"
            else (_ for _ in ()).throw(AssertionError("should not call magnific"))
        )
        r = _redis_mock()
        r.exists.return_value = True
        with patch.dict("os.environ", {"NOTION_PUBLICACIONES_DB_ID": "pub-db"}, clear=False):
            _generate_magnific_variants_for_pending_rows(wc, r)
        assert self._magnific_calls(wc) == []

    def test_batch_limit_caps_generations_per_cycle(self):
        rows = [_promoted_row(page_id=f"row-{i}") for i in range(5)]
        wc, r = self._run_scan(
            rows,
            magnific_result={"ok": True, "generated": 5, "requested": 5},
        )
        assert len(self._magnific_calls(wc)) == 1  # MAGNIFIC_BATCH_LIMIT

    def test_disabled_log_helper_resets_without_error(self):
        _reset_magnific_disabled_log()


# ---------------------------------------------------------------------------
# P2.4: dedupe scan isolation — default-off flag, dedupe_status-empty gate
# (independent of Resultado revisión), idempotent hand-off to
# editorial.dedupe_candidate_vs_backlog (Worker/core).
# See docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.4.
# ---------------------------------------------------------------------------

from dispatcher.notion_poller import (  # noqa: E402
    DEDUPE_FAIL_TTL_SEC,
    DEDUPED_TTL_SEC,
    _dedupe_enabled,
    _dedupe_pending_shortlist_rows,
    _reset_dedupe_disabled_log,
)


def _pending_dedupe_row(page_id="shortlist-1", **props):
    base = {"dedupe_status": ""}
    base.update(props)
    return {"page_id": page_id, "properties": base}


class TestDedupeFlagParsing:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_explicit_truthy_enables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_DEDUPE": value}, clear=False):
            assert _dedupe_enabled() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "junk", "enable", "si"])
    def test_everything_else_disables(self, value):
        with patch.dict("os.environ", {"NOTION_POLLER_ENABLE_DEDUPE": value}, clear=False):
            assert _dedupe_enabled() is False

    def test_absent_env_disables(self, monkeypatch):
        monkeypatch.delenv("NOTION_POLLER_ENABLE_DEDUPE", raising=False)
        assert _dedupe_enabled() is False


class TestDedupeScanBehavior:
    def _run_scan(self, items, dedupe_result=None, dedupe_exc=None, shortlist_ds_id="shortlist-ds"):
        wc = MagicMock()

        def _run(task, payload):
            if task == "notion.read_database":
                return {"ok": True, "result": {"items": items}}
            if task == "editorial.dedupe_candidate_vs_backlog":
                if dedupe_exc:
                    raise dedupe_exc
                return dedupe_result
            raise AssertionError(f"unexpected task {task}")

        wc.run.side_effect = _run
        r = _redis_mock()
        with patch.dict("os.environ", {"NOTION_SHORTLIST_DS_ID": shortlist_ds_id or ""}, clear=False):
            _dedupe_pending_shortlist_rows(wc, r)
        return wc, r

    def _dedupe_calls(self, wc):
        return [
            c for c in wc.run.call_args_list if c.args and c.args[0] == "editorial.dedupe_candidate_vs_backlog"
        ]

    def test_no_shortlist_ds_id_configured_is_noop(self):
        wc, r = self._run_scan([_pending_dedupe_row()], shortlist_ds_id="")
        assert wc.run.call_count == 0
        r.set.assert_not_called()

    def test_already_evaluated_rows_are_skipped(self):
        wc, r = self._run_scan([_pending_dedupe_row(dedupe_status="nuevo")])
        assert self._dedupe_calls(wc) == []
        r.set.assert_not_called()

    def test_archived_rows_are_skipped(self):
        row = _pending_dedupe_row()
        row["archived"] = True
        wc, r = self._run_scan([row])
        assert self._dedupe_calls(wc) == []
        r.set.assert_not_called()

    def test_pending_row_is_evaluated_regardless_of_resultado_revision(self):
        # Dedupe must not depend on Resultado revisión — it runs before/
        # alongside HITL-1, not only after Aprobar.
        wc, r = self._run_scan(
            [_pending_dedupe_row(**{"Resultado revisión": "Pendiente"})],
            dedupe_result={"ok": True, "dedupe_status": "nuevo"},
        )
        assert len(self._dedupe_calls(wc)) == 1

    def test_pending_row_is_evaluated_and_checkpointed(self):
        wc, r = self._run_scan(
            [_pending_dedupe_row()],
            dedupe_result={"ok": True, "dedupe_status": "nuevo"},
        )
        assert len(self._dedupe_calls(wc)) == 1
        assert self._dedupe_calls(wc)[0].args[1] == {"shortlist_page_id": "shortlist-1"}
        r.set.assert_called_once_with(
            "umbral:notion_poller:deduped:shortlist-1", "1", ex=DEDUPED_TTL_SEC
        )

    def test_worker_reported_failure_sets_backoff_not_success(self, caplog):
        with caplog.at_level("WARNING", logger="dispatcher.notion_poller"):
            wc, r = self._run_scan(
                [_pending_dedupe_row()],
                dedupe_result={"ok": False, "error": "some_error"},
            )
        assert r.set.call_count == 1
        key = r.set.call_args.args[0]
        assert key.startswith("umbral:notion_poller:dedupe_fail:")
        assert r.set.call_args.kwargs == {"ex": DEDUPE_FAIL_TTL_SEC}
        assert "did NOT evaluate" in caplog.text

    def test_dedupe_call_exception_sets_backoff(self):
        wc, r = self._run_scan([_pending_dedupe_row()], dedupe_exc=RuntimeError("worker unreachable"))
        assert r.set.call_count == 1
        assert r.set.call_args.args[0].startswith("umbral:notion_poller:dedupe_fail:")

    def test_already_checkpointed_row_is_skipped_without_recall(self):
        wc = MagicMock()
        wc.run.side_effect = lambda task, payload: (
            {"ok": True, "result": {"items": [_pending_dedupe_row()]}}
            if task == "notion.read_database"
            else (_ for _ in ()).throw(AssertionError("should not call dedupe"))
        )
        r = _redis_mock()
        r.exists.return_value = True
        with patch.dict("os.environ", {"NOTION_SHORTLIST_DS_ID": "shortlist-ds"}, clear=False):
            _dedupe_pending_shortlist_rows(wc, r)
        assert self._dedupe_calls(wc) == []

    def test_batch_limit_caps_evaluations_per_cycle(self):
        rows = [_pending_dedupe_row(page_id=f"row-{i}") for i in range(5)]
        wc, r = self._run_scan(
            rows,
            dedupe_result={"ok": True, "dedupe_status": "nuevo"},
        )
        assert len(self._dedupe_calls(wc)) == 3  # DEDUPE_BATCH_LIMIT

    def test_disabled_log_helper_resets_without_error(self):
        _reset_dedupe_disabled_log()
