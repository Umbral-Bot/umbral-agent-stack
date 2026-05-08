"""
foundry_connection.py — O16.2/051 cablea connection Foundry → AI Search.

Crea (o actualiza) una connection en el Foundry project del AgenteUB que apunta
a `srch-umbral-kb-prod` con auth AAD (UAMI). Idempotente.

Endpoint usado (Azure ARM):
  PUT /subscriptions/{sub}/resourceGroups/{rg}/providers/
      Microsoft.MachineLearningServices/workspaces/{workspace}/
      connections/{name}?api-version=2024-04-01-preview

Auth local: DefaultAzureCredential con scope `https://management.azure.com/.default`.

Uso:
    python scripts/aeco-kb/foundry_connection.py \\
      --foundry-sub <foundry-sub-id> \\
      --foundry-rg <foundry-rg> \\
      --foundry-workspace umbralbim \\
      --search-service srch-umbral-kb-prod \\
      --search-rg rg-umbral-agents-prod \\
      --search-sub f14f61f0-e692-4fbb-900d-73e55a632374
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aeco-foundry-connection")

ARM_API_VERSION = "2024-04-01-preview"
CONNECTION_NAME = "aeco-kb-search"


def upsert_connection(
    foundry_sub: str,
    foundry_rg: str,
    foundry_workspace: str,
    search_service: str,
    search_rg: str,
    search_sub: str,
) -> int:
    import httpx
    from azure.identity import DefaultAzureCredential

    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default").token

    search_resource_id = (
        f"/subscriptions/{search_sub}/resourceGroups/{search_rg}"
        f"/providers/Microsoft.Search/searchServices/{search_service}"
    )
    target = f"https://{search_service}.search.windows.net"

    arm_url = (
        f"https://management.azure.com/subscriptions/{foundry_sub}"
        f"/resourceGroups/{foundry_rg}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{foundry_workspace}"
        f"/connections/{CONNECTION_NAME}"
        f"?api-version={ARM_API_VERSION}"
    )

    body = {
        "properties": {
            "category": "CognitiveSearch",
            "target": target,
            "authType": "AAD",
            "metadata": {
                "ApiType": "Azure",
                "ResourceId": search_resource_id,
                "Description": "AECO KB index alias aeco-kb-es-current — O16.2/051",
            },
        }
    }

    log.info("Upserting Foundry connection '%s' → %s", CONNECTION_NAME, target)
    with httpx.Client(timeout=60) as client:
        r = client.put(arm_url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=body)
        if r.status_code >= 400:
            log.error("ARM PUT failed: %d %s", r.status_code, r.text[:500])
            return 1
        log.info("Connection upserted (HTTP %d).", r.status_code)
        log.info("Resource ID: %s", r.json().get("id", "<unknown>"))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--foundry-sub", required=True, help="Subscription ID del Foundry project.")
    p.add_argument("--foundry-rg", required=True, help="RG del Foundry project (umbralbim-resource).")
    p.add_argument("--foundry-workspace", default="umbralbim", help="Foundry workspace name.")
    p.add_argument("--search-service", default="srch-umbral-kb-prod")
    p.add_argument("--search-rg", default="rg-umbral-agents-prod")
    p.add_argument("--search-sub", default="f14f61f0-e692-4fbb-900d-73e55a632374")
    args = p.parse_args(argv)

    return upsert_connection(
        foundry_sub=args.foundry_sub,
        foundry_rg=args.foundry_rg,
        foundry_workspace=args.foundry_workspace,
        search_service=args.search_service,
        search_rg=args.search_rg,
        search_sub=args.search_sub,
    )


if __name__ == "__main__":
    sys.exit(main())
