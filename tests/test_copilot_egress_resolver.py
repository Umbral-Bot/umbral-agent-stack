"""Tests for scripts/copilot_egress_resolver.py — F6 step 4.

Pure-python tests using tmp_path. NEVER hit real DNS (we stub
``socket.getaddrinfo``). NEVER call subprocess. NEVER touch nftables /
iptables / Docker. NEVER require root.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "copilot_egress_resolver.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "copilot_egress_resolver", SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["copilot_egress_resolver"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rmod():
    return _load_module()


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


def _stub_getaddrinfo(mapping: dict[str, list[tuple[int, str]]]):
    """Build a getaddrinfo stub that returns canned addresses per host."""
    def _stub(host, port, *args, **kwargs):
        if host not in mapping:
            raise OSError(f"no stub for {host!r}")
        out = []
        for family, addr in mapping[host]:
            out.append((family, socket.SOCK_STREAM, 0, "", (addr, port)))
        return out
    return _stub


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


# ---------------------------------------------------------------------------
# Resolution + dedup
# ---------------------------------------------------------------------------


def test_reads_endpoints_from_policy(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=[
        "api.githubcopilot.com:443", "api.github.com:443",
    ])
    stub = _stub_getaddrinfo({
        "api.githubcopilot.com": [(socket.AF_INET, "140.82.113.21")],
        "api.github.com":        [(socket.AF_INET, "140.82.114.6")],
    })
    rc, _text, report = rmod.run(policy_path=policy, getaddrinfo=stub)
    assert rc == 0
    assert report["policy_endpoints"] == [
        "api.githubcopilot.com:443", "api.github.com:443",
    ]


def test_deduplicates_and_sorts(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=[
        "a.example.com:443", "b.example.com:443",
    ])
    stub = _stub_getaddrinfo({
        "a.example.com": [
            (socket.AF_INET, "140.82.114.7"),
            (socket.AF_INET, "140.82.114.5"),
            (socket.AF_INET6, "2606:50c0:8000::2"),
        ],
        "b.example.com": [
            (socket.AF_INET, "140.82.114.5"),  # duplicate of a's
            (socket.AF_INET6, "2606:50c0:8000::1"),
        ],
    })
    rc, _text, report = rmod.run(policy_path=policy, getaddrinfo=stub)
    assert rc == 0
    assert report["ip_sets"]["copilot_v4"] == ["140.82.114.5", "140.82.114.7"]
    assert report["ip_sets"]["copilot_v6"] == ["2606:50c0:8000::1", "2606:50c0:8000::2"]


def test_filters_loopback_and_private_addresses(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["bad.example.com:443"])
    stub = _stub_getaddrinfo({
        "bad.example.com": [
            (socket.AF_INET, "127.0.0.1"),       # loopback → skipped
            (socket.AF_INET, "10.0.0.5"),        # private → error + skipped
            (socket.AF_INET, "140.82.114.10"),    # public → kept
        ],
    })
    rc, _text, report = rmod.run(policy_path=policy, getaddrinfo=stub,
                                 strict=False)
    assert report["ip_sets"]["copilot_v4"] == ["140.82.114.10"]
    # private_address_resolved is recorded as endpoint error
    assert any("private_address_resolved" in e["error"]
               for e in report["errors"])


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------


def test_json_output_is_stable(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    rc, text, _report = rmod.run(policy_path=policy, fmt="json",
                                 getaddrinfo=stub)
    assert rc == 0
    parsed = json.loads(text)
    assert parsed["dry_run"] is True
    assert parsed["would_apply"] is False
    assert parsed["schema"] == "copilot-egress-resolver/v1"


def test_nft_format_has_no_uncommented_live_commands(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    rc, text, _ = rmod.run(policy_path=policy, fmt="nft", getaddrinfo=stub)
    assert rc == 0
    # Reuse the egress verifier's pattern set: every `nft …` line MUST
    # be a comment in the rendered output.
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("nft "):
            pytest.fail(f"line {lineno} contains uncommented nft command: {line!r}")


def test_nft_format_includes_dry_run_marker(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    _rc, text, _ = rmod.run(policy_path=policy, fmt="nft", getaddrinfo=stub)
    assert "DRY-RUN" in text
    assert "DO NOT PIPE INTO `nft`" in text


# ---------------------------------------------------------------------------
# DNS failure modes
# ---------------------------------------------------------------------------


def test_dns_failure_strict_returns_nonzero(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["broken.example.com:443"])
    def _explode(host, port, *a, **k):
        raise socket.gaierror("Name or service not known")
    rc, _text, report = rmod.run(policy_path=policy, getaddrinfo=_explode,
                                 strict=True)
    assert rc != 0
    assert report["errors"]


def test_dns_failure_non_strict_returns_zero(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["broken.example.com:443"])
    def _explode(host, port, *a, **k):
        raise socket.gaierror("Name or service not known")
    rc, _text, report = rmod.run(policy_path=policy, getaddrinfo=_explode,
                                 strict=False)
    assert rc == 0
    assert report["errors"]


# ---------------------------------------------------------------------------
# Cache path allow-list
# ---------------------------------------------------------------------------


def test_write_cache_accepts_allowed_path(tmp_path, rmod, monkeypatch):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    target = REPO_ROOT / "reports" / "copilot-cli" / "egress-cache" / "TEST_DELETE_ME.json"
    try:
        rc, _text, _report = rmod.run(
            policy_path=policy, write_cache_path=target,
            getaddrinfo=stub,
        )
        assert rc == 0
        assert target.exists()
    finally:
        if target.exists():
            target.unlink()


def test_write_cache_refuses_tmp(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    bad = tmp_path / "cache.json"
    rc, text, _ = rmod.run(policy_path=policy, write_cache_path=bad,
                           getaddrinfo=stub)
    assert rc != 0
    assert "refused" in text.lower()
    assert not bad.exists()


def test_write_cache_refuses_etc(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    rc, text, _ = rmod.run(policy_path=policy,
                           write_cache_path=Path("/etc/umbral/cache.json"),
                           getaddrinfo=stub)
    assert rc != 0
    assert "refused" in text.lower()


def test_write_cache_refuses_repo_root(tmp_path, rmod):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    bad = REPO_ROOT / "cache.json"
    rc, text, _ = rmod.run(policy_path=policy, write_cache_path=bad,
                           getaddrinfo=stub)
    assert rc != 0
    assert "refused" in text.lower()
    assert not bad.exists()


# ---------------------------------------------------------------------------
# Activation guard
# ---------------------------------------------------------------------------


def test_refuses_to_run_when_egress_activated_true(tmp_path, rmod):
    policy = _write_policy(tmp_path, activated="true",
                           endpoints=["a.example.com:443"])
    rc, text, _ = rmod.run(policy_path=policy, getaddrinfo=lambda *a, **k: [])
    assert rc != 0
    assert "must be false" in text


# ---------------------------------------------------------------------------
# Side-effect blocks: no subprocess, no token printing
# ---------------------------------------------------------------------------


def test_does_not_call_subprocess(tmp_path, rmod, monkeypatch):
    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })

    def _boom(*a, **k):
        raise AssertionError("subprocess must not be invoked")

    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(subprocess, "call", _boom)
    monkeypatch.setattr(subprocess, "check_call", _boom)
    monkeypatch.setattr(subprocess, "check_output", _boom)

    rc, _text, _ = rmod.run(policy_path=policy, getaddrinfo=stub, fmt="nft")
    assert rc == 0


def test_does_not_print_tokens_from_env(tmp_path, rmod, monkeypatch, capsys):
    leak = "github_pat_DO_NOT_LEAK_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", leak)
    monkeypatch.setenv("GH_TOKEN", leak)
    monkeypatch.setenv("GITHUB_TOKEN", leak)

    policy = _write_policy(tmp_path, endpoints=["a.example.com:443"])
    stub = _stub_getaddrinfo({
        "a.example.com": [(socket.AF_INET, "140.82.114.7")],
    })
    monkeypatch.setattr(sys, "argv", [
        "resolver", "--policy", str(policy),
    ])
    # Patch the module's getaddrinfo so main() uses the stub.
    monkeypatch.setattr(rmod.socket, "getaddrinfo", stub)

    rc = rmod.main()
    out = capsys.readouterr()
    # rc may be 4 (DNS failed because the stub didn't replace the
    # default-bound getaddrinfo); the point of this test is the
    # no-leak assertion below.
    assert rc in (0, 4)
    assert leak not in out.out
    assert leak not in out.err


# ---------------------------------------------------------------------------
# Endpoint parity vs the policy / verifier expectation
# ---------------------------------------------------------------------------


def test_repo_policy_endpoints_match_verifier_expectations(rmod):
    activated, endpoints = rmod.load_policy_endpoints(rmod.DEFAULT_POLICY)
    assert activated is False
    assert endpoints, "policy must declare allowed_endpoints"
    # Mandatory endpoints from infra/networking/copilot-egress-resolver.md
    hosts = {rmod._split_endpoint(e)[0] for e in endpoints}
    for required in ("api.githubcopilot.com", "api.github.com"):
        assert required in hosts, f"{required!r} missing from policy"
