"""
Tests for magnific.generate_variants (P2.2 — Magnific 5 alternativas de
imagen). See worker/tasks/magnific.py and
docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md row P2.2.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest


FLASH_ENDPOINT = "https://api.magnific.com/v1/ai/text-to-image/nano-banana-pro-flash"
PRO_ENDPOINT = "https://api.magnific.com/v1/ai/text-to-image/nano-banana-pro"
MYSTIC_ENDPOINT = "https://api.magnific.com/v1/ai/mystic"


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
    seleccion_imagen="Pendiente",
):
    return {
        "id": page_id,
        "properties": {
            "Título": _title_prop(titulo),
            "Premisa": _rich_text_prop(premisa),
            "Visual brief": _rich_text_prop(visual_brief),
            "Estado imagen": _select_prop(estado_imagen),
            "Selección imagen": _select_prop(seleccion_imagen),
        },
    }


def _mystic_submit_response(task_id):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"task_id": task_id, "status": "CREATED", "generated": []}}
    return resp


def _mystic_poll_completed_response(url, task_id="task-1"):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "data": {"task_id": task_id, "status": "COMPLETED", "generated": [url]}
    }
    return resp


def _mystic_poll_failed_response(task_id="task-1"):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "data": {
            "task_id": task_id,
            "status": "FAILED",
            "generated": [],
            "error": "nsfw_filtered",
        }
    }
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


@pytest.mark.parametrize("count", [0, 6])
def test_invalid_count_rejected(count):
    from worker.tasks.magnific import handle_magnific_generate_variants

    result = handle_magnific_generate_variants(
        {"publicacion_page_id": "pub-1", "count": count}
    )
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
    assert result["model"] == "nano-banana-pro-flash"
    assert result["endpoint"] == FLASH_ENDPOINT
    assert result["aspect_ratio"] == "4:3"
    assert result["resolution"] == "2K"
    assert result["use_google_search_tool"] is False
    assert "IFC 4.3 en infraestructura lineal" in result["prompt"]
    assert "ilustración editorial isométrica no fotoreal" in result["prompt"]
    assert "SIN obra" in result["prompt"]
    assert "Contexto AECO real" not in result["prompt"]
    mock_nc.update_page_properties.assert_not_called()
    mock_httpx_client_cls.assert_not_called()


def test_visual_brief_yaml_uses_scene_and_avoid_without_metadata_in_prompt():
    from worker.tasks.magnific import handle_magnific_generate_variants

    visual_brief = """\
style: isometric-editorial
model: nano-banana-2
scene: >-
  Isometric openBIM data exchange with mint geometry over a navy background.
avoid:
  - photorealistic people
  - embedded typography
trace_id: trace-local
publication_id: shortlist-local
style_ref: null
vignette: T18
aspect_ratio: 4:3
resolution: 2K
"""
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_httpx_client_cls:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(visual_brief=visual_brief)

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["model"] == "nano-banana-pro-flash"
    assert result["endpoint"] == FLASH_ENDPOINT
    assert result["aspect_ratio"] == "4:3"
    assert result["resolution"] == "2K"
    assert result["prompt"].startswith("Isometric openBIM data exchange")
    assert "photorealistic people" in result["prompt"]
    assert "embedded typography" in result["prompt"]
    for metadata_key in (
        "style:",
        "model:",
        "scene:",
        "trace_id:",
        "publication_id:",
        "style_ref:",
        "vignette:",
        "aspect_ratio:",
        "resolution:",
    ):
        assert metadata_key not in result["prompt"]
    mock_nc.update_page_properties.assert_not_called()
    mock_httpx_client_cls.assert_not_called()


@pytest.mark.parametrize(
    ("alias", "expected_model", "expected_endpoint"),
    [
        ("nano-banana-2", "nano-banana-pro-flash", FLASH_ENDPOINT),
        ("nano-banana-2-flash", "nano-banana-pro-flash", FLASH_ENDPOINT),
        ("imagen-nano-banana-2-flash", "nano-banana-pro-flash", FLASH_ENDPOINT),
        ("nano-banana-pro-flash", "nano-banana-pro-flash", FLASH_ENDPOINT),
        ("nano-banana-pro", "nano-banana-pro", PRO_ENDPOINT),
        ("imagen-nano-banana-2", "nano-banana-pro", PRO_ENDPOINT),
        ("mystic", "realism", MYSTIC_ENDPOINT),
        ("realism", "realism", MYSTIC_ENDPOINT),
    ],
)
def test_model_aliases_select_the_documented_endpoint(alias, expected_model, expected_endpoint):
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page()

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True, "model": alias}
        )

    assert result["ok"] is True
    assert result["model"] == expected_model
    assert result["endpoint"] == expected_endpoint


def test_prompt_is_capped_at_flash_api_limit():
    from worker.tasks.magnific import handle_magnific_generate_variants

    visual_brief = f"scene: {'x' * 4000}\nmodel: nano-banana-2"
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(visual_brief=visual_brief)

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert 2 <= len(result["prompt"]) <= 3000


def test_long_scene_keeps_avoid_clause_inside_api_limit():
    from worker.tasks.magnific import handle_magnific_generate_variants

    visual_brief = f"scene: {'x' * 5000}\navoid: preserve-this-negative-constraint"
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(visual_brief=visual_brief)

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert "preserve-this-negative-constraint" in result["prompt"]
    assert len(result["prompt"]) <= 3000


def test_explicit_prompt_override_is_authoritative_and_capped():
    from worker.tasks.magnific import handle_magnific_generate_variants

    override = "manual art direction " + ("z" * 4000)
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            visual_brief="scene: This must not appear"
        )

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True, "prompt": override}
        )

    assert result["ok"] is True
    assert result["prompt"] == override[:3000]
    assert "ilustración editorial" not in result["prompt"]


def test_one_character_prompt_fails_before_writes_or_http():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_http:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page()

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "prompt": "x"}
        )

    assert result["ok"] is False
    assert "between 2 and 3000" in result["error"]
    mock_nc.update_page_properties.assert_not_called()
    mock_http.assert_not_called()


@pytest.mark.parametrize(
    "visual_brief",
    [
        "style: technical\nmodel: nano-banana-2",
        "style: [malformed",
        "legacy unstructured visual instructions",
    ],
)
def test_visual_brief_without_valid_scene_falls_back_to_title_and_premise(visual_brief):
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            titulo="Fallback title",
            premisa="Fallback premise",
            visual_brief=visual_brief,
        )

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert "Fallback title" in result["prompt"]
    assert "Fallback premise" in result["prompt"]
    assert "legacy unstructured visual instructions" not in result["prompt"]


def test_null_scene_falls_back_to_title_and_premise():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            titulo="Fallback title",
            premisa="Fallback premise",
            visual_brief="scene: null\naspect_ratio: 4:3",
        )

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["aspect_ratio"] == "4:3"
    assert "Fallback title" in result["prompt"]


def test_visual_brief_controls_model_and_dimensions_without_input_overrides():
    from worker.tasks.magnific import handle_magnific_generate_variants

    visual_brief = """\
scene: Isometric model coordination
model: nano-banana-pro
aspect_ratio: 16:9
resolution: 4K
"""
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(visual_brief=visual_brief)

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "dry_run": True}
        )

    assert result["ok"] is True
    assert result["model"] == "nano-banana-pro"
    assert result["endpoint"] == PRO_ENDPOINT
    assert result["aspect_ratio"] == "16:9"
    assert result["resolution"] == "4K"


def test_input_model_and_dimensions_override_visual_brief_config():
    from worker.tasks.magnific import handle_magnific_generate_variants

    visual_brief = """\
scene: Isometric model coordination
model: mystic
aspect_ratio: "1:1"
resolution: 1K
"""
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(visual_brief=visual_brief)

        result = handle_magnific_generate_variants(
            {
                "publicacion_page_id": "pub-1",
                "dry_run": True,
                "model": "nano-banana-pro",
                "aspect_ratio": "16:9",
                "resolution": "4K",
            }
        )

    assert result["ok"] is True
    assert result["model"] == "nano-banana-pro"
    assert result["endpoint"] == PRO_ENDPOINT
    assert result["aspect_ratio"] == "16:9"
    assert result["resolution"] == "4K"


def test_unknown_model_alias_fails_closed_without_writes_or_http():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_httpx_client_cls:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page()

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "model": "mystic-by-accident"}
        )

    assert result["ok"] is False
    assert "Unsupported Magnific model alias" in result["error"]
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
    get_effects = [
        _mystic_poll_completed_response(urls[i - 1], f"task-{i}")
        for i in range(1, 6)
    ]
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

    for call in http_client.post.call_args_list:
        assert call.args[0] == FLASH_ENDPOINT
        assert call.kwargs["headers"]["Content-Type"] == "application/json"
        assert "x-magnific-api-key" in call.kwargs["headers"]
        payload = call.kwargs["json"]
        assert payload["aspect_ratio"] == "4:3"
        assert payload["resolution"] == "2K"
        assert payload["use_google_search_tool"] is False
        assert "model" not in payload
    for i, call in enumerate(http_client.get.call_args_list, start=1):
        assert call.args[0] == f"{FLASH_ENDPOINT}/task-{i}"
        assert "x-magnific-api-key" in call.kwargs["headers"]
        assert "Content-Type" not in call.kwargs["headers"]


def test_explicit_mystic_override_keeps_legacy_endpoint_and_payload():
    from worker.tasks.magnific import handle_magnific_generate_variants

    patcher, http_client = _patch_httpx_client(
        [_mystic_submit_response("task-1")],
        [_mystic_poll_completed_response("https://cdn.magnific.com/img-1.png")],
    )
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="Pendiente generación")

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "count": 1, "model": "mystic"}
        )

    assert result["ok"] is True
    post_call = http_client.post.call_args
    assert post_call.args[0] == MYSTIC_ENDPOINT
    assert post_call.kwargs["json"]["model"] == "realism"
    assert post_call.kwargs["json"]["aspect_ratio"] == "classic_4_3"
    assert post_call.kwargs["json"]["resolution"] == "2k"
    assert "use_google_search_tool" not in post_call.kwargs["json"]
    final_props = mock_nc.update_page_properties.call_args_list[-1].kwargs["properties"]
    assert not any(value == {"url": None} for value in final_props.values())


@pytest.mark.parametrize(
    ("aspect_ratio", "resolution", "expected_aspect", "expected_resolution"),
    [
        ("1:1", "1K", "square_1_1", "1k"),
        ("16:9", "4K", "widescreen_16_9", "4k"),
        ("social_post_4_5", "2k", "social_post_4_5", "2k"),
    ],
)
def test_explicit_mystic_validates_and_maps_official_dimensions(
    aspect_ratio, resolution, expected_aspect, expected_resolution
):
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page()

        result = handle_magnific_generate_variants(
            {
                "publicacion_page_id": "pub-1",
                "dry_run": True,
                "model": "mystic",
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            }
        )

    assert result["ok"] is True
    assert result["aspect_ratio"] == expected_aspect
    assert result["resolution"] == expected_resolution


@pytest.mark.parametrize(
    ("aspect_ratio", "resolution", "message"),
    [
        ("bogus", "2K", "Unsupported Mystic aspect_ratio"),
        ("4:3", "medium", "Unsupported Mystic resolution"),
    ],
)
def test_explicit_mystic_rejects_unknown_dimensions_without_writes(
    aspect_ratio, resolution, message
):
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page()

        result = handle_magnific_generate_variants(
            {
                "publicacion_page_id": "pub-1",
                "model": "mystic",
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            }
        )

    assert result["ok"] is False
    assert message in result["error"]
    mock_nc.update_page_properties.assert_not_called()


def test_regenerar_from_listo_transitions_then_generates_without_early_url_clear():
    from worker.tasks.magnific import handle_magnific_generate_variants

    urls = [f"https://cdn.magnific.com/regen-{i}.png" for i in range(1, 6)]
    patcher, http_client = _patch_httpx_client(
        [_mystic_submit_response(f"task-{i}") for i in range(1, 6)],
        [
            _mystic_poll_completed_response(url, f"task-{i}")
            for i, url in enumerate(urls, start=1)
        ],
    )
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            visual_brief="scene: Isometric openBIM layers\nmodel: nano-banana-2",
            estado_imagen="Listo para selección",
            seleccion_imagen="Regenerar",
        )

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is True
    assert all(call.args[0] == FLASH_ENDPOINT for call in http_client.post.call_args_list)
    assert not any(call.args[0] == MYSTIC_ENDPOINT for call in http_client.post.call_args_list)
    assert mock_nc.update_page_properties.call_count == 3
    transition_call, generating_call, success_call = mock_nc.update_page_properties.call_args_list
    transition_props = transition_call.kwargs["properties"]
    assert transition_props["Estado imagen"] == {"select": {"name": "Regeneración pedida"}}
    assert transition_props["Selección imagen"] == {"select": {"name": "Pendiente"}}
    assert not any(key.startswith("imagen_alt_") for key in transition_props)
    assert generating_call.kwargs["properties"]["Estado imagen"] == {
        "select": {"name": "Generando"}
    }
    assert not any(key.startswith("imagen_alt_") for key in generating_call.kwargs["properties"])
    for i, url in enumerate(urls, start=1):
        assert success_call.kwargs["properties"][f"imagen_alt_{i}_url"] == {"url": url}


def test_regenerar_transition_write_failure_aborts_before_magnific_call():
    from worker.tasks.magnific import handle_magnific_generate_variants

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patch("worker.tasks.magnific.httpx.Client") as mock_httpx_client_cls:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(
            estado_imagen="Listo para selección",
            seleccion_imagen="Regenerar",
        )
        mock_nc.update_page_properties.side_effect = RuntimeError("Notion write failed")

        result = handle_magnific_generate_variants({"publicacion_page_id": "pub-1"})

    assert result["ok"] is False
    assert "consume 'Regenerar'" in result["error"]
    assert mock_nc.update_page_properties.call_count == 1
    mock_httpx_client_cls.assert_not_called()


def test_final_notion_write_failure_recovers_row_to_error_without_clearing_urls():
    from worker.tasks.magnific import handle_magnific_generate_variants

    generated_url = "https://cdn.magnific.com/img-1.png"
    patcher, _http_client = _patch_httpx_client(
        [_mystic_submit_response("task-1")],
        [_mystic_poll_completed_response(generated_url)],
    )
    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.notion_client"
    ) as mock_nc, patcher:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        mock_nc.get_page.return_value = _publicacion_page(estado_imagen="No aplica")
        mock_nc.update_page_properties.side_effect = [
            None,
            RuntimeError(
                'write failed x-magnific-api-key="fake-secret-value" '
                "https://cdn.example.test/image?signature=fake"
            ),
            None,
        ]

        result = handle_magnific_generate_variants(
            {"publicacion_page_id": "pub-1", "count": 1}
        )

    assert result["ok"] is False
    assert result["generated"] == 1
    assert "fake-secret-value" not in result["error"]
    assert "https://cdn.example.test" not in result["error"]
    assert mock_nc.update_page_properties.call_count == 3
    final_props = mock_nc.update_page_properties.call_args_list[1].kwargs["properties"]
    recovery_props = mock_nc.update_page_properties.call_args_list[2].kwargs["properties"]
    assert final_props["imagen_alt_1_url"] == {"url": generated_url}
    assert recovery_props["Estado imagen"] == {"select": {"name": "Error"}}
    assert not any(key.startswith("imagen_alt_") for key in recovery_props)


def test_interim_write_never_clears_existing_urls():
    """Regression guard: a retry that fails immediately must not destroy
    URLs a *previous* run already paid Magnific credits to produce. The
    interim 'Generando' write must not touch imagen_alt_*_url at all, and a
    failed run must not write any image slot."""
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
    # Nothing about alt_1..5 (including a hypothetical prior success) is
    # touched by a failed retry.
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
    assert not any(key.startswith("imagen_alt_") for key in final_props)
    assert "imagen_cantidad" not in final_props
    assert "imagen_generada_at" not in final_props
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


def test_http_error_diagnostics_redact_urls_and_credential_values():
    from worker.tasks.magnific import _safe_httpx_error_body

    request = httpx.Request("POST", MYSTIC_ENDPOINT)
    response = httpx.Response(
        status_code=500,
        text="failed URL=https://cdn.example.test/image?signature=fake API_KEY=fake-value",
        request=request,
    )
    exc = httpx.HTTPStatusError("server error", request=request, response=response)

    safe_body = _safe_httpx_error_body(exc)

    assert "https://" not in safe_body
    assert "fake-value" not in safe_body
    assert "[REDACTED_URL]" in safe_body
    assert "[REDACTED_CREDENTIAL]" in safe_body


def test_error_diagnostics_redact_quoted_hyphenated_credential_key():
    from worker.tasks.magnific import _safe_error_text

    safe_body = _safe_error_text(
        '{"x-magnific-api-key":"fake-secret-value","status":"failed"}'
    )

    assert "fake-secret-value" not in safe_body
    assert "[REDACTED_CREDENTIAL]" in safe_body


def test_submit_retries_transient_503_with_exponential_backoff():
    from worker.tasks.magnific import _submit_mystic

    request = httpx.Request("POST", MYSTIC_ENDPOINT)
    unavailable = MagicMock()
    unavailable.raise_for_status.side_effect = httpx.HTTPStatusError(
        "unavailable",
        request=request,
        response=httpx.Response(503, text="try again", request=request),
    )
    success = _mystic_submit_response("task-1")
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.post.side_effect = [unavailable, success]

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ), patch("worker.tasks.magnific.time.sleep") as mock_sleep:
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        task_id = _submit_mystic("a prompt", "classic_4_3", "2k", "realism")

    assert task_id == "task-1"
    assert http_client.post.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


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


@pytest.mark.parametrize(
    ("generated", "message"),
    [
        ("https://cdn.magnific.com/image.png", "invalid generated shape"),
        (["not-a-url"], "invalid generated URL"),
        (["https://APP.MAGNIFIC.COM/creations/abc"], "not a direct export"),
    ],
)
def test_poll_rejects_invalid_generated_response_shapes_and_urls(generated, message):
    from worker.tasks.magnific import _poll_mystic

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "data": {"task_id": "task-1", "status": "COMPLETED", "generated": generated}
    }
    http_client = MagicMock()
    http_client.__enter__.return_value = http_client
    http_client.__exit__.return_value = False
    http_client.get.return_value = resp

    with patch("worker.tasks.magnific.config") as mock_cfg, patch(
        "worker.tasks.magnific.httpx.Client", return_value=http_client
    ):
        mock_cfg.MAGNIFIC_API_KEY = "key-123"
        with pytest.raises(RuntimeError, match=message):
            _poll_mystic("task-1")


def test_cli_redacts_signed_urls_and_error_diagnostics():
    from scripts.editorial.magnific_generate_variants import (
        _DEFAULT_GENERATE_TIMEOUT_SEC,
        _redact_result_for_output,
    )

    result = {
        "ok": False,
        "urls": ["https://cdn.example.test/image?signature=fake"],
        "error": "x-magnific-api-key=fake-secret-value",
    }

    safe = _redact_result_for_output(result)

    assert safe["urls"] == ["[REDACTED_URL]"]
    assert safe["error"] == "[REDACTED_DIAGNOSTIC]"
    assert result["urls"][0].startswith("https://")
    assert _DEFAULT_GENERATE_TIMEOUT_SEC == 1200.0
