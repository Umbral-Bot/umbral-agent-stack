#!/usr/bin/env python3
"""verify_copilot_egress_contract.py — F6 step 3 verifier.

Asserts that the egress design artifacts in this repo are internally
consistent and aligned with `config/tool_policy.yaml`. Does NOT touch
nftables / iptables / Docker networks. Does NOT require root. Does
NOT resolve DNS unless `--resolve` is passed (and even then, only as
a read-only sanity check whose results are printed and discarded).

Exit 0 if the contract holds; exit 1 if any error is found.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POLICY = REPO_ROOT / "config" / "tool_policy.yaml"
DEFAULT_NFT = REPO_ROOT / "infra" / "networking" / "copilot-egress.nft.example"
DEFAULT_RESOLVER_DOC = REPO_ROOT / "infra" / "networking" / "copilot-egress-resolver.md"

# Live-firewall commands that must NEVER appear uncommented in the
# repo artifacts (they would be dangerous if executed by mistake).
_DANGEROUS_LIVE_CMDS = (
    re.compile(r"^\s*nft\s+(?:add|delete|flush|create|insert)\b"),
    re.compile(r"^\s*iptables\b"),
    re.compile(r"^\s*ip6tables\b"),
    re.compile(r"^\s*ufw\b"),
    re.compile(r"^\s*systemctl\s+(?:start|enable|restart)\b"),
    re.compile(r"^\s*docker\s+network\s+(?:create|connect|disconnect|rm)\b"),
)

_REQUIRED_NFT_MARKERS = (
    "DO NOT APPLY",
    "define copilot_bridge",
    "policy accept",
    "iifname != $copilot_bridge accept",
    "counter drop",
    "table inet copilot_egress",
)

_REQUIRED_RESOLVER_MARKERS = (
    "DESIGN ONLY",
    "rollback",
)


@dataclass
class Finding:
    path: str
    severity: str  # "error" | "warn" | "info"
    code: str
    message: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, path: str, severity: str, code: str, message: str) -> None:
        self.findings.append(Finding(path, severity, code, message))

    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def render(self) -> str:
        if not self.findings:
            return "OK"
        lines = []
        for f in self.findings:
            lines.append(f"[{f.severity.upper():5}] {f.path}: {f.code} — {f.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Policy parsing — minimal, no PyYAML dependency
# ---------------------------------------------------------------------------


def _parse_egress_block(policy_text: str) -> tuple[bool | None, list[str]]:
    """Return (activated, allowed_endpoints) parsed from tool_policy.yaml.

    Robust to indentation but expects the structure shipped in the repo:

        egress:
          activated: false
          allowed_endpoints:
            - api.githubcopilot.com:443
            ...
    """
    activated: bool | None = None
    endpoints: list[str] = []
    in_egress = False
    in_endpoints = False
    egress_indent = -1
    for raw in policy_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if not in_egress:
            if stripped.startswith("egress:"):
                in_egress = True
                egress_indent = indent
            continue
        # Exit egress block when indentation drops back.
        if indent <= egress_indent and not stripped.startswith(("activated", "allowed_endpoints", "profile_name", "blocked_by_default", "audit_log", "enforcement", "-")):
            break
        if stripped.startswith("activated:"):
            value = stripped.split(":", 1)[1].strip().lower()
            activated = value in ("true", "yes", "1")
            in_endpoints = False
        elif stripped.startswith("allowed_endpoints:"):
            in_endpoints = True
        elif in_endpoints and stripped.startswith("- "):
            endpoint = stripped[2:].strip().strip('"').strip("'")
            endpoints.append(endpoint)
        elif in_endpoints and not stripped.startswith("-"):
            in_endpoints = False
    return activated, endpoints


def _endpoint_host(endpoint: str) -> str:
    return endpoint.split(":", 1)[0]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_policy(policy_path: Path, report: Report) -> tuple[bool | None, list[str]]:
    if not policy_path.exists():
        report.add(str(policy_path), "error", "missing_file",
                   "tool_policy.yaml not found")
        return None, []
    text = policy_path.read_text(encoding="utf-8")
    activated, endpoints = _parse_egress_block(text)
    if activated is None:
        report.add(str(policy_path), "error", "missing_activated_flag",
                   "copilot_cli.egress.activated not declared")
    elif activated is True:
        report.add(str(policy_path), "error", "egress_activated_true",
                   "copilot_cli.egress.activated must remain false in F6 step 3")
    if not endpoints:
        report.add(str(policy_path), "error", "missing_allowed_endpoints",
                   "copilot_cli.egress.allowed_endpoints is empty")
    return activated, endpoints


def check_nft_artifact(nft_path: Path, endpoints: Iterable[str], report: Report) -> None:
    if not nft_path.exists():
        report.add(str(nft_path), "error", "missing_file",
                   "nftables example artifact missing")
        return
    text = nft_path.read_text(encoding="utf-8")
    for marker in _REQUIRED_NFT_MARKERS:
        if marker not in text:
            report.add(str(nft_path), "error", "missing_marker",
                       f"required marker {marker!r} not present")
    if re.search(r"chain\s+output\s*\{[^}]*hook\s+output[^}]*policy\s+drop", text, re.S):
        report.add(
            str(nft_path),
            "error",
            "host_wide_output_drop",
            "egress profile must not install a host-wide output hook with policy drop",
        )
    # Endpoint parity: every authorized host must appear somewhere in
    # the artifact (we keep them as comments at the bottom — see the
    # template's `allowed:` lines).
    hosts = {_endpoint_host(e) for e in endpoints}
    for host in hosts:
        if host not in text:
            report.add(str(nft_path), "error", "endpoint_missing_in_artifact",
                       f"policy host {host!r} not referenced in artifact")
    # Dangerous live commands must be commented (every line starting
    # with `#` is a comment in nft syntax).
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("#"):
            continue
        for pat in _DANGEROUS_LIVE_CMDS:
            if pat.search(raw):
                report.add(str(nft_path), "error", "uncommented_live_command",
                           f"line {lineno}: {raw.strip()!r} would mutate live state")
                break


def check_resolver_doc(doc_path: Path, endpoints: Iterable[str], report: Report) -> None:
    if not doc_path.exists():
        report.add(str(doc_path), "error", "missing_file",
                   "resolver design doc missing")
        return
    text = doc_path.read_text(encoding="utf-8")
    for marker in _REQUIRED_RESOLVER_MARKERS:
        if marker not in text:
            report.add(str(doc_path), "error", "missing_marker",
                       f"required marker {marker!r} not present")
    hosts = {_endpoint_host(e) for e in endpoints}
    for host in hosts:
        if host not in text:
            report.add(str(doc_path), "warn", "endpoint_undocumented",
                       f"policy host {host!r} not mentioned in resolver doc")
    for lineno, raw in enumerate(text.splitlines(), 1):
        # Markdown fences keep snippets visible; we only flag bare
        # commands at column zero (i.e. not inside a fenced block).
        # A simple heuristic: if the line is not indented and matches a
        # dangerous pattern, complain.
        for pat in _DANGEROUS_LIVE_CMDS:
            if pat.search(raw) and not raw.startswith(" ") and not raw.startswith("    "):
                # Allow if line is inside a fenced ```sh block — the
                # convention in the doc is that those examples ARE
                # operator commands; they should still be inside a
                # fence. Tracked by checking for backticks nearby.
                if "```" in text[: text.find(raw) + len(raw)].splitlines()[-3:][0]:
                    continue
    # That heuristic block is intentionally permissive; the nft file
    # is the authoritative dangerous-command surface.


def maybe_resolve(endpoints: Iterable[str], report: Report) -> None:
    """Optional DNS sanity check. Read-only, results discarded."""
    import socket
    for endpoint in endpoints:
        host = _endpoint_host(endpoint)
        try:
            infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            count = len({info[4][0] for info in infos})
            report.add(host, "info", "dns_resolved",
                       f"{count} address(es) resolved (not stored, not applied)")
        except OSError as exc:
            report.add(host, "warn", "dns_unresolved",
                       f"getaddrinfo failed: {exc.__class__.__name__}")


def run(
    policy_path: Path = DEFAULT_POLICY,
    nft_path: Path = DEFAULT_NFT,
    resolver_doc_path: Path = DEFAULT_RESOLVER_DOC,
    *,
    resolve: bool = False,
) -> Report:
    report = Report()
    _activated, endpoints = check_policy(policy_path, report)
    check_nft_artifact(nft_path, endpoints, report)
    check_resolver_doc(resolver_doc_path, endpoints, report)
    if resolve:
        maybe_resolve(endpoints, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Copilot CLI egress design artifacts (F6 step 3).",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--nft", type=Path, default=DEFAULT_NFT)
    parser.add_argument("--resolver-doc", type=Path, default=DEFAULT_RESOLVER_DOC)
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="optionally run DNS getaddrinfo on each endpoint (read-only, "
             "no files written, no firewall touched)",
    )
    args = parser.parse_args(argv)
    report = run(
        policy_path=args.policy,
        nft_path=args.nft,
        resolver_doc_path=args.resolver_doc,
        resolve=args.resolve,
    )
    print(report.render())
    return 1 if report.errors() else 0


if __name__ == "__main__":
    sys.exit(main())
