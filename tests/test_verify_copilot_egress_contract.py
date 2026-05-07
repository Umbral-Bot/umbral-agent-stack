"""Tests for scripts/verify_copilot_egress_contract.py — F6 step 3.

Pure-python tests using tmp_path. NEVER touch nftables / iptables /
Docker. NEVER require root. NEVER write to ~/.openclaw or /etc/.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "verify_copilot_egress_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_copilot_egress_contract", SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_copilot_egress_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vmod():
    return _load_module()


# ---------------------------------------------------------------------------
# Helpers — minimal valid artifacts
# ---------------------------------------------------------------------------


def _write_policy(tmp_path: Path, *, activated: str = "false",
                  endpoints: list[str] | None = None) -> Path:
    if endpoints is None:
        endpoints = ["api.githubcopilot.com:443", "api.github.com:443"]
    body = "copilot_cli:\n  egress:\n    activated: " + activated + "\n"
    body += "    allowed_endpoints:\n"
    for e in endpoints:
        body += f"      - {e}\n"
    p = tmp_path / "tool_policy.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def _write_nft(tmp_path: Path, hosts: list[str], *,
               include_default_deny: bool = True,
               include_warning: bool = True,
               extra: str = "") -> Path:
    parts = []
    if include_warning:
        parts.append("# DO NOT APPLY IN F6 STEP 3")
    parts.append('define copilot_bridge = "br-copilot"')
    parts.append("table inet copilot_egress {")
    parts.append("    chain forward {")
    parts.append("        type filter hook forward priority filter; policy accept;")
    parts.append("        iifname != $copilot_bridge accept")
    if include_default_deny:
        parts.append("        counter drop")
    parts.append("    }")
    parts.append("}")
    for h in hosts:
        parts.append(f"#   allowed: {h}")
    if extra:
        parts.append(extra)
    p = tmp_path / "copilot-egress.nft.example"
    p.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return p


def _write_resolver_doc(tmp_path: Path, hosts: list[str]) -> Path:
    body = "# Resolver — DESIGN ONLY\n\n## rollback\n\nsome rollback.\n\n"
    for h in hosts:
        body += f"- {h}\n"
    p = tmp_path / "copilot-egress-resolver.md"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_repo_artifacts_pass(vmod):
    report = vmod.run()
    assert report.errors() == [], report.render()


def test_synthetic_minimal_artifacts_pass(tmp_path, vmod):
    hosts = ["api.githubcopilot.com", "api.github.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts)
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    assert report.errors() == [], report.render()


# ---------------------------------------------------------------------------
# Activation gating
# ---------------------------------------------------------------------------


def test_fails_when_activated_true(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, activated="true",
                           endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts)
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    assert "egress_activated_true" in codes


# ---------------------------------------------------------------------------
# Required markers in nft artifact
# ---------------------------------------------------------------------------


def test_fails_when_default_deny_missing(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts, include_default_deny=False)
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    assert "missing_marker" in codes


def test_fails_when_host_wide_output_drop_present(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(
        tmp_path,
        hosts,
        extra="chain output { type filter hook output priority 0; policy drop; }",
    )
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    assert "host_wide_output_drop" in codes


def test_fails_when_apply_warning_missing(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts, include_warning=False)
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    msgs = " ".join(f.message for f in report.errors())
    assert "missing_marker" in codes
    assert "DO NOT APPLY" in msgs


# ---------------------------------------------------------------------------
# Endpoint parity
# ---------------------------------------------------------------------------


def test_fails_when_policy_endpoint_missing_in_artifact(tmp_path, vmod):
    policy_hosts = ["api.githubcopilot.com", "api.github.com"]
    artifact_hosts = ["api.githubcopilot.com"]  # missing api.github.com
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in policy_hosts])
    nft = _write_nft(tmp_path, artifact_hosts)
    doc = _write_resolver_doc(tmp_path, policy_hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    assert "endpoint_missing_in_artifact" in codes


# ---------------------------------------------------------------------------
# Dangerous live commands
# ---------------------------------------------------------------------------


def test_uncommented_live_command_in_artifact_fails(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts,
                     extra="nft add element inet copilot_egress copilot_v4 { 1.2.3.4 }")
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    codes = {f.code for f in report.errors()}
    assert "uncommented_live_command" in codes


def test_commented_live_command_is_ok(tmp_path, vmod):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts,
                     extra="# nft add element inet copilot_egress copilot_v4 { 1.2.3.4 }")
    doc = _write_resolver_doc(tmp_path, hosts)
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    assert report.errors() == [], report.render()


# ---------------------------------------------------------------------------
# Resolver flag is read-only and does not require root
# ---------------------------------------------------------------------------


def test_resolve_flag_does_not_write_files(tmp_path, vmod, monkeypatch):
    """--resolve must not create or mutate any file on disk."""
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts)
    doc = _write_resolver_doc(tmp_path, hosts)

    # Stub getaddrinfo so the test does not depend on the network.
    import socket
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.1", 443))],
    )

    snapshot = sorted(p.name for p in tmp_path.iterdir())
    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc,
                      resolve=True)
    after = sorted(p.name for p in tmp_path.iterdir())
    assert snapshot == after  # no new files
    assert report.errors() == [], report.render()
    assert any(f.code == "dns_resolved" for f in report.findings)


def test_default_run_does_not_resolve_dns(tmp_path, vmod, monkeypatch):
    hosts = ["api.githubcopilot.com"]
    policy = _write_policy(tmp_path, endpoints=[h + ":443" for h in hosts])
    nft = _write_nft(tmp_path, hosts)
    doc = _write_resolver_doc(tmp_path, hosts)

    import socket
    def explode(*a, **k):
        raise AssertionError("DNS must not be queried without --resolve")
    monkeypatch.setattr(socket, "getaddrinfo", explode)

    report = vmod.run(policy_path=policy, nft_path=nft, resolver_doc_path=doc)
    assert report.errors() == [], report.render()


# ---------------------------------------------------------------------------
# Repo-shipped policy / config still says activated=false
# ---------------------------------------------------------------------------


def test_shipped_policy_egress_still_disabled(vmod):
    report = vmod.run()
    codes = {f.code for f in report.errors()}
    assert "egress_activated_true" not in codes


def test_main_returns_zero_for_repo(vmod, capsys):
    rc = vmod.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out or "INFO" in out
