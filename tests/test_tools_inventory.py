import os
import pytest
from fastapi.testclient import TestClient

os.environ["WORKER_TOKEN"] = "test-token-12345"
from worker.app import app
from worker.tasks import TASK_HANDLERS

AUTH = {"Authorization": "Bearer test-token-12345"}


@pytest.fixture
def client():
    return TestClient(app)


# ── Auth ──────────────────────────────────────────────────────────


class TestToolsInventoryAuth:
    def test_no_auth_returns_401(self, client):
        resp = client.get("/tools/inventory")
        assert resp.status_code == 401

    def test_bad_token_returns_401(self, client):
        resp = client.get("/tools/inventory", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401


# ── Response format ───────────────────────────────────────────────


class TestToolsInventoryFormat:
    def test_response_has_required_keys(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "timestamp" in data
        assert "total_tasks" in data
        assert "tasks" in data
        assert "skills" in data
        assert "categories" in data

    def test_total_tasks_matches_handlers(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        assert data["total_tasks"] == len(TASK_HANDLERS)

    def test_all_handlers_present(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        returned_names = {t["name"] for t in data["tasks"]}
        for handler_name in TASK_HANDLERS:
            assert handler_name in returned_names, f"{handler_name} missing from inventory"

    def test_task_entry_has_required_fields(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        for task in data["tasks"]:
            assert "name" in task
            assert "module" in task
            assert "category" in task


# ── Categories ────────────────────────────────────────────────────


class TestToolsInventoryCategories:
    def test_categories_sum_equals_total(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        cat_sum = sum(data["categories"].values())
        assert cat_sum == data["total_tasks"]

    def test_known_categories_present(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        # At minimum: notion, windows, ai, figma should have tasks
        for expected in ["notion", "windows", "ai", "figma"]:
            assert expected in data["categories"], f"Category {expected} missing"
            assert data["categories"][expected] > 0

    def test_figma_category_count(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        figma_tasks = [t for t in data["tasks"] if t["category"] == "figma"]
        assert data["categories"]["figma"] == len(figma_tasks)

    def test_ping_is_system_category(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        ping = next(t for t in data["tasks"] if t["name"] == "ping")
        assert ping["category"] == "system"


# ── Skills ────────────────────────────────────────────────────────


class TestToolsInventorySkills:
    def test_skills_detected(self, client):
        """At minimum the figma skill should be detected."""
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        assert isinstance(data["skills"], list)
        assert "figma" in data["skills"]

    def test_skills_detail_has_name_and_description(self, client):
        resp = client.get("/tools/inventory", headers=AUTH)
        data = resp.json()
        assert "skills_detail" in data
        for skill in data["skills_detail"]:
            assert "name" in skill
            assert "description" in skill
