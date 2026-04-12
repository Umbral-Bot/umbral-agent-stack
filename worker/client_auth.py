"""
Client Auth — API key management and multi-tenant client registry.

Provides:
- API key generation, validation, and revocation
- Per-client tier enforcement (rate limits, task access)
- Usage tracking per client
- Redis-backed storage with in-memory fallback

Env vars:
    CLIENT_AUTH_STORE — "redis" or "memory" (default: redis if available)
    REDIS_URL         — Redis connection URL (for redis store)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("worker.client_auth")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TIERS_CACHE: Optional[Dict[str, Any]] = None
_TIERS_CACHE_MTIME: float = 0.0

# API key prefix for identification
API_KEY_PREFIX = "ubim_"
API_KEY_LENGTH = 40  # total length including prefix


# ---------------------------------------------------------------------------
# Tier config
# ---------------------------------------------------------------------------


def load_tiers(force: bool = False) -> Dict[str, Any]:
    """Load tier config from config/client_tiers.yaml with file-mtime caching."""
    global _TIERS_CACHE, _TIERS_CACHE_MTIME

    path = _REPO_ROOT / "config" / "client_tiers.yaml"
    if not path.is_file():
        return {"tiers": {}, "default_tier": "free", "admin": {}}

    mtime = path.stat().st_mtime
    if not force and _TIERS_CACHE is not None and mtime == _TIERS_CACHE_MTIME:
        return _TIERS_CACHE

    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load client_tiers.yaml: %s", e)
        return {"tiers": {}, "default_tier": "free", "admin": {}}

    _TIERS_CACHE = data
    _TIERS_CACHE_MTIME = mtime
    return data


def get_tier_config(tier_name: str) -> Dict[str, Any]:
    """Get config for a specific tier."""
    data = load_tiers()
    tiers = data.get("tiers", {})
    return tiers.get(tier_name, tiers.get(data.get("default_tier", "free"), {}))


def is_task_allowed(tier_name: str, task_name: str) -> bool:
    """Check if a task is allowed for the given tier."""
    tier = get_tier_config(tier_name)
    allowed = tier.get("allowed_tasks", "*")
    blocked = tier.get("blocked_tasks", [])

    if isinstance(blocked, list) and task_name in blocked:
        return False
    if allowed == "*":
        return True
    if isinstance(allowed, list):
        return task_name in allowed
    return True


# ---------------------------------------------------------------------------
# Client record
# ---------------------------------------------------------------------------


@dataclass
class ClientRecord:
    """A registered API client."""
    client_id: str
    name: str
    email: str
    tier: str
    api_key_hash: str
    created_at: float = field(default_factory=time.time)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# API key generation
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    """Generate a new API key with prefix."""
    random_part = secrets.token_urlsafe(API_KEY_LENGTH - len(API_KEY_PREFIX))
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """SHA-256 hash of the API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def is_client_api_key(value: str) -> bool:
    """Check if a string looks like a client API key (has our prefix)."""
    return isinstance(value, str) and value.startswith(API_KEY_PREFIX)


# ---------------------------------------------------------------------------
# Client store interface + in-memory implementation
# ---------------------------------------------------------------------------


class ClientStore:
    """Base interface for client storage."""

    def register(self, name: str, email: str, tier: str = "") -> tuple[ClientRecord, str]:
        """Register a new client. Returns (record, raw_api_key)."""
        raise NotImplementedError

    def get_by_api_key(self, api_key: str) -> Optional[ClientRecord]:
        """Look up client by raw API key."""
        raise NotImplementedError

    def get_by_id(self, client_id: str) -> Optional[ClientRecord]:
        """Look up client by ID."""
        raise NotImplementedError

    def revoke(self, client_id: str) -> bool:
        """Deactivate a client. Returns True if found."""
        raise NotImplementedError

    def rotate_key(self, client_id: str) -> Optional[str]:
        """Generate new API key for client. Returns new raw key or None."""
        raise NotImplementedError

    def list_clients(self, active_only: bool = True) -> List[ClientRecord]:
        """List all clients."""
        raise NotImplementedError

    def record_usage(self, client_id: str, task: str) -> None:
        """Record a task execution for usage tracking."""
        raise NotImplementedError

    def get_usage(self, client_id: str) -> Dict[str, Any]:
        """Get usage stats for a client."""
        raise NotImplementedError

    def check_daily_limit(self, client_id: str) -> bool:
        """Returns True if the client is within daily limits."""
        raise NotImplementedError


class InMemoryClientStore(ClientStore):
    """In-memory implementation for dev/testing."""

    def __init__(self) -> None:
        self._clients: Dict[str, ClientRecord] = {}
        self._key_index: Dict[str, str] = {}  # hash → client_id
        self._usage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def register(self, name: str, email: str, tier: str = "") -> tuple[ClientRecord, str]:
        if not tier:
            data = load_tiers()
            tier = data.get("default_tier", "free")

        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        client_id = hashlib.sha256(f"{email}:{time.time()}:{secrets.token_hex(8)}".encode()).hexdigest()[:16]

        record = ClientRecord(
            client_id=client_id,
            name=name,
            email=email,
            tier=tier,
            api_key_hash=key_hash,
        )
        self._clients[client_id] = record
        self._key_index[key_hash] = client_id
        logger.info("Registered client '%s' (%s) tier=%s", name, client_id, tier)
        return record, api_key

    def get_by_api_key(self, api_key: str) -> Optional[ClientRecord]:
        key_hash = hash_api_key(api_key)
        client_id = self._key_index.get(key_hash)
        if not client_id:
            return None
        record = self._clients.get(client_id)
        if record and not record.active:
            return None
        return record

    def get_by_id(self, client_id: str) -> Optional[ClientRecord]:
        return self._clients.get(client_id)

    def revoke(self, client_id: str) -> bool:
        record = self._clients.get(client_id)
        if not record:
            return False
        record.active = False
        # Remove key index entry
        self._key_index = {h: cid for h, cid in self._key_index.items() if cid != client_id}
        logger.info("Revoked client '%s' (%s)", record.name, client_id)
        return True

    def rotate_key(self, client_id: str) -> Optional[str]:
        record = self._clients.get(client_id)
        if not record or not record.active:
            return None
        # Remove old key index
        self._key_index = {h: cid for h, cid in self._key_index.items() if cid != client_id}
        # Generate new key
        new_key = generate_api_key()
        new_hash = hash_api_key(new_key)
        record.api_key_hash = new_hash
        self._key_index[new_hash] = client_id
        logger.info("Rotated key for client '%s' (%s)", record.name, client_id)
        return new_key

    def list_clients(self, active_only: bool = True) -> List[ClientRecord]:
        clients = list(self._clients.values())
        if active_only:
            clients = [c for c in clients if c.active]
        return sorted(clients, key=lambda c: c.created_at)

    def record_usage(self, client_id: str, task: str) -> None:
        now = time.time()
        self._usage[client_id].append({"task": task, "timestamp": now})
        day_key = time.strftime("%Y-%m-%d", time.gmtime(now))
        self._daily_counts[client_id][day_key] += 1

    def get_usage(self, client_id: str) -> Dict[str, Any]:
        record = self._clients.get(client_id)
        if not record:
            return {"error": "client not found"}

        today = time.strftime("%Y-%m-%d", time.gmtime())
        daily = self._daily_counts.get(client_id, {})
        today_count = daily.get(today, 0)
        total = sum(daily.values())

        tier = get_tier_config(record.tier)
        daily_limit = tier.get("daily_limit", 0)

        return {
            "client_id": client_id,
            "tier": record.tier,
            "today_requests": today_count,
            "daily_limit": daily_limit,
            "total_requests": total,
            "daily_remaining": max(daily_limit - today_count, 0) if daily_limit else "unlimited",
        }

    def check_daily_limit(self, client_id: str) -> bool:
        """Returns True if the client is within daily limits."""
        record = self._clients.get(client_id)
        if not record:
            return False
        tier = get_tier_config(record.tier)
        daily_limit = tier.get("daily_limit", 0)
        if not daily_limit:
            return True  # unlimited

        today = time.strftime("%Y-%m-%d", time.gmtime())
        today_count = self._daily_counts.get(client_id, {}).get(today, 0)
        return today_count < daily_limit


# ---------------------------------------------------------------------------
# Global store singleton
# ---------------------------------------------------------------------------

_store: Optional[ClientStore] = None


def get_client_store() -> ClientStore:
    """Get or create the global client store."""
    global _store
    if _store is not None:
        return _store
    _store = InMemoryClientStore()
    logger.info("Client store initialized (in-memory)")
    return _store


def set_client_store(store: ClientStore) -> None:
    """Override the global store (for testing)."""
    global _store
    _store = store
