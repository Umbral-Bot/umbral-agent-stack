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
          key
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


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def list_labels(api_key: str, team_id: str) -> List[Dict[str, Any]]:
    """Lista los issue labels de un equipo Linear."""
    q = """
    query IssueLabels($teamId: ID!) {
      issueLabels(filter: { team: { id: { eq: $teamId } } }) {
        nodes { id name color }
      }
    }
    """
    data = _gql(api_key, q, {"teamId": team_id})
    return data.get("issueLabels", {}).get("nodes", [])


def get_or_create_label(
    api_key: str,
    team_id: str,
    name: str,
    color: str = "#6B7280",
) -> Optional[str]:
    """
    Retorna el id del label con ese nombre en el equipo.
    Si no existe, lo crea. Retorna el label_id o None si falla.
    """
    for label in list_labels(api_key, team_id):
        if label.get("name", "").lower() == name.lower():
            return label["id"]

    mutation = """
    mutation IssueLabelCreate($input: IssueLabelCreateInput!) {
      issueLabelCreate(input: $input) {
        success
        issueLabel { id name }
      }
    }
    """
    try:
        data = _gql(api_key, mutation, {"input": {"teamId": team_id, "name": name, "color": color}})
        created = data.get("issueLabelCreate", {}).get("issueLabel")
        if created:
            logger.info("[LinearClient] Label creado: '%s' → %s", name, created["id"])
            return created["id"]
    except Exception as e:
        logger.warning("[LinearClient] No se pudo crear label '%s': %s", name, e)
    return None


# ---------------------------------------------------------------------------
# Workflow states
# ---------------------------------------------------------------------------

def list_states(api_key: str, team_id: str) -> List[Dict[str, Any]]:
    """Lista los workflow states de un equipo."""
    q = """
    query WorkflowStates($teamId: ID!) {
      workflowStates(filter: { team: { id: { eq: $teamId } } }) {
        nodes { id name type }
      }
    }
    """
    data = _gql(api_key, q, {"teamId": team_id})
    return data.get("workflowStates", {}).get("nodes", [])


def get_state_id_by_name(api_key: str, team_id: str, state_name: str) -> Optional[str]:
    """Busca el ID de un workflow state por nombre (case-insensitive)."""
    for state in list_states(api_key, team_id):
        if state.get("name", "").lower() == state_name.lower():
            return state["id"]
    logger.warning("[LinearClient] State '%s' no encontrado en team %s", state_name, team_id)
    return None


# ---------------------------------------------------------------------------
# Update issue + comments
# ---------------------------------------------------------------------------

def add_comment(api_key: str, issue_id: str, body: str) -> Dict[str, Any]:
    """Agrega un comentario a un issue de Linear."""
    mutation = """
    mutation CommentCreate($input: CommentCreateInput!) {
      commentCreate(input: $input) {
        success
        comment { id body createdAt }
      }
    }
    """
    data = _gql(api_key, mutation, {"input": {"issueId": issue_id, "body": body}})
    return data.get("commentCreate", {})


def update_issue(
    api_key: str,
    issue_id: str,
    state_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Actualiza campos de un issue y/o agrega un comentario.

    Args:
        api_key: LINEAR_API_KEY
        issue_id: UUID del issue en Linear
        state_id: ID del nuevo workflow state
        assignee_id: ID del nuevo assignee
        label_ids: Lista de label IDs a asignar (reemplaza los existentes)
        comment: Texto del comentario a agregar (separado del update)

    Returns:
        {"update": {...}, "comment": {...}}  (las claves presentes según lo que se hizo)
    """
    results: Dict[str, Any] = {}

    input_fields: Dict[str, Any] = {}
    if state_id:
        input_fields["stateId"] = state_id
    if assignee_id:
        input_fields["assigneeId"] = assignee_id
    if label_ids is not None:
        input_fields["labelIds"] = label_ids

    if input_fields:
        mutation = """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              state { name }
              updatedAt
            }
          }
        }
        """
        data = _gql(api_key, mutation, {"id": issue_id, "input": input_fields})
        results["update"] = data.get("issueUpdate", {})

    if comment:
        results["comment"] = add_comment(api_key, issue_id, comment)

    return results
