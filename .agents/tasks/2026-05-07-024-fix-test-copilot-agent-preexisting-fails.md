# Task 024 — Fix tests preexistentes en test_copilot_agent.py

**Owner:** TBD (David asigna)  
**Origen:** Hallazgo durante PR #344 (CI bs4 fix). Mergeado con --admin porque los 2 fails son ortogonales al scope.  
**Prioridad:** Media (no bloquea PRs porque ya estaban rojos antes).

## Contexto

Después de fixear bs4 en CI (PR #344), `pytest tests/` deja al descubierto 2 fails que **estaban ocultos detrás del crash de `ModuleNotFoundError: bs4`** en test_html_to_notion_blocks.py.

## Fails

```
FAILED tests/test_copilot_agent.py::TestUmbralCopilotAgent::test_run_without_start_raises
  AssertionError: Regex pattern did not match.

FAILED tests/test_copilot_agent.py::TestUmbralCopilotAgent::test_stop_without_start_is_safe
  RuntimeError: There is no current event loop in thread 'MainThread'.
```

## Diagnóstico inicial (no verificado en profundidad)

- `test_run_without_start_raises`: el regex esperado para el error message probablemente cambió en una refactor de `UmbralCopilotAgent.run()`. Actualizar el regex o el mensaje del raise.
- `test_stop_without_start_is_safe`: patrón típico de pytest+asyncio sin fixture `pytest_asyncio` o sin `asyncio_mode=auto`. Revisar si el test debería usar `@pytest.mark.asyncio` y si pyproject.toml tiene `asyncio_mode` configurado.

## Acción

1. Branch: copilot-vps/fix-test-copilot-agent-preexisting
2. Reproducir local: `pytest tests/test_copilot_agent.py -v`
3. Decidir: arreglar tests o arreglar el código según el caso.
4. PR con scope chico, sin tocar nada fuera de test_copilot_agent.py o copilot_agent/ módulo.

## Quality gates

- 0 cambios en otros tests.
- 0 cambios runtime fuera de copilot_agent/ si el bug está ahí.
- CI debe quedar 100% verde tras este fix.
