"""
Tests for fake progress detection in Rick's session behavior.

Motivated by live test audit 2026-03-09:
- Rick declared "ya validé" / "ya tengo avance real" without fresh tool calls
- Cron events interrupted active work sessions
- No traceable actions were left after project prompts

References:
  docs/audits/rick-live-test-2026-03-09-detailed.md
  .agents/tasks/2026-03-09-003-rick-claude-recommendations.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


# ── Progress claim keywords (mirror of SOUL.md guardrail) ─────────

PROGRESS_CLAIM_PHRASES = [
    "ya analicé",
    "ya validé",
    "ya empecé",
    "tengo avance real",
    "ya confirmé acceso",
    "ya confirme acceso",
    "ya tengo avance",
    "ya valide",
    "already validated",
    "already started",
    "i already confirmed",
    "already have progress",
]

PROJECT_TRIGGER_PHRASES = [
    "proyecto",
    "project",
    "proyecto-embudo",
    "linear project",
    "paso 1",
    "step 1",
    "analiza mi perfil",
    "ya analizaste",
    "empieza",
]


def _contains_any(text: str, phrases: list[str]) -> bool:
    lower = text.lower()
    return any(p in lower for p in phrases)


def detect_fake_progress_turns(session_turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Scan a list of session turns for assistant turns that:
    - Contain a progress claim phrase
    - Have no tool calls in the same turn

    Args:
        session_turns: List of turn dicts with keys:
            - role: "user" | "assistant"
            - content: str
            - tool_calls: list (may be absent or empty)
            - timestamp: str (ISO, optional)

    Returns:
        List of flagged turns (those with fake progress).
    """
    flagged = []
    for turn in session_turns:
        if turn.get("role") != "assistant":
            continue
        content = turn.get("content", "")
        if not _contains_any(content, PROGRESS_CLAIM_PHRASES):
            continue
        tool_calls = turn.get("tool_calls", [])
        if not tool_calls:
            flagged.append(turn)
    return flagged


def detect_project_turns_without_tool_calls(session_turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Find assistant turns that immediately follow a project-trigger user message
    but contain no tool calls.

    Returns flagged assistant turns.
    """
    flagged = []
    for i, turn in enumerate(session_turns):
        if turn.get("role") != "user":
            continue
        if not _contains_any(turn.get("content", ""), PROJECT_TRIGGER_PHRASES):
            continue
        # Look at the next assistant turn(s) after this trigger
        for j in range(i + 1, min(i + 3, len(session_turns))):
            next_turn = session_turns[j]
            if next_turn.get("role") != "assistant":
                continue
            if not next_turn.get("tool_calls"):
                flagged.append(next_turn)
            break  # Only check the first assistant response
    return flagged


def check_ops_log_activity(
    ops_log_entries: list[dict[str, Any]],
    after_timestamp: str,
    within_seconds: int = 120,
) -> bool:
    """
    Check if the ops log has at least one new entry after a given timestamp.

    Used to verify that Rick actually executed work (not just replied).

    Args:
        ops_log_entries: List of ops log dicts with "timestamp" key (ISO).
        after_timestamp: ISO timestamp to check after.
        within_seconds: Window to check (default 120s).

    Returns:
        True if at least one entry found in the window.
    """
    try:
        after_dt = datetime.fromisoformat(after_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False

    for entry in ops_log_entries:
        ts_str = entry.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        delta = (ts - after_dt).total_seconds()
        if 0 < delta <= within_seconds:
            return True
    return False


# ── Unit tests ────────────────────────────────────────────────────


class TestFakeProgressDetection:
    """Unit tests for the fake progress detector."""

    def test_clean_turn_with_tool_call_not_flagged(self):
        """Assistant turn with tool call + progress claim is NOT fake."""
        turns = [
            {
                "role": "assistant",
                "content": "Ya validé la carpeta del proyecto.",
                "tool_calls": [{"name": "umbral_windows_fs_list", "result": "desktop.ini"}],
            }
        ]
        assert detect_fake_progress_turns(turns) == []

    def test_progress_claim_without_tool_call_is_flagged(self):
        """Assistant claims progress but has no tool calls — fake progress."""
        turns = [
            {
                "role": "assistant",
                "content": "Ya validé Notion y ya confirme acceso a los docs de perfil en la VM.",
                "tool_calls": [],
            }
        ]
        flagged = detect_fake_progress_turns(turns)
        assert len(flagged) == 1
        assert flagged[0]["content"].startswith("Ya validé")

    def test_no_progress_claim_not_flagged(self):
        """Assistant without progress claims is not flagged even without tool calls."""
        turns = [
            {
                "role": "assistant",
                "content": "Entendido. El proyecto se reinicia desde cero con los nuevos parámetros.",
                "tool_calls": [],
            }
        ]
        assert detect_fake_progress_turns(turns) == []

    def test_multiple_turns_only_flags_fake_ones(self):
        turns = [
            {
                "role": "assistant",
                "content": "Entendido, el proyecto se reinicia.",
                "tool_calls": [],
            },
            {
                "role": "assistant",
                "content": "Ya tengo avance real: analicé el perfil y el contexto.",
                "tool_calls": [],
            },
            {
                "role": "assistant",
                "content": "Ya analicé el perfil completo.",
                "tool_calls": [{"name": "umbral_notion_read_page", "result": "..."}],
            },
        ]
        flagged = detect_fake_progress_turns(turns)
        assert len(flagged) == 1
        assert "tengo avance real" in flagged[0]["content"]

    def test_english_claims_also_flagged(self):
        turns = [
            {
                "role": "assistant",
                "content": "I already validated the Notion page and have progress.",
                "tool_calls": [],
            }
        ]
        flagged = detect_fake_progress_turns(turns)
        assert len(flagged) == 1


class TestProjectTriggerDetection:
    """Assistant must make a tool call after a project trigger."""

    def test_project_trigger_with_tool_call_passes(self):
        turns = [
            {"role": "user", "content": "ok, ya analizaste mi perfil o estas en eso?"},
            {
                "role": "assistant",
                "content": "Estoy en eso, leyendo ahora.",
                "tool_calls": [{"name": "umbral_notion_read_page"}],
            },
        ]
        flagged = detect_project_turns_without_tool_calls(turns)
        assert flagged == []

    def test_project_trigger_without_tool_call_flagged(self):
        """Matches the exact failure from the 2026-03-09 live test."""
        turns = [
            {"role": "user", "content": "ok, ya analizaste mi perfil o estas en eso?"},
            {
                "role": "assistant",
                "content": "Estoy en eso, pero ya tengo avance real. Ya validé Notion y "
                           "ya confirmé acceso a los docs de perfil en la VM.",
                "tool_calls": [],
            },
        ]
        flagged = detect_project_turns_without_tool_calls(turns)
        assert len(flagged) == 1

    def test_non_project_turn_not_flagged(self):
        turns = [
            {"role": "user", "content": "¿cuánto es 2 + 2?"},
            {"role": "assistant", "content": "4.", "tool_calls": []},
        ]
        flagged = detect_project_turns_without_tool_calls(turns)
        assert flagged == []


class TestOpsLogActivityCheck:
    """Verify ops_log has entries after a prompt (no ghost activity)."""

    def _make_entry(self, ts: str, task: str = "notion.add_comment") -> dict:
        return {"timestamp": ts, "task": task, "status": "task_completed"}

    def test_activity_found_within_window(self):
        entries = [
            self._make_entry("2026-03-09T02:50:00Z", "umbral_notion_read_page"),
        ]
        assert check_ops_log_activity(entries, "2026-03-09T02:49:16Z", within_seconds=120)

    def test_no_activity_in_window(self):
        """This is the exact failure from 2026-03-09: ops_log silent after prompt."""
        entries = [
            # Last activity was 42 minutes BEFORE the prompt
            self._make_entry("2026-03-09T02:07:51Z", "windows.fs.list"),
        ]
        assert not check_ops_log_activity(
            entries, "2026-03-09T02:49:16Z", within_seconds=120
        )

    def test_activity_outside_window_not_counted(self):
        entries = [
            self._make_entry("2026-03-09T02:55:00Z"),  # 5m 44s after — outside 120s
        ]
        assert not check_ops_log_activity(
            entries, "2026-03-09T02:49:16Z", within_seconds=120
        )

    def test_empty_ops_log_returns_false(self):
        assert not check_ops_log_activity([], "2026-03-09T02:49:16Z")

    def test_activity_exactly_at_boundary(self):
        entries = [self._make_entry("2026-03-09T02:51:16Z")]  # exactly 120s after
        assert check_ops_log_activity(entries, "2026-03-09T02:49:16Z", within_seconds=120)
