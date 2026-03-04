"""
Tests for SKILL.md validation — both real skills and synthetic edge cases.
"""

import textwrap
from pathlib import Path

import pytest

# Import validation functions
from scripts.validate_skills import (
    find_skill_files,
    parse_frontmatter,
    validate_skill,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Real skills in the repo must be valid
# ---------------------------------------------------------------------------

class TestRealSkills:
    """Validate all existing SKILL.md files in the repo."""

    def test_skill_files_exist(self):
        """At least one SKILL.md should exist."""
        files = find_skill_files(REPO_ROOT)
        assert len(files) >= 1, "Expected at least 1 SKILL.md in the repo"

    @pytest.mark.parametrize(
        "skill_path",
        find_skill_files(REPO_ROOT),
        ids=[p.parent.name for p in find_skill_files(REPO_ROOT)],
    )
    def test_all_existing_skills_are_valid(self, skill_path):
        """Each real SKILL.md must pass all validation checks."""
        errors = validate_skill(skill_path)
        assert errors == [], f"Validation errors in {skill_path.parent.name}: {errors}"


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = textwrap.dedent("""\
            ---
            name: test
            description: A test skill
            ---
            # Body
        """)
        fm, err = parse_frontmatter(text)
        assert err == ""
        assert fm["name"] == "test"
        assert fm["description"] == "A test skill"

    def test_no_opening_delimiter(self):
        text = "name: test\n---\n# Body"
        _, err = parse_frontmatter(text)
        assert "No frontmatter delimiter" in err

    def test_no_closing_delimiter(self):
        text = "---\nname: test\n# Body"
        _, err = parse_frontmatter(text)
        assert "No closing frontmatter delimiter" in err

    def test_invalid_yaml(self):
        text = "---\n: invalid: [yaml\n---\n"
        _, err = parse_frontmatter(text)
        assert "Invalid YAML" in err

    def test_non_dict_frontmatter(self):
        text = "---\n- just a list\n---\n"
        _, err = parse_frontmatter(text)
        assert "not a dict" in err


# ---------------------------------------------------------------------------
# Validation edge cases (synthetic SKILL.md via tmp_path)
# ---------------------------------------------------------------------------

def _write_skill(tmp_path: Path, dir_name: str, content: str) -> Path:
    """Create a fake skill directory with SKILL.md."""
    skill_dir = tmp_path / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


VALID_SKILL = textwrap.dedent("""\
    ---
    name: myskill
    description: A valid skill
    metadata:
      openclaw:
        emoji: "\\U0001F600"
        requires:
          env:
            - MY_API_KEY
    ---
    # myskill
""")


class TestValidateSkillEdgeCases:
    def test_valid_skill(self, tmp_path):
        path = _write_skill(tmp_path, "myskill", VALID_SKILL)
        assert validate_skill(path) == []

    def test_missing_name(self, tmp_path):
        content = VALID_SKILL.replace("name: myskill\n", "")
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("name" in e.lower() for e in errors)

    def test_missing_description(self, tmp_path):
        content = VALID_SKILL.replace("description: A valid skill\n", "")
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("description" in e.lower() for e in errors)

    def test_missing_emoji(self, tmp_path):
        content = VALID_SKILL.replace('    emoji: "\\U0001F600"\n', "")
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("emoji" in e.lower() for e in errors)

    def test_missing_env_list(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            name: myskill
            description: A skill
            metadata:
              openclaw:
                emoji: "\\U0001F600"
                requires: {}
            ---
        """)
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("env" in e.lower() for e in errors)

    def test_env_not_list(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            name: myskill
            description: A skill
            metadata:
              openclaw:
                emoji: "\\U0001F600"
                requires:
                  env: "NOT_A_LIST"
            ---
        """)
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("list" in e.lower() for e in errors)

    def test_env_items_not_strings(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            name: myskill
            description: A skill
            metadata:
              openclaw:
                emoji: "\\U0001F600"
                requires:
                  env:
                    - 123
                    - true
            ---
        """)
        path = _write_skill(tmp_path, "myskill", content)
        errors = validate_skill(path)
        assert any("string" in e.lower() for e in errors)

    def test_directory_name_mismatch(self, tmp_path):
        path = _write_skill(tmp_path, "wrong_dir", VALID_SKILL)
        errors = validate_skill(path)
        assert any("does not match" in e for e in errors)

    def test_directory_name_matches(self, tmp_path):
        path = _write_skill(tmp_path, "myskill", VALID_SKILL)
        errors = validate_skill(path)
        assert errors == []

    def test_invalid_yaml_detected(self, tmp_path):
        content = "---\n: broken [yaml\n---\n"
        path = _write_skill(tmp_path, "broken", content)
        errors = validate_skill(path)
        assert any("Invalid YAML" in e for e in errors)
