"""Unit tests for scripts/build_skill.py — Skill Builder Pipeline."""

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("WORKER_TOKEN", "test")

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_skill import (
    _extract_env_vars,
    _extract_title,
    _generate_description_heuristic,
    _pick_emoji,
    _strip_html,
    _truncate_content,
    _word_count,
    build_skill,
    read_directory,
    read_file,
    read_input,
    render_skill,
    validate_output,
)
from validate_skills import parse_frontmatter, validate_skill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_doc(tmp_path):
    """Create a temp directory with sample documentation files."""
    d = tmp_path / "docs"
    d.mkdir()
    (d / "01_Instrucciones.md").write_text(
        "# Consultor BIM\n\nEste es un asistente especializado en BIM y Revit.\n\n"
        "## Procedimientos\n\n1. Analizar el modelo Revit\n2. Generar reporte\n\n"
        "## Referencias\n\n- https://www.autodesk.com/revit\n"
    )
    (d / "02_Avanzado.md").write_text(
        "## Funciones Avanzadas\n\nSoporte para Dynamo scripts.\n\n"
        "Requiere `REVIT_API_KEY` y `DYNAMO_TOKEN` para acceso.\n"
    )
    return d


@pytest.fixture
def single_file(tmp_path):
    """Create a single markdown file."""
    f = tmp_path / "instrucciones.md"
    f.write_text(
        "# Speckle Integration\n\n"
        "Integrate with Speckle for 3D model management.\n\n"
        "Requires `SPECKLE_API_KEY` for authentication.\n\n"
        "## Usage\n\nSend models to Speckle streams.\n"
    )
    return f


@pytest.fixture
def empty_dir(tmp_path):
    """Create an empty directory."""
    d = tmp_path / "empty"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Test: Generate from directory with multiple .md files
# ---------------------------------------------------------------------------
class TestBuildFromDirectory:
    def test_generates_valid_skill(self, sample_doc, tmp_path):
        out = tmp_path / "skill" / "SKILL.md"
        result = build_skill(
            name="skill",
            source=str(sample_doc),
            output=str(out),
            use_llm=False,
        )
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "---" in content
        fm, err = parse_frontmatter(content)
        assert err == "", f"Frontmatter parse error: {err}"
        assert fm["name"] == "skill"
        assert fm.get("description")

    def test_reads_files_in_order(self, sample_doc):
        content = read_directory(sample_doc)
        idx_instrucciones = content.index("Instrucciones")
        idx_avanzado = content.index("Avanzado")
        assert idx_instrucciones < idx_avanzado

    def test_extracts_env_vars_from_content(self, sample_doc):
        content = read_directory(sample_doc)
        env_vars = _extract_env_vars(content)
        assert "REVIT_API_KEY" in env_vars or "DYNAMO_TOKEN" in env_vars


# ---------------------------------------------------------------------------
# Test: Generate from single file
# ---------------------------------------------------------------------------
class TestBuildFromFile:
    def test_generates_valid_skill(self, single_file, tmp_path):
        out = tmp_path / "speckle" / "SKILL.md"
        result = build_skill(
            name="speckle",
            source=str(single_file),
            output=str(out),
            use_llm=False,
        )
        assert result == out
        assert out.exists()
        content = out.read_text()
        fm, err = parse_frontmatter(content)
        assert err == ""
        assert fm["name"] == "speckle"


# ---------------------------------------------------------------------------
# Test: Output passes validate_skills.py
# ---------------------------------------------------------------------------
class TestValidation:
    def test_output_passes_validation(self, sample_doc, tmp_path):
        skill_dir = tmp_path / "consultor-bim"
        skill_dir.mkdir()
        out = skill_dir / "SKILL.md"
        build_skill(
            name="consultor-bim",
            source=str(sample_doc),
            output=str(out),
            use_llm=False,
        )
        errors = validate_skill(out)
        assert errors == [], f"Validation errors: {errors}"


# ---------------------------------------------------------------------------
# Test: Empty directory raises error
# ---------------------------------------------------------------------------
class TestEmptyDirectory:
    def test_raises_on_empty_dir(self, empty_dir, tmp_path):
        out = tmp_path / "empty-skill" / "SKILL.md"
        with pytest.raises(FileNotFoundError, match="No .md or .txt"):
            build_skill(
                name="empty-skill",
                source=str(empty_dir),
                output=str(out),
                use_llm=False,
            )


# ---------------------------------------------------------------------------
# Test: URL source (mocked)
# ---------------------------------------------------------------------------
class TestBuildFromUrl:
    @patch("urllib.request.urlopen")
    def test_generates_from_url(self, mock_urlopen, tmp_path):
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b"<html><head><title>API Docs</title></head>"
            b"<body><h1>My API</h1><p>This API provides SPECKLE_API_KEY access to 3D models.</p></body></html>"
        )
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        out = tmp_path / "my-api" / "SKILL.md"
        result = build_skill(
            name="my-api",
            source=None,
            url="https://example.com/docs",
            output=str(out),
            use_llm=False,
        )
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "my-api" in content


# ---------------------------------------------------------------------------
# Test: Output word count limit
# ---------------------------------------------------------------------------
class TestWordCountLimit:
    def test_does_not_exceed_max(self, tmp_path):
        big_content = "word " * 8000
        f = tmp_path / "big.md"
        f.write_text(f"# Big Doc\n\n{big_content}")

        out = tmp_path / "big-skill" / "SKILL.md"
        build_skill(
            name="big-skill",
            source=str(f),
            output=str(out),
            use_llm=False,
        )
        content = out.read_text()
        assert _word_count(content) <= 6000


# ---------------------------------------------------------------------------
# Heuristic helper tests
# ---------------------------------------------------------------------------
class TestHelpers:
    def test_pick_emoji_audio(self):
        assert _pick_emoji("audio-tool", "") == "\U0001F50A"

    def test_pick_emoji_default(self):
        assert _pick_emoji("xyz-unknown", "nothing relevant") == "\U0001F4E6"

    def test_pick_emoji_from_content(self):
        assert _pick_emoji("tool", "search the web for research") == "\U0001F50D"

    def test_extract_env_vars(self):
        content = "Set `MY_API_KEY` and `OTHER_TOKEN` in your env."
        result = _extract_env_vars(content)
        assert "MY_API_KEY" in result
        assert "OTHER_TOKEN" in result

    def test_extract_title_from_heading(self):
        content = "# Awesome Tool\n\nSome content."
        title = _extract_title("awesome-tool", content)
        assert title == "Awesome Tool"

    def test_extract_title_fallback(self):
        content = "No heading here, just content."
        title = _extract_title("my-skill", content)
        assert "My Skill" in title

    def test_generate_description(self):
        content = "This tool helps developers build faster applications with less code."
        desc = _generate_description_heuristic("fast-build", content)
        assert len(desc) > 10

    def test_strip_html(self):
        html = "<div><p>Hello</p><script>evil()</script></div>"
        result = _strip_html(html)
        assert "Hello" in result
        assert "<" not in result
        assert "evil" not in result

    def test_truncate_content(self):
        long_text = "\n".join([f"Line {i}: " + "word " * 50 for i in range(100)])
        result = _truncate_content(long_text, max_words=200)
        assert _word_count(result) < 500

    def test_word_count(self):
        assert _word_count("one two three four") == 4


# ---------------------------------------------------------------------------
# Test: No source and no url raises
# ---------------------------------------------------------------------------
class TestInputValidation:
    def test_no_source_no_url_raises(self):
        with pytest.raises(ValueError, match="Either --source or --url"):
            read_input(source=None, url=None)

    def test_nonexistent_source_raises(self):
        with pytest.raises(FileNotFoundError):
            read_input(source="/nonexistent/path/abc123")
