import json

from scripts import openclaw_runtime_snapshot as snapshot


def test_build_snapshot_aggregates_panel_and_llm_usage():
    events = [
        {
            "event": "system_activity",
            "component": "dashboard_rick",
            "status": "updated",
            "ts": "2026-03-24T20:00:00+00:00",
            "trigger": "cron.hourly",
            "duration_ms": 420,
            "notion_reads": 3,
            "notion_writes": 1,
            "worker_calls": 4,
        },
        {
            "event": "system_activity",
            "component": "openclaw_panel",
            "status": "skipped",
            "ts": "2026-03-24T20:05:00+00:00",
            "trigger": "cron.6h",
            "duration_ms": 180,
            "notion_reads": 2,
            "notion_writes": 0,
            "worker_calls": 0,
        },
        {
            "event": "task_completed",
            "source": "openclaw_gateway",
            "task": "linear.list_teams",
            "duration_ms": 130,
            "ts": "2026-03-24T20:10:00+00:00",
        },
        {
            "event": "task_failed",
            "source": "openclaw_gateway",
            "task": "research.web",
            "error": "quota",
            "ts": "2026-03-24T20:11:00+00:00",
        },
        {
            "event": "llm_usage",
            "source": "openclaw_gateway",
            "provider": "openai",
            "model": "gpt-5.4",
            "usage_component": "llm.generate",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "duration_ms": 900,
            "ts": "2026-03-24T20:12:00+00:00",
        },
        {
            "event": "llm_usage",
            "source": "openclaw_gateway",
            "provider": "vertex",
            "model": "gemini-3.1-pro-preview",
            "usage_component": "composite.research_report.report_generation",
            "prompt_tokens": 300,
            "completion_tokens": 120,
            "total_tokens": 420,
            "duration_ms": 1500,
            "ts": "2026-03-24T20:13:00+00:00",
        },
        {
            "event": "research_usage",
            "provider": "gemini_google_search",
            "result_count": 3,
            "source": "openclaw_gateway",
            "ts": "2026-03-24T20:14:00+00:00",
        },
        {
            "event": "research_usage",
            "provider": "tavily",
            "result_count": 1,
            "fallback_reason": "research_provider_quota_exceeded",
            "source": "openclaw_gateway",
            "ts": "2026-03-24T20:15:00+00:00",
        },
    ]

    report = snapshot.build_snapshot(events, days=7)

    assert report["panels"]["components"]["dashboard_rick"]["updated"] == 1
    assert report["panels"]["components"]["openclaw_panel"]["skipped"] == 1
    assert report["openclaw_runtime"]["completed"] == 1
    assert report["openclaw_runtime"]["failed"] == 1
    assert report["llm_usage"]["tracked"] is True
    assert report["llm_usage"]["tokens_total"] == 570
    assert report["llm_usage"]["by_provider"][0]["name"] == "vertex"
    assert report["research_usage"]["tracked"] is True
    assert report["research_usage"]["by_provider"][0]["name"] == "gemini_google_search"
    assert report["research_usage"]["by_provider"][1]["fallback_calls"] == 1
    assert report["sessions_usage"]["tracked"] is False


def test_build_snapshot_reads_sessions_root(tmp_path):
    root = tmp_path / "agents"
    main_sessions = root / "main" / "sessions"
    qa_sessions = root / "rick-qa" / "sessions"
    main_sessions.mkdir(parents=True)
    qa_sessions.mkdir(parents=True)

    (main_sessions / "sessions.json").write_text(
        json.dumps(
            {
                "agent:main:telegram:1": {
                    "updatedAt": 1774303638131,
                    "model": "gpt-5.4",
                    "modelProvider": "openai-codex",
                    "inputTokens": 1000,
                    "outputTokens": 200,
                    "totalTokens": 1200,
                    "cacheRead": 500,
                    "cacheWrite": 0,
                    "origin": {"provider": "telegram", "surface": "telegram"},
                }
            }
        ),
        encoding="utf-8",
    )
    (qa_sessions / "sessions.json").write_text(
        json.dumps(
            {
                "agent:rick-qa:direct:1": {
                    "updatedAt": 1774304638131,
                    "model": "gemini-2.5-flash",
                    "modelProvider": "google",
                    "inputTokens": 500,
                    "outputTokens": 100,
                    "totalTokens": 600,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "origin": {"provider": "openai-user", "surface": "direct"},
                }
            }
        ),
        encoding="utf-8",
    )

    report = snapshot.build_snapshot([], days=7, sessions_root=str(root))

    assert report["sessions_usage"]["tracked"] is True
    assert report["sessions_usage"]["agents"][0]["name"] == "main"
    assert report["sessions_usage"]["agents"][0]["total_tokens"] == 1200
    assert report["sessions_usage"]["by_model"][0]["name"] == "gpt-5.4"
    assert report["sessions_usage"]["recent_sessions"][0]["agent"] == "rick-qa"


def test_to_markdown_mentions_limitations_and_panels():
    report = {
        "generated_at": "2026-03-24T20:30:00+00:00",
        "window_days": 7,
        "total_events": 12,
        "panels": {
            "components": {
                "dashboard_rick": {
                    "updated": 1,
                    "skipped": 0,
                    "failed": 0,
                    "notion_reads": 3,
                    "notion_writes": 1,
                    "worker_calls": 2,
                    "last_status": "updated",
                    "last_trigger": "cron.hourly",
                    "last_ts": "2026-03-24T20:00:00+00:00",
                },
                "openclaw_panel": {
                    "updated": 0,
                    "skipped": 1,
                    "failed": 0,
                    "notion_reads": 2,
                    "notion_writes": 0,
                    "worker_calls": 0,
                    "last_status": "skipped",
                    "last_trigger": "cron.6h",
                    "last_ts": "2026-03-24T20:05:00+00:00",
                },
            },
            "totals": {"notion_reads": 5, "notion_writes": 1, "worker_calls": 2},
        },
        "openclaw_runtime": {
            "source": "openclaw_gateway",
            "task_events_total": 2,
            "completed": 1,
            "failed": 1,
            "blocked": 0,
            "top_tasks": [
                {"name": "linear.list_teams", "completed": 1, "failed": 0, "blocked": 0, "avg_duration_ms": 130}
            ],
            "recent_failures": [],
        },
        "llm_usage": {
            "tracked_events": 1,
            "tracked": True,
            "tokens_total": 150,
            "estimated_cost_proxy_usd": 0.000045,
            "by_provider": [
                {
                    "name": "openai",
                    "calls": 1,
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "avg_duration_ms": 900,
                    "estimated_cost_proxy_usd": 0.000045,
                }
            ],
            "by_usage_component": [
                {
                    "name": "llm.generate",
                    "calls": 1,
                    "total_tokens": 150,
                    "estimated_cost_proxy_usd": 0.000045,
                }
            ],
        },
        "research_usage": {
            "tracked": True,
            "tracked_events": 2,
            "by_provider": [
                {
                    "name": "gemini_google_search",
                    "calls": 1,
                    "fallback_calls": 0,
                    "result_count": 3,
                }
            ],
        },
        "sessions_usage": {
            "tracked": True,
            "root": "/tmp/openclaw-agents",
            "agents": [
                {
                    "name": "main",
                    "sessions": 3,
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "total_tokens": 1200,
                    "cache_read": 500,
                    "estimated_cost_proxy_usd": 0.000270,
                }
            ],
            "by_model": [
                {
                    "name": "gpt-5.4",
                    "provider": "openai-codex",
                    "sessions": 3,
                    "total_tokens": 1200,
                    "estimated_cost_proxy_usd": 0.000270,
                }
            ],
            "recent_sessions": [],
        },
        "limitations": ["Limitation A", "Limitation B"],
    }

    rendered = snapshot.to_markdown(report)

    assert "## Paneles" in rendered
    assert "dashboard_rick" in rendered
    assert "## LLM usage" in rendered
    assert "## Research usage" in rendered
    assert "## Session usage" in rendered
    assert "/tmp/openclaw-agents" in rendered
    assert "Limitation A" in rendered
