"""
Shared test fixtures.

Sets WORKER_TOKEN and RATE_LIMIT_RPM *before* any worker module is imported,
and resets the rate limiter between tests.

NOTE on WORKER_TOKEN handling (Task 040): worker.config._load_openclaw_env()
runs at import time and OVERWRITES os.environ["WORKER_TOKEN"] from
~/.config/openclaw/env when present (VPS dev box). Setting the env var
before importing worker.config is therefore not enough — the file load wins.
We must import worker.config first (let it load the production env), then
forcibly clobber both worker.config.WORKER_TOKEN and os.environ back to the
test value, and patch worker.app.WORKER_TOKEN as well because worker.app
binds the name at import time via `from .config import WORKER_TOKEN`.
"""

import os

_TEST_TOKEN = "test-token-12345"

os.environ["WORKER_TOKEN"] = _TEST_TOKEN
os.environ["RATE_LIMIT_RPM"] = "999999"
os.environ["RATE_LIMIT_INTERNAL_RPM"] = "999999"

# Pre-import worker.config so its _load_openclaw_env hook fires once here
# (not later, after test_worker.py has set its expectations).
import worker.config as _wcfg  # noqa: E402

# Now force-clobber back to the test token. Any subsequent
# `from worker.config import WORKER_TOKEN` (e.g. by worker.app) will bind to
# this value.
_wcfg.WORKER_TOKEN = _TEST_TOKEN
os.environ["WORKER_TOKEN"] = _TEST_TOKEN

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear rate limiter state between tests."""
    try:
        from worker.app import external_limiter, internal_limiter, limiter
        for candidate in (external_limiter, internal_limiter, limiter):
            try:
                candidate.clear()
            except Exception:
                candidate._requests.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _strip_openclaw_proxy_env_leaks(monkeypatch):
    """PKG-MACRO-P5-L2-T5: worker.config._load_openclaw_env() (see module
    docstring above, Task 040) also ingests UMBRAL_DISABLE_CLAUDE and, since
    PKG-MACRO-P5-L2-T4, a real OPENCLAW_GATEWAY_TOKEN from
    ~/.config/openclaw/env into every test process. That leaks the VPS's live
    Claude-routing state into tests, silently flipping "Claude native" /
    "no provider configured" assertions to resolve via openclaw_proxy instead.

    Strip both by default here (centralizes what used to be duplicated across
    5 test files); tests that need either present set it back explicitly via
    monkeypatch.setenv in the test body."""
    monkeypatch.delenv("UMBRAL_DISABLE_CLAUDE", raising=False)
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)


@pytest.fixture(autouse=True)
def _sync_worker_token():
    """Keep worker.config.WORKER_TOKEN AND worker.app.WORKER_TOKEN pinned to
    the test value. worker.app does `from .config import WORKER_TOKEN`, which
    binds the symbol at import time — patching only worker.config is not
    enough for the auth check inside worker.app._authenticate."""
    os.environ["WORKER_TOKEN"] = _TEST_TOKEN
    try:
        import worker.config as cfg
        cfg.WORKER_TOKEN = _TEST_TOKEN
    except Exception:
        pass
    try:
        import worker.app as wapp
        wapp.WORKER_TOKEN = _TEST_TOKEN
    except Exception:
        pass


# ── Shape del sobre del worker (PKG-MACRO-P5-L3-T1) ─────────────────
# Vivía duplicado en test_e2e_validation.py, test_task_result.py y (por import
# test-a-test) test_sim_to_make.py. Como el helper subió a client/, el fixture
# sube con él: un cambio real del shape se toca en un solo lugar.

def worker_status_envelope(payload) -> dict:
    """Lo que devuelve GET /task/<id>/status: el sobre del worker dentro de result.

    El dispatcher guarda en Redis el sobre completo (dispatcher/queue.py:243),
    así que el payload del handler queda un nivel más adentro que en POST /run.
    """
    return {
        "task_id": "e2e-1234",
        "status": "done",
        "task": "llm.generate",
        "team": "lab",
        "result": {
            "ok": True,
            "task_id": "e2e-1234",
            "task": "llm.generate",
            "team": "lab",
            "trace_id": "trace-1234",
            "result": payload,
        },
        "error": None,
    }


def worker_run_envelope(payload) -> dict:
    """Lo que devuelve POST /run (y WorkerClient.run): un solo nivel de result."""
    return {"ok": True, "task_id": "e2e-1234", "task": "llm.generate", "result": payload}


def naive_unwrap(response) -> dict:
    """El unwrap ingenuo previo a T12. Sólo para MUTAR el helper en los tests."""
    return response.get("result", {})
