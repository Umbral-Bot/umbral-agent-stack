#!/usr/bin/env python3
"""PIT — deliver pack post-torneo: deck (+ zip PIT-DEV) → Drive → telegram_pack.json.

Flujo (PIT-TG-DRIVE — orden canónico de entrega en SKILL §Post-torneo):
  1. Lee ``pit/<pit_id>/outcome/pit_outcome_report.yaml`` del vault.
     Falla si no existe o si el winner sigue pending (gate David):
     ``david_gate`` cuenta como pending por PREFIJO ("pending", "pending
     review de David", …), no por igualdad exacta.
  2. Construye el deck ejecutivo con ``pit_build_outcome_deck.build_deck``.
  3. **Solo PIT-DEV** (spec v3, ``mode: dev`` en ``pit/<pit_id>/spec/``) —
     gates de calidad fail-closed (postmortem ``pit-dev-ifc-viewer``):
     a. gate de trazabilidad — ``check_traceability`` debe dar
        ``TRACE_COMPLETE`` y ``traceability/report.md`` debe existir
        (FAIL ``traceability_report_missing`` / ``traceability_gaps:<lista>``);
     b. **billing truth** — ``budget.tokens_total`` numérico > 0 en el outcome
        (lo puebla ``pit_collect_tokens.py --update-outcome``); con
        ``not_reported``/ausente NO hay entrega (FAIL
        ``tokens_total_not_reported``);
     c. **QA de producto** — bloque ``human_qa`` con ``QA_PASS`` (y los
        screenshots reales en ``deliverables/qa-screenshots/``) o
        ``QA_SKIPPED_WITH_REASON`` con motivo auditable (lo escribe
        ``pit_dev_human_qa_gate.py``); FAIL ``human_qa_missing`` /
        ``human_qa_failed:<status>`` / ``human_qa_skip_without_reason`` /
        ``qa_screenshots_missing:<detalle>``;
     d. **fulfillment explícito** — ``fulfillment_decision.product_fulfillment``
        ∈ {accepted, rejected, pending_validation}: el cierre procedural NUNCA
        implica aceptación de producto (FAIL ``product_fulfillment_missing`` /
        ``product_fulfillment_invalid:<v>``);
     e. zip del deliverable winner
        (``pit/<pit_id>/lanes/<winner>/deliverable/`` →
        ``pit/<pit_id>/deliverables/<pit_id>-<winner>-deliverable.zip``).
  4. Sube el .pptx (y el .zip en PIT-DEV) a la carpeta compartida Rick↔David
     (``GOOGLE_DRIVE_PIT_FOLDER_ID``) vía el handler Worker
     ``google_drive.upload_file`` (import directo) → ``web_view_link``.
  5. Hook Notion fase 2 (``notion_publish_stub``): reserva
     ``notion_page_url: null`` en el pack — publicación de subpágina Notion
     documentada pero NO implementada aún.
  6. Escribe ``pit/<pit_id>/deliverables/telegram_pack.json`` con
     ``{pit_id, drive_deck_url, drive_file_id, deliverable_zip_path,
     drive_deliverable_zip_url, drive_deliverable_zip_file_id,
     notion_page_url, mc_judge_hint, summary_lines[]}``.
  7. Veredicto stdout (sin secretos):
     ``PIT_DELIVER_PACK_OK | drive_url=<webViewLink>``
     (`` | deliverable_zip_url=<webViewLink>`` en PIT-DEV)
     ``PIT_DELIVER_PACK_DRY_OK`` (con ``--dry-run``: deck + zip + pack, sin Drive)
     ``PIT_DELIVER_PACK_FAIL | reason=<...>`` (exit 2)

Rick usa ``summary_lines`` como plantilla Telegram (≤12 líneas + link Drive);
NUNCA se adjunta el .pptx/.zip por Telegram. Si Drive no está configurado el
fallback es texto + MC judge hint (comportamiento actual) — este script lo
reporta como FAIL ``drive_not_configured`` para que Rick no invente links.

Los modos v1 producto y v2 broker NO cambian: sin spec ``mode: dev`` en el
vault, el flujo es idéntico al histórico (deck solo, sin gates dev).

Uso::

    python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id> \
        [--vault-path <path>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pit.pit_build_outcome_deck import (  # noqa: E402
    _clean,
    _fmt_num,
    build_deck,
    load_yaml,
)
from scripts.pit.pit_dev_human_qa_gate import (  # noqa: E402
    STATUS_PASS as QA_STATUS_PASS,
    STATUS_SKIPPED as QA_STATUS_SKIPPED,
    check_screenshots,
    qa_screenshots_dir,
)
from scripts.pit.pit_spec_validate import is_dev_spec  # noqa: E402
from scripts.pit.pit_traceability_check import check_traceability  # noqa: E402

VERDICT_OK = "PIT_DELIVER_PACK_OK"
VERDICT_DRY_OK = "PIT_DELIVER_PACK_DRY_OK"
VERDICT_FAIL = "PIT_DELIVER_PACK_FAIL"

_PENDING_VALUES = {"", "null", "none"}
_PENDING_PREFIX = "pending"

# Fulfillment de producto explícito (gate C, postmortem pit-dev-ifc-viewer):
# cierre procedural (trace + gate David) ≠ aceptación del producto.
PRODUCT_FULFILLMENT_VALUES = frozenset({"accepted", "rejected", "pending_validation"})
PRODUCT_FULFILLMENT_LABELS = {
    "accepted": "aceptado",
    "rejected": "rechazado",
    "pending_validation": "pendiente validación David",
}


def default_vault_path() -> Path:
    return Path(os.environ.get("PIT_VAULT_PATH", "~/umbral-pit-vault")).expanduser()


def winner_is_closed(outcome: dict[str, Any]) -> bool:
    """Gate: hay winner con lane_id real y david_gate no pending.

    ``david_gate`` cuenta como pending por PREFIJO, no por igualdad exacta:
    "pending", "pending review de David", "pending_gate", "PENDING — …" son
    todos pending. También cuentan vacío/null/none y los placeholders de
    plantilla (``<...>``, que ``_clean`` reduce a vacío).
    """
    winner = outcome.get("winner") or {}
    lane_id = _clean(winner.get("lane_id"), "")
    gate = _clean(winner.get("david_gate"), "")
    if not lane_id:
        return False
    gate_norm = gate.lower()
    if gate_norm in _PENDING_VALUES:
        return False
    return not gate_norm.startswith(_PENDING_PREFIX)


def load_spec_raw(vault_path: Path, pit_id: str) -> dict[str, Any] | None:
    """Lee ``pit/<pit_id>/spec/pit_spec.yaml`` si existe (sin validar)."""
    for name in ("pit_spec.yaml", "pit_spec.yml"):
        spec_path = vault_path / "pit" / pit_id / "spec" / name
        if spec_path.is_file():
            try:
                return load_yaml(spec_path)
            except Exception:
                return None
    return None


def is_dev_tournament(vault_path: Path, pit_id: str) -> bool:
    """True si el spec del vault es PIT-DEV (v3 / ``mode: dev``)."""
    raw = load_spec_raw(vault_path, pit_id)
    return bool(raw) and is_dev_spec(raw)


def assert_traceability_complete(vault_path: Path, pit_id: str) -> None:
    """Gate PIT-DEV: entrega solo con ``TRACE_COMPLETE`` (fail-closed).

    Exige ``pit/<pit_id>/traceability/report.md`` (el agente de trazabilidad
    corrió) y re-verifica la cadena con ``check_traceability``. Con gaps NO se
    entrega: informe a Rick → mejora continua, no bypass silencioso.
    """
    report = vault_path / "pit" / pit_id / "traceability" / "report.md"
    if not report.is_file():
        raise ValueError("traceability_report_missing")
    result = check_traceability(vault_path, pit_id)
    if not result.get("complete"):
        gaps = ",".join(result.get("gaps") or []) or "unknown"
        raise ValueError(f"traceability_gaps:{gaps}")


def assert_billing_truth(outcome: dict[str, Any]) -> None:
    """Gate PIT-DEV: billing truth — ``budget.tokens_total`` numérico > 0.

    ``budget_usd`` es el TECHO autorizado, no el gasto; sin
    ``tokens_total`` real (lo puebla ``pit_collect_tokens.py
    --update-outcome``) el torneo NO se entrega como cerrado. Un
    ``not_reported`` honesto bloquea — un \"0/50 USD\" engañoso ya no pasa.
    """
    budget = outcome.get("budget") or {}
    tokens_total = budget.get("tokens_total")
    if isinstance(tokens_total, bool) or not isinstance(tokens_total, (int, float)):
        raise ValueError("tokens_total_not_reported")
    if tokens_total <= 0:
        raise ValueError("tokens_total_not_reported")


def assert_human_qa(outcome: dict[str, Any], vault_path: Path, pit_id: str) -> None:
    """Gate PIT-DEV: QA de producto (``pit_dev_human_qa_gate.py``) fail-closed.

    ``QA_PASS`` exige además que los screenshots sigan en
    ``deliverables/qa-screenshots/`` (≥3 PNG reales). ``QA_SKIPPED_WITH_REASON``
    pasa SOLO con motivo no vacío — queda visible en el pack, no es un verde
    silencioso. Todo lo demás (ausente, QA_FAIL, estados desconocidos) bloquea.
    """
    block = outcome.get("human_qa")
    if not isinstance(block, dict):
        raise ValueError("human_qa_missing")
    status = _clean(block.get("status"), "")
    if status == QA_STATUS_PASS:
        try:
            check_screenshots(qa_screenshots_dir(vault_path, pit_id))
        except ValueError as exc:
            raise ValueError(f"qa_screenshots_missing:{exc}") from exc
        return
    if status == QA_STATUS_SKIPPED:
        if not _clean(block.get("reason"), ""):
            raise ValueError("human_qa_skip_without_reason")
        return
    raise ValueError(f"human_qa_failed:{status or 'unknown'}")


def assert_product_fulfillment(outcome: dict[str, Any]) -> str:
    """Gate PIT-DEV: fulfillment de producto EXPLÍCITO (≠ cierre procedural).

    Devuelve el valor validado. ``pending_validation`` es legítimo (David
    decide post-pack) pero tiene que estar declarado — la ausencia era el bug
    del incidente: cierre admin leído como aceptación de producto.
    """
    decision = outcome.get("fulfillment_decision") or {}
    value = _clean(decision.get("product_fulfillment"), "")
    if not value:
        raise ValueError("product_fulfillment_missing")
    if value not in PRODUCT_FULFILLMENT_VALUES:
        raise ValueError(f"product_fulfillment_invalid:{value}")
    return value


def build_deliverable_zip(vault_path: Path, pit_id: str, winner_lane: str) -> Path:
    """Zipea ``lanes/<winner>/deliverable/`` en ``deliverables/`` (PIT-DEV)."""
    deliverable_dir = (
        vault_path / "pit" / pit_id / "lanes" / winner_lane / "deliverable"
    )
    if not deliverable_dir.is_dir() or not any(deliverable_dir.iterdir()):
        raise ValueError(f"winner_deliverable_missing:{deliverable_dir}")
    out_dir = vault_path / "pit" / pit_id / "deliverables"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_base = out_dir / f"{pit_id}-{winner_lane}-deliverable"
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=deliverable_dir)
    return Path(archive)


def notion_publish_stub(pack: dict[str, Any]) -> None:
    """Fase 2 — hook documentado, NO implementado: subpágina Notion post-torneo.

    Contrato previsto (cuando se implemente):
      - task Worker ``notion.create_page`` bajo el índice PIT del Control Room,
        con el resumen del outcome + links Drive (deck + zip deliverable);
      - escribe ``notion_page_url`` en este pack y en el outcome report
        (``deliverables.notion_page_url``);
      - el mensaje de CIERRE de Rick suma el link Notion a los links Drive.

    Hasta entonces el pack lleva ``notion_page_url: null`` y el cierre NO
    menciona Notion. Orden canónico: SKILL §Post-torneo (entrega) y
    ``docs/ops/pit-dev-mode-vision-2026-07-03.md`` §Cierre.
    """
    pack.setdefault("notion_page_url", None)


def build_summary_lines(
    outcome: dict[str, Any],
    drive_url: str | None,
    *,
    deliverable_zip_url: str | None = None,
    dev_mode: bool = False,
) -> list[str]:
    """Plantilla Telegram ejecutiva (≤12 líneas) — SKILL §Entrega Telegram.

    Billing truth: la línea de budget SIEMPRE distingue gasto estimado de
    techo autorizado (nunca un \"0/50\" ambiguo). En PIT-DEV la línea de
    preview (v1) se reemplaza por el zip del winner en Drive y se agrega la
    línea Producto (fulfillment explícito + estado QA).
    """
    pit_id = _clean(outcome.get("pit_id"), "pit-?")
    winner = outcome.get("winner") or {}
    winner_lane = _clean(winner.get("lane_id"), "pending")

    fulfillment = "—"
    for lane in outcome.get("lanes") or []:
        if isinstance(lane, dict) and _clean(lane.get("lane_id"), "") == winner_lane:
            fulfillment = _fmt_num(lane.get("fulfillment_score"))
            break

    budget = outcome.get("budget") or {}
    lanes_count = len(outcome.get("lanes") or [])
    spent = _fmt_num(budget.get("usd_estimated_spent"), "no reportado")
    ceiling = _fmt_num(budget.get("budget_usd"))
    tokens_total = budget.get("tokens_total")
    if isinstance(tokens_total, (int, float)) and not isinstance(tokens_total, bool):
        tokens_text = f" · tokens {_fmt_num(tokens_total)}"
    else:
        tokens_text = " · tokens not_reported"
    budget_line = (
        f"• {lanes_count} lanes · gasto estimado {spent} USD / techo {ceiling} USD"
        f"{tokens_text}"
    )

    problem_line = _clean(outcome.get("title"), pit_id)

    kpi_line = "KPI clave: —"
    for kpi in outcome.get("kpi_summary") or []:
        if isinstance(kpi, dict):
            kpi_line = (
                f"KPI clave: {_clean(kpi.get('kpi_id'), 'kpi')} "
                f"{_fmt_num(kpi.get('kpi_achieved'))} vs {_fmt_num(kpi.get('kpi_expected'))} "
                f"{_clean(kpi.get('unit'), '')}".rstrip()
            )
            break

    learnings = outcome.get("learnings") or {}
    learning_line = "Aprendizaje: —"
    for key in ("validated", "refuted"):
        items = [item for item in (learnings.get(key) or []) if _clean(item, "")]
        if items:
            prefix = "validado" if key == "validated" else "refutado"
            learning_line = f"Aprendizaje ({prefix}): {_clean(items[0])}"
            break

    if dev_mode:
        artifact_line = (
            "Deliverable winner (zip, Drive): "
            f"{deliverable_zip_url or '(pendiente — Drive no configurado)'}"
        )
    else:
        artifact_line = (
            f"Preview prototipos (PC + túnel): scripts/ops/pit-judge-open.ps1 → /pit/judge/{pit_id}"
        )

    lines = [
        f"TORNEO PIT · {pit_id}",
        f"Estado: cerrado · Winner: {winner_lane} · Fulfillment: {fulfillment}",
        "Resumen:",
        f"• {problem_line}",
        budget_line,
        f"• {kpi_line}",
        f"• {learning_line}",
        "Deck ejecutivo (Google Drive):",
        drive_url or "(pendiente — Drive no configurado; usar preview MC)",
        artifact_line,
        f"Detalle vault: pit/{pit_id}/outcome/pit_outcome_report.yaml",
    ]
    if dev_mode:
        decision = outcome.get("fulfillment_decision") or {}
        pf_value = _clean(decision.get("product_fulfillment"), "")
        pf_label = PRODUCT_FULFILLMENT_LABELS.get(pf_value, pf_value or "no declarado")
        qa_block = outcome.get("human_qa") or {}
        qa_status = _clean(qa_block.get("status"), "sin QA")
        product_line = f"• Producto: fulfillment {pf_label} · QA {qa_status}"
        if qa_status == QA_STATUS_SKIPPED:
            product_line += f" ({_clean(qa_block.get('reason'), 's/motivo')})"
        lines.insert(7, product_line)
    assert len(lines) <= 12, "plantilla Telegram debe ser ≤12 líneas"
    return lines


def drive_env_configured() -> bool:
    required = (
        "GOOGLE_DRIVE_PIT_FOLDER_ID",
        "GOOGLE_DRIVE_OAUTH_CLIENT_ID",
        "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET",
        "GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN",
    )
    return all((os.environ.get(name) or "").strip() for name in required)


def deliver(
    pit_id: str,
    vault_path: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Ejecuta el flujo; devuelve (veredicto, pack). Lanza ValueError en FAIL."""
    outcome_path = vault_path / "pit" / pit_id / "outcome" / "pit_outcome_report.yaml"
    if not outcome_path.is_file():
        raise ValueError(f"outcome_missing:{outcome_path}")

    outcome = load_yaml(outcome_path)
    if _clean(outcome.get("pit_id"), "") != pit_id:
        raise ValueError("outcome_pit_id_mismatch")
    if not winner_is_closed(outcome):
        raise ValueError("winner_pending")

    dev_mode = is_dev_tournament(vault_path, pit_id)
    winner_lane = _clean((outcome.get("winner") or {}).get("lane_id"), "")

    if dev_mode:
        # Gates de calidad PIT-DEV (fail-closed, ANTES de construir nada):
        # trazabilidad + billing truth + QA producto + fulfillment explícito.
        # Postmortem pit-dev-ifc-viewer: el cierre procedural verde no vuelve
        # a taparse una calidad de producto inaceptable.
        assert_traceability_complete(vault_path, pit_id)
        assert_billing_truth(outcome)
        assert_human_qa(outcome, vault_path, pit_id)
        assert_product_fulfillment(outcome)

    deck = build_deck(outcome_path)
    deck_path = deck.get("path")
    if not deck.get("ok") or not deck_path:
        raise ValueError("deck_build_failed")

    zip_path: Path | None = None
    if dev_mode:
        # Orden canónico PIT-DEV (SKILL §Post-torneo): el zip del deliverable
        # winner viaja con el deck.
        zip_path = build_deliverable_zip(vault_path, pit_id, winner_lane)

    drive_url: str | None = None
    drive_file_id: str | None = None
    zip_drive_url: str | None = None
    zip_drive_file_id: str | None = None
    if dry_run:
        verdict = VERDICT_DRY_OK
    else:
        if not drive_env_configured():
            raise ValueError("drive_not_configured")
        from worker.tasks.google_drive import handle_google_drive_upload_file

        upload = handle_google_drive_upload_file({"local_path": deck_path})
        if not upload.get("ok"):
            raise ValueError(f"drive_upload_failed:{upload.get('error', 'unknown')}")
        drive_url = upload.get("web_view_link") or None
        drive_file_id = upload.get("file_id") or None
        if not drive_url:
            raise ValueError("drive_upload_no_link")
        if zip_path is not None:
            zip_upload = handle_google_drive_upload_file(
                {"local_path": str(zip_path)}
            )
            if not zip_upload.get("ok"):
                raise ValueError(
                    f"drive_zip_upload_failed:{zip_upload.get('error', 'unknown')}"
                )
            zip_drive_url = zip_upload.get("web_view_link") or None
            zip_drive_file_id = zip_upload.get("file_id") or None
            if not zip_drive_url:
                raise ValueError("drive_zip_upload_no_link")
        verdict = VERDICT_OK

    pack = {
        "pit_id": pit_id,
        "drive_deck_url": drive_url,
        "drive_file_id": drive_file_id,
        "deck_path": str(deck_path),
        "deliverable_zip_path": str(zip_path) if zip_path else None,
        "drive_deliverable_zip_url": zip_drive_url,
        "drive_deliverable_zip_file_id": zip_drive_file_id,
        "mc_judge_hint": f"scripts/ops/pit-judge-open.ps1 → /pit/judge/{pit_id}",
        "summary_lines": build_summary_lines(
            outcome,
            drive_url,
            deliverable_zip_url=zip_drive_url,
            dev_mode=dev_mode,
        ),
    }
    notion_publish_stub(pack)  # fase 2: subpágina Notion — hook documentado

    pack_path = vault_path / "pit" / pit_id / "deliverables" / "telegram_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pack["pack_path"] = str(pack_path)
    return verdict, pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pit-id", required=True, help="pit_id del torneo cerrado")
    parser.add_argument("--vault-path", type=Path, default=None,
                        help="Raíz del pit-vault (default: $PIT_VAULT_PATH o ~/umbral-pit-vault)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Construye deck + pack sin subir a Drive (sin red)")
    args = parser.parse_args(argv)

    vault = args.vault_path or default_vault_path()
    try:
        verdict, pack = deliver(args.pit_id, vault, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"{VERDICT_FAIL} | reason={exc}")
        return 2
    except Exception as exc:  # error inesperado, igual sin traceback al chat
        print(f"{VERDICT_FAIL} | reason={type(exc).__name__}:{exc}")
        return 2

    if verdict == VERDICT_OK:
        line = f"{verdict} | drive_url={pack['drive_deck_url']}"
        if pack.get("drive_deliverable_zip_url"):
            line += f" | deliverable_zip_url={pack['drive_deliverable_zip_url']}"
        print(line)
    else:
        print(f"{verdict} | deck={pack['deck_path']} | pack={pack['pack_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
