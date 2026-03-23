from scripts.audit_traceability_check import _check_audit_fields, _identify_gaps


def test_audit_fields_counts_source_kind_coverage():
    events = [
        {
            "event": "task_completed",
            "task_id": "t1",
            "task": "ping",
            "team": "system",
            "model": "gpt-4o-mini",
            "duration_ms": 10,
            "trace_id": "trace-1",
            "source": "openclaw_gateway",
            "source_kind": "tool_enqueue",
            "task_type": "general",
        },
        {
            "event": "task_failed",
            "task_id": "t2",
            "task": "ping",
            "team": "system",
            "error": "boom",
            "trace_id": "trace-2",
            "task_type": "general",
        },
    ]

    report = _check_audit_fields(events)

    assert report["total_task_events"] == 2
    assert report["fields"]["source_kind"]["present"] == 1
    assert report["fields"]["source_kind"]["coverage_pct"] == 50.0


def test_identify_gaps_flags_missing_source_kind_coverage():
    gaps = _identify_gaps(
        file_stats={"exists": True, "size_mb": 1, "rotation_files": 1},
        structure={"event_counts": {"task_queued": 1}},
        audit_fields={
            "fields": {
                "trace_id": {"coverage_pct": 100.0},
                "source": {"coverage_pct": 100.0},
                "source_kind": {"coverage_pct": 0.0},
                "task_type": {"coverage_pct": 100.0},
            }
        },
        retention={"has_rotation": True, "current_size_mb": 1, "over_size_limit": False},
    )

    assert any(gap["id"] == "G3b" for gap in gaps)
