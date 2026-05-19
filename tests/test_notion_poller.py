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
