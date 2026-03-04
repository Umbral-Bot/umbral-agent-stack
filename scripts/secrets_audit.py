#!/usr/bin/env python3
"""
Secrets Audit — Escanea el repo en busca de credenciales expuestas.

Uso:
    python scripts/secrets_audit.py              # escanea y reporta
    python scripts/secrets_audit.py --ci         # exit code 1 si encuentra algo (para CI)

Patterns detectados:
    - API keys (sk-, key-, ghp_, ghs_, AKIA)
    - Tokens largos alfanuméricos (32+ chars)
    - Passwords en variables de entorno hardcodeadas
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories/files to exclude
EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "docs", ".agents", ".gemini", ".pre-commit-config.yaml",
}
EXCLUDED_FILES = {
    ".env.example", ".env.sample", "secrets_audit.py",
}
EXCLUDED_EXTENSIONS = {
    ".pyc", ".pyo", ".whl", ".egg", ".tar", ".gz", ".zip",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".webm", ".webp",
}

# Secret patterns
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("AWS Access Key",     re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub PAT",         re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub Server",      re.compile(r"ghs_[A-Za-z0-9]{36}")),
    ("OpenAI Key",         re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Generic key=",       re.compile(r"""(?:api[_-]?key|secret|token|password|passwd)\s*[=:]\s*['"][A-Za-z0-9+/=]{16,}['"]""", re.IGNORECASE)),
    ("Long hex/b64 token", re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9+/]{40,}(?![A-Za-z0-9+/=])")),
]


def _should_skip(path: Path) -> bool:
    """Return True if path should be excluded from scanning."""
    parts = path.relative_to(REPO_ROOT).parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    if path.name in EXCLUDED_FILES:
        return True
    if path.suffix in EXCLUDED_EXTENSIONS:
        return True
    # Skip test files
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True
    return False


def scan_file(path: Path) -> List[Tuple[int, str, str]]:
    """Scan a single file for secret patterns. Returns [(line_num, pattern_name, line)]."""
    findings = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return findings

    for line_num, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((line_num, name, stripped[:120]))
                break  # one finding per line is enough
    return findings


def scan_repo(root: Path = REPO_ROOT) -> dict:
    """Scan entire repo and return results dict."""
    results = {"files_scanned": 0, "findings": []}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _should_skip(path):
            continue
        results["files_scanned"] += 1
        findings = scan_file(path)
        if findings:
            rel = path.relative_to(root)
            for line_num, pattern_name, line_text in findings:
                results["findings"].append({
                    "file": str(rel),
                    "line": line_num,
                    "pattern": pattern_name,
                    "preview": line_text,
                })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo for exposed secrets")
    parser.add_argument("--ci", action="store_true", help="Exit 1 if secrets found (for CI)")
    args = parser.parse_args()

    results = scan_repo()

    print(f"📂 Files scanned: {results['files_scanned']}")

    if not results["findings"]:
        print("✅ No secrets found.")
        return 0

    print(f"\n⚠️  Found {len(results['findings'])} potential secret(s):\n")
    for f in results["findings"]:
        print(f"  {f['file']}:{f['line']}  [{f['pattern']}]")
        print(f"    {f['preview']}")
        print()

    if args.ci:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
