#!/usr/bin/env python3
"""PIT — deliver pack post-torneo: deck → Drive → telegram_pack.json.

Flujo (PIT-TG-DRIVE):
  1. Lee ``pit/<pit_id>/outcome/pit_outcome_report.yaml`` del vault.
     Falla si no existe o si el winner sigue pending (gate David).
  2. Construye el deck ejecutivo con ``pit_build_outcome_deck.build_deck``.
  3. Sube el .pptx a la carpeta compartida Rick↔David vía el handler Worker
     ``google_drive.upload_file`` (import directo) → ``web_view_link``.
  4. Escribe ``pit/<pit_id>/deliverables/telegram_pack.json`` con
     ``{pit_id, drive_deck_url, drive_file_id, mc_judge_hint, summary_lines[]}``.
  5. Veredicto stdout (sin secretos):
     ``PIT_DELIVER_PACK_OK | drive_url=<webViewLink>``
     ``PIT_DELIVER_PACK_DRY_OK`` (con ``--dry-run``: deck + pack, sin Drive)
     ``PIT_DELIVER_PACK_FAIL | reason=<...>`` (exit 2)

Rick usa ``summary_lines`` como plantilla Telegram (≤12 líneas + link Drive);
NUNCA se adjunta el .pptx por Telegram (v1). Si Drive no está configurado el
fallback es texto + MC judge hint (comportamiento actual) — este script lo
reporta como FAIL ``drive_not_configured`` para que Rick no invente links.

Uso::

    python scripts/pit/pit_deliver_telegram_pack.py --pit-id <pit_id> \
        [--vault-path <path>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
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

VERDICT_OK = "PIT_DELIVER_PACK_OK"
VERDICT_DRY_OK = "PIT_DELIVER_PACK_DRY_OK"
VERDICT_FAIL = "PIT_DELIVER_PACK_FAIL"

_PENDING_VALUES = {"", "pending", "null", "none"}


def default_vault_path() -> Path:
    return Path(os.environ.get("PIT_VAULT_PATH", "~/umbral-pit-vault")).expanduser()


def winner_is_closed(outcome: dict[str, Any]) -> bool:
    """Gate: hay winner con lane_id real y david_gate no pending."""
    winner = outcome.get("winner") or {}
    lane_id = _clean(winner.get("lane_id"), "")
    gate = _clean(winner.get("david_gate"), "")
    if not lane_id:
        return False
    return gate.lower() not in _PENDING_VALUES


def build_summary_lines(outcome: dict[str, Any], drive_url: str | None) -> list[str]:
    """Plantilla Telegram ejecutiva (≤12 líneas) — SKILL §Entrega Telegram."""
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

    lines = [
        f"TORNEO PIT · {pit_id}",
        f"Estado: cerrado · Winner: {winner_lane} · Fulfillment: {fulfillment}",
        "Resumen:",
        f"• {problem_line}",
        f"• {lanes_count} lanes · budget {_fmt_num(budget.get('usd_estimated_spent'))}/"
        f"{_fmt_num(budget.get('budget_usd'))} USD (estimado)",
        f"• {kpi_line}",
        f"• {learning_line}",
        "Deck ejecutivo (Google Drive):",
        drive_url or "(pendiente — Drive no configurado; usar preview MC)",
        f"Preview prototipos (PC + túnel): scripts/ops/pit-judge-open.ps1 → /pit/judge/{pit_id}",
        f"Detalle vault: pit/{pit_id}/outcome/pit_outcome_report.yaml",
    ]
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

    deck = build_deck(outcome_path)
    deck_path = deck.get("path")
    if not deck.get("ok") or not deck_path:
        raise ValueError("deck_build_failed")

    drive_url: str | None = None
    drive_file_id: str | None = None
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
        verdict = VERDICT_OK

    pack = {
        "pit_id": pit_id,
        "drive_deck_url": drive_url,
        "drive_file_id": drive_file_id,
        "deck_path": str(deck_path),
        "mc_judge_hint": f"scripts/ops/pit-judge-open.ps1 → /pit/judge/{pit_id}",
        "summary_lines": build_summary_lines(outcome, drive_url),
    }

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
        print(f"{verdict} | drive_url={pack['drive_deck_url']}")
    else:
        print(f"{verdict} | deck={pack['deck_path']} | pack={pack['pack_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
