import pytest

from dispatcher.task_routing import task_requires_vm


@pytest.mark.parametrize(
    ('team_requires_vm', 'task', 'expected'),
    [
        (False, 'research.web', False),
        (False, 'windows.fs.list', False),
        (True, 'research.web', False),
        (True, 'llm.generate', False),
        (True, 'composite.research_report', False),
        (True, 'browser.navigate', True),
        (True, 'gui.screenshot', True),
        (True, 'windows.fs.list', True),
        (True, 'granola.process_transcript', True),
        (True, 'custom.task', True),
    ],
)
def test_task_requires_vm(team_requires_vm, task, expected):
    assert task_requires_vm(team_requires_vm, task) is expected
