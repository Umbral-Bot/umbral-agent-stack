"""
Tests for S6 observability: OODA report and self-evaluation.
"""
import json
import pytest

try:
    import fakeredis
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

pytestmark = pytest.mark.skipif(not HAS_FAKEREDIS, reason="fakeredis not installed")


class TestOodaReport:
    def test_report_from_redis_with_tasks(self, monkeypatch):
        r = fakeredis.FakeRedis(decode_responses=True)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        import scripts.ooda_report as ooda
        monkeypatch.setattr(ooda, "_connect_redis", lambda: r)

        r.set("umbral:task:t1", json.dumps({"status": "done", "task": "ping"}))
        r.set("umbral:task:t2", json.dumps({"status": "failed", "task": "ping"}))
        r.set("umbral:task:t3", json.dumps({"status": "blocked", "task": "ping"}))

        result = ooda._report_from_redis()
        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["blocked"] == 1
        assert result["source"] == "redis"

    def test_report_from_redis_unavailable(self, monkeypatch):
        import scripts.ooda_report as ooda
        monkeypatch.setattr(ooda, "_connect_redis", lambda: None)

        result = ooda._report_from_redis()
        assert result["source"] == "redis_unavailable"

    def test_to_markdown_output(self):
        import scripts.ooda_report as ooda
        report = {
            "period": {"start": "2026-02-21T00:00:00", "end": "2026-02-28T00:00:00"},
            "tasks": {"completed": 5, "failed": 1, "blocked": 0, "pending": 2, "source": "redis"},
            "llm": {"traces": 0, "generations": 0, "source": "langfuse_stub"},
            "generated_at": "2026-02-28T01:00:00",
        }
        md = ooda.to_markdown(report)
        assert "Completadas: 5" in md
        assert "Fallidas: 1" in md
        assert "Pendientes: 2" in md


class TestSelfEval:
    def test_evaluate_task_ok(self):
        from scripts.evals_self_check import evaluate_task
        task = {
            "task_id": "t1",
            "task": "ping",
            "team": "system",
            "status": "done",
            "result": {"ok": True, "echo": {"message": "hi"}},
            "started_at": 1000.0,
            "completed_at": 1002.0,
        }
        ev = evaluate_task(task)
        assert ev["overall"] > 0.5
        assert ev["scores"]["ok_flag"] == 1.0
        assert ev["duration_sec"] == 2.0

    def test_evaluate_task_no_result(self):
        from scripts.evals_self_check import evaluate_task
        task = {
            "task_id": "t2",
            "task": "bad",
            "team": "system",
            "status": "done",
            "result": {},
            "started_at": 1000.0,
            "completed_at": 1005.0,
        }
        ev = evaluate_task(task)
        assert ev["scores"]["ok_flag"] == 0.0

    def test_run_evals_no_redis(self, monkeypatch):
        from scripts.evals_self_check import run_evals
        monkeypatch.setattr("scripts.evals_self_check._connect_redis", lambda: None)
        result = run_evals()
        assert result[0].get("error") == "Redis not available"

    def test_to_markdown(self):
        from scripts.evals_self_check import to_markdown
        evals = [
            {"task_id": "t1", "task": "ping", "team": "system", "overall": 0.85,
             "duration_sec": 2.0, "scores": {"latency": 1.0, "ok_flag": 1.0, "result_richness": 0.5, "has_result": 1.0}},
        ]
        md = to_markdown(evals)
        assert "ping" in md
        assert "0.85" in md


class TestObservabilityHandlers:
    def test_ooda_handler_returns_report(self, monkeypatch):
        import scripts.ooda_report as ooda
        monkeypatch.setattr(ooda, "_connect_redis", lambda: None)

        from worker.tasks.observability import handle_ooda_report
        result = handle_ooda_report({"format": "markdown"})
        assert result["ok"] is True
        assert "OODA Weekly Report" in result["report"]

    def test_self_eval_handler_no_redis(self, monkeypatch):
        monkeypatch.setattr("scripts.evals_self_check._connect_redis", lambda: None)

        from worker.tasks.observability import handle_self_eval
        result = handle_self_eval({"format": "markdown"})
        assert result["ok"] is True
        assert "Redis not available" in result["report"]
