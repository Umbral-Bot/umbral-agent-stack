import pytest

from worker import config


def test_get_notion_session_capitalizable_db_id_uses_curated_binding(monkeypatch):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")

    assert config.get_notion_session_capitalizable_db_id() == "curated-db-1"


def test_require_notion_session_capitalizable_db_id_returns_value(monkeypatch):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")

    assert config.require_notion_session_capitalizable_db_id() == "curated-db-1"


@pytest.mark.parametrize("missing_value", [None, ""])
def test_require_notion_session_capitalizable_db_id_raises_when_missing(monkeypatch, missing_value):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", missing_value)

    with pytest.raises(RuntimeError, match="NOTION_CURATED_SESSIONS_DB_ID not configured"):
        config.require_notion_session_capitalizable_db_id()
