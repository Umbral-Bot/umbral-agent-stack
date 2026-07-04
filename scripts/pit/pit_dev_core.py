#!/usr/bin/env python3
"""PIT-DEV runner core — primitivas ejecutables del modo dev sobre el pit-vault.

Capa repo-side del torneo PIT-DEV (``docs/ops/pit-dev-mode-vision-2026-07-03.md``):
preflight, verificación de cierre de lane dev, parseo/consolidación de egress,
validación de scorecards de jueces y ranking agregado. SIN spawn OpenClaw (eso
es ``pit_dev_run.py``). La consumen:

- ``scripts/pit/pit_dev_run.py`` — runner PIT-DEV (dispatch desde
  ``pit_tournament_run.py`` cuando el spec es ``mode: dev``);
- ``scripts/pit/pit_traceability_check.py`` — verificación de cadena.

Contratos sobre los que opera (no los redefine):

- entrada: pit_spec v3 (``scripts/pit/pit_spec_validate.py`` → ``PitSpecDev``);
- cierre de lane: ``DELIVERABLE_PATH=`` / ``TEST_REPORT=`` / ``SELF_ASSESSMENT=``
  en ``announce.md`` + ``test-report.schema.json`` (vault templates);
- jueces: ``judge-scorecard.schema.json`` (vault templates);
- egress: eventos JSONL declarados por lane/juez
  (``docs/ops/pit-security-egress-monitor.md``).

Los modos v1 producto (``pit_runner_core``) y v2 broker quedan intactos.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.pit.pit_runner_core import (
        LANE_ID_RE,
        _find_template,
        _resolve_vault,
        _validate_lane_id,
        _validate_pit_id,
    )
    from scripts.pit.pit_spec_validate import (
        DEV_RUBRIC_CRITERIA,
        validate_dev_file,
    )
    from scripts.pit.pit_vault_check import check_pit_vault
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit.pit_runner_core import (
        LANE_ID_RE,
        _find_template,
        _resolve_vault,
        _validate_lane_id,
        _validate_pit_id,
    )
    from scripts.pit.pit_spec_validate import (
        DEV_RUBRIC_CRITERIA,
        validate_dev_file,
    )
    from scripts.pit.pit_vault_check import check_pit_vault

TEST_REPORT_SCHEMA_NAME = "test-report.schema.json"
JUDGE_SCORECARD_SCHEMA_NAME = "judge-scorecard.schema.json"
ANNOUNCE_FILE_NAME = "announce.md"

JUDGE_ID_RE = re.compile(r"^judge-[a-z0-9][a-z0-9-]{0,63}$")

# Líneas literales del cierre de lane PIT-DEV (visión §3).
_ANNOUNCE_LINE_RES = {
    "deliverable_path": re.compile(r"^DELIVERABLE_PATH=(?P<value>\S+)\s*$", re.MULTILINE),
    "test_report": re.compile(r"^TEST_REPORT=(?P<value>\S+)\s*$", re.MULTILINE),
    "self_assessment": re.compile(r"^SELF_ASSESSMENT=(?P<value>\S+)\s*$", re.MULTILINE),
}

# Evento de egress declarado (security monitor §contrato): campos mínimos.
EGRESS_REQUIRED_FIELDS = ("url_or_query", "purpose", "timestamp")

PREFLIGHT_PASS = "PIT_DEV_PREFLIGHT_PASS"
PREFLIGHT_FAIL = "PIT_DEV_PREFLIGHT_FAIL"

SECURITY_CLEAN = "EGRESS_CLEAN"
SECURITY_FLAGGED = "EGRESS_FLAGGED"
SECURITY_MISSING = "EGRESS_VERDICT_MISSING"

_SECURITY_VERDICT_RE = re.compile(
    r"^(?P<lane>lane-[a-z0-9][a-z0-9-]{1,63})\s*:\s*"
    r"(?P<verdict>EGRESS_CLEAN|EGRESS_FLAGGED)(?:\((?P<reasons>[^)]*)\))?\s*$",
    re.MULTILINE,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lane_root(vault: Path, pit_id: str, lane_id: str) -> Path:
    return vault / "pit" / pit_id / "lanes" / lane_id


# ---------------------------------------------------------------------------
# Preflight dev (spec v3 + vault) — paralelo a pit_runner_core.preflight
# ---------------------------------------------------------------------------


def dev_preflight(
    spec_path: str | Path,
    vault_path: str | Path,
    *,
    require_write_scope: bool = False,
) -> dict[str, Any]:
    """Valida pit_spec v3 + vault antes de cualquier orquestación dev."""
    spec_result = validate_dev_file(Path(spec_path))
    spec_ok = spec_result["status"] == "pass"

    errors: list[str] = list(spec_result["errors"])
    vault_result: dict[str, Any]
    try:
        vault = _resolve_vault(str(vault_path))
    except ValueError as exc:
        vault_result = {"status": "fail", "errors": [str(exc)]}
        errors.append(str(exc))
    else:
        vault_result = check_pit_vault(vault, require_write_scope=require_write_scope)
        errors.extend(vault_result["errors"])
    vault_ok = vault_result["status"] == "pass"

    budget: dict[str, Any] | None = None
    if spec_ok:
        summary = spec_result["spec"]
        budget = {
            "budget_usd": summary["budget_usd"],
            "budget_per_lane_usd": summary["budget_per_lane_usd"],
            "max_cost_estimate_usd": summary["budget_usd"],
        }

    ok = spec_ok and vault_ok
    return {
        "ok": ok,
        "verdict": PREFLIGHT_PASS if ok else PREFLIGHT_FAIL,
        "spec_path": str(spec_path),
        "vault_path": str(vault_path),
        "spec": spec_result,
        "vault": vault_result,
        "budget": budget,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Announce dev — parse + verificación de cierre de lane (regla de verdad §3)
# ---------------------------------------------------------------------------


def parse_announce_dev(text: str) -> dict[str, Any]:
    """Extrae las 3 líneas literales del announce dev; errores por línea faltante."""
    parsed: dict[str, Any] = {}
    errors: list[str] = []
    for key, pattern in _ANNOUNCE_LINE_RES.items():
        match = pattern.search(text or "")
        if not match:
            errors.append(f"missing literal line {key.upper()}= in announce")
            parsed[key] = None
        else:
            parsed[key] = match.group("value")
    if parsed.get("self_assessment") is not None:
        try:
            score = float(parsed["self_assessment"])
        except ValueError:
            errors.append(
                f"SELF_ASSESSMENT must be a number 0-1 (got {parsed['self_assessment']!r})"
            )
        else:
            if not 0.0 <= score <= 1.0:
                errors.append(f"SELF_ASSESSMENT must be within [0, 1] (got {score})")
            else:
                parsed["self_assessment"] = score
    parsed["errors"] = errors
    return parsed


def validate_test_report(report: dict[str, Any], vault: Path) -> str:
    """Valida el test_report: jsonschema si está disponible + checks duros siempre.

    Espejo del patrón ``_validate_kpi_pack`` de v1 (checks duros + schema).
    """
    if not isinstance(report, dict):
        raise ValueError("test_report must be a JSON object")
    command = report.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) and part for part in command
    ):
        raise ValueError("test_report.command must be a non-empty argv list of strings")
    if not isinstance(report.get("exit_code"), int) or isinstance(report.get("exit_code"), bool):
        raise ValueError("test_report.exit_code must be an integer")
    for field in ("total", "passed", "failed"):
        value = report.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"test_report.{field} must be an integer >= 0")

    schema_path = _find_template(vault, TEST_REPORT_SCHEMA_NAME)
    try:
        import jsonschema
    except ImportError:
        return "builtin-only"
    if schema_path is None:
        return "builtin-only"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)
    return "jsonschema"


def _re_run_tests(
    report: dict[str, Any],
    lane_root: Path,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Re-ejecuta el comando declarado del test_report (collect --re-run-tests)."""
    workdir_rel = report.get("workdir") or "deliverable"
    workdir = (lane_root / workdir_rel).resolve()
    if not str(workdir).startswith(str(lane_root.resolve())):
        return {"ran": False, "ok": False, "error": "workdir escapes lane root"}
    if not workdir.is_dir():
        return {"ran": False, "ok": False, "error": f"workdir not found: {workdir_rel}"}
    try:
        proc = subprocess.run(
            list(report["command"]),
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ran": False, "ok": False, "error": str(exc)}
    return {
        "ran": True,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "error": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-500:],
    }


def verify_dev_lane(
    vault_path: str | Path,
    pit_id: str,
    lane_id: str,
    *,
    re_run_tests: bool = False,
    test_timeout_seconds: float = 600.0,
) -> dict[str, Any]:
    """Verifica el cierre de una lane PIT-DEV contra el vault (regla de verdad §3).

    lane_complete = announce con 3 líneas literales + deliverable presente y no
    vacío + test_report válido contra schema con exit_code 0 (+ re-ejecución
    verde cuando ``re_run_tests``).
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    lane_id = _validate_lane_id(lane_id)
    lane_root = _lane_root(vault, pit_id, lane_id)

    incomplete: list[str] = []
    state: dict[str, Any] = {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "announce_file_present": False,
        "lane_complete": False,
    }

    announce_path = lane_root / ANNOUNCE_FILE_NAME
    parsed: dict[str, Any] = {}
    if announce_path.is_file():
        state["announce_file_present"] = True
        parsed = parse_announce_dev(announce_path.read_text(encoding="utf-8"))
        incomplete.extend(parsed["errors"])
    else:
        incomplete.append(
            f"missing lane result file {ANNOUNCE_FILE_NAME} (lane did not declare close)"
        )

    state["deliverable_path"] = parsed.get("deliverable_path")
    state["test_report"] = parsed.get("test_report")
    state["self_assessment"] = parsed.get("self_assessment")

    # Deliverable presente y no vacío (dentro de la lane, path del announce).
    deliverable_rel = parsed.get("deliverable_path") or f"pit/{pit_id}/lanes/{lane_id}/deliverable/"
    expected_prefix = f"pit/{pit_id}/lanes/{lane_id}/"
    if not str(deliverable_rel).startswith(expected_prefix):
        incomplete.append(
            f"DELIVERABLE_PATH must live under {expected_prefix} (got {deliverable_rel!r})"
        )
    deliverable_dir = vault / str(deliverable_rel).rstrip("/")
    if not deliverable_dir.is_dir() or not any(deliverable_dir.iterdir()):
        incomplete.append(f"deliverable missing or empty: {deliverable_rel}")

    # test_report válido contra schema + exit_code 0.
    report: dict[str, Any] | None = None
    report_rel = parsed.get("test_report")
    if report_rel:
        if not str(report_rel).startswith(expected_prefix):
            incomplete.append(
                f"TEST_REPORT must live under {expected_prefix} (got {report_rel!r})"
            )
        report_path = vault / str(report_rel)
        if not report_path.is_file():
            incomplete.append(f"test_report not found: {report_rel}")
        else:
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                state["test_report_schema_validation"] = validate_test_report(report, vault)
            except (json.JSONDecodeError, ValueError) as exc:
                report = None
                incomplete.append(f"test_report invalid: {exc}")
            except Exception as exc:  # jsonschema.ValidationError sin importar el tipo
                report = None
                incomplete.append(f"test_report schema validation failed: {exc}")
        if report is not None:
            if report.get("pit_id") != pit_id or report.get("lane_id") != lane_id:
                incomplete.append("test_report pit_id/lane_id do not match the lane")
            if report.get("exit_code") != 0:
                incomplete.append(
                    f"test_report.exit_code must be 0 (got {report.get('exit_code')})"
                )

    # Re-ejecución opcional (tests re-ejecutables por el collect).
    if re_run_tests:
        if report is not None and report.get("exit_code") == 0:
            rerun = _re_run_tests(report, lane_root, timeout_seconds=test_timeout_seconds)
            state["re_run"] = rerun
            if not rerun["ok"]:
                incomplete.append(f"test re-run failed: {rerun.get('error')}")
        else:
            # Sin report válido no hay nada que re-ejecutar; ya quedó reportado.
            state["re_run"] = {"ran": False, "ok": False, "error": "no valid test_report"}

    state["incomplete_reasons"] = incomplete
    state["lane_complete"] = not incomplete
    return state


# ---------------------------------------------------------------------------
# Egress — parse por archivo + consolidación (security monitor)
# ---------------------------------------------------------------------------


def parse_egress_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Parsea un egress.jsonl declarado; devuelve ``(events, errors)`` por línea.

    Evento mínimo: ``{url_or_query, purpose, timestamp}`` + identidad del actor
    (``lane_id`` para lanes — con ``iteration`` — o ``judge_id`` para jueces).
    """
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return events, [f"egress file not found: {path}"]
    for lineno, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: invalid JSON ({exc})")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {lineno}: event must be an object")
            continue
        missing = [
            field
            for field in EGRESS_REQUIRED_FIELDS
            if not isinstance(event.get(field), str) or not event.get(field)
        ]
        if missing:
            errors.append(f"line {lineno}: missing/empty fields {missing}")
            continue
        lane_id = event.get("lane_id")
        judge_id = event.get("judge_id")
        if lane_id is not None and not LANE_ID_RE.fullmatch(str(lane_id)):
            errors.append(f"line {lineno}: invalid lane_id {lane_id!r}")
            continue
        if judge_id is not None and not JUDGE_ID_RE.fullmatch(str(judge_id)):
            errors.append(f"line {lineno}: invalid judge_id {judge_id!r}")
            continue
        if lane_id is None and judge_id is None:
            errors.append(f"line {lineno}: event needs lane_id or judge_id")
            continue
        if lane_id is not None:
            iteration = event.get("iteration")
            if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
                errors.append(f"line {lineno}: lane event needs integer iteration >= 1")
                continue
        events.append(event)
    return events, errors


def consolidate_egress(
    vault_path: str | Path,
    pit_id: str,
    lane_ids: list[str],
    *,
    judge_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Consolida los egress declarados en ``pit/<pit_id>/security/egress_ledger.jsonl``.

    Consolidación MECÁNICA (v1 pragmática): merge de los ``egress.jsonl`` que
    lanes (por iteración) y jueces declararon. El VEREDICTO (CLEAN/FLAGGED) es
    del security agent (o Rick), que además contrasta contra los logs reales
    disponibles (audit JSONL del broker, logs del gateway exportados por el
    operador) — este helper no juzga.
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    security_dir = vault / "pit" / pit_id / "security"
    security_dir.mkdir(parents=True, exist_ok=True)

    all_events: list[dict[str, Any]] = []
    parse_errors: dict[str, list[str]] = {}
    declared_files = 0

    for lane_id in lane_ids:
        lane_id = _validate_lane_id(lane_id)
        iterations_dir = _lane_root(vault, pit_id, lane_id) / "iterations"
        if not iterations_dir.is_dir():
            continue
        for iter_dir in sorted(
            (p for p in iterations_dir.iterdir() if p.is_dir() and p.name.isdigit()),
            key=lambda p: int(p.name),
        ):
            egress_path = iter_dir / "egress.jsonl"
            if not egress_path.is_file():
                continue
            declared_files += 1
            events, errors = parse_egress_file(egress_path)
            rel = str(egress_path.relative_to(vault))
            if errors:
                parse_errors[rel] = errors
            for event in events:
                event.setdefault("lane_id", lane_id)
                event.setdefault("iteration", int(iter_dir.name))
                event["source_file"] = rel
                all_events.append(event)

    for judge_id in judge_ids or []:
        if not JUDGE_ID_RE.fullmatch(judge_id):
            raise ValueError(f"judge_id must match {JUDGE_ID_RE.pattern} (got {judge_id!r})")
        egress_path = vault / "pit" / pit_id / "judge" / judge_id / "egress.jsonl"
        if not egress_path.is_file():
            continue
        declared_files += 1
        events, errors = parse_egress_file(egress_path)
        rel = str(egress_path.relative_to(vault))
        if errors:
            parse_errors[rel] = errors
        for event in events:
            event.setdefault("judge_id", judge_id)
            event["source_file"] = rel
            all_events.append(event)

    ledger_path = security_dir / "egress_ledger.jsonl"
    with ledger_path.open("w", encoding="utf-8") as handle:
        for event in all_events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    return {
        "pit_id": pit_id,
        "ledger_path": str(ledger_path),
        "events": len(all_events),
        "declared_files": declared_files,
        "parse_errors": parse_errors,
        "consolidated_at": _utcnow_iso(),
    }


def security_verdict_state(vault_path: str | Path, pit_id: str) -> dict[str, Any]:
    """Lee ``pit/<pit_id>/security/verdict.md`` → estado por lane.

    Formato por lane (una línea): ``lane-<slug>: EGRESS_CLEAN`` o
    ``lane-<slug>: EGRESS_FLAGGED(<motivos>)``. Sin archivo o sin línea para
    una lane ⇒ ``EGRESS_VERDICT_MISSING`` (fail-closed: judge no corre).
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    verdict_path = vault / "pit" / pit_id / "security" / "verdict.md"
    lanes: dict[str, dict[str, Any]] = {}
    if not verdict_path.is_file():
        return {"verdict_file_present": False, "lanes": lanes, "path": str(verdict_path)}
    text = verdict_path.read_text(encoding="utf-8")
    for match in _SECURITY_VERDICT_RE.finditer(text):
        reasons = (match.group("reasons") or "").strip()
        lanes[match.group("lane")] = {
            "verdict": match.group("verdict"),
            "reasons": [r.strip() for r in reasons.split(";") if r.strip()] if reasons else [],
        }
    return {"verdict_file_present": True, "lanes": lanes, "path": str(verdict_path)}


# ---------------------------------------------------------------------------
# Judges — validación de scorecards + ranking agregado
# ---------------------------------------------------------------------------


def validate_scorecard(scorecard: dict[str, Any], vault: Path) -> str:
    """Valida un judge scorecard: jsonschema si está + checks duros siempre.

    Hardening post ``pit-dev-ifc-viewer`` (jueces laxos): un
    ``meets_functional_spec: true`` exige ``functional_evidence`` con
    ``real_input_used: true`` y descripción del input real probado. Fixture
    de test + HTTP 200 + tests offline NO son evidencia funcional.
    """
    if not isinstance(scorecard, dict):
        raise ValueError("scorecard must be a JSON object")
    criteria = scorecard.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError("scorecard.criteria must be an object")
    for criterion in DEV_RUBRIC_CRITERIA:
        value = criteria.get(criterion)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"criteria.{criterion} must be a number 0-1")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"criteria.{criterion} must be within [0, 1]")
    judge_id = scorecard.get("judge_id") or ""
    if not JUDGE_ID_RE.fullmatch(str(judge_id)):
        raise ValueError(f"judge_id must match {JUDGE_ID_RE.pattern} (got {judge_id!r})")
    for flag in ("installed_clean", "ran", "own_tests_passed", "meets_functional_spec"):
        if not isinstance(scorecard.get(flag), bool):
            raise ValueError(f"scorecard.{flag} must be a boolean")

    if scorecard.get("meets_functional_spec") is True:
        evidence = scorecard.get("functional_evidence")
        if not isinstance(evidence, dict):
            raise ValueError(
                "functional_evidence required when meets_functional_spec is true "
                "(hardening post pit-dev-ifc-viewer)"
            )
        if evidence.get("real_input_used") is not True:
            raise ValueError(
                "functional_evidence.real_input_used must be true when "
                "meets_functional_spec is true (fixture/synthetic input does not count)"
            )
        description = str(evidence.get("input_description") or "").strip()
        if not description:
            raise ValueError(
                "functional_evidence.input_description required when "
                "meets_functional_spec is true"
            )

    schema_path = _find_template(vault, JUDGE_SCORECARD_SCHEMA_NAME)
    try:
        import jsonschema
    except ImportError:
        return "builtin-only"
    if schema_path is None:
        return "builtin-only"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=scorecard, schema=schema)
    return "jsonschema"


def weighted_score(criteria: dict[str, Any], weights: dict[str, float]) -> float:
    """Score 0-1 de un scorecard con los pesos de la rúbrica del spec."""
    total_weight = 0.0
    weighted = 0.0
    for criterion in DEV_RUBRIC_CRITERIA:
        weight = float(weights.get(criterion, 1.0))
        if weight <= 0:
            raise ValueError(f"rubric weight for {criterion} must be > 0")
        total_weight += weight
        weighted += weight * float(criteria[criterion])
    return round(weighted / total_weight, 4)


def collect_scorecards(
    vault_path: str | Path, pit_id: str
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Lee y valida ``pit/<pit_id>/judge/scorecards/*.json`` → (válidos, errores)."""
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    scorecards_dir = vault / "pit" / pit_id / "judge" / "scorecards"
    valid: list[dict[str, Any]] = []
    errors: dict[str, list[str]] = {}
    if not scorecards_dir.is_dir():
        return valid, errors
    for path in sorted(scorecards_dir.glob("*.json")):
        rel = str(path.relative_to(vault))
        try:
            scorecard = json.loads(path.read_text(encoding="utf-8"))
            validate_scorecard(scorecard, vault)
        except (json.JSONDecodeError, ValueError) as exc:
            errors[rel] = [str(exc)]
            continue
        except Exception as exc:  # jsonschema.ValidationError
            errors[rel] = [str(exc)]
            continue
        scorecard["_source_file"] = rel
        valid.append(scorecard)
    return valid, errors


def aggregate_ranking(
    scorecards: list[dict[str, Any]],
    rubric_weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Ranking agregado por lane (media de scores ponderados entre jueces).

    El ranking NO decide: Rick consolida y David da el gate de winner (regla
    existente de PIT). Esto solo ordena la información.
    """
    per_lane: dict[str, list[float]] = {}
    judges_per_lane: dict[str, set[str]] = {}
    for scorecard in scorecards:
        lane_id = scorecard["lane_id"]
        score = weighted_score(scorecard["criteria"], rubric_weights)
        per_lane.setdefault(lane_id, []).append(score)
        judges_per_lane.setdefault(lane_id, set()).add(scorecard["judge_id"])
    ranking = [
        {
            "lane_id": lane_id,
            "mean_weighted_score": round(sum(scores) / len(scores), 4),
            "scores": scores,
            "judges": sorted(judges_per_lane[lane_id]),
        }
        for lane_id, scores in per_lane.items()
    ]
    ranking.sort(key=lambda item: (-item["mean_weighted_score"], item["lane_id"]))
    for position, item in enumerate(ranking, start=1):
        item["rank"] = position
    return ranking
