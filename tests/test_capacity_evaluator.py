import copy
import json
import socket
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from dispatcher.capacity_evaluator import Evaluation, codex_observations, evaluate

NOW = datetime(2026, 9, 22, 10, tzinfo=timezone.utc)


def test_historical_real_candidates_receipt_is_reproducible():
    folder = Path(__file__).resolve().parents[1] / "examples/t3c1"
    snapshot = Evaluation.model_validate_json((folder / "observed-snapshot.json").read_text(encoding="utf-8"))
    receipt = json.loads((folder / "observed-receipt.json").read_text(encoding="utf-8"))
    assert evaluate(snapshot) == receipt
    assert receipt["status"] == "IDLE"
    assert receipt["dispatch_allowed"] is False
    assert receipt["capacity_observations"][0]["observed_remaining"] == 76
    assert receipt["capacity_observations"][0]["source"] == "tool"


def evidence():
    return dict(observed_at=NOW, received_at=NOW, expires_at=NOW + timedelta(minutes=5),
                evidence_ref="fixture:evidence")


def data():
    return dict(now=NOW, mode="simulation", routes=[dict(
        route_id="codex-tarro", product="codex", account_ref="a", pool_id="p",
        pool_relationships_verified=True, windows_complete=True,
        window_ids=["week"], included_usage_verified=True,
        checks={name: dict(**evidence(), value="pass") for name in
                ("credential", "permission", "health", "capability", "host", "lease")})],
        observations=[dict(**evidence(), product="codex", account_ref="a", pool_id="p",
                           window_id="week", source="fixture", remaining=91, availability="pass")],
        commitments=[dict(**evidence(), pool_id="p", amounts={"week": 0})],
        candidates=[dict(task_id="t1", revision="1", owner="rick", source_ref="fixture:task",
                         status="pending", kind="deliverable", authorized=True, useful=True,
                         ready=True, route_id="codex-tarro", max_cost={"week": 10},
                         cost_evidence_ref="fixture:upper-bound", next_step="Review proposal")])


def run(d):
    return evaluate(Evaluation.model_validate(d))


def reasons(d):
    return run(d)["decisions"][0]["reasons"]


@pytest.mark.parametrize("source", ["ui", "tool"])
def test_simulated_confidence_cannot_be_observed_capacity(source):
    d = data(); d["mode"] = "observed"
    d["observations"][0].update(source=source, confidence="simulated")
    assert "SIMULATED_QUOTA:week" in reasons(d)


@pytest.mark.parametrize("field,expected", [
    ("commitments", "COMMITMENT_WINDOW_SET_MISMATCH"),
    ("cost", "COST_WINDOW_SET_MISMATCH")])
def test_limiting_window_in_budget_cannot_be_silently_omitted(field, expected):
    d = data()
    if field == "commitments":
        d["commitments"][0]["amounts"]["5h"] = 100
    else:
        d["candidates"][0]["max_cost"]["5h"] = 5
    assert expected in reasons(d)


def test_proposal_is_pure_reproducible_and_never_dispatches(monkeypatch):
    d = data()
    before = copy.deepcopy(d)
    def forbidden(*args, **kwargs):
        raise AssertionError("network/process side effect")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = run(d)
    assert result == run(d)
    assert d == before
    assert result["dispatch_allowed"] is False
    assert result["incremental_spend_authorized_usd"] == 0
    assert result["decisions"][0]["status"] == "PROPOSED_ONLY"
    assert result["decisions"][0]["available_before"] == {"week": 66}
    d["candidates"][0]["revision"] = "2"
    assert run(d)["decision_id"] != result["decision_id"]


@pytest.mark.parametrize("cost,commitments,expected", [
    (None, True, "COST_NOT_BOUNDED"), ({"week": 10}, False, "COMMITMENTS_UNKNOWN_OR_STALE")])
def test_observed_91_percent_is_not_enough_without_bounded_commitments(cost, commitments, expected):
    d = data(); d["candidates"][0]["max_cost"] = cost
    if not commitments: d["commitments"] = []
    assert expected in reasons(d)


def test_ui_stale_even_with_future_expiry():
    d = data(); obs = d["observations"][0]
    obs.update(source="ui", observed_at=NOW - timedelta(minutes=16), remaining=72)
    assert "QUOTA_STALE_OR_RESET:week" in reasons(d)


def test_shared_pool_is_not_double_budgeted_across_two_routes():
    d = data()
    d["candidates"][0]["max_cost"] = {"week": 40}
    d["routes"].append(dict(d["routes"][0], route_id="codex-pcrick"))
    d["candidates"].append(dict(d["candidates"][0], task_id="t2", route_id="codex-pcrick"))
    result = run(d)
    assert result["decisions"][0]["status"] == "PROPOSED_ONLY"
    assert result["decisions"][1]["available_before"]["week"] == 26
    assert "RESERVE_PROTECTED:week" in result["decisions"][1]["reasons"]


def test_unknown_relationship_is_not_independent_capacity():
    d = data(); d["routes"][0]["pool_relationships_verified"] = False
    assert "POOL_RELATIONSHIP_UNKNOWN" in reasons(d)


def test_api_health_does_not_make_desktop_quota_available():
    d = data(); d["routes"][0].update(product="anthropic-api", included_usage_verified=False)
    assert "INCLUDED_USAGE_UNKNOWN" in reasons(d)
    assert "QUOTA_IDENTITY_MISMATCH:week" in reasons(d)


def test_reset_never_refills_without_a_new_observation():
    d = data(); d["observations"][0]["resets_at"] = NOW
    assert "QUOTA_STALE_OR_RESET:week" in reasons(d)


def test_gui_requires_own_evidence_even_with_shell_and_lease_pass():
    d = data(); d["candidates"][0]["needs_gui"] = True
    assert "READINESS_GUI" in reasons(d)
    d["routes"][0]["checks"]["gui"] = dict(**evidence(), value="pass")
    assert run(d)["decisions"][0]["status"] == "PROPOSED_ONLY"
    d["routes"][0]["checks"]["lease"]["value"] = "fail"
    assert "READINESS_LEASE" in reasons(d)


def test_fallback_cannot_inherit_primary_budget():
    d = data(); d["candidates"][0]["route_id"] = "fallback"
    d["routes"].append(dict(d["routes"][0], route_id="fallback", pool_id="other"))
    assert "QUOTA_UNKNOWN:week" in reasons(d)
    assert "COMMITMENTS_UNKNOWN_OR_STALE" in reasons(d)


@pytest.mark.parametrize("change,expected", [
    ({"useful": False}, "NO_USEFUL_OUTCOME"),
    ({"status": "done"}, "ALREADY_COMPLETED"),
    ({"status": "blocked"}, "TASK_NOT_READY"),
    ({"authorized": False}, "NOT_AUTHORIZED")])
def test_never_spends_to_empty_balance_or_repeat_closed_work(change, expected):
    d = data(); d["candidates"][0].update(change)
    assert expected in reasons(d)
    assert run(d)["status"] == "IDLE"


def test_global_stop_and_route_refusal_win():
    d = data(); d["stop"] = True
    assert "GLOBAL_STOP" in reasons(d)
    d["stop"] = False; d["routes"][0]["stop_reason"] = "429"
    assert "ROUTE_STOP" in reasons(d)


def test_secondary_limiting_window_cannot_be_omitted():
    d = data()
    d["observations"].append(dict(d["observations"][0], window_id="5h", remaining=21))
    assert "WINDOW_SET_MISMATCH" in reasons(d)
    d["routes"][0]["window_ids"].append("5h")
    d["commitments"][0]["amounts"]["5h"] = 0
    d["candidates"][0]["max_cost"]["5h"] = 1
    assert "RESERVE_PROTECTED:5h" in reasons(d)


def test_priority_max_three_and_no_allocation_for_held_candidate():
    d = data()
    d["candidates"] = [dict(d["candidates"][0], task_id=f"t{i}", kind="learning") for i in range(4)]
    d["candidates"].append(dict(d["candidates"][0], task_id="urgent", kind="incident"))
    result = run(d)
    assert result["decisions"][0]["task_id"] == "urgent"
    assert sum(x["status"] == "PROPOSED_ONLY" for x in result["decisions"]) == 3
    assert result["decisions"][-1]["reasons"] == ["CANDIDATE_LIMIT"]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "10"])
def test_invalid_telemetry_is_rejected(value):
    d = data(); d["observations"][0]["remaining"] = value
    with pytest.raises(ValidationError): Evaluation.model_validate(d)


def test_duplicate_observations_and_naive_dates_rejected():
    d = data(); d["observations"].append(copy.deepcopy(d["observations"][0]))
    with pytest.raises(ValidationError): Evaluation.model_validate(d)
    d = data(); d["now"] = NOW.replace(tzinfo=None)
    with pytest.raises(ValidationError): Evaluation.model_validate(d)


def test_future_or_expired_signals_cannot_authorize():
    d = data(); d["routes"][0]["checks"]["health"]["expires_at"] = NOW
    with pytest.raises(ValidationError): Evaluation.model_validate(d)
    d = data(); d["now"] = NOW + timedelta(minutes=5)
    assert "READINESS_HEALTH" in reasons(d)
    d = data(); d["now"] = NOW - timedelta(seconds=1)
    assert "READINESS_HEALTH" in reasons(d)


def test_fixture_cannot_be_presented_as_observed():
    d = data(); d["mode"] = "observed"
    assert "SIMULATED_QUOTA:week" in reasons(d)


@pytest.mark.parametrize("ordinary,spend,expected", [(True, False, "pass"), (False, False, "blocked"),
                                                     (True, True, "blocked"), (None, False, "unknown")])
def test_codex_reader_selects_account_bucket_only_and_preserves_denial(ordinary, spend, expected):
    payload = {"ordinaryUsageAllowed": ordinary, "rateLimitsByLimitId": {
        "codex": {"limitId": "codex", "spendControlReached": spend,
                  "primary": {"usedPercent": 9, "resetsAt": (NOW + timedelta(days=7)).timestamp()},
                  "secondary": None, "credits": {"balance": "0"}},
        "base_model_inference": {"primary": {"usedPercent": 0}}}}
    rows = codex_observations(payload, account_ref="local-account", observed_at=NOW,
                              received_at=NOW, evidence_ref="native:usage")
    assert len(rows) == 1
    assert rows[0].remaining == 91
    assert rows[0].availability == expected
    assert rows[0].window_id == "primary"
    assert rows[0].pool_id == "codex:local-account"


def test_cli_emits_only_receipt_and_hides_invalid_input(tmp_path):
    f = tmp_path / "snapshot.json"
    f.write_text(Evaluation.model_validate(data()).model_dump_json(), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.evaluate_capacity", str(f)], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["dispatch_allowed"] is False
    f.write_text('{"secret": "DO_NOT_ECHO_ME"}', encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.evaluate_capacity", str(f)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "DO_NOT_ECHO_ME" not in result.stdout + result.stderr
