"""
Linear API client — create/update issues for Rick.

Uses GraphQL API: https://api.linear.app/graphql
Auth: Personal API key as Authorization: <API_KEY> (sin prefijo Bearer; ver Linear docs).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("worker.linear")

LINEAR_API_URL = "https://api.linear.app/graphql"
TIMEOUT = 30.0


def _headers(api_key: str) -> Dict[str, str]:
    # Linear personal API keys: Authorization: <API_KEY> (no Bearer prefix).
    key = api_key.strip()
    if key.startswith("Bearer "):
        key = key[7:].strip()
    return {
        "Authorization": key,
        "Content-Type": "application/json",
    }


def _gql(api_key: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a GraphQL query/mutation against Linear."""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            LINEAR_API_URL,
            headers=_headers(api_key),
            json={"query": query, "variables": variables or {}},
        )
        try:
            data = resp.json()
        except Exception:
            data = {}
        if resp.status_code >= 400:
            msg = resp.text
            if isinstance(data.get("errors"), list):
                msg = str(data["errors"])
            raise RuntimeError(f"Linear API HTTP {resp.status_code}: {msg}")
        if "errors" in data:
            errs = data["errors"]
            raise RuntimeError(f"Linear API errors: {errs}")
        return data.get("data", {})


def list_teams(api_key: str) -> List[Dict[str, Any]]:
    """
    List teams in the workspace.

    Returns:
        [{"id": "...", "key": "UMB", "name": "Umbral"}, ...]
        (key may be missing if the API does not return it)
    """
    # Query only id and name (documented); key is optional in case schema differs.
    q = """
    query Teams {
      teams {
        nodes {
          id
          name
        }
      }
    }
    """
    data = _gql(api_key, q)
    nodes = data.get("teams", {}).get("nodes", [])
    # Linear Team has a key (e.g. UMB); try to add it via a second field if needed.
    # For now return as-is; get_team_by_key will match by name if key is absent.
    return nodes


def create_issue(
    api_key: str,
    team_id: str,
    title: str,
    description: Optional[str] = None,
    assignee_id: Optional[str] = None,
    priority: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create an issue in Linear.

    Args:
        api_key: LINEAR_API_KEY
        team_id: Team ID (from list_teams)
        title: Issue title
        description: Optional description
        assignee_id: Optional user ID to assign
        priority: Optional 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low

    Returns:
        {"id": "...", "identifier": "UMB-5", "title": "...", "url": "https://..."}
    """
    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        issue {
          id
          identifier
          title
          url
        }
      }
    }
    """
    inp: Dict[str, Any] = {"teamId": team_id, "title": title}
    if description:
        inp["description"] = description
    if assignee_id:
        inp["assigneeId"] = assignee_id
    if priority is not None:
        inp["priority"] = priority

    data = _gql(api_key, mutation, {"input": inp})
    issue = data.get("issueCreate", {}).get("issue", {})
    if not issue:
        raise RuntimeError("Linear issueCreate returned no issue")
    return issue


def get_team_by_key(api_key: str, key: str) -> Optional[Dict[str, Any]]:
    """
    Get team by key (e.g. "UMB") or by name (fallback if API does not return key).

    Returns:
        {"id": "...", "key": "UMB", "name": "Umbral"} or None
    """
    teams = list_teams(api_key)
    key_upper = key.upper()
    for t in teams:
        if (t.get("key") or "").upper() == key_upper:
            return t
        # Fallback: match by name (case-insensitive) if key not in response
        if (t.get("name") or "").upper() == key_upper:
            return t
    return None
