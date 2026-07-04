#!/usr/bin/env python3
"""PIT-DEV — gate de QA de producto (humano/automático) pre-entrega.

Quality gate nacido del postmortem ``pit-dev-ifc-viewer`` (2026-07-04): el
torneo cerró "verde" procedural (TRACE_COMPLETE, Drive, gate David) con un
visor inusable — parser casero que degrada IFC reales a cajas fallback, KPIs
100 % sintéticos y deck sin una sola captura. Este gate exige evidencia visual
REAL antes de que ``pit_deliver_telegram_pack.py`` entregue nada:

* ``human_qa.real_ifc_upload`` — el deliverable winner procesó un archivo IFC
  **real** (>100 KB; los fixtures de test tipo ``mini-site.ifc`` están
  denylisteados) con ≥1 elemento parseado y sin error fatal.
* ``human_qa.screenshots`` — ≥3 PNG reales en
  ``pit/<pit_id>/deliverables/qa-screenshots/`` (vista 3D cargada, panel de
  propiedades con elemento seleccionado, observación creada / export JSON).
* El resultado queda en el outcome report (bloque ``human_qa``) — es lo que
  ``pit_deliver_telegram_pack.py`` verifica fail-closed.

Modos::

    # Automático (requiere playwright instalado y el winner sirviendo):
    python scripts/pit/pit_dev_human_qa_gate.py --pit-id <pit_id> --auto \
        --app-url http://127.0.0.1:8123 --ifc-file ~/fixtures/real-building.ifc \
        --elements-js "window.__viewer ? window.__viewer.elementCount : 0"

    # Validar evidencia ya capturada (humano u otro runner dejó screenshots
    # + qa_results.json en deliverables/qa-screenshots/):
    python scripts/pit/pit_dev_human_qa_gate.py --pit-id <pit_id> --from-evidence \
        [--ifc-file <path>]

    # Skip explícito y auditable (ej.: deliverable sin UI):
    python scripts/pit/pit_dev_human_qa_gate.py --pit-id <pit_id> --skip \
        --reason "deliverable es una CLI sin superficie visual"

Veredictos stdout (sin secretos)::

    PIT_DEV_QA_PASS | screenshots=<n> | elements_parsed=<n>      (exit 0)
    PIT_DEV_QA_SKIPPED | reason=<...>                            (exit 0)
    PIT_DEV_QA_FAIL | reason=<...>                               (exit 2)

El estado (PASS/FAIL/SKIPPED) SIEMPRE se persiste en el outcome: un QA_FAIL
registrado bloquea la entrega igual que un QA ausente — no hay bypass
silencioso.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PIT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

MIN_IFC_BYTES = 100 * 1024  # IFC real: >100 KB (mini-site.ifc pesa 4.4 KB)
MIN_SCREENSHOT_BYTES = 8 * 1024  # un PNG no trivial de UI pesa >> 8 KB
MIN_SCREENSHOTS = 3
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Fixtures de test conocidos que NO cuentan como "IFC real" (postmortem).
FIXTURE_DENYLIST = frozenset({"mini-site.ifc"})

STATUS_PASS = "QA_PASS"
STATUS_FAIL = "QA_FAIL"
STATUS_SKIPPED = "QA_SKIPPED_WITH_REASON"

VERDICT_PASS = "PIT_DEV_QA_PASS"
VERDICT_FAIL = "PIT_DEV_QA_FAIL"
VERDICT_SKIPPED = "PIT_DEV_QA_SKIPPED"

RESULTS_FILENAME = "qa_results.json"


class QaError(ValueError):
    """Fallo de un check del gate — el mensaje es el reason code del veredicto."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_vault_path() -> Path:
    return Path(os.environ.get("PIT_VAULT_PATH", "~/umbral-pit-vault")).expanduser()


def qa_screenshots_dir(vault_path: Path, pit_id: str) -> Path:
    return vault_path / "pit" / pit_id / "deliverables" / "qa-screenshots"


def qa_screenshots_rel(pit_id: str) -> str:
    return f"pit/{pit_id}/deliverables/qa-screenshots"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_ifc_source(
    ifc_path: Path | None,
    *,
    recorded_name: str | None = None,
    recorded_size: Any = None,
) -> dict[str, Any]:
    """Valida el IFC usado: real (>100 KB) y fuera del denylist de fixtures.

    Con ``ifc_path`` valida el archivo en disco; sin él (evidencia capturada
    en otra máquina) valida el nombre/tamaño registrados en qa_results.json.
    """
    if ifc_path is not None:
        if not ifc_path.is_file():
            raise QaError(f"ifc_file_missing:{ifc_path}")
        name = ifc_path.name
        size = ifc_path.stat().st_size
    else:
        name = str(recorded_name or "").strip()
        if not name:
            raise QaError("ifc_file_not_recorded")
        try:
            size = int(recorded_size)
        except (TypeError, ValueError):
            raise QaError("ifc_size_not_recorded") from None

    if name.lower() in FIXTURE_DENYLIST:
        raise QaError(f"ifc_is_test_fixture:{name}")
    if size <= MIN_IFC_BYTES:
        raise QaError(
            f"ifc_too_small:{name}:{size}B (min {MIN_IFC_BYTES}B — un fixture no es un IFC real)"
        )
    return {"ifc_file": name, "ifc_size_bytes": size}


def check_screenshots(shots_dir: Path) -> list[str]:
    """≥3 PNG reales (magic + tamaño no trivial) en qa-screenshots/."""
    if not shots_dir.is_dir():
        raise QaError(f"qa_screenshots_dir_missing:{shots_dir}")
    valid: list[str] = []
    for path in sorted(shots_dir.glob("*.png")):
        try:
            with path.open("rb") as handle:
                magic = handle.read(len(PNG_MAGIC))
        except OSError:
            continue
        if magic != PNG_MAGIC:
            continue
        if path.stat().st_size < MIN_SCREENSHOT_BYTES:
            continue
        valid.append(path.name)
    if len(valid) < MIN_SCREENSHOTS:
        raise QaError(
            f"qa_screenshots_insufficient:{len(valid)}/{MIN_SCREENSHOTS} "
            f"(PNG reales ≥{MIN_SCREENSHOT_BYTES}B en {shots_dir})"
        )
    return valid


def load_results(shots_dir: Path) -> dict[str, Any]:
    results_path = shots_dir / RESULTS_FILENAME
    if not results_path.is_file():
        raise QaError(f"qa_results_missing:{results_path}")
    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QaError(f"qa_results_unparseable:{exc.__class__.__name__}") from exc
    if not isinstance(data, dict):
        raise QaError("qa_results_not_an_object")
    return data


def validate_results(results: dict[str, Any]) -> int:
    """≥1 elemento parseado y sin error fatal — devuelve elements_parsed."""
    try:
        elements = int(results.get("elements_parsed"))
    except (TypeError, ValueError):
        raise QaError("elements_parsed_not_recorded") from None
    if elements < 1:
        raise QaError(f"no_elements_parsed:{elements}")
    if results.get("fatal_error"):
        raise QaError(f"fatal_error_recorded:{results.get('fatal_error')}")
    return elements


# ---------------------------------------------------------------------------
# Outcome update
# ---------------------------------------------------------------------------
def update_outcome_human_qa(
    vault_path: Path, pit_id: str, block: dict[str, Any]
) -> Path:
    """Escribe el bloque ``human_qa`` en el outcome report (debe existir)."""
    outcome_path = vault_path / "pit" / pit_id / "outcome" / "pit_outcome_report.yaml"
    if not outcome_path.is_file():
        raise QaError(f"outcome_missing:{outcome_path}")
    try:
        raw = yaml.safe_load(outcome_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise QaError(f"outcome_unparseable:{exc.__class__.__name__}") from exc
    if not isinstance(raw, dict):
        raise QaError("outcome_not_a_mapping")
    raw["human_qa"] = block
    outcome_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return outcome_path


def build_block(
    *,
    status: str,
    mode: str,
    pit_id: str,
    real_ifc_upload: str,
    ifc_meta: dict[str, Any] | None = None,
    elements_parsed: int | None = None,
    screenshots: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    ifc_meta = ifc_meta or {}
    return {
        "status": status,
        "real_ifc_upload": real_ifc_upload,
        "ifc_file": ifc_meta.get("ifc_file"),
        "ifc_size_bytes": ifc_meta.get("ifc_size_bytes"),
        "elements_parsed": elements_parsed,
        "screenshots_dir": qa_screenshots_rel(pit_id),
        "screenshots": screenshots or [],
        "verified_at": _now_iso(),
        "mode": mode,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------
def run_skip(pit_id: str, reason: str) -> tuple[str, dict[str, Any]]:
    reason = (reason or "").strip()
    if not reason:
        raise QaError("skip_requires_reason")
    block = build_block(
        status=STATUS_SKIPPED,
        mode="skip",
        pit_id=pit_id,
        real_ifc_upload="skipped",
        reason=reason,
    )
    return STATUS_SKIPPED, block


def run_evidence(
    vault_path: Path, pit_id: str, ifc_file: Path | None
) -> tuple[str, dict[str, Any]]:
    """Valida evidencia ya presente en deliverables/qa-screenshots/."""
    shots_dir = qa_screenshots_dir(vault_path, pit_id)
    screenshots = check_screenshots(shots_dir)
    results = load_results(shots_dir)
    elements = validate_results(results)
    ifc_meta = check_ifc_source(
        ifc_file,
        recorded_name=results.get("ifc_file"),
        recorded_size=results.get("ifc_size_bytes"),
    )
    block = build_block(
        status=STATUS_PASS,
        mode="evidence",
        pit_id=pit_id,
        real_ifc_upload="pass",
        ifc_meta=ifc_meta,
        elements_parsed=elements,
        screenshots=screenshots,
    )
    return STATUS_PASS, block


def _import_playwright():  # seam para tests — playwright es dependencia opcional
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    return sync_playwright


def run_auto(
    vault_path: Path,
    pit_id: str,
    *,
    app_url: str,
    ifc_file: Path,
    elements_js: str | None,
    elements_selector: str | None,
    file_input_selector: str,
    properties_click_selector: str | None,
    observation_click_selector: str | None,
    wait_ms: int,
) -> tuple[str, dict[str, Any]]:
    """Corre el flujo headless contra el winner servido y captura evidencia."""
    ifc_meta = check_ifc_source(ifc_file)
    if not elements_js and not elements_selector:
        raise QaError(
            "elements_probe_required:pasar --elements-js o --elements-selector "
            "(el gate debe verificar elementos parseados, no solo HTTP 200)"
        )
    try:
        sync_playwright = _import_playwright()
    except ImportError as exc:
        raise QaError("playwright_not_installed:pip install playwright && playwright install chromium") from exc

    shots_dir = qa_screenshots_dir(vault_path, pit_id)
    shots_dir.mkdir(parents=True, exist_ok=True)

    notes: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(app_url, wait_until="load")
            page.set_input_files(file_input_selector, str(ifc_file))
            page.wait_for_timeout(wait_ms)

            page.screenshot(path=str(shots_dir / "01-viewer-3d.png"), full_page=True)
            notes.append("01-viewer-3d: vista tras cargar el IFC real")

            if elements_js:
                elements = int(page.evaluate(elements_js) or 0)
            else:
                elements = page.locator(elements_selector).count()

            if properties_click_selector:
                page.click(properties_click_selector)
            else:
                # Picking best-effort: click al centro del canvas.
                canvas = page.locator("canvas").first
                canvas.click(position={"x": 400, "y": 300})
            page.wait_for_timeout(min(wait_ms, 2000))
            page.screenshot(path=str(shots_dir / "02-properties.png"), full_page=True)
            notes.append("02-properties: panel de propiedades / picking")

            if observation_click_selector:
                page.click(observation_click_selector)
                page.wait_for_timeout(min(wait_ms, 2000))
                notes.append("03-observation: observación/export disparado")
            else:
                notes.append("03-observation: estado final (sin selector de observación)")
            page.screenshot(path=str(shots_dir / "03-observation.png"), full_page=True)

            body_text = page.inner_text("body")
            fatal = any(marker in body_text for marker in ("Traceback", "Uncaught", "FATAL"))
        finally:
            browser.close()

    results = {
        "pit_id": pit_id,
        "ifc_file": ifc_meta["ifc_file"],
        "ifc_size_bytes": ifc_meta["ifc_size_bytes"],
        "elements_parsed": elements,
        "fatal_error": fatal,
        "notes": "; ".join(notes),
        "captured_at": _now_iso(),
    }
    (shots_dir / RESULTS_FILENAME).write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    screenshots = check_screenshots(shots_dir)
    elements = validate_results(results)
    block = build_block(
        status=STATUS_PASS,
        mode="auto",
        pit_id=pit_id,
        real_ifc_upload="pass",
        ifc_meta=ifc_meta,
        elements_parsed=elements,
        screenshots=screenshots,
    )
    return STATUS_PASS, block


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pit_dev_human_qa_gate",
        description="PIT-DEV — gate de QA de producto (IFC real + screenshots) pre-entrega.",
    )
    parser.add_argument("--pit-id", required=True)
    parser.add_argument("--vault-path", type=Path, default=None,
                        help="Raíz del pit-vault (default: $PIT_VAULT_PATH o ~/umbral-pit-vault)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--auto", action="store_true",
                      help="Flujo headless con playwright contra el winner servido")
    mode.add_argument("--from-evidence", action="store_true",
                      help="Validar screenshots + qa_results.json ya capturados")
    mode.add_argument("--skip", action="store_true",
                      help="Registrar QA_SKIPPED_WITH_REASON (requiere --reason)")
    parser.add_argument("--reason", default=None, help="Motivo del --skip (obligatorio con --skip)")
    parser.add_argument("--ifc-file", type=Path, default=None,
                        help="IFC real (>100 KB) usado en el QA — obligatorio con --auto")
    parser.add_argument("--app-url", default=None, help="URL del winner servido (--auto)")
    parser.add_argument("--elements-js", default=None,
                        help="Expresión JS que devuelve el nº de elementos parseados (--auto)")
    parser.add_argument("--elements-selector", default=None,
                        help="Selector CSS cuyo count = elementos parseados (--auto)")
    parser.add_argument("--file-input-selector", default='input[type="file"]')
    parser.add_argument("--properties-click-selector", default=None)
    parser.add_argument("--observation-click-selector", default=None)
    parser.add_argument("--wait-ms", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pit_id = str(args.pit_id)
    if not PIT_ID_RE.match(pit_id):
        print(f"{VERDICT_FAIL} | reason=invalid_pit_id:{pit_id}")
        return 2
    vault = (args.vault_path or default_vault_path()).expanduser()

    status: str
    block: dict[str, Any]
    try:
        if args.skip:
            status, block = run_skip(pit_id, args.reason or "")
        elif args.from_evidence:
            status, block = run_evidence(vault, pit_id, args.ifc_file)
        else:  # --auto
            if not args.app_url or not args.ifc_file:
                raise QaError("auto_requires_app_url_and_ifc_file")
            status, block = run_auto(
                vault,
                pit_id,
                app_url=args.app_url,
                ifc_file=args.ifc_file,
                elements_js=args.elements_js,
                elements_selector=args.elements_selector,
                file_input_selector=args.file_input_selector,
                properties_click_selector=args.properties_click_selector,
                observation_click_selector=args.observation_click_selector,
                wait_ms=args.wait_ms,
            )
    except QaError as exc:
        # Registrar el FAIL en el outcome (best-effort) — sin bypass silencioso.
        fail_block = build_block(
            status=STATUS_FAIL,
            mode="auto" if args.auto else ("evidence" if args.from_evidence else "skip"),
            pit_id=pit_id,
            real_ifc_upload="fail",
            reason=str(exc),
        )
        try:
            update_outcome_human_qa(vault, pit_id, fail_block)
        except QaError:
            pass  # el reason primario es el del check; outcome_missing ya bloquea deliver
        print(f"{VERDICT_FAIL} | reason={exc}")
        return 2
    except Exception as exc:  # error inesperado — veredicto legible, sin traceback
        print(f"{VERDICT_FAIL} | reason={type(exc).__name__}:{exc}")
        return 2

    try:
        outcome_path = update_outcome_human_qa(vault, pit_id, block)
    except QaError as exc:
        print(f"{VERDICT_FAIL} | reason={exc}")
        return 2

    if status == STATUS_SKIPPED:
        print(f"{VERDICT_SKIPPED} | reason={block['reason']} | outcome={outcome_path}")
        return 0
    print(
        f"{VERDICT_PASS} | screenshots={len(block['screenshots'])} "
        f"| elements_parsed={block['elements_parsed']} | outcome={outcome_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
