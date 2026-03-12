from unittest.mock import patch

import pytest

from worker.tasks.browser import (
    handle_browser_click,
    handle_browser_navigate,
    handle_browser_press_key,
    handle_browser_read_page,
    handle_browser_screenshot,
    handle_browser_type_text,
)


@patch("worker.tasks.browser.get_browser_manager")
def test_handle_browser_click_success(mock_get_manager):
    mock_get_manager.return_value.click.return_value = {"ok": True, "selector": "#go"}

    result = handle_browser_click({"selector": "#go", "timeout_ms": 1500})

    assert result["ok"] is True
    mock_get_manager.return_value.click.assert_called_once_with(
        page_id=None,
        selector="#go",
        timeout_ms=1500,
    )


def test_handle_browser_click_requires_selector():
    with pytest.raises(ValueError, match="'selector' is required"):
        handle_browser_click({})


@patch("worker.tasks.browser.get_browser_manager")
def test_handle_browser_type_text_success(mock_get_manager):
    mock_get_manager.return_value.type_text.return_value = {"ok": True, "chars": 4}

    result = handle_browser_type_text(
        {
            "page_id": "page-1",
            "selector": "input[name='q']",
            "text": "BIM",
            "clear": False,
            "press_enter": True,
            "timeout_ms": 2500,
        }
    )

    assert result["ok"] is True
    mock_get_manager.return_value.type_text.assert_called_once_with(
        page_id="page-1",
        selector="input[name='q']",
        text="BIM",
        clear=False,
        press_enter=True,
        timeout_ms=2500,
    )


def test_handle_browser_type_text_requires_selector_and_text():
    with pytest.raises(ValueError, match="'selector' is required"):
        handle_browser_type_text({"text": "hola"})
    with pytest.raises(ValueError, match="'text' is required"):
        handle_browser_type_text({"selector": "#q"})


@patch("worker.tasks.browser.get_browser_manager")
def test_handle_browser_press_key_success(mock_get_manager):
    mock_get_manager.return_value.press_key.return_value = {"ok": True, "key": "Enter"}

    result = handle_browser_press_key({"page_id": "page-1", "key": "Enter"})

    assert result["ok"] is True
    mock_get_manager.return_value.press_key.assert_called_once_with(
        page_id="page-1",
        key="Enter",
    )


def test_handle_browser_press_key_requires_key():
    with pytest.raises(ValueError, match="'key' is required"):
        handle_browser_press_key({})


@patch("worker.tasks.browser.get_browser_manager")
def test_existing_browser_handlers_still_delegate(mock_get_manager):
    mock_get_manager.return_value.navigate.return_value = {"ok": True}
    mock_get_manager.return_value.read_page.return_value = {"ok": True}
    mock_get_manager.return_value.screenshot.return_value = {"ok": True}

    assert handle_browser_navigate({"url": "https://example.com"})["ok"] is True
    assert handle_browser_read_page({})["ok"] is True
    assert handle_browser_screenshot({})["ok"] is True
