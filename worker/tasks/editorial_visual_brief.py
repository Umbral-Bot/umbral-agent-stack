"""Deterministic Visual brief v2 parsing and prompt assembly.

The editorial agent owns the semantic derivation of the core metaphor and the
five controlled variation axes.  The Worker deliberately does not call an LLM
here: it validates that versioned contract and assembles one bounded prompt per
axis.  This keeps image generation reproducible and leaves legacy, unversioned
briefs to their existing one-prompt/five-sample path.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


VISUAL_BRIEF_V2_VERSION = 2
V2_DEFAULT_ENGINE = "nano-banana-pro"
V2_PROMPT_STRATEGY = "five_controlled_prompts"
V2_VARIANT_COUNT = 5
MAX_VISUAL_BRIEF_V2_CHARS = 2000

_RAW_V2_DECLARATION_RE = re.compile(
    r'''(?im)^(?:version|["']version["'])\s*:\s*'''
    r'''(?:2|v2|["']2["']|["']v2["'])\s*(?:#.*)?$'''
)
_RAW_V2_FLOW_ENTRY_RE = re.compile(
    r'''(?is)^\s*(?:version|["']version["'])\s*:\s*'''
    r'''(?:2|v2|["']2["']|["']v2["'])\s*(?:#.*)?$'''
)


class VisualBriefV2Error(ValueError):
    """Raised when a declared Visual brief v2 violates its contract."""


@dataclass(frozen=True)
class VisualBriefVariation:
    axis: str
    direction: str


@dataclass(frozen=True)
class VisualBriefV2:
    central_fact: str
    ignored_consequence: str
    core_metaphor: str
    invariants: tuple[str, ...]
    variation_axes: tuple[VisualBriefVariation, ...]
    negative_prohibitions: tuple[str, ...]
    avoid: tuple[str, ...]
    engine: str | None


def is_visual_brief_v2(brief: Mapping[str, Any]) -> bool:
    """Return true only for an explicit v2 declaration.

    Missing and unrecognized versions intentionally remain on the legacy path
    so existing free-form/v1 briefs keep their historical behavior.
    """

    value = str(brief.get("version") or "").strip().lower()
    return value in {"2", "v2"}


def raw_declares_visual_brief_v2(raw_brief: Any) -> bool:
    """Detect an explicit top-level v2 marker even when YAML parsing fails.

    Legacy malformed briefs keep their historical fallback.  A document that
    explicitly opts into v2 must instead fail closed rather than silently
    spending five calls through the legacy Flash path.
    """

    text = normalize_visual_brief_text(raw_brief)
    flow_candidate = "\n".join(
        line
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith(("#", "%"))
        and line.strip() not in {"---", "..."}
    ).lstrip()
    return bool(
        _RAW_V2_DECLARATION_RE.search(text)
        or _root_flow_mapping_declares_v2(flow_candidate)
    )


def _root_flow_mapping_declares_v2(text: str) -> bool:
    """Find a v2 key anywhere in a root flow mapping, even if its tail is invalid."""

    candidate = re.sub(r"^---(?:\s+|$)", "", text.lstrip(), count=1).lstrip()
    if not candidate.startswith("{"):
        return False

    curly_depth = 1
    square_depth = 0
    quote = ""
    entry_start = 1
    index = 1
    while index < len(candidate):
        char = candidate[index]
        if quote:
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if (
                    quote == "'"
                    and index + 1 < len(candidate)
                    and candidate[index + 1] == "'"
                ):
                    index += 2
                    continue
                quote = ""
            index += 1
            continue

        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            curly_depth += 1
        elif char == "}":
            if curly_depth == 1 and square_depth == 0:
                return bool(
                    _RAW_V2_FLOW_ENTRY_RE.match(candidate[entry_start:index])
                )
            curly_depth = max(1, curly_depth - 1)
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth = max(0, square_depth - 1)
        elif char == "," and curly_depth == 1 and square_depth == 0:
            if _RAW_V2_FLOW_ENTRY_RE.match(candidate[entry_start:index]):
                return True
            entry_start = index + 1
        index += 1
    return bool(
        curly_depth == 1
        and square_depth == 0
        and not quote
        and _RAW_V2_FLOW_ENTRY_RE.match(candidate[entry_start:])
    )


def _dedent_yaml_payload(text: str) -> str:
    """Dedent YAML content while ignoring column-zero comments/directives."""

    lines = text.splitlines()
    significant_indents = []
    for line in lines:
        stripped = line.lstrip()
        if (
            not stripped
            or stripped.startswith(("#", "%"))
            or stripped in {"---", "..."}
        ):
            continue
        significant_indents.append(len(line) - len(stripped))
    margin = min(significant_indents, default=0)
    if margin:
        lines = [
            line[margin:]
            if len(line) - len(line.lstrip()) >= margin
            else line
            for line in lines
        ]
    return "\n".join(lines)


def normalize_visual_brief_text(raw_brief: Any) -> str:
    """Normalize transport indentation without changing the YAML contract.

    Notion/CLI callers can supply a uniformly indented block or a fenced YAML
    block.  Dedenting here keeps an explicit top-level v2 marker top-level for
    both parsing and fail-closed raw detection, while the column-zero detector
    still ignores a nested ``version`` key in a legacy document.
    """

    text = _dedent_yaml_payload(
        textwrap.dedent(str(raw_brief or "").lstrip("\ufeff"))
    ).strip()
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
        if lines and lines[-1].lstrip().startswith("```"):
            lines = lines[:-1]
        text = _dedent_yaml_payload("\n".join(lines)).strip()
    return text


def _required_text(brief: Mapping[str, Any], key: str) -> str:
    raw_value = brief.get(key)
    if not isinstance(raw_value, str):
        raise VisualBriefV2Error(f"Visual brief v2 '{key}' must be text")
    value = raw_value.strip()
    if not value:
        raise VisualBriefV2Error(f"Visual brief v2 requires '{key}'")
    return value


def _text_items(value: Any, *, key: str, required: bool) -> tuple[str, ...]:
    if value is None:
        items: Sequence[Any] = ()
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        raise VisualBriefV2Error(f"Visual brief v2 '{key}' must be a list")
    if any(not isinstance(item, str) for item in items):
        raise VisualBriefV2Error(
            f"Visual brief v2 '{key}' items must be text"
        )
    normalized = tuple(item.strip() for item in items if item.strip())
    if required and not normalized:
        raise VisualBriefV2Error(
            f"Visual brief v2 requires at least one '{key}' item"
        )
    return normalized


def parse_visual_brief_v2(brief: Mapping[str, Any]) -> VisualBriefV2:
    """Validate and normalize an explicitly declared Visual brief v2."""

    if not is_visual_brief_v2(brief):
        raise VisualBriefV2Error("Visual brief is not explicitly version 2")

    raw_axes = brief.get("variation_axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != V2_VARIANT_COUNT:
        raise VisualBriefV2Error(
            "Visual brief v2 requires exactly five 'variation_axes'"
        )

    axes: list[VisualBriefVariation] = []
    seen_axes: set[str] = set()
    seen_directions: set[str] = set()
    for index, raw_axis in enumerate(raw_axes, start=1):
        if not isinstance(raw_axis, dict):
            raise VisualBriefV2Error(
                f"Visual brief v2 variation_axes[{index}] must be a mapping"
            )
        normalized_axis = {
            str(key).strip().lower(): value for key, value in raw_axis.items()
        }
        raw_axis_name = normalized_axis.get("axis")
        raw_direction = normalized_axis.get("direction")
        if not isinstance(raw_axis_name, str) or not isinstance(raw_direction, str):
            raise VisualBriefV2Error(
                f"Visual brief v2 variation_axes[{index}] axis and direction must be text"
            )
        axis = raw_axis_name.strip()
        direction = raw_direction.strip()
        if not axis or not direction:
            raise VisualBriefV2Error(
                f"Visual brief v2 variation_axes[{index}] requires axis and direction"
            )
        axis_key = axis.casefold()
        direction_key = " ".join(direction.casefold().split())
        if axis_key in seen_axes:
            raise VisualBriefV2Error(
                "Visual brief v2 variation axis names must be unique"
            )
        if direction_key in seen_directions:
            raise VisualBriefV2Error(
                "Visual brief v2 variation directions must be unique"
            )
        seen_axes.add(axis_key)
        seen_directions.add(direction_key)
        axes.append(VisualBriefVariation(axis=axis, direction=direction))

    raw_engine = brief.get("engine")
    if raw_engine is not None and not isinstance(raw_engine, str):
        raise VisualBriefV2Error("Visual brief v2 'engine' must be text")
    engine_text = (raw_engine or "").strip()
    return VisualBriefV2(
        central_fact=_required_text(brief, "central_fact"),
        ignored_consequence=_required_text(brief, "ignored_consequence"),
        core_metaphor=_required_text(brief, "core_metaphor"),
        invariants=_text_items(
            brief.get("invariants"), key="invariants", required=False
        ),
        variation_axes=tuple(axes),
        negative_prohibitions=_text_items(
            brief.get("negative_prohibitions"),
            key="negative_prohibitions",
            required=True,
        ),
        avoid=_text_items(brief.get("avoid"), key="avoid", required=False),
        engine=engine_text or None,
    )


def _compact(value: str) -> str:
    return " ".join(value.split())


def _join_items(items: Sequence[str]) -> str:
    return "; ".join(_compact(item) for item in items)


def _sentence(value: str) -> str:
    return value if value.endswith((".", "!", "?")) else f"{value}."


def build_visual_brief_v2_prompts(
    brief: Mapping[str, Any],
    *,
    anti_slop_suffix: str,
    max_prompt_chars: int,
) -> tuple[VisualBriefV2, list[str]]:
    """Build exactly five bounded prompts from a generic v2 brief.

    The semantic prohibitions, per-alternative axis, and shared style suffix
    live in the fixed tail so pathological long source fields cannot truncate
    the safety/variation contract.
    """

    parsed = parse_visual_brief_v2(brief)
    common = " ".join(
        [
            f"Metáfora núcleo: {_sentence(_compact(parsed.core_metaphor))}",
            (
                "Consecuencia de ignorar el hecho central: "
                f"{_sentence(_compact(parsed.ignored_consequence))}"
            ),
            f"Hecho central: {_sentence(_compact(parsed.central_fact))}",
        ]
    )

    invariants_clause = ""
    if parsed.invariants:
        invariants_clause = (
            "Invariantes compartidos: "
            f"{_sentence(_join_items(parsed.invariants))}"
        )

    negative_clause = (
        "Prohibiciones negativas: "
        f"{_sentence(_join_items(parsed.negative_prohibitions))}"
    )
    avoid_clause = ""
    if parsed.avoid:
        avoid_clause = f"Evitar: {_sentence(_join_items(parsed.avoid))}"
    suffix = " ".join(str(anti_slop_suffix or "").split()).strip()

    prompts: list[str] = []
    for index, variation in enumerate(parsed.variation_axes, start=1):
        invariant_clause = (
            "Mantén constantes la metáfora núcleo, la consecuencia y los invariantes."
            if parsed.invariants
            else "Mantén constantes la metáfora núcleo y la consecuencia."
        )
        variation_clause = (
            f"Alternativa {index}: cambia únicamente el eje "
            f"'{_compact(variation.axis)}': "
            f"{_sentence(_compact(variation.direction))} {invariant_clause}"
        )
        fixed_tail = " ".join(
            part
            for part in (
                invariants_clause,
                variation_clause,
                negative_clause,
                avoid_clause,
                suffix,
            )
            if part
        )
        prefix_budget = max_prompt_chars - len(fixed_tail) - 1
        if prefix_budget < 2:
            raise VisualBriefV2Error(
                "Visual brief v2 constraints exceed the image prompt limit"
            )
        prompt = f"{common[:prefix_budget].rstrip()} {fixed_tail}".strip()
        if len(prompt) > max_prompt_chars:
            raise VisualBriefV2Error(
                "Visual brief v2 prompt exceeds the image prompt limit"
            )
        prompts.append(prompt)

    if len(set(prompts)) != V2_VARIANT_COUNT:
        raise VisualBriefV2Error(
            "Visual brief v2 must produce five distinct prompts"
        )
    return parsed, prompts
