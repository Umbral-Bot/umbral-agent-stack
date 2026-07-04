"""Tests — política de comunicación Rick → David + orden canónico de entrega PIT.

Snapshot lint sobre los docs canónicos (mismo patrón que
``test_pit_dev_mode.py::test_skill_has_the_hard_stop``): las reglas duras de
comms y el orden de entrega post-torneo deben seguir presentes en:

- SKILL ``product-innovation-tournament`` (§Política de comunicación + §Post-torneo);
- ``rick-orchestrator/ROLE.md`` (§Communication policy);
- ``docs/ops/pit-dev-mode-vision-2026-07-03.md`` (§Cierre y entrega).

Si un test de este archivo rompe, alguien tocó la política de comunicación o
el orden de entrega — revisar con David antes de mergear.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = (
    REPO_ROOT
    / "openclaw"
    / "workspace-templates"
    / "skills"
    / "product-innovation-tournament"
    / "SKILL.md"
)
ROLE_MD = (
    REPO_ROOT
    / "openclaw"
    / "workspace-agent-overrides"
    / "rick-orchestrator"
    / "ROLE.md"
)
VISION_MD = REPO_ROOT / "docs" / "ops" / "pit-dev-mode-vision-2026-07-03.md"


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _role_text() -> str:
    return ROLE_MD.read_text(encoding="utf-8")


def _vision_text() -> str:
    return VISION_MD.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """Devuelve el cuerpo de una sección `## heading` hasta el próximo `## `."""
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


# ---------------------------------------------------------------------------
# SKILL — política de comunicación Rick → David
# ---------------------------------------------------------------------------


class TestSkillCommsPolicy:
    def test_has_policy_section(self):
        assert "## Política de comunicación Rick → David (Telegram)" in _skill_text()

    def test_three_allowed_moments(self):
        section = _section(
            _skill_text(), "## Política de comunicación Rick → David (Telegram)"
        )
        for marker in ("**INICIO**", "**BLOQUEO**", "**CIERRE**"):
            assert marker in section, marker

    def test_no_granular_progress_unless_asked(self):
        section = _section(
            _skill_text(), "## Política de comunicación Rick → David (Telegram)"
        )
        assert "NO envía progreso granular" in section
        assert "pregunte explícitamente por status" in section
        # ejemplos prohibidos explícitos
        for banned in ("lane completada", "judge-1 listo", "scorecards", "vault"):
            assert banned in section, banned

    def test_everything_else_goes_to_vault(self):
        section = _section(
            _skill_text(), "## Política de comunicación Rick → David (Telegram)"
        )
        assert "vault + evidencia, no chat" in section

    def test_inicio_is_one_short_message(self):
        section = _section(
            _skill_text(), "## Política de comunicación Rick → David (Telegram)"
        )
        assert "arrancado" in section
        assert "1 mensaje corto" in section

    def test_cierre_is_bounded_with_drive_links(self):
        section = _section(
            _skill_text(), "## Política de comunicación Rick → David (Telegram)"
        )
        assert "≤15 líneas" in section
        assert "Drive" in section
        assert "Notion" in section  # fase 2

    def test_broker_comms_points_to_global_policy(self):
        assert "Aplica la política global" in _skill_text()


# ---------------------------------------------------------------------------
# ROLE rick-orchestrator — misma política
# ---------------------------------------------------------------------------


class TestRoleCommsPolicy:
    def test_has_policy_section(self):
        assert "## Communication policy — Telegram to David" in _role_text()

    def test_three_allowed_moments(self):
        section = _section(_role_text(), "## Communication policy — Telegram to David")
        for marker in ("**INICIO**", "**BLOQUEO**", "**CIERRE**"):
            assert marker in section, marker

    def test_no_granular_progress_rule(self):
        section = _section(_role_text(), "## Communication policy — Telegram to David")
        assert "does **NOT** send granular progress" in section
        assert "unless David explicitly asks for status" in section

    def test_vault_not_chat(self):
        section = _section(_role_text(), "## Communication policy — Telegram to David")
        assert "vault + evidence, not chat" in section

    def test_cross_references_skill(self):
        section = _section(_role_text(), "## Communication policy — Telegram to David")
        assert "product-innovation-tournament/SKILL.md" in section


# ---------------------------------------------------------------------------
# Orden canónico de entrega post-torneo
# ---------------------------------------------------------------------------


class TestCanonicalDeliveryOrder:
    def test_skill_post_torneo_has_ordered_steps(self):
        section = _section(_skill_text(), "## Post-torneo")
        markers = [
            "Outcome report",
            "Trazabilidad PASS",
            "Gate David sobre el winner",
            "Drive upload",
            "Telegram CIERRE",
            "Notion publish",
        ]
        positions = [section.index(marker) for marker in markers]
        assert positions == sorted(positions), "orden canónico alterado en SKILL"

    def test_skill_documents_pending_prefix_rule(self):
        section = _section(_skill_text(), "## Post-torneo")
        assert "empiece con" in section and "pending" in section
        assert "prefijo, no igualdad exacta" in section

    def test_skill_documents_zip_and_notion_stub(self):
        section = _section(_skill_text(), "## Post-torneo")
        assert "zip del deliverable winner" in section
        assert "GOOGLE_DRIVE_PIT_FOLDER_ID" in section
        assert "notion_publish_stub" in section
        assert "NO implementado" in section

    def test_vision_has_canonical_close_section(self):
        text = _vision_text()
        assert "## 7. Cierre y entrega post-torneo (orden canónico)" in text
        section = _section(text, "## 7. Cierre y entrega post-torneo (orden canónico)")
        markers = [
            "Outcome report",
            "Trazabilidad PASS",
            "Gate David sobre el winner",
            "Drive upload",
            "Telegram CIERRE",
            "Notion publish",
        ]
        positions = [section.index(marker) for marker in markers]
        assert positions == sorted(positions), "orden canónico alterado en visión"
        assert "TRACE_COMPLETE" in section
        assert "winner_deliverable_missing" in section
        assert "notion_publish_stub" in section

    def test_delivery_script_enforces_the_gates(self):
        """Los FAIL reasons del orden canónico existen en el script."""
        script = (
            REPO_ROOT / "scripts" / "pit" / "pit_deliver_telegram_pack.py"
        ).read_text(encoding="utf-8")
        for reason in (
            "traceability_report_missing",
            "traceability_gaps",
            "winner_pending",
            "winner_deliverable_missing",
            "drive_not_configured",
        ):
            assert reason in script, reason
        assert "notion_publish_stub" in script
