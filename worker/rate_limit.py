"""
S7 — Rate limiting para Worker.

Sliding window in-memory. Límite configurable por ventana (requests por minuto).
"""

import logging
import time
from threading import Lock
from typing import Dict

logger = logging.getLogger("worker.rate_limit")

# Default: 120 req/min por cliente (IP o token hash)
DEFAULT_LIMIT = 120
DEFAULT_WINDOW_SEC = 60

_lock = Lock()
_window: Dict[str, list] = {}
try:
    from .config import WORKER_RATE_LIMIT_PER_MIN as _cfg
    _configured_limit = _cfg
except Exception:
    _configured_limit = DEFAULT_LIMIT
_configured_window = DEFAULT_WINDOW_SEC


def _cleanup_expired(client_key: str, now: float) -> int:
    """Remove timestamps older than window, return count remaining."""
    ts_list = _window.get(client_key, [])
    cutoff = now - _configured_window
    valid = [t for t in ts_list if t > cutoff]
    if valid:
        _window[client_key] = valid
    else:
        _window.pop(client_key, None)
    return len(valid)


def check_rate_limit(client_key: str) -> tuple[bool, int]:
    """
    Check if client is within rate limit. Record this request.
    Returns (allowed, remaining_requests) where remaining may be 0 if at limit.
    """
    with _lock:
        now = time.monotonic()
        count = _cleanup_expired(client_key, now)
        if count >= _configured_limit:
            logger.warning("Rate limit exceeded for %s (%d/%d)", client_key[:16], count, _configured_limit)
            return False, 0
        if client_key not in _window:
            _window[client_key] = []
        _window[client_key].append(now)
        remaining = max(0, _configured_limit - count - 1)
        return True, remaining
