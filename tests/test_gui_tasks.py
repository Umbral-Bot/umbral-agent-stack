import sys
import types

from worker.tasks.gui import (
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

    class _FakeMss:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def shot(self, output):
            with open(output, "wb") as fh:
                fh.write(b"pngdata")
            return output

    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=lambda: _FakeMss()))

    result = handle_gui_screenshot({"path": str(target), "return_b64": True})

    assert result["ok"] is True
    assert target.exists()
    assert result["path"] == str(target)
    assert result["b64_png"]


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
