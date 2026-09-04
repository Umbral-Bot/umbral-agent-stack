"""Fail-closed contract tests for editorial.produce_copy_brief."""

from copy import deepcopy
import json
import os
from unittest.mock import patch

import pytest

from worker.tasks import TASK_HANDLERS
from worker.tasks import editorial_copy_brief as subject


@pytest.fixture(autouse=True)
def _openclaw_enabled_for_tests(monkeypatch):
    monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)


def _text_prop(prop_type: str, value: str) -> dict:
    return {
        "type": prop_type,
        prop_type: [
            {
                "type": "text",
                "plain_text": value,
                "text": {"content": value},
            }
        ] if value else [],
    }


def _page(**overrides) -> dict:
    props = {
        "Estado": {"type": "status", "status": {"name": "Borrador"}},
        "origen_alternativa": {
            "type": "relation",
            "relation": [{"id": "shortlist-1"}],
        },
        "Copy Blog": _text_prop("rich_text", ""),
        "Copy LinkedIn": _text_prop("rich_text", ""),
        "Copy X": _text_prop("rich_text", ""),
        "Copy Newsletter": _text_prop("rich_text", ""),
        "Visual brief": _text_prop("rich_text", ""),
        "aprobado_contenido": {"type": "checkbox", "checkbox": False},
        "autorizar_publicacion": {"type": "checkbox", "checkbox": False},
        "publication_id": _text_prop("rich_text", "PUB-001"),
        "Título": _text_prop("title", "Una tesis editorial"),
        "Canal": {"type": "select", "select": {"name": "blog"}},
        "Tipo de contenido": {"type": "select", "select": {"name": "Artículo"}},
        "Premisa": _text_prop("rich_text", "Una premisa verificable"),
        "Notas": _text_prop("rich_text", "Contexto editorial"),
        "Fuente primaria": {"type": "url", "url": "https://example.test/pieza"},
    }
    props.update(overrides)
    return {"id": "pub-1", "archived": False, "in_trash": False, "properties": props}


def _brief_v2() -> dict:
    return {
        "version": 2,
        "central_fact": "La automatización replica la premisa que recibe.",
        "ignored_consequence": "Una premisa débil escala con apariencia de certeza.",
        "core_metaphor": "Una misma maqueta cruza cinco mesas de decisión.",
        "invariants": ["la misma maqueta", "la grieta siempre visible"],
        "variation_axes": [
            {"axis": f"axis-{index}", "direction": f"direction-{index}"}
            for index in range(1, 6)
        ],
        "negative_prohibitions": ["sin texto incrustado", "sin stock photo"],
        "avoid": ["logos", "interfaces legibles"],
        "aspect_ratio": "4:3",
        "resolution": "2K",
    }


def _agent_text(copy_blog: str = "Copy blog largo") -> str:
    return json.dumps(
        {
            "copy_blog": copy_blog,
            "copy_linkedin": "Copy para LinkedIn",
            "copy_x": "Copy para X",
            "copy_newsletter": "Copy para Newsletter",
            "visual_brief": _brief_v2(),
        },
        ensure_ascii=False,
    )


def _run_happy(*, page_before=None, page_after=None, copy_blog="Copy blog largo"):
    page_before = page_before or _page()
    page_after = page_after or deepcopy(page_before)
    with (
        patch.object(subject.notion_client, "get_page", side_effect=[page_before, page_after]),
        patch.object(subject.notion_client, "update_page_properties") as update,
        patch.object(subject, "_call_openclaw_proxy", return_value={"text": _agent_text(copy_blog)}) as agent,
        patch("worker.tasks.llm.handle_llm_generate") as generic_llm,
        patch("worker.tasks.magnific.handle_magnific_generate_variants") as magnific,
    ):
        result = subject.handle_editorial_produce_copy_brief(
            {"publicacion_page_id": "pub-1"}
        )
    return result, agent, update, generic_llm, magnific


def test_task_is_registered_under_governed_name():
    assert TASK_HANDLERS["editorial.produce_copy_brief"] is subject.handle_editorial_produce_copy_brief


def test_happy_path_uses_rick_and_patches_only_copy_plus_brief_without_truncation():
    long_blog = "contenido " * 600
    result, agent, update, generic_llm, magnific = _run_happy(copy_blog=long_blog)

    assert result["ok"] is True
    assert result["updated"] is True
    assert result["producer"] == "rick-editorial"
    assert set(result["written_fields"]) == {
        "Copy Blog", "Copy LinkedIn", "Copy X", "Copy Newsletter", "Visual brief"
    }
    assert agent.call_args.kwargs["agent_id"] == "rick-editorial"
    assert agent.call_args.kwargs["model"] == "rick-editorial"
    generic_llm.assert_not_called()
    magnific.assert_not_called()

    written = update.call_args.kwargs["properties"]
    assert set(written) == set(result["written_fields"])
    assert not ({"Estado", "aprobado_contenido", "autorizar_publicacion"} & set(written))
    reconstructed = "".join(
        part["text"]["content"] for part in written["Copy Blog"]["rich_text"]
    )
    assert reconstructed == long_blog.strip()
    assert len(written["Copy Blog"]["rich_text"]) > 1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda props: props["Estado"].update(status={"name": "Publicado"}),
        lambda props: props["origen_alternativa"].update(relation=[]),
        lambda props: props.__setitem__("Copy Blog", _text_prop("rich_text", "ocupado")),
        lambda props: props.__setitem__("Visual brief", _text_prop("rich_text", "ocupado")),
        lambda props: props["aprobado_contenido"].update(checkbox=True),
        lambda props: props["autorizar_publicacion"].update(checkbox=True),
        lambda props: props.pop("aprobado_contenido"),
        lambda props: props["Visual brief"].update(type="title"),
        lambda props: props.pop("Copy X"),
        lambda props: props["Copy Newsletter"].update(type="title"),
    ],
)
def test_ineligible_or_malformed_row_fails_closed_before_rick(mutation):
    page = _page()
    mutation(page["properties"])
    with (
        patch.object(subject.notion_client, "get_page", return_value=page),
        patch.object(subject.notion_client, "update_page_properties") as update,
        patch.object(subject, "_call_openclaw_proxy") as agent,
    ):
        result = subject.handle_editorial_produce_copy_brief(
            {"publicacion_page_id": "pub-1"}
        )

    assert result["ok"] is True and result["skipped"] is True
    agent.assert_not_called()
    update.assert_not_called()


def test_global_openclaw_kill_switch_blocks_reads_agent_and_write():
    with (
        patch.dict(os.environ, {"UMBRAL_DISABLE_CLAUDE": "true"}, clear=False),
        patch.object(subject.notion_client, "get_page") as get_page,
        patch.object(subject.notion_client, "update_page_properties") as update,
        patch.object(subject, "_call_openclaw_proxy") as agent,
    ):
        result = subject.handle_editorial_produce_copy_brief(
            {"publicacion_page_id": "pub-1"}
        )

    assert result["ok"] is False and result["error"] == "openclaw_disabled"
    get_page.assert_not_called()
    agent.assert_not_called()
    update.assert_not_called()


def test_second_fetch_revalidates_human_gates_before_patch():
    changed = _page()
    changed["properties"]["aprobado_contenido"]["checkbox"] = True
    result, agent, update, _generic_llm, _magnific = _run_happy(page_after=changed)

    assert agent.call_count == 1
    assert result["ok"] is True and result["skipped"] is True
    assert result["reason"] == "stale:aprobado_contenido_not_false"
    update.assert_not_called()


@pytest.mark.parametrize(
    "payload_mutator",
    [
        lambda payload: payload.pop("copy_newsletter"),
        lambda payload: payload.__setitem__("autorizar_publicacion", True),
        lambda payload: payload["visual_brief"].update(version=1),
    ],
)
def test_invalid_or_gate_bearing_rick_output_is_rejected_without_write(payload_mutator):
    payload = json.loads(_agent_text())
    payload_mutator(payload)
    with (
        patch.object(subject.notion_client, "get_page", return_value=_page()),
        patch.object(subject.notion_client, "update_page_properties") as update,
        patch.object(subject, "_call_openclaw_proxy", return_value={"text": json.dumps(payload)}),
    ):
        result = subject.handle_editorial_produce_copy_brief(
            {"publicacion_page_id": "pub-1"}
        )

    assert result["ok"] is False
    assert result["error"] == "rick_editorial_output_rejected"
    update.assert_not_called()


@pytest.mark.parametrize(
    "agent_text",
    [
        lambda valid: f"explicación previa {valid}",
        lambda valid: f"{valid}\nexplicación posterior",
        lambda valid: f"{valid}\n{valid}",
    ],
)
def test_embedded_or_multiple_json_objects_are_rejected(agent_text):
    with (
        patch.object(subject.notion_client, "get_page", return_value=_page()),
        patch.object(subject.notion_client, "update_page_properties") as update,
        patch.object(
            subject,
            "_call_openclaw_proxy",
            return_value={"text": agent_text(_agent_text())},
        ),
    ):
        result = subject.handle_editorial_produce_copy_brief(
            {"publicacion_page_id": "pub-1"}
        )

    assert result["ok"] is False
    assert result["error"] == "rick_editorial_output_rejected"
    update.assert_not_called()
