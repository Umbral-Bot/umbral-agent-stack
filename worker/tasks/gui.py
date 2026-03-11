"""Minimal GUI automation task handlers for interactive Windows sessions."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import ctypes
import importlib
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


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


def _capture_with_imagegrab(output_path: Path) -> None:
    image_grab = importlib.import_module("PIL.ImageGrab")
    image = image_grab.grab(all_screens=True)
    image.save(output_path, format="PNG")


def _capture_with_pyautogui(output_path: Path) -> None:
    pyautogui = importlib.import_module("pyautogui")
    image = pyautogui.screenshot()
    image.save(output_path, format="PNG")


def _capture_with_mss(output_path: Path) -> None:
    mss_module = importlib.import_module("mss")
    with mss_module.mss() as capture:
        capture.shot(output=str(output_path))


def _analyze_image(output_path: Path) -> Dict[str, Any]:
    from PIL import Image, ImageFile, ImageStat

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    image = Image.open(output_path).convert("RGB")
    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    extrema = stat.extrema[0]
    return {
        "width": int(image.width),
        "height": int(image.height),
        "mean_luma": float(stat.mean[0]),
        "min_luma": int(extrema[0]),
        "max_luma": int(extrema[1]),
        "black_frame": int(extrema[1]) == 0,
    }


def handle_gui_screenshot(input_data: Dict[str, Any]) -> Dict[str, Any]:
    path = str(input_data.get("path") or "").strip()
    if path:
        output_path = Path(path)
    else:
        output_path = Path(tempfile.gettempdir()) / "openclaw-gui-shots" / "gui-shot.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    preferred = str(input_data.get("method") or "").strip().lower()
    methods = [
        ("imagegrab", _capture_with_imagegrab),
        ("pyautogui", _capture_with_pyautogui),
        ("mss", _capture_with_mss),
    ]
    if preferred:
        methods.sort(key=lambda item: item[0] != preferred)

    diagnostics: List[Dict[str, Any]] = []
    black_result: Dict[str, Any] | None = None
    black_bytes: bytes | None = None

    for method_name, capture_fn in methods:
        try:
            capture_fn(output_path)
            metrics = _analyze_image(output_path)
            diagnostics.append({"method": method_name, **metrics})
            if not metrics["black_frame"]:
                result: Dict[str, Any] = {
                    "ok": True,
                    "path": str(output_path),
                    "capture_method": method_name,
                    "usable_visual": True,
                    "diagnostics": diagnostics,
                    **metrics,
                }
                if bool(input_data.get("return_b64", False)):
                    result["b64_png"] = base64.b64encode(output_path.read_bytes()).decode("ascii")
                return result
            if black_result is None:
                black_result = {
                    "ok": True,
                    "path": str(output_path),
                    "capture_method": method_name,
                    "usable_visual": False,
                    "diagnostics": diagnostics.copy(),
                    **metrics,
                }
                if bool(input_data.get("return_b64", False)):
                    black_bytes = output_path.read_bytes()
        except Exception as exc:
            diagnostics.append({"method": method_name, "error": str(exc)})

    if black_result is not None:
        black_result["diagnostics"] = diagnostics
        if black_bytes is not None:
            black_result["b64_png"] = base64.b64encode(black_bytes).decode("ascii")
        return black_result

    raise RuntimeError(f"GUI screenshot failed with all backends: {diagnostics}")


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


def _list_windows_impl(visible_only: bool = True) -> List[Dict[str, Any]]:
    if not hasattr(ctypes, "windll"):
        raise RuntimeError("Window enumeration is only supported on Windows.")

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    windows: List[Dict[str, Any]] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        if visible_only and not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True

        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buffer, 256)

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_name = None
        process_handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if process_handle:
            try:
                exe_buffer = ctypes.create_unicode_buffer(260)
                size = ctypes.c_ulong(len(exe_buffer))
                if ctypes.windll.psapi.GetProcessImageFileNameW(process_handle, exe_buffer, size):
                    process_name = Path(exe_buffer.value).name
            except Exception:
                process_name = None
            finally:
                kernel32.CloseHandle(process_handle)

        windows.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "class_name": class_buffer.value,
                "pid": int(pid.value),
                "process_name": process_name,
                "visible": bool(user32.IsWindowVisible(hwnd)),
                "minimized": bool(user32.IsIconic(hwnd)),
            }
        )
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows


def _get_foreground_window_info() -> Dict[str, Any] | None:
    if not hasattr(ctypes, "windll"):
        return None

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1 if length > 0 else 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    title = buffer.value.strip()

    class_buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buffer, 256)

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    return {
        "hwnd": int(hwnd),
        "title": title,
        "class_name": class_buffer.value,
        "pid": int(pid.value),
    }


def _app_activate(title: str) -> bool:
    escaped = title.replace("'", "''")
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"$wshell = New-Object -ComObject WScript.Shell; if ($wshell.AppActivate('{escaped}')) {{ exit 0 }} else {{ exit 1 }}",
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return completed.returncode == 0


def _pywinauto_activate(hwnd: int) -> bool:
    try:
        from pywinauto import Application
    except Exception:
        return False

    try:
        app = Application(backend="uia").connect(handle=hwnd)
        window = app.window(handle=hwnd)
        try:
            window.restore()
        except Exception:
            pass
        window.set_focus()
        return True
    except Exception:
        return False


def _activation_titles(title: str) -> List[str]:
    candidates = [title]
    if ":" in title:
        candidates.append(title.split(":", 1)[-1].strip())
    if " - " in title:
        left, right = title.split(" - ", 1)
        candidates.extend([left.strip(), right.strip()])
    unique: List[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _activate_window_impl(
    *,
    exact_title: str | None = None,
    title_contains: str | None = None,
    process_name: str | None = None,
) -> Dict[str, Any]:
    candidates = _list_windows_impl(visible_only=False)

    def matches(item: Dict[str, Any]) -> bool:
        title = str(item.get("title") or "")
        proc = str(item.get("process_name") or "")
        if exact_title and title != exact_title:
            return False
        if title_contains and title_contains.lower() not in title.lower():
            return False
        if process_name and proc.lower() != process_name.lower():
            return False
        return True

    matching = [item for item in candidates if matches(item)]
    if not matching:
        raise ValueError("No matching window found.")

    target = matching[0]
    hwnd = int(target["hwnd"])

    if not hasattr(ctypes, "windll"):
        raise RuntimeError("Window activation is only supported on Windows.")

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    SW_SHOW = 5

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    else:
        user32.ShowWindow(hwnd, SW_SHOW)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)

    def _is_target_foreground(info: Dict[str, Any] | None) -> bool:
        return bool(info and int(info.get("hwnd", 0)) == hwnd)

    time.sleep(0.25)
    foreground = _get_foreground_window_info()
    if not _is_target_foreground(foreground):
        _pywinauto_activate(hwnd)
        time.sleep(0.25)
        foreground = _get_foreground_window_info()
    if not _is_target_foreground(foreground):
        for candidate_title in _activation_titles(str(target["title"])):
            if _app_activate(candidate_title):
                time.sleep(0.25)
                foreground = _get_foreground_window_info()
                if _is_target_foreground(foreground):
                    break
    if not _is_target_foreground(foreground):
        raise RuntimeError(
            f"Window activation did not bring the requested window to foreground. Foreground: {foreground}"
        )

    return {
        "ok": True,
        "hwnd": hwnd,
        "title": target["title"],
        "class_name": target["class_name"],
        "pid": target["pid"],
        "process_name": target["process_name"],
        "foreground": foreground,
    }


def handle_gui_list_windows(input_data: Dict[str, Any]) -> Dict[str, Any]:
    visible_only = bool(input_data.get("visible_only", True))
    windows = _list_windows_impl(visible_only=visible_only)
    return {
        "ok": True,
        "count": len(windows),
        "windows": windows,
    }


def handle_gui_activate_window(input_data: Dict[str, Any]) -> Dict[str, Any]:
    exact_title = str(input_data.get("exact_title") or "").strip() or None
    title_contains = str(input_data.get("title_contains") or "").strip() or None
    process_name = str(input_data.get("process_name") or "").strip() or None
    if not exact_title and not title_contains and not process_name:
        raise ValueError("Provide at least one of: exact_title, title_contains, process_name.")
    return _activate_window_impl(
        exact_title=exact_title,
        title_contains=title_contains,
        process_name=process_name,
    )
