"""Minimal Playwright-backed browser manager for Worker browser.* tasks."""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _load_playwright() -> tuple[Callable[[], Any], type[Exception], type[Exception]]:
    """Load Playwright lazily so tests can run without the dependency installed."""
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - exercised through RuntimeError path
        raise RuntimeError(
            "Playwright is not installed. Install with `pip install playwright` and "
            "`playwright install chromium` on the target Worker."
        ) from exc
    return async_playwright, PlaywrightError, PlaywrightTimeoutError


def _default_user_data_dir() -> str:
    configured = (os.environ.get("BROWSER_USER_DATA_DIR") or "").strip()
    if configured:
        return configured
    if os.name == "nt":
        return r"C:\openclaw-browser-profile"
    return os.path.join(tempfile.gettempdir(), "openclaw-browser-profile")


def _default_screenshot_dir() -> str:
    configured = (os.environ.get("BROWSER_SCREENSHOT_DIR") or "").strip()
    if configured:
        return configured
    return os.path.join(tempfile.gettempdir(), "openclaw-browser-shots")


def _default_timeout_ms() -> int:
    raw = (os.environ.get("BROWSER_TIMEOUT_MS") or "").strip()
    if raw.isdigit():
        return max(1000, min(int(raw), 120000))
    return 30000


def _default_headless() -> bool:
    raw = (os.environ.get("BROWSER_HEADLESS") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


@dataclass
class _PageRef:
    page_id: str
    page: Any


class BrowserManager:
    """Persistent Playwright manager running on a dedicated background loop."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._playwright = None
        self._context = None
        self._pages: dict[str, _PageRef] = {}
        self._startup_error: BaseException | None = None

    def _ensure_runtime(self) -> None:
        with self._lock:
            if self._loop and self._ready.is_set():
                return
            if self._thread and self._thread.is_alive():
                self._ready.wait(timeout=30)
            else:
                self._thread = threading.Thread(
                    target=self._thread_main,
                    name="BrowserManagerLoop",
                    daemon=True,
                )
                self._thread.start()
                self._ready.wait(timeout=30)

            if self._startup_error is not None:
                raise RuntimeError(f"Browser runtime failed to start: {self._startup_error}")
            if self._loop is None or not self._ready.is_set():
                raise RuntimeError("Browser runtime did not start within the timeout.")

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._async_init())
        except BaseException as exc:  # pragma: no cover - startup failure path
            self._startup_error = exc
            self._ready.set()
            return
        self._ready.set()
        loop.run_forever()

    async def _async_init(self) -> None:
        async_playwright, _, _ = _load_playwright()
        user_data_dir = _default_user_data_dir()
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        chromium = self._playwright.chromium
        self._context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=_default_headless(),
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )

    def _run(self, coro: Any) -> Any:
        self._ensure_runtime()
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=120)

    async def _create_page(self, page_id: str | None = None) -> _PageRef:
        assert self._context is not None
        page = await self._context.new_page()
        resolved_page_id = page_id or str(uuid.uuid4())
        ref = _PageRef(page_id=resolved_page_id, page=page)
        self._pages[resolved_page_id] = ref
        return ref

    async def _get_page_ref(self, page_id: str | None = None, *, create: bool = True) -> _PageRef:
        if page_id:
            ref = self._pages.get(page_id)
            if not ref:
                if create:
                    return await self._create_page(page_id)
                raise ValueError(f"Unknown page_id: {page_id}")
            return ref
        if not self._pages:
            if not create:
                raise ValueError("No browser page exists yet. Navigate first or provide page_id.")
            return await self._create_page()
        return next(iter(self._pages.values()))

    async def _navigate(
        self,
        *,
        url: str,
        page_id: str | None = None,
        wait_until: str = "load",
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=True)
        timeout = timeout_ms or _default_timeout_ms()
        await ref.page.goto(url, wait_until=wait_until, timeout=timeout)
        return {
            "ok": True,
            "page_id": ref.page_id,
            "title": await ref.page.title(),
            "url": ref.page.url,
        }

    async def _read_page(
        self,
        *,
        page_id: str | None = None,
        selector: str | None = None,
        include_html: bool = False,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=False)
        target = ref.page.locator(selector) if selector else ref.page.locator("body")
        text = await target.inner_text()
        result: dict[str, Any] = {
            "ok": True,
            "page_id": ref.page_id,
            "title": await ref.page.title(),
            "url": ref.page.url,
            "text": text,
        }
        if include_html:
            result["html"] = await ref.page.content()
        return result

    async def _screenshot(
        self,
        *,
        page_id: str | None = None,
        path: str | None = None,
        full_page: bool = True,
        selector: str | None = None,
        return_b64: bool = False,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=False)
        if path:
            shot_path = Path(path)
        else:
            Path(_default_screenshot_dir()).mkdir(parents=True, exist_ok=True)
            shot_path = Path(_default_screenshot_dir()) / f"browser-shot-{uuid.uuid4().hex}.png"
        shot_path.parent.mkdir(parents=True, exist_ok=True)

        if selector:
            await ref.page.locator(selector).screenshot(path=str(shot_path))
        else:
            await ref.page.screenshot(path=str(shot_path), full_page=full_page)

        result: dict[str, Any] = {
            "ok": True,
            "page_id": ref.page_id,
            "path": str(shot_path),
            "url": ref.page.url,
            "title": await ref.page.title(),
        }
        if return_b64:
            result["b64_png"] = base64.b64encode(shot_path.read_bytes()).decode("ascii")
        return result

    async def _click(
        self,
        *,
        page_id: str | None = None,
        selector: str,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=False)
        timeout = timeout_ms or _default_timeout_ms()
        locator = ref.page.locator(selector)
        await locator.first.click(timeout=timeout)
        return {
            "ok": True,
            "page_id": ref.page_id,
            "url": ref.page.url,
            "title": await ref.page.title(),
            "selector": selector,
        }

    async def _type_text(
        self,
        *,
        page_id: str | None = None,
        selector: str,
        text: str,
        clear: bool = True,
        press_enter: bool = False,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=False)
        timeout = timeout_ms or _default_timeout_ms()
        locator = ref.page.locator(selector).first
        await locator.wait_for(timeout=timeout)
        if clear:
            await locator.fill("", timeout=timeout)
        await locator.type(text, timeout=timeout)
        if press_enter:
            await locator.press("Enter", timeout=timeout)
        return {
            "ok": True,
            "page_id": ref.page_id,
            "url": ref.page.url,
            "title": await ref.page.title(),
            "selector": selector,
            "chars": len(text),
            "press_enter": press_enter,
        }

    async def _press_key(
        self,
        *,
        page_id: str | None = None,
        key: str,
    ) -> dict[str, Any]:
        ref = await self._get_page_ref(page_id, create=False)
        await ref.page.keyboard.press(key)
        try:
            await ref.page.wait_for_load_state("load", timeout=2_000)
        except Exception:
            pass

        url = ref.page.url
        try:
            title = await ref.page.title()
        except Exception:
            title = None
        return {
            "ok": True,
            "page_id": ref.page_id,
            "url": url,
            "title": title,
            "key": key,
        }

    def navigate(
        self,
        *,
        url: str,
        page_id: str | None = None,
        wait_until: str = "load",
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        return self._run(
            self._navigate(
                url=url,
                page_id=page_id,
                wait_until=wait_until,
                timeout_ms=timeout_ms,
            )
        )

    def read_page(
        self,
        *,
        page_id: str | None = None,
        selector: str | None = None,
        include_html: bool = False,
    ) -> dict[str, Any]:
        return self._run(
            self._read_page(
                page_id=page_id,
                selector=selector,
                include_html=include_html,
            )
        )

    def screenshot(
        self,
        *,
        page_id: str | None = None,
        path: str | None = None,
        full_page: bool = True,
        selector: str | None = None,
        return_b64: bool = False,
    ) -> dict[str, Any]:
        return self._run(
            self._screenshot(
                page_id=page_id,
                path=path,
                full_page=full_page,
                selector=selector,
                return_b64=return_b64,
            )
        )

    def click(
        self,
        *,
        page_id: str | None = None,
        selector: str,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        return self._run(
            self._click(
                page_id=page_id,
                selector=selector,
                timeout_ms=timeout_ms,
            )
        )

    def type_text(
        self,
        *,
        page_id: str | None = None,
        selector: str,
        text: str,
        clear: bool = True,
        press_enter: bool = False,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        return self._run(
            self._type_text(
                page_id=page_id,
                selector=selector,
                text=text,
                clear=clear,
                press_enter=press_enter,
                timeout_ms=timeout_ms,
            )
        )

    def press_key(
        self,
        *,
        page_id: str | None = None,
        key: str,
    ) -> dict[str, Any]:
        return self._run(
            self._press_key(
                page_id=page_id,
                key=key,
            )
        )


_browser_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


def _reset_browser_manager_for_tests() -> None:
    global _browser_manager
    _browser_manager = None
