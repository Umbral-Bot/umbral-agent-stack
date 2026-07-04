#!/usr/bin/env python3
"""PIT — construir el deck ejecutivo (.pptx) desde el outcome report.

Toma ``pit/<pit_id>/outcome/pit_outcome_report.yaml`` (+ opcional
``pit_spec.yaml`` y ``run-metrics.json``) y genera
``pit/<pit_id>/deliverables/<pit_id>-outcome-deck.pptx`` usando el handler
Worker ``document.create_presentation`` (import directo — mismo código).

Slides (mapeo desde la plantilla de outcome):
  1. Título · pit_id · fechas · gasto estimado vs techo budget · tokens
  2. Problem statement (del spec si está)
  3. Tabla de lanes (lane_id, fulfillment, status, hypothesis_validated)
  4. Winner + rationale + gate David
  5. KPI summary (expected vs achieved, synthetic_share)
  6. Learnings (validated / refuted / inconclusive)
  7. Próximo paso (fulfillment_decision + product_fulfillment + QA producto)
     + preview MC (hint, nunca URL pública)
  8. (solo si hay) Stuck log
  9+ (PIT-DEV con QA) capturas reales de deliverables/qa-screenshots/ — una
     slide por PNG (evidencia visual del gate pit_dev_human_qa_gate.py; el
     deck de un torneo con QA_PASS ya no puede salir sin imágenes)

Uso::

    python scripts/pit/pit_build_outcome_deck.py --outcome <pit_outcome_report.yaml> \
        [--spec <pit_spec.yaml>] [--run-metrics <run-metrics.json>] [--output <deck.pptx>]

Veredicto stdout: ``PIT_DECK_BUILD_OK | path=<pptx>`` (exit 0) o
``PIT_DECK_BUILD_FAIL | reason=<...>`` (exit 1). Sin secretos en la salida.

Nota: este builder NO exige winner cerrado (sirve para borradores); el gate de
winner/david_gate lo aplica ``pit_deliver_telegram_pack.py`` antes de subir a
Drive y avisar por Telegram.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # ejecución directa por path
    sys.path.insert(0, str(REPO_ROOT))

_PLACEHOLDER_PREFIX = "<"


def _clean(value: Any, fallback: str = "—") -> str:
    """Render seguro: placeholders de plantilla (`<...>`) y None → fallback."""
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.startswith(_PLACEHOLDER_PREFIX):
        return fallback
    return text


def _fmt_num(value: Any, fallback: str = "—") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_run_metrics(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_slides(
    outcome: dict[str, Any],
    spec: dict[str, Any] | None = None,
    run_metrics: dict[str, Any] | None = None,
    qa_screenshots: list[Path] | None = None,
) -> list[dict[str, str]]:
    """Mapear outcome (+spec/metrics/QA) → slides para document.create_presentation."""
    spec = spec or {}
    pit_id = _clean(outcome.get("pit_id"), "pit-?")
    title = _clean(outcome.get("title"), _clean(spec.get("title"), pit_id))

    dates = outcome.get("dates") or {}
    budget = outcome.get("budget") or {}
    budget_usd = _fmt_num(budget.get("budget_usd"))
    spent = _fmt_num(budget.get("usd_estimated_spent"), "no reportado")
    tokens_total = budget.get("tokens_total")
    if isinstance(tokens_total, (int, float)) and not isinstance(tokens_total, bool):
        tokens_line = f"Tokens: {_fmt_num(tokens_total)}"
        source = _clean(budget.get("pricing_source"), "")
        if source != "—":
            tokens_line += f" · pricing: {source}"
    else:
        tokens_line = "Tokens: not_reported"

    slides: list[dict[str, str]] = []

    # 1 — Título (billing truth: gasto estimado ≠ techo autorizado)
    verdict = ""
    if run_metrics:
        verdict = _clean(run_metrics.get("verdict"), "")
    title_lines = [
        f"{pit_id}",
        f"Periodo: {_clean(dates.get('started_at'))} → {_clean(dates.get('closed_at'))}",
        f"Gasto estimado: {spent} USD · techo budget: {budget_usd} USD",
        tokens_line,
    ]
    if verdict:
        title_lines.append(f"Runner: {verdict}")
    slides.append({"title": f"Torneo PIT — {title}", "content": "\n".join(title_lines)})

    # 2 — Problema
    problem = _clean(spec.get("problem_statement"), _clean(outcome.get("problem_statement")))
    slides.append({"title": "Problema / oportunidad", "content": problem})

    # 3 — Lanes
    lane_lines: list[str] = []
    for lane in outcome.get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        lane_lines.append(
            "- {lane}: fulfillment {score} · {status} · hipótesis validada: {hyp}".format(
                lane=_clean(lane.get("lane_id"), "lane-?"),
                score=_fmt_num(lane.get("fulfillment_score")),
                status=_clean(lane.get("status")),
                hyp=_clean(lane.get("hypothesis_validated"), "null"),
            )
        )
    slides.append({
        "title": "Lanes — resultado",
        "content": "\n".join(lane_lines) or "Sin lanes registradas.",
    })

    # 4 — Winner
    winner = outcome.get("winner") or {}
    winner_lines = [
        f"Winner: {_clean(winner.get('lane_id'), 'pending')}",
        "",
        _clean(winner.get("rationale"), "Rationale pendiente."),
        "",
        f"Gate David: {_clean(winner.get('david_gate'), 'pending')}",
    ]
    slides.append({"title": "Winner y rationale", "content": "\n".join(winner_lines)})

    # 5 — KPI summary
    kpi_lines: list[str] = []
    for kpi in outcome.get("kpi_summary") or []:
        if not isinstance(kpi, dict):
            continue
        kpi_lines.append(
            "- {kpi}: {achieved} vs {expected} {unit} · synthetic {synth}".format(
                kpi=_clean(kpi.get("kpi_id"), "kpi-?"),
                achieved=_fmt_num(kpi.get("kpi_achieved")),
                expected=_fmt_num(kpi.get("kpi_expected")),
                unit=_clean(kpi.get("unit"), ""),
                synth=_fmt_num(kpi.get("synthetic_share")),
            )
        )
    slides.append({
        "title": "KPIs — expected vs achieved",
        "content": "\n".join(kpi_lines) or "Sin KPI summary registrado.",
    })

    # 6 — Learnings
    learnings = outcome.get("learnings") or {}

    def _bullets(key: str) -> list[str]:
        items = learnings.get(key) or []
        return [f"- {_clean(item)}" for item in items if _clean(item, "") != ""]

    learn_lines: list[str] = []
    for label, key in (("Validado", "validated"), ("Refutado", "refuted"), ("Inconcluso", "inconclusive")):
        bullets = _bullets(key)
        if bullets:
            learn_lines.append(f"{label}:")
            learn_lines.extend(bullets)
    slides.append({
        "title": "Aprendizajes",
        "content": "\n".join(learn_lines) or "Sin learnings registrados.",
    })

    # 7 — Próximo paso + fulfillment producto + QA + preview
    decision = outcome.get("fulfillment_decision") or {}
    product_fulfillment = _clean(decision.get("product_fulfillment"), "no declarado")
    qa_block = outcome.get("human_qa") or {}
    qa_status = _clean(qa_block.get("status"), "sin QA registrado")
    next_lines = [
        f"Próximo paso: {_clean(decision.get('next_step'))}",
        f"Fulfillment producto: {product_fulfillment} (cierre procedural ≠ aceptación de producto)",
        f"QA producto: {qa_status}",
        _clean(decision.get("notes"), ""),
        "",
        "Preview prototipos (PC + túnel, nunca URL pública):",
        f"  scripts/ops/pit-judge-open.ps1 → /pit/judge/{pit_id}",
    ]
    slides.append({
        "title": "Decisión y preview",
        "content": "\n".join(line for line in next_lines if line is not None),
    })

    # 8 — Stuck log (solo si hay contenido real)
    stuck_lines: list[str] = []
    for entry in outcome.get("stuck_log") or []:
        if not isinstance(entry, dict):
            continue
        card = _clean(entry.get("card"), "")
        blocker = _clean(entry.get("blocker"), "")
        if not card and not blocker:
            continue
        stuck_lines.append(
            f"- {_clean(entry.get('lane_id'), 'lane-?')} · {card or 'tarjeta'} — "
            f"{blocker or 'blocker'} → {_clean(entry.get('resolution'))}"
        )
    if stuck_lines:
        slides.append({"title": "Stuck log", "content": "\n".join(stuck_lines)})

    # 9+ — Evidencia QA (PIT-DEV): una slide por captura real. Postmortem
    # pit-dev-ifc-viewer: el deck salió con 7 slides y 0 imágenes.
    for shot in qa_screenshots or []:
        slides.append({
            "title": f"QA producto — {shot.stem}",
            "content": f"Captura del gate de QA ({shot.name})",
            "image_path": str(shot),
        })

    return slides


def find_qa_screenshots(outcome_path: Path) -> list[Path]:
    """PNG reales del gate QA en pit/<pit_id>/deliverables/qa-screenshots/."""
    shots_dir = outcome_path.parent.parent / "deliverables" / "qa-screenshots"
    if not shots_dir.is_dir():
        return []
    return sorted(p for p in shots_dir.glob("*.png") if p.is_file())


def default_output_path(outcome_path: Path, pit_id: str) -> Path:
    """pit/<pit_id>/outcome/... → pit/<pit_id>/deliverables/<pit_id>-outcome-deck.pptx."""
    return outcome_path.parent.parent / "deliverables" / f"{pit_id}-outcome-deck.pptx"


def build_deck(
    outcome_path: Path,
    spec_path: Path | None = None,
    run_metrics_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Construir el deck; devuelve el resultado del handler + metadata."""
    outcome = load_yaml(outcome_path)
    pit_id = _clean(outcome.get("pit_id"), "pit-unknown")

    spec: dict[str, Any] | None = None
    if spec_path is None:
        candidate = outcome_path.parent.parent / "spec" / "pit_spec.yaml"
        spec_path = candidate if candidate.is_file() else None
    if spec_path is not None and spec_path.is_file():
        spec = load_yaml(spec_path)

    run_metrics = load_run_metrics(run_metrics_path)

    slides = build_slides(
        outcome,
        spec=spec,
        run_metrics=run_metrics,
        qa_screenshots=find_qa_screenshots(outcome_path),
    )

    if output_path is None:
        output_path = default_output_path(outcome_path, pit_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from worker.tasks.document_generator import handle_document_create_presentation

    result = handle_document_create_presentation(
        {"slides": slides, "output_path": str(output_path)}
    )
    result["pit_id"] = pit_id
    result["slides"] = len(slides)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outcome", type=Path, required=True,
                        help="Path a pit_outcome_report.yaml")
    parser.add_argument("--spec", type=Path, default=None,
                        help="pit_spec.yaml (default: ../spec/pit_spec.yaml junto al outcome)")
    parser.add_argument("--run-metrics", type=Path, default=None,
                        help="run-metrics.json del runner (opcional)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Destino .pptx (default: pit/<pit_id>/deliverables/<pit_id>-outcome-deck.pptx)")
    args = parser.parse_args(argv)

    if not args.outcome.is_file():
        print(f"PIT_DECK_BUILD_FAIL | reason=outcome_missing:{args.outcome}")
        return 1
    try:
        result = build_deck(
            args.outcome,
            spec_path=args.spec,
            run_metrics_path=args.run_metrics,
            output_path=args.output,
        )
    except Exception as exc:  # veredicto legible; el traceback no aporta a Rick
        print(f"PIT_DECK_BUILD_FAIL | reason={type(exc).__name__}:{exc}")
        return 1

    print(f"PIT_DECK_BUILD_OK | path={result.get('path')} | slides={result.get('slides')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
