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
    validate_publication_file,
    validate_publication_payload,
)

_REPO = Path(__file__).resolve().parent.parent
_CAND001 = _REPO / "evals" / "editorial" / "cand-001-final-copy.yaml"


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
