import sys
import tempfile
import types
from pathlib import Path

from PIL import Image

from worker.tasks.gui import (
    _analyze_image,
    handle_gui_click,
    handle_gui_desktop_status,
    handle_gui_hotkey,
    handle_gui_screenshot,
    handle_gui_type_text,
)


class _Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.width = x
        self.height = y


def _install_pyautogui_stub(monkeypatch):
    calls = {"moveTo": [], "click": [], "write": [], "hotkey": []}
    module = types.SimpleNamespace(
        size=lambda: _Point(1024, 768),
        position=lambda: _Point(100, 200),
        moveTo=lambda x, y, duration=0.0: calls["moveTo"].append((x, y, duration)),
        click=lambda **kwargs: calls["click"].append(kwargs),
        write=lambda text, interval=0.0: calls["write"].append((text, interval)),
        hotkey=lambda *keys: calls["hotkey"].append(keys),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", module)
    return calls


def test_gui_desktop_status(monkeypatch):
    _install_pyautogui_stub(monkeypatch)
    auto_module = types.SimpleNamespace(GetRootControl=lambda: types.SimpleNamespace(Name="Escritorio"))
    monkeypatch.setitem(sys.modules, "uiautomation", auto_module)

    result = handle_gui_desktop_status({})

    assert result["ok"] is True
    assert result["screen_width"] == 1024
    assert result["screen_height"] == 768
    assert result["cursor_x"] == 100
    assert result["cursor_y"] == 200
    assert result["root_name"] == "Escritorio"


def test_gui_screenshot(tmp_path, monkeypatch):
    target = tmp_path / "screen.png"

    image_grab = types.SimpleNamespace(
        grab=lambda all_screens=True: Image.new("RGB", (4, 3), (255, 255, 255))
    )
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", image_grab)

    result = handle_gui_screenshot({"path": str(target), "return_b64": True})

    assert result["ok"] is True
    assert target.exists()
    assert result["path"] == str(target)
    assert result["b64_png"]
    assert result["capture_method"] == "imagegrab"
    assert result["usable_visual"] is True
    assert result["black_frame"] is False


def test_gui_screenshot_uses_temp_path_when_missing(monkeypatch):
    target_root = Path(tempfile.gettempdir()) / "openclaw-gui-shots"
    target = target_root / "gui-shot.png"
    if target.exists():
        target.unlink()

    image_grab = types.SimpleNamespace(
        grab=lambda all_screens=True: Image.new("RGB", (2, 2), (255, 255, 255))
    )
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", image_grab)

    result = handle_gui_screenshot({})

    assert result["ok"] is True
    assert result["path"].endswith("gui-shot.png")
    assert target.exists()


def test_gui_screenshot_falls_back_from_black_imagegrab_to_pyautogui(tmp_path, monkeypatch):
    target = tmp_path / "screen.png"
    image_grab = types.SimpleNamespace(
        grab=lambda all_screens=True: Image.new("RGB", (2, 2), (0, 0, 0))
    )
    pyautogui = types.SimpleNamespace(
        screenshot=lambda: Image.new("RGB", (2, 2), (12, 34, 56))
    )
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", image_grab)
    monkeypatch.setitem(sys.modules, "pyautogui", pyautogui)

    result = handle_gui_screenshot({"path": str(target)})

    assert result["ok"] is True
    assert result["capture_method"] == "pyautogui"
    assert result["usable_visual"] is True
    assert result["black_frame"] is False
    assert result["diagnostics"][0]["method"] == "imagegrab"
    assert result["diagnostics"][0]["black_frame"] is True


def test_gui_screenshot_returns_black_frame_diagnostics_when_all_backends_black(tmp_path, monkeypatch):
    target = tmp_path / "screen.png"
    image_grab = types.SimpleNamespace(
        grab=lambda all_screens=True: Image.new("RGB", (2, 2), (0, 0, 0))
    )
    pyautogui = types.SimpleNamespace(
        screenshot=lambda: Image.new("RGB", (2, 2), (0, 0, 0))
    )

    class _FakeMss:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def shot(self, output):
            Image.new("RGB", (2, 2), (0, 0, 0)).save(output, format="PNG")
            return output

    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", image_grab)
    monkeypatch.setitem(sys.modules, "pyautogui", pyautogui)
    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=lambda: _FakeMss()))

    result = handle_gui_screenshot({"path": str(target)})

    assert result["ok"] is True
    assert result["usable_visual"] is False
    assert result["black_frame"] is True
    assert result["capture_method"] == "imagegrab"
    assert len(result["diagnostics"]) == 3


def test_analyze_image_detects_black_frame(tmp_path):
    target = tmp_path / "black.png"
    Image.new("RGB", (3, 4), (0, 0, 0)).save(target, format="PNG")

    result = _analyze_image(target)

    assert result["width"] == 3
    assert result["height"] == 4
    assert result["black_frame"] is True
    assert result["min_luma"] == 0
    assert result["max_luma"] == 0


def test_gui_click(monkeypatch):
    calls = _install_pyautogui_stub(monkeypatch)

    result = handle_gui_click({"x": 320, "y": 240, "clicks": 2, "button": "left"})

    assert result["ok"] is True
    assert calls["moveTo"] == [(320, 240, 0.0)]
    assert calls["click"] == [{"x": 320, "y": 240, "clicks": 2, "interval": 0.0, "button": "left"}]


def test_gui_type_text(monkeypatch):
    calls = _install_pyautogui_stub(monkeypatch)

    result = handle_gui_type_text({"text": "hola", "interval": 0.05})

    assert result == {"ok": True, "chars": 4}
    assert calls["write"] == [("hola", 0.05)]


def test_gui_hotkey(monkeypatch):
    calls = _install_pyautogui_stub(monkeypatch)

    result = handle_gui_hotkey({"keys": ["ctrl", "l"]})

    assert result == {"ok": True, "keys": ["ctrl", "l"]}
    assert calls["hotkey"] == [("ctrl", "l")]
