"""GET /gates — operational gates read-only snapshot."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/gates")
async def gates_state() -> dict:
    return {
        "read_only": True,
        "gates": [
            {
                "id": "D6.1",
                "name": "AECO KB",
                "status": "blocked_source_repair",
                "evidence": "buildingSMART direct PDF seeds returned 404; D6.1e source repair required.",
                "next_action": "Run crawler preflight, parser, publisher, then verify_kb.py with intl coverage.",
            },
            {
                "id": "D5/O15",
                "name": "Gmail + Calendar skills",
                "status": "ready",
                "evidence": "O15_GMAIL_CALENDAR_SKILLS_OK.",
                "next_action": "Keep tests hermetic; no real Google credentials by default.",
            },
            {
                "id": "editorial",
                "name": "Editorial + LinkedIn",
                "status": "hitl_required",
                "evidence": "LinkedIn v1 requires approved content and explicit publish authorization.",
                "next_action": "Complete Wave 2 idempotency, lifecycle, and source-use policy.",
            },
            {
                "id": "security",
                "name": "Dependency + secret hygiene",
                "status": "watch",
                "evidence": "pip-audit and local .env ACL are tracked as operational risks.",
                "next_action": "Run pip check, pip-audit, and redacted secret scan before merge.",
            },
            {
                "id": "tests",
                "name": "Full suite",
                "status": "required",
                "evidence": "Core-first PR must keep pytest suites green without live credentials.",
                "next_action": "Run targeted suites first, then python -m pytest tests -q.",
            },
        ],
    }
