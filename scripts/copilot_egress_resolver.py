#!/usr/bin/env python3
"""copilot_egress_resolver.py — F6 step 4 (DRY-RUN ONLY).

Resolves the endpoints declared in
``config/tool_policy.yaml :: copilot_cli.egress.allowed_endpoints``
and prints the IP-set diff that *would* be applied to the
``copilot_v4`` / ``copilot_v6`` named sets defined in
``infra/networking/copilot-egress.nft.example``.

This script intentionally does NOT:
  - call ``nft`` / ``iptables`` / ``ip6tables`` / ``ufw``
  - create or modify any Docker network
  - flip ``copilot_cli.egress.activated``
  - read tokens or any GitHub credential
  - require root
  - write outside an allow-listed cache directory

Design reference: ``infra/networking/copilot-egress-resolver.md``.
"""

from __future__ import annotations

import argparse
import dataclasses
import ipaddress
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO_ROOT / "config" / "tool_policy.yaml"
GITHUB_META_URL = "https://api.github.com/meta"
GITHUB_META_KEYS = ("api", "web", "copilot_api")

# Cache writes are only allowed under these prefixes (relative to repo
# root). Both are gitignored from F4. Any other --write-cache target is
# refused.
_ALLOWED_CACHE_PREFIXES = (
    REPO_ROOT / "reports" / "copilot-cli" / "egress-cache",
    REPO_ROOT / "artifacts" / "copilot-cli" / "egress-cache",
)


# ---------------------------------------------------------------------------
# Policy parsing — minimal, no PyYAML dep (mirrors the verifier)
# ---------------------------------------------------------------------------


def _parse_egress_block(policy_text: str) -> tuple[bool | None, list[str]]:
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
        if indent <= egress_indent and not stripped.startswith((
            "activated", "allowed_endpoints", "profile_name",
            "blocked_by_default", "audit_log", "enforcement", "-",
        )):
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


def _split_endpoint(endpoint: str) -> tuple[str, int]:
    if ":" in endpoint:
        host, port = endpoint.rsplit(":", 1)
        return host, int(port)
    return endpoint, 443


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class EndpointResult:
    endpoint: str
    host: str
    port: int
    v4: list[str]
    v6: list[str]
    error: str | None = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def resolve_endpoint(endpoint: str, *, getaddrinfo=socket.getaddrinfo) -> EndpointResult:
    host, port = _split_endpoint(endpoint)
    v4: set[str] = set()
    v6: set[str] = set()
    error: str | None = None
    try:
        infos = getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        return EndpointResult(endpoint, host, port, [], [], error=f"{exc.__class__.__name__}: {exc}")
    for info in infos:
        family, _stype, _proto, _cname, sockaddr = info
        addr = sockaddr[0]
        try:
            obj = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if obj.is_loopback or obj.is_link_local or obj.is_multicast or obj.is_unspecified:
            continue
        if obj.is_private:
            # Public Copilot endpoints must never resolve to RFC1918.
            error = "private_address_resolved"
            continue
        if family == socket.AF_INET6:
            v6.add(str(obj))
        else:
            v4.add(str(obj))
    return EndpointResult(endpoint, host, port, sorted(v4), sorted(v6), error=error)


# ---------------------------------------------------------------------------
# GitHub Meta CIDR expansion
# ---------------------------------------------------------------------------


def _is_public_network(obj: ipaddress._BaseNetwork) -> bool:
    return not (
        obj.is_loopback
        or obj.is_link_local
        or obj.is_multicast
        or obj.is_unspecified
        or obj.is_private
    )


def _ip_sort_key(value: str) -> tuple[int, int, int]:
    network = ipaddress.ip_network(value, strict=False)
    return (network.version, int(network.network_address), network.prefixlen)


def _dedupe_overlapping_values(values: set[str]) -> list[str]:
    """Sort nft elements and remove IPs/subnets covered by broader CIDRs."""
    raw_ips: list[tuple[str, ipaddress._BaseAddress]] = []
    cidrs: list[tuple[str, ipaddress._BaseNetwork]] = []

    for value in values:
        if "/" in value:
            cidrs.append((value, ipaddress.ip_network(value, strict=False)))
        else:
            raw_ips.append((value, ipaddress.ip_address(value)))

    kept_cidrs: list[tuple[str, ipaddress._BaseNetwork]] = []
    for value, network in cidrs:
        covered = any(
            network.version == other.version
            and network != other
            and network.subnet_of(other)
            for _other_value, other in cidrs
        )
        if not covered:
            kept_cidrs.append((value, network))

    kept_raw = [
        value
        for value, address in raw_ips
        if not any(
            address.version == network.version and address in network
            for _cidr_value, network in kept_cidrs
        )
    ]
    return sorted(set(kept_raw).union(value for value, _network in kept_cidrs),
                  key=_ip_sort_key)


def fetch_github_meta(*, urlopen=urllib.request.urlopen) -> dict:
    """Fetch GitHub Meta without reading or sending credentials."""
    request = urllib.request.Request(
        GITHUB_META_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "umbral-copilot-egress-resolver",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"github_meta_fetch_failed: {exc}") from exc
    return json.loads(raw.decode("utf-8"))


def _github_meta_networks(meta: dict, *, keys=GITHUB_META_KEYS) -> tuple[list[str], list[str], list[dict]]:
    v4: set[str] = set()
    v6: set[str] = set()
    errors: list[dict] = []

    for key in keys:
        entries = meta.get(key, [])
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            errors.append({"endpoint": f"github_meta.{key}", "error": "not_a_list"})
            continue
        for raw in entries:
            try:
                network = ipaddress.ip_network(str(raw), strict=False)
            except ValueError:
                errors.append({"endpoint": f"github_meta.{key}", "error": f"invalid_cidr:{raw}"})
                continue
            if not _is_public_network(network):
                errors.append({"endpoint": f"github_meta.{key}", "error": f"non_public_cidr:{network}"})
                continue
            if network.version == 6:
                v6.add(str(network))
            else:
                v4.add(str(network))

    return _dedupe_overlapping_values(v4), _dedupe_overlapping_values(v6), errors


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _flatten(results: list[EndpointResult]) -> tuple[list[str], list[str]]:
    v4: set[str] = set()
    v6: set[str] = set()
    for r in results:
        v4.update(r.v4)
        v6.update(r.v6)
    return _dedupe_overlapping_values(v4), _dedupe_overlapping_values(v6)


def build_report(
    endpoints: list[str],
    *,
    getaddrinfo=socket.getaddrinfo,
    include_github_meta: bool = False,
    github_meta: dict | None = None,
    github_meta_fetcher=fetch_github_meta,
) -> dict:
    results = [resolve_endpoint(e, getaddrinfo=getaddrinfo) for e in endpoints]
    v4, v6 = _flatten(results)
    errors = [
        {"endpoint": r.endpoint, "error": r.error}
        for r in results if r.error
    ]
    github_meta_section = {
        "included": include_github_meta,
        "source": GITHUB_META_URL,
        "keys": list(GITHUB_META_KEYS),
        "copilot_v4": [],
        "copilot_v6": [],
        "errors": [],
    }

    if include_github_meta:
        try:
            meta = github_meta if github_meta is not None else github_meta_fetcher()
            meta_v4, meta_v6, meta_errors = _github_meta_networks(meta)
        except Exception as exc:  # noqa: BLE001 - report dry-run diagnostics, don't hide cause.
            meta_v4, meta_v6 = [], []
            meta_errors = [{"endpoint": "github_meta", "error": str(exc)}]
        github_meta_section["copilot_v4"] = meta_v4
        github_meta_section["copilot_v6"] = meta_v6
        github_meta_section["errors"] = meta_errors
        errors.extend(meta_errors)
        v4 = _dedupe_overlapping_values(set(v4).union(meta_v4))
        v6 = _dedupe_overlapping_values(set(v6).union(meta_v6))

    return {
        "schema": "copilot-egress-resolver/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": True,
        "would_apply": False,
        "policy_endpoints": endpoints,
        "endpoints": [r.to_dict() for r in results],
        "ip_sets": {
            "copilot_v4": v4,
            "copilot_v6": v6,
        },
        "github_meta": github_meta_section,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# nft dry-run rendering
# ---------------------------------------------------------------------------


_NFT_BANNER = (
    "# DRY-RUN OUTPUT — DO NOT PIPE INTO `nft`.\n"
    "# Generated by scripts/copilot_egress_resolver.py.\n"
    "# F6 step 4 forbids live application; egress remains DISABLED.\n"
    "# To apply, an operator must explicitly run F6 step 5+ procedures.\n"
)


def render_nft(report: dict) -> str:
    v4 = report["ip_sets"]["copilot_v4"]
    v6 = report["ip_sets"]["copilot_v6"]
    lines = [_NFT_BANNER]
    lines.append(f"# generated_at: {report['generated_at']}")
    lines.append(f"# dry_run: {report['dry_run']}")
    lines.append(f"# would_apply: {report['would_apply']}")
    lines.append("")
    lines.append("# IPv4 set diff (would-be):")
    if v4:
        joined = ", ".join(v4)
        lines.append(f"# nft flush set inet copilot_egress copilot_v4")
        lines.append(f"# nft add element inet copilot_egress copilot_v4 {{ {joined} }}")
    else:
        lines.append("# (no IPv4 addresses resolved)")
    lines.append("")
    lines.append("# IPv6 set diff (would-be):")
    if v6:
        joined = ", ".join(v6)
        lines.append(f"# nft flush set inet copilot_egress copilot_v6")
        lines.append(f"# nft add element inet copilot_egress copilot_v6 {{ {joined} }}")
    else:
        lines.append("# (no IPv6 addresses resolved)")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Cache writing — strict path allow-list
# ---------------------------------------------------------------------------


class CachePathRefused(Exception):
    pass


def _validate_cache_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    for prefix in _ALLOWED_CACHE_PREFIXES:
        try:
            resolved.relative_to(prefix)
        except ValueError:
            continue
        return resolved
    raise CachePathRefused(
        f"refused: --write-cache must live under "
        f"reports/copilot-cli/egress-cache/ or "
        f"artifacts/copilot-cli/egress-cache/, got: {resolved}"
    )


def write_cache(report: dict, path: Path) -> Path:
    target = _validate_cache_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Top-level run helper (for tests)
# ---------------------------------------------------------------------------


def load_policy_endpoints(policy_path: Path) -> tuple[bool | None, list[str]]:
    text = policy_path.read_text(encoding="utf-8")
    return _parse_egress_block(text)


def run(
    *,
    policy_path: Path = DEFAULT_POLICY,
    fmt: str = "json",
    write_cache_path: Path | None = None,
    strict: bool = True,
    getaddrinfo=socket.getaddrinfo,
    include_github_meta: bool = False,
    github_meta: dict | None = None,
    github_meta_fetcher=fetch_github_meta,
) -> tuple[int, str, dict]:
    activated, endpoints = load_policy_endpoints(policy_path)
    if activated is True:
        # Defensive: even though we don't apply, refuse to operate if
        # someone flipped activation while the design is in review.
        return (
            2,
            "ERROR: copilot_cli.egress.activated must be false in F6 step 4.\n",
            {},
        )
    if not endpoints:
        return (2, "ERROR: no allowed_endpoints in policy.\n", {})
    report = build_report(
        endpoints,
        getaddrinfo=getaddrinfo,
        include_github_meta=include_github_meta,
        github_meta=github_meta,
        github_meta_fetcher=github_meta_fetcher,
    )
    if write_cache_path is not None:
        try:
            write_cache(report, write_cache_path)
        except CachePathRefused as exc:
            return (3, f"ERROR: {exc}\n", report)
    if fmt == "nft":
        text = render_nft(report)
    else:
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    rc = 0
    if strict and report["errors"]:
        rc = 4
    return rc, text, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copilot CLI egress resolver — DRY-RUN only.",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                        help="path to tool_policy.yaml")
    parser.add_argument("--format", choices=("json", "nft"), default="json",
                        help="output format (default: json)")
    parser.add_argument("--write-cache", type=Path, default=None,
                        help="optional cache path; must live under "
                             "reports/copilot-cli/egress-cache/ or "
                             "artifacts/copilot-cli/egress-cache/")
    parser.add_argument("--non-strict", action="store_true",
                        help="report DNS errors but exit 0")
    parser.add_argument("--include-github-meta", action="store_true",
                        help="merge public GitHub Meta CIDRs into the dry-run "
                             "IP sets for GitHub load-balanced endpoints")
    args = parser.parse_args(argv)

    rc, text, _ = run(
        policy_path=args.policy,
        fmt=args.format,
        write_cache_path=args.write_cache,
        strict=not args.non_strict,
        include_github_meta=args.include_github_meta,
    )
    sys.stdout.write(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
