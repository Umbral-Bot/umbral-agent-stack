#!/usr/bin/env python3
"""PIT-DEV — verificación de trazabilidad post-torneo (rol traceability).

Script ejecutable (lo corre el agente de trazabilidad o el operador) que
verifica la cadena completa de un torneo PIT-DEV contra el pit-vault:

    spec → lanes.yaml → agents.yaml → workspace init → iterations
      (egress.jsonl + test_report.json) → announce.md → judge scorecards
      → outcome report → deck deliverables

Cada eslabón recibe un estado ``PRESENT | MISSING | UNVERIFIABLE``:

- ``PRESENT`` — el artefacto existe y es parseable/válido.
- ``MISSING`` — el artefacto no existe.
- ``UNVERIFIABLE`` — existe pero no se puede validar (JSON roto, schema
  inválido, egress con líneas malformadas).

Output: ``pit/<pit_id>/traceability/report.md`` + veredicto
``TRACE_COMPLETE`` | ``TRACE_GAPS(<lista>)``. Con gaps el agente NO arregla
nada: informa a Rick; Rick redacta la propuesta de automatización de
trazabilidad y la registra vía el handoff de mejora continua
(``docs/ops/pit-handoff-mejora-continua.md`` §5).

Exit codes: ``0`` TRACE_COMPLETE · ``1`` TRACE_GAPS · ``2`` error de entrada.

Rol/protocolo: ``docs/ops/pit-traceability-agent.md``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.pit import pit_dev_core as dev_core
    from scripts.pit.pit_runner_core import LANE_ID_RE, PIT_ID_RE
except ImportError:  # invocado como script directo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit import pit_dev_core as dev_core
    from scripts.pit.pit_runner_core import LANE_ID_RE, PIT_ID_RE

PRESENT = "PRESENT"
MISSING = "MISSING"
UNVERIFIABLE = "UNVERIFIABLE"

TRACE_COMPLETE = "TRACE_COMPLETE"
TRACE_GAPS = "TRACE_GAPS"

REPORT_REL = "traceability/report.md"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _link(name: str, status: str, detail: str = "") -> dict[str, str]:
    return {"link": name, "status": status, "detail": detail}


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _check_spec(pit_root: Path) -> tuple[dict[str, str], dict[str, Any] | None]:
    spec_path = pit_root / "spec" / "pit_spec.yaml"
    if not spec_path.is_file():
        spec_path = pit_root / "spec" / "pit_spec.yml"
    if not spec_path.is_file():
        return _link("spec", MISSING, "spec/pit_spec.yaml not found"), None
    try:
        raw = _load_yaml(spec_path)
    except yaml.YAMLError as exc:
        return _link("spec", UNVERIFIABLE, f"unparseable YAML: {exc}"), None
    if not isinstance(raw, dict):
        return _link("spec", UNVERIFIABLE, "spec root is not a mapping"), None
    return _link("spec", PRESENT, spec_path.name), raw


def _check_lanes_yaml(pit_root: Path) -> tuple[dict[str, str], list[str]]:
    lanes_path = pit_root / "spec" / "lanes.yaml"
    if not lanes_path.is_file():
        return _link("lanes.yaml", MISSING, "spec/lanes.yaml not found"), []
    try:
        raw = _load_yaml(lanes_path)
    except yaml.YAMLError as exc:
        return _link("lanes.yaml", UNVERIFIABLE, f"unparseable YAML: {exc}"), []
    lanes = raw.get("lanes") if isinstance(raw, dict) else None
    if not isinstance(lanes, list) or not lanes:
        return _link("lanes.yaml", UNVERIFIABLE, "no 'lanes:' list"), []
    lane_ids = [
        str(item.get("lane_id"))
        for item in lanes
        if isinstance(item, dict) and item.get("lane_id")
    ]
    bad = [lane_id for lane_id in lane_ids if not LANE_ID_RE.fullmatch(lane_id)]
    if bad or len(lane_ids) != len(lanes):
        return _link("lanes.yaml", UNVERIFIABLE, f"invalid lane ids: {bad}"), lane_ids
    return _link("lanes.yaml", PRESENT, f"{len(lane_ids)} lanes"), lane_ids


def _check_agents_yaml(pit_root: Path) -> dict[str, str]:
    agents_path = pit_root / "spec" / "agents.yaml"
    if not agents_path.is_file():
        return _link("agents.yaml", MISSING, "spec/agents.yaml not found")
    try:
        raw = _load_yaml(agents_path)
    except yaml.YAMLError as exc:
        return _link("agents.yaml", UNVERIFIABLE, f"unparseable YAML: {exc}")
    agents = raw.get("agents") if isinstance(raw, dict) else None
    if not isinstance(agents, list) or not agents:
        return _link("agents.yaml", UNVERIFIABLE, "no 'agents:' list")
    return _link("agents.yaml", PRESENT, f"{len(agents)} ephemeral agents recorded")


def _check_workspaces(pit_root: Path, lane_ids: list[str]) -> dict[str, str]:
    if not lane_ids:
        return _link("workspace_init", UNVERIFIABLE, "no lane ids to check")
    missing = []
    for lane_id in lane_ids:
        workspace = pit_root / "lanes" / lane_id / "workspace"
        if not (workspace / "CONTEXT_INDEX.md").is_file() or not (
            workspace / "snapshot"
        ).is_dir():
            missing.append(lane_id)
    if missing:
        return _link(
            "workspace_init",
            MISSING,
            f"lanes without snapshot+CONTEXT_INDEX: {missing}",
        )
    return _link("workspace_init", PRESENT, f"{len(lane_ids)} curated workspaces")


def _check_iterations(pit_root: Path, lane_ids: list[str]) -> dict[str, str]:
    """egress.jsonl parseable + test_report.json presente/válido por lane."""
    if not lane_ids:
        return _link("iterations", UNVERIFIABLE, "no lane ids to check")
    problems: list[str] = []
    vault = pit_root.parents[1]
    for lane_id in lane_ids:
        iterations_dir = pit_root / "lanes" / lane_id / "iterations"
        iter_dirs = (
            sorted(
                (p for p in iterations_dir.iterdir() if p.is_dir() and p.name.isdigit()),
                key=lambda p: int(p.name),
            )
            if iterations_dir.is_dir()
            else []
        )
        if not iter_dirs:
            problems.append(f"{lane_id}: no iterations")
            continue
        egress_seen = False
        report_valid = False
        for iter_dir in iter_dirs:
            egress_path = iter_dir / "egress.jsonl"
            if egress_path.is_file():
                egress_seen = True
                _events, errors = dev_core.parse_egress_file(egress_path)
                if errors:
                    problems.append(
                        f"{lane_id}/iterations/{iter_dir.name}/egress.jsonl unverifiable: "
                        f"{errors[:2]}"
                    )
            report_path = iter_dir / "test_report.json"
            if report_path.is_file():
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    dev_core.validate_test_report(report, vault)
                    report_valid = True
                except Exception as exc:
                    problems.append(
                        f"{lane_id}/iterations/{iter_dir.name}/test_report.json "
                        f"unverifiable: {exc}"
                    )
        if not egress_seen:
            problems.append(f"{lane_id}: no egress.jsonl declared in any iteration")
        if not report_valid:
            problems.append(f"{lane_id}: no valid test_report.json in any iteration")
    if problems:
        has_unverifiable = any("unverifiable" in p for p in problems)
        status = UNVERIFIABLE if has_unverifiable else MISSING
        return _link("iterations", status, "; ".join(problems[:6]))
    return _link("iterations", PRESENT, "egress + test_report per lane")


def _check_announces(pit_root: Path, lane_ids: list[str]) -> dict[str, str]:
    if not lane_ids:
        return _link("announce.md", UNVERIFIABLE, "no lane ids to check")
    missing: list[str] = []
    unverifiable: list[str] = []
    for lane_id in lane_ids:
        announce_path = pit_root / "lanes" / lane_id / "announce.md"
        if not announce_path.is_file():
            missing.append(lane_id)
            continue
        parsed = dev_core.parse_announce_dev(announce_path.read_text(encoding="utf-8"))
        if parsed["errors"]:
            unverifiable.append(f"{lane_id}: {parsed['errors'][0]}")
    if missing:
        return _link("announce.md", MISSING, f"lanes without announce: {missing}")
    if unverifiable:
        return _link("announce.md", UNVERIFIABLE, "; ".join(unverifiable[:4]))
    return _link("announce.md", PRESENT, f"{len(lane_ids)} lane result files")


def _check_scorecards(pit_root: Path) -> dict[str, str]:
    scorecards_dir = pit_root / "judge" / "scorecards"
    if not scorecards_dir.is_dir() or not any(scorecards_dir.glob("*.json")):
        return _link("judge_scorecards", MISSING, "judge/scorecards/*.json not found")
    vault = pit_root.parents[1]
    valid, errors = dev_core.collect_scorecards(vault, pit_root.name)
    if errors:
        first = next(iter(errors.items()))
        return _link(
            "judge_scorecards",
            UNVERIFIABLE,
            f"{len(errors)} invalid scorecard(s), e.g. {first[0]}: {first[1][0]}",
        )
    if not valid:
        return _link("judge_scorecards", UNVERIFIABLE, "no valid scorecards")
    return _link("judge_scorecards", PRESENT, f"{len(valid)} valid scorecards")


def _check_outcome(pit_root: Path) -> dict[str, str]:
    outcome_path = pit_root / "outcome" / "pit_outcome_report.yaml"
    if not outcome_path.is_file():
        return _link("outcome_report", MISSING, "outcome/pit_outcome_report.yaml not found")
    try:
        raw = _load_yaml(outcome_path)
    except yaml.YAMLError as exc:
        return _link("outcome_report", UNVERIFIABLE, f"unparseable YAML: {exc}")
    if not isinstance(raw, dict) or not raw.get("pit_id"):
        return _link("outcome_report", UNVERIFIABLE, "no pit_id in outcome report")
    return _link("outcome_report", PRESENT, "outcome report parseable")


def _check_deck(pit_root: Path) -> dict[str, str]:
    deliverables_dir = pit_root / "deliverables"
    deck = deliverables_dir / f"{pit_root.name}-outcome-deck.pptx"
    if deck.is_file():
        return _link("deck_deliverables", PRESENT, deck.name)
    pack = deliverables_dir / "telegram_pack.json"
    if pack.is_file():
        return _link("deck_deliverables", PRESENT, "telegram_pack.json (deck via pack)")
    return _link(
        "deck_deliverables",
        MISSING,
        "deliverables/ without outcome deck nor telegram_pack.json",
    )


def check_traceability(vault_path: Path, pit_id: str) -> dict[str, Any]:
    """Corre la cadena completa y devuelve links + veredicto."""
    if not PIT_ID_RE.fullmatch(pit_id or ""):
        raise ValueError(f"pit_id must match {PIT_ID_RE.pattern} (got {pit_id!r})")
    vault = Path(vault_path).expanduser().resolve()
    if not vault.is_dir():
        raise ValueError(f"vault_path is not a directory: {vault}")
    pit_root = vault / "pit" / pit_id
    if not pit_root.is_dir():
        raise ValueError(f"tournament not found in vault: pit/{pit_id}/")

    links: list[dict[str, str]] = []

    spec_link, _spec_raw = _check_spec(pit_root)
    links.append(spec_link)
    lanes_link, lane_ids = _check_lanes_yaml(pit_root)
    links.append(lanes_link)
    links.append(_check_agents_yaml(pit_root))
    links.append(_check_workspaces(pit_root, lane_ids))
    links.append(_check_iterations(pit_root, lane_ids))
    links.append(_check_announces(pit_root, lane_ids))
    links.append(_check_scorecards(pit_root))
    links.append(_check_outcome(pit_root))
    links.append(_check_deck(pit_root))

    gaps = [link for link in links if link["status"] != PRESENT]
    verdict = (
        TRACE_COMPLETE
        if not gaps
        else f"{TRACE_GAPS}({', '.join(link['link'] for link in gaps)})"
    )
    return {
        "pit_id": pit_id,
        "vault_path": str(vault),
        "checked_at": _utcnow_iso(),
        "links": links,
        "gaps": [link["link"] for link in gaps],
        "verdict": verdict,
        "complete": not gaps,
    }


def format_report_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Trazabilidad PIT-DEV — {result['pit_id']}",
        "",
        f"- Veredicto: **{result['verdict']}**",
        f"- Verificado: {result['checked_at']} por `scripts/pit/pit_traceability_check.py`",
        "",
        "| Eslabón | Estado | Detalle |",
        "|---|---|---|",
    ]
    for link in result["links"]:
        detail = link["detail"].replace("|", "\\|")
        lines.append(f"| {link['link']} | {link['status']} | {detail} |")
    lines.append("")
    if result["gaps"]:
        lines.extend(
            [
                "## Gaps",
                "",
                "El agente de trazabilidad NO arregla nada: este informe va a Rick;",
                "Rick redacta la propuesta de automatización de trazabilidad y la",
                "registra vía el handoff de mejora continua",
                "(`docs/ops/pit-handoff-mejora-continua.md` §5).",
                "",
            ]
        )
        lines.extend(f"- `{gap}`" for gap in result["gaps"])
        lines.append("")
    return "\n".join(lines)


def write_report(vault_path: Path, result: dict[str, Any]) -> Path:
    """Persiste el report en ``pit/<pit_id>/traceability/report.md``."""
    report_path = (
        Path(vault_path).expanduser().resolve()
        / "pit"
        / result["pit_id"]
        / REPORT_REL
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(format_report_markdown(result), encoding="utf-8")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PIT-DEV — verificación de trazabilidad de la cadena del torneo."
    )
    parser.add_argument("--pit-id", required=True)
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ["PIT_VAULT_PATH"]) if os.getenv("PIT_VAULT_PATH") else None,
        help="pit-vault (default: $PIT_VAULT_PATH).",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--no-write-report",
        action="store_true",
        help="Solo imprime; no persiste pit/<pit_id>/traceability/report.md.",
    )
    args = parser.parse_args(argv)

    if args.vault_path is None:
        print("ERROR: --vault-path or PIT_VAULT_PATH is required", file=sys.stderr)
        return 2
    try:
        result = check_traceability(args.vault_path, args.pit_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.no_write_report:
        report_path = write_report(args.vault_path, result)
        result["report_path"] = str(report_path)

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_report_markdown(result), end="")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
