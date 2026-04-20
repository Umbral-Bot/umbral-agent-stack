import time

from dispatcher.supervisor_resolution import (
    SupervisorResolution,
    load_supervisor_registry,
    resolve_supervisor,
)


TEAMS_CONFIG = {
    "teams": {
        "marketing": {
            "supervisor": "Marketing Supervisor",
            "description": "Estrategia digital",
            "requires_vm": False,
        },
        "improvement": {
            "supervisor": "Mejora Continua Supervisor",
            "description": "Mejora continua del sistema",
            "requires_vm": True,
        },
        "lab": {
            "supervisor": None,
            "description": "Experimentos",
            "requires_vm": True,
        },
    }
}


def registry_for(entry):
    return {"supervisors": {"improvement": entry}}


def test_design_only_improvement_registry_does_not_activate():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "label": "Mejora Continua Supervisor",
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "design_only",
                "fallback": "direct",
            }
        ),
    )

    assert result.resolution_status == "unresolved"
    assert result.target_type == "openclaw_agent"
    assert result.target == "improvement-supervisor"
    assert result.fallback == "direct"
    assert result.fallback_used is True
    assert result.should_block is False
    assert result.reason == "status_design_only"


def test_team_without_supervisor_returns_none_direct():
    result = resolve_supervisor("lab", teams_config=TEAMS_CONFIG, registry={})

    assert result.resolution_status == "none"
    assert result.target_type == "none"
    assert result.fallback == "direct"
    assert result.should_block is False
    assert result.reason == "team_has_no_supervisor"


def test_supervisor_label_without_registry_entry_is_unresolved_direct():
    result = resolve_supervisor("marketing", teams_config=TEAMS_CONFIG, registry={})

    assert result.supervisor_label == "Marketing Supervisor"
    assert result.resolution_status == "unresolved"
    assert result.target is None
    assert result.fallback == "direct"
    assert result.should_block is False
    assert result.reason == "registry_entry_missing"


def test_disabled_entry_is_unresolved_direct():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "disabled",
                "fallback": "direct",
            }
        ),
    )

    assert result.resolution_status == "unresolved"
    assert result.reason == "status_disabled"
    assert result.should_block is False


def test_active_entry_without_health_signal_is_not_ready_direct():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "active",
                "fallback": "direct",
            }
        ),
    )

    assert result.resolution_status == "not_ready"
    assert result.reason == "target_availability_unknown"
    assert result.fallback == "direct"
    assert result.should_block is False


def test_active_entry_with_unavailable_target_is_unresolved_direct():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "active",
                "fallback": "direct",
            }
        ),
        target_available=False,
    )

    assert result.resolution_status == "unresolved"
    assert result.reason == "target_unavailable"
    assert result.fallback_used is True
    assert result.should_block is False


def test_active_entry_with_available_target_resolves_without_blocking():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "active",
                "fallback": "direct",
            }
        ),
        target_available=True,
    )

    assert result.resolution_status == "resolved"
    assert result.target == "improvement-supervisor"
    assert result.fallback_used is False
    assert result.should_block is False


def test_corrupt_registry_shape_falls_back_direct():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry={"supervisors": "not-a-mapping"},
    )

    assert result.resolution_status == "unresolved"
    assert result.fallback == "direct"
    assert result.reason == "registry_entry_missing"
    assert result.should_block is False


def test_invalid_active_entry_falls_back_direct():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "status": "active",
                "fallback": "direct",
            }
        ),
    )

    assert result.resolution_status == "unresolved"
    assert result.reason == "active_target_missing"
    assert result.should_block is False


def test_no_string_matching_against_human_label():
    registry = {
        "supervisors": {
            "Mejora Continua Supervisor": {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "active",
                "fallback": "direct",
            }
        }
    }

    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry,
        target_available=True,
    )

    assert result.resolution_status == "unresolved"
    assert result.target is None
    assert result.reason == "registry_entry_missing"
    assert result.should_block is False


def test_result_log_fields_include_monitoring_shape():
    result = resolve_supervisor(
        "improvement",
        teams_config=TEAMS_CONFIG,
        registry=registry_for(
            {
                "type": "openclaw_agent",
                "target": "improvement-supervisor",
                "status": "design_only",
                "fallback": "direct",
            }
        ),
    )

    assert result.to_log_fields() == {
        "team": "improvement",
        "supervisor_label": "Mejora Continua Supervisor",
        "resolution_status": "unresolved",
        "target_type": "openclaw_agent",
        "target": "improvement-supervisor",
        "fallback": "direct",
        "fallback_used": True,
        "should_block": False,
        "reason": "status_design_only",
    }


def test_load_registry_returns_empty_for_missing_file(tmp_path):
    missing = tmp_path / "missing.yaml"

    assert load_supervisor_registry(missing) == {}


def test_load_registry_returns_empty_for_invalid_yaml(tmp_path):
    invalid = tmp_path / "supervisors.yaml"
    invalid.write_text("supervisors: [", encoding="utf-8")

    assert load_supervisor_registry(invalid) == {}


def test_load_registry_reads_valid_yaml(tmp_path):
    valid = tmp_path / "supervisors.yaml"
    valid.write_text(
        """
supervisors:
  improvement:
    type: openclaw_agent
    target: improvement-supervisor
    status: design_only
    fallback: direct
""".strip(),
        encoding="utf-8",
    )

    data = load_supervisor_registry(valid)

    assert data["supervisors"]["improvement"]["target"] == "improvement-supervisor"


def test_resolution_is_fast_enough_for_future_monitoring():
    registry = registry_for(
        {
            "type": "openclaw_agent",
            "target": "improvement-supervisor",
            "status": "design_only",
            "fallback": "direct",
        }
    )

    start = time.perf_counter()
    for _ in range(1000):
        result = resolve_supervisor("improvement", teams_config=TEAMS_CONFIG, registry=registry)
    elapsed = time.perf_counter() - start

    assert isinstance(result, SupervisorResolution)
    assert elapsed < 0.5
