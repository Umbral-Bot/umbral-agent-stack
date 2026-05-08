"""Tests for scripts/discovery/migrate_publicaciones_schema.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from scripts.discovery import migrate_publicaciones_schema as mod


DB_OK = {"id": "db-1", "data_sources": [{"id": "ds-1", "name": "Publicaciones"}]}


class _FakeClient:
    """Tiny fake httpx.Client that returns canned GET responses and records
    PATCH calls without raising."""

    def __init__(self, ds_payload: dict):
        self._ds = ds_payload
        self.patch_calls: list[tuple[str, dict]] = []

    def get(self, path: str, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        if path.startswith("/databases/"):
            resp.json.return_value = DB_OK
        elif path.startswith("/data_sources/"):
            resp.json.return_value = self._ds
        else:
            raise AssertionError(f"unexpected GET {path}")
        return resp

    def patch(self, path: str, json: dict | None = None, **kwargs):
        self.patch_calls.append((path, json or {}))
        # Persist the patch so the next read reflects the new state.
        for name, body in (json or {}).get("properties", {}).items():
            ptype = next(iter(body.keys()))
            current = self._ds["properties"].get(name)
            if current is None:
                # New property
                if ptype == "select":
                    self._ds["properties"][name] = {
                        "type": "select",
                        "select": {"options": list(body["select"]["options"])},
                    }
                else:
                    self._ds["properties"][name] = {"type": ptype}
            else:
                # Existing select getting more options
                if ptype in ("select", "multi_select"):
                    current[ptype] = {"options": list(body[ptype]["options"])}
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = self._ds
        return resp

    def close(self):
        pass


def _ds(properties: dict) -> dict:
    return {"id": "ds-1", "properties": properties}


def _full_estado_select() -> dict:
    return {
        "type": "select",
        "select": {
            "options": [
                {"name": n}
                for n in ("Borrador", "En revisión", "Autorizado",
                         "Rechazado", "Publicado")
            ]
        },
    }


def test_dry_run_does_not_patch_when_changes_pending():
    ds = _ds(
        {
            "Visual asset URL": {"type": "url"},
        }
    )
    client = _FakeClient(ds)
    result = mod.run("db-1", commit=False, token="t", client=client)
    assert result["dry_run"] is True
    assert result["applied"] is False
    assert client.patch_calls == []
    # Plan should add Copy LinkedIn AND Estado.
    plan_kinds = {(a["kind"], a["name"]) for a in result["plan"]}
    assert ("add_property", "Copy LinkedIn") in plan_kinds
    assert ("add_property", "Estado") in plan_kinds


def test_commit_applies_patch():
    ds = _ds({"Visual asset URL": {"type": "url"}})
    client = _FakeClient(ds)
    result = mod.run("db-1", commit=True, token="t", client=client)
    assert result["applied"] is True
    assert len(client.patch_calls) == 1
    body = client.patch_calls[0][1]
    assert "Copy LinkedIn" in body["properties"]
    assert body["properties"]["Copy LinkedIn"] == {"rich_text": {}}
    assert "Estado" in body["properties"]
    estado_opts = body["properties"]["Estado"]["select"]["options"]
    assert {o["name"] for o in estado_opts} == {
        "Borrador", "En revisión", "Autorizado", "Rechazado", "Publicado",
    }


def test_idempotent_second_commit_is_noop():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": _full_estado_select(),
            "Visual asset URL": {"type": "url"},
        }
    )
    client = _FakeClient(ds)
    result = mod.run("db-1", commit=True, token="t", client=client)
    assert result["plan"] == []
    assert result["applied"] is False
    assert result.get("note") == "no_changes_required"
    assert client.patch_calls == []


def test_skips_status_property_no_destructive_change():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": {
                "type": "status",
                "status": {"options": [{"name": "Borrador"}]},
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    client = _FakeClient(ds)
    result = mod.run("db-1", commit=True, token="t", client=client)
    assert "Estado" in result["skipped_due_to_status_property"]
    # No PATCH attempted because there are no additive actions.
    assert client.patch_calls == []
    assert result["applied"] is False


def test_additive_options_only_when_select_partial():
    ds = _ds(
        {
            "Copy LinkedIn": {"type": "rich_text"},
            "Estado": {
                "type": "select",
                "select": {"options": [{"name": "Borrador"}]},
            },
            "Visual asset URL": {"type": "url"},
        }
    )
    client = _FakeClient(ds)
    result = mod.run("db-1", commit=True, token="t", client=client)
    body = client.patch_calls[0][1]
    opts = [o["name"] for o in body["properties"]["Estado"]["select"]["options"]]
    # Existing 'Borrador' must be preserved (additive merge).
    assert opts[0] == "Borrador"
    # Required missing options appended.
    assert set(opts) == {
        "Borrador", "En revisión", "Autorizado", "Rechazado", "Publicado",
    }


def test_double_commit_idempotent_full_round_trip():
    ds = _ds({"Visual asset URL": {"type": "url"}})
    client = _FakeClient(ds)
    first = mod.run("db-1", commit=True, token="t", client=client)
    assert first["applied"] is True
    # Second run on the same fake should now be a no-op.
    second = mod.run("db-1", commit=True, token="t", client=client)
    assert second["applied"] is False
    assert second["plan"] == []
    # Only one PATCH ever issued.
    assert len(client.patch_calls) == 1


def test_run_raises_without_token(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NOTION_API_KEY"):
        mod.run("db-1")
