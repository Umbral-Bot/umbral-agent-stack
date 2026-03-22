# Claude Main Reconciliation — 2026-03-12

Ejecutado por: codex

## Objetivo

Reconciliar el merge de `main` posterior a la consolidación de Claude (`#118`) para
cerrar la deriva entre código, tests y documentación antes de seguir agregando
features.

## Hallazgos iniciales

- `pytest -q` quedó rojo tras el pull de `origin/main`:
  - `8 failed`
  - `1040 passed`
  - `4 skipped`
- La mayoría de los fallos venían de cambios intencionales no reflejados en tests:
  - `HealthMonitor` con inicio pesimista
  - retries de `ConnectError` con backoff de `30s`
  - team key de Linear tomado desde `config/teams.yaml`
  - alias único `openclaw_proxy`
  - `granola.*` ya no VM-only
- Además apareció un bug real en `scripts/audit_to_linear.py`:
  - seguía llamando `worker.linear_client._graphql`
  - el helper real hoy se llama `_gql`
  - el error no había saltado porque el smoke previo fue en `--dry-run`

## Cambios aplicados

### Código

- `dispatcher/health.py`
  - se corrigió `_on_failure()` para que el sistema entre a `PARTIAL` cuando
    alcanza el umbral de fallos, incluso si parte con init pesimista.
- `scripts/audit_to_linear.py`
  - ahora resuelve el helper GraphQL de forma compatible:
    - `_gql`
    - fallback `_graphql`

### Tests

- Actualizados:
  - `tests/test_dispatcher.py`
  - `tests/test_dispatcher_resilience.py`
  - `tests/test_dispatcher_escalation.py`
  - `tests/test_openclaw_proxy.py`
  - `tests/test_task_routing.py`
- Nuevos:
  - `tests/test_audit_to_linear.py`

### Documentación

- `docs/15-model-quota-policy.md`
  - se actualizó la sección de `openclaw_proxy`
  - se eliminó la referencia vieja a `openclaw_claude_*`
  - se añadió nota de routing para `granola.*`

## Validación

### Suite focalizada

- `python -m pytest tests/test_dispatcher.py tests/test_dispatcher_resilience.py tests/test_dispatcher_escalation.py tests/test_openclaw_proxy.py tests/test_task_routing.py tests/test_audit_to_linear.py -q`
- Resultado: `100 passed`

### Suite completa

- `python -m pytest -q`
- Resultado:
  - `1054 passed`
  - `4 skipped`
  - `1 warning`

### Validaciones adicionales

- `python scripts/validate_skills.py`
  - `68` skills validadas correctamente
- `python scripts/audit_to_linear.py --dry-run`
  - parseo correcto
  - `21` items detectados

## Estado final

- La consolidación de Claude ya no deja el repo en rojo.
- Los cambios intencionales quedaron alineados con tests y docs.
- El bug oculto de `audit_to_linear.py` quedó corregido antes de entrar en uso real.

## Riesgos residuales

- La warning de `tests/test_skills_coverage.py` sigue mostrando tasks sin skill
  dedicada. No rompe el sistema, pero sigue siendo deuda de cobertura.
- Todavía conviene no mezclar esta reconciliación con un upgrade de OpenClaw en el
  mismo corte.
