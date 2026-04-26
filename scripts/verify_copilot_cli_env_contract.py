#!/usr/bin/env python3
"""Verify the Copilot CLI EnvironmentFile contract.

Checks /etc/umbral/copilot-cli.env and /etc/umbral/copilot-cli-secrets.env
against the contract documented in:

  docs/copilot-cli-f6-step1-token-plumbing-evidence.md

What it checks (when files exist):
  - owner == ``rick``, group == ``rick``
  - mode == ``0600``
  - copilot-cli.env       MUST NOT contain COPILOT_GITHUB_TOKEN
  - copilot-cli-secrets.env MUST NOT contain GH_TOKEN or GITHUB_TOKEN
  - neither file contains a classic PAT (``ghp_…``) — unsupported and
    a strong signal of misconfiguration

By default the script EXITS 0 if files are missing (operator hasn't
provisioned yet). Pass ``--strict`` to require their presence.

The script never prints token values. Findings reference offsets only.
"""

from __future__ import annotations

import argparse
import os
import pwd
import re
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_RUNTIME_PATH = Path("/etc/umbral/copilot-cli.env")
DEFAULT_SECRETS_PATH = Path("/etc/umbral/copilot-cli-secrets.env")
EXPECTED_OWNER = "rick"
EXPECTED_GROUP = "rick"
EXPECTED_MODE = 0o600

_FORBIDDEN_IN_RUNTIME = ("COPILOT_GITHUB_TOKEN",)
_FORBIDDEN_IN_SECRETS = ("GH_TOKEN", "GITHUB_TOKEN")
_CLASSIC_PAT_RE = re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")


@dataclass
class Finding:
    path: str
    severity: str  # "error" | "warn" | "info"
    code: str
    message: str  # never contains token values

    def render(self) -> str:
        return f"[{self.severity.upper():5}] {self.path}: {self.code} — {self.message}"


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)

    def add(self, *args, **kwargs) -> None:
        self.findings.append(Finding(*args, **kwargs))

    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def render(self) -> str:
        if not self.findings:
            return "OK — no findings."
        return "\n".join(f.render() for f in self.findings)


def _resolve_owner_group(uid: int, gid: int) -> Tuple[Optional[str], Optional[str]]:
    try:
        owner = pwd.getpwuid(uid).pw_name
    except KeyError:
        owner = None
    try:
        import grp
        group = grp.getgrgid(gid).gr_name
    except (KeyError, ImportError):
        group = None
    return owner, group


def check_perms(path: Path, report: Report) -> None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return
    mode = stat.S_IMODE(st.st_mode)
    if mode != EXPECTED_MODE:
        report.add(
            str(path), "error", "perm_mode",
            f"mode is 0{mode:o}, expected 0{EXPECTED_MODE:o}",
        )
    owner, group = _resolve_owner_group(st.st_uid, st.st_gid)
    if owner != EXPECTED_OWNER:
        report.add(
            str(path), "error", "perm_owner",
            f"owner is {owner!r}, expected {EXPECTED_OWNER!r}",
        )
    if group != EXPECTED_GROUP:
        report.add(
            str(path), "error", "perm_group",
            f"group is {group!r}, expected {EXPECTED_GROUP!r}",
        )


def _scan_lines(path: Path) -> List[Tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    out: List[Tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append((i, line))
    return out


def _line_assigns(line: str) -> Optional[str]:
    """Return the variable name being assigned, or None."""
    if "=" not in line:
        return None
    name, _, _ = line.partition("=")
    return name.strip()


def check_runtime_file(path: Path, report: Report) -> None:
    if not path.exists():
        return
    # Scan ALL lines for classic PAT (defense against accidental pastes
    # in comments), then scan non-comment lines for forbidden assignments.
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    for lineno, raw in enumerate(text.splitlines(), 1):
        if _CLASSIC_PAT_RE.search(raw):
            report.add(
                str(path), "error", "classic_pat_detected",
                f"line {lineno}: classic PAT (ghp_*) is unsupported by Copilot CLI; rotate to fine-grained PAT v2",
            )
    for lineno, line in _scan_lines(path):
        var = _line_assigns(line)
        if var in _FORBIDDEN_IN_RUNTIME:
            report.add(
                str(path), "error", "secret_in_runtime_file",
                f"line {lineno}: variable {var!r} must live in copilot-cli-secrets.env, not here",
            )


def check_secrets_file(path: Path, report: Report) -> None:
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    for lineno, raw in enumerate(text.splitlines(), 1):
        if _CLASSIC_PAT_RE.search(raw):
            report.add(
                str(path), "error", "classic_pat_detected",
                f"line {lineno}: classic PAT (ghp_*) is unsupported by Copilot CLI; rotate to fine-grained PAT v2",
            )
    saw_copilot_token = False
    for lineno, line in _scan_lines(path):
        var = _line_assigns(line)
        if var in _FORBIDDEN_IN_SECRETS:
            report.add(
                str(path), "error", "wrong_token_var",
                f"line {lineno}: variable {var!r} forbidden — use COPILOT_GITHUB_TOKEN only",
            )
        if var == "COPILOT_GITHUB_TOKEN":
            saw_copilot_token = True
    if not saw_copilot_token:
        report.add(
            str(path), "warn", "no_copilot_token",
            "COPILOT_GITHUB_TOKEN not set; capability will reject at runtime",
        )


def run(
    runtime_path: Path = DEFAULT_RUNTIME_PATH,
    secrets_path: Path = DEFAULT_SECRETS_PATH,
    *,
    strict: bool = False,
    check_permissions: bool = True,
) -> Report:
    report = Report()

    for label, path in (("runtime", runtime_path), ("secrets", secrets_path)):
        if not path.exists():
            sev = "error" if strict else "info"
            code = "missing_file" if strict else "missing_file_skipped"
            report.add(str(path), sev, code, f"{label} env file absent")

    if check_permissions:
        check_perms(runtime_path, report)
        check_perms(secrets_path, report)
    check_runtime_file(runtime_path, report)
    check_secrets_file(secrets_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--runtime", default=str(DEFAULT_RUNTIME_PATH))
    parser.add_argument("--secrets", default=str(DEFAULT_SECRETS_PATH))
    parser.add_argument(
        "--strict", action="store_true",
        help="exit non-zero if env files are missing",
    )
    parser.add_argument(
        "--no-perm-check", action="store_true",
        help="skip owner/group/mode checks (useful in CI)",
    )
    args = parser.parse_args()

    report = run(
        Path(args.runtime),
        Path(args.secrets),
        strict=args.strict,
        check_permissions=not args.no_perm_check,
    )
    print(report.render())
    return 1 if report.errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
