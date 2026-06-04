from __future__ import annotations

import json

from infra import eval_harness


def test_core_eval_harness_all_suites_pass():
    report = eval_harness.run_suites(["all"])

    assert report["overall_status"] == "pass"
    assert report["read_only"] is True
    assert report["network"] == "none"
    assert report["llm_calls"] == 0
    assert report["summary"]["suites_total"] == 3
    assert {suite["name"] for suite in report["suites"]} == set(eval_harness.ALL_SUITES)


def test_stage5_suite_reports_precision_at_5():
    result = eval_harness.run_stage5_ranking()

    assert result.status == "pass"
    assert result.metrics["precision_at_5"] >= result.metrics["threshold"]
    assert len(result.metrics["top5_ids"]) == 5


def test_agent_output_gold_set_is_offline_by_default():
    result = eval_harness.run_agent_output_gold_set()

    assert result.status == "pass"
    assert result.metrics["total_cases"] >= 5
    assert result.metrics["offline_by_default"] is True
    assert "gmail.router" in result.metrics["tasks_covered"]
    assert "calendar.propose" in result.metrics["tasks_covered"]


def test_write_report_files(tmp_path):
    report = eval_harness.run_suites(["agent_output_gold_set"])
    paths = eval_harness.write_report_files(report, tmp_path)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert loaded["overall_status"] == "pass"
    assert "Core Eval Harness Report" in paths["markdown"].read_text(encoding="utf-8")
