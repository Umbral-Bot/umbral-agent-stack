import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_add_resumen_requires_bitacora_db_id(monkeypatch):
    monkeypatch.delenv("NOTION_BITACORA_DB_ID", raising=False)
    module = _load_script_module("add_resumen_amigable_test", "scripts/add_resumen_amigable.py")

    with pytest.raises(SystemExit, match="NOTION_BITACORA_DB_ID"):
        module.require_bitacora_db_id()


def test_enrich_requires_bitacora_db_id(monkeypatch):
    monkeypatch.delenv("NOTION_BITACORA_DB_ID", raising=False)
    module = _load_script_module("enrich_bitacora_pages_test", "scripts/enrich_bitacora_pages.py")

    with pytest.raises(SystemExit, match="NOTION_BITACORA_DB_ID"):
        module.require_bitacora_db_id()
