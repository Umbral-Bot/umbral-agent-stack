"""
Tasks: Client administration for UmbralBIM.io SaaS tier.

- client.register: Register a new API client with tier assignment.
- client.revoke: Deactivate a client's API key.
- client.rotate_key: Generate a new API key for existing client.
- client.list: List registered clients.
- client.usage: Get usage stats for a client.
- client.get: Get client details by ID.

All admin tasks require WORKER_TOKEN (internal only).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from worker.client_auth import get_client_store, is_task_allowed, get_tier_config, load_tiers

logger = logging.getLogger("worker.tasks.client_admin")


def handle_client_register(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a new API client.

    Input:
        name (str, required): Client display name.
        email (str, required): Client email (for identification).
        tier (str, optional): Tier name — free|pro|enterprise (default: free).

    Returns:
        client_id, name, email, tier, api_key (shown ONCE), created_at
    """
    name = str(input_data.get("name", "")).strip()
    email = str(input_data.get("email", "")).strip()
    tier = str(input_data.get("tier", "")).strip()

    if not name:
        raise ValueError("'name' is required")
    if not email:
        raise ValueError("'email' is required")

    # Validate tier
    if tier:
        tiers_data = load_tiers()
        valid_tiers = list(tiers_data.get("tiers", {}).keys())
        if tier not in valid_tiers:
            raise ValueError(f"Invalid tier '{tier}'. Valid: {valid_tiers}")

    store = get_client_store()
    record, api_key = store.register(name=name, email=email, tier=tier)

    return {
        "client_id": record.client_id,
        "name": record.name,
        "email": record.email,
        "tier": record.tier,
        "api_key": api_key,  # shown once at registration
        "created_at": record.created_at,
        "note": "Store this API key securely. It cannot be retrieved again.",
    }


def handle_client_revoke(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Revoke (deactivate) a client's API key.

    Input:
        client_id (str, required): Client ID to revoke.

    Returns:
        {"revoked": true/false, "client_id": "..."}
    """
    client_id = str(input_data.get("client_id", "")).strip()
    if not client_id:
        raise ValueError("'client_id' is required")

    store = get_client_store()
    success = store.revoke(client_id)
    return {"revoked": success, "client_id": client_id}


def handle_client_rotate_key(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a new API key for an existing client (invalidates old key).

    Input:
        client_id (str, required): Client ID.

    Returns:
        {"client_id": "...", "new_api_key": "...", "note": "..."}
    """
    client_id = str(input_data.get("client_id", "")).strip()
    if not client_id:
        raise ValueError("'client_id' is required")

    store = get_client_store()
    new_key = store.rotate_key(client_id)
    if not new_key:
        return {"error": "Client not found or inactive", "client_id": client_id}

    return {
        "client_id": client_id,
        "new_api_key": new_key,
        "note": "Store this API key securely. The old key is now invalid.",
    }


def handle_client_list(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    List registered clients.

    Input:
        active_only (bool, optional): Filter to active clients (default: true).

    Returns:
        {"clients": [...], "count": N}
    """
    active_only = bool(input_data.get("active_only", True))
    store = get_client_store()
    clients = store.list_clients(active_only=active_only)

    return {
        "clients": [
            {
                "client_id": c.client_id,
                "name": c.name,
                "email": c.email,
                "tier": c.tier,
                "active": c.active,
                "created_at": c.created_at,
            }
            for c in clients
        ],
        "count": len(clients),
    }


def handle_client_usage(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get usage stats for a client.

    Input:
        client_id (str, required): Client ID.

    Returns:
        {client_id, tier, today_requests, daily_limit, total_requests, daily_remaining}
    """
    client_id = str(input_data.get("client_id", "")).strip()
    if not client_id:
        raise ValueError("'client_id' is required")

    store = get_client_store()
    return store.get_usage(client_id)


def handle_client_get(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get client details by ID.

    Input:
        client_id (str, required): Client ID.

    Returns:
        Client details (without API key hash).
    """
    client_id = str(input_data.get("client_id", "")).strip()
    if not client_id:
        raise ValueError("'client_id' is required")

    store = get_client_store()
    record = store.get_by_id(client_id)
    if not record:
        return {"error": "Client not found", "client_id": client_id}

    tier_config = get_tier_config(record.tier)
    return {
        "client_id": record.client_id,
        "name": record.name,
        "email": record.email,
        "tier": record.tier,
        "active": record.active,
        "created_at": record.created_at,
        "tier_config": {
            "display_name": tier_config.get("display_name", record.tier),
            "rate_limit_rpm": tier_config.get("rate_limit_rpm", 0),
            "daily_limit": tier_config.get("daily_limit", 0),
            "features": tier_config.get("features", {}),
        },
    }
