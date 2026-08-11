import pytest

from dispatcher.task_routing import task_requires_vm


@pytest.mark.parametrize(
    ('team_requires_vm', 'task', 'expected'),
    [
        (False, 'research.web', False),
        # Contrato 2026-08-11 (PKG-UAS-VM-ROUTE-WINDOWS): los prefijos de VM
        # fuerzan VM aunque el equipo no la requiera — el cron con team
        # normalizado a system debe llegar a pcrick, no al worker Linux.
        (False, 'windows.fs.list', True),
        (False, 'browser.navigate', True),
        (False, 'gui.screenshot', True),
        (False, 'custom.task', False),
        (True, 'research.web', False),
        (True, 'llm.generate', False),
        (True, 'composite.research_report', False),
        (True, 'browser.navigate', True),
        (True, 'gui.screenshot', True),
        (True, 'windows.fs.list', True),
        (True, 'granola.process_transcript', False),
        (True, 'custom.task', True),
    ],
)
def test_task_requires_vm(team_requires_vm, task, expected):
    assert task_requires_vm(team_requires_vm, task) is expected


def test_normalized_cron_envelope_routes_to_vm():
    """Caso rick-ops end-to-end: el envelope ops/cron se normaliza a
    system/general y aun asi windows.fs.list debe rutear a la VM."""
    from dispatcher.task_routing import normalize_envelope_identity

    envelope = {
        'schema_version': '0.1',
        'team': 'ops',
        'task_type': 'cron',
        'task': 'windows.fs.list',
        'input': {'path': 'G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas', 'limit': 50},
    }
    normalize_envelope_identity(envelope)
    assert envelope['team'] == 'system'
    # team system no requiere VM, pero el prefijo windows. la fuerza
    assert task_requires_vm(False, envelope['task']) is True


class TestNormalizeEnvelopeIdentity:
    """Regresion del 400 'Invalid request body' en tasks encoladas.

    Caso real (2026-08-11): windows.fs.list encolada por el gateway con
    team='ops' y task_type='cron' — ambos fuera de los enums del worker —
    moria con 400 en cada corrida del cron de rick-ops.
    Diagnostico: docs/ops/uas-fossil-disc-plus-20260811.md
    """

    def test_production_payload_is_coerced_and_parses(self):
        from dispatcher.task_routing import normalize_envelope_identity
        from worker.models import TaskEnvelope

        envelope = {
            'schema_version': '0.1',
            'task_id': '49e5a9fd-e568-42ce-a8af-3352010ffa7b',
            'team': 'ops',
            'task_type': 'cron',
            'task': 'windows.fs.list',
            'input': {'path': 'G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas', 'limit': 50},
        }
        fixes = normalize_envelope_identity(envelope)
        assert envelope['team'] == 'system'
        assert envelope['task_type'] == 'general'
        assert len(fixes) == 2
        # El envelope normalizado ya no revienta la validacion del worker.
        parsed = TaskEnvelope.from_run_payload(envelope)
        assert parsed.team.value == 'system'
        assert parsed.task_type.value == 'general'

    def test_valid_values_untouched(self):
        from dispatcher.task_routing import normalize_envelope_identity

        envelope = {'team': 'marketing', 'task_type': 'writing', 'task': 'ping', 'input': {}}
        assert normalize_envelope_identity(envelope) == []
        assert envelope['team'] == 'marketing'
        assert envelope['task_type'] == 'writing'

    def test_missing_keys_untouched(self):
        from dispatcher.task_routing import normalize_envelope_identity

        envelope = {'task': 'ping', 'input': {}}
        assert normalize_envelope_identity(envelope) == []
        assert 'team' not in envelope
        assert 'task_type' not in envelope

    def test_only_invalid_field_is_coerced(self):
        from dispatcher.task_routing import normalize_envelope_identity

        envelope = {'team': 'rick-orchestrator', 'task_type': 'cron', 'task': 'ping', 'input': {}}
        fixes = normalize_envelope_identity(envelope)
        assert envelope['team'] == 'rick-orchestrator'
        assert envelope['task_type'] == 'general'
        assert len(fixes) == 1


def test_normalize_sets_match_worker_enums():
    """Guardia anti-drift: los sets locales del dispatcher (sin pydantic) deben
    ser identicos a los enums del contrato del worker."""
    from worker.models import TaskType, Team

    from dispatcher import task_routing

    assert task_routing._VALID_TEAM_VALUES == {m.value for m in Team}
    assert task_routing._VALID_TASK_TYPE_VALUES == {m.value for m in TaskType}
    assert task_routing._TEAM_FALLBACK in task_routing._VALID_TEAM_VALUES
    assert task_routing._TASK_TYPE_FALLBACK in task_routing._VALID_TASK_TYPE_VALUES
