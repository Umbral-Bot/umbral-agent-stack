"""Tests for Linear integration."""
import pytest
from unittest.mock import patch


class TestLinearTasks:
    def test_create_issue_no_api_key(self):
        from worker.tasks.linear import handle_linear_create_issue
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", None):
            r = handle_linear_create_issue({"title": "Test"})
        assert r["ok"] is False
        assert "LINEAR_API_KEY" in r["error"]

    def test_create_issue_no_title(self):
        from worker.tasks.linear import handle_linear_create_issue
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"):
            r = handle_linear_create_issue({})
        assert r["ok"] is False
        assert "title" in r["error"].lower()

    def test_list_teams_no_api_key(self):
        from worker.tasks.linear import handle_linear_list_teams
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", None):
            r = handle_linear_list_teams({})
        assert r["ok"] is False
        assert r["teams"] == []

    def test_list_teams_returns_teams(self):
        from worker.tasks.linear import handle_linear_list_teams
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.list_teams", return_value=[{"id": "t1", "key": "UMB", "name": "Umbral"}]):
            r = handle_linear_list_teams({})
        assert r["ok"] is True
        assert len(r["teams"]) == 1
        assert r["teams"][0]["key"] == "UMB"

    def test_create_issue_attaches_to_existing_project(self):
        from worker.tasks.linear import handle_linear_create_issue

        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.list_teams", return_value=[{"id": "team-1", "name": "Umbral"}]), \
             patch("worker.tasks.linear.linear_client.get_or_create_label", return_value="label-1"), \
             patch("worker.tasks.linear.linear_client.create_issue", return_value={
                 "id": "issue-1",
                 "identifier": "UMB-99",
                 "title": "Test issue",
                 "url": "https://linear.app/umbral/issue/UMB-99",
             }), \
             patch("worker.tasks.linear.linear_client.update_issue", return_value={"update": {"success": True}}), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value={
                 "id": "project-1",
                 "name": "Proyecto Embudo Ventas",
                 "url": "https://linear.app/umbral/project/proyecto-embudo-ventas",
                 "state": "backlog",
             }), \
             patch("worker.tasks.linear.linear_client.attach_issue_to_project", return_value={
                 "success": True,
                 "issue": {
                     "id": "issue-1",
                     "identifier": "UMB-99",
                     "project": {
                         "id": "project-1",
                         "name": "Proyecto Embudo Ventas",
                         "url": "https://linear.app/umbral/project/proyecto-embudo-ventas",
                     },
                 },
             }) as mock_attach:
            r = handle_linear_create_issue({
                "title": "Test issue",
                "project_name": "Proyecto Embudo Ventas",
            })

        assert r["ok"] is True
        assert r["project"]["id"] == "project-1"
        mock_attach.assert_called_once_with("lin_api_fake", "issue-1", "project-1")

    def test_create_project_returns_existing_by_name(self):
        from worker.tasks.linear import handle_linear_create_project

        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value={
                 "id": "project-1",
                 "name": "Proyecto Embudo Ventas",
                 "url": "https://linear.app/umbral/project/proyecto-embudo-ventas",
                 "state": "backlog",
             }):
            r = handle_linear_create_project({"name": "Proyecto Embudo Ventas"})

        assert r["ok"] is True
        assert r["created"] is False
        assert r["project"]["id"] == "project-1"

    def test_list_projects_returns_filtered_projects(self):
        from worker.tasks.linear import handle_linear_list_projects

        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.list_projects", return_value=[
                 {"id": "project-1", "name": "Proyecto Embudo Ventas"}
             ]) as mock_list:
            r = handle_linear_list_projects({"query": "Embudo", "limit": 10})

        assert r["ok"] is True
        assert r["projects"][0]["name"] == "Proyecto Embudo Ventas"
        mock_list.assert_called_once_with("lin_api_fake", limit=10, query="Embudo")

    def test_attach_issue_to_project_resolves_project_name(self):
        from worker.tasks.linear import handle_linear_attach_issue_to_project

        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value={
                 "id": "project-1",
                 "name": "Proyecto Embudo Ventas",
                 "url": "https://linear.app/umbral/project/proyecto-embudo-ventas",
                 "state": "backlog",
             }), \
             patch("worker.tasks.linear.linear_client.attach_issue_to_project", return_value={
                 "success": True,
                 "issue": {"id": "issue-1", "identifier": "UMB-99"},
             }) as mock_attach:
            r = handle_linear_attach_issue_to_project({
                "issue_id": "issue-1",
                "project_name": "Proyecto Embudo Ventas",
            })

        assert r["ok"] is True
        assert r["project"]["id"] == "project-1"
        mock_attach.assert_called_once_with("lin_api_fake", "issue-1", "project-1")

    def test_list_project_issues_requires_project_resolution(self):
        from worker.tasks.linear import handle_linear_list_project_issues

        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value=None):
            r = handle_linear_list_project_issues({"project_name": "No existe"})

        assert r["ok"] is False
        assert r["issues"] == []

    def test_list_project_issues_returns_issues(self):
        from worker.tasks.linear import handle_linear_list_project_issues

        project = {
            "id": "project-1",
            "name": "Proyecto Embudo Ventas",
            "url": "https://linear.app/umbral/project/proyecto-embudo-ventas",
            "state": "backlog",
        }
        issues = [
            {"id": "issue-1", "identifier": "UMB-27", "title": "Paso 1"},
            {"id": "issue-2", "identifier": "UMB-28", "title": "Paso 2"},
        ]
        with patch("worker.tasks.linear.config.LINEAR_API_KEY", "lin_api_fake"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value=project), \
             patch("worker.tasks.linear.linear_client.list_project_issues", return_value=issues) as mock_list:
            r = handle_linear_list_project_issues({
                "project_name": "Proyecto Embudo Ventas",
                "limit": 20,
            })

        assert r["ok"] is True
        assert len(r["issues"]) == 2
        assert r["project"]["id"] == "project-1"
        mock_list.assert_called_once_with("lin_api_fake", "project-1", limit=20)

    def test_linear_client_project_issues_query_uses_id_type(self):
        from worker import linear_client

        seen = {}

        def fake_gql(api_key, query, variables=None):
            seen["api_key"] = api_key
            seen["query"] = query
            seen["variables"] = variables
            return {"issues": {"nodes": []}}

        with patch("worker.linear_client._gql", side_effect=fake_gql):
            result = linear_client.list_project_issues("lin_api_fake", "project-1", limit=10)

        assert result == []
        assert "query ProjectIssues($projectId: ID!, $first: Int!)" in seen["query"]
        assert seen["variables"] == {"projectId": "project-1", "first": 10}

    def test_publish_agent_stack_followup_creates_issue_in_canonical_project(self):
        from worker.tasks.linear import handle_linear_publish_agent_stack_followup

        with patch("worker.tasks.linear._linear_api_key", return_value="lin_api_fake"), \
             patch("worker.tasks.linear._resolve_agent_stack_project", return_value={
                 "id": "project-1",
                 "name": "Mejora Continua Agent Stack",
                 "url": "https://linear.app/umbral/project/mejora-continua-agent-stack",
             }), \
             patch("worker.tasks.linear._resolve_agent_stack_team_id", return_value="team-1"), \
             patch("worker.tasks.linear.linear_client.create_issue", return_value={
                 "id": "issue-1",
                 "identifier": "UMB-120",
                 "title": "[Agent Stack] Unificar dispatcher",
                 "url": "https://linear.app/umbral/issue/UMB-120",
             }), \
             patch("worker.tasks.linear.linear_client.attach_issue_to_project", return_value={
                 "issue": {"project": {"id": "project-1", "name": "Mejora Continua Agent Stack", "url": "https://linear.app/umbral/project/mejora-continua-agent-stack"}}
             }), \
             patch("worker.tasks.linear._ensure_label_ids", return_value=["l1", "l2", "l3"]) as mock_labels, \
             patch("worker.tasks.linear.linear_client.update_issue", return_value={"update": {"success": True}}):
            result = handle_linear_publish_agent_stack_followup({
                "title": "Unificar dispatcher",
                "summary": "Hay dos procesos vivos en VPS",
                "kind": "operational_debt",
                "designated_agent": "codex",
            })

        assert result["ok"] is True
        assert result["project"]["name"] == "Mejora Continua Agent Stack"
        assert result["designated_agent"] == "Codex"
        labels = mock_labels.call_args.args[2]
        assert ("Agent Stack", "#2563EB") in labels
        assert ("Operational Debt", "#DC2626") in labels
        assert ("Agente: Codex", "#0F766E") in labels

    def test_resolve_agent_stack_project_reuses_historical_alias(self):
        from worker.tasks.linear import _resolve_agent_stack_project

        historical = {
            "id": "project-old",
            "name": "Auditoria Mejora Continua - Umbral Agent Stack",
            "url": "https://linear.app/umbral/project/historical",
            "state": "backlog",
        }
        with patch("worker.tasks.linear.config.LINEAR_AGENT_STACK_PROJECT_ID", None), \
             patch("worker.tasks.linear.config.LINEAR_AGENT_STACK_PROJECT_NAME", "Mejora Continua Agent Stack"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", side_effect=[None, historical]) as mock_get, \
             patch("worker.tasks.linear.linear_client.create_project") as mock_create:
            result = _resolve_agent_stack_project("lin_api_fake")

        assert result["id"] == "project-old"
        assert mock_get.call_count == 2
        mock_create.assert_not_called()

    def test_resolve_agent_stack_project_creates_rich_project_if_missing(self):
        from worker.tasks.linear import _resolve_agent_stack_project

        created = {
            "id": "project-new",
            "name": "Mejora Continua Agent Stack",
            "url": "https://linear.app/umbral/project/mejora-continua-agent-stack",
            "state": "backlog",
        }
        with patch("worker.tasks.linear.config.LINEAR_AGENT_STACK_PROJECT_ID", None), \
             patch("worker.tasks.linear.config.LINEAR_AGENT_STACK_PROJECT_NAME", "Mejora Continua Agent Stack"), \
             patch("worker.tasks.linear.linear_client.get_project_by_name", return_value=None), \
             patch("worker.tasks.linear._resolve_agent_stack_team_id", return_value="team-1"), \
             patch("worker.tasks.linear.linear_client.create_project", return_value=created) as mock_create:
            result = _resolve_agent_stack_project("lin_api_fake")

        assert result["id"] == "project-new"
        assert mock_create.call_args.kwargs["name"] == "Mejora Continua Agent Stack"
        assert "drift operativo" in mock_create.call_args.kwargs["description"]
        assert "Usar este proyecto para" in mock_create.call_args.kwargs["content"]

    def test_claim_agent_stack_issue_requires_allowed_agent(self):
        from worker.tasks.linear import handle_linear_claim_agent_stack_issue

        with patch("worker.tasks.linear._linear_api_key", return_value="lin_api_fake"):
            result = handle_linear_claim_agent_stack_issue({
                "identifier": "UMB-120",
                "agent_name": "alice",
            })

        assert result["ok"] is False
        assert "agent_name" in result["error"]

    def test_claim_agent_stack_issue_updates_labels_and_comment(self):
        from worker.tasks.linear import handle_linear_claim_agent_stack_issue

        issue = {
            "id": "issue-1",
            "identifier": "UMB-120",
            "title": "[Agent Stack] Unificar dispatcher",
            "team": {"id": "team-1", "name": "Umbral", "key": "UMB"},
            "project": {"id": "project-1", "name": "Mejora Continua Agent Stack"},
            "labels": {"nodes": [{"id": "existing-label", "name": "Agent Stack"}]},
        }
        refreshed = {
            **issue,
            "labels": {"nodes": [{"id": "existing-label", "name": "Agent Stack"}, {"id": "agent-label", "name": "Agente: Rick"}]},
        }

        with patch("worker.tasks.linear._linear_api_key", return_value="lin_api_fake"), \
             patch("worker.tasks.linear._resolve_agent_stack_project", return_value={"id": "project-1", "name": "Mejora Continua Agent Stack", "url": "https://linear.app/umbral/project/mejora-continua-agent-stack"}), \
             patch("worker.tasks.linear._resolve_issue_for_agent_stack", return_value=issue), \
             patch("worker.tasks.linear._ensure_label_ids", return_value=["agent-label"]), \
             patch("worker.tasks.linear.linear_client.get_state_id_by_name", return_value="state-1"), \
             patch("worker.tasks.linear.linear_client.update_issue", return_value={"update": {"success": True}, "comment": {"success": True}}) as mock_update, \
             patch("worker.tasks.linear.linear_client.get_issue", return_value=refreshed):
            result = handle_linear_claim_agent_stack_issue({
                "identifier": "UMB-120",
                "agent_name": "rick",
                "comment": "Tomar deploy y dejar trazabilidad.",
            })

        assert result["ok"] is True
        assert result["claimed_by"] == "Rick"
        assert mock_update.call_args.kwargs["label_ids"] == ["existing-label", "agent-label"]
        assert "Tomada por: Rick" in mock_update.call_args.kwargs["comment"]

    def test_list_agent_stack_issues_filters_unclaimed(self):
        from worker.tasks.linear import handle_linear_list_agent_stack_issues

        issues = [
            {
                "id": "issue-1",
                "identifier": "UMB-1",
                "title": "[Agent Stack] A",
                "url": "https://linear.app/umbral/issue/UMB-1",
                "state": {"name": "Todo"},
                "assignee": None,
                "labels": {"nodes": [{"id": "l1", "name": "Agent Stack"}]},
            },
            {
                "id": "issue-2",
                "identifier": "UMB-2",
                "title": "[Agent Stack] B",
                "url": "https://linear.app/umbral/issue/UMB-2",
                "state": {"name": "In Progress"},
                "assignee": None,
                "labels": {"nodes": [{"id": "l2", "name": "Agente: Codex"}]},
            },
        ]
        with patch("worker.tasks.linear._linear_api_key", return_value="lin_api_fake"), \
             patch("worker.tasks.linear._resolve_agent_stack_project", return_value={"id": "project-1", "name": "Mejora Continua Agent Stack", "url": "https://linear.app/umbral/project/mejora-continua-agent-stack"}), \
             patch("worker.tasks.linear.linear_client.list_project_issues", return_value=issues):
            result = handle_linear_list_agent_stack_issues({"only_unclaimed": True})

        assert result["ok"] is True
        assert [item["identifier"] for item in result["issues"]] == ["UMB-1"]
