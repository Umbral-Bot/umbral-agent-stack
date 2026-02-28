"""
S7 — Generador y validador de ACL Tailscale para Umbral Agent Stack.

Genera la configuración de ACL recomendada y valida la existente.

Uso:
  python -m infra.tailscale_acl generate     # imprime ACL recomendada
  python -m infra.tailscale_acl validate     # valida nodos activos
"""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("infra.tailscale_acl")

RECOMMENDED_ACL = {
    "tagOwners": {
        "tag:umbral-vps": ["autogroup:admin"],
        "tag:umbral-vm": ["autogroup:admin"],
    },
    "acls": [
        {
            "action": "accept",
            "src": ["tag:umbral-vps"],
            "dst": ["tag:umbral-vm:8088"],
            "comment": "VPS Dispatcher -> VM Worker (port 8088 only)",
        },
        {
            "action": "accept",
            "src": ["tag:umbral-vm"],
            "dst": ["tag:umbral-vps:6379"],
            "comment": "VM -> VPS Redis (if Worker needs direct Redis access)",
        },
        {
            "action": "accept",
            "src": ["autogroup:admin"],
            "dst": ["*:*"],
            "comment": "Admin (David) full access",
        },
    ],
    "ssh": [
        {
            "action": "accept",
            "src": ["autogroup:admin"],
            "dst": ["tag:umbral-vps", "tag:umbral-vm"],
            "users": ["autogroup:nonroot", "root"],
        }
    ],
}


def generate_acl() -> str:
    """Genera la ACL JSON recomendada."""
    return json.dumps(RECOMMENDED_ACL, indent=2)


def get_tailscale_status() -> Optional[Dict[str, Any]]:
    """Obtiene el estado de Tailscale desde el CLI."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except FileNotFoundError:
        logger.warning("tailscale CLI not found")
    except subprocess.TimeoutExpired:
        logger.warning("tailscale status timed out")
    except Exception as e:
        logger.error("tailscale status failed: %s", e)
    return None


def validate_nodes() -> Dict[str, Any]:
    """
    Valida que los nodos esperados estén online en Tailscale.
    Retorna reporte de validación.
    """
    status = get_tailscale_status()
    if status is None:
        return {"ok": False, "error": "Cannot get Tailscale status", "nodes": []}

    peers = status.get("Peer", {})
    self_node = status.get("Self", {})

    nodes: List[Dict[str, Any]] = []

    if self_node:
        nodes.append({
            "hostname": self_node.get("HostName", "self"),
            "ip": self_node.get("TailscaleIPs", [None])[0],
            "online": self_node.get("Online", True),
            "os": self_node.get("OS", "unknown"),
            "tags": self_node.get("Tags", []),
            "is_self": True,
        })

    for peer_id, peer in peers.items():
        nodes.append({
            "hostname": peer.get("HostName", peer_id),
            "ip": peer.get("TailscaleIPs", [None])[0],
            "online": peer.get("Online", False),
            "os": peer.get("OS", "unknown"),
            "tags": peer.get("Tags", []),
            "is_self": False,
        })

    issues: List[str] = []

    tagged_vps = [n for n in nodes if "tag:umbral-vps" in n.get("tags", [])]
    tagged_vm = [n for n in nodes if "tag:umbral-vm" in n.get("tags", [])]

    if not tagged_vps:
        issues.append("No node tagged 'tag:umbral-vps'. Apply tag in Tailscale Admin Console.")
    if not tagged_vm:
        issues.append("No node tagged 'tag:umbral-vm'. Apply tag in Tailscale Admin Console.")

    offline = [n for n in nodes if not n.get("online", False)]
    if offline:
        names = [n["hostname"] for n in offline]
        issues.append(f"Offline nodes: {', '.join(names)}")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "nodes": nodes,
        "total": len(nodes),
        "online": sum(1 for n in nodes if n.get("online")),
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Tailscale ACL tool for Umbral")
    p.add_argument("action", choices=["generate", "validate"], help="Action to perform")
    args = p.parse_args()

    if args.action == "generate":
        print(generate_acl())
    elif args.action == "validate":
        result = validate_nodes()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
