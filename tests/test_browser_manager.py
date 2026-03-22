import asyncio

import pytest

from worker.browser.manager import BrowserManager


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self._title = "Blank"

    async def goto(self, url: str, wait_until: str = "load", timeout: int = 30000) -> None:
        self.url = url
        self._title = f"Visited {url}"

    async def title(self) -> str:
        return self._title


class _FakeContext:
    def __init__(self) -> None:
        self.created = 0

    async def new_page(self) -> _FakePage:
        self.created += 1
        return _FakePage()


def _new_manager() -> BrowserManager:
    manager = BrowserManager()
    manager._context = _FakeContext()
    return manager


def test_get_page_ref_creates_named_page_when_missing():
    manager = _new_manager()

    ref = asyncio.run(manager._get_page_ref("talana-fix", create=True))

    assert ref.page_id == "talana-fix"
    assert manager._pages["talana-fix"] is ref
    assert manager._context.created == 1


def test_get_page_ref_raises_for_missing_named_page_without_create():
    manager = _new_manager()

    with pytest.raises(ValueError, match="Unknown page_id: talana-fix"):
        asyncio.run(manager._get_page_ref("talana-fix", create=False))


def test_navigate_reuses_named_page_id_across_calls():
    manager = _new_manager()

    first = asyncio.run(
        manager._navigate(
            url="https://example.com",
            page_id="talana-fix",
            wait_until="networkidle",
            timeout_ms=1000,
        )
    )
    second = asyncio.run(
        manager._navigate(
            url="https://example.org",
            page_id="talana-fix",
            wait_until="networkidle",
            timeout_ms=1000,
        )
    )

    assert first["page_id"] == "talana-fix"
    assert second["page_id"] == "talana-fix"
    assert manager._context.created == 1
    assert manager._pages["talana-fix"].page.url == "https://example.org"

