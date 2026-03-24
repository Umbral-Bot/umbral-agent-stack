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
    ]

    report = snapshot.build_snapshot(events, days=7)

    assert report["panels"]["components"]["dashboard_rick"]["updated"] == 1
    assert report["panels"]["components"]["openclaw_panel"]["skipped"] == 1
    assert report["openclaw_runtime"]["completed"] == 1
    assert report["openclaw_runtime"]["failed"] == 1
    assert report["llm_usage"]["tracked"] is True
    assert report["llm_usage"]["tokens_total"] == 570
    assert report["llm_usage"]["by_provider"][0]["name"] == "vertex"


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
        "limitations": ["Limitation A", "Limitation B"],
    }

    rendered = snapshot.to_markdown(report)

    assert "## Paneles" in rendered
    assert "dashboard_rick" in rendered
    assert "## LLM usage" in rendered
    assert "Limitation A" in rendered
