#!/usr/bin/env bash
# tournament-preflight-dry-run.sh — D2.2 Mega 1
# Runs pre-flight checks from docs/79 §5 + G-D1b without sessions_spawn.
# Usage: ./scripts/openclaw/tournament-preflight-dry-run.sh [path/to/spec.yaml]
set -euo pipefail

SPEC="${1:-}"
OPENCLAW_JSON="${OPENCLAW_JSON:-$HOME/.openclaw/openclaw.json}"
REPO_PATH="${REPO_PATH:-$HOME/umbral-agent-stack}"

pass=0
fail=0
warn=0

ok()   { echo "  OK  $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL $1"; fail=$((fail + 1)); }
note() { echo "  WARN $1"; warn=$((warn + 1)); }

echo "=== Tournament pre-flight dry-run (D2.2) ==="
echo "openclaw.json: $OPENCLAW_JSON"
echo "repo_path:     $REPO_PATH"
echo ""

# 1 maxSpawnDepth
if [[ -f "$OPENCLAW_JSON" ]]; then
  depth="$(jq -r '.agents.defaults.subagents.maxSpawnDepth // 1' "$OPENCLAW_JSON" 2>/dev/null || echo 1)"
  if [[ "$depth" -ge 2 ]]; then
    ok "maxSpawnDepth=$depth (>= 2)"
  else
    bad "maxSpawnDepth=$depth (need >= 2 — G-D1a)"
  fi
else
  bad "openclaw.json not found at $OPENCLAW_JSON"
fi

# 2 G-D1b — cannot fully verify standalone from shell; instruct operator
note "G-D1b standalone: verify sessions_spawn in main session tool list (ISSUE-001) — manual in Control UI or agent turn"

# 3 git clean + on main
if [[ -d "$REPO_PATH/.git" ]]; then
  if [[ -z "$(git -C "$REPO_PATH" status --porcelain)" ]]; then
    ok "git worktree clean"
  else
    bad "git worktree dirty in $REPO_PATH"
  fi
  branch="$(git -C "$REPO_PATH" rev-parse --abbrev-ref HEAD)"
  if [[ "$branch" == "main" ]]; then
    ok "on branch main"
  else
    note "on branch $branch (expected main for tournament base)"
  fi
  if git -C "$REPO_PATH" fetch origin main 2>/dev/null; then
    if git -C "$REPO_PATH" merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
      ok "main is ancestor of origin/main (ff-ready)"
    else
      bad "main not fast-forward with origin/main"
    fi
  else
    note "could not fetch origin/main (offline or no remote)"
  fi
else
  bad "not a git repo: $REPO_PATH"
fi

# 4 gh auth (required before real tournament PR/merge; David-scoped)
if gh auth status >/dev/null 2>&1; then
  ok "gh auth status green"
else
  note "gh auth status failed — expected until David runs gh auth login (D3.0 gate)"
fi

# 5 gateway health (optional)
if curl -sf "http://127.0.0.1:18789/health" >/dev/null 2>&1; then
  ok "openclaw gateway :18789 health"
else
  note "gateway health not reachable on :18789 (may be OK if different bind)"
fi

# 6 spec validation (if provided)
if [[ -n "$SPEC" ]]; then
  if [[ -f "$SPEC" ]]; then
    ok "spec file exists: $SPEC"
    if command -v yq >/dev/null 2>&1; then
      lane_count="$(yq '.lanes | length' "$SPEC" 2>/dev/null || echo 0)"
      if [[ "$lane_count" -ge 2 && "$lane_count" -le 5 ]]; then
        ok "lane count=$lane_count (2-5)"
      else
        bad "lane count=$lane_count (need 2-5)"
      fi
    else
      note "yq not installed — skip lane count parse"
    fi
  else
    bad "spec file missing: $SPEC"
  fi
else
  note "no spec.yaml passed — skip lane validation"
fi

# 7 skill present in repo template
skill_path="$REPO_PATH/openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/SKILL.md"
if [[ -f "$skill_path" ]]; then
  ok "skill template in repo"
else
  bad "skill template missing: $skill_path"
fi

# 8 plugin umbral-tournament-github (D3.6 Fase 3) — read-only, never mutate live config
if [[ -f "$OPENCLAW_JSON" ]]; then
  plugin_enabled="$(jq -r '.plugins.entries["umbral-tournament-github"].enabled // empty' "$OPENCLAW_JSON" 2>/dev/null || echo "")"
  if [[ "$plugin_enabled" == "true" ]]; then
    ok "plugin umbral-tournament-github enabled in openclaw.json"
  elif [[ -n "$plugin_enabled" ]]; then
    note "plugin umbral-tournament-github present but enabled=$plugin_enabled (deploy pending — D3.6 Fase 3)"
  else
    note "plugin umbral-tournament-github not in openclaw.json (deploy pending — D3.6 Fase 3)"
  fi
else
  note "openclaw.json not found — skip plugin check"
fi

# 9 lane skill tournament-github-cli — repo template (hard) + workspace sync (warn)
repo_lane_skill="$REPO_PATH/openclaw/workspace-templates/skills/tournament-github-cli/SKILL.md"
if [[ -f "$repo_lane_skill" ]]; then
  ok "lane skill template in repo (tournament-github-cli)"
else
  bad "lane skill template missing: $repo_lane_skill"
fi
ws_lane_skill="${WORKSPACE_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}/tournament-github-cli/SKILL.md"
if [[ -f "$ws_lane_skill" ]]; then
  ok "lane skill synced to workspace: $ws_lane_skill"
else
  note "lane skill not synced to workspace ($ws_lane_skill) — rsync before real tournament (D3.6)"
fi

echo ""
echo "=== Summary: OK=$pass FAIL=$fail WARN=$warn ==="
if [[ "$fail" -gt 0 ]]; then
  verdict="BLOCKED"
elif [[ "$warn" -gt 0 ]]; then
  verdict="PARTIAL"
else
  verdict="OK"
fi
echo "PREFLIGHT_VERDICT=$verdict"
if [[ "$fail" -gt 0 ]]; then
  echo "Result: NOT READY for spawn (hard FAIL above)"
  exit 1
fi
echo "Result: DRY-RUN PASSED (spawn still requires G-D1b manual + gh auth + David gate)"
exit 0
