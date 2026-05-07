"""Tests for scripts/notion_publicaciones_setup_checklist.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CLI_SCRIPT = "scripts/notion_publicaciones_setup_checklist.py"


def _run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "NOTION_API_KEY"}
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
        assert result.returncode == 0, f"CLI failed (rc={result.returncode}):\n{result.stderr}\n{result.stdout}"
    return result


# ---------------------------------------------------------------------------
# Basic CLI
# ---------------------------------------------------------------------------

class TestCLIBasic:
    def test_no_env_vars_required(self) -> None:
        result = _run_cli()
        assert result.returncode == 0

    def test_no_network_calls(self) -> None:
        """CLI completes without any network access."""
        result = _run_cli()
        assert result.returncode == 0

    def test_default_markdown_title(self) -> None:
        result = _run_cli()
        assert "Setup checklist — Publicaciones" in result.stdout

    def test_default_parent_name(self) -> None:
        result = _run_cli()
        assert "Sistema Editorial Rick" in result.stdout

    def test_custom_parent_name(self) -> None:
        result = _run_cli("--parent-name", "Mi Workspace Custom")
        assert "Mi Workspace Custom" in result.stdout
        assert "Sistema Editorial Rick" not in result.stdout


# ---------------------------------------------------------------------------
# Critical properties
# ---------------------------------------------------------------------------

class TestCriticalProperties:
    def test_aprobado_contenido(self) -> None:
        result = _run_cli()
        assert "aprobado_contenido" in result.stdout

    def test_autorizar_publicacion(self) -> None:
        result = _run_cli()
        assert "autorizar_publicacion" in result.stdout

    def test_gate_invalidado(self) -> None:
        result = _run_cli()
        assert "gate_invalidado" in result.stdout

    def test_content_hash(self) -> None:
        result = _run_cli()
        assert "content_hash" in result.stdout

    def test_idempotency_key(self) -> None:
        result = _run_cli()
        assert "idempotency_key" in result.stdout


# ---------------------------------------------------------------------------
# Channels and Rick status
# ---------------------------------------------------------------------------

class TestContent:
    def test_newsletter_present(self) -> None:
        result = _run_cli()
        assert "newsletter" in result.stdout

    def test_rick_not_participating(self) -> None:
        result = _run_cli()
        assert "Rick todavía no participa" in result.stdout


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------

class TestOutputFormats:
    def test_json_valid(self) -> None:
        result = _run_cli("--json")
        parsed = json.loads(result.stdout)
        assert parsed["title"] == "Setup checklist — Publicaciones"
        assert parsed["database_name"] == "Publicaciones"

    def test_json_has_critical(self) -> None:
        result = _run_cli("--json")
        parsed = json.loads(result.stdout)
        names = [cp["name"] for cp in parsed["critical_properties"]]
        assert "aprobado_contenido" in names
        assert "autorizar_publicacion" in names

    def test_json_has_channels(self) -> None:
        result = _run_cli("--json")
        parsed = json.loads(result.stdout)
        assert "newsletter" in parsed["channels"]

    def test_json_has_rick_status(self) -> None:
        result = _run_cli("--json")
        parsed = json.loads(result.stdout)
        assert "Rick todavía no participa" in parsed["rick_status"]

    def test_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "checklist.md"
        result = _run_cli("--output", str(out))
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Setup checklist — Publicaciones" in content


# ---------------------------------------------------------------------------
# Optional sections
# ---------------------------------------------------------------------------

class TestOptionalSections:
    def test_include_property_table(self) -> None:
        result = _run_cli("--include-property-table")
        assert "| Name | Type | Required |" in result.stdout
        assert "| Título | title | yes |" in result.stdout

    def test_include_view_checklist(self) -> None:
        result = _run_cli("--include-view-checklist")
        assert "Recommended views" in result.stdout
        assert "Pipeline editorial" in result.stdout

    def test_include_audit_next_steps(self) -> None:
        result = _run_cli("--include-audit-next-steps")
        assert "Audit next steps" in result.stdout
        assert "audit_notion_publicaciones.py" in result.stdout

    def test_all_includes(self) -> None:
        result = _run_cli(
            "--include-property-table",
            "--include-view-checklist",
            "--include-audit-next-steps",
        )
        assert "| Name | Type | Required |" in result.stdout
        assert "Recommended views" in result.stdout
        assert "Audit next steps" in result.stdout


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

class TestSafety:
    def test_apply_fails(self) -> None:
        result = _run_cli("--apply", expect_ok=False)
        assert result.returncode == 1
        assert "not available" in result.stderr.lower()

    def test_no_notion_api_key_required(self) -> None:
        result = _run_cli()
        assert result.returncode == 0

    def test_missing_schema(self) -> None:
        result = _run_cli("--schema", "nonexistent.yaml", expect_ok=False)
        assert result.returncode == 1
