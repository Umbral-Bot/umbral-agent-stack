"""Tests for Stage 6 multi-platform dispatcher (skeleton)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the dispatcher module by file path because ``scripts/discovery`` is
# not a package on the test sys.path consistently.
import importlib.util

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCHER_PATH = REPO_ROOT / "scripts" / "discovery" / "stage6_generate_variants.py"
FIXTURES_PATH = REPO_ROOT / "tests" / "discovery" / "fixtures" / "synthetic_candidates.json"


def _load_dispatcher():
    spec = importlib.util.spec_from_file_location("stage6_generate_variants", DISPATCHER_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def stage6():
    return _load_dispatcher()


@pytest.fixture
def candidate():
    return {
        "id": "SYN-AECO-001",
        "title": "Cómo los gemelos digitales reducen retrabajo en obra",
        "topic": "AECO digital twins",
    }


@pytest.fixture
def angle():
    return {
        "title": "Gemelos digitales: del modelo al sitio",
        "hook": "El RFI promedio cuesta 3 días.",
    }


def test_dispatcher_linkedin_only_calls_stage7_5(stage6, candidate, angle):
    with patch.object(stage6, "_invoke_stage7_5", wraps=stage6._invoke_stage7_5) as mock_ln, \
         patch.object(stage6, "_stub_x") as mock_x, \
         patch.object(stage6, "_stub_blog") as mock_blog:
        out = stage6.generate_variants(candidate, angle, ["linkedin"])
    assert set(out.keys()) == {"linkedin"}
    assert out["linkedin"].platform == "linkedin"
    mock_ln.assert_called_once_with(candidate, angle)
    mock_x.assert_not_called()
    mock_blog.assert_not_called()


def test_dispatcher_three_platforms(stage6, candidate, angle):
    out = stage6.generate_variants(candidate, angle, ["linkedin", "x", "blog"])
    assert set(out.keys()) == {"linkedin", "x", "blog"}
    assert out["linkedin"].platform == "linkedin"
    assert out["x"].platform == "x"
    assert out["blog"].platform == "blog"
    assert out["x"].model_used == "stub-wave2"
    assert out["blog"].model_used == "stub-wave2"


def test_dispatcher_unknown_platform_raises(stage6, candidate, angle):
    with pytest.raises(ValueError) as exc:
        stage6.generate_variants(candidate, angle, ["linkedin", "tiktok"])
    assert "tiktok" in str(exc.value)


def test_dispatcher_invokes_stage7_5_with_correct_args(stage6, candidate, angle):
    captured = {}

    def fake_handler(c, a):
        captured["candidate"] = c
        captured["angle"] = a
        return stage6.LinkedInVariant(
            content="x",
            char_count=1,
            word_count=1,
            model_used="stage7_5",
            voice_match_score=0.8,
        )

    with patch.object(stage6, "_invoke_stage7_5", side_effect=fake_handler):
        stage6.generate_variants(candidate, angle, ["linkedin"])
    assert captured["candidate"] is candidate
    assert captured["angle"] is angle


def test_dispatcher_all_platforms_produce_valid_variants(stage6, candidate, angle):
    out = stage6.generate_variants(
        candidate, angle, ["linkedin", "x", "blog", "newsletter", "carousel", "video"]
    )
    assert len(out) == 6
    for p, v in out.items():
        assert v.platform == p
        # Pydantic model validated at construction time → presence proves it.
        assert v.char_count >= 0


def test_dispatcher_logs_stub_wave2(stage6, candidate, angle, caplog):
    caplog.set_level(logging.INFO, logger="stage6_generate_variants")
    stage6.generate_variants(candidate, angle, ["x"])
    msgs = " ".join(rec.message for rec in caplog.records)
    assert "stub Wave 2" in msgs
    assert "platform=x" in msgs


def test_load_candidate_finds_synthetic(stage6):
    cand, ang = stage6._load_candidate("SYN-AECO-001", FIXTURES_PATH)
    assert cand["id"] == "SYN-AECO-001"
    assert "hook" in ang


def test_load_candidate_unknown_raises(stage6):
    with pytest.raises(KeyError):
        stage6._load_candidate("SYN-DOES-NOT-EXIST", FIXTURES_PATH)


def test_cli_dispatcher_runs(stage6, capsys):
    rc = stage6.main([
        "--candidate-id", "SYN-AECO-001",
        "--platforms", "linkedin,x",
        "--fixtures", str(FIXTURES_PATH),
        "--dry-run",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "linkedin" in parsed
    assert "x" in parsed


def test_no_real_candidate_ids_in_fixtures():
    raw = FIXTURES_PATH.read_text(encoding="utf-8")
    for forbidden in ("CAND-002", "CAND-003", "CAND-004"):
        assert forbidden not in raw, f"{forbidden} must not appear in synthetic fixtures"
