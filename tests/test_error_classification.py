import json

from infra.error_classification import classify_error, normalize_error_kind
from infra.ops_logger import OpsLogger


def test_classifies_stable_error_kinds():
    assert classify_error("ReadTimeout while calling Worker").error_kind == "timeout"
    assert classify_error("HTTP 429 quota exceeded").error_kind == "quota"
    assert classify_error("WORKER_TOKEN not configured").error_kind == "config"
    assert classify_error("401 unauthorized token expired").error_kind == "auth"
    assert classify_error("Unknown task: nope").error_kind == "validation"
    assert classify_error("JSONDecodeError malformed payload").error_kind == "data"
    assert classify_error("503 service unavailable").error_kind == "upstream"
    assert classify_error("opaque failure").error_kind == "unknown"


def test_normalizes_unknown_error_kind():
    assert normalize_error_kind("quota") == "quota"
    assert normalize_error_kind("made_up") == "unknown"


def test_ops_logger_task_failed_persists_structured_classification(tmp_path):
    sink = OpsLogger(log_dir=tmp_path)

    sink.task_failed(
        "task-1",
        "research.web",
        "improvement",
        "HTTP 429 quota exceeded",
        model="gemini",
        trace_id="trace-1",
        task_type="research",
    )

    event = json.loads(sink.path.read_text(encoding="utf-8").strip())
    assert event["event"] == "task_failed"
    assert event["error_kind"] == "quota"
    assert event["error_code"] == "task_failed_quota"
    assert event["retryable"] is False
    assert event["trace_id"] == "trace-1"
    assert event["task_type"] == "research"


def test_ops_logger_task_failed_allows_structured_override(tmp_path):
    sink = OpsLogger(log_dir=tmp_path)

    sink.task_failed(
        "task-1",
        "research.web",
        "improvement",
        "[research_provider_quota_exceeded] plan exceeded",
        error_kind="quota",
        error_code="research_provider_quota_exceeded",
        retryable=False,
        provider="tavily",
        upstream_status=432,
    )

    event = json.loads(sink.path.read_text(encoding="utf-8").strip())
    assert event["error_kind"] == "quota"
    assert event["error_code"] == "research_provider_quota_exceeded"
    assert event["retryable"] is False
    assert event["provider"] == "tavily"
    assert event["upstream_status"] == 432
