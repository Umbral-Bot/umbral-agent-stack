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
