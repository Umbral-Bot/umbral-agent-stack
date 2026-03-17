from unittest.mock import MagicMock, patch

from dispatcher.notion_poller import _do_poll, _extract_poll_comments_result


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

    _do_poll(wc, queue, r, scheduler)

    wc.notion_poll_comments.assert_called_once_with(
        since="2026-03-16T20:00:00+00:00",
        limit=20,
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

    _do_poll(wc, queue, r, scheduler)

    mock_handle_smart_reply.assert_called_once()
    r.set.assert_any_call(
        "umbral:notion_poller:last_ts",
        "2026-03-16T21:00:00+00:00",
    )


@patch("dispatcher.notion_poller.handle_smart_reply")
def test_do_poll_skips_already_processed_comment(mock_handle_smart_reply):
    wc = MagicMock()
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

    _do_poll(wc, queue, r, scheduler)

    mock_handle_smart_reply.assert_not_called()
    r.set.assert_any_call(
        "umbral:notion_poller:last_ts",
        "2026-03-16T21:00:00+00:00",
    )
