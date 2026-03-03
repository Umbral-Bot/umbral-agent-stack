"""
Tests para worker/linear_team_router.py
"""
import pytest
from worker.linear_team_router import (
    infer_team_from_text,
    get_team_labels,
    get_supervisor_display_name,
    resolve_team_for_issue,
)

# Config mínima de equipos para tests (sin leer el archivo real)
_CONFIG = {
    "teams": {
        "marketing": {
            "supervisor": "Marketing Supervisor",
            "description": "Estrategia digital",
            "requires_vm": False,
            "roles": ["supervisor", "seo", "social_media"],
        },
        "advisory": {
            "supervisor": "Asesoría Personal Supervisor",
            "description": "Asesoría",
            "requires_vm": False,
            "roles": ["supervisor", "financial"],
        },
        "improvement": {
            "supervisor": "Mejora Continua Supervisor",
            "description": "OODA",
            "requires_vm": True,
            "roles": ["supervisor", "sota_research"],
        },
        "lab": {
            "supervisor": None,
            "description": "Experimentos",
            "requires_vm": True,
            "roles": ["researcher"],
        },
        "system": {
            "supervisor": None,
            "description": "Tareas internas",
            "requires_vm": False,
            "roles": ["ping", "health"],
        },
    }
}


class TestInferTeamFromText:
    def test_marketing_seo(self):
        assert infer_team_from_text("Crear post de SEO para Instagram") == "marketing"

    def test_marketing_copywriting(self):
        assert infer_team_from_text("Necesito copywriting para campaña de LinkedIn") == "marketing"

    def test_advisory_financial(self):
        assert infer_team_from_text("Revisar portafolio financiero y presupuesto") == "advisory"

    def test_advisory_lifestyle(self):
        assert infer_team_from_text("Asesoría personal sobre lifestyle e inversión") == "advisory"

    def test_improvement_ooda(self):
        assert infer_team_from_text("Aplicar ciclo OODA para optimizar el sistema") == "improvement"

    def test_improvement_refactor(self):
        assert infer_team_from_text("Refactor y benchmark del pipeline") == "improvement"

    def test_lab_experiment(self):
        assert infer_team_from_text("Experimento con nuevo sandbox en VM") == "lab"

    def test_system_infra(self):
        assert infer_team_from_text("Deploy de infra en pipeline CI/CD") == "system"

    def test_no_match_returns_none(self):
        assert infer_team_from_text("xyz abc 123 qwerty") is None

    def test_empty_string_returns_none(self):
        assert infer_team_from_text("") is None

    def test_case_insensitive(self):
        assert infer_team_from_text("MARKETING SEO CONTENT") == "marketing"

    def test_higher_score_wins(self):
        # múltiples keywords de marketing
        result = infer_team_from_text("marketing seo social media content blog copywriting")
        assert result == "marketing"


class TestGetTeamLabels:
    def test_marketing_has_team_and_supervisor(self):
        labels = get_team_labels("marketing", _CONFIG)
        assert "Marketing" in labels
        assert "Marketing Supervisor" in labels

    def test_advisory_supervisor_display_name(self):
        labels = get_team_labels("advisory", _CONFIG)
        assert "Advisory" in labels
        assert "Asesoría Personal Supervisor" in labels

    def test_lab_no_supervisor(self):
        labels = get_team_labels("lab", _CONFIG)
        assert "Lab" in labels
        # sin supervisor → no aparece label de supervisor
        assert not any("Supervisor" in l for l in labels)

    def test_unknown_team_returns_empty(self):
        assert get_team_labels("nonexistent", _CONFIG) == []

    def test_system_no_supervisor(self):
        labels = get_team_labels("system", _CONFIG)
        assert "System" in labels
        assert len(labels) == 1  # solo el equipo, sin supervisor


class TestGetSupervisorDisplayName:
    def test_marketing(self):
        assert get_supervisor_display_name("marketing", _CONFIG) == "Marketing Supervisor"

    def test_advisory(self):
        assert get_supervisor_display_name("advisory", _CONFIG) == "Asesoría Personal Supervisor"

    def test_improvement(self):
        assert get_supervisor_display_name("improvement", _CONFIG) == "Mejora Continua Supervisor"

    def test_lab_returns_none(self):
        assert get_supervisor_display_name("lab", _CONFIG) is None

    def test_system_returns_none(self):
        assert get_supervisor_display_name("system", _CONFIG) is None

    def test_unknown_returns_none(self):
        assert get_supervisor_display_name("nonexistent", _CONFIG) is None


class TestResolveTeamForIssue:
    def test_explicit_team_key(self):
        result = resolve_team_for_issue(team_key="marketing", teams_config=_CONFIG)
        assert result["team_key"] == "marketing"
        assert result["inferred"] is False
        assert "Marketing" in result["labels"]
        assert "Marketing Supervisor" in result["labels"]
        assert result["supervisor_display_name"] == "Marketing Supervisor"

    def test_colors_match_label_count(self):
        result = resolve_team_for_issue(team_key="marketing", teams_config=_CONFIG)
        assert len(result["labels"]) == len(result["label_colors"])

    def test_inferred_from_title(self):
        result = resolve_team_for_issue(
            title="Crear estrategia SEO para blog",
            teams_config=_CONFIG,
        )
        assert result["team_key"] == "marketing"
        assert result["inferred"] is True

    def test_inferred_from_description(self):
        result = resolve_team_for_issue(
            title="Nueva tarea",
            description="Revisar finanzas y presupuesto del cliente",
            teams_config=_CONFIG,
        )
        assert result["team_key"] == "advisory"
        assert result["inferred"] is True

    def test_explicit_overrides_inference(self):
        result = resolve_team_for_issue(
            team_key="lab",
            title="Hacer SEO marketing content",
            teams_config=_CONFIG,
        )
        assert result["team_key"] == "lab"
        assert result["inferred"] is False

    def test_no_match_returns_empty(self):
        result = resolve_team_for_issue(title="xyz 123 abc", teams_config=_CONFIG)
        assert result["team_key"] is None
        assert result["labels"] == []
        assert result["label_colors"] == []
        assert result["supervisor_display_name"] is None
        assert result["inferred"] is False

    def test_no_params_returns_empty(self):
        result = resolve_team_for_issue(teams_config=_CONFIG)
        assert result["team_key"] is None

    def test_lab_no_supervisor_in_result(self):
        result = resolve_team_for_issue(team_key="lab", teams_config=_CONFIG)
        assert result["supervisor_display_name"] is None
        assert len(result["labels"]) == 1  # solo "Lab"
