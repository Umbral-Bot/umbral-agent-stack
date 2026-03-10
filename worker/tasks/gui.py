"""Minimal GUI automation task handlers for interactive Windows sessions."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import tempfile
from pathlib import Path
from typing import Any, Dict


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field}' must be an integer") from exc


def _coerce_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field}' must be a number") from exc


@contextmanager
def _failsafe_disabled(pyautogui):
    previous = getattr(pyautogui, "FAILSAFE", True)
    pyautogui.FAILSAFE = False
    try:
        yield
    finally:
        pyautogui.FAILSAFE = previous


def handle_gui_desktop_status(_input_data: Dict[str, Any]) -> Dict[str, Any]:
    import pyautogui

    try:
        import uiautomation as auto
    except Exception:  # pragma: no cover - optional on non-Windows
        auto = None

    size = pyautogui.size()
    position = pyautogui.position()
    root_name = None
    if auto is not None:
        try:
            root = auto.GetRootControl()
            root_name = getattr(root, "Name", None)
        except Exception:
            root_name = None

    return {
        "ok": True,
        "screen_width": int(size.width),
        "screen_height": int(size.height),
        "cursor_x": int(position.x),
        "cursor_y": int(position.y),
        "root_name": root_name,
    }


def handle_gui_screenshot(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from mss import mss

    path = str(input_data.get("path") or "").strip()
    if path:
        output_path = Path(path)
    else:
        output_path = Path(tempfile.gettempdir()) / "openclaw-gui-shots" / "gui-shot.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with mss() as capture:
        capture.shot(output=str(output_path))

    result: Dict[str, Any] = {
        "ok": True,
        "path": str(output_path),
    }

    if bool(input_data.get("return_b64", False)):
        result["b64_png"] = base64.b64encode(output_path.read_bytes()).decode("ascii")

    return result


def handle_gui_click(input_data: Dict[str, Any]) -> Dict[str, Any]:
    import pyautogui

    x = _coerce_int(input_data.get("x"), "x")
    y = _coerce_int(input_data.get("y"), "y")
    clicks = _coerce_int(input_data.get("clicks", 1), "clicks")
    interval = _coerce_float(input_data.get("interval", 0.0), "interval")
    duration = _coerce_float(input_data.get("duration", 0.0), "duration")
    button = str(input_data.get("button") or "left").strip().lower()
    if button not in {"left", "right", "middle"}:
        raise ValueError("'button' must be one of: left, right, middle")

    with _failsafe_disabled(pyautogui):
        pyautogui.moveTo(x, y, duration=duration)
        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
        position = pyautogui.position()
    return {
        "ok": True,
        "x": int(position.x),
        "y": int(position.y),
        "button": button,
        "clicks": clicks,
    }


def handle_gui_type_text(input_data: Dict[str, Any]) -> Dict[str, Any]:
    import pyautogui

    text = str(input_data.get("text") or "")
    if not text:
        raise ValueError("'text' is required")
    interval = _coerce_float(input_data.get("interval", 0.02), "interval")
    with _failsafe_disabled(pyautogui):
        pyautogui.write(text, interval=interval)
    return {
        "ok": True,
        "chars": len(text),
    }


def handle_gui_hotkey(input_data: Dict[str, Any]) -> Dict[str, Any]:
    import pyautogui

    keys = input_data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("'keys' must be a non-empty array of strings")
    normalized = [str(key).strip() for key in keys if str(key).strip()]
    if not normalized:
        raise ValueError("'keys' must contain at least one non-empty string")
    with _failsafe_disabled(pyautogui):
        pyautogui.hotkey(*normalized)
    return {
        "ok": True,
        "keys": normalized,
    }
