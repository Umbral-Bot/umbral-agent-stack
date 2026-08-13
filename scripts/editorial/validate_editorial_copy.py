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


def _channel_blocks(channel_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Bloques de canal del YAML. Las claves meta (`schema_version`,
    `regla_voz_umbral`) no son dicts, así que se filtran solas y un canal nuevo
    queda reconocido con solo agregar su bloque."""
    return {k: v for k, v in channel_cfg.items() if isinstance(v, dict)}


def validate_copy_text(
    text: str,
    *,
    channel: str = "linkedin",
    check_linkedin_no_question_opening: bool = False,
) -> ValidationResult:
    result = ValidationResult(ok=True)
    benchmark = _load_yaml(_BENCHMARK_PATH)["benchmark_editorial_umbral"]["umbral_de_paso"]
    channel_cfg = _load_yaml(_CHANNEL_PATH)
    blocks = _channel_blocks(channel_cfg)

    # Los canales llegan de selects de Notion y de payloads escritos a mano, así
    # que se normalizan igual que en `_declared_channels`; el mensaje conserva el
    # valor original para que se vea qué se pasó.
    raw_channel = channel
    channel = channel.strip().lower() if isinstance(channel, str) else channel

    # Un canal sin criterios no se puede validar contra su canal: antes caía
    # fuera de todos los `if` y devolvía OK, que es peor que fallar.
    if channel not in blocks:
        result.ok = False
        result.errors.append(
            f"canal sin criterios en channel-criteria-v1.yaml: {raw_channel!r} "
            f"(declarados: {sorted(blocks)})"
        )

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

    # Por defecto todo canal lleva cierre canónico; el bloque que no lo lleve
    # tiene que decirlo. Con la lista al revés (los tres que sí lo llevaban),
    # cada canal nuevo se saltaba el chequeo sin que nadie lo notara.
    cierre_canonico = "Primero claridad. Después velocidad."
    if blocks.get(channel, {}).get("requiere_cierre_canonico", True):
        if cierre_canonico not in text:
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

    if channel == "linkedin_empresa":
        lo, hi = channel_cfg["linkedin_empresa"]["longitud_objetivo_chars"]
        n = len(text.strip())
        if n < lo or n > hi + 200:
            result.warnings.append(f"LinkedIn empresa longitud {n} fuera de objetivo [{lo},{hi}]")

    return result


_PIECE_CHANNELS: tuple[tuple[str, str], ...] = (
    ("linkedin", "copy_linkedin"),
    ("blog", "copy_blog"),
    ("x", "copy_x"),
    ("newsletter", "copy_newsletter"),
)

_CHANNEL_DECLARATION_KEYS = ("canal", "canal_publicado", "target_channels", "channels")


def _coerce_channel_names(value: Any) -> list[str]:
    """Nombres de canal desde cualquiera de los shapes en que llegan: string
    plano, lista, o el `{"select": {"name": ...}}` / `{"name": ...}` crudo de
    Notion. Sin esto el gate falla abierto justo con props de Notion."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        if "select" in value:
            return _coerce_channel_names(value["select"])
        if "name" in value:
            return _coerce_channel_names(value["name"])
        if "multi_select" in value:
            return _coerce_channel_names(value["multi_select"])
        return []
    if isinstance(value, (list, tuple, set)):
        return [name for item in value for name in _coerce_channel_names(item)]
    return [str(value)]


def _declared_channels(payload: dict[str, Any]) -> set[str]:
    """Canales que el payload dice tener como destino, mirando las claves que
    usan las distintas superficies (`canal` en Notion, `target_channels` en el
    gold-set)."""
    declared: set[str] = set()
    for key in _CHANNEL_DECLARATION_KEYS:
        declared.update(n.strip().lower() for n in _coerce_channel_names(payload.get(key)))
    return declared - {""}


def validate_publication_payload(payload: dict[str, Any]) -> ValidationResult:
    merged = ValidationResult(ok=True)
    tesis = payload.get("tesis_canonica", "")
    cierre = payload.get("cierre_canonico", "")
    declared = _declared_channels(payload)

    for channel, key in _PIECE_CHANNELS:
        copy = payload.get(key, "")
        if not copy:
            # `newsletter` se habilitó después de los payloads existentes
            # (CAND-001 no lo trae): falta = warning, salvo que el propio
            # payload declare ese canal como destino, y entonces es error.
            if channel == "newsletter" and channel not in declared:
                merged.warnings.append(
                    f"newsletter: missing {key} (canal habilitado 2026-08-13, "
                    "opcional mientras el payload no lo declare como destino)"
                )
                continue
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

    # copy_linkedin_empresa is P2.3 (Copy LinkedIn empresa), optional for
    # backward compat with payloads written before this column existed
    # (e.g. the CAND-001 anchor) — missing is a warning, not a hard failure.
    copy_linkedin_empresa = payload.get("copy_linkedin_empresa", "")
    if not copy_linkedin_empresa:
        merged.warnings.append("linkedin_empresa: missing copy_linkedin_empresa (P2.3, optional for now)")
    else:
        r = validate_copy_text(copy_linkedin_empresa, channel="linkedin_empresa")
        if not r.ok:
            merged.ok = False
        merged.errors.extend(f"linkedin_empresa: {e}" for e in r.errors)
        merged.warnings.extend(f"linkedin_empresa: {w}" for w in r.warnings)

    blog = payload.get("copy_blog", "")
    if tesis and "gobernanza" not in blog.lower() and "desorden" not in blog.lower():
        merged.warnings.append("blog: verificar tesis canónica explícita")

    # Un solo recorrido de las piezas presentes para los dos chequeos que
    # siguen: antes eran dos tuplas fijas más, y cada canal nuevo obligaba a
    # acordarse de las tres.
    present = [(label, payload.get(key, "")) for label, key in _PIECE_CHANNELS if payload.get(key)]

    for _label, copy in present:
        if re.search(r"\d{2,}%|\d{4}|\bISO\b|\bestudio\b", copy, re.I):
            merged.warnings.append("posible dato/estudio no verificado en pieza de opinión")

    if cierre:
        for label, copy in present:
            if cierre not in copy:
                merged.warnings.append(f"{label}: cierre canónico no encontrado literal")

    return merged


def validate_publication_file(path: Path) -> ValidationResult:
    payload = _load_yaml(path)
    return validate_publication_payload(payload)
