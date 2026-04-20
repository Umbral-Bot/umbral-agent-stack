#!/usr/bin/env python3
"""Emit a ``notion.operation_trace`` breadcrumb into ``ops_log.jsonl``.

Uso previsto:
    Cuando alguien (David, Copilot, Claude, un script manual, o un
    ``curl`` directo a la Notion API) regulariza Notion por fuera del
    pipeline del Worker — por ejemplo corrigiendo a mano una
    capitalizacion rota como la de la reunion Granola "Comgrap Dynamo" —
    este CLI deja una traza central auditable en ``ops_log.jsonl``.

El script **no hace llamadas a Notion**: solo escribe el evento local.
No requiere ``NOTION_API_KEY``; tampoco toca ninguna pagina ni comentario.
Es responsabilidad del caller ejecutar (o haber ejecutado) las
operaciones reales contra Notion; este CLI solo captura el "que / quien
/ por que / sobre que paginas / cuantas lecturas y escrituras".

Ejemplo (caso Comgrap Dynamo) ::

    python scripts/notion_trace_operation.py \\
        --actor copilot \\
        --action regularize_granola_capitalization \\
        --reason task_only_capitalization_corrected_to_project_task \\
        --raw-page-id 3485f443-fb5c-81e9-ae88-fe2fb7cd7b54 \\
        --target-page-id df938460-fdee-4752-b9d4-293bede5e541 \\
        --target-page-id 3485f443-fb5c-8198-9f54-fc5882302bf2 \\
        --notion-reads 3 \\
        --notion-writes 5 \\
        --source vps_curl \\
        --source-kind manual_regularization \\
        --status ok \\
        --details "created project, linked raw and task, added cross comments"

Dry-run (no escribe en ops_log, solo imprime el evento que se escribiria)::

    python scripts/notion_trace_operation.py --dry-run \\
        --actor david --action regularize_granola_capitalization \\
        --reason example
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Emit a notion.operation_trace breadcrumb into ops_log.jsonl. "
            "Does NOT call Notion."
        )
    )
    p.add_argument("--actor", required=True, help="Quien ejecuto la operacion (david, copilot, claude, rick, ...).")
    p.add_argument("--action", required=True, help="Accion logica (ej. regularize_granola_capitalization).")
    p.add_argument("--reason", required=True, help="Motivo corto y estructurado (ej. task_only_capitalization_corrected_to_project_task).")
    p.add_argument("--raw-page-id", default=None, help="ID / URL de la pagina raw origen si aplica.")
    p.add_argument(
        "--target-page-id",
        action="append",
        default=[],
        help="ID / URL de pagina afectada. Repetible. Maximo 25 entradas.",
    )
    p.add_argument("--source", default=None, help="Origen de la operacion (ej. vps_curl, copilot_script, cursor_agent).")
    p.add_argument("--source-kind", default=None, help="Subtipo (ej. manual_regularization, cli, curl).")
    p.add_argument("--notion-reads", type=int, default=None, help="Cantidad aprox. de reads a Notion realizados.")
    p.add_argument("--notion-writes", type=int, default=None, help="Cantidad aprox. de writes a Notion realizados.")
    p.add_argument("--status", default="ok", help="Estado final (ok, partial, failed, rolled_back).")
    p.add_argument("--details", default=None, help="Descripcion breve. Se trunca a 500 chars. NO incluir transcript, prompts, ni contenido de paginas.")
    p.add_argument("--operation-id", default=None, help="Opcional. Si no se pasa, se genera un UUID4 estable para la corrida.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe en ops_log.jsonl. Solo imprime el evento que se escribiria.",
    )
    p.add_argument(
        "--log-dir",
        default=None,
        help="Directorio alternativo para ops_log.jsonl (default: UMBRAL_OPS_LOG_DIR o ~/.config/umbral).",
    )
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Imprimir el output como JSON (default).",
    )
    return p


def run(args: argparse.Namespace) -> Dict[str, Any]:
    # Deferred import: permite que ``--help`` no pague costo de importar
    # el paquete ``infra`` si el caller solo quiere la ayuda.
    from infra.ops_logger import OpsLogger

    log_dir = Path(args.log_dir).expanduser() if args.log_dir else None
    logger = OpsLogger(log_dir=log_dir)
    ev = logger.notion_operation(
        actor=args.actor,
        action=args.action,
        reason=args.reason,
        raw_page_id=args.raw_page_id,
        target_page_ids=args.target_page_id,
        source=args.source,
        source_kind=args.source_kind,
        notion_reads=args.notion_reads,
        notion_writes=args.notion_writes,
        status=args.status,
        details=args.details,
        operation_id=args.operation_id,
        dry_run=args.dry_run,
    )
    ev = dict(ev)
    if not args.dry_run:
        ev["ops_log_path"] = str(logger.path)
    return ev


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # pragma: no cover - defensive
        print(json.dumps({"error": str(exc), "status": "failed"}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
