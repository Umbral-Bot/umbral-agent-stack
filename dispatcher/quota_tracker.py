"""
QuotaTracker — S4: contador de uso por proveedor, persistido en Redis.

Ventanas por proveedor (config); al expirar ventana se reinicia el contador.
Uso: número de requests (proxy para tokens/tiempo).
"""

import logging
import time
from typing import Any, Dict

logger = logging.getLogger("dispatcher.quota_tracker")

REDIS_KEY_USED = "umbral:quota:{provider}:used"
REDIS_KEY_WINDOW_END = "umbral:quota:{provider}:window_end"


class QuotaTracker:
    """
    Contador por proveedor. Persiste en Redis.
    provider_config: { "claude_pro": { "limit_requests": 200, "window_seconds": 18000 }, ... }
    """

    def __init__(self, redis_client: Any, provider_config: Dict[str, Dict[str, Any]]):
        self.redis = redis_client
        self.config = provider_config or {}

    def _key_used(self, provider: str) -> str:
        return REDIS_KEY_USED.format(provider=provider)

    def _key_window_end(self, provider: str) -> str:
        return REDIS_KEY_WINDOW_END.format(provider=provider)

    def _ensure_window(self, provider: str) -> None:
        """Si la ventana expiró, reinicia used y fija nueva ventana."""
        cfg = self.config.get(provider)
        if not cfg:
            return
        limit = int(cfg.get("limit_requests", 100))
        window_sec = int(cfg.get("window_seconds", 3600))
        key_used = self._key_used(provider)
        key_end = self._key_window_end(provider)
        now = time.time()
        end_raw = self.redis.get(key_end)
        end = float(end_raw) if end_raw else 0
        if now >= end:
            pipe = self.redis.pipeline()
            pipe.set(key_used, 0)
            pipe.set(key_end, now + window_sec)
            pipe.execute()
            logger.debug("Quota window reset for %s (next end %s)", provider, now + window_sec)

    def record_usage(self, provider: str, tokens: int = 0, duration_ms: int = 0) -> None:
        """Registra un uso (1 request; tokens/duration opcionales para futuro)."""
        if provider not in self.config:
            return
        self._ensure_window(provider)
        key_used = self._key_used(provider)
        self.redis.incr(key_used)
        logger.debug("Recorded usage for %s", provider)

    def get_quota_state(self, provider: str) -> float:
        """
        Uso actual como fracción 0.0–1.0 del límite.
        Si no hay config, devuelve 0.0 (sin uso).
        """
        if provider not in self.config:
            return 0.0
        self._ensure_window(provider)
        limit = int(self.config[provider].get("limit_requests", 100))
        key_used = self._key_used(provider)
        used = int(self.redis.get(key_used) or 0)
        if limit <= 0:
            return 0.0
        return min(1.0, used / limit)

    def get_all_quota_states(self) -> Dict[str, float]:
        """Estado de todos los proveedores configurados."""
        return {p: self.get_quota_state(p) for p in self.config}

    def reset_window(self, provider: str) -> None:
        """Fuerza reinicio de ventana (p. ej. cron)."""
        if provider not in self.config:
            return
        key_used = self._key_used(provider)
        key_end = self._key_window_end(provider)
        window_sec = int(self.config[provider].get("window_seconds", 3600))
        now = time.time()
        self.redis.set(key_used, 0)
        self.redis.set(key_end, now + window_sec)
        logger.info("Manual quota window reset for %s", provider)
