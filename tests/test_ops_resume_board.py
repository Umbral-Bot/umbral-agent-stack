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
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [event(evento="PASS", gate_state="X_PASS")])
    rc = board.main(["--root", str(tmp_path), "--json", "--now", "2026-08-01T12:00:00Z"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["meta"]["ledger_count"] == 1
    # Los 6 opcionales 0.11.0 viajan hasta el --json del CLI (passthrough literal).
    ball = parsed["pelotas"][0]
    assert {k: ball[k] for k in board.OPTIONAL_FIELDS} == {
        "event_id": "",
        "thread": "",
        "tipo": "",
        "gate_state": "X_PASS",
        "next": "",
        "links": [],
    }


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


# ---------------------------------------------------------------------------
# Opcionales 0.11.0 (event_id, thread, tipo, gate_state, next, links) —
# passthrough literal, nunca inferidos. PKG-OPS-RESUME-GEN.
# ---------------------------------------------------------------------------

NOW = datetime(2026, 8, 21, 12, 0, 0)

EMPTY_OPTIONALS = {"event_id": "", "thread": "", "tipo": "", "gate_state": "", "next": "", "links": []}


def _single_ball_dict(tmp_path, line):
    write_ledger(tmp_path, "repo-a", "ledger-alpha.jsonl", [line])
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=NOW)
    assert len(balls) == 1
    parsed = json.loads(board.render_json(balls, meta))
    return balls[0], parsed["pelotas"][0], parsed["meta"]


def test_optional_fields_constant_is_the_contract_list():
    # La tupla del módulo DIRIGE load/copy/emit: si cambia, cambia el --json.
    assert board.OPTIONAL_FIELDS == ("event_id", "thread", "tipo", "gate_state", "next", "links")


def test_old_line_without_optionals_yields_all_six_keys_empty(tmp_path):
    # Línea vieja (schema 2026-07-28): las 6 claves están igual, vacías — el
    # consumidor (espejo Notion) nunca debe hacer .get() a ciegas.
    ball, d, meta = _single_ball_dict(tmp_path, event(evento="REPORTADO", nota="algo"))
    assert {k: d[k] for k in board.OPTIONAL_FIELDS} == EMPTY_OPTIONALS
    assert d["opcionales_descartados"] == []
    assert meta["optionals_type_mismatch"] == 0
    assert ball.links == []


def test_line_with_all_six_optionals_is_copied_literally(tmp_path):
    line = event(
        evento="RESUMED",
        nota="",
        event_id="e1a4f4",
        thread="claude/pkg-ops-resume-schema-20260820",
        tipo="implementación",
        gate_state="OPS_RESUME_SCHEMA_CODE_PASS",
        next="continuar implementación",
        links=["https://example.com/pr/123", "https://example.com/doc"],
    )
    _, d, _ = _single_ball_dict(tmp_path, line)
    assert {k: d[k] for k in board.OPTIONAL_FIELDS} == {
        "event_id": "e1a4f4",
        "thread": "claude/pkg-ops-resume-schema-20260820",
        "tipo": "implementación",
        "gate_state": "OPS_RESUME_SCHEMA_CODE_PASS",
        "next": "continuar implementación",
        "links": ["https://example.com/pr/123", "https://example.com/doc"],
    }
    assert d["opcionales_descartados"] == []


@pytest.mark.parametrize("evento", ["PAUSED", "RESUMED"])
def test_paused_and_resumed_are_open_known_events(tmp_path, evento):
    # Entraron al enum en cursor-orchestrator 0.11.0; siguen siendo abiertos.
    ball, d, _ = _single_ball_dict(tmp_path, event(evento=evento, next="retomar tras respuesta de David"))
    assert ball.is_terminal is False
    assert ball.is_known_event is True
    assert d["next"] == "retomar tras respuesta de David"


def test_next_from_source_is_separate_from_next_inferido(tmp_path):
    # `next` viene de la fuente; `next_inferido` es la heurística local (= nota
    # si hay nota). Son campos distintos y NO se copian entre sí.
    _, d, _ = _single_ball_dict(tmp_path, event(evento="ACK", nota="nota de la fuente", next="paso emitido por la fuente"))
    assert d["next"] == "paso emitido por la fuente"
    assert d["next_inferido"] == "nota de la fuente"


def test_empty_next_is_not_filled_from_heuristic(tmp_path):
    # Sin `next` en la fuente, la heurística sigue viviendo SOLO en next_inferido.
    ball, d, _ = _single_ball_dict(tmp_path, event(evento="ACK", nota=""))
    assert d["next"] == ""
    assert "REPORTADO" in d["next_inferido"]  # heurística de ACK presente, aparte
    assert ball.next == ""


def test_latest_line_wins_for_optionals_too(tmp_path):
    # Los opcionales se toman de la línea VIGENTE, no se acumulan de líneas previas.
    write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [
            event(evento="EMITIDO", ts="2026-08-20T09:10", event_id="e1", thread="t1", links=["https://old"]),
            event(evento="ACK", ts="2026-08-20T11:05", event_id="e2"),
        ],
    )
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=NOW)
    d = json.loads(board.render_json(balls, meta))["pelotas"][0]
    assert d["evento"] == "ACK"
    assert d["event_id"] == "e2"
    assert d["thread"] == ""  # la línea ACK no lo trae → vacío, no heredado
    assert d["links"] == []


def test_equal_ts_tie_goes_to_the_line_read_later(tmp_path):
    # Caso real: ACK y REPORTADO en el mismo minuto. Gana la línea de más abajo,
    # y sus opcionales viajan con ella (los de la anterior NO se mezclan).
    write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [
            event(evento="ACK", ts="2026-08-21T10:48", thread="t-ack", links=["https://ack"]),
            event(evento="REPORTADO", ts="2026-08-21T10:48", gate_state="X_CODE_PASS"),
        ],
    )
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=NOW)
    d = json.loads(board.render_json(balls, meta))["pelotas"][0]
    assert d["evento"] == "REPORTADO"
    assert d["gate_state"] == "X_CODE_PASS"
    assert d["thread"] == ""
    assert d["links"] == []


# --- helpers puros: optional_str / normalize_links / optional_type_mismatches


@pytest.mark.parametrize("value", [123, 1.5, True, ["x"], {"k": "v"}, None, "", "   "])
def test_optional_str_non_string_null_or_blank_becomes_empty(value):
    # Passthrough literal: no se coacciona ni se inventa; en blanco = ausente.
    assert board.optional_str({"next": value}, "next") == ""


def test_optional_str_keeps_string_verbatim_without_trimming():
    assert board.optional_str({"thread": " hilo con espacios "}, "thread") == " hilo con espacios "
    assert board.optional_str({}, "thread") == ""


@pytest.mark.parametrize("bad", [42, {"url": "x"}, True, None, "", "   ", [None, 7]])
def test_normalize_links_non_list_non_string_or_blank_becomes_empty(bad):
    assert board.normalize_links(bad) == []


def test_normalize_links_single_string_is_wrapped_and_trimmed():
    assert board.normalize_links("  https://example.com/pr/9 ") == ["https://example.com/pr/9"]


def test_normalize_links_list_with_only_strings_keeps_non_blank_trimmed():
    # Forma válida (todos string): filtra blancos, recorta URLs. No es mismatch.
    assert board.normalize_links(["https://a", "", "   ", " https://b "]) == ["https://a", "https://b"]


def test_normalize_links_list_with_any_non_string_item_becomes_empty():
    # Un solo ítem no-string invalida TODO el campo — nunca keep parcial.
    # Antes: normalize_links devolvía ["https://a"] mientras
    # optional_type_mismatches ya marcaba "links" como mismatch (flag y
    # payload contradictorios). PKG-OPS-RESUME-GEN2.
    assert board.normalize_links(["https://a", 7]) == []
    assert board.normalize_links([7, "https://a"]) == []
    assert board.normalize_links(["https://a", None]) == []


def test_optional_type_mismatches_names_wrong_typed_fields_only():
    data = {
        "event_id": "ok",  # string → bien
        "thread": None,  # null → ausente, no mismatch
        "tipo": 5,  # número → mismatch
        "next": ["paso 1", "paso 2"],  # lista donde va string → mismatch (caso real)
        "links": ["https://a", 7],  # ítem no-string → mismatch de TODO el campo
    }
    assert board.optional_type_mismatches(data) == ["tipo", "next", "links"]
    assert board.optional_type_mismatches({}) == []
    assert board.optional_type_mismatches({"links": "https://solo"}) == []  # string único es tolerado
    assert board.optional_type_mismatches({"links": ["https://a", "https://b"]}) == []  # todos string, no mismatch


def test_links_mismatch_flag_and_payload_never_disagree(tmp_path):
    # El bug que PKG-OPS-RESUME-GEN2 corrige: mismatch ⇒ vacío, siempre.
    _, d, meta = _single_ball_dict(tmp_path, event(evento="ACK", links=["https://a", 7]))
    assert d["links"] == []
    assert d["opcionales_descartados"] == ["links"]
    assert meta["optionals_type_mismatch"] == 1


def test_wrong_typed_optional_is_dropped_but_named_and_counted(tmp_path):
    # "No vino" y "vino mal" tienen que ser distinguibles en el --json.
    _, d, meta = _single_ball_dict(tmp_path, event(evento="ACK", next=["paso 1", "paso 2"], links=42))
    assert d["next"] == ""
    assert d["links"] == []
    assert d["opcionales_descartados"] == ["next", "links"]
    assert meta["optionals_type_mismatch"] == 2


def test_meta_optionals_type_mismatch_counts_only_vigente_mismatch(tmp_path):
    # Línea vieja Y vigente con `next` mal tipado, misma clave: el mismatch de
    # la vieja (ya superada) NO debe contarse; el de la vigente SI. Un solo
    # test que discrimina ambas direcciones: si contara todo daría 2, si no
    # contara nada daría 0 — solo "solo vigente" da 1.
    write_ledger(
        tmp_path,
        "repo-a",
        "ledger-alpha.jsonl",
        [
            event(evento="EMITIDO", ts="2026-08-20T09:10", next=["paso viejo mal tipado"]),
            event(evento="ACK", ts="2026-08-20T11:05", next=["paso nuevo mal tipado"]),
        ],
    )
    balls, meta = board.build_board(tmp_path, stale_hours=24, now=NOW)
    d = json.loads(board.render_json(balls, meta))["pelotas"][0]
    assert d["evento"] == "ACK"
    assert d["next"] == ""
    assert d["opcionales_descartados"] == ["next"]
    assert meta["optionals_type_mismatch"] == 1


def test_ledger_with_non_utf8_bytes_does_not_abort_the_board(tmp_path):
    # Un writer ANSI (PowerShell viejo) no puede tumbar el tablero entero: se
    # decodifica con reemplazo (U+FFFD, que ya aparece en ledgers reales).
    ledger_dir = tmp_path / "repo-a" / "docs" / "operations"
    ledger_dir.mkdir(parents=True)
    path = ledger_dir / "ledger-alpha.jsonl"
    raw = json.dumps(event(evento="ACK", tipo="implementación"), ensure_ascii=False) + "\n"
    path.write_bytes(raw.encode("cp1252"))
    events, skipped = board.load_events(path, tmp_path)
    assert skipped == 0
    assert len(events) == 1
    assert events[0].tipo.startswith("implementaci")
    assert "\ufffd" in events[0].tipo


def test_events_from_helper_defaults_keep_optionals_empty():
    # LedgerEvent construido sin opcionales (como hacen los tests viejos) sigue válido.
    events, _ = _events_from([event(evento="EMITIDO")])
    assert events[0].event_id == ""
    assert events[0].links == []
    assert events[0].opcionales_descartados == []
