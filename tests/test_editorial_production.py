"""Tests for editorial model guard and copy validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.editorial.editorial_model_guard import (
    EditorialModelError,
    assert_editorial_model,
    is_editorial_model_allowed,
)
from scripts.editorial.validate_editorial_copy import (
    validate_copy_text,
    validate_publication_file,
    validate_publication_payload,
)

_REPO = Path(__file__).resolve().parent.parent
_CAND001 = _REPO / "evals" / "editorial" / "cand-001-final-copy.yaml"
_CIERRE = "Primero claridad. Después velocidad."


def test_editorial_model_allows_gpt55():
    assert is_editorial_model_allowed("azure-openai-responses/gpt-5.5")


def test_editorial_model_blocks_gpt54_silent():
    with pytest.raises(EditorialModelError, match="BLOCKED"):
        assert_editorial_model("azure-openai-responses/gpt-5.4")


def test_editorial_model_blocks_gemini():
    with pytest.raises(EditorialModelError, match="forbidden"):
        assert_editorial_model("google/gemini-2.5-flash")


def test_cand001_final_copy_validates():
    result = validate_publication_file(_CAND001)
    assert result.ok, result.errors
    payload = yaml.safe_load(_CAND001.read_text(encoding="utf-8"))
    assert "?" not in payload["copy_linkedin"].strip().split("\n")[0]
    assert "Primero claridad" in payload["copy_linkedin"]
    assert "amplificar" not in payload["copy_blog"].lower()
    assert payload["trace_id"] == "CAND-001-v3.1-human-editorial-sensitivity-fix"
    blog = payload["copy_blog"]
    assert "procesos lentos" not in blog.lower()
    assert "pocas personas" not in blog.lower()
    assert "clasificar incidencias" in blog
    assert "agrupar incidencias" in blog


def test_cand001_linkedin_opens_with_affirmation():
    payload = yaml.safe_load(_CAND001.read_text(encoding="utf-8"))
    first = payload["copy_linkedin"].strip().split("\n")[0]
    assert first.startswith("Un equipo BIM")
    assert not first.endswith("?")


def test_fail_automatico_detected():
    payload = yaml.safe_load(_CAND001.read_text(encoding="utf-8"))
    bad = dict(payload)
    bad["copy_linkedin"] = "Ahí aparece el problema con amplificar todo."
    result = validate_publication_payload(bad)
    assert not result.ok


# ---------------------------------------------------------------------------
# Contrato de canal (PKG-MACRO-P5-L1-T6)
#
# `newsletter` entró a VALID_CHANNELS en #639 y el validador de copy seguía
# siendo un pipeline de tres canales: el chequeo del cierre canónico estaba
# guardado por `channel in ("linkedin", "blog", "x")`, así que una pieza de
# newsletter lo saltaba sin error ni warning.
# ---------------------------------------------------------------------------


def test_newsletter_sin_cierre_canonico_ya_no_pasa_callado():
    result = validate_copy_text("Cuerpo de newsletter sin el cierre.", channel="newsletter")
    assert any("cierre canónico" in w for w in result.warnings), result.warnings


def test_newsletter_con_cierre_canonico_no_avisa():
    result = validate_copy_text(f"Cuerpo de newsletter. {_CIERRE}", channel="newsletter")
    assert not any("cierre canónico" in w for w in result.warnings), result.warnings


def test_canal_desconocido_es_error():
    result = validate_copy_text(f"Texto cualquiera. {_CIERRE}", channel="tiktok")
    assert not result.ok
    assert any("canal sin criterios" in e and "tiktok" in e for e in result.errors), result.errors


def test_canal_nuevo_hereda_el_chequeo_de_cierre():
    # El default es "requiere cierre": un canal sin criterios acumula el error
    # de canal Y el aviso de cierre, en vez de salir limpio como antes.
    result = validate_copy_text("Texto sin cierre.", channel="tiktok")
    assert not result.ok
    assert any("cierre canónico" in w for w in result.warnings), result.warnings


def test_linkedin_empresa_sigue_exento_del_cierre():
    # Único bloque con requiere_cierre_canonico: false — acompaña al post de la
    # empresa, no es pieza propia. Sin el opt-out, invertir el default lo habría
    # empezado a marcar.
    result = validate_copy_text("Texto para compartir el post.", channel="linkedin_empresa")
    assert not any("cierre canónico" in w for w in result.warnings), result.warnings


def _cand001_payload() -> dict:
    return dict(yaml.safe_load(_CAND001.read_text(encoding="utf-8")))


def test_payload_que_declara_newsletter_exige_copy_newsletter():
    payload = _cand001_payload()
    payload["canal"] = "newsletter"
    result = validate_publication_payload(payload)
    assert not result.ok
    assert "missing copy_newsletter" in result.errors


def test_payload_que_declara_newsletter_en_target_channels_tambien_lo_exige():
    payload = _cand001_payload()
    payload["target_channels"] = ["blog", "newsletter"]
    result = validate_publication_payload(payload)
    assert not result.ok
    assert "missing copy_newsletter" in result.errors


def test_payload_sin_declarar_newsletter_solo_avisa():
    # CAND-001 se escribió antes de que el canal existiera: no puede romperse.
    result = validate_publication_payload(_cand001_payload())
    assert result.ok, result.errors
    assert any("missing copy_newsletter" in w for w in result.warnings), result.warnings


def test_copy_newsletter_presente_se_valida_como_los_demas():
    payload = _cand001_payload()
    payload["target_channels"] = ["newsletter"]
    payload["copy_newsletter"] = "Ahí aparece el problema con amplificar todo."
    result = validate_publication_payload(payload)
    assert not result.ok
    assert any(e.startswith("newsletter: fail_automatico") for e in result.errors), result.errors


def test_canal_se_normaliza_como_lo_hace_el_payload():
    # Los canales llegan de selects de Notion y de YAML a mano; el lookup y
    # _declared_channels tienen que tratar el mismo dato igual.
    for channel in ("Newsletter", " newsletter ", "NEWSLETTER"):
        result = validate_copy_text(f"Cuerpo. {_CIERRE}", channel=channel)
        assert result.ok, (channel, result.errors)


def test_canal_declarado_en_shape_notion_tambien_exige_copy():
    # Sin coerción del {"select": {"name": ...}} el gate falla abierto: no ve el
    # canal declarado y degrada el error a warning.
    payload = _cand001_payload()
    payload["canal"] = {"select": {"name": "newsletter"}}
    result = validate_publication_payload(payload)
    assert not result.ok
    assert "missing copy_newsletter" in result.errors


def test_build_properties_mapea_copy_newsletter():
    from scripts.editorial.apply_publication_copy import build_properties

    payload = _cand001_payload()
    assert "Copy Newsletter" not in build_properties(payload)

    payload["copy_newsletter"] = f"Cuerpo de la newsletter. {_CIERRE}"
    props = build_properties(payload)
    assert "Copy Newsletter" in props, sorted(props)
