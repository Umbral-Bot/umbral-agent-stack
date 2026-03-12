"""Browser automation task handlers backed by Playwright."""

from __future__ import annotations

from typing import Any, Dict

from ..browser.manager import get_browser_manager

_ALLOWED_WAIT_UNTIL = {"commit", "domcontentloaded", "load", "networkidle"}


def handle_browser_navigate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    url = str(input_data.get("url") or "").strip()
    if not url:
        raise ValueError("'url' is required")
    wait_until = str(input_data.get("wait_until") or "load").strip().lower()
    if wait_until not in _ALLOWED_WAIT_UNTIL:
        raise ValueError(f"Invalid wait_until: {wait_until}")
    timeout_ms = input_data.get("timeout_ms")
    if timeout_ms is not None:
        try:
            timeout_ms = int(timeout_ms)
        except (TypeError, ValueError) as exc:
            raise ValueError("'timeout_ms' must be an integer") from exc
    return get_browser_manager().navigate(
        url=url,
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        wait_until=wait_until,
        timeout_ms=timeout_ms,
    )


def handle_browser_read_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return get_browser_manager().read_page(
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        selector=(str(input_data.get("selector")).strip() or None) if input_data.get("selector") else None,
        include_html=bool(input_data.get("include_html", False)),
    )


def handle_browser_screenshot(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return get_browser_manager().screenshot(
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        path=(str(input_data.get("path")).strip() or None) if input_data.get("path") else None,
        full_page=bool(input_data.get("full_page", True)),
        selector=(str(input_data.get("selector")).strip() or None) if input_data.get("selector") else None,
        return_b64=bool(input_data.get("return_b64", False)),
    )


def handle_browser_click(input_data: Dict[str, Any]) -> Dict[str, Any]:
    selector = str(input_data.get("selector") or "").strip()
    if not selector:
        raise ValueError("'selector' is required")
    timeout_ms = input_data.get("timeout_ms")
    if timeout_ms is not None:
        try:
            timeout_ms = int(timeout_ms)
        except (TypeError, ValueError) as exc:
            raise ValueError("'timeout_ms' must be an integer") from exc
    return get_browser_manager().click(
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        selector=selector,
        timeout_ms=timeout_ms,
    )


def handle_browser_type_text(input_data: Dict[str, Any]) -> Dict[str, Any]:
    selector = str(input_data.get("selector") or "").strip()
    if not selector:
        raise ValueError("'selector' is required")
    text = str(input_data.get("text") or "")
    if not text:
        raise ValueError("'text' is required")
    timeout_ms = input_data.get("timeout_ms")
    if timeout_ms is not None:
        try:
            timeout_ms = int(timeout_ms)
        except (TypeError, ValueError) as exc:
            raise ValueError("'timeout_ms' must be an integer") from exc
    return get_browser_manager().type_text(
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        selector=selector,
        text=text,
        clear=bool(input_data.get("clear", True)),
        press_enter=bool(input_data.get("press_enter", False)),
        timeout_ms=timeout_ms,
    )


def handle_browser_press_key(input_data: Dict[str, Any]) -> Dict[str, Any]:
    key = str(input_data.get("key") or "").strip()
    if not key:
        raise ValueError("'key' is required")
    return get_browser_manager().press_key(
        page_id=(str(input_data.get("page_id")).strip() or None) if input_data.get("page_id") else None,
        key=key,
    )
