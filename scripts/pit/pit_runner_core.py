#!/usr/bin/env python3
"""PIT-2 runner core — orquestación ejecutable del torneo PIT sobre el pit-vault.

Capa repo-side (PIT-2, docs/ops/pit-2-runner-protocol.md): preflight, init de
lane, cierre de iteración y announce de lane, SIN spawn OpenClaw (eso es
PIT-2b). La consumen:

- ``worker/tasks/pit_runner.py`` — tasks Worker ``pit.*``.
- ``scripts/pit/pit_dry_run.py`` — smoke local de torneo completo
  (``pit_tournament_dry_run.sh``).

Contratos sobre los que opera (no los redefine):

- entrada: ``docs/schemas/pit-spec-v1.schema.json`` vía
  ``scripts/pit/pit_spec_validate.py``;
- salida por iteración: ``kpi-pack.schema.json`` (pit-vault templates);
- tablero: 9 columnas canónicas de ``docs/ops/pit-kanban-kpi-protocol.md``;
- write scope: SOLO ``pit/<pit_id>/lanes/<lane_id>/``
  (``docs/ops/pit-vault-layout.md``).

El protocolo D3 (``tournament_lane.*``, docs/79) queda intacto: PIT es el modo
hermano product.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.pit.pit_spec_validate import (
        RESEARCH_PROFILES,
        compute_fulfillment,
        validate_file,
    )
    from scripts.pit.pit_vault_check import check_pit_vault
except ImportError:  # invocado como script directo (python scripts/pit/pit_runner_core.py)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.pit.pit_spec_validate import (
        RESEARCH_PROFILES,
        compute_fulfillment,
        validate_file,
    )
    from scripts.pit.pit_vault_check import check_pit_vault

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "openclaw" / "workspace-templates" / "pit-vault" / "templates"
KANBAN_TEMPLATE_NAME = "kanban-lane.md"
KPI_PACK_SCHEMA_NAME = "kpi-pack.schema.json"

# Mismos patrones que pit-spec-v1.schema.json / kpi-pack.schema.json. Excluyen
# "/", "\\" y ".", así que también funcionan como guard anti path-traversal.
PIT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
LANE_ID_RE = re.compile(r"^lane-[a-z0-9][a-z0-9-]{1,63}$")
KPI_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")

# 9 columnas canónicas — títulos exactos (docs/ops/pit-kanban-kpi-protocol.md §1).
KANBAN_COLUMNS = (
    "Backlog",
    "Research",
    "Hypothesis",
    "Prototype",
    "KPI Track",
    "Fulfillment",
    "Review",
    "Done",
    "Stuck",
)

# Budget kill switch — stub PIT-2: budget_usd del spec actúa como estimación
# tope (max cost estimate) y se loguea en preflight/dry-run. El corte duro al
# alcanzar el 100 % del budget queda documentado aquí y su enforcement real es
# PIT-3 (docs/ops/pit-2-runner-protocol.md §Budget).
BUDGET_KILL_SWITCH = {
    "threshold_pct": 100,
    "enforced": False,
    "enforcement_milestone": "PIT-3",
}

PREFLIGHT_PASS = "PIT_PREFLIGHT_PASS"
PREFLIGHT_FAIL = "PIT_PREFLIGHT_FAIL"


def _validate_pit_id(pit_id: Any) -> str:
    value = (pit_id or "").strip() if isinstance(pit_id, str) else ""
    if not value or not PIT_ID_RE.fullmatch(value):
        raise ValueError(
            f"pit_id must match {PIT_ID_RE.pattern} (got {pit_id!r})"
        )
    return value


def _validate_lane_id(lane_id: Any) -> str:
    value = (lane_id or "").strip() if isinstance(lane_id, str) else ""
    if not value or not LANE_ID_RE.fullmatch(value):
        raise ValueError(
            f"lane_id must match {LANE_ID_RE.pattern} (got {lane_id!r})"
        )
    return value


def _validate_iteration(iteration: Any) -> int:
    if isinstance(iteration, bool) or not isinstance(iteration, int):
        raise ValueError(f"iteration must be an integer 1-10 (got {iteration!r})")
    if not 1 <= iteration <= 10:
        # kpi-pack.schema.json es 1-based (iteration >= 1); no existe iteración 0.
        raise ValueError(f"iteration must be between 1 and 10 (got {iteration})")
    return iteration


def _resolve_vault(vault_path: Any) -> Path:
    raw = (vault_path or "").strip() if isinstance(vault_path, str) else str(vault_path or "")
    if not raw:
        raise ValueError("vault_path is required")
    vault = Path(raw).expanduser().resolve()
    if not vault.is_dir():
        raise ValueError(f"vault_path is not a directory: {vault}")
    return vault


def _lane_root(vault: Path, pit_id: str, lane_id: str) -> Path:
    # Único subárbol writable por una lane (docs/ops/pit-vault-layout.md §3).
    return vault / "pit" / pit_id / "lanes" / lane_id


def _kpi_pack_rel(pit_id: str, lane_id: str, iteration: int) -> str:
    return f"pit/{pit_id}/lanes/{lane_id}/iterations/{iteration}/kpi_pack.json"


def _find_template(vault: Path, name: str) -> Path | None:
    """Plantilla del vault primero (sync de pit_vault_init.sh), repo como fallback."""
    vault_copy = vault / "templates" / name
    if vault_copy.is_file():
        return vault_copy
    repo_copy = TEMPLATES_DIR / name
    if repo_copy.is_file():
        return repo_copy
    return None


# ---------------------------------------------------------------------------
# pit.preflight
# ---------------------------------------------------------------------------


def preflight(
    spec_path: str | Path,
    vault_path: str | Path,
    *,
    require_write_scope: bool = False,
) -> dict[str, Any]:
    """Valida pit_spec + vault + budget antes de cualquier orquestación.

    Equivalente product del ``tournament_lane.preflight`` de D3: sin veredicto
    PASS no hay lanes. No escribe nada.
    """
    spec_result = validate_file(Path(spec_path))
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
        spec_summary = spec_result["spec"]
        budget = {
            "budget_usd": spec_summary["budget_usd"],
            "budget_per_lane_usd": spec_summary["budget_per_lane_usd"],
            # Stub PIT-2: el budget completo es la estimación tope de costo.
            "max_cost_estimate_usd": spec_summary["budget_usd"],
            "kill_switch": dict(BUDGET_KILL_SWITCH),
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
# pit.lane_init
# ---------------------------------------------------------------------------


def lane_init(
    vault_path: str | Path,
    pit_id: str,
    lane_id: str,
    *,
    research_profile: str = "mixed",
) -> dict[str, Any]:
    """Crea el workspace de una lane: kanban/board.md + iterations/1/.

    El kpi-pack es 1-based (``iteration >= 1``), así que la primera carpeta de
    trabajo pre-creada es ``iterations/1/``. Idempotente: un board existente
    nunca se sobreescribe.
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    lane_id = _validate_lane_id(lane_id)
    profile = (research_profile or "mixed").strip()
    if profile not in RESEARCH_PROFILES:
        raise ValueError(
            f"research_profile must be one of {RESEARCH_PROFILES} (got {research_profile!r})"
        )

    template_path = _find_template(vault, KANBAN_TEMPLATE_NAME)
    if template_path is None:
        raise ValueError(
            f"kanban template '{KANBAN_TEMPLATE_NAME}' not found in vault templates/ nor repo"
        )

    lane_root = _lane_root(vault, pit_id, lane_id)
    board_path = lane_root / "kanban" / "board.md"
    first_iteration_dir = lane_root / "iterations" / "1"

    board_created = False
    if not board_path.exists():
        board_path.parent.mkdir(parents=True, exist_ok=True)
        board = (
            template_path.read_text(encoding="utf-8")
            .replace("{{pit_id}}", pit_id)
            .replace("{{lane_id}}", lane_id)
            .replace("{{research_profile}}", profile)
        )
        board_path.write_text(board, encoding="utf-8")
        board_created = True
    first_iteration_dir.mkdir(parents=True, exist_ok=True)

    return {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "lane_root": str(lane_root),
        "board_path": str(board_path),
        "board_created": board_created,
        "board_template": str(template_path),
        "first_iteration_dir": str(first_iteration_dir),
        "research_profile": profile,
    }


# ---------------------------------------------------------------------------
# pit.iteration_close
# ---------------------------------------------------------------------------


def _normalize_hypothesis(hypothesis: Any) -> dict[str, Any]:
    if not isinstance(hypothesis, dict):
        raise ValueError("hypothesis must be an object with variable/statement/kpi_id")
    normalized: dict[str, Any] = {}
    for key in ("variable", "statement", "kpi_id"):
        value = (hypothesis.get(key) or "").strip() if isinstance(hypothesis.get(key), str) else ""
        if not value:
            raise ValueError(f"hypothesis.{key} is required and must be a non-empty string")
        normalized[key] = value
    if not KPI_ID_RE.fullmatch(normalized["kpi_id"]):
        raise ValueError(f"hypothesis.kpi_id must match {KPI_ID_RE.pattern}")
    validated = hypothesis.get("validated", None)
    if validated not in (True, False, None):
        raise ValueError("hypothesis.validated must be true, false, or null")
    normalized["validated"] = validated
    return normalized


def _normalize_kpis(kpis: Any) -> list[dict[str, Any]]:
    if not isinstance(kpis, list) or not kpis:
        raise ValueError("kpis must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    for index, kpi in enumerate(kpis):
        if not isinstance(kpi, dict):
            raise ValueError(f"kpis[{index}] must be an object")
        kpi_id = (kpi.get("kpi_id") or "").strip() if isinstance(kpi.get("kpi_id"), str) else ""
        if not kpi_id or not KPI_ID_RE.fullmatch(kpi_id):
            raise ValueError(f"kpis[{index}].kpi_id must match {KPI_ID_RE.pattern}")
        unit = (kpi.get("unit") or "").strip() if isinstance(kpi.get("unit"), str) else ""
        if not unit:
            raise ValueError(f"kpis[{index}].unit is required")
        try:
            expected = float(kpi["kpi_expected"])
            achieved = float(kpi["kpi_achieved"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"kpis[{index}] requires numeric kpi_expected and kpi_achieved"
            ) from exc
        direction = kpi.get("direction", "increase")
        if direction not in ("increase", "decrease"):
            raise ValueError(f"kpis[{index}].direction must be increase|decrease")
        weight = float(kpi.get("weight", 1.0))
        if weight <= 0:
            raise ValueError(f"kpis[{index}].weight must be > 0")
        item: dict[str, Any] = {
            "kpi_id": kpi_id,
            "unit": unit,
            "kpi_expected": expected,
            "kpi_achieved": achieved,
            "direction": direction,
            "weight": weight,
            # Señales sintéticas SIEMPRE etiquetadas (decisión David #14).
            "synthetic": bool(kpi.get("synthetic", False)),
        }
        evidence_url = kpi.get("evidence_url")
        if evidence_url is not None:
            item["evidence_url"] = str(evidence_url)
        normalized.append(item)
    return normalized


def _validate_kpi_pack(pack: dict[str, Any], vault: Path) -> str:
    """Valida el kpi_pack: jsonschema si está disponible + checks duros siempre."""
    # Checks duros (espejo de los invariantes del schema que más importan).
    if pack["fulfillment_score"] < 0 or pack["fulfillment_score"] > 1:
        raise ValueError("fulfillment_score must be within [0, 1]")
    personas = pack.get("synthetic_personas")
    if personas is not None and personas.get("labeled") is not True:
        raise ValueError("synthetic_personas.labeled must be true (not configurable)")
    if pack["kanban_column"] not in KANBAN_COLUMNS:
        raise ValueError(f"kanban_column must be one of {KANBAN_COLUMNS}")

    schema_path = _find_template(vault, KPI_PACK_SCHEMA_NAME)
    try:
        import jsonschema
    except ImportError:
        return "builtin-only"
    if schema_path is None:
        return "builtin-only"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=pack, schema=schema)
    return "jsonschema"


def _kanban_insert_card(board_path: Path, column: str, card: str) -> None:
    """Inserta una tarjeta al final de la columna `## <column>` del board."""
    if not board_path.is_file():
        raise ValueError(
            f"kanban board not found ({board_path}); run pit.lane_init first"
        )
    lines = board_path.read_text(encoding="utf-8").splitlines()
    heading = f"## {column}"
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise ValueError(
            f"column '{column}' not found in board (expected canonical 9-column kanban)"
        ) from None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    insert_at = end
    while insert_at - 1 > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, card)
    board_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def iteration_close(
    vault_path: str | Path,
    pit_id: str,
    lane_id: str,
    iteration: int,
    hypothesis: dict[str, Any],
    kpis: list[dict[str, Any]],
    *,
    prototype_url: str | None = None,
    kanban_column: str = "Fulfillment",
    synthetic_personas: dict[str, Any] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Cierra una iteración: escribe el kpi_pack.json y actualiza el kanban.

    El fulfillment_score se calcula SIEMPRE con ``compute_fulfillment`` (nunca
    viene del caller), y la tarjeta agregada al tablero lleva hipótesis, KPI y
    fulfillment de la iteración.
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    lane_id = _validate_lane_id(lane_id)
    iteration = _validate_iteration(iteration)
    hypothesis_n = _normalize_hypothesis(hypothesis)
    kpis_n = _normalize_kpis(kpis)

    kpi_ids = {kpi["kpi_id"] for kpi in kpis_n}
    if hypothesis_n["kpi_id"] not in kpi_ids:
        raise ValueError(
            f"hypothesis.kpi_id '{hypothesis_n['kpi_id']}' not present in kpis "
            f"(got {sorted(kpi_ids)})"
        )
    if kanban_column not in KANBAN_COLUMNS:
        raise ValueError(f"kanban_column must be one of {KANBAN_COLUMNS}")

    fulfillment = compute_fulfillment(kpis_n)

    pack: dict[str, Any] = {
        "schema_version": 1,
        "pit_id": pit_id,
        "lane_id": lane_id,
        "iteration": iteration,
        "hypothesis": hypothesis_n,
        "kpis": kpis_n,
        "fulfillment_score": fulfillment,
        "prototype_url": (prototype_url or "").strip() or None,
        "kanban_column": kanban_column,
        "notes": notes,
    }
    if synthetic_personas is not None:
        pack["synthetic_personas"] = {
            "used": bool(synthetic_personas.get("used", True)),
            "labeled": True,
            "count": int(synthetic_personas.get("count", 0)),
        }
    elif any(kpi["synthetic"] for kpi in kpis_n):
        pack["synthetic_personas"] = {"used": True, "labeled": True, "count": 0}

    schema_validation = _validate_kpi_pack(pack, vault)

    lane_root = _lane_root(vault, pit_id, lane_id)
    pack_path = lane_root / "iterations" / str(iteration) / "kpi_pack.json"
    existed = pack_path.exists()
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    card = (
        f"- [x] iter-{iteration} · {hypothesis_n['variable']} → "
        f"{hypothesis_n['kpi_id']} · fulfillment {fulfillment:.2f} #iter{iteration}"
    )
    _kanban_insert_card(lane_root / "kanban" / "board.md", kanban_column, card)

    return {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "iteration": iteration,
        "kpi_pack_path": str(pack_path),
        "kpi_pack_rel": _kpi_pack_rel(pit_id, lane_id, iteration),
        "fulfillment_score": fulfillment,
        "kanban_column": kanban_column,
        "kanban_card": card,
        "schema_validation": schema_validation,
        "overwrote_existing_pack": existed,
    }


# ---------------------------------------------------------------------------
# pit.lane_announce
# ---------------------------------------------------------------------------


def lane_announce(
    vault_path: str | Path,
    pit_id: str,
    lane_id: str,
    *,
    iteration: int | None = None,
    prototype_url: str | None = None,
) -> dict[str, Any]:
    """Emite el cierre verificable de la lane (3 líneas literales).

    Regla de verdad (SKILL §Cierre, paralela a docs/79 §4.1): la lane está
    completa solo si hay PROTOTYPE_URL y el fulfillment del kpi_pack es
    reproducible con ``compute_fulfillment``. ``finalStatus=success`` sin esas
    líneas verificables ⇒ ``lane_incomplete``.
    """
    vault = _resolve_vault(str(vault_path))
    pit_id = _validate_pit_id(pit_id)
    lane_id = _validate_lane_id(lane_id)

    iterations_dir = _lane_root(vault, pit_id, lane_id) / "iterations"
    if iteration is None:
        candidates = sorted(
            int(path.name)
            for path in iterations_dir.glob("*")
            if path.name.isdigit() and (path / "kpi_pack.json").is_file()
        ) if iterations_dir.is_dir() else []
        if not candidates:
            raise ValueError(
                f"no iterations with kpi_pack.json found under {iterations_dir}"
            )
        iteration = candidates[-1]
    else:
        iteration = _validate_iteration(iteration)

    pack_path = iterations_dir / str(iteration) / "kpi_pack.json"
    if not pack_path.is_file():
        raise ValueError(f"kpi_pack.json not found for iteration {iteration}: {pack_path}")
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    stored = pack.get("fulfillment_score")
    incomplete_reasons: list[str] = []
    try:
        recomputed = compute_fulfillment(pack["kpis"])
        reproducible = recomputed == stored
        if not reproducible:
            incomplete_reasons.append(
                f"fulfillment_score not reproducible (stored {stored}, computed {recomputed})"
            )
    except (KeyError, TypeError, ValueError) as exc:
        reproducible = False
        incomplete_reasons.append(f"kpi_pack kpis not computable: {exc}")

    url = (prototype_url or pack.get("prototype_url") or "").strip() or None
    if not url:
        incomplete_reasons.append("missing PROTOTYPE_URL (tunnel + Mission Control)")

    kpi_pack_rel = _kpi_pack_rel(pit_id, lane_id, iteration)
    announce = "\n".join(
        [
            f"PROTOTYPE_URL={url or ''}",
            f"KPI_PACK={kpi_pack_rel}",
            f"FULFILLMENT={stored}",
        ]
    )

    return {
        "pit_id": pit_id,
        "lane_id": lane_id,
        "iteration": iteration,
        "prototype_url": url,
        "kpi_pack": kpi_pack_rel,
        "kpi_pack_path": str(pack_path),
        "fulfillment": stored,
        "reproducible": reproducible,
        "lane_complete": bool(url) and reproducible,
        "incomplete_reasons": incomplete_reasons,
        "announce": announce,
    }
