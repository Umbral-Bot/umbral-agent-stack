"""
Tests for notion.append_bitacora handler and populate_bitacora.py script.
"""

import importlib
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.notion import handle_notion_append_bitacora


# ---------------------------------------------------------------------------
# Tests for handle_notion_append_bitacora
# ---------------------------------------------------------------------------


class TestHandleNotionAppendBitacora:
    """Unit tests for the notion.append_bitacora task handler."""

    @patch("worker.tasks.notion.notion_client.append_bitacora")
    def test_success_all_fields(self, mock_append):
        """Handler passes all fields correctly to notion_client.append_bitacora."""
        mock_append.return_value = {
            "page_id": "abc123",
            "url": "https://notion.so/abc123",
        }

        input_data = {
            "titulo": "R13 — Bitácora poblada",
            "fecha": "2026-03-05",
            "ronda": "R13",
            "tipo": "Documentación",
            "detalle": "Poblamiento inicial de la Bitácora.",
            "referencia": "https://github.com/Umbral-Bot/umbral-agent-stack/pull/99",
            "agente": "Cursor",
            "estado": "Completado",
        }

        result = handle_notion_append_bitacora(input_data)

        assert result["page_id"] == "abc123"
        assert result["url"] == "https://notion.so/abc123"

        mock_append.assert_called_once_with(
            titulo="R13 — Bitácora poblada",
            fecha="2026-03-05",
            ronda="R13",
            tipo="Documentación",
            detalle="Poblamiento inicial de la Bitácora.",
            referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pull/99",
            agente="Cursor",
            estado="Completado",
            database_id=None,
        )

    @patch("worker.tasks.notion.notion_client.append_bitacora")
    def test_success_minimal_fields(self, mock_append):
        """Handler works with only the required fields."""
        mock_append.return_value = {"page_id": "xyz789", "url": ""}

        result = handle_notion_append_bitacora(
            {
                "titulo": "Hito mínimo",
                "fecha": "2026-03-01",
                "ronda": "Hackathon",
                "tipo": "Hito",
            }
        )

        assert result["page_id"] == "xyz789"

        call_kwargs = mock_append.call_args.kwargs
        assert call_kwargs["titulo"] == "Hito mínimo"
        assert call_kwargs["agente"] == "Cursor"
        assert call_kwargs["estado"] == "Completado"
        assert call_kwargs["detalle"] == ""
        assert call_kwargs["referencia"] == ""

    @patch("worker.tasks.notion.notion_client.append_bitacora")
    def test_custom_database_id(self, mock_append):
        """Handler forwards custom database_id override."""
        mock_append.return_value = {"page_id": "custom_id", "url": ""}

        handle_notion_append_bitacora(
            {
                "titulo": "Test entry",
                "fecha": "2026-03-05",
                "ronda": "R13",
                "tipo": "Otro",
                "database_id": "custom-db-123",
            }
        )

        assert mock_append.call_args.kwargs["database_id"] == "custom-db-123"

    def test_missing_titulo_raises(self):
        with pytest.raises(ValueError, match="'titulo' is required"):
            handle_notion_append_bitacora(
                {"fecha": "2026-03-05", "ronda": "R13", "tipo": "Hito"}
            )

    def test_missing_fecha_raises(self):
        with pytest.raises(ValueError, match="'fecha' is required"):
            handle_notion_append_bitacora(
                {"titulo": "X", "ronda": "R13", "tipo": "Hito"}
            )

    def test_missing_ronda_raises(self):
        with pytest.raises(ValueError, match="'ronda' is required"):
            handle_notion_append_bitacora(
                {"titulo": "X", "fecha": "2026-03-05", "tipo": "Hito"}
            )

    def test_missing_tipo_raises(self):
        with pytest.raises(ValueError, match="'tipo' is required"):
            handle_notion_append_bitacora(
                {"titulo": "X", "fecha": "2026-03-05", "ronda": "R13"}
            )

    def test_empty_titulo_raises(self):
        with pytest.raises(ValueError, match="'titulo' is required"):
            handle_notion_append_bitacora(
                {"titulo": "  ", "fecha": "2026-03-05", "ronda": "R13", "tipo": "Hito"}
            )


# ---------------------------------------------------------------------------
# Tests for notion_client.append_bitacora
# ---------------------------------------------------------------------------


class TestNotionClientAppendBitacora:
    """Unit tests for notion_client.append_bitacora (httpx mocked)."""

    def _make_mock_response(self, page_id: str = "page-abc", url: str = "https://notion.so/page-abc"):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"id": page_id, "url": url}
        return mock

    @patch("worker.notion_client.config")
    @patch("worker.notion_client.httpx.Client")
    def test_append_bitacora_sends_correct_payload(self, mock_httpx_client, mock_config):
        """append_bitacora builds the correct Notion API payload."""
        from worker import notion_client

        mock_config.NOTION_API_KEY = "test-key"
        mock_config.NOTION_BITACORA_DB_ID = "db-id-123"
        mock_config.NOTION_API_VERSION = "2022-06-28"

        mock_resp = self._make_mock_response()
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_resp
        mock_httpx_client.return_value = mock_client_instance

        result = notion_client.append_bitacora(
            titulo="R12 mergeada — 8 PRs",
            fecha="2026-03-04",
            ronda="R12",
            tipo="Hito",
            detalle="Merge de 8 PRs",
            referencia="https://github.com/Umbral-Bot/umbral-agent-stack/pulls",
            agente="Manual",
            estado="Completado",
        )

        assert result["page_id"] == "page-abc"
        assert result["url"] == "https://notion.so/page-abc"

        post_call = mock_client_instance.post.call_args
        payload = post_call.kwargs.get("json") or post_call.args[1] if len(post_call.args) > 1 else post_call.kwargs["json"]
        assert payload["parent"]["database_id"] == "db-id-123"
        props = payload["properties"]
        assert props["Título"]["title"][0]["text"]["content"] == "R12 mergeada — 8 PRs"
        assert props["Fecha"]["date"]["start"] == "2026-03-04"
        assert props["Ronda"]["select"]["name"] == "R12"
        assert props["Tipo"]["select"]["name"] == "Hito"
        assert props["Agente"]["select"]["name"] == "Manual"
        assert props["Estado"]["select"]["name"] == "Completado"
        assert props["Referencia"]["url"] == "https://github.com/Umbral-Bot/umbral-agent-stack/pulls"

    @patch("worker.notion_client.config")
    @patch("worker.notion_client.httpx.Client")
    def test_append_bitacora_no_optional_fields(self, mock_httpx_client, mock_config):
        """append_bitacora omits optional fields when empty."""
        from worker import notion_client

        mock_config.NOTION_API_KEY = "test-key"
        mock_config.NOTION_BITACORA_DB_ID = "db-id-123"
        mock_config.NOTION_API_VERSION = "2022-06-28"

        mock_resp = self._make_mock_response()
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_resp
        mock_httpx_client.return_value = mock_client_instance

        notion_client.append_bitacora(
            titulo="Solo título",
            fecha="2026-03-05",
            ronda="R13",
            tipo="Otro",
            detalle="",
            referencia="",
            agente="",
            estado="",
        )

        post_call = mock_client_instance.post.call_args
        payload = post_call.kwargs.get("json") or post_call.kwargs["json"]
        props = payload["properties"]
        assert "Detalle" not in props
        assert "Referencia" not in props
        assert "Agente" not in props
        assert "Estado" not in props

    @patch("worker.notion_client.config")
    def test_append_bitacora_no_api_key_raises(self, mock_config):
        """append_bitacora raises if NOTION_API_KEY is missing."""
        from worker import notion_client

        mock_config.NOTION_API_KEY = None
        mock_config.NOTION_BITACORA_DB_ID = "db-id"

        with pytest.raises(RuntimeError, match="NOTION_API_KEY not configured"):
            notion_client.append_bitacora(
                titulo="T", fecha="2026-03-05", ronda="R13", tipo="Otro"
            )

    @patch("worker.notion_client.config")
    def test_append_bitacora_no_db_id_raises(self, mock_config):
        """append_bitacora raises if NOTION_BITACORA_DB_ID is missing."""
        from worker import notion_client

        mock_config.NOTION_API_KEY = "test-key"
        mock_config.NOTION_BITACORA_DB_ID = None

        with pytest.raises(RuntimeError, match="NOTION_BITACORA_DB_ID not configured"):
            notion_client.append_bitacora(
                titulo="T", fecha="2026-03-05", ronda="R13", tipo="Otro"
            )

    @patch("worker.notion_client.config")
    def test_append_bitacora_custom_db_id(self, mock_config):
        """append_bitacora uses provided database_id override."""
        from worker import notion_client

        mock_config.NOTION_API_KEY = "test-key"
        mock_config.NOTION_BITACORA_DB_ID = None

        with patch("worker.notion_client.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "new-page", "url": ""}
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=False)
            ctx.post.return_value = mock_resp
            mock_client_cls.return_value = ctx

            result = notion_client.append_bitacora(
                titulo="Override DB",
                fecha="2026-03-05",
                ronda="R13",
                tipo="Otro",
                database_id="override-db-999",
            )

        assert result["page_id"] == "new-page"
        payload = ctx.post.call_args.kwargs.get("json") or ctx.post.call_args.kwargs["json"]
        assert payload["parent"]["database_id"] == "override-db-999"


# ---------------------------------------------------------------------------
# Tests for notion.append_bitacora registered in TASK_HANDLERS
# ---------------------------------------------------------------------------


def test_notion_append_bitacora_registered_in_handlers():
    """notion.append_bitacora must be registered in TASK_HANDLERS."""
    from worker.tasks import TASK_HANDLERS

    assert "notion.append_bitacora" in TASK_HANDLERS
    assert callable(TASK_HANDLERS["notion.append_bitacora"])


# ---------------------------------------------------------------------------
# Tests for config
# ---------------------------------------------------------------------------


def test_notion_bitacora_db_id_in_config():
    """NOTION_BITACORA_DB_ID must be defined in worker.config."""
    from worker import config

    assert hasattr(config, "NOTION_BITACORA_DB_ID")


# ---------------------------------------------------------------------------
# Tests for populate_bitacora.py script
# ---------------------------------------------------------------------------


class TestPopulateBitacoraScript:
    """Tests for the populate_bitacora.py CLI script."""

    def test_dry_run_produces_entries(self):
        """--dry-run should print entries without raising."""
        result = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"
        assert "DRY-RUN" in result.stdout
        assert "Total:" in result.stdout

    def test_dry_run_minimum_entries(self):
        """--dry-run should generate at least 10 entries."""
        result = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        assert result.returncode == 0

        # Count numbered entries like [01], [02], ...
        import re
        entries = re.findall(r"^\[(\d+)\]", result.stdout, re.MULTILINE)
        assert len(entries) >= 10, (
            f"Expected at least 10 entries, got {len(entries)}:\n{result.stdout[:1000]}"
        )

    def test_dry_run_skip_inferred(self):
        """--dry-run --skip-inferred uses only hardcoded entries."""
        result_all = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run"],
            capture_output=True, text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        result_hard = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run", "--skip-inferred"],
            capture_output=True, text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )

        import re
        entries_all = re.findall(r"^\[(\d+)\]", result_all.stdout, re.MULTILINE)
        entries_hard = re.findall(r"^\[(\d+)\]", result_hard.stdout, re.MULTILINE)

        # With inferred entries, should have more (or equal if task files are empty)
        assert len(entries_all) >= len(entries_hard)

    def test_dry_run_shows_all_required_rondas(self):
        """--dry-run output includes entries for multiple rondas."""
        result = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run", "--skip-inferred"],
            capture_output=True, text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        output = result.stdout
        for ronda in ["Hackathon", "Pre-R11", "R11", "R12", "R13"]:
            assert ronda in output, f"Ronda '{ronda}' not found in dry-run output"

    def test_dry_run_contains_required_entry_titles(self):
        """--dry-run must include the minimum required entries from the task spec."""
        result = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run", "--skip-inferred"],
            capture_output=True, text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        output = result.stdout.lower()

        required_keywords = [
            "hackathon",        # Hackathon base entry
            "multi-llm",        # R6 entry
            "langfuse",         # R7 entry
            "linear",           # R8 entry
            "figma",            # R9 entry
            "bim",              # R11 entry
            "granola",          # R11 entry
            "bitácora",         # R13 entry
        ]
        for kw in required_keywords:
            assert kw in output, (
                f"Required keyword '{kw}' not found in dry-run output"
            )

    def test_dry_run_tasks_only(self):
        """--tasks-only uses only parsed task files."""
        result = subprocess.run(
            [sys.executable, "scripts/populate_bitacora.py", "--dry-run", "--tasks-only"],
            capture_output=True, text=True,
            cwd=str(pytest.importorskip("pathlib").Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "DRY-RUN" in result.stdout
