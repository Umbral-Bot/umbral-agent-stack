"""
Shared test fixtures.

Sets WORKER_TOKEN and RATE_LIMIT_RPM *before* any worker module is imported,
and resets the rate limiter between tests.
"""

import os

os.environ["WORKER_TOKEN"] = "test-token-12345"
os.environ["RATE_LIMIT_RPM"] = "999999"
os.environ["RATE_LIMIT_INTERNAL_RPM"] = "999999"

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
    """Keep worker.config.WORKER_TOKEN in sync with os.environ."""
    try:
        import worker.config as cfg
        cfg.WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "test-token-12345")
    except Exception:
        pass
