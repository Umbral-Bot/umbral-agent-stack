# Pytest Report R12

**Fecha:** 2026-03-04  
**Total tests:** 751  
**Passed:** 746  
**Failed:** 0  
**Skipped:** 5  
**Warnings:** 4

## Problema encontrado y corregido

### Rate limiter + Token mismatch en test suite completa

**Error original:** 49 tests fallaban con 401 Unauthorized y 429 Too Many Requests al ejecutar la suite completa (`pytest tests/`), pero pasaban al ejecutarse individualmente.

**Causa raíz:** 
1. `WORKER_TOKEN=test` (CLI) vs `Bearer test-token-12345` (test AUTH headers) — mismatch cuando `worker.config` se importaba antes de que los test files pudieran sobrescribir `os.environ["WORKER_TOKEN"]`.
2. El rate limiter (60 RPM default) se agotaba al ejecutar >60 tests que hacen HTTP requests.

**Fix aplicado:** Creado `tests/conftest.py` con:
- `os.environ["WORKER_TOKEN"] = "test-token-12345"` antes de cualquier import de worker
- `os.environ["RATE_LIMIT_RPM"] = "999999"` para deshabilitar rate limiting en tests
- Fixture `autouse` que sincroniza `worker.config.WORKER_TOKEN` y resetea el rate limiter entre tests

## Tests skipped (5)

| Test | Razón |
|------|-------|
| `test_hardening::test_encrypt_decrypt_roundtrip` | Requiere paquete `cryptography` |
| `test_e2e_validation` (4 tests) | Requieren infra real (Redis, Worker, VPS) |

## Warnings (4)

| Warning | Origen |
|---------|--------|
| `PytestCollectionWarning: cannot collect TestResult` | `scripts/e2e_validation.py` usa `@dataclass` con `__init__` |
| `DeprecationWarning: on_event` (×2) | FastAPI recomienda `lifespan` handlers |
| `UserWarning: 1 task(s) have no SKILL.md: ['ping']` | Test informacional — `ping` no tiene dots en regex |
