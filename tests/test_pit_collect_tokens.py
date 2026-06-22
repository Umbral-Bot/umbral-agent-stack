"""Tests for the PIT-P6 read-only token ledger collector.

The collector aggregates per-lane token usage from OpenClaw sessions and the
copilot_cli broker audit JSONL. These tests assemble controlled OpenClaw and
audit roots under ``tmp_path`` from the static fixtures in
``tests/fixtures/pit-token-ledger/`` and assert the aggregation, the
``not_reported`` token fallback, exit codes, and YAML output keys.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from scripts.pit.pit_collect_tokens import (  # noqa: E402
    NOT_REPORTED,
    build_ledger,
    collect_copilot_cli,
    collect_openclaw,
    lane_from_agent_dir,
    load_lane_budgets,
    main,
    validate_pit_id,
)

FIXTURES = Path(__file__).parent / "fixtures" / "pit-token-ledger"
PIT_ID = "pit-fixture"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _make_openclaw(root: Path, pit_id: str, lane: str, *, sessions_json: bool, jsonl: bool) -> None:
    sessions = root / "agents" / f"{pit_id}-{lane}" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    if sessions_json:
        (sessions / "sessions.json").write_text(_read("openclaw_sessions.json"), encoding="utf-8")
    if jsonl:
        (sessions / "transcript.jsonl").write_text(_read("openclaw_session.jsonl"), encoding="utf-8")


def _make_audit(root: Path, *names: str) -> Path:
    month = root / "2026-06"
    month.mkdir(parents=True, exist_ok=True)
    for name in names:
        (month / name).write_text(_read(name), encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Case 1 — OpenClaw aggregation per lane
# ---------------------------------------------------------------------------
def test_lane_from_agent_dir_real_world_naming() -> None:
    # pit_id already carries the "pit-" prefix; agent dir is <pit_id>-lane-<slug>
    # (the convention observed on the VPS, NOT a doubled "pit-pit-..." prefix).
    pid = "pit-umbral-bim2-sharepoint-acc"
    assert lane_from_agent_dir(f"{pid}-lane-foundry-tools", pid) == "lane-foundry-tools"
    assert lane_from_agent_dir(pid, pid) == "_pit_root"
    assert lane_from_agent_dir("other-agent", pid) is None
    assert lane_from_agent_dir("main", pid) is None
    # tolerate the documented pit-<pit_id> form only when id lacks the prefix
    assert lane_from_agent_dir("pit-foo-lane-x", "foo") == "lane-x"


def test_collect_openclaw_aggregates_per_lane(tmp_path: Path) -> None:
    oc_root = tmp_path / "openclaw"
    _make_openclaw(oc_root, PIT_ID, "lane-alpha", sessions_json=True, jsonl=True)

    lanes, warnings = collect_openclaw(oc_root, PIT_ID)

    assert "lane-alpha" in lanes
    alpha = lanes["lane-alpha"]
    # sessions.json: 1500/300/1800/cache50 ; jsonl: 400/100/500/cache0
    assert alpha["input"] == 1900
    assert alpha["output"] == 400
    assert alpha["total"] == 2300
    assert alpha["cache_read"] == 50
    # 2 sessions in sessions.json + 1 jsonl transcript file
    assert alpha["sessions"] == 3
    # model chosen by highest aggregated tokens
    assert alpha["model"] == "claude-opus-4.7"
    assert warnings == []


def test_collect_openclaw_ignores_foreign_agents(tmp_path: Path) -> None:
    oc_root = tmp_path / "openclaw"
    _make_openclaw(oc_root, PIT_ID, "lane-alpha", sessions_json=True, jsonl=False)
    # A different tournament's agent must not leak into our pit_id.
    _make_openclaw(oc_root, "pit-other", "lane-zzz", sessions_json=True, jsonl=False)

    lanes, _ = collect_openclaw(oc_root, PIT_ID)

    assert set(lanes) == {"lane-alpha"}


# ---------------------------------------------------------------------------
# Case 2 — copilot_cli aggregation per pit_id/lane_id
# ---------------------------------------------------------------------------
def test_collect_copilot_cli_aggregates_and_filters(tmp_path: Path) -> None:
    audit_root = _make_audit(
        tmp_path / "audit",
        "copilot_audit_dry.jsonl",
        "copilot_audit_real.jsonl",
        "copilot_audit_other_pit.jsonl",
    )

    lanes, warnings = collect_copilot_cli(audit_root, PIT_ID)

    assert set(lanes) == {"lane-alpha"}  # pit-other filtered out
    alpha = lanes["lane-alpha"]
    assert alpha["calls"] == 2
    assert alpha["dry_run"] == 1
    assert alpha["real"] == 1
    assert alpha["exit_codes"] == {"0": 1}
    assert alpha["duration_sec"] == {"sum": 12.5, "avg": 12.5}
    assert warnings == []


def test_collect_copilot_cli_warns_when_no_match(tmp_path: Path) -> None:
    audit_root = _make_audit(tmp_path / "audit", "copilot_audit_other_pit.jsonl")

    lanes, warnings = collect_copilot_cli(audit_root, PIT_ID)

    assert lanes == {}
    assert any("no copilot-cli audit events matched" in w for w in warnings)


# ---------------------------------------------------------------------------
# Case 3 — tokens not_reported when copilot CLI gives no usage
# ---------------------------------------------------------------------------
def test_copilot_tokens_not_reported(tmp_path: Path) -> None:
    audit_root = _make_audit(
        tmp_path / "audit",
        "copilot_audit_dry.jsonl",
        "copilot_audit_real.jsonl",
    )

    lanes, _ = collect_copilot_cli(audit_root, PIT_ID)

    assert lanes["lane-alpha"]["tokens"] == {"source": NOT_REPORTED}


def test_build_ledger_fills_missing_sides(tmp_path: Path) -> None:
    # copilot-only lane must still expose a zeroed openclaw block, and vice versa.
    ledger = build_ledger(
        PIT_ID,
        openclaw_lanes={"lane-alpha": {"input": 10, "output": 2, "total": 12, "cache_read": 0, "model": "m", "sessions": 1, "events": 1}},
        copilot_lanes={"lane-beta": {"calls": 1, "dry_run": 1, "real": 0, "exit_codes": {}, "duration_sec": {"sum": 0.0, "avg": None}, "tokens": {"source": NOT_REPORTED}}},
    )

    lanes = ledger["lanes"]
    assert set(lanes) == {"lane-alpha", "lane-beta"}
    # lane with only openclaw gets a default copilot block (tokens not_reported)
    assert lanes["lane-alpha"]["copilot_cli"]["tokens"]["source"] == NOT_REPORTED
    # lane with only copilot gets a zeroed openclaw block
    assert lanes["lane-beta"]["openclaw"]["total"] == 0
    assert ledger["tournament_total"]["openclaw_total"] == 12
    assert ledger["tournament_total"]["copilot_cli_calls"] == 1


# ---------------------------------------------------------------------------
# Case 4 — invalid pit_id -> exit 2
# ---------------------------------------------------------------------------
def test_invalid_pit_id_rejected() -> None:
    assert validate_pit_id("pit-ok_1.2") is True
    assert validate_pit_id("bad id!") is False
    assert validate_pit_id("") is False
    assert validate_pit_id("x" * 65) is False


def test_main_invalid_pit_id_exit_2(tmp_path: Path) -> None:
    rc = main([
        "--pit-id", "bad id!",
        "--vault-root", str(tmp_path),
        "--openclaw-root", str(tmp_path),
        "--audit-root", str(tmp_path),
        "--output", str(tmp_path / "out.yaml"),
    ])
    assert rc == 2
    assert not (tmp_path / "out.yaml").exists()


# ---------------------------------------------------------------------------
# Case 5 — output YAML written with expected keys
# ---------------------------------------------------------------------------
def test_main_writes_ledger_yaml(tmp_path: Path) -> None:
    oc_root = tmp_path / "openclaw"
    _make_openclaw(oc_root, PIT_ID, "lane-alpha", sessions_json=True, jsonl=True)
    audit_root = _make_audit(
        tmp_path / "audit",
        "copilot_audit_dry.jsonl",
        "copilot_audit_real.jsonl",
    )
    out = tmp_path / "metrics" / "token_ledger.yaml"

    rc = main([
        "--pit-id", PIT_ID,
        "--vault-root", str(tmp_path / "vault"),
        "--openclaw-root", str(oc_root),
        "--audit-root", str(audit_root),
        "--output", str(out),
    ])

    assert rc == 0
    assert out.exists()
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["pit_id"] == PIT_ID
    assert "generated_at_utc" in data
    assert "lanes" in data and "tournament_total" in data
    lane = data["lanes"]["lane-alpha"]
    assert set(lane) == {"openclaw", "copilot_cli", "budget_usd_allocated", "budget_usd_estimated"}
    assert lane["openclaw"]["total"] == 2300
    assert lane["copilot_cli"]["calls"] == 2
    assert lane["copilot_cli"]["tokens"]["source"] == NOT_REPORTED
    assert data["tournament_total"]["copilot_cli_calls"] == 2


def test_main_default_output_under_vault(tmp_path: Path) -> None:
    oc_root = tmp_path / "openclaw"
    _make_openclaw(oc_root, PIT_ID, "lane-alpha", sessions_json=True, jsonl=False)
    vault = tmp_path / "vault"

    rc = main([
        "--pit-id", PIT_ID,
        "--vault-root", str(vault),
        "--openclaw-root", str(oc_root),
        "--audit-root", str(tmp_path / "missing-audit"),
    ])

    assert rc == 0
    expected = vault / "pit" / PIT_ID / "metrics" / "token_ledger.yaml"
    assert expected.exists()


# ---------------------------------------------------------------------------
# Budget (best-effort) — even split across lanes
# ---------------------------------------------------------------------------
def test_load_lane_budgets_even_split(tmp_path: Path) -> None:
    spec_dir = tmp_path / "pit" / PIT_ID / "spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "pit_spec.yaml").write_text(
        "pit_id: pit-fixture\n"
        "budget_usd_total: 30\n"
        "lanes:\n"
        "  - lane_id: lane-alpha\n"
        "    model: claude-opus-4.7\n"
        "  - lane_id: lane-beta\n"
        "    model: gpt-5.4\n"
        "  - lane_id: lane-gamma\n"
        "    budget_usd: 5\n",
        encoding="utf-8",
    )

    budgets = load_lane_budgets(tmp_path, PIT_ID)

    assert budgets["lane-alpha"] == 10.0
    assert budgets["lane-beta"] == 10.0
    # explicit per-lane budget overrides the even split
    assert budgets["lane-gamma"] == 5.0


def test_load_lane_budgets_missing_spec_is_empty(tmp_path: Path) -> None:
    assert load_lane_budgets(tmp_path, PIT_ID) == {}
