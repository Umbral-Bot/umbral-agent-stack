"""Tests for scripts/discovery/check_publicaciones_schema.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from scripts.discovery import check_publicaciones_schema as mod


def _mock_client(db_payload: dict, ds_payload: dict) -> MagicMock:
    client = MagicMock(spec=httpx.Client)

    def fake_get(path: str, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        if path.startswith("/databases/"):
            resp.json.return_value = db_payload
        elif path.startswith("/data_sources/"):
            resp.json.return_value = ds_payload
        else:
            raise AssertionError(f"unexpected GET {path}")
        return resp

    client.get.side_effect = fake_get
    return client


def _ds(properties: dict) -> dict:
    return {"id": "ds-1", "properties": properties}


DB_OK = {"id": "db-1", "data_sources": [{"id": "ds-1", "name": "Publicaciones"}]}


def test_run_returns_ok_when_all_present():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": n}
                        for n in ("Borrador", "En revisión", "Autorizado",
                                 "Rechazado", "Publicado")
                    ]
                },
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    client = _mock_client(DB_OK, ds)
    report = mod.run("db-1", token="t", client=client)
    assert report["ok"] is True
    assert report["data_source_id"] == "ds-1"
    assert all(c["status"] == "ok" for c in report["checks"])


def test_missing_property_detected():
    ds = _ds(
        {
            "Estado": {
                "type": "select",
                "select": {"options": [{"name": "Borrador"}]},
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    report = mod.run("db-1", token="t", client=_mock_client(DB_OK, ds))
    assert report["ok"] is False
    summary = report["summary"]
    assert "Copy LinkedIn" in summary["missing_properties"]
    assert summary["options_missing"]["Estado"] == [
        "En revisión", "Autorizado", "Rechazado", "Publicado",
    ]


def test_estado_status_type_no_action():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": {
                "type": "status",
                "status": {
                    "options": [
                        {"name": n}
                        for n in ("Borrador", "Revisión pendiente",
                                 "Autorizado", "Publicado")
                    ]
                },
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    report = mod.run("db-1", token="t", client=_mock_client(DB_OK, ds))
    assert report["ok"] is False
    assert report["summary"]["type_mismatches_no_action"] == ["Estado"]
    estado_check = next(c for c in report["checks"] if c["name"] == "Estado")
    assert estado_check["actual_type"] == "status"
    # Required options that are not in status options must be flagged.
    assert "En revisión" in estado_check["missing_options"]
    assert "Rechazado" in estado_check["missing_options"]
    # Existing equivalents must NOT be reported as missing.
    assert "Borrador" not in estado_check["missing_options"]


def test_options_missing_when_estado_is_select_partial():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": {
                "type": "select",
                "select": {
                    "options": [{"name": "Borrador"}, {"name": "Autorizado"}]
                },
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    report = mod.run("db-1", token="t", client=_mock_client(DB_OK, ds))
    assert report["ok"] is False
    chk = next(c for c in report["checks"] if c["name"] == "Estado")
    assert chk["status"] == "options_missing"
    assert chk["missing_options"] == ["En revisión", "Rechazado", "Publicado"]


def test_run_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
        mod.run("db-1")


def test_diff_property_url_type_mismatch():
    chk = mod.diff_property(
        "Visual asset URL",
        {"type": "url"},
        {"type": "rich_text"},
    )
    assert chk.status == "type_mismatch"
