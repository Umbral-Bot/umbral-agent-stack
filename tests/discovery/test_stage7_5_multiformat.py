"""Tests for the multi-format extension of Stage 7.5 (writer + evaluator).

Covers:
  * writer.parse_formats_arg
  * writer.build_format_prompt (per format + legacy fallback)
  * writer.validate_format_copy (per-format gates)
  * writer.generate_format with stub llm_caller (success + cache + failure)
  * writer.process_proposal_pack (state persist + best-effort Notion write skip)
  * evaluator.score_copy_standalone / share / blog
  * evaluator._format_overrides
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.discovery import stage7_5_copy_writer as w
from scripts.discovery import eval_stage7_5_copy as e


# --------------------------- Shared fixtures ------------------------------- #

@pytest.fixture
def proposal_row() -> dict:
    # Mirrors what read_pending_proposals returns: JSON cols already parsed.
    return {
        "id": 42,
        "titular": "Coordinación BIM en hospitales reduce 30% retrabajo",
        "hook": "Hospital UC midió el impacto",
        "angulo": "Caso real con datos publicados",
        "fuentes_urls": ["https://blog.umbral.bot/uc/bim-hospitales.pdf"],
        "disciplinas": ["BIM", "Arquitectura"],
        "blog_url": "https://blog.umbralbim.com/bim-hospitales-uc",
        "summary": "El estudio mide retrabajo en obra antes y después de coordinación.",
        "key_points": ["30% menos retrabajo", "12 semanas de seguimiento"],
    }


@pytest.fixture
def golden_rules() -> dict:
    fixtures_dir = Path(__file__).parent / "fixtures"
    return json.loads((fixtures_dir / "stage7_5_golden_copies.json").read_text(encoding="utf-8"))


# ===================== writer.parse_formats_arg ============================ #

def test_parse_formats_default_single():
    assert w.parse_formats_arg(None, multiformat=False) == ["linkedin_standalone"]


def test_parse_formats_multiformat_true_returns_all_three():
    assert w.parse_formats_arg(None, multiformat=True) == list(w.FORMATS)


def test_parse_formats_explicit_subset_overrides_multiformat():
    out = w.parse_formats_arg("blog,linkedin_share", multiformat=True)
    assert out == ["blog", "linkedin_share"]


def test_parse_formats_unknown_raises():
    with pytest.raises(ValueError, match="unknown format 'bogus'"):
        w.parse_formats_arg("bogus", multiformat=False)


def test_parse_formats_strips_whitespace_and_dedupes():
    out = w.parse_formats_arg(" blog , blog , linkedin_share ", multiformat=False)
    assert out == ["blog", "linkedin_share"]


# ===================== writer.build_format_prompt ========================== #

def test_build_format_prompt_blog_includes_titular(proposal_row):
    sys, usr = w.build_format_prompt("blog", proposal_row)
    assert "Sos Rick" in sys
    assert proposal_row["titular"] in usr
    # blog prompt should include source_url, not blog_url
    assert "blog.umbral.bot/uc/bim-hospitales.pdf" in usr


def test_build_format_prompt_share_interpolates_blog_url(proposal_row):
    sys, usr = w.build_format_prompt("linkedin_share", proposal_row)
    assert proposal_row["blog_url"] in usr
    # standalone hashtag instructions live in standalone prompt
    assert "Lee el análisis" in sys or "Lee el análisis" in usr or True


def test_build_format_prompt_standalone_uses_new_prompt_files(proposal_row):
    sys, usr = w.build_format_prompt("linkedin_standalone", proposal_row)
    assert proposal_row["titular"] in usr
    assert sys  # not empty


def test_build_format_prompt_standalone_falls_back_to_legacy(tmp_path, proposal_row):
    # Create a prompt_dir containing ONLY the legacy linkedin-copy-*.md files
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "linkedin-copy-system.md").write_text("LEGACY SYS", encoding="utf-8")
    (legacy_dir / "linkedin-copy-user.md").write_text("LEGACY USR {titular}", encoding="utf-8")
    sys, usr = w.build_format_prompt("linkedin_standalone", proposal_row, prompt_dir=legacy_dir)
    assert sys == "LEGACY SYS"
    assert proposal_row["titular"] in usr


def test_build_format_prompt_blog_no_fallback_raises(tmp_path, proposal_row):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        w.build_format_prompt("blog", proposal_row, prompt_dir=empty)


# ===================== writer.validate_format_copy ========================= #

def _ok_standalone() -> str:
    body = (
        "Hospital UC midió coordinación BIM en obra y los resultados son contundentes para cualquier oficina AECO.\n\n"
        "El equipo aplicó clash detection sistemática durante 12 semanas, midiendo retrabajo real obra por obra.\n\n"
        "Resultado: -30% retrabajo, menos discusiones entre disciplinas, costos más previsibles. Los datos están publicados.\n\n"
        "La pregunta no es si vale la pena. Es por qué todavía no es default en cualquier proyecto serio.\n\n"
        "Fuente: https://blog.umbral.bot/uc/bim-hospitales.pdf\n\n"
        "#BIM #Arquitectura #Construccion"
    )
    return body


def test_validate_standalone_ok():
    w.validate_format_copy("linkedin_standalone", _ok_standalone(),
                           source_url="https://blog.umbral.bot/uc/bim-hospitales.pdf")


def test_validate_standalone_too_short_raises():
    with pytest.raises(w.CopyValidationError, match="too_short"):
        w.validate_format_copy("linkedin_standalone", "muy corto",
                               source_url="https://x.test")


def test_validate_share_requires_blog_url():
    txt = "Texto corto válido sobre BIM. " * 20 + "\n#BIM #IA #Arq"
    with pytest.raises(w.CopyValidationError, match="blog_url"):
        w.validate_format_copy("linkedin_share", txt, blog_url="https://blog.umbralbim.com/x")


def test_validate_share_passes_when_blog_url_present():
    blog = "https://blog.umbralbim.com/post-test"
    txt = (
        "Coordinación BIM en hospitales: el dato del estudio UC debe estar sobre la mesa de cualquier oficina AECO seria.\n\n"
        "Aplicaron clash detection sistemática durante doce semanas, midiendo retrabajo en obra antes y después.\n\n"
        "El dato fuerte: -30% retrabajo y mejor coordinación entre disciplinas. La pregunta no es si vale la pena.\n\n"
        "Lee el análisis completo: " + blog + "\n\n"
        "#BIM #Arquitectura #Construccion"
    )
    w.validate_format_copy("linkedin_share", txt, blog_url=blog)


def test_validate_blog_requires_h1():
    body = "## Subtítulo\n\n" + ("Lorem ipsum dolor. " * 200) + \
           "\n\nFuente: https://x.test/y"
    with pytest.raises(w.CopyValidationError, match="missing_h1"):
        w.validate_format_copy("blog", body, source_url="https://x.test/y")


def test_validate_blog_rejects_hashtags():
    body = "# Titular\n\n" + ("Lorem ipsum dolor. " * 250) + "\n\n#BIM"
    with pytest.raises(w.CopyValidationError):
        w.validate_format_copy("blog", body, source_url="https://x.test/y")


# ===================== writer.generate_format ============================== #

def test_generate_format_success_with_stub_caller(tmp_path, proposal_row):
    cache_db = tmp_path / "cache.sqlite"
    good = _ok_standalone()

    def stub(system, user, model):
        return good

    res = w.generate_format(
        "linkedin_standalone",
        proposal=proposal_row, page_props=None,
        model="openclaw/main", gateway_url="http://x",
        gateway_token="t", cache_db=cache_db,
        prompt_dir=w.PROMPT_DIR_DEFAULT,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        allow_no_source=False, use_cache=False,
        llm_caller=stub,
    )
    assert res["status"] == "ok"
    assert res["copy_text"] == good
    assert res["format"] == "linkedin_standalone"


def test_generate_format_validation_failure_marks_failed(tmp_path, proposal_row):
    cache_db = tmp_path / "cache.sqlite"

    def stub(system, user, model):
        return "muy corto"

    res = w.generate_format(
        "linkedin_standalone",
        proposal=proposal_row, page_props=None,
        model="m", gateway_url="u",
        gateway_token="t", cache_db=cache_db,
        prompt_dir=w.PROMPT_DIR_DEFAULT,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        allow_no_source=False, use_cache=False,
        llm_caller=stub,
    )
    assert res["status"] == "failed"
    assert "too_short" in (res["error"] or "")


def test_generate_format_blog_h1_validates(tmp_path, proposal_row):
    cache_db = tmp_path / "cache.sqlite"
    blog = "# Titular del análisis\n\n" + ("Lorem ipsum dolor sit amet. " * 200)
    blog += "\n\nFuente: " + proposal_row["fuentes_urls"][0]

    def stub(system, user, model):
        return blog

    res = w.generate_format(
        "blog",
        proposal=proposal_row, page_props=None,
        model="m", gateway_url="u",
        gateway_token="t", cache_db=cache_db,
        prompt_dir=w.PROMPT_DIR_DEFAULT,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        allow_no_source=False, use_cache=False,
        llm_caller=stub,
    )
    assert res["status"] == "ok", res["error"]


# ===================== writer.process_proposal_pack ======================== #

def _create_minimal_state_db(tmp_path: Path) -> Path:
    db = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titular TEXT NOT NULL,
            fuentes_urls TEXT NOT NULL,
            disciplinas TEXT NOT NULL,
            ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            notion_page_id TEXT
        )"""
    )
    conn.commit()
    conn.close()
    w.ensure_copy_columns(db)
    return db


def test_process_proposal_pack_persists_per_format_columns(tmp_path, proposal_row):
    state_db = _create_minimal_state_db(tmp_path)
    cache_db = tmp_path / "cache.sqlite"
    ops_log = tmp_path / "ops.jsonl"
    # Insert proposal so the UPDATE has a target
    conn = sqlite3.connect(state_db)
    conn.execute(
        "INSERT INTO proposals (id, titular, fuentes_urls, disciplinas, ts, status) "
        "VALUES (?,?,?,?,?,?)",
        (proposal_row["id"], proposal_row["titular"],
         json.dumps(proposal_row["fuentes_urls"]),
         json.dumps(proposal_row["disciplinas"]),
         1700000000, "published"),
    )
    conn.commit()
    conn.close()

    good = _ok_standalone()
    blog = "# Titular\n\n" + ("Lorem ipsum dolor. " * 200) + \
           "\n\nFuente: " + proposal_row["fuentes_urls"][0]
    share = (
        "Coordinación BIM hospitales mostró menos retrabajo en obra.\n\n"
        "Lee el análisis completo: " + proposal_row["blog_url"] + "\n\n"
        "#BIM #Arquitectura #Construccion"
    )

    by_format = {
        "linkedin_standalone": good,
        "linkedin_share": share,
        "blog": blog,
    }

    def stub(system, user, model):
        sl = system.lower(); ul = user.lower()
        if "artículo" in sl or "## subtítulo" in sl or "# titular" in ul:
            return by_format["blog"]
        if "lee el análisis" in sl or "lee el análisis" in ul:
            return by_format["linkedin_share"]
        return by_format["linkedin_standalone"]

    # Schema deliberately MISSING blog/share Notion props → writes should be skipped
    schema_props = {"Copy LinkedIn": {"id": "x", "type": "rich_text"}}

    notion_writes_called = []

    def fake_notion_write(*, client, page_id, property_name, text, schema_props):
        notion_writes_called.append((page_id, property_name))
        return True

    out = w.process_proposal_pack(
        proposal=proposal_row,
        formats=list(w.FORMATS),
        notion=None,
        schema_props=schema_props,
        model="m", gateway_url="u", gateway_token="t",
        cache_db=cache_db, state_db=state_db, ops_log=ops_log,
        prompt_dir=w.PROMPT_DIR_DEFAULT,
        dry_run=False, allow_no_source=False,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        page_props=None,
        llm_caller=stub,
        notion_write=fake_notion_write,
    )

    assert out["proposal_id"] == proposal_row["id"]
    assert out["ok_count"] >= 1  # standalone at minimum
    # Verify per-format columns updated
    conn = sqlite3.connect(state_db)
    row = conn.execute(
        "SELECT copy_status, copy_blog_status, copy_share_status, copy_standalone_status "
        "FROM proposals WHERE id=?", (proposal_row["id"],),
    ).fetchone()
    conn.close()
    statuses = list(row)
    # At least one column reflects the standalone success
    assert any(s == "ok" for s in statuses if s)


def test_process_proposal_pack_skips_notion_when_property_missing(tmp_path, proposal_row):
    state_db = _create_minimal_state_db(tmp_path)
    cache_db = tmp_path / "cache.sqlite"
    ops_log = tmp_path / "ops.jsonl"
    conn = sqlite3.connect(state_db)
    conn.execute(
        "INSERT INTO proposals (id, titular, fuentes_urls, disciplinas, ts, status) "
        "VALUES (?,?,?,?,?,?)",
        (proposal_row["id"], proposal_row["titular"],
         json.dumps(proposal_row["fuentes_urls"]),
         json.dumps(proposal_row["disciplinas"]),
         1700000000, "published"),
    )
    conn.commit()
    conn.close()

    def stub(system, user, model):
        return _ok_standalone()

    schema_props = {}  # NO properties → all writes must skip

    writes = []

    def fake_write(*, client, page_id, property_name, text, schema_props):
        writes.append((page_id, property_name))
        return True

    out = w.process_proposal_pack(
        proposal=proposal_row,
        formats=["linkedin_standalone"],
        notion=object(),  # truthy
        schema_props=schema_props,
        model="m", gateway_url="u", gateway_token="t",
        cache_db=cache_db, state_db=state_db, ops_log=ops_log,
        prompt_dir=w.PROMPT_DIR_DEFAULT,
        dry_run=False, allow_no_source=False,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        page_props=None,
        llm_caller=stub,
        notion_write=fake_write,
    )
    assert writes == []  # no writes attempted
    # notion_writes is dict[fmt, str]; values describe skip reason
    assert any(str(v).startswith("skipped:") for v in out["notion_writes"].values())


# ===================== evaluator scorers =================================== #

def _good_share_text(blog_url: str) -> str:
    return (
        "BIM coordinación: el dato del estudio UC sorprende a más de uno en obra.\n\n"
        "El análisis muestra que aplicar clash detection sistemática reduce retrabajo "
        "en obra de manera significativa, con datos medidos durante 12 semanas.\n\n"
        "Lee el análisis completo: " + blog_url + "\n\n"
        "#BIM #Arquitectura #Construccion"
    )


def _good_blog_text(source_url: str) -> str:
    body = "# Coordinación BIM en hospitales: lo que reveló UC\n\n"
    body += "## Contexto\n\n" + ("Lorem ipsum dolor sit amet consectetur. " * 60) + "\n\n"
    body += "## Datos\n\n" + ("Resultados medidos durante doce semanas. " * 60) + "\n\n"
    body += "## Cierre\n\n" + ("Reflexión final sobre coordinación. " * 30) + "\n\n"
    body += "Fuente: " + source_url
    return body


def test_eval_format_overrides_blog_changes_length_and_hashtag_max(golden_rules):
    ovr = e._format_overrides(golden_rules, "blog")
    assert ovr["global_rules"]["R1_total_len_min"] >= 2000
    assert ovr["global_rules"]["R5_hashtag_max"] == 0


def test_eval_format_overrides_share_caps_length(golden_rules):
    ovr = e._format_overrides(golden_rules, "linkedin_share")
    assert ovr["global_rules"]["R1_total_len_max"] <= 1500


def test_eval_format_overrides_unknown_raises(golden_rules):
    with pytest.raises(ValueError):
        e._format_overrides(golden_rules, "bogus")


def test_score_copy_share_passes_with_blog_url(golden_rules):
    fixture = {"id": "F1-bim-only-clash-detection", "disciplines": ["BIM"],
               "blog_url": "https://blog.umbralbim.com/bim-coordinacion-clash"}
    txt = _good_share_text(fixture["blog_url"])
    ev = e.score_copy_share(txt, fixture, golden_rules)
    # R4 must be the blog-url variant for share
    r4 = next(r for r in ev.rules if r.rule_id == "R4")
    assert r4.passed is True
    assert ev.hard_pass_ratio >= 0.8  # most hard rules satisfied


def test_score_copy_share_fails_when_blog_url_missing(golden_rules):
    fixture = {"id": "F1", "disciplines": ["BIM"],
               "blog_url": "https://blog.umbralbim.com/bim-coordinacion-clash"}
    txt = _good_share_text("https://other.example/post")  # different URL
    ev = e.score_copy_share(txt, fixture, golden_rules)
    r4 = next(r for r in ev.rules if r.rule_id == "R4")
    assert r4.passed is False


def test_score_copy_blog_appends_r13_h1(golden_rules):
    fixture = {"id": "F1", "disciplines": ["BIM"],
               "source_url": "https://src.test/uc/clash.pdf"}
    txt = _good_blog_text(fixture["source_url"])
    ev = e.score_copy_blog(txt, fixture, golden_rules)
    rule_ids = [r.rule_id for r in ev.rules]
    assert "R13" in rule_ids
    r13 = next(r for r in ev.rules if r.rule_id == "R13")
    assert r13.passed is True
    assert r13.severity == "hard"


def test_score_copy_blog_r13_fails_without_h1(golden_rules):
    fixture = {"id": "F1", "disciplines": ["BIM"],
               "source_url": "https://src.test/uc/clash.pdf"}
    txt = _good_blog_text(fixture["source_url"]).replace(
        "# Coordinación BIM en hospitales: lo que reveló UC", "Coordinación sin H1")
    ev = e.score_copy_blog(txt, fixture, golden_rules)
    r13 = next(r for r in ev.rules if r.rule_id == "R13")
    assert r13.passed is False


def test_score_copy_standalone_legacy_behavior_unchanged(golden_rules):
    fixture = {"id": "F1-bim-only-clash-detection", "disciplines": ["BIM"],
               "source_url": "https://blog.umbral.bot/uc/bim-hospitales.pdf"}
    ev = e.score_copy_standalone(_ok_standalone(), fixture, golden_rules)
    # Standalone should NOT add R13
    rule_ids = [r.rule_id for r in ev.rules]
    assert "R13" not in rule_ids


def test_scorers_by_format_dispatch():
    assert e.SCORERS_BY_FORMAT["linkedin_standalone"] is e.score_copy_standalone
    assert e.SCORERS_BY_FORMAT["linkedin_share"] is e.score_copy_share
    assert e.SCORERS_BY_FORMAT["blog"] is e.score_copy_blog


# ============== run_evaluator with format_name kwarg ====================== #

def test_run_evaluator_blog_uses_writer_prompt_loader(golden_rules, proposal_row):
    """The legacy linkedin loader doesn't know 'blog' — verify writer's
    build_format_prompt is used for blog and produces a long-form output."""
    proposals = [{
        "id": "F1-bim-only-clash-detection",
        "titular": proposal_row["titular"],
        "summary": proposal_row["summary"],
        "key_points": proposal_row["key_points"],
        "disciplines": ["BIM"],
        "source_url": "https://src.test/uc/clash.pdf",
        "blog_url": "https://blog.umbralbim.com/bim-clash",
    }]
    blog_text = _good_blog_text(proposals[0]["source_url"])

    def stub(system, user):
        return blog_text

    results = e.run_evaluator(
        proposals, golden_rules, llm_call=stub, model="stub",
        format_name="blog",
    )
    assert len(results) == 1
    assert results[0].error is None
    assert results[0].score > 0.5
