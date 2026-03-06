"""
Deprecated compatibility wrapper for the active rate limiter.

Prefer importing ``worker.rate_limiter`` directly.
"""

from .config import RATE_LIMIT_RPM
from .rate_limiter import RateLimiter

_compat_limiter = RateLimiter(max_requests=RATE_LIMIT_RPM, window_seconds=60)


def check_rate_limit(client_key: str) -> tuple[bool, int]:
    """Backwards-compatible wrapper around ``worker.rate_limiter``."""
    return _compat_limiter.is_allowed(client_key)


__all__ = ["RateLimiter", "check_rate_limit"]
