#!/usr/bin/env python3
"""
build_skill.py — Pipeline that converts documentation into valid SKILL.md files.

Usage:
    # From a directory of .md/.txt files
    python scripts/build_skill.py \
        --name "consultor-bim" \
        --source "path/to/docs/" \
        --output "openclaw/workspace-templates/skills/consultor-bim/SKILL.md"

    # From a single markdown file
    python scripts/build_skill.py \
        --name "dynamo-scripting" \
        --source "instrucciones.md" \
        --output "openclaw/workspace-templates/skills/dynamo-scripting/SKILL.md"

    # From a URL
    python scripts/build_skill.py \
        --name "speckle" \
        --url "https://speckle.guide/dev/" \
        --output "openclaw/workspace-templates/skills/speckle/SKILL.md"

Optionally uses LLM (Gemini Flash via GOOGLE_API_KEY) for description/emoji
generation. Falls back to heuristics when no API key is available.
"""

import argparse
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "skill_template.md"
MAX_WORDS = 5000
SUMMARY_TARGET = 4000

EMOJI_MAP = {
    "audio": "\U0001F50A",
    "music": "\U0001F3B5",
    "video": "\U0001F3AC",
    "image": "\U0001F5BC",
    "design": "\U0001F4D0",
    "figma": "\U0001F4D0",
    "search": "\U0001F50D",
    "research": "\U0001F50D",
    "web": "\U0001F310",
    "code": "\U0001F4BB",
    "script": "\U0001F4BB",
    "database": "\U0001F4BE",
    "data": "\U0001F4CA",
    "chart": "\U0001F4CA",
    "status": "\U0001F4CA",
    "monitor": "\U0001F4CA",
    "email": "\U0001F4E7",
    "message": "\U0001F4AC",
    "chat": "\U0001F4AC",
    "file": "\U0001F4C1",
    "folder": "\U0001F4C2",
    "document": "\U0001F4C4",
    "note": "\U0001F4DD",
    "notion": "\U0001F4DD",
    "task": "\U0001F4CB",
    "issue": "\U0001F4CB",
    "linear": "\U0001F4CB",
    "calendar": "\U0001F4C5",
    "time": "\U0000231A",
    "security": "\U0001F512",
    "key": "\U0001F511",
    "api": "\U0001F517",
    "webhook": "\U0001F517",
    "cloud": "\U00002601",
    "server": "\U0001F5A5",
    "deploy": "\U0001F680",
    "build": "\U0001F3D7",
    "test": "\U00002705",
    "debug": "\U0001F41B",
    "bot": "\U0001F916",
    "ai": "\U0001F916",
    "llm": "\U0001F916",
    "automation": "\U00002699",
    "config": "\U00002699",
    "window": "\U0001FAA9",
    "windows": "\U0001FAA9",
    "bim": "\U0001F3D7",
    "revit": "\U0001F3D7",
    "dynamo": "\U0001F3D7",
    "consultor": "\U0001F4BC",
    "business": "\U0001F4BC",
    "marketing": "\U0001F4E2",
}
DEFAULT_EMOJI = "\U0001F4E6"


# ---------------------------------------------------------------------------
# Input reading
# ---------------------------------------------------------------------------

def _sort_key(p: Path) -> Tuple[int, str]:
    """Sort files: numbered prefixes first, then alphabetical."""
    match = re.match(r"^(\d+)", p.stem)
    num = int(match.group(1)) if match else 999
    return (num, p.name.lower())


def read_directory(source_dir: Path) -> str:
    """Read all .md and .txt files from a directory, concatenated in order."""
    files = sorted(
        [f for f in source_dir.iterdir() if f.suffix.lower() in (".md", ".txt") and f.is_file()],
        key=_sort_key,
    )
    if not files:
        raise FileNotFoundError(f"No .md or .txt files found in {source_dir}")

    index_files = [
        f for f in files
        if re.match(r"^(00|01)[_\-]", f.stem, re.IGNORECASE)
        or "indice" in f.stem.lower()
        or "instrucciones" in f.stem.lower()
    ]
    remaining = [f for f in files if f not in index_files]
    ordered = index_files + remaining

    parts: List[str] = []
    for f in ordered:
        content = f.read_text(encoding="utf-8", errors="replace").strip()
        if content:
            parts.append(f"<!-- source: {f.name} -->\n{content}")

    return "\n\n---\n\n".join(parts)


def read_file(source_path: Path) -> str:
    """Read a single file."""
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    return source_path.read_text(encoding="utf-8", errors="replace").strip()


def read_url(url: str) -> str:
    """Fetch content from a URL."""
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-SkillBuilder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code} fetching {url}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e

    raw = _strip_html(raw)
    return raw.strip()


def _strip_html(text: str) -> str:
    """Minimal HTML tag removal for URL-fetched content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_input(source: Optional[str] = None, url: Optional[str] = None) -> str:
    """Read content from source (file or dir) or URL."""
    if source:
        p = Path(source)
        if p.is_dir():
            return read_directory(p)
        elif p.is_file():
            return read_file(p)
        else:
            raise FileNotFoundError(f"Source not found: {source}")
    elif url:
        return read_url(url)
    else:
        raise ValueError("Either --source or --url is required")


# ---------------------------------------------------------------------------
# Metadata extraction (heuristic)
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split())


def _pick_emoji(name: str, content: str) -> str:
    """Pick an emoji based on name/content keywords."""
    combined = f"{name} {content[:500]}".lower()
    for keyword, emoji in EMOJI_MAP.items():
        if keyword in combined:
            return emoji
    return DEFAULT_EMOJI


def _extract_env_vars(content: str) -> List[str]:
    """Extract likely environment variable names from content."""
    patterns = [
        r"`([A-Z][A-Z0-9_]{2,})`",
        r"\b([A-Z][A-Z0-9_]{3,}_(?:KEY|TOKEN|URL|SECRET|ENDPOINT|ID|PASSWORD))\b",
        r"\$\{?([A-Z][A-Z0-9_]{2,})\}?",
    ]
    candidates: set = set()
    for pat in patterns:
        for m in re.finditer(pat, content):
            var = m.group(1)
            if var.endswith(("_KEY", "_TOKEN", "_URL", "_SECRET", "_ENDPOINT", "_ID", "_API_KEY")):
                candidates.add(var)
    exclude = {"TRUE", "FALSE", "NULL", "NONE", "DEFAULT", "OPTIONAL", "REQUIRED"}
    return sorted(candidates - exclude)


def _generate_description_heuristic(name: str, content: str) -> str:
    """Generate a description from content using heuristics."""
    lines = content.strip().splitlines()
    desc_lines: List[str] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith(("#", "<!--", "---", "```", "|")):
            continue
        if len(clean) > 20:
            desc_lines.append(clean)
        if len(desc_lines) >= 3:
            break

    if desc_lines:
        raw = " ".join(desc_lines)
        raw = re.sub(r"\s+", " ", raw).strip()
        if len(raw) > 200:
            raw = raw[:197] + "..."
        return raw

    return f"Skill for {name.replace('-', ' ')}."


def _extract_title(name: str, content: str) -> str:
    """Extract or generate a title."""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# ") and not line.startswith("##"):
            title = line.lstrip("# ").strip()
            if len(title) > 5:
                return title
    return name.replace("-", " ").title() + " Skill"


def _extract_triggers(name: str, content: str) -> List[str]:
    """Extract trigger phrases for the description's 'Use when' clause."""
    words = name.replace("-", " ").split()
    triggers = []
    for w in words:
        if len(w) >= 3:
            triggers.append(w.lower())
    return triggers[:5]


# ---------------------------------------------------------------------------
# LLM-assisted extraction (optional)
# ---------------------------------------------------------------------------

def _try_llm_extraction(name: str, content: str) -> Optional[Dict[str, Any]]:
    """Use Gemini Flash via worker's llm handler to enhance metadata."""
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import json
        import urllib.request

        prompt = textwrap.dedent(f"""\
        Analyze this documentation and generate metadata for an OpenClaw skill.
        Return ONLY a JSON object (no markdown, no code fences) with these fields:
        - "description": concise one-line description (max 150 chars)
        - "emoji": a single Unicode emoji that best represents this tool
        - "triggers": list of 3-5 short trigger phrases (e.g. "search the web")
        - "env_vars": list of environment variable names required

        Skill name: {name}
        Documentation (first 2000 chars):
        {content[:2000]}
        """)

        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```\w*\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
            return json.loads(text)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Content processing
# ---------------------------------------------------------------------------

def _truncate_content(content: str, max_words: int = SUMMARY_TARGET) -> str:
    """Truncate content to max_words, keeping structure."""
    words = content.split()
    if len(words) <= max_words:
        return content

    lines = content.splitlines()
    result: List[str] = []
    count = 0
    for line in lines:
        line_words = len(line.split())
        if count + line_words > max_words:
            result.append("...")
            result.append(f"\n_(Content truncated from {len(words)} to ~{max_words} words)_")
            break
        result.append(line)
        count += line_words

    return "\n".join(result)


def _split_procedures_and_body(content: str) -> Tuple[str, str, str]:
    """Split content into body, procedures, and references."""
    body_parts: List[str] = []
    procedures_parts: List[str] = []
    references_parts: List[str] = []

    current_section = "body"
    for line in content.splitlines():
        lower = line.strip().lower()
        if re.match(r"^#{1,3}\s*(procedimientos?|procedures?|pasos|steps|how[\s-]to|uso|usage)", lower):
            current_section = "procedures"
            continue
        elif re.match(r"^#{1,3}\s*(referencias?|references?|links?|fuentes?|sources?|recursos?)", lower):
            current_section = "references"
            continue

        if current_section == "body":
            body_parts.append(line)
        elif current_section == "procedures":
            procedures_parts.append(line)
        else:
            references_parts.append(line)

    body = "\n".join(body_parts).strip()
    procedures = "\n".join(procedures_parts).strip()
    references = "\n".join(references_parts).strip()

    if not procedures:
        procedures = _auto_generate_procedures(body)
    if not references:
        references = "_No external references._"

    return body, procedures, references


def _auto_generate_procedures(content: str) -> str:
    """Generate basic procedures from content structure."""
    steps: List[str] = []
    for line in content.splitlines():
        line_s = line.strip()
        if line_s.startswith(("### ", "## ")) and not line_s.startswith("####"):
            heading = line_s.lstrip("#").strip()
            if heading and len(heading) > 3:
                steps.append(f"- {heading}")

    if steps:
        return "\n".join(steps[:10])
    return "_Refer to the documentation above for detailed procedures._"


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_skill(
    name: str,
    content: str,
    llm_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a complete SKILL.md from name and content."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    content = _truncate_content(content)

    if llm_meta:
        description = llm_meta.get("description", "")
        emoji = llm_meta.get("emoji", "")
        env_vars = llm_meta.get("env_vars", [])
        triggers = llm_meta.get("triggers", [])
    else:
        description = ""
        emoji = ""
        env_vars = []
        triggers = []

    if not description:
        description = _generate_description_heuristic(name, content)

    if triggers:
        trigger_str = ", ".join(f'"{t}"' for t in triggers[:5])
        description = f"{description}\n  Use when {trigger_str}."

    if not emoji:
        emoji = _pick_emoji(name, content)

    if not env_vars:
        env_vars = _extract_env_vars(content)
    if not env_vars:
        env_vars = ["WORKER_TOKEN"]

    title = _extract_title(name, content)
    body, procedures, references = _split_procedures_and_body(content)

    env_lines = "\n".join(f"        - {v}" for v in env_vars)

    result = template
    result = result.replace("{{name}}", name)
    result = result.replace("{{description}}", description)
    result = result.replace("{{emoji}}", emoji)
    result = result.replace("{{env_vars}}", env_lines)
    result = result.replace("{{title}}", title)
    result = result.replace("{{body}}", body)
    result = result.replace("{{procedures}}", procedures)
    result = result.replace("{{references}}", references)

    return result


# ---------------------------------------------------------------------------
# Validation integration
# ---------------------------------------------------------------------------

def validate_output(output_path: Path) -> Tuple[bool, List[str]]:
    """Run validation on the generated SKILL.md."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from validate_skills import validate_skill
        errors = validate_skill(output_path)
        return len(errors) == 0, errors
    except ImportError:
        return True, ["validate_skills.py not found; skipping validation"]
    finally:
        sys.path.pop(0)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_skill(
    name: str,
    source: Optional[str] = None,
    url: Optional[str] = None,
    output: Optional[str] = None,
    use_llm: bool = True,
) -> Path:
    """Main pipeline: read input → extract metadata → render → validate → write."""
    content = read_input(source=source, url=url)

    if not content.strip():
        raise ValueError("Source content is empty")

    llm_meta = None
    if use_llm:
        llm_meta = _try_llm_extraction(name, content)
        if llm_meta:
            print(f"  LLM metadata extracted: {list(llm_meta.keys())}")
        else:
            print("  LLM not available; using heuristics.")

    rendered = render_skill(name, content, llm_meta)

    word_count = _word_count(rendered)
    if word_count > MAX_WORDS:
        print(f"  WARNING: Output has {word_count} words (max {MAX_WORDS})")

    if output:
        out_path = Path(output)
    else:
        out_path = REPO_ROOT / "openclaw" / "workspace-templates" / "skills" / name / "SKILL.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"  Written: {out_path} ({word_count} words)")

    valid, errors = validate_output(out_path)
    if valid:
        print("  Validation: PASSED")
    else:
        print(f"  Validation: FAILED")
        for err in errors:
            print(f"    - {err}")

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SKILL.md from documentation sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", required=True, help="Skill name (lowercase, hyphenated)")
    parser.add_argument("--source", help="Path to source file or directory")
    parser.add_argument("--url", help="URL to fetch documentation from")
    parser.add_argument("--output", help="Output path for SKILL.md (default: skills/<name>/SKILL.md)")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM-assisted extraction")

    args = parser.parse_args()

    if not args.source and not args.url:
        parser.error("Either --source or --url is required")

    print(f"Building skill: {args.name}")

    try:
        build_skill(
            name=args.name,
            source=args.source,
            url=args.url,
            output=args.output,
            use_llm=not args.no_llm,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
