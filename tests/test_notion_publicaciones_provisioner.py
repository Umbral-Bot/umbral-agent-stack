"""Tests for infra/notion_provisioner.py and scripts/plan_notion_publicaciones.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from infra.notion_provisioner import (
    apply_plan,
    build_provisioning_plan,
    convert_property,
    plan_to_json,
    plan_to_markdown,
)

SCHEMA_PATH = Path("notion/schemas/publicaciones.schema.yaml")
CLI_SCRIPT = "scripts/plan_notion_publicaciones.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in __import__("os").environ.items() if k != "NOTION_API_KEY"}
    env["PYTHONPATH"] = "."
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, *args],
        capture_output=True,
        encoding="utf-8",
        text=True,
        env=env,
    )
    if expect_ok:
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
    return result


@pytest.fixture
def plan() -> dict:
    return build_provisioning_plan(SCHEMA_PATH, validate=True, dry_run=True)


# ---------------------------------------------------------------------------
# Schema loading and validation
# ---------------------------------------------------------------------------

class TestSchemaLoading:
    def test_load_approved_schema(self, plan: dict) -> None:
        assert plan["database"]["name"] == "Publicaciones"

    def test_validation_runs(self) -> None:
        plan = build_provisioning_plan(SCHEMA_PATH, validate=True)
        assert plan["dry_run"] is True

    def test_validation_skip(self) -> None:
        plan = build_provisioning_plan(SCHEMA_PATH, validate=False)
        assert plan["dry_run"] is True

    def test_missing_schema_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            build_provisioning_plan("nonexistent.yaml")

    def test_invalid_schema_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("database:\n  name: Test\n")
        with pytest.raises(ValueError, match="validation failed"):
            build_provisioning_plan(bad, validate=True)


# ---------------------------------------------------------------------------
# Plan structure
# ---------------------------------------------------------------------------

class TestPlanStructure:
    def test_database_name(self, plan: dict) -> None:
        assert plan["database"]["name"] == "Publicaciones"

    def test_database_version(self, plan: dict) -> None:
        assert plan["database"]["version"] == "0.1.0"

    def test_dry_run_flag(self, plan: dict) -> None:
        assert plan["dry_run"] is True

    def test_schema_path(self, plan: dict) -> None:
        assert "publicaciones.schema.yaml" in plan["schema_path"]

    def test_parent_policy(self, plan: dict) -> None:
        pp = plan["parent_policy"]
        assert pp["recommended_parent"] == "Sistema Editorial Automatizado Umbral"
        assert "Control Room" in pp["forbidden_parents"]

    def test_has_properties(self, plan: dict) -> None:
        assert len(plan["properties"]) > 0

    def test_has_api_properties(self, plan: dict) -> None:
        assert len(plan["api_properties"]) > 0

    def test_has_state_machine(self, plan: dict) -> None:
        assert plan["state_machine"] is not None
        assert plan["state_machine"]["initial"] == "Idea"

    def test_has_invariants(self, plan: dict) -> None:
        assert len(plan["invariants"]) > 0

    def test_has_recommended_views(self, plan: dict) -> None:
        assert len(plan["recommended_views"]) > 0


# ---------------------------------------------------------------------------
# Key properties present
# ---------------------------------------------------------------------------

class TestKeyProperties:
    @pytest.fixture
    def prop_names(self, plan: dict) -> set[str]:
        return {p["name"] for p in plan["properties"]}

    def test_aprobado_contenido(self, prop_names: set[str]) -> None:
        assert "aprobado_contenido" in prop_names

    def test_autorizar_publicacion(self, prop_names: set[str]) -> None:
        assert "autorizar_publicacion" in prop_names

    def test_gate_invalidado(self, prop_names: set[str]) -> None:
        assert "gate_invalidado" in prop_names

    def test_content_hash(self, prop_names: set[str]) -> None:
        assert "content_hash" in prop_names

    def test_idempotency_key(self, prop_names: set[str]) -> None:
        assert "idempotency_key" in prop_names

    def test_newsletter_channel(self, plan: dict) -> None:
        channels = plan["summary"]["channels"]
        assert "newsletter" in channels

    def test_all_channels(self, plan: dict) -> None:
        channels = plan["summary"]["channels"]
        assert set(channels) == {"blog", "linkedin", "x", "newsletter"}


# ---------------------------------------------------------------------------
# No separate DBs
# ---------------------------------------------------------------------------

class TestNoSeparateDBs:
    def test_no_variantes_db(self, plan: dict) -> None:
        assert plan["database"]["name"] != "Variantes"
        for p in plan["properties"]:
            if p["type"] == "relation" and "relation" in p["config"]:
                assert p["config"]["relation"].get("database_name") != "Variantes"

    def test_no_assets_visuales_rick_db(self, plan: dict) -> None:
        for p in plan["properties"]:
            if p["type"] == "relation" and "relation" in p["config"]:
                assert p["config"]["relation"].get("database_name") != "Assets Visuales Rick"

    def test_no_publication_log_db(self, plan: dict) -> None:
        for p in plan["properties"]:
            if p["type"] == "relation" and "relation" in p["config"]:
                assert p["config"]["relation"].get("database_name") != "PublicationLog"


# ---------------------------------------------------------------------------
# Property type conversion
# ---------------------------------------------------------------------------

class TestPropertyConversion:
    def test_title(self) -> None:
        result = convert_property({"name": "T", "type": "title"})
        assert result["config"] == {"title": {}}

    def test_rich_text(self) -> None:
        result = convert_property({"name": "R", "type": "rich_text"})
        assert result["config"] == {"rich_text": {}}

    def test_select(self) -> None:
        result = convert_property({
            "name": "S", "type": "select",
            "options": [{"name": "a", "color": "blue"}, {"name": "b"}],
        })
        opts = result["config"]["select"]["options"]
        assert len(opts) == 2
        assert opts[0] == {"name": "a", "color": "blue"}
        assert opts[1] == {"name": "b"}

    def test_multi_select(self) -> None:
        result = convert_property({
            "name": "M", "type": "multi_select",
            "options": [{"name": "x"}],
        })
        assert "multi_select" in result["config"]

    def test_checkbox(self) -> None:
        result = convert_property({"name": "C", "type": "checkbox"})
        assert result["config"] == {"checkbox": {}}

    def test_date(self) -> None:
        result = convert_property({"name": "D", "type": "date"})
        assert result["config"] == {"date": {}}

    def test_url(self) -> None:
        result = convert_property({"name": "U", "type": "url"})
        assert result["config"] == {"url": {}}

    def test_relation(self) -> None:
        result = convert_property({
            "name": "R", "type": "relation",
            "relation_database": "Publicaciones",
        })
        assert result["config"]["relation"]["database_name"] == "Publicaciones"

    def test_status(self) -> None:
        result = convert_property({
            "name": "E", "type": "status",
            "groups": [{"name": "G1", "statuses": [{"name": "S1", "color": "blue"}]}],
        })
        groups = result["config"]["status"]["groups"]
        assert len(groups) == 1
        assert groups[0]["statuses"][0]["name"] == "S1"

    def test_created_by(self) -> None:
        result = convert_property({"name": "CB", "type": "created_by"})
        assert result["config"] == {"created_by": {}}

    def test_last_edited_time(self) -> None:
        result = convert_property({"name": "LE", "type": "last_edited_time"})
        assert result["config"] == {"last_edited_time": {}}

    def test_formula(self) -> None:
        result = convert_property({
            "name": "F", "type": "formula", "expression": "1+1",
        })
        assert result["config"]["formula"]["expression"] == "1+1"

    def test_rollup(self) -> None:
        result = convert_property({
            "name": "R", "type": "rollup",
            "relation_property": "Items",
            "rollup_property": "Price",
            "function": "sum",
        })
        r = result["config"]["rollup"]
        assert r["relation_property"] == "Items"
        assert r["function"] == "sum"

    def test_unknown_type(self) -> None:
        result = convert_property({"name": "X", "type": "exotic"})
        assert result["config"] == {"exotic": {}}


# ---------------------------------------------------------------------------
# Dry-run safety
# ---------------------------------------------------------------------------

class TestDryRunSafety:
    def test_dry_run_no_network(self, plan: dict) -> None:
        """build_provisioning_plan does not call any network function."""
        # If we got a plan back, no real API call happened.
        assert plan["dry_run"] is True

    def test_dry_run_false_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="intentionally disabled"):
            build_provisioning_plan(SCHEMA_PATH, dry_run=False)

    def test_apply_plan_raises(self, plan: dict) -> None:
        with pytest.raises(NotImplementedError, match="intentionally disabled"):
            apply_plan(plan)

    def test_apply_plan_with_flag_raises(self, plan: dict) -> None:
        with pytest.raises(NotImplementedError):
            apply_plan(plan, apply=True)

    def test_no_notion_api_key_required(self, plan: dict) -> None:
        """Plan was built without NOTION_API_KEY in the environment."""
        import os
        # Ensure the provisioner doesn't depend on this
        env_backup = os.environ.pop("NOTION_API_KEY", None)
        try:
            plan2 = build_provisioning_plan(SCHEMA_PATH, validate=True)
            assert plan2["database"]["name"] == "Publicaciones"
        finally:
            if env_backup is not None:
                os.environ["NOTION_API_KEY"] = env_backup


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_json_valid(self, plan: dict) -> None:
        text = plan_to_json(plan)
        parsed = json.loads(text)
        assert parsed["database"]["name"] == "Publicaciones"

    def test_json_roundtrip(self, plan: dict) -> None:
        text = plan_to_json(plan)
        parsed = json.loads(text)
        assert parsed["dry_run"] is True
        assert len(parsed["properties"]) == len(plan["properties"])

    def test_markdown_valid(self, plan: dict) -> None:
        text = plan_to_markdown(plan)
        assert text.startswith("# Provisioning Plan: Publicaciones")
        assert "## Properties" in text
        assert "| Name | Type | Required |" in text

    def test_markdown_contains_gates(self, plan: dict) -> None:
        text = plan_to_markdown(plan)
        assert "aprobado_contenido" in text
        assert "autorizar_publicacion" in text

    def test_markdown_contains_invariants(self, plan: dict) -> None:
        text = plan_to_markdown(plan)
        assert "## Invariants" in text
        assert "no_publish_without_gates" in text

    def test_markdown_contains_state_machine(self, plan: dict) -> None:
        text = plan_to_markdown(plan)
        assert "## State Machine" in text
        assert "Idea" in text


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_default_summary(self) -> None:
        result = _run_cli()
        assert "Publicaciones" in result.stdout
        assert "dry run" in result.stdout.lower()

    def test_validate_flag(self) -> None:
        result = _run_cli("--validate")
        assert "Publicaciones" in result.stdout
        assert "Validation: passed" in result.stdout

    def test_json_output(self) -> None:
        result = _run_cli("--json")
        parsed = json.loads(result.stdout)
        assert parsed["database"]["name"] == "Publicaciones"

    def test_validate_json(self) -> None:
        result = _run_cli("--validate", "--json")
        parsed = json.loads(result.stdout)
        assert parsed["dry_run"] is True

    def test_markdown_output(self) -> None:
        result = _run_cli("--markdown")
        assert result.stdout.startswith("# Provisioning Plan: Publicaciones")

    def test_validate_markdown(self) -> None:
        result = _run_cli("--validate", "--markdown")
        assert "## Properties" in result.stdout

    def test_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "plan.json"
        result = _run_cli("--json", "--output", str(out))
        assert result.returncode == 0
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert parsed["database"]["name"] == "Publicaciones"

    def test_output_not_written_by_default(self) -> None:
        """Default run does not write any file."""
        result = _run_cli()
        assert "written to" not in result.stdout.lower()

    def test_apply_disabled(self) -> None:
        result = _run_cli("--apply", expect_ok=False)
        assert result.returncode == 1
        assert "intentionally disabled" in result.stderr

    def test_missing_schema(self) -> None:
        result = _run_cli("--schema", "nonexistent.yaml", expect_ok=False)
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
