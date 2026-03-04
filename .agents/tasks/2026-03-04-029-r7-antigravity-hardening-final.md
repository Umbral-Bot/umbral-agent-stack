---
id: "029"
title: "Hardening Final — Rate limiting + sanitización + secrets audit"
assigned_to: antigravity
branch: feat/antigravity-hardening
round: 7
status: assigned
created: 2026-03-04
---

## Objetivo

Cerrar las brechas de seguridad pendientes: rate limiting real en el Worker API, sanitización de inputs, y auditoría de secretos expuestos en el código.

## Contexto

- `worker/app.py` — Worker FastAPI, sin rate limiting real
- `worker/tool_policy.py` — ToolPolicy existente (allowlist)
- `infra/secrets.py` — SecretStore placeholder
- `tests/test_hardening.py` — tests existentes para SecretStore, Sanitize, RateLimit

## Requisitos

### 1. Rate Limiting en Worker API

Implementar rate limiting real usando un middleware simple (sin dependencias externas):

```python
# worker/rate_limiter.py
import time
from collections import defaultdict
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.monotonic()
        reqs = self._requests[client_id]
        # Limpiar requests viejos
        reqs[:] = [t for t in reqs if now - t < self.window]
        if len(reqs) >= self.max_requests:
            return False, self.max_requests - len(reqs)
        reqs.append(now)
        return True, self.max_requests - len(reqs)
```

Integrar como middleware en `worker/app.py`:
- 60 req/min por default (configurable vía `RATE_LIMIT_RPM` env var)
- Retornar 429 con header `Retry-After` cuando se exceda
- Excluir `/health` del rate limiting

### 2. Sanitización de inputs

Crear `worker/sanitizer.py`:
- Sanitizar todos los inputs de tareas antes de procesarlos
- Prevenir injection en campos que se usan en URLs, comandos, o queries
- Truncar inputs excesivamente largos (max 10000 chars por campo)
- Validar tipos esperados (str, int, etc.)
- Loguear intentos de injection como WARNING

### 3. Secrets Audit

Crear `scripts/secrets_audit.py`:
- Escanear el repo en busca de patrones de secrets: API keys, tokens, passwords
- Patterns: `sk-`, `key-`, `ghp_`, `ghs_`, `AKIA`, strings de 32+ chars alfanuméricos
- Excluir: `.env.example`, `docs/`, test files
- Output: lista de archivos y líneas con posibles secretos
- Exit code 1 si encuentra alguno (para CI)

### 4. Actualizar tests

- `tests/test_hardening.py` — agregar tests para RateLimiter real
- Tests de sanitización con inputs maliciosos
- Tests de secrets_audit contra fixtures

### 5. Pre-commit hook (opcional)

Crear `.pre-commit-config.yaml` con hook para `secrets_audit.py` (prevenir commits con secretos).

## Entregable

PR a `main` desde `feat/antigravity-hardening` con todos los tests pasando.
