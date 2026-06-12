"""Synthetic PIT vault builders shared by test_pit_vault_adapter / test_pit_routes.

Builds a deterministic vault under tmp_path — tests must NEVER read a real
vault (~/umbral-pit-vault) nor real evidence (~/.coord-ag-evidence).

Demo dataset:

- ``pit-judge-demo`` (active, under ``pit/``): spec en vault, 3 lanes —
  lane-alpha (2 iter, announce OK, prototype index.html) y lane-beta (1 iter,
  announce OK, prototype demo.html sin index) completas; lane-gamma sin
  announce. 2 announces → status ``judge_pending``.
- ``pit-old-closed`` (under ``archive/``): outcome con winner → archived.
- evidence: ``pit-run/pit-judge-demo/run-metrics.json`` verdict PIT_RUN_PASS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEMO_PIT_ID = "pit-judge-demo"
ARCHIVED_PIT_ID = "pit-old-closed"
TOKEN = "test-token-123"


def write_spec(tournament_dir: Path, pit_id: str, **overrides: Any) -> Path:
    spec_dir = tournament_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"pit_id: {pit_id}",
        f"title: {overrides.get('title', 'Demo tournament')}",
        f"mode: {overrides.get('mode', 'sintetico')}",
        f"lane_count: {overrides.get('lane_count', 3)}",
        f"iteration_count: {overrides.get('iteration_count', 5)}",
        f"budget_usd: {overrides.get('budget_usd', 25)}",
        "kpi_definitions:",
        "  - kpi_id: kpi-activation",
        "    name: Activación día 1",
        "    unit: percent",
        "    kpi_expected: 40",
        "    direction: up",
        "    weight: 0.6",
        "  - kpi_id: kpi-retention",
        "    name: Retención semana 1",
        "    unit: percent",
        "    kpi_expected: 25",
        "    direction: up",
        "    weight: 0.4",
    ]
    path = spec_dir / "pit_spec.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_kpi_pack(
    pit_id: str,
    lane_id: str,
    iteration: int,
    fulfillment_score: float,
    *,
    synthetic_flags: tuple[bool, ...] = (True, False),
    validated: bool = True,
) -> dict[str, Any]:
    return {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "iteration": iteration,
        "fulfillment_score": fulfillment_score,
        "hypothesis": {
            "variable": "onboarding copy",
            "kpi_id": "kpi-activation",
            "validated": validated,
        },
        "kpis": [
            {
                "kpi_id": f"kpi-{idx}",
                "value": 10 * (idx + 1),
                "synthetic": flag,
            }
            for idx, flag in enumerate(synthetic_flags)
        ],
    }


def write_iteration(
    lane_dir: Path,
    iteration: int,
    kpi_pack: dict[str, Any] | str | None,
    *,
    prototype_files: tuple[str, ...] = (),
) -> Path:
    iter_dir = lane_dir / "iterations" / str(iteration)
    iter_dir.mkdir(parents=True, exist_ok=True)
    if kpi_pack is not None:
        raw = (
            kpi_pack
            if isinstance(kpi_pack, str)
            else json.dumps(kpi_pack, ensure_ascii=False, indent=2)
        )
        (iter_dir / "kpi_pack.json").write_text(raw, encoding="utf-8")
    if prototype_files:
        proto_dir = iter_dir / "prototype"
        proto_dir.mkdir(parents=True, exist_ok=True)
        for name in prototype_files:
            (proto_dir / name).write_text("<html></html>", encoding="utf-8")
    return iter_dir


def write_announce(
    lane_dir: Path,
    *,
    prototype_url: str = "http://127.0.0.1:8090/demo/",
    kpi_pack: str = "kpi_pack.json",
    fulfillment: str = "0.82",
) -> Path:
    path = lane_dir / "announce.md"
    path.write_text(
        f"PROTOTYPE_URL={prototype_url}\nKPI_PACK={kpi_pack}\nFULFILLMENT={fulfillment}\n",
        encoding="utf-8",
    )
    return path


def write_outcome(
    tournament_dir: Path, winner_lane_id: str, david_gate: str = "GO"
) -> Path:
    outcome_dir = tournament_dir / "outcome"
    outcome_dir.mkdir(parents=True, exist_ok=True)
    path = outcome_dir / "pit_outcome_report.yaml"
    path.write_text(
        "winner:\n"
        f"  lane_id: {winner_lane_id}\n"
        f"  david_gate: {david_gate}\n",
        encoding="utf-8",
    )
    return path


def build_demo_vault(vault: Path) -> Path:
    """Vault sintético completo. Devuelve el path del vault."""
    demo = vault / "pit" / DEMO_PIT_ID
    write_spec(demo, DEMO_PIT_ID)

    alpha = demo / "lanes" / "lane-alpha"
    write_iteration(
        alpha, 1, make_kpi_pack(DEMO_PIT_ID, "lane-alpha", 1, 0.4)
    )
    write_iteration(
        alpha,
        2,
        make_kpi_pack(DEMO_PIT_ID, "lane-alpha", 2, 0.82),
        prototype_files=("index.html", "extra.html"),
    )
    write_announce(alpha, fulfillment="0.82")

    beta = demo / "lanes" / "lane-beta"
    write_iteration(
        beta,
        1,
        make_kpi_pack(
            DEMO_PIT_ID,
            "lane-beta",
            1,
            0.55,
            synthetic_flags=(True, True),
            validated=False,
        ),
        prototype_files=("demo.html",),
    )
    write_announce(beta, fulfillment="0.55")

    gamma = demo / "lanes" / "lane-gamma"
    write_iteration(gamma, 1, make_kpi_pack(DEMO_PIT_ID, "lane-gamma", 1, 0.3))
    # lane-gamma: sin announce.md → lane_complete False.

    archived = vault / "archive" / ARCHIVED_PIT_ID
    write_spec(archived, ARCHIVED_PIT_ID, title="Old closed", lane_count=1)
    winner = archived / "lanes" / "lane-winner"
    write_iteration(
        winner, 1, make_kpi_pack(ARCHIVED_PIT_ID, "lane-winner", 1, 0.9)
    )
    write_announce(winner, fulfillment="0.9")
    write_outcome(archived, "lane-winner", david_gate="GO")

    return vault


def build_evidence(evidence: Path, verdict: str = "PIT_RUN_PASS") -> Path:
    metrics_dir = evidence / "pit-run" / DEMO_PIT_ID
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (metrics_dir / "run-metrics.json").write_text(
        json.dumps({"verdict": verdict, "pit_id": DEMO_PIT_ID}), encoding="utf-8"
    )
    return evidence
