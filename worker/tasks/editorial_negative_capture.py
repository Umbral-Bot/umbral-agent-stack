"""
Task: editorial.capture_negative_example — P2.5 poller/handler.

Closes fila D of the gap matrix (previously AUSENTE): when a Shortlist
("Alternativas / Shortlist") row is marked `Resultado revisión = Descartar`,
persist/validate the negative-example fields the contract requires — per:

    docs/ops/editorial-norte-hitl-contract-2026-07-22.md §4 (Descartar: "no
      procede y registra un ejemplo negativo")
    docs/ops/editorial-roadmap-norte-p1-p3-2026-07-22.md P2.5
    notion/schemas/alternativas-shortlist.schema.yaml (source fields, live)

Contract (do not weaken):
- Writing to Notion is Worker/core's exclusive job (ADR-011 #1) — the
  dispatcher poller only decides *which* Shortlist rows still need capture;
  it never writes to Notion itself.
- Fail-closed: this handler re-fetches the Shortlist page itself and only
  acts when `Resultado revisión == "Descartar"` is verified live — it never
  trusts a caller-supplied snapshot for the gate check.
- Idempotent: `ejemplo_negativo` is both the input signal ("has this been
  captured?") and, once flipped to true by this handler, the terminal
  marker — a row with `ejemplo_negativo == True` is a no-op
  (`already_captured=True`), mirroring `promovido_a` (P2.1) and
  `dedupe_status` (P2.4).
- `motivo_descarte` is a hard requirement: the schema's own description
  ("Requerido si Resultado revisión = Descartar") is a convention, not a
  Notion-enforced constraint, so this handler enforces it in code — a
  Descartar without a reason is refused (`error: "motivo_descarte_missing"`)
  rather than silently marking `ejemplo_negativo = true` with nothing useful
  for rick-qa/generation to learn from. `error_kind` stays optional: its own
  schema description says its options are deliberately unenumerated
  ("poblar empiricamente ... no inventar un enum cerrado aqui"), so this
  handler never blocks on it being empty and never invents a value.
- This handler never opens a gate, never publishes, never promotes, never
  writes copy/images — Descartar is a *terminal, negative* outcome (distinct
  from Aprobar/P2.1), and this package only captures the negative-example
  metadata for later consumption (see scripts/editorial/sync_negative_examples.py),
  it does not itself consume/act on it.
"""

from __future__ import annotations

from typing import Any, Dict

from .. import notion_client

_DISCARDED_VALUE = "Descartar"


def _flatten_prop(prop: Any) -> Any:
    """Flatten a single raw Notion property value (as returned by get_page)."""
    if not isinstance(prop, dict):
        return None
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "select":
        return (prop.get("select") or {}).get("name")
    if ptype == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", [])]
    if ptype == "checkbox":
        return bool(prop.get("checkbox"))
    return None


def _read_shortlist_fields(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get("properties") or {}

    def get(name: str) -> Any:
        return _flatten_prop(props.get(name))

    return {
        "resultado_revision": get("Resultado revisión"),
        "motivo_descarte": get("motivo_descarte"),
        "ejemplo_negativo": bool(get("ejemplo_negativo")),
        "error_kind": get("error_kind") or [],
    }


def handle_editorial_capture_negative_example(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capture the negative-example metadata for one Descartar'd Shortlist row (P2.5).

    Input:
        shortlist_page_id (str, required): Notion page id (or URL) of the
            Shortlist row to evaluate.
        dry_run (bool, optional): if True, verify eligibility and return what
            would be written, without calling Notion to write anything.

    Returns:
        Every branch: {"ok": bool, "shortlist_page_id": str, "dry_run": bool}.
        Error branches (``ok`` False) add ``"error": str``; some also add
        context fields (e.g. ``resultado_revision``) but never fabricate the
        success-only fields below before they're actually known.
        Success branches (``ok`` True) add ``"error": None`` plus
        ``"captured": bool, "already_captured": bool,
        "motivo_descarte": str, "error_kind": list[str]``.
    """
    dry_run = bool(input_data.get("dry_run", False))
    shortlist_page_id = (input_data.get("shortlist_page_id") or "").strip()
    if not shortlist_page_id:
        return {
            "ok": False,
            "error": "'shortlist_page_id' is required",
            "shortlist_page_id": shortlist_page_id,
            "dry_run": dry_run,
        }

    try:
        page = notion_client.get_page(shortlist_page_id)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to read shortlist page: {e}",
            "shortlist_page_id": shortlist_page_id,
            "dry_run": dry_run,
        }

    fields = _read_shortlist_fields(page)

    if fields["resultado_revision"] != _DISCARDED_VALUE:
        return {
            "ok": False,
            "error": "not_discarded",
            "resultado_revision": fields["resultado_revision"],
            "shortlist_page_id": shortlist_page_id,
            "dry_run": dry_run,
        }

    if fields["ejemplo_negativo"]:
        return {
            "ok": True,
            "error": None,
            "dry_run": dry_run,
            "captured": False,
            "already_captured": True,
            "motivo_descarte": fields["motivo_descarte"],
            "error_kind": fields["error_kind"],
            "shortlist_page_id": shortlist_page_id,
        }

    motivo_descarte = (fields["motivo_descarte"] or "").strip()
    if not motivo_descarte:
        return {
            "ok": False,
            "error": "motivo_descarte_missing",
            "shortlist_page_id": shortlist_page_id,
            "dry_run": dry_run,
        }

    if dry_run:
        return {
            "ok": True,
            "error": None,
            "dry_run": True,
            "would_capture": True,
            "captured": False,
            "already_captured": False,
            "motivo_descarte": motivo_descarte,
            "error_kind": fields["error_kind"],
            "shortlist_page_id": shortlist_page_id,
        }

    try:
        notion_client.update_page_properties(
            page_id_or_url=shortlist_page_id,
            properties={"ejemplo_negativo": {"checkbox": True}},
        )
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "shortlist_page_id": shortlist_page_id,
            "dry_run": False,
        }

    return {
        "ok": True,
        "error": None,
        "dry_run": False,
        "captured": True,
        "already_captured": False,
        "motivo_descarte": motivo_descarte,
        "error_kind": fields["error_kind"],
        "shortlist_page_id": shortlist_page_id,
    }
