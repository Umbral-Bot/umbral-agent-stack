"""Read-only adapter for the PIT vault (``umbral-pit-vault``) + runner evidence.

PIT-5 P5.1 (docs/ops/pit-5-mission-control-v2-implementation-plan.md §4):
exposes tournaments, lanes, iterations, kpi_packs, announce files, outcome
reports and runner ``run-metrics.json`` to the ``/pit/*`` JSON routes.

Hard rules (ADR-009 D1 + addendum 2026-06):

- **Never writes.** Every filesystem access is a read; there is a dedicated
  test asserting no file is ever opened in write mode.
- Best-effort: missing/corrupt sources degrade to ``None`` fields or
  ``available: false`` — never raise on bad vault content.
- Input ids are validated against the same regexes as
  ``openclaw/workspace-templates/pit-vault/templates/kpi-pack.schema.json``
  **before** touching the filesystem (``ValueError`` on mismatch).
- Defense in depth: tournament/lane dirs are resolved (symlink-aware) and must
  stay inside the vault, otherwise they are treated as not found.

Spec fallback (P5.0 finding): the pilot vault has no ``spec/pit_spec.yaml``;
when the vault spec is absent the adapter falls back to
``<spec_fallback_dir>/<pit_id>.yaml`` (repo ``examples/``) iff its ``pit_id``
matches. ``spec_source`` reports ``"vault"`` / ``"fallback"`` / ``None``.

Lane-closing rule (pit-kanban-kpi-protocol §3): ``fulfillment_score``,
``hypothesis_final`` and ``synthetic_share`` come from the kpi_pack of the
**last** iteration. ``lane_complete`` here is the read-only consistency proxy:
announce.md present with its 3 literal lines, a parseable last kpi_pack and
matching FULFILLMENT. The authoritative recompute (``compute_fulfillment``)
stays in the runner / ``pit.lane_announce``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Same patterns as kpi-pack.schema.json (frozen contract).
PIT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
LANE_ID_RE = re.compile(r"^lane-[a-z0-9][a-z0-9-]{1,63}$")
ITERATION_MIN = 1
ITERATION_MAX = 10

ANNOUNCE_KEYS = ("PROTOTYPE_URL", "KPI_PACK", "FULFILLMENT")

_SPEC_SUMMARY_KEYS = ("title", "mode", "lane_count", "iteration_count", "budget_usd")
_KPI_DEF_KEYS = ("kpi_id", "name", "unit", "kpi_expected", "direction", "weight")


# ---------------------------------------------------------------------------
# Input validation (raise BEFORE touching the filesystem)
# ---------------------------------------------------------------------------


def validate_pit_id(pit_id: str) -> str:
    """Return ``pit_id`` if it matches the frozen schema pattern, else raise."""
    if not isinstance(pit_id, str) or not PIT_ID_RE.fullmatch(pit_id):
        raise ValueError(f"invalid pit_id: {pit_id!r}")
    return pit_id


def validate_lane_id(lane_id: str) -> str:
    """Return ``lane_id`` if it matches the frozen schema pattern, else raise."""
    if not isinstance(lane_id, str) or not LANE_ID_RE.fullmatch(lane_id):
        raise ValueError(f"invalid lane_id: {lane_id!r}")
    return lane_id


def validate_iteration(iteration: int) -> int:
    """Return ``iteration`` if it is an int in [1, 10], else raise."""
    if isinstance(iteration, bool) or not isinstance(iteration, int):
        raise ValueError(f"invalid iteration: {iteration!r}")
    if not ITERATION_MIN <= iteration <= ITERATION_MAX:
        raise ValueError(f"iteration out of range [1, 10]: {iteration}")
    return iteration


# ---------------------------------------------------------------------------
# Status derivation (pure, frozen in P5.1 — plan §4 P5.1)
# ---------------------------------------------------------------------------


def derive_status(
    *,
    archived: bool,
    has_winner: bool,
    lanes_with_announce: int,
    lane_dir_count: int,
) -> str:
    """archived → closed → judge_pending → running → spec_only."""
    if archived:
        return "archived"
    if has_winner:
        return "closed"
    if lanes_with_announce >= 2:
        return "judge_pending"
    if lane_dir_count >= 1:
        return "running"
    return "spec_only"


# ---------------------------------------------------------------------------
# Internal helpers (all read-only)
# ---------------------------------------------------------------------------


def _safe_child(base: Path, name: str) -> Path | None:
    """``base / name`` iff the resolved result stays inside resolved ``base``."""
    candidate = base / name
    try:
        if not candidate.resolve().is_relative_to(base.resolve()):
            return None
    except OSError:
        return None
    return candidate


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, "file not found"
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _load_json(path: Path) -> tuple[Any, str | None]:
    text, error = _read_text(path)
    if text is None:
        return None, error
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: {exc}"


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    import yaml

    text, error = _read_text(path)
    if text is None:
        return None, error
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _iter_tournament_dirs(vault_path: Path) -> list[tuple[str, Path, bool]]:
    """``(pit_id, tournament_dir, archived)`` for pit/ first, then archive/."""
    found: list[tuple[str, Path, bool]] = []
    for subtree, archived in (("pit", False), ("archive", True)):
        root = vault_path / subtree
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir() or not PIT_ID_RE.fullmatch(entry.name):
                continue
            if _safe_child(root, entry.name) is None:
                continue
            found.append((entry.name, entry, archived))
    return found


def _find_tournament_dir(vault_path: Path, pit_id: str) -> tuple[Path | None, bool]:
    for subtree, archived in (("pit", False), ("archive", True)):
        root = vault_path / subtree
        candidate = _safe_child(root, pit_id)
        if candidate is not None and candidate.is_dir():
            return candidate, archived
    return None, False


def _read_spec(
    tournament_dir: Path, pit_id: str, spec_fallback_dir: Path | None
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Return ``(spec, source, error)`` — vault spec first, repo fallback after."""
    vault_spec = tournament_dir / "spec" / "pit_spec.yaml"
    if vault_spec.is_file():
        data, error = _load_yaml(vault_spec)
        if isinstance(data, dict):
            return data, "vault", None
        return None, "vault", error or "spec is not a YAML mapping"

    if spec_fallback_dir is not None:
        fallback = _safe_child(spec_fallback_dir, f"{pit_id}.yaml")
        if fallback is not None and fallback.is_file():
            data, error = _load_yaml(fallback)
            if isinstance(data, dict) and data.get("pit_id") == pit_id:
                return data, "fallback", None
            if error:
                return None, "fallback", error
            return None, None, "fallback spec pit_id mismatch"

    return None, None, "spec not found"


def _spec_summary(spec: dict[str, Any] | None) -> dict[str, Any]:
    summary: dict[str, Any] = {key: None for key in _SPEC_SUMMARY_KEYS}
    if isinstance(spec, dict):
        for key in _SPEC_SUMMARY_KEYS:
            summary[key] = spec.get(key)
    return summary


def _spec_detail(spec: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(spec, dict):
        return None
    detail = _spec_summary(spec)
    kpi_definitions: list[dict[str, Any]] = []
    raw_defs = spec.get("kpi_definitions")
    if isinstance(raw_defs, list):
        for raw in raw_defs:
            if isinstance(raw, dict):
                kpi_definitions.append({key: raw.get(key) for key in _KPI_DEF_KEYS})
    detail["kpi_definitions"] = kpi_definitions
    return detail


def _parse_announce(path: Path) -> dict[str, str | None] | None:
    """Parse the 3 literal lines of announce.md; ``None`` if file is absent."""
    text, _error = _read_text(path)
    if text is None:
        return None
    parsed: dict[str, str | None] = {key: None for key in ANNOUNCE_KEYS}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key in parsed and parsed[key] is None:
            parsed[key] = value.strip() or None
    return parsed


def _fulfillment_matches(announce_value: str | None, score: Any) -> bool:
    if announce_value is None or not isinstance(score, (int, float)):
        return False
    try:
        return abs(float(announce_value) - float(score)) < 1e-9
    except ValueError:
        return False


def _scan_lane(lane_dir: Path, pit_id: str, rel_root: str) -> dict[str, Any]:
    lane_id = lane_dir.name

    iterations_dir = lane_dir / "iterations"
    iter_dirs: list[Path] = []
    if iterations_dir.is_dir():
        iter_dirs = sorted(
            (d for d in iterations_dir.iterdir() if d.is_dir() and d.name.isdigit()),
            key=lambda d: int(d.name),
        )
    with_pack = [d for d in iter_dirs if (d / "kpi_pack.json").is_file()]
    iterations_run = len(with_pack)
    # Closing rule: judge fields come from the LAST iteration with a kpi_pack;
    # fall back to the last iteration dir so prototype info is still surfaced.
    last_dir = with_pack[-1] if with_pack else (iter_dirs[-1] if iter_dirs else None)
    last_iteration = int(last_dir.name) if last_dir is not None else None

    fulfillment_score: float | None = None
    hypothesis_final: dict[str, Any] | None = None
    synthetic_share: float | None = None
    kpi_pack_path: str | None = None
    pack_valid = False
    if last_dir is not None:
        pack_file = last_dir / "kpi_pack.json"
        if pack_file.is_file():
            kpi_pack_path = (
                f"{rel_root}/{pit_id}/lanes/{lane_id}/iterations/{last_dir.name}/kpi_pack.json"
            )
            pack, _error = _load_json(pack_file)
            if isinstance(pack, dict):
                score = pack.get("fulfillment_score")
                if isinstance(score, (int, float)) and not isinstance(score, bool):
                    fulfillment_score = float(score)
                    pack_valid = True
                hypothesis = pack.get("hypothesis")
                if isinstance(hypothesis, dict):
                    hypothesis_final = {
                        "variable": hypothesis.get("variable"),
                        "kpi_id": hypothesis.get("kpi_id"),
                        "validated": hypothesis.get("validated"),
                    }
                kpis = pack.get("kpis")
                if isinstance(kpis, list) and kpis:
                    flagged = sum(
                        1
                        for kpi in kpis
                        if isinstance(kpi, dict) and kpi.get("synthetic") is True
                    )
                    synthetic_share = round(flagged / len(kpis), 4)

    prototype_entry: str | None = None
    if last_dir is not None:
        proto_dir = last_dir / "prototype"
        if proto_dir.is_dir():
            html_files = sorted(
                p.name
                for p in proto_dir.iterdir()
                if p.is_file() and p.suffix.lower() in (".html", ".htm")
            )
            if "index.html" in html_files:
                prototype_entry = "index.html"
            elif html_files:
                prototype_entry = html_files[0]
    prototype = {
        "available": prototype_entry is not None,
        "entry": prototype_entry,
        # Emitted from P5.1 so the shape is stable; the route 404s until P5.3.
        "preview_path": (
            f"/pit/preview/{pit_id}/{lane_id}/{last_iteration}/"
            if last_iteration is not None
            else None
        ),
    }

    announce_file = lane_dir / "announce.md"
    announce_present = announce_file.is_file()
    announce = _parse_announce(announce_file) if announce_present else None

    lane_complete = bool(
        announce_present
        and announce is not None
        and all(announce.get(key) for key in ANNOUNCE_KEYS)
        and pack_valid
        and _fulfillment_matches(announce.get("FULFILLMENT"), fulfillment_score)
    )

    return {
        "lane_id": lane_id,
        "announce_present": announce_present,
        "lane_complete": lane_complete,
        "iterations_run": iterations_run,
        "last_iteration": last_iteration,
        "fulfillment_score": fulfillment_score,
        "hypothesis_final": hypothesis_final,
        "kpi_pack_path": kpi_pack_path,
        "synthetic_share": synthetic_share,
        "prototype": prototype,
        "announce": announce,
    }


def _scan_lanes(tournament_dir: Path, pit_id: str, rel_root: str) -> list[dict[str, Any]]:
    lanes_root = tournament_dir / "lanes"
    if not lanes_root.is_dir():
        return []
    lanes: list[dict[str, Any]] = []
    for entry in sorted(lanes_root.iterdir()):
        if not entry.is_dir() or not LANE_ID_RE.fullmatch(entry.name):
            continue
        if _safe_child(lanes_root, entry.name) is None:
            continue
        lanes.append(_scan_lane(entry, pit_id, rel_root))
    return lanes


def _read_outcome(tournament_dir: Path) -> dict[str, Any]:
    outcome_file = tournament_dir / "outcome" / "pit_outcome_report.yaml"
    if not outcome_file.is_file():
        return {"present": False, "winner_lane_id": None, "david_gate": None}
    data, _error = _load_yaml(outcome_file)
    winner_lane_id: str | None = None
    david_gate: str | None = None
    if isinstance(data, dict):
        winner = data.get("winner")
        if isinstance(winner, dict):
            raw_lane = winner.get("lane_id")
            if isinstance(raw_lane, str) and raw_lane.strip():
                winner_lane_id = raw_lane.strip()
            raw_gate = winner.get("david_gate")
            if isinstance(raw_gate, str) and raw_gate.strip():
                david_gate = raw_gate.strip()
    return {
        "present": True,
        "winner_lane_id": winner_lane_id,
        "david_gate": david_gate,
    }


def _read_run_evidence(evidence_dir: Path, pit_id: str) -> dict[str, Any]:
    metrics_file = evidence_dir / "pit-run" / pit_id / "run-metrics.json"
    if not metrics_file.is_file():
        return {"run_metrics_present": False, "verdict": None}
    data, _error = _load_json(metrics_file)
    verdict = data.get("verdict") if isinstance(data, dict) else None
    return {
        "run_metrics_present": True,
        "verdict": verdict if isinstance(verdict, str) else None,
    }


# ---------------------------------------------------------------------------
# Public API (consumed by mission_control/routes/pit.py)
# ---------------------------------------------------------------------------


def list_tournaments(
    vault_path: Path,
    evidence_dir: Path,
    spec_fallback_dir: Path | None = None,
) -> dict[str, Any]:
    """``GET /pit/tournaments`` payload — best-effort, never raises on content."""
    available = vault_path.is_dir()
    tournaments: list[dict[str, Any]] = []
    if available:
        for pit_id, tournament_dir, archived in _iter_tournament_dirs(vault_path):
            spec, source, _error = _read_spec(tournament_dir, pit_id, spec_fallback_dir)
            summary = _spec_summary(spec)
            rel_root = "archive" if archived else "pit"
            lanes = _scan_lanes(tournament_dir, pit_id, rel_root)
            outcome = _read_outcome(tournament_dir)
            evidence = _read_run_evidence(evidence_dir, pit_id)
            tournaments.append(
                {
                    "pit_id": pit_id,
                    "title": summary["title"],
                    "mode": summary["mode"],
                    "lane_count": summary["lane_count"],
                    "iteration_count": summary["iteration_count"],
                    "budget_usd": summary["budget_usd"],
                    "status": derive_status(
                        archived=archived,
                        has_winner=outcome["winner_lane_id"] is not None,
                        lanes_with_announce=sum(
                            1 for lane in lanes if lane["announce_present"]
                        ),
                        lane_dir_count=len(lanes),
                    ),
                    "lanes_complete": sum(1 for lane in lanes if lane["lane_complete"]),
                    "has_outcome": outcome["present"],
                    "archived": archived,
                    "run_verdict": evidence["verdict"],
                    "spec_source": source,
                }
            )
    return {
        "read_only": True,
        "vault": {"path": str(vault_path), "available": available},
        "tournaments": tournaments,
    }


def read_tournament(
    vault_path: Path,
    evidence_dir: Path,
    pit_id: str,
    spec_fallback_dir: Path | None = None,
) -> dict[str, Any] | None:
    """``GET /pit/tournaments/{pit_id}`` payload; ``None`` → 404."""
    validate_pit_id(pit_id)
    tournament_dir, archived = _find_tournament_dir(vault_path, pit_id)
    if tournament_dir is None:
        return None
    spec, source, _error = _read_spec(tournament_dir, pit_id, spec_fallback_dir)
    rel_root = "archive" if archived else "pit"
    lanes = _scan_lanes(tournament_dir, pit_id, rel_root)
    outcome = _read_outcome(tournament_dir)
    evidence = _read_run_evidence(evidence_dir, pit_id)
    return {
        "read_only": True,
        "pit_id": pit_id,
        "archived": archived,
        "status": derive_status(
            archived=archived,
            has_winner=outcome["winner_lane_id"] is not None,
            lanes_with_announce=sum(1 for lane in lanes if lane["announce_present"]),
            lane_dir_count=len(lanes),
        ),
        "spec_source": source,
        "spec": _spec_detail(spec),
        "lanes": lanes,
        "outcome": outcome,
        "evidence": evidence,
    }


def read_kpi_pack(
    vault_path: Path,
    pit_id: str,
    lane_id: str,
    iteration: int,
) -> dict[str, Any] | None:
    """``GET .../lanes/{lane_id}/kpi/{iteration}`` payload; ``None`` → 404."""
    validate_pit_id(pit_id)
    validate_lane_id(lane_id)
    validate_iteration(iteration)
    tournament_dir, archived = _find_tournament_dir(vault_path, pit_id)
    if tournament_dir is None:
        return None
    lane_dir = _safe_child(tournament_dir / "lanes", lane_id)
    if lane_dir is None or not lane_dir.is_dir():
        return None
    pack_file = lane_dir / "iterations" / str(iteration) / "kpi_pack.json"
    if not pack_file.is_file():
        return None
    pack, error = _load_json(pack_file)
    rel_root = "archive" if archived else "pit"
    return {
        "read_only": True,
        "pit_id": pit_id,
        "lane_id": lane_id,
        "iteration": iteration,
        "path": f"{rel_root}/{pit_id}/lanes/{lane_id}/iterations/{iteration}/kpi_pack.json",
        "kpi_pack": pack if isinstance(pack, dict) else None,
        "error": error,
    }
