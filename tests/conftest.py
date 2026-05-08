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
