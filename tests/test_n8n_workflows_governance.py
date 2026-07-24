"""Governance guard for exported n8n workflows (ADR-011 anti-patterns #1/#3/#6).

Runs on every ``infra/n8n/workflows/*.json`` so a PR that re-introduces a Notion
write node, the native Notion polling trigger, or an embedded credential secret
fails CI — the "grep en CI ... rechazo automatico en PR" that
docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md (Riesgos table) and
docs/ops/n8n-notion-integration-proposal-post-smoke-2026-07-24.md (§4.3) require.

Scope: these are the *permanent* invariants for any exported edge workflow. The
"ships INACTIVE until GO David" state of this pack is a point-in-time fact
tracked in the runbook, not asserted here (a future export of an activated
workflow will legitimately carry ``active: true``).
"""
import json
from pathlib import Path

import pytest

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / "infra" / "n8n" / "workflows"

# ADR-011 #1/#3 + proposal §4.3/§4.4: n8n never writes Notion, and the native
# Notion polling trigger is banned in production (duplicates the core poller).
_FORBIDDEN_NODE_TYPES = {
    "n8n-nodes-base.notion",         # Notion action node (write ops) — anti-pattern #1
    "n8n-nodes-base.notionTool",     # same node exposed as an AI-agent tool — §4.3
    "n8n-nodes-base.notionTrigger",  # native polling trigger — §4.4
}

# Credential refs may only carry id + name (reference by name, ADR-011 #6). A
# real secret would surface as one of these inline keys anywhere in the JSON.
_SECRET_KEYS = {
    "access_token", "accessToken", "token", "apiKey", "api_key", "password",
    "secret", "clientSecret", "oauthTokenData", "sessionToken",
}


def _workflow_files():
    return sorted(WORKFLOWS_DIR.glob("*.json"))


def test_workflows_dir_exists_and_nonempty():
    assert WORKFLOWS_DIR.is_dir(), f"missing {WORKFLOWS_DIR}"
    assert _workflow_files(), "no exported workflows found under infra/n8n/workflows/"


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
class TestWorkflowGovernance:
    def _load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_valid_structure(self, path):
        wf = self._load(path)
        assert isinstance(wf.get("nodes"), list) and wf["nodes"], "nodes must be a non-empty list"
        assert isinstance(wf.get("connections"), dict), "connections must be an object"
        assert "active" in wf, "workflow must declare 'active'"

    def test_no_forbidden_notion_nodes(self, path):
        wf = self._load(path)
        types = [n.get("type") for n in wf["nodes"]]
        bad = _FORBIDDEN_NODE_TYPES.intersection(types)
        assert not bad, f"{path.name}: forbidden node(s) {sorted(bad)} — ADR-011 #1/#3, proposal §4"

    def test_credentials_referenced_by_name_only(self, path):
        wf = self._load(path)
        for node in wf["nodes"]:
            creds = node.get("credentials") or {}
            for cred_type, ref in creds.items():
                assert isinstance(ref, dict), f"{node['name']}.{cred_type}: credential must be an object"
                extra = set(ref.keys()) - {"id", "name"}
                assert not extra, f"{node['name']}.{cred_type}: only id+name allowed, got extra {extra}"
                assert ref.get("name"), f"{node['name']}.{cred_type}: credential 'name' is required (ADR-011 #6)"

    def test_no_embedded_secret_values(self, path):
        wf = self._load(path)
        found = []

        def walk(obj, trail=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in _SECRET_KEYS and isinstance(value, str) and value.strip():
                        found.append(f"{trail}.{key}")
                    walk(value, f"{trail}.{key}")
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    walk(value, f"{trail}[{i}]")

        walk(wf)
        assert not found, f"{path.name}: possible embedded secret key(s) {found} — ADR-011 #6"
