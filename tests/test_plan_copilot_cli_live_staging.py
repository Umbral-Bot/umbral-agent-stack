"""Tests for scripts/plan_copilot_cli_live_staging.py — F6 step 6A.

Pure-python tests; never invoke real systemctl. The discovery functions
are exercised by stubbing ``_safe_systemctl`` so the planner can be
verified in CI without root, without a live umbral-worker, and without
touching ``/etc``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests._token_fixtures import fine_grained_pat

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "plan_copilot_cli_live_staging.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "plan_copilot_cli_live_staging", SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["plan_copilot_cli_live_staging"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pmod():
    return _load_module()


# ---------------------------------------------------------------------------
# _safe_systemctl refuses non-read-only verbs
# ---------------------------------------------------------------------------


def test_systemctl_refuses_mutating_verbs(pmod):
    for verb in ("start", "stop", "restart", "enable", "disable",
                 "reload", "daemon-reload", "kill", "mask"):
        with pytest.raises(pmod.PlannerRefused):
            pmod._safe_systemctl([verb, "umbral-worker.service"], user=True)


def test_systemctl_allows_show(pmod, monkeypatch):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        class P: returncode = 0; stdout = "FragmentPath=/x\n"; stderr = ""
        return P()
    monkeypatch.setattr(pmod.subprocess, "run", fake_run)
    rc, out, _ = pmod._safe_systemctl(["show", "u.service", "-p", "FragmentPath"],
                                       user=True)
    assert rc == 0
    assert captured["cmd"][0] == "systemctl"
    assert "--user" in captured["cmd"]
    assert "show" in captured["cmd"]


# ---------------------------------------------------------------------------
# Unit discovery — user vs system vs absent
# ---------------------------------------------------------------------------


def test_discover_unit_user_scope(pmod, monkeypatch):
    user_responses = {
        ("show",): (0,
                    "FragmentPath=/home/rick/.config/systemd/user/umbral-worker.service\n"
                    "DropInPaths=\n"
                    "EnvironmentFiles=/home/rick/.config/openclaw/env (ignore_errors=no)\n",
                    ""),
        ("is-active",): (0, "active\n", ""),
        ("is-enabled",): (0, "enabled\n", ""),
    }
    def fake(args, *, user):
        assert user is True
        return user_responses[(args[0],)]
    monkeypatch.setattr(pmod, "_safe_systemctl", fake)
    info = pmod.discover_unit("umbral-worker.service")
    assert info.scope == "user"
    assert info.fragment_path.endswith("umbral-worker.service")
    assert info.environment_files == ["/home/rick/.config/openclaw/env"]
    assert info.is_active and info.is_enabled


def test_discover_unit_system_scope(pmod, monkeypatch):
    state = {"calls": 0}
    def fake(args, *, user):
        state["calls"] += 1
        if user:
            return 1, "", "Unit not found"
        if args[0] == "show":
            return 0, "FragmentPath=/etc/systemd/system/x.service\nDropInPaths=\nEnvironmentFiles=\n", ""
        return 0, "", ""
    monkeypatch.setattr(pmod, "_safe_systemctl", fake)
    info = pmod.discover_unit("x.service")
    assert info.scope == "system"
    assert info.fragment_path.startswith("/etc/systemd/system/")


def test_discover_unit_absent(pmod, monkeypatch):
    monkeypatch.setattr(pmod, "_safe_systemctl",
                        lambda args, *, user: (1, "", "not found"))
    info = pmod.discover_unit("nope.service")
    assert info.scope == "absent"


# ---------------------------------------------------------------------------
# nftables.conf parsing
# ---------------------------------------------------------------------------


def test_nftables_no_include_means_no_autoload(pmod, tmp_path):
    conf = tmp_path / "nftables.conf"
    conf.write_text(
        "#!/usr/sbin/nft -f\nflush ruleset\ntable inet filter { }\n",
        encoding="utf-8",
    )
    nft = pmod.discover_nftables(conf)
    assert nft.conf_present is True
    assert nft.autoloads_directory is False
    assert nft.autoload_directories == []


def test_nftables_with_include_glob(pmod, tmp_path):
    conf = tmp_path / "nftables.conf"
    conf.write_text(
        '#!/usr/sbin/nft -f\nflush ruleset\ninclude "/etc/nftables.d/*.nft"\n',
        encoding="utf-8",
    )
    nft = pmod.discover_nftables(conf)
    assert nft.autoloads_directory is True
    assert "/etc/nftables.d/*.nft" in nft.autoload_directories


def test_nftables_conf_absent(pmod, tmp_path):
    nft = pmod.discover_nftables(tmp_path / "nope.conf")
    assert nft.conf_present is False


# ---------------------------------------------------------------------------
# Recommended paths per scope
# ---------------------------------------------------------------------------


def test_recommended_paths_user(pmod):
    unit = pmod.UnitInfo(
        scope="user",
        fragment_path="/home/rick/.config/systemd/user/umbral-worker.service",
    )
    paths = pmod.recommended_paths(unit)
    assert paths["scope"] == "user"
    assert paths["dropin_dir"] == "/home/rick/.config/systemd/user/umbral-worker.service.d"
    assert paths["dropin_file"].endswith("/copilot-cli.conf")
    assert paths["envfile_runtime"].startswith("/home/rick/.config/openclaw/")
    assert paths["envfile_secrets"].startswith("/home/rick/.config/openclaw/")
    assert paths["uses_sudo"] == "no"
    assert paths["reload_cmd"] == "systemctl --user daemon-reload"


def test_recommended_paths_system(pmod):
    unit = pmod.UnitInfo(scope="system",
                         fragment_path="/etc/systemd/system/x.service")
    paths = pmod.recommended_paths(unit)
    assert paths["scope"] == "system"
    assert paths["envfile_runtime"].startswith("/etc/umbral/")
    assert paths["uses_sudo"] == "yes"
    assert paths["reload_cmd"] == "sudo systemctl daemon-reload"


def test_recommended_paths_absent(pmod):
    paths = pmod.recommended_paths(pmod.UnitInfo(scope="absent"))
    assert paths["scope"] == "absent"
    assert "note" in paths


# ---------------------------------------------------------------------------
# Install / rollback command rendering
# ---------------------------------------------------------------------------


def test_install_commands_marked_manual_only_user(pmod):
    unit = pmod.UnitInfo(
        scope="user",
        fragment_path="/home/rick/.config/systemd/user/umbral-worker.service",
    )
    cmds = pmod.render_install_commands(pmod.recommended_paths(unit))
    # Every non-comment line that resembles a system call must NOT be live.
    assert any("manual_only" in c for c in cmds)
    # No sudo for user-scope.
    assert not any(c.startswith("sudo ") for c in cmds)
    # Must NOT restart the worker.
    assert not any("restart umbral-worker" in c and not c.lstrip().startswith("#")
                   for c in cmds)


def test_install_commands_marked_manual_only_system(pmod):
    unit = pmod.UnitInfo(scope="system",
                         fragment_path="/etc/systemd/system/x.service")
    cmds = pmod.render_install_commands(pmod.recommended_paths(unit))
    assert any("manual_only" in c for c in cmds)
    # System scope uses sudo.
    assert any(c.startswith("sudo ") for c in cmds)


def test_rollback_commands_marked_manual_only(pmod):
    for scope, frag in [
        ("user", "/home/rick/.config/systemd/user/umbral-worker.service"),
        ("system", "/etc/systemd/system/x.service"),
    ]:
        unit = pmod.UnitInfo(scope=scope, fragment_path=frag)
        cmds = pmod.render_rollback_commands(pmod.recommended_paths(unit))
        assert any("manual_only" in c for c in cmds)


# ---------------------------------------------------------------------------
# Cache writing — strict path allow-list
# ---------------------------------------------------------------------------


def test_write_report_refuses_outside_allowlist(pmod, tmp_path):
    plan = {"schema": "test", "dry_run": True}
    with pytest.raises(pmod.PlannerRefused):
        pmod.write_report(plan, tmp_path / "out.json")
    with pytest.raises(pmod.PlannerRefused):
        pmod.write_report(plan, Path("/etc/copilot-cli-plan.json"))


def test_write_report_accepts_reports_path(pmod):
    plan = {"schema": "test", "dry_run": True}
    target = REPO_ROOT / "reports" / "copilot-cli" / "TEST_PLAN_DELETE_ME.json"
    try:
        out = pmod.write_report(plan, target)
        assert out.exists()
        assert json.loads(out.read_text(encoding="utf-8"))["schema"] == "test"
    finally:
        if target.exists():
            target.unlink()


# ---------------------------------------------------------------------------
# End-to-end build_plan — guards present, no live mutations
# ---------------------------------------------------------------------------


def test_build_plan_guards_block_all_mutations(pmod):
    unit = pmod.UnitInfo(
        scope="user",
        fragment_path="/home/rick/.config/systemd/user/umbral-worker.service",
    )
    nft = pmod.NftablesInfo(conf_present=True, conf_path="/etc/nftables.conf",
                            autoloads_directory=False)
    plan = pmod.build_plan(unit, nft)
    assert plan["dry_run"] is True
    assert plan["would_apply"] is False
    g = plan["guards"]
    assert g["uses_sudo_in_planner"] is False
    assert g["writes_to_etc"] is False
    assert g["spawns_nft"] is False
    assert g["spawns_iptables"] is False
    assert g["creates_docker_network"] is False
    assert g["flips_flags"] is False
    assert g["prints_tokens"] is False


def test_main_does_not_print_tokens_from_env(pmod, monkeypatch, capsys):
    leak = fine_grained_pat(body_char="G", body_len=40)
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", leak)
    monkeypatch.setenv("GH_TOKEN", leak)
    monkeypatch.setenv("GITHUB_TOKEN", leak)

    monkeypatch.setattr(pmod, "discover_unit",
                        lambda u: pmod.UnitInfo(scope="absent"))
    monkeypatch.setattr(pmod, "discover_nftables",
                        lambda *a, **kw: pmod.NftablesInfo(False, "x", False))
    monkeypatch.setattr(sys, "argv", ["planner"])
    rc = pmod.main()
    out = capsys.readouterr()
    assert rc == 0
    assert leak not in out.out
    assert leak not in out.err
