import pytest
from scripts.quota_report import build_visual_report

def test_build_visual_report_empty():
    report = build_visual_report({"providers": {}})
    assert "No providers configured" in report

def test_build_visual_report_data():
    data = {"providers": {}}
    report = build_visual_report(data)
    assert "No providers configured" in report

    data = {
        "timestamp": "2026-03-04T14:00:00Z",
        "providers": {
            "gemini_pro": {"used": 410, "limit": 500, "fraction": 0.82, "status": "warn"},
            "azure_foundry": {"used": 69, "limit": 300, "fraction": 0.23, "status": "ok"},
            "claude_pro": {"used": 200, "limit": 200, "fraction": 1.0, "status": "exceeded"},
            "something": {"used": 1500, "limit": 1000, "fraction": 1.5, "status": "restrict"}
        }
    }
    report = build_visual_report(data)
    
    assert "gemini_pro" in report
    assert "82%" in report
    assert "WARN" in report
    assert "azure_foundry" in report
    assert "23%" in report
    assert "OK" in report
    assert "claude_pro" in report
    assert "100%" in report
    assert "EXCEEDED" in report
    assert "something" in report
    assert "150%" in report
    assert "RESTRICT" in report
