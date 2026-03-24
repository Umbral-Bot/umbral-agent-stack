import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _seed_workspace_root(home: Path, agent_paths: list[str]):
    for relative in agent_paths:
        (home / relative).mkdir(parents=True, exist_ok=True)


def test_governance_source_prefers_agent_override(tmp_path):
    module = _load_script_module(
        "sync_openclaw_workspace_governance_override",
        "scripts/sync_openclaw_workspace_governance.py",
    )
    repo_root = tmp_path / "repo"
    (repo_root / "openclaw" / "workspace-templates").mkdir(parents=True)
    (repo_root / "openclaw" / "workspace-agent-overrides" / "rick-ops").mkdir(parents=True)
    (repo_root / "openclaw" / "workspace-templates" / "HEARTBEAT.md").write_text(
        "template\n", encoding="utf-8"
    )
    override = repo_root / "openclaw" / "workspace-agent-overrides" / "rick-ops" / "HEARTBEAT.md"
    override.write_text("override\n", encoding="utf-8")

    source = module.governance_source_for("rick-ops", "HEARTBEAT.md", repo_root=repo_root)

    assert source == override


def test_build_sync_plan_uses_template_for_main_and_detects_changes(tmp_path):
    module = _load_script_module(
        "sync_openclaw_workspace_governance_plan",
        "scripts/sync_openclaw_workspace_governance.py",
    )
    repo_root = tmp_path / "repo"
    template_dir = repo_root / "openclaw" / "workspace-templates"
    template_dir.mkdir(parents=True)
    overrides_dir = repo_root / "openclaw" / "workspace-agent-overrides" / "rick-ops"
    overrides_dir.mkdir(parents=True)
    (template_dir / "BOOTSTRAP.md").write_text("boot-template\n", encoding="utf-8")
    (template_dir / "HEARTBEAT.md").write_text("main-heartbeat\n", encoding="utf-8")
    (overrides_dir / "HEARTBEAT.md").write_text("ops-heartbeat\n", encoding="utf-8")
    (repo_root / "openclaw" / "workspace-agent-overrides" / "rick-ops" / "BOOTSTRAP.md").write_text(
        "ops-boot\n", encoding="utf-8"
    )

    home = tmp_path / "home"
    _seed_workspace_root(
        home,
        [
            ".openclaw/workspace",
            ".openclaw/workspaces/rick-delivery",
            ".openclaw/workspaces/rick-ops",
            ".openclaw/workspaces/rick-orchestrator",
            ".openclaw/workspaces/rick-qa",
            ".openclaw/workspaces/rick-tracker",
        ],
    )
    (home / ".openclaw/workspace/HEARTBEAT.md").write_text("old-main\n", encoding="utf-8")
    (home / ".openclaw/workspaces/rick-ops/HEARTBEAT.md").write_text(
        "ops-heartbeat\n", encoding="utf-8"
    )

    plan = module.build_sync_plan(repo_root=repo_root, home=home)

    main_heartbeat = next(
        entry for entry in plan if entry.agent_id == "main" and entry.filename == "HEARTBEAT.md"
    )
    ops_heartbeat = next(
        entry
        for entry in plan
        if entry.agent_id == "rick-ops" and entry.filename == "HEARTBEAT.md"
    )

    assert main_heartbeat.content_changed is True
    assert main_heartbeat.source == template_dir / "HEARTBEAT.md"
    assert ops_heartbeat.content_changed is False
    assert ops_heartbeat.source == overrides_dir / "HEARTBEAT.md"


def test_apply_sync_plan_creates_backup_for_modified_targets(tmp_path):
    module = _load_script_module(
        "sync_openclaw_workspace_governance_apply",
        "scripts/sync_openclaw_workspace_governance.py",
    )
    repo_root = tmp_path / "repo"
    template_dir = repo_root / "openclaw" / "workspace-templates"
    template_dir.mkdir(parents=True)
    (template_dir / "BOOTSTRAP.md").write_text("boot\n", encoding="utf-8")
    (template_dir / "HEARTBEAT.md").write_text("heartbeat\n", encoding="utf-8")

    for agent in ["rick-delivery", "rick-ops", "rick-orchestrator", "rick-qa", "rick-tracker"]:
        agent_dir = repo_root / "openclaw" / "workspace-agent-overrides" / agent
        agent_dir.mkdir(parents=True)
        (agent_dir / "BOOTSTRAP.md").write_text("boot\n", encoding="utf-8")
        (agent_dir / "HEARTBEAT.md").write_text(f"{agent}\n", encoding="utf-8")

    home = tmp_path / "home"
    _seed_workspace_root(
        home,
        [
            ".openclaw/workspace",
            ".openclaw/workspaces/rick-delivery",
            ".openclaw/workspaces/rick-ops",
            ".openclaw/workspaces/rick-orchestrator",
            ".openclaw/workspaces/rick-qa",
            ".openclaw/workspaces/rick-tracker",
        ],
    )
    target = home / ".openclaw/workspace/HEARTBEAT.md"
    target.write_text("old\n", encoding="utf-8")

    plan = module.build_sync_plan(repo_root=repo_root, home=home)
    backup_root = module.apply_sync_plan(plan, home=home)

    assert target.read_text(encoding="utf-8") == "heartbeat\n"
    backup_target = backup_root / ".openclaw" / "workspace" / "HEARTBEAT.md"
    assert backup_target.read_text(encoding="utf-8") == "old\n"
