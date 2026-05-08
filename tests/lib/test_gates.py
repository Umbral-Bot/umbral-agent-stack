"""Tests for ``scripts.discovery.lib.gates``.

Pure / offline. No HTTP. No Notion. ``dedup_check`` is always a stub.
"""

from __future__ import annotations

import pytest

from scripts.discovery.lib.gates import (
    GatesStatus,
    can_publish,
    evaluate_gates,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _happy_page() -> dict:
    """A Notion-shaped page where every gate passes."""
    return {
        "aprobado_contenido": True,
        "autorizar_publicacion": True,
        "gate_invalidado": False,
        "Fuente primaria": "https://example.com/source",
        "Canal": "linkedin",
        "content_hash": "deadbeefcafebabe",
    }


def _never_dup(_h: str) -> bool:
    return False


def _always_dup(_h: str) -> bool:
    return True


# ---------------------------------------------------------------------------
# can_publish — happy path & 6 individual gate failures
# ---------------------------------------------------------------------------


def test_can_publish_happy_path():
    gates = evaluate_gates(_happy_page(), _never_dup)
    allowed, reasons = can_publish(gates)
    assert allowed is True
    assert reasons == []


def test_gate1_aprobado_contenido_blocks():
    page = _happy_page()
    page["aprobado_contenido"] = False
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["aprobado_contenido_missing"]


def test_gate2_autorizar_publicacion_blocks():
    page = _happy_page()
    page["autorizar_publicacion"] = False
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["autorizar_publicacion_missing"]


def test_gate3_gate_invalidado_blocks():
    page = _happy_page()
    page["gate_invalidado"] = True
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["gate_invalidado_active"]


def test_gate4_fuente_primaria_blocks():
    page = _happy_page()
    page["Fuente primaria"] = ""
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["fuente_primaria_missing"]


def test_gate5_plataforma_blocks():
    page = _happy_page()
    page["Canal"] = "telegram"  # not in {blog, linkedin, x, newsletter}
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["plataforma_no_seleccionada"]


def test_gate6_no_duplicado_blocks_when_dup():
    page = _happy_page()
    allowed, reasons = can_publish(evaluate_gates(page, _always_dup))
    assert allowed is False
    assert reasons == ["contenido_duplicado"]


def test_gate6_no_duplicado_blocks_when_hash_missing():
    """Missing content_hash must NOT silently approve. Block."""
    page = _happy_page()
    page["content_hash"] = ""
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == ["contenido_duplicado"]


# ---------------------------------------------------------------------------
# Multi-gate failure: stable order
# ---------------------------------------------------------------------------


def test_multiple_gates_failing_returns_all_in_stable_order():
    page = {
        "aprobado_contenido": False,
        "autorizar_publicacion": False,
        "gate_invalidado": True,
        "Fuente primaria": "",
        "Canal": "telegram",
        "content_hash": "",
    }
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is False
    assert reasons == [
        "aprobado_contenido_missing",
        "autorizar_publicacion_missing",
        "gate_invalidado_active",
        "fuente_primaria_missing",
        "plataforma_no_seleccionada",
        "contenido_duplicado",
    ]


def test_gate_invalidado_blocks_even_when_others_ok():
    page = _happy_page()
    page["gate_invalidado"] = True
    gates = evaluate_gates(page, _never_dup)
    assert gates.gate_invalidado is True
    assert gates.aprobado_contenido is True
    assert gates.autorizar_publicacion is True
    allowed, reasons = can_publish(gates)
    assert allowed is False
    assert "gate_invalidado_active" in reasons


# ---------------------------------------------------------------------------
# evaluate_gates — defaults & shape tolerance
# ---------------------------------------------------------------------------


def test_empty_dict_yields_all_blocking_defaults():
    gates = evaluate_gates({}, _never_dup)
    assert gates == GatesStatus()  # all defaults
    allowed, reasons = can_publish(gates)
    assert allowed is False
    # 5 gates fail (gate_invalidado defaults False which is OK), so 5 reasons
    assert "aprobado_contenido_missing" in reasons
    assert "gate_invalidado_active" not in reasons


def test_notion_property_dict_shape_is_accepted():
    page = {
        "properties": {
            "aprobado_contenido": {"checkbox": True},
            "autorizar_publicacion": {"checkbox": True},
            "gate_invalidado": {"checkbox": False},
            "Fuente primaria": {"url": "https://example.com/x"},
            "Canal": {"select": {"name": "blog"}},
            "content_hash": {"rich_text": [{"plain_text": "abc123"}]},
        }
    }
    allowed, reasons = can_publish(evaluate_gates(page, _never_dup))
    assert allowed is True
    assert reasons == []


def test_dedup_callback_exception_treats_as_duplicate():
    def boom(_h: str) -> bool:
        raise RuntimeError("dedup index unreachable")

    page = _happy_page()
    gates = evaluate_gates(page, boom)
    assert gates.no_duplicado is False
    allowed, reasons = can_publish(gates)
    assert allowed is False
    assert reasons == ["contenido_duplicado"]


def test_dedup_callback_not_invoked_when_hash_missing():
    calls = []

    def tracker(h: str) -> bool:
        calls.append(h)
        return False

    page = _happy_page()
    page["content_hash"] = ""
    evaluate_gates(page, tracker)
    assert calls == []


@pytest.mark.parametrize("canal", ["blog", "linkedin", "x", "newsletter"])
def test_all_supported_channels_accepted(canal: str):
    page = _happy_page()
    page["Canal"] = canal
    gates = evaluate_gates(page, _never_dup)
    assert gates.plataforma_seleccionada is True


def test_gates_status_defaults_are_safe_blocking():
    g = GatesStatus()
    assert g.aprobado_contenido is False
    assert g.autorizar_publicacion is False
    assert g.gate_invalidado is False  # inverted gate → False is the *passing* state
    assert g.fuente_primaria_ok is False
    assert g.plataforma_seleccionada is False
    assert g.no_duplicado is False
    allowed, _ = can_publish(g)
    assert allowed is False
