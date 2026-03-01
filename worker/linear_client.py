"""
Linear API client — create/update issues for Rick.

Uses GraphQL API: https://api.linear.app/graphql
Auth: Authorization: Bearer <LINEAR_API_KEY>
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("worker.linear")

LINEAR_API_URL = "https://api.linear.app/graphql"
TIMEOUT = 30.0


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": api_key if api_key.startswith("Bearer") else f"Bearer {api_key}",
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
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            errs = data["errors"]
            raise RuntimeError(f"Linear API errors: {errs}")
        return data.get("data", {})


def list_teams(api_key: str) -> List[Dict[str, Any]]:
    """
    List teams in the workspace.

    Returns:
        [{"id": "...", "key": "UMB", "name": "Umbral"}, ...]
    """
    q = """
    query Teams {
      teams {
        nodes {
          id
          key
          name
        }
      }
    }
    """
    data = _gql(api_key, q)
    nodes = data.get("teams", {}).get("nodes", [])
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
    Get team by key (e.g. "UMB").

    Returns:
        {"id": "...", "key": "UMB", "name": "Umbral"} or None
    """
    teams = list_teams(api_key)
    key_upper = key.upper()
    for t in teams:
        if (t.get("key") or "").upper() == key_upper:
            return t
    return None
