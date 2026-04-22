"""Tests for infra/notion_readonly_audit.py and scripts/audit_notion_publicaciones.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from infra.notion_readonly_audit import (
    CRITICAL_FIELDS,
    build_audit_report,
    compare_schema_to_database,
    fetch_database_metadata_readonly,
    format_audit_json,
    format_audit_markdown,
    load_actual_database_metadata,
    load_expected_schema,
    normalize_name,
)

SCHEMA_PATH = Path("notion/schemas/publicaciones.schema.yaml")
FIXTURE_DIR = Path("tests/fixtures/notion")
FIXTURE_VALID = FIXTURE_DIR / "publicaciones_database_valid.json"
FIXTURE_MISSING = FIXTURE_DIR / "publicaciones_database_missing_critical.json"
FIXTURE_MISMATCH = FIXTURE_DIR / "publicaciones_database_type_mismatch.json"
FIXTURE_EXTRA = FIXTURE_DIR / "publicaciones_database_extra_properties.json"
CLI_SCRIPT = "scripts/audit_notion_publicaciones.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "NOTION_API_KEY"}
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if expect_ok:
        assert result.returncode == 0, f"CLI failed (rc={result.returncode}):\n{result.stderr}\n{result.stdout}"
    return result


@pytest.fixture
def schema() -> dict:
    return load_expected_schema(SCHEMA_PATH)


@pytest.fixture
def valid_actual() -> dict:
    return load_actual_database_metadata(FIXTURE_VALID)


@pytest.fixture
def missing_actual() -> dict:
    return load_actual_database_metadata(FIXTURE_MISSING)


@pytest.fixture
def mismatch_actual() -> dict:
    return load_actual_database_metadata(FIXTURE_MISMATCH)


@pytest.fixture
def extra_actual() -> dict:
    return load_actual_database_metadata(FIXTURE_EXTRA)


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_lowercase(self) -> None:
        assert normalize_name("Content_Hash") == "content_hash"

    def test_spaces_to_underscores(self) -> None:
        assert normalize_name("Content Hash") == "content_hash"

    def test_hyphens_to_underscores(self) -> None:
        assert normalize_name("content-hash") == "content_hash"

    def test_accents_stripped(self) -> None:
        assert normalize_name("Autorizar publicación") == "autorizar_publicacion"

    def test_titulo_accent(self) -> None:
        assert normalize_name("Título") == "titulo"

    def test_mixed(self) -> None:
        assert normalize_name("Etapa audiencia") == "etapa_audiencia"

    def test_content_hash_vs_display(self) -> None:
        assert normalize_name("content_hash") == normalize_name("Content Hash")

    def test_autorizar_vs_display(self) -> None:
        assert normalize_name("autorizar_publicacion") == normalize_name("Autorizar publicación")


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

class TestSchemaLoading:
    def test_load_expected_schema(self, schema: dict) -> None:
        assert schema.get("database", {}).get("name") == "Publicaciones"

    def test_load_fixture_valid(self, valid_actual: dict) -> None:
        assert valid_actual["object"] == "database"

    def test_load_fixture_dict(self) -> None:
        data = {"object": "database", "properties": {}}
        result = load_actual_database_metadata(data)
        assert result is data

    def test_load_fixture_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_actual_database_metadata("nonexistent.json")


# ---------------------------------------------------------------------------
# Audit: valid fixture — no blockers
# ---------------------------------------------------------------------------

class TestAuditValid:
    def test_no_blockers(self, schema: dict, valid_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, valid_actual)
        blockers = [d for d in diffs if d["severity"] == "blocker"]
        assert len(blockers) == 0

    def test_report_verdict_pass(self, schema: dict, valid_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, valid_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        assert report["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# Audit: missing critical fields — blocker
# ---------------------------------------------------------------------------

class TestAuditMissingCritical:
    def test_has_blockers(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        blockers = [d for d in diffs if d["severity"] == "blocker"]
        assert len(blockers) > 0

    def test_aprobado_contenido_missing(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        blocker_fields = {
            d["normalized"] for d in diffs
            if d["severity"] == "blocker" and d["issue"] == "missing_property"
        }
        assert "aprobado_contenido" in blocker_fields

    def test_autorizar_publicacion_missing(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        blocker_fields = {
            d["normalized"] for d in diffs
            if d["severity"] == "blocker" and d["issue"] == "missing_property"
        }
        assert "autorizar_publicacion" in blocker_fields

    def test_content_hash_missing(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        blocker_fields = {
            d["normalized"] for d in diffs
            if d["severity"] == "blocker" and d["issue"] == "missing_property"
        }
        assert "content_hash" in blocker_fields

    def test_idempotency_key_missing(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        blocker_fields = {
            d["normalized"] for d in diffs
            if d["severity"] == "blocker" and d["issue"] == "missing_property"
        }
        assert "idempotency_key" in blocker_fields

    def test_report_verdict_fail(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        assert report["verdict"] == "FAIL"


# ---------------------------------------------------------------------------
# Audit: type mismatch — blocker on critical
# ---------------------------------------------------------------------------

class TestAuditTypeMismatch:
    def test_type_mismatch_blocker(self, schema: dict, mismatch_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, mismatch_actual)
        type_blockers = [
            d for d in diffs
            if d["severity"] == "blocker" and d["issue"] == "type_mismatch"
        ]
        assert len(type_blockers) > 0

    def test_aprobado_contenido_type_mismatch(self, schema: dict, mismatch_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, mismatch_actual)
        mismatched = {
            d["normalized"] for d in diffs
            if d["issue"] == "type_mismatch" and d["severity"] == "blocker"
        }
        assert "aprobado_contenido" in mismatched

    def test_content_hash_type_mismatch(self, schema: dict, mismatch_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, mismatch_actual)
        mismatched = {
            d["normalized"] for d in diffs
            if d["issue"] == "type_mismatch"
        }
        assert "content_hash" in mismatched


# ---------------------------------------------------------------------------
# Audit: extra properties — info
# ---------------------------------------------------------------------------

class TestAuditExtra:
    def test_extra_properties_info(self, schema: dict, extra_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, extra_actual)
        extras = [d for d in diffs if d["issue"] == "extra_property"]
        assert len(extras) > 0
        for d in extras:
            assert d["severity"] == "info"

    def test_extra_names(self, schema: dict, extra_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, extra_actual)
        extra_fields = {d["field"] for d in diffs if d["issue"] == "extra_property"}
        assert "Legacy score" in extra_fields
        assert "Old category" in extra_fields
        assert "Deprecated flag" in extra_fields


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_json_valid(self, schema: dict, valid_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, valid_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        text = format_audit_json(report)
        parsed = json.loads(text)
        assert parsed["verdict"] == "PASS"

    def test_json_with_diffs(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        text = format_audit_json(report)
        parsed = json.loads(text)
        assert parsed["blockers"] > 0

    def test_markdown_valid(self, schema: dict, valid_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, valid_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        text = format_audit_markdown(report)
        assert text.startswith("# Notion Publicaciones")
        assert "**PASS**" in text

    def test_markdown_with_blockers(self, schema: dict, missing_actual: dict) -> None:
        diffs = compare_schema_to_database(schema, missing_actual)
        report = build_audit_report(str(SCHEMA_PATH), "fixture", diffs)
        text = format_audit_markdown(report)
        assert "BLOCKER" in text
        assert "## Differences" in text


# ---------------------------------------------------------------------------
# Fetch read-only — mocked
# ---------------------------------------------------------------------------

class TestFetchReadOnly:
    def test_empty_token_raises(self) -> None:
        with pytest.raises(ValueError, match="NOTION_API_KEY"):
            fetch_database_metadata_readonly("db-id", "")

    def test_empty_database_id_raises(self) -> None:
        with pytest.raises(ValueError, match="database_id"):
            fetch_database_metadata_readonly("", "secret_token")

    def test_uses_get_method(self) -> None:
        """Verify that fetch builds a GET request, not POST/PATCH/DELETE."""
        with mock.patch("infra.notion_readonly_audit.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.read.return_value = b'{"object": "database", "properties": {}}'
            mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            fetch_database_metadata_readonly("test-db-id", "test-token")

            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            assert req.method == "GET"
            assert "test-db-id" in req.full_url
            assert "api.notion.com" in req.full_url

    def test_no_post_patch_delete(self) -> None:
        """Verify the request method is never POST, PATCH, or DELETE."""
        with mock.patch("infra.notion_readonly_audit.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.read.return_value = b'{"object": "database", "properties": {}}'
            mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            fetch_database_metadata_readonly("db-id", "token")

            req = mock_urlopen.call_args[0][0]
            assert req.method not in ("POST", "PATCH", "DELETE")

    def test_token_not_printed(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Token must never appear in stdout/stderr."""
        secret = "secret_ntn_MYSECRETTOKEN123"
        with mock.patch("infra.notion_readonly_audit.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.read.return_value = b'{"object": "database", "properties": {}}'
            mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            fetch_database_metadata_readonly("db-id", secret)

        captured = capsys.readouterr()
        assert secret not in captured.out
        assert secret not in captured.err


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_requires_fixture_or_database_id(self) -> None:
        result = _run_cli(expect_ok=False)
        assert result.returncode == 1
        assert "--fixture" in result.stderr or "--database-id" in result.stderr

    def test_fixture_valid_exit_0(self) -> None:
        result = _run_cli("--fixture", str(FIXTURE_VALID))
        assert "Verdict: PASS" in result.stdout

    def test_fixture_valid_with_validate(self) -> None:
        result = _run_cli("--fixture", str(FIXTURE_VALID), "--validate-schema")
        assert "PASS" in result.stdout

    def test_fixture_json(self) -> None:
        result = _run_cli("--fixture", str(FIXTURE_VALID), "--json")
        parsed = json.loads(result.stdout)
        assert parsed["verdict"] == "PASS"

    def test_fixture_markdown(self) -> None:
        result = _run_cli("--fixture", str(FIXTURE_VALID), "--markdown")
        assert result.stdout.startswith("# Notion Publicaciones")

    def test_fail_on_blocker(self) -> None:
        result = _run_cli(
            "--fixture", str(FIXTURE_MISSING), "--fail-on-blocker",
            expect_ok=False,
        )
        assert result.returncode == 1

    def test_fail_on_warning_with_warnings(self) -> None:
        result = _run_cli(
            "--fixture", str(FIXTURE_MISSING), "--fail-on-warning",
            expect_ok=False,
        )
        assert result.returncode == 1

    def test_fail_on_warning_clean(self) -> None:
        result = _run_cli("--fixture", str(FIXTURE_VALID), "--fail-on-warning")
        assert result.returncode == 0

    def test_database_id_without_token_fails(self) -> None:
        result = _run_cli("--database-id", "fake-id", expect_ok=False)
        assert result.returncode == 1
        assert "NOTION_API_KEY" in result.stderr

    def test_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        result = _run_cli("--fixture", str(FIXTURE_VALID), "--json", "--output", str(out))
        assert result.returncode == 0
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert parsed["verdict"] == "PASS"

    def test_no_notion_api_key_in_fixture_mode(self) -> None:
        """Fixture mode does not require NOTION_API_KEY."""
        result = _run_cli("--fixture", str(FIXTURE_VALID))
        assert result.returncode == 0

    def test_missing_fixture_file(self) -> None:
        result = _run_cli("--fixture", "nonexistent.json", expect_ok=False)
        assert result.returncode == 1
