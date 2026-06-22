#!/usr/bin/env python3
"""PIT spec v1 — modelos pydantic + validador CLI.

Fuente ejecutable del contrato documentado en
``docs/schemas/pit-spec-v1.schema.json``. Un pit_spec describe un torneo de
producto (modo ``product``: PROTOTYPE_URL + KPI), a diferencia del modo D3
``code`` (PR_URL, ver docs/79-tournament-protocol-openclaw-native.md).

Reglas no negociables (decisiones David 2026-06-09):

- ``budget_usd`` SIEMPRE viene del input de David — sin default silencioso.
- ``iteration_count`` variable 2-10, también desde input David.
- Visual Magnific default ``aspect_ratio: "4:3"`` (canónico Umbral).
- Personas sintéticas permitidas pero SIEMPRE etiquetadas.
- Preview por túnel + Mission Control, nunca URL pública.

Uso CLI::

    python scripts/pit/pit_spec_validate.py examples/pit-salud-mental-pilot.yaml
    python scripts/pit/pit_spec_validate.py <spec.yaml> --format json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "schemas" / "pit-spec-v1.schema.json"

PROTOTYPE_OUTPUTS = ("html", "figma", "both")
RESEARCH_PROFILES = ("academic", "market_pain", "competitive", "mixed")
PIT_ASPECT_RATIOS = ("4:3", "16:9", "9:16", "4:5", "1:1")
PIT_DEFAULT_ASPECT_RATIO = "4:3"
PREVIEW_MODE = "tunnel+mission-control"
PIT_VAULT_NAME = "umbral-pit-vault"

# ---------------------------------------------------------------------------
# PIT spec v2 — broker-only contract (P5)
# ---------------------------------------------------------------------------
# A v2 spec describes a *code / repo-analysis* tournament whose lanes are
# dispatched through the Worker task ``copilot_cli.run`` (P4 broker contract,
# docs/ops/pit-p4-broker-contract-20260621.md). It is a different shape from the
# v1 product spec above and is detected by ``schema_version: 2`` or the presence
# of a ``broker_contract`` block.

TOOL_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "tool_policy.yaml"

# Mirror worker.tasks.copilot_cli._PIT_METADATA_VALUE_RE so the spec validator
# and the runtime broker agree on the id grammar.
PIT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# reasoning_effort the broker understands: CLI choices low|medium|high|xhigh plus
# the display alias ``max`` (normalized to xhigh by copilot_cli at run time).
BROKER_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")

BROKER_REQUIRED_TASK = "copilot_cli.run"
BROKER_SECRET_DENY_REQUIRED = "WORKER_TOKEN"

# secrets_scope holds logical names only — never values. Enforce an env-var-like
# grammar so a literal secret cannot be smuggled into the spec.
LOGICAL_SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def load_policy_models() -> tuple[list[str], dict[str, str]]:
    """Return ``(allowed_models, model_aliases)`` from the Copilot CLI policy.

    The single source of truth is ``worker.tool_policy``; if that import is not
    available (standalone use of this script) fall back to reading
    ``config/tool_policy.yaml`` directly. Empty collections are returned only
    when the policy is unreadable, in which case model validation degrades to a
    no-op rather than failing closed.
    """
    try:
        from worker import tool_policy as _tp

        allowed = list(_tp.get_copilot_cli_allowed_models())
        aliases = dict(_tp.get_copilot_cli_model_aliases())
        if allowed:
            return allowed, aliases
    except Exception:  # pragma: no cover - fallback path
        pass
    try:
        data = yaml.safe_load(TOOL_POLICY_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):  # pragma: no cover - fallback path
        return [], {}
    section = data.get("copilot_cli", {}) if isinstance(data, dict) else {}
    allowed = list(section.get("allowed_models", []) or [])
    aliases = dict(section.get("model_aliases", {}) or {})
    return allowed, aliases


class KpiDefinition(BaseModel):
    """Un KPI del torneo; unidad variable, objetivo + dirección + peso."""

    kpi_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    kpi_expected: float
    direction: Literal["increase", "decrease"] = "increase"
    weight: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def _expected_positive_for_increase(self) -> "KpiDefinition":
        if self.direction == "increase" and self.kpi_expected <= 0:
            raise ValueError(
                f"kpi '{self.kpi_id}': kpi_expected must be > 0 when direction=increase"
            )
        if self.direction == "decrease" and self.kpi_expected < 0:
            raise ValueError(
                f"kpi '{self.kpi_id}': kpi_expected must be >= 0 when direction=decrease"
            )
        return self


class VisualGeneration(BaseModel):
    """Generación visual Magnific (gate + broker en docs/ops/pit-visual-magnific.md)."""

    enabled: bool = False
    provider: Literal["magnific"] = "magnific"
    aspect_ratio: Literal["4:3", "16:9", "9:16", "4:5", "1:1"] = PIT_DEFAULT_ASPECT_RATIO
    style_ref: str | None = None


class SyntheticPersonas(BaseModel):
    """Personas sintéticas: permitidas, SIEMPRE etiquetadas (labeled no es opt-out)."""

    enabled: bool = False
    labeled: Literal[True] = True


class PitSpec(BaseModel):
    """Contrato pit_spec v1 (modo product)."""

    schema_version: Literal[1] = 1
    pit_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    mode: Literal["product"] = "product"
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    lane_count: int = Field(..., ge=2, le=5)
    iteration_count: int = Field(..., ge=2, le=10)
    budget_usd: float = Field(..., gt=0)
    prototype_output: Literal["html", "figma", "both"] = "html"
    research_profile: Literal["academic", "market_pain", "competitive", "mixed"] = "mixed"
    kpi_definitions: list[KpiDefinition] = Field(..., min_length=1)
    hypothesis_seed: str | None = None
    visual_generation: VisualGeneration = Field(default_factory=VisualGeneration)
    synthetic_personas: SyntheticPersonas = Field(default_factory=SyntheticPersonas)
    preview_mode: Literal["tunnel+mission-control"] = PREVIEW_MODE
    vault: Literal["umbral-pit-vault"] = PIT_VAULT_NAME
    template_name: str | None = None
    notes: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("kpi_definitions")
    @classmethod
    def _unique_kpi_ids(cls, v: list[KpiDefinition]) -> list[KpiDefinition]:
        seen: set[str] = set()
        for kpi in v:
            if kpi.kpi_id in seen:
                raise ValueError(f"duplicate kpi_id: {kpi.kpi_id}")
            seen.add(kpi.kpi_id)
        return v

    @property
    def budget_per_lane_usd(self) -> float:
        return self.budget_usd / self.lane_count


def compute_fulfillment(kpis: list[dict[str, Any]]) -> float:
    """fulfillment_score 0-1 según docs/ops/pit-kanban-kpi-protocol.md.

    Cada item necesita ``kpi_expected``, ``kpi_achieved`` y opcionalmente
    ``direction`` (default increase) y ``weight`` (default 1.0).

    - increase: score_i = clamp01(achieved / expected), expected > 0.
    - decrease: score_i = 1.0 si achieved <= expected; si no,
      score_i = clamp01(expected / achieved).
    - fulfillment = sum(w_i * score_i) / sum(w_i), redondeado a 2 decimales.
    """
    if not kpis:
        raise ValueError("compute_fulfillment requires at least one KPI")
    total_weight = 0.0
    weighted = 0.0
    for kpi in kpis:
        expected = float(kpi["kpi_expected"])
        achieved = float(kpi["kpi_achieved"])
        direction = kpi.get("direction", "increase")
        weight = float(kpi.get("weight", 1.0))
        if weight <= 0:
            raise ValueError("kpi weight must be > 0")
        if direction == "increase":
            if expected <= 0:
                raise ValueError("kpi_expected must be > 0 for direction=increase")
            score = max(0.0, min(1.0, achieved / expected))
        elif direction == "decrease":
            if achieved <= expected:
                score = 1.0
            else:
                score = max(0.0, min(1.0, expected / achieved))
        else:
            raise ValueError(f"unknown direction: {direction}")
        total_weight += weight
        weighted += weight * score
    return round(weighted / total_weight, 2)


def load_spec(path: Path) -> PitSpec:
    """Carga YAML/JSON y valida; levanta ValidationError/ValueError si inválido."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"spec root must be a mapping, got {type(raw).__name__}")
    return PitSpec.model_validate(raw)


def validate_file(path: Path) -> dict[str, Any]:
    """Valida un spec en disco y devuelve un resultado estilo obsidian_context_check."""
    errors: list[str] = []
    spec_summary: dict[str, Any] = {}
    try:
        spec = load_spec(path)
    except FileNotFoundError:
        errors.append(f"spec file not found: {path}")
    except (ValidationError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    else:
        spec_summary = {
            "pit_id": spec.pit_id,
            "mode": spec.mode,
            "lane_count": spec.lane_count,
            "iteration_count": spec.iteration_count,
            "budget_usd": spec.budget_usd,
            "budget_per_lane_usd": round(spec.budget_per_lane_usd, 2),
            "prototype_output": spec.prototype_output,
            "research_profile": spec.research_profile,
            "kpi_ids": [k.kpi_id for k in spec.kpi_definitions],
            "visual_aspect_ratio": spec.visual_generation.aspect_ratio,
            "preview_mode": spec.preview_mode,
        }
    return {
        "spec_path": str(path),
        "status": "fail" if errors else "pass",
        "errors": errors,
        "spec": spec_summary,
        "schema": str(SCHEMA_PATH),
    }


def format_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# PIT Spec Validate",
        "",
        f"- Status: `{result['status']}`",
        f"- Spec: `{result['spec_path']}`",
    ]
    if result["spec"]:
        spec = result["spec"]
        lines.extend(
            [
                f"- pit_id: `{spec['pit_id']}` | lanes: `{spec['lane_count']}` | "
                f"iteraciones: `{spec['iteration_count']}`",
                f"- budget: `{spec['budget_usd']}` USD "
                f"(`{spec['budget_per_lane_usd']}` por lane)",
                f"- prototipo: `{spec['prototype_output']}` | research: `{spec['research_profile']}`",
                f"- visual: `{spec['visual_aspect_ratio']}` | preview: `{spec['preview_mode']}`",
                f"- KPIs: {', '.join(f'`{k}`' for k in spec['kpi_ids'])}",
            ]
        )
    if result["errors"]:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# PIT spec v2 — broker-only models + validation (P5)
# ---------------------------------------------------------------------------


class BrokerLane(BaseModel):
    """One tournament lane dispatched through ``copilot_cli.run``."""

    lane_id: str
    model: str
    reasoning_effort: str
    mission: str = Field(..., min_length=1)
    max_iterations: int = Field(..., ge=1, le=999)

    model_config = {"extra": "forbid"}

    @field_validator("lane_id")
    @classmethod
    def _lane_id_format(cls, v: str) -> str:
        if not PIT_ID_RE.match(v):
            raise ValueError(
                f"invalid_lane_id:{v!r} (must match ^[A-Za-z0-9._-]{{1,64}}$)"
            )
        return v

    @field_validator("reasoning_effort")
    @classmethod
    def _reasoning_effort_allowed(cls, v: str) -> str:
        if v not in BROKER_REASONING_EFFORTS:
            raise ValueError(
                f"invalid_reasoning_effort:{v!r} "
                f"(allowed: {', '.join(BROKER_REASONING_EFFORTS)})"
            )
        return v

    @field_validator("model")
    @classmethod
    def _model_allowed(cls, v: str, info) -> str:
        ctx = info.context or {}
        allowed = ctx.get("allowed_models") or []
        aliases = ctx.get("model_aliases") or {}
        if not allowed:
            # Policy unavailable: cannot validate the model, do not fail closed.
            return v
        if v in allowed:
            return v
        if v in aliases and aliases[v] in allowed:
            return v
        raise ValueError(
            f"invalid_model:{v!r} "
            "(not in allowed_models nor resolvable via model_aliases)"
        )


class SecretsScope(BaseModel):
    """Logical secret names a lane may/may not reference — never values."""

    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("allow", "deny")
    @classmethod
    def _logical_names_only(cls, v: list[str], info) -> list[str]:
        for name in v:
            if not LOGICAL_SECRET_NAME_RE.match(name):
                raise ValueError(
                    f"secrets_scope.{info.field_name}: {name!r} must be a logical "
                    "name (UPPER_SNAKE), never a value"
                )
        return v

    @model_validator(mode="after")
    def _deny_has_worker_token(self) -> "SecretsScope":
        if BROKER_SECRET_DENY_REQUIRED not in self.deny:
            raise ValueError(
                f"secrets_scope.deny must contain {BROKER_SECRET_DENY_REQUIRED}"
            )
        return self


class BrokerContract(BaseModel):
    """The broker-only guarantee enforced for every code/repo-analysis lane."""

    required_task: str = BROKER_REQUIRED_TASK
    forbid_direct_llm_repo_analysis: bool

    model_config = {"extra": "forbid"}

    @field_validator("required_task")
    @classmethod
    def _required_task(cls, v: str) -> str:
        if v != BROKER_REQUIRED_TASK:
            raise ValueError(
                f"broker_contract.required_task must be {BROKER_REQUIRED_TASK!r}, got {v!r}"
            )
        return v

    @field_validator("forbid_direct_llm_repo_analysis")
    @classmethod
    def _forbid_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError(
                "broker_contract.forbid_direct_llm_repo_analysis must be true"
            )
        return v


class OpenClawOrchestration(BaseModel):
    """P10: how the runner spawns/collects the ephemeral OpenClaw lane agents.

    Optional block. When ``enabled`` is true the tournament runner takes the
    broker spawn path (ephemeral ``<pit_id>-lane-*`` agents each issue ONE
    ``copilot_cli.run``) instead of treating the spec as a plan-only artifact.
    """

    enabled: bool = False
    spawn_from: Literal["main_standalone"] = "main_standalone"
    collect_mode: Literal["broker_announce"] = "broker_announce"

    model_config = {"extra": "forbid"}


class PitSpecV2(BaseModel):
    """pit_spec v2 contract (code / broker-only mode)."""

    schema_version: Literal[2] = 2
    pit_id: str
    repo_path: str = Field(..., min_length=1)
    budget_usd_total: float = Field(..., gt=0)
    lanes: list[BrokerLane] = Field(..., min_length=1)
    secrets_scope: SecretsScope
    broker_contract: BrokerContract
    title: str | None = None
    notes: str | None = None
    openclaw_orchestration: OpenClawOrchestration | None = None

    model_config = {"extra": "forbid"}

    @field_validator("pit_id")
    @classmethod
    def _pit_id_format(cls, v: str) -> str:
        if not PIT_ID_RE.match(v):
            raise ValueError(
                f"invalid_pit_id:{v!r} (must match ^[A-Za-z0-9._-]{{1,64}}$)"
            )
        return v

    @field_validator("lanes")
    @classmethod
    def _unique_lane_ids(cls, v: list[BrokerLane]) -> list[BrokerLane]:
        seen: set[str] = set()
        for lane in v:
            if lane.lane_id in seen:
                raise ValueError(f"duplicate lane_id: {lane.lane_id}")
            seen.add(lane.lane_id)
        return v


def is_broker_spec(raw: dict[str, Any]) -> bool:
    """True when a raw mapping is a v2 broker spec (vs v1 product spec)."""
    return raw.get("schema_version") == 2 or "broker_contract" in raw


def load_broker_spec(path: Path) -> PitSpecV2:
    """Load + validate a v2 broker spec against the Copilot CLI policy."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"spec root must be a mapping, got {type(raw).__name__}")
    allowed, aliases = load_policy_models()
    return PitSpecV2.model_validate(
        raw, context={"allowed_models": allowed, "model_aliases": aliases}
    )


def _format_validation_errors(exc: ValidationError) -> list[str]:
    """Flatten a pydantic error into clear ``<loc>: <msg>`` strings."""
    out: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = str(err.get("msg", "")).replace("Value error, ", "")
        out.append(f"{loc}: {msg}" if loc else msg)
    return out


def validate_broker_file(path: Path) -> dict[str, Any]:
    """Validate a v2 broker spec; return a ``status``/``errors``/``spec`` dict."""
    errors: list[str] = []
    spec_summary: dict[str, Any] = {}
    try:
        spec = load_broker_spec(path)
    except FileNotFoundError:
        errors.append(f"spec file not found: {path}")
    except ValidationError as exc:
        errors.extend(_format_validation_errors(exc))
    except (ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    else:
        _, aliases = load_policy_models()
        spec_summary = {
            "schema_version": 2,
            "pit_id": spec.pit_id,
            "repo_path": spec.repo_path,
            "budget_usd_total": spec.budget_usd_total,
            "lane_count": len(spec.lanes),
            "lanes": [
                {
                    "lane_id": lane.lane_id,
                    "model": lane.model,
                    "model_slug": aliases.get(lane.model, lane.model),
                    "reasoning_effort": lane.reasoning_effort,
                    "mission": lane.mission,
                    "max_iterations": lane.max_iterations,
                }
                for lane in spec.lanes
            ],
            "broker_required_task": spec.broker_contract.required_task,
            "forbid_direct_llm_repo_analysis": spec.broker_contract.forbid_direct_llm_repo_analysis,
            "secrets_deny": spec.secrets_scope.deny,
            "openclaw_orchestration": (
                {
                    "enabled": spec.openclaw_orchestration.enabled,
                    "spawn_from": spec.openclaw_orchestration.spawn_from,
                    "collect_mode": spec.openclaw_orchestration.collect_mode,
                }
                if spec.openclaw_orchestration is not None
                else None
            ),
        }
    return {
        "spec_path": str(path),
        "schema_version": 2,
        "status": "fail" if errors else "pass",
        "errors": errors,
        "spec": spec_summary,
    }


def format_broker_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# PIT Spec Validate — v2 broker",
        "",
        f"- Status: `{result['status']}`",
        f"- Spec: `{result['spec_path']}`",
    ]
    if result["spec"]:
        spec = result["spec"]
        lines.extend(
            [
                f"- pit_id: `{spec['pit_id']}` | lanes: `{spec['lane_count']}` | "
                f"budget: `{spec['budget_usd_total']}` USD",
                f"- broker: `{spec['broker_required_task']}` | "
                f"forbid_direct_llm_repo_analysis: `{spec['forbid_direct_llm_repo_analysis']}`",
                f"- secrets_deny: {', '.join(f'`{s}`' for s in spec['secrets_deny'])}",
            ]
        )
        for lane in spec["lanes"]:
            lines.append(
                f"  - lane `{lane['lane_id']}`: model `{lane['model_slug']}` "
                f"(`{lane['reasoning_effort']}`) · mission `{lane['mission']}` · "
                f"max_iterations `{lane['max_iterations']}`"
            )
    if result["errors"]:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in result["errors"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a PIT spec (v1 product or v2 broker) YAML/JSON file."
    )
    parser.add_argument("spec_path", type=Path, help="Path to pit_spec YAML/JSON.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    try:
        raw = yaml.safe_load(args.spec_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raw = None

    if isinstance(raw, dict) and is_broker_spec(raw):
        result = validate_broker_file(args.spec_path)
        rendered = format_broker_markdown(result)
    else:
        result = validate_file(args.spec_path)
        rendered = format_markdown(result)

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
