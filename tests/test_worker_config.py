import pytest

from worker import config


def test_get_notion_session_capitalizable_db_id_returns_bound_value(monkeypatch):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", "session-db-1")

    assert config.get_notion_session_capitalizable_db_id() == "session-db-1"


def test_require_notion_session_capitalizable_db_id_raises_when_missing(monkeypatch):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", None)

    with pytest.raises(RuntimeError, match="NOTION_CURATED_SESSIONS_DB_ID not configured"):
        config.require_notion_session_capitalizable_db_id()


def test_require_notion_session_capitalizable_db_id_returns_id_when_present(monkeypatch):
    monkeypatch.setattr(config, "NOTION_CURATED_SESSIONS_DB_ID", "session-db-2")

    assert config.require_notion_session_capitalizable_db_id() == "session-db-2"
