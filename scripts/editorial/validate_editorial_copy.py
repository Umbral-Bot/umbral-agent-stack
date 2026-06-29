"""Validate editorial copy against benchmark + channel criteria."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BENCHMARK_PATH = _REPO_ROOT / "evals" / "editorial" / "benchmark-umbral-voice-v1.yaml"
_CHANNEL_PATH = _REPO_ROOT / "evals" / "editorial" / "channel-criteria-v1.yaml"


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise ValueError("Editorial validation failed:\n- " + "\n- ".join(self.errors))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _phrase_hits(text: str, phrases: list[str]) -> list[str]:
    lower = text.lower()
    hits = []
    for p in phrases:
        pl = p.lower()
        if pl in ("amplificar",):
            if re.search(r"amplific", lower):
                hits.append(p)
        elif pl in lower:
            hits.append(p)
    return hits


def validate_copy_text(
    text: str,
    *,
    channel: str = "linkedin",
    check_linkedin_no_question_opening: bool = False,
) -> ValidationResult:
    result = ValidationResult(ok=True)
    benchmark = _load_yaml(_BENCHMARK_PATH)["benchmark_editorial_umbral"]["umbral_de_paso"]
    channel_cfg = _load_yaml(_CHANNEL_PATH)

    literal_fails = [
        p for p in benchmark["fail_automatico_si_aparece"]
        if not p.startswith(("capturar", "impacto", "preparación", "equipos", "em dash", "apertura", "mini-ensayo", "pregunta", "riesgo", "transformación"))
    ]
    hits = _phrase_hits(text, literal_fails)
    if hits:
        result.ok = False
        result.errors.append(f"fail_automatico: {hits}")

    if "—" in text or "–" in text:
        result.ok = False
        result.errors.append("em dash en copy público")

    amp_count = len(re.findall(r"amplific", text.lower()))
    max_amp = benchmark.get("reglas_cuantitativas", {}).get("max_repeticion_verbo_riesgo", 2)
    if amp_count > max_amp:
        result.ok = False
        result.errors.append(f"amplificar/repetición {amp_count} > {max_amp}")

    cierre_canonico = "Primero claridad. Después velocidad."
    if channel in ("linkedin", "blog", "x") and cierre_canonico not in text:
        result.warnings.append("cierre canónico ausente o incompleto")

    if channel == "linkedin":
        lo, hi = channel_cfg["linkedin"]["longitud_objetivo_chars"]
        n = len(text.strip())
        if n < lo or n > hi + 200:
            result.warnings.append(f"LinkedIn longitud {n} fuera de objetivo [{lo},{hi}]")

        if check_linkedin_no_question_opening:
            first_line = text.strip().split("\n")[0].strip()
            if first_line.endswith("?"):
                result.ok = False
                result.errors.append("LinkedIn abre con pregunta; preferir afirmativa (ALT 1)")

    return result


def validate_publication_payload(payload: dict[str, Any]) -> ValidationResult:
    merged = ValidationResult(ok=True)
    tesis = payload.get("tesis_canonica", "")
    cierre = payload.get("cierre_canonico", "")

    for channel, key in (
        ("linkedin", "copy_linkedin"),
        ("blog", "copy_blog"),
        ("x", "copy_x"),
    ):
        copy = payload.get(key, "")
        if not copy:
            merged.ok = False
            merged.errors.append(f"missing {key}")
            continue
        r = validate_copy_text(
            copy,
            channel=channel,
            check_linkedin_no_question_opening=(channel == "linkedin"),
        )
        if not r.ok:
            merged.ok = False
        merged.errors.extend(f"{channel}: {e}" for e in r.errors)
        merged.warnings.extend(f"{channel}: {w}" for w in r.warnings)

    blog = payload.get("copy_blog", "")
    if tesis and "gobernanza" not in blog.lower() and "desorden" not in blog.lower():
        merged.warnings.append("blog: verificar tesis canónica explícita")

    for copy in (payload.get("copy_linkedin", ""), payload.get("copy_blog", ""), payload.get("copy_x", "")):
        if re.search(r"\d{2,}%|\d{4}|\bISO\b|\bestudio\b", copy, re.I):
            merged.warnings.append("posible dato/estudio no verificado en pieza de opinión")

    if cierre:
        for label, copy in (
            ("linkedin", payload.get("copy_linkedin", "")),
            ("blog", payload.get("copy_blog", "")),
            ("x", payload.get("copy_x", "")),
        ):
            if cierre not in copy:
                merged.warnings.append(f"{label}: cierre canónico no encontrado literal")

    return merged


def validate_publication_file(path: Path) -> ValidationResult:
    payload = _load_yaml(path)
    return validate_publication_payload(payload)
