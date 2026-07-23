"""
Tests for magnific.generate_variants (P2.2 — Magnific 5 alternativas de
imagen). See worker/tasks/magnific.py and
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.2.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest


def _title_prop(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def _rich_text_prop(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]}


def _select_prop(name):
    return {"type": "select", "select": {"name": name} if name else None}


def _publicacion_page(
    page_id="pub-1",
    titulo="Un ángulo interesante",
    premisa="Tesis condensada.",
    visual_brief="",
    estado_imagen="No aplica",
):
    return {
        "id": page_id,
        "properties": {
            "Título": _title_prop(titulo),
            "Premisa": _rich_text_prop(premisa),
            "Visual brief": _rich_text_prop(visual_brief),
            "Estado imagen": _select_prop(estado_imagen),
        },
    }


def _mystic_submit_response(task_id):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"task_id": task_id, "status": "CREATED", "generated": []}}
    return resp


def _mystic_poll_completed_response(url):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"status": "COMPLETED", "generated": [url]}}
    return resp


def _mystic_poll_failed_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"status": "FAILED", "error": "nsfw_filtered"}}
    return resp


def _patch_httpx_client(post_side_effect, get_side_effect):
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.post.side_effect = post_side_effect
    http_client.get.side_effect = get_side_effect
    return patch("worker.tasks.magnific.httpx.Client", return_value=http_client), http_client


def test_requires_publicacion_page_id():
    from worker.tasks.magnific import handle_magnific_generate_variants

    result = handle_magnific_generate_variants({})
    assert result["ok"] is False
    assert "publicacion_page_id" in result["error"]


def test_invalid_count_rejected():
    from worker.tasks.magnific import handle_magnific_generate_variants

    result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1", "count": 6})
    assert result["ok"] is False
    assert "count" in result["error"]


def test_no_api_key_configured_blocks_before_any_write():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = None
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="No aplica")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is False
    assert "MAGNIFIC_API_KEY" in result["error"]
    mock_nc.update_page_properties.assert_not_called()


def test_in_progress_is_idempotent_noop():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Generando")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["reason"] == "in_progress"
    mock_nc.update_page_properties.assert_not_called()


@pytest.mark.parametrize("estado", ["Listo para selección", "Seleccionada"])
def test_already_generated_is_idempotent_noop(estado):
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen=estado)

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["already_generated"] is True
    mock_nc.update_page_properties.assert_not_called()


def test_unrecognized_estado_imagen_blocks():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Un estado inventado")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is False
    assert "estado_imagen_not_eligible" in result["error"]
    mock_nc.update_page_properties.assert_not_called()


def test_dry_run_previews_without_writes_or_http_calls():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_httpx_client_cls:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            titulo="IFC 4.3 en infraestructura lineal", premisa="El hueco es proceso, no formato."
        )

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1", "dry_run": True})

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["would_generate"] is True
    assert result["count"] == 5
    assert result["aspect_ratio"] == "classic_4_3"
    assert "IFC 4.3 en infraestructura lineal" in result["prompt"]
    assert "Sin personas foto-real" in result["prompt"]
    mock_nc.update_page_properties.assert_not_called()
    mock_httpx_client_cls.assert_not_called()


def test_regeneracion_pedida_is_eligible():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Regeneración pedida")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1", "dry_run": True})

    assert result["ok"] is True
    assert result["would_generate"] is True


def test_generando_write_failure_aborts_before_any_magnific_call():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_httpx_client_cls:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="No aplica")
        mock_nc.update_page_properties.side_effect = RuntimeError("Notion API error (500)")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is False
    assert "interim" in result["error"].lower()
    mock_httpx_client_cls.assert_not_called()


def test_generates_five_variants_and_writes_notion():
    from worker.tasks.magnific import handle_magnific_generate_variants

    urls = [f"https://cdn.magnific.com/img-{i}.png" for i in range(1, 6)]
    post_effects = [_mystic_submit_response(f"task-{i}") for i in range(1, 6)]
    get_effects = [_mystic_poll_completed_response(urls[i - 1]) for i in range(1, 6)]
    patcher, http_client = _patch_httpx_client(post_effects, get_effects)

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Pendiente generación")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is True
    assert result["generated"] == 5
    assert result["requested"] == 5
    assert result["urls"] == urls
    assert result["estado_imagen"] == "Listo para selección"

    assert http_client.post.call_count == 5
    assert http_client.get.call_count == 5
    assert mock_nc.update_page_properties.call_count == 2  # interim "Generando" + final

    interim_call, final_call = mock_nc.update_page_properties.call_args_list
    interim_props = interim_call.kwargs["properties"]
    assert interim_props["Estado imagen"] == {"select": {"name": "Generando"}}
    assert interim_props["imagen_error"] == {"rich_text": []}
    # The interim write must NOT clear any imagen_alt_*_url — see
    # test_interim_write_never_clears_existing_urls for the destructive-retry
    # regression this guards against.
    assert not any(k.startswith("imagen_alt_") for k in interim_props)

    final_props = final_call.kwargs["properties"]
    assert final_props["Estado imagen"] == {"select": {"name": "Listo para selección"}}
    assert final_props["imagen_cantidad"] == {"number": 5}
    for i, url in enumerate(urls, start=1):
        assert final_props[f"imagen_alt_{i}_url"] == {"url": url}


def test_interim_write_never_clears_existing_urls():
    """Regression guard: a retry that fails immediately must not destroy
    URLs a *previous* run already paid Magnific credits to produce. The
    interim 'Generando' write must not touch imagen_alt_*_url at all, and a
    failed run must only write the slots it itself produced."""
    from worker.tasks.magnific import handle_magnific_generate_variants

    post_effects = [_mystic_submit_response("task-1")]
    get_effects = [_mystic_poll_failed_response()]
    patcher, http_client = _patch_httpx_client(post_effects, get_effects)

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        # Simulates a row that already has 2 good URLs from a prior partial
        # run before landing in Error (imagen_cantidad=2 in Notion already).
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Error")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1", "count": 1})

    assert result["ok"] is False
    interim_call, final_call = mock_nc.update_page_properties.call_args_list
    assert not any(k.startswith("imagen_alt_") for k in interim_call.kwargs["properties"])
    # Only alt_1 (what this run attempted) may appear; it must not be present
    # at all since this run produced zero successful URLs — nothing about
    # alt_2..5 (a hypothetical prior success) is touched either way.
    assert not any(k.startswith("imagen_alt_") for k in final_call.kwargs["properties"])


def test_partial_failure_writes_error_state_not_listo():
    from worker.tasks.magnific import handle_magnific_generate_variants

    urls = [f"https://cdn.magnific.com/img-{i}.png" for i in (1, 2)]
    post_effects = [
        _mystic_submit_response("task-1"),
        _mystic_submit_response("task-2"),
        _mystic_submit_response("task-3"),
    ]
    get_effects = [
        _mystic_poll_completed_response(urls[0]),
        _mystic_poll_completed_response(urls[1]),
        _mystic_poll_failed_response(),
    ]
    patcher, http_client = _patch_httpx_client(post_effects, get_effects)

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="No aplica")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is False
    assert "alt_3" in result["error"]
    assert result["generated"] == 2

    interim_call, final_call = mock_nc.update_page_properties.call_args_list
    final_props = final_call.kwargs["properties"]
    assert final_props["Estado imagen"] == {"select": {"name": "Error"}}
    assert final_props["imagen_alt_1_url"] == {"url": urls[0]}
    assert final_props["imagen_alt_2_url"] == {"url": urls[1]}
    assert "imagen_alt_3_url" not in final_props
    assert final_props["imagen_cantidad"] == {"number": 2}
    assert "alt_3" in final_props["imagen_error"]["rich_text"][0]["text"]["content"]


def test_app_magnific_com_url_is_rejected_as_failure():
    from worker.tasks.magnific import handle_magnific_generate_variants

    post_effects = [_mystic_submit_response("task-1")]
    get_effects = [_mystic_poll_completed_response("https://app.magnific.com/creations/abc")]
    patcher, http_client = _patch_httpx_client(post_effects, get_effects)

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="No aplica")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1", "count": 1})

    assert result["ok"] is False
    assert "alt_1" in result["error"]
    assert result["generated"] == 0


# ---------------------------------------------------------------------------
# Low-level Mystic client behavior (submit/poll error paths)
# ---------------------------------------------------------------------------


def test_submit_missing_task_id_raises():
    from worker.tasks.magnific import _submit_mystic

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"status": "CREATED"}}  # no task_id
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.post.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match="missing task_id"):
            _submit_mystic("a prompt", "classic_4_3", "2k", "realism")


def test_submit_http_status_error_is_wrapped():
    from worker.tasks.magnific import _submit_mystic

    http_resp = httpx.Response(status_code=402, text="insufficient credits", request=httpx.Request("POST", "https://api.magnific.com/v1/ai/mystic"))
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError("payment required", request=http_resp.request, response=http_resp)
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.post.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match="submit error 402"):
            _submit_mystic("a prompt", "classic_4_3", "2k", "realism")


def test_poll_http_status_error_is_wrapped():
    from worker.tasks.magnific import _poll_mystic

    http_resp = httpx.Response(status_code=500, text="internal error", request=httpx.Request("GET", "https://api.magnific.com/v1/ai/mystic/task-1"))
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError("server error", request=http_resp.request, response=http_resp)
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.get.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match="poll error 500"):
            _poll_mystic("task-1")


def test_poll_exhausts_attempts_and_raises_with_elapsed_time():
    from worker.tasks.magnific import _poll_mystic

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"status": "IN_PROGRESS", "generated": []}}
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.get.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ), patch("worker.tasks.magnific.time.sleep", return_value=None), patch(
        "worker.tasks.magnific._MAX_POLL_ATTEMPTS", 3
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match="did not complete within"):
            _poll_mystic("task-x")

    assert http_client.get.call_count == 3


def test_poll_completed_without_generated_url_raises():
    from worker.tasks.magnific import _poll_mystic

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"status": "COMPLETED", "generated": []}}
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.get.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match="without a generated URL"):
            _poll_mystic("task-1")
