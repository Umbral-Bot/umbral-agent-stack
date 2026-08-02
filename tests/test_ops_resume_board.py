"""
Tests for scripts/ops_resume_board.py

Todos los ledgers son fixtures escritas en tmp_path — sin red, sin tocar los
ledgers reales del repo. Run:
    python -m pytest tests/test_ops_resume_board.py -v
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts import ops_resume_board as board  # noqa: E402


def write_ledger(root: Path, repo_name: str, ledger_name: str, lines):
    ledger_dir = root / repo_name / "docs" / "operations"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / ledger_name
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for line in lines:
            if isinstance(line, str):
                fh.write(line + "\n")
            else:
                fh.write(json.dumps(line) + "\n")
    return path


def event(**overrides):
    base = {
        "ts": "2026-08-01T12:00:00Z",
        "pkg": "PKG-TEST",
        "frente": "test-front",
        "dest": "claude",
        "evento": "EMITIDO",
        "ev": "",
        "nota": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# parse_ts
# ---------------------------------------------------------------------------

def test_parse_ts_handles_z_suffix():
    dt = board.parse_ts("2026-08-01T04:55:00Z")
    assert dt == datetime(2026, 8, 1, 4, 55, 0)


def test_parse_ts_handles_naive_no_seconds():
    dt = board.parse_ts("2026-08-01T12:40")
    assert dt == datetime(2026, 8, 1, 12, 40)


def test_parse_ts_invalid_returns_none():
    assert board.parse_ts("not-a-timestamp") is None
    assert board.parse_ts(None) is None
    assert board.parse_ts("") is None


# ---------------------------------------------------------------------------
# discover_ledgers / load_events
# ---------------------------------------------------------------------------

def test_discover_ledgers_finds_nested_files(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event()])
    write_ledger(tmp_path, "repo-b", "ledger-beta.jsonl", [event(pkg="PKG-BETA")])
    found = board.discover_ledgers(tmp_path)
    assert len(found) == 2
    names = sorted(p.name for p in found)
    assert names == ["ledger-alpha.jsonl", "ledger-beta.jsonl"]


def test_discover_ledgers_missing_root_returns_empty(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert board.discover_ledgers(missing) == []


def test_load_events_skips_malformed_lines_without_crashing(tmp_path):
    ledger = write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [
            event(),
            '{"ts\\:\\broken\\,\\pkg\\:\\PKG-X\\}',  # línea rota real (visto en ledger-workshop-n8n-usm)
            "",
            json.dumps(["not", "a", "dict"]),
        ],
    )
    events, skipped = board.load_events(ledger, tmp_path)
    assert len(events) == 1
    assert skipped == 2


def test_load_events_handles_bom(tmp_path):
    ledger_dir = tmp_path / "repo-a" / "docs" / "operations"
    ledger_dir.mkdir(parents=True)
    path = ledger_dir / "ledger-alpha.jsonl"
    path.write_bytes(("﻿" + json.dumps(event()) + "\n").encode("utf-8"))
    events, skipped = board.load_events(path, tmp_path)
    assert skipped == 0
    assert len(events) == 1
    assert events[0].pkg == "PKG-TEST"


def test_load_events_records_repo_and_line_number(tmp_path):
    ledger = write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(), event(dest="codex")])
    events, _ = board.load_events(ledger, tmp_path)
    assert events[0].repo == "repo-a"
    assert events[0].line_no == 1
    assert events[1].line_no == 2


# ---------------------------------------------------------------------------
# latest_by_key
# ---------------------------------------------------------------------------

def test_latest_by_key_picks_newest_timestamp_per_dest():
    events, _ = _events_from(
        [
            event(dest="claude", evento="EMITIDO", ts="2026-08-01T10:00:00Z"),
            event(dest="claude", evento="REPORTADO", ts="2026-08-01T12:00:00Z"),
            event(dest="claude", evento="ACK", ts="2026-08-01T11:00:00Z"),
        ]
    )
    latest = board.latest_by_key(events)
    key = ("test-front", "PKG-TEST", "claude")
    assert latest[key].evento == "REPORTADO"


def test_latest_by_key_keeps_parallel_dest_separate():
    events, _ = _events_from(
        [
            event(dest="claude", evento="PASS"),
            event(dest="codex", evento="EMITIDO"),
        ]
    )
    latest = board.latest_by_key(events)
    assert len(latest) == 2
    assert latest[("test-front", "PKG-TEST", "claude")].evento == "PASS"
    assert latest[("test-front", "PKG-TEST", "codex")].evento == "EMITIDO"


def _events_from(dicts, tmp_path=None):
    """Helper: construye LedgerEvent directamente sin pasar por disco cuando
    el test no necesita ejercitar load_events."""
    events = []
    for i, d in enumerate(dicts, start=1):
        events.append(
            board.LedgerEvent(
                repo="repo-a",
                ledger_file="ledger-alpha.jsonl",
                line_no=i,
                ts_raw=str(d.get("ts") or ""),
                ts=board.parse_ts(d.get("ts")),
                pkg=d["pkg"],
                frente=d["frente"],
                dest=d["dest"],
                evento=d["evento"].upper(),
                ev=d.get("ev", ""),
                nota=d.get("nota", ""),
            )
        )
    return events, None


# ---------------------------------------------------------------------------
# build_board — terminal / drift / staleness
# ---------------------------------------------------------------------------

def test_build_board_marks_terminal_events(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="PASS")])
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 2, 12, 0, 0))
    assert len(balls) == 1
    assert balls[0].is_terminal is True
    assert balls[0].stale is False  # PASS no dispara staleness aunque sea viejo


def test_build_board_treats_blocked_as_open_not_terminal(tmp_path):
    # BLOCKED/NO_ACK son "estados marcados, no silencio" (reference-bitacora.md):
    # deben seguir contando como abiertos, no desaparecer bajo [CERRADO].
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="BLOCKED")])
    balls, _ = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    assert balls[0].is_terminal is False
    assert balls[0].is_known_event is True


def test_build_board_treats_no_ack_as_open_not_terminal(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="NO_ACK")])
    balls, _ = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    assert balls[0].is_terminal is False
    assert balls[0].is_known_event is True


def test_build_board_marks_unknown_event_as_drift(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="DEPLOY_STARTED")])
    balls, _ = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    assert balls[0].is_known_event is False
    assert balls[0].is_terminal is False  # abierto por defecto, no crashea


def test_build_board_flags_stale_emitido_past_threshold(tmp_path):
    write_ledger(
        tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="EMITIDO", ts="2026-08-01T00:00:00Z")]
    )
    now_fresh = datetime(2026, 8, 1, 10, 0, 0)  # 10h despues
    now_stale = datetime(2026, 8, 3, 10, 0, 0)  # >24h despues
    balls_fresh, _ = board.build_board(tmp_path, stale_hours=24, now=now_fresh)
    balls_stale, _ = board.build_board(tmp_path, stale_hours=24, now=now_stale)
    assert balls_fresh[0].stale is False
    assert balls_stale[0].stale is True


def test_build_board_does_not_flag_stale_for_reportado(tmp_path):
    write_ledger(
        tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="REPORTADO", ts="2026-08-01T00:00:00Z")]
    )
    now_far = datetime(2026, 9, 1, 0, 0, 0)
    balls, _ = board.build_board(tmp_path, stale_hours=24, now=now_far)
    assert balls[0].stale is False  # REPORTADO no es un evento-gatillo de staleness


def test_build_board_counts_skipped_malformed_in_meta(tmp_path):
    write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [event(), '{"ts\\:\\broken\\}'],
    )
    _, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    assert meta["events_skipped_malformed"] == 1
    assert meta["events_total"] == 1


def test_build_board_empty_root_returns_empty(tmp_path):
    balls, meta = board.build_board(tmp_path / "nope", stale_hours=24, now=datetime(2026, 8, 1, 0, 0, 0))
    assert balls == []
    assert meta["ledger_count"] == 0


def test_build_board_scans_multiple_repos(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(pkg="PKG-A", frente="front-a")])
    write_ledger(tmp_path, "repo-b", "ledger-beta.jsonl", [event(pkg="PKG-B", frente="front-b")])
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    assert meta["ledger_count"] == 2
    fronts = {b.frente for b in balls}
    assert fronts == {"front-a", "front-b"}


# ---------------------------------------------------------------------------
# infer_next
# ---------------------------------------------------------------------------

def test_infer_next_prefers_nota():
    assert board.infer_next("EMITIDO", "claude", "algo especifico") == "algo especifico"


def test_infer_next_falls_back_to_heuristic_when_no_nota():
    result = board.infer_next("ACK", "codex", "")
    assert "codex" in result
    assert "REPORTADO" in result


def test_infer_next_unknown_event_says_drift():
    result = board.infer_next("MERGED_DEPLOYED", "codex", "")
    assert "drift" in result.lower()


@pytest.mark.parametrize("evento", ["PASS", "FAIL", "BLOCKED", "NO_ACK", "CERRADO"])
def test_infer_next_terminal_and_open_marked_events_never_say_drift(evento):
    # Todo evento reconocido por el schema (terminal o abierto) debe tener su
    # propia heuristica; solo eventos fuera del enum caen en "posible drift".
    result = board.infer_next(evento, "codex", "")
    assert "drift" not in result.lower()


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def test_render_human_no_crash_on_empty(tmp_path):
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 0, 0, 0))
    output = board.render_human(balls, meta)
    assert "sin ledgers" in output or "nada que mostrar" in output


def test_render_json_is_valid_json(tmp_path):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="PASS")])
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 12, 0, 0))
    output = board.render_json(balls, meta)
    parsed = json.loads(output)
    assert parsed["meta"]["ledger_count"] == 1
    assert len(parsed["pelotas"]) == 1
    assert parsed["pelotas"][0]["pkg"] == "PKG-TEST"


def test_render_human_marks_stale_and_drift_flags(tmp_path):
    write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [
            event(evento="EMITIDO", ts="2026-01-01T00:00:00Z", dest="claude"),
            event(evento="DEPLOY_STARTED", dest="codex", pkg="PKG-DRIFT"),
        ],
    )
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=datetime(2026, 8, 1, 0, 0, 0))
    output = board.render_human(balls, meta)
    assert "STALE" in output
    assert "DRIFT" in output


# ---------------------------------------------------------------------------
# fetch_open_prs — nunca debe lanzar, aunque falle gh
# ---------------------------------------------------------------------------

def test_fetch_open_prs_handles_missing_gh_binary(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("gh not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = board.fetch_open_prs(tmp_path)
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_fetch_open_prs_handles_nonzero_exit(tmp_path, monkeypatch):
    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "not a git repository"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())
    result = board.fetch_open_prs(tmp_path)
    assert result["ok"] is False
    assert "not a git repository" in result["error"]


def test_fetch_open_prs_parses_success(tmp_path, monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = json.dumps([{"number": 1, "title": "x", "headRefName": "y", "updatedAt": "2026-08-01"}])
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())
    result = board.fetch_open_prs(tmp_path)
    assert result["ok"] is True
    assert result["prs"][0]["number"] == 1


# ---------------------------------------------------------------------------
# main() — CLI end-to-end sin red (sin --with-prs)
# ---------------------------------------------------------------------------

def test_main_json_end_to_end(tmp_path, capsys):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="PASS")])
    rc = board.main(["--root", str(tmp_path), "--json", "--now", "2026-08-01T12:00:00Z"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["meta"]["ledger_count"] == 1


def test_main_human_end_to_end(tmp_path, capsys):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event()])
    rc = board.main(["--root", str(tmp_path), "--now", "2026-08-01T12:00:00Z"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TABLERO DE REINGRESO" in out


def test_main_invalid_now_returns_error(tmp_path, capsys):
    rc = board.main(["--root", str(tmp_path), "--now", "not-a-date"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "invalido" in err


def test_main_does_not_call_gh_without_with_prs_flag(tmp_path, monkeypatch):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event()])

    def fail_if_called(*args, **kwargs):
        pytest.fail("subprocess.run no debe invocarse sin --with-prs")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    rc = board.main(["--root", str(tmp_path), "--json", "--now", "2026-08-01T12:00:00Z"])
    assert rc == 0
