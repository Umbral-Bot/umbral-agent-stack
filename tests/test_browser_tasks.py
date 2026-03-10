from types import SimpleNamespace

import pytest

import worker.tasks.browser as browser_tasks


class FakeManager:
    def navigate(self, **kwargs):
        return {"ok": True, "mode": "navigate", **kwargs}

    def read_page(self, **kwargs):
        return {"ok": True, "mode": "read", **kwargs}

    def screenshot(self, **kwargs):
        return {"ok": True, "mode": "screenshot", **kwargs}


def test_browser_navigate_requires_url(monkeypatch):
    monkeypatch.setattr(browser_tasks, "get_browser_manager", lambda: FakeManager())
    with pytest.raises(ValueError, match="url"):
        browser_tasks.handle_browser_navigate({})


def test_browser_navigate_passes_expected_params(monkeypatch):
    monkeypatch.setattr(browser_tasks, "get_browser_manager", lambda: FakeManager())
    result = browser_tasks.handle_browser_navigate(
        {
            "url": "https://example.com",
            "page_id": "page-1",
            "wait_until": "networkidle",
            "timeout_ms": "1234",
        }
    )
    assert result == {
        "ok": True,
        "mode": "navigate",
        "url": "https://example.com",
        "page_id": "page-1",
        "wait_until": "networkidle",
        "timeout_ms": 1234,
    }


def test_browser_read_page_passes_selector(monkeypatch):
    monkeypatch.setattr(browser_tasks, "get_browser_manager", lambda: FakeManager())
    result = browser_tasks.handle_browser_read_page(
        {"page_id": "page-1", "selector": "main", "include_html": True}
    )
    assert result == {
        "ok": True,
        "mode": "read",
        "page_id": "page-1",
        "selector": "main",
        "include_html": True,
    }


def test_browser_screenshot_defaults(monkeypatch):
    monkeypatch.setattr(browser_tasks, "get_browser_manager", lambda: FakeManager())
    result = browser_tasks.handle_browser_screenshot({"page_id": "page-1"})
    assert result == {
        "ok": True,
        "mode": "screenshot",
        "page_id": "page-1",
        "path": None,
        "full_page": True,
        "selector": None,
        "return_b64": False,
    }


def test_browser_navigate_rejects_invalid_wait_until(monkeypatch):
    monkeypatch.setattr(browser_tasks, "get_browser_manager", lambda: FakeManager())
    with pytest.raises(ValueError, match="Invalid wait_until"):
        browser_tasks.handle_browser_navigate({"url": "https://example.com", "wait_until": "banana"})
