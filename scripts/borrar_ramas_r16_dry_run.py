#!/usr/bin/env python3
"""
Genera comandos de borrado remoto de ramas para R16 (dry-run).

No ejecuta ningun borrado. Solo imprime o guarda comandos:
    git push origin --delete <rama>

Uso:
    python scripts/borrar_ramas_r16_dry_run.py
    python scripts/borrar_ramas_r16_dry_run.py --doc docs/ramas-recomendadas-borrar-r16.md
    python scripts/borrar_ramas_r16_dry_run.py --output docs/comandos-borrar-ramas-r16.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_DOC_CANDIDATES = [
    Path("docs/guia-borrar-ramas-r16.md"),
    Path("docs/ramas-recomendadas-borrar-r16.md"),
]

# Branch names are usually in markdown code ticks (`branch/name`) in the first column.
TICKED_BRANCH_RE = re.compile(r"`([A-Za-z0-9._\-/]+)`")


def pick_doc(path_arg: str | None) -> Path:
    if path_arg:
        doc = Path(path_arg)
        if not doc.exists():
            raise FileNotFoundError(f"Document not found: {doc}")
        return doc

    for candidate in DEFAULT_DOC_CANDIDATES:
        if candidate.exists():
            return candidate

    tried = ", ".join(str(p) for p in DEFAULT_DOC_CANDIDATES)
    raise FileNotFoundError(f"No input document found. Tried: {tried}")


def parse_branches_from_markdown(text: str) -> list[str]:
    branches: list[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Markdown table row: | `branch` | reason |
        if line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            # Expected shape: ["", "<col1>", "<col2>", ... , ""]
            if len(parts) >= 3:
                first_col = parts[1]
                m = TICKED_BRANCH_RE.search(first_col)
                if m:
                    branch = m.group(1)
                    if branch not in seen:
                        seen.add(branch)
                        branches.append(branch)
            continue

        # Bullet fallback: - `branch/name`
        if line.startswith("-") or line.startswith("*"):
            m = TICKED_BRANCH_RE.search(line)
            if m:
                branch = m.group(1)
                if branch not in seen:
                    seen.add(branch)
                    branches.append(branch)

    return branches


def build_delete_commands(branches: list[str]) -> list[str]:
    return [f"git push origin --delete {branch}" for branch in branches]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate dry-run git delete commands for R16 branch cleanup."
    )
    parser.add_argument(
        "--doc",
        help="Markdown source with branches to delete. Defaults to docs/guia-borrar-ramas-r16.md or docs/ramas-recomendadas-borrar-r16.md",
    )
    parser.add_argument(
        "--output",
        help="Optional output .txt path. If omitted, prints to stdout.",
    )
    args = parser.parse_args()

    try:
        doc_path = pick_doc(args.doc)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    content = doc_path.read_text(encoding="utf-8")
    branches = parse_branches_from_markdown(content)
    if not branches:
        print(f"No branches found in: {doc_path}", file=sys.stderr)
        return 1

    commands = build_delete_commands(branches)
    header = [
        "# DRY-RUN ONLY: generated commands, do not run blindly.",
        f"# Source document: {doc_path}",
        f"# Branches found: {len(branches)}",
        "",
    ]
    output_text = "\n".join(header + commands) + "\n"

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"Wrote {len(commands)} commands to: {out_path}")
    else:
        print(output_text, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

