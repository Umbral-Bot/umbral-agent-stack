import importlib.util
import io
import sys
import textwrap
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_script_module("sync_skills_adapters_under_test", "scripts/sync_skills_adapters.py")


VALID_SKILL = textwrap.dedent(
    """\
    ---
    name: alpha
    description: Alpha test skill
    ---
    # Alpha

    Alpha body.
    """
)


SECOND_SKILL = textwrap.dedent(
    """\
    ---
    name: beta
    description: Beta test skill
    ---
    # Beta

    Beta body.
    """
)


def _write_skill(skills_dir: Path, slug: str, content: str) -> Path:
    skill_dir = skills_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file



def _run_main(*args: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = MODULE.main(list(args))
    return exit_code, stdout.getvalue(), stderr.getvalue()



def test_unknown_platform_rejected():
    with pytest.raises(ValueError):
        MODULE.resolve_platforms("unknown")



def test_empty_skills_dir_reports_no_skills(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    exit_code, stdout, stderr = _run_main("--skills-dir", str(skills_dir))

    assert exit_code == 0
    assert stderr == ""
    assert "skills=0 planned_writes=0" in stdout
    assert "No skills found." in stdout



def test_malformed_frontmatter_falls_back_to_slug_and_empty_description(tmp_path):
    skills_dir = tmp_path / "skills"
    skill_file = _write_skill(skills_dir, "broken", "---\nname: broken\ndescription: [oops\n---\n")

    metadata = MODULE.parse_skill_frontmatter(skill_file)
    exit_code, stdout, stderr = _run_main("--skills-dir", str(skills_dir))

    assert metadata["name"] == "broken"
    assert metadata["description"] == ""
    assert metadata["parse_error"] == "frontmatter_missing_or_invalid"
    assert exit_code == 0
    assert stderr == ""
    assert "codex | broken | create" in stdout
    assert "cursor | broken | create" in stdout



def test_dry_run_is_default_and_platform_all_is_stable(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "beta", SECOND_SKILL)
    _write_skill(skills_dir, "alpha", VALID_SKILL)
    codex_root = tmp_path / "codex-root"
    cursor_root = tmp_path / "cursor-root"

    first = _run_main(
        "--skills-dir",
        str(skills_dir),
        "--codex-root",
        str(codex_root),
        "--cursor-root",
        str(cursor_root),
    )
    second = _run_main(
        "--skills-dir",
        str(skills_dir),
        "--codex-root",
        str(codex_root),
        "--cursor-root",
        str(cursor_root),
    )

    assert first[0] == 0
    assert first == second
    assert first[2] == ""
    assert first[1].startswith("[dry-run]")
    assert "codex | alpha | create" in first[1]
    assert "cursor | alpha | create" in first[1]
    assert first[1].index("codex | alpha | create") < first[1].index("codex | beta | create")



def test_platform_flag_limits_output_to_selected_adapter(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "alpha", VALID_SKILL)
    codex_root = tmp_path / "codex-root"
    cursor_root = tmp_path / "cursor-root"

    exit_code, stdout, stderr = _run_main(
        "--skills-dir",
        str(skills_dir),
        "--codex-root",
        str(codex_root),
        "--cursor-root",
        str(cursor_root),
        "--platform",
        "cursor",
    )

    assert exit_code == 0
    assert stderr == ""
    assert "cursor | alpha | create" in stdout
    assert "codex | alpha | create" not in stdout
    assert str(cursor_root / "alpha.mdc") in stdout



def test_execute_writes_only_to_explicit_temp_roots(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "alpha", VALID_SKILL)
    codex_root = tmp_path / "codex-root"
    cursor_root = tmp_path / "cursor-root"

    exit_code, stdout, stderr = _run_main(
        "--skills-dir",
        str(skills_dir),
        "--codex-root",
        str(codex_root),
        "--cursor-root",
        str(cursor_root),
        "--execute",
    )

    assert exit_code == 0
    assert stderr == ""
    codex_skill = codex_root / "alpha" / "SKILL.md"
    cursor_rule = cursor_root / "alpha.mdc"
    assert codex_skill.read_text(encoding="utf-8") == VALID_SKILL
    cursor_text = cursor_rule.read_text(encoding="utf-8")
    assert "description: \"Alpha test skill\"" in cursor_text
    assert "Generated by: `scripts/sync_skills_to_vps.py --platform cursor`" in cursor_text
    assert "<!-- BEGIN OPENCLAW SKILL -->" in cursor_text
    assert "Alpha body." in cursor_text
    assert "[execute] platform=all" in stdout
    assert "skills=1 planned_writes=2 create=2 update=0 unchanged=0" in stdout
