import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

os.environ["WORKER_TOKEN"] = "test-token-12345"
from worker.app import app

AUTH = {"Authorization": "Bearer test-token-12345"}

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def fake_redis():
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis.FakeRedis(decode_responses=True)

class TestQuotaStatus:
    def test_quota_status_no_auth(self, client):
        resp = client.get("/quota/status")
        assert resp.status_code == 401
    
    def test_quota_status_redis_down(self, client):
        with patch("worker.app._get_redis", return_value=None):
            resp = client.get("/quota/status", headers=AUTH)
            assert resp.status_code == 503
            assert "Redis" in resp.json()["detail"]
            
    def test_quota_status_success(self, client, fake_redis):
        with patch("worker.app._get_redis", return_value=fake_redis):
            resp = client.get("/quota/status", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert "timestamp" in data
            assert "providers" in data
            
            # Providers from quota_policy.yaml should be listed with 0 usage
            assert "gemini_pro" in data["providers"]
            assert data["providers"]["gemini_pro"]["used"] == 0
            assert data["providers"]["gemini_pro"]["status"] == "ok"
