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
                    {"page_id": "deliverable-1"},
                    {"page_id": "deliverable-2"},
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
            "NOTION_CONTROL_ROOM_PAGE_ID": "control-room-page",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert [comment["id"] for comment in comments] == ["c-1", "c-2", "c-3"]
    assert comments[1]["page_id"] == "deliverable-1"
    assert comments[1]["page_kind"] == "deliverable"
    assert comments[2]["page_id"] == "project-1"
    assert comments[2]["page_kind"] == "project"
    expected_calls = [
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": None},
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
    assert comments[1]["page_id"] == "session-1"
    assert comments[1]["page_kind"] == "session_capitalizable"
    expected_calls = [
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": None},
        {"since": "2026-03-16T20:55:00+00:00", "limit": 20, "page_id": "session-1"},
    ]
    assert [call.kwargs for call in wc.notion_poll_comments.call_args_list] == expected_calls


def test_collect_candidate_comments_falls_back_when_deliverable_filter_fails():
    wc = MagicMock()
    wc.run.side_effect = [
        RuntimeError("500 from deliverables filter"),
        {"ok": True, "result": {"items": [{"page_id": "deliverable-1"}]}},
        {"ok": True, "result": {"items": []}},
    ]
    wc.notion_poll_comments.side_effect = [
        {"ok": True, "result": {"comments": []}},
        {"ok": True, "result": {"comments": []}},
    ]

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert comments == []
    deliverable_calls = [call.args[1] for call in wc.run.call_args_list[:2]]
    assert deliverable_calls[0]["filter"]["or"][0]["property"] == "Estado revision"
    assert "filter" not in deliverable_calls[1]


def test_collect_candidate_comments_continues_when_session_target_resolution_fails():
    wc = MagicMock()
    wc.run.side_effect = [
        {"ok": True, "result": {"items": []}},
        {"ok": True, "result": {"items": []}},
        RuntimeError("session db unavailable"),
    ]
    wc.notion_poll_comments.return_value = {
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
    }

    with patch.dict(
        "os.environ",
        {
            "NOTION_DELIVERABLES_DB_ID": "deliverables-db",
            "NOTION_PROJECTS_DB_ID": "projects-db",
            "NOTION_CURATED_SESSIONS_DB_ID": "curated-db",
            "NOTION_POLL_OVERLAP_SEC": "300",
        },
        clear=False,
    ):
        comments = _collect_candidate_comments(wc, "2026-03-16T21:00:00+00:00", 20)

    assert [comment["id"] for comment in comments] == ["c-1"]
    wc.notion_poll_comments.assert_called_once_with(
        since="2026-03-16T20:55:00+00:00",
        limit=20,
        page_id=None,
    )
