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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a PIT spec v1 YAML/JSON file.")
    parser.add_argument("spec_path", type=Path, help="Path to pit_spec YAML/JSON.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    result = validate_file(args.spec_path)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(format_markdown(result), end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
