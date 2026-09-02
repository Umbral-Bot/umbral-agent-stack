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

CIERRE_CANONICO = "Primero claridad. Después velocidad."

# A source line is the "Fuente:" row that closes every piece. The URL there must
# be a markdown hyperlink with visible text, never the bare address: a raw URL
# reads as a paste, breaks on LinkedIn, and glues itself to the closing slogan.
_SOURCE_LINE_RE = re.compile(r"^\s*fuente\s*:\s*(?P<rest>.+?)\s*$", re.IGNORECASE)
_MD_LINK_RE = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)")
_RAW_URL_RE = re.compile(r"(?<![(\]])\bhttps?://[^\s)\]]+")
_HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_H2_RE = re.compile(r"^\s*##\s+\S")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s*\S")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")


def _blog_structure_counts(text: str) -> tuple[int, int]:
    """Count H2 headings and blockquote *blocks*, ignoring fenced code.

    A four-line quote is one quote, and a ``##`` inside a fenced code block is a
    code sample, not a subtitle: counting either naively turns a correct piece
    into a warning QA learns to ignore.
    """
    h2 = 0
    quote_blocks = 0
    in_fence = False
    in_quote = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            in_quote = False
            continue
        if in_fence:
            continue
        if _H2_RE.match(line):
            h2 += 1
        if _BLOCKQUOTE_RE.match(line):
            if not in_quote:
                quote_blocks += 1
            in_quote = True
        elif not line.strip():
            in_quote = False
    return h2, quote_blocks


def _closing_and_link_findings(text: str, *, requires_cierre: bool) -> tuple[list[str], list[str]]:
    """Enforce the closing contract: hyperlinked source, then the slogan alone.

    Returns ``(errors, warnings)``. Three rules, all learned from the live
    `bim-carbono-ciclo-de-vida-diseno` post (2026-09-02), where the raw RICS
    address and the brand slogan ran together at the end of a wall of text:

    1. the ``Fuente:`` line carries ``[texto](url)``, never a bare address;
    2. the canonical slogan is the last non-empty line of the piece;
    3. at least one blank line or a markdown ``hr`` separates the slogan from
       whatever precedes it, so it reads as a brand sign-off and not as the
       continuation of the argument.
    """
    errors: list[str] = []
    warnings: list[str] = []
    lines = text.splitlines()
    non_empty = [(i, ln) for i, ln in enumerate(lines) if ln.strip()]

    source_urls: set[str] = set()
    for _, line in non_empty:
        m = _SOURCE_LINE_RE.match(line)
        if not m:
            continue
        rest = m.group("rest")
        linked = _MD_LINK_RE.findall(rest)
        for raw in _RAW_URL_RE.findall(rest):
            errors.append(
                f"URL cruda en la línea Fuente ({raw[:60]}...); usar [texto](url)"
            )
        for _text, url in linked:
            source_urls.add(url)

    # The same source address pasted bare anywhere else is the identical defect.
    normalized_sources = {u.rstrip("/") for u in source_urls}
    for _, line in non_empty:
        if _SOURCE_LINE_RE.match(line):
            continue
        for raw in _RAW_URL_RE.findall(line):
            if raw.rstrip("/") in normalized_sources:
                errors.append(f"URL de fuente cruda fuera de un hipervínculo ({raw[:60]}...)")

    if not requires_cierre:
        return errors, warnings

    if CIERRE_CANONICO not in text:
        errors.append("cierre canónico ausente o incompleto")
        return errors, warnings

    if not non_empty:
        errors.append("cierre canónico ausente o incompleto")
        return errors, warnings

    last_idx, last_line = non_empty[-1]
    if CIERRE_CANONICO not in last_line:
        errors.append("el cierre canónico no es la última línea de la pieza")
        return errors, warnings
    if last_line.strip() != CIERRE_CANONICO:
        warnings.append("el cierre canónico comparte línea con otro texto")

    if len(non_empty) > 1:
        gap = lines[last_idx - 1] if last_idx > 0 else ""
        if gap.strip() and not _HR_RE.match(gap):
            errors.append(
                "cierre canónico pegado al bloque anterior; falta línea en blanco o hr"
            )
    return errors, warnings


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
    #
    # Desde 2026-09-02 el cierre es contrato duro, no un aviso: ausente, fuera
    # del final o pegado al bloque Fuente bloquea la pieza, igual que una URL
    # de fuente sin hipervínculo.
    closing_errors, closing_warnings = _closing_and_link_findings(
        text,
        requires_cierre=blocks.get(channel, {}).get("requiere_cierre_canonico", True),
    )
    if closing_errors:
        result.ok = False
        result.errors.extend(closing_errors)
    result.warnings.extend(closing_warnings)

    # H2, blockquote y hr son formato de lectura permitido (y esperado en blog):
    # nada de lo anterior los penaliza. Sólo se avisa cuando se van del rango
    # del contrato para que QA lo mire, sin bloquear piezas históricas.
    if channel == "blog":
        h2_count, quote_blocks = _blog_structure_counts(text)
        if not 2 <= h2_count <= 4:
            result.warnings.append(f"blog: {h2_count} subtítulos H2 fuera del rango [2,4]")
        if quote_blocks > 1:
            result.warnings.append(f"blog: {quote_blocks} citas; el contrato pide una sola")

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
