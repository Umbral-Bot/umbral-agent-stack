# Task R21 — Quick Wins Auditoría: Worker (Codex)

**Fecha:** 2026-03-07  
**Ronda:** 21  
**Agente:** Codex (GPT-5.4)  
**Rama:** `codex/audit-qw-worker` — trabajar solo en esta rama.

---

## Flujo Git (obligatorio)

1. **Antes de tocar código:** `git fetch origin && git checkout main && git pull origin main`
2. **Crear tu rama:** `git checkout -b codex/audit-qw-worker`
3. **Trabajar solo en esta rama.** No hacer merge a main ni a otras ramas.
4. **Al terminar:** commit, `git push origin codex/audit-qw-worker`, abrir PR a main. No mergear el PR tú mismo salvo que se te indique.

---

## Objetivo

Implementar los quick wins de la auditoría 2026-03 que afectan al **worker**: QW-1, QW-2, QW-3, QW-5 (parte worker) y QW-6. Plan completo: [docs/plan-implementacion-auditoria-2026-03.md](../../docs/plan-implementacion-auditoria-2026-03.md).

---

## Tareas

### QW-1: Sanitize efectivo + _check_injection defensivo (P0 #3, SEC-13)

- En `worker/app.py`, endpoint `/run`: asignar retorno de sanitize: `envelope.input = sanitize_input(envelope.input)` (no solo llamar sin asignar).
- En `worker/app.py`, endpoint `/enqueue`: usar input sanitizado al construir el envelope, p. ej. `envelope["input"] = sanitize_input(body.input)` (o equivalente).
- En `worker/sanitize.py`: hacer que `_check_injection()` lance `ValueError` en lugar de solo loguear cuando detecte patrón de inyección.
- Ajustar tests de sanitize para verificar que `ValueError` se propaga y que FastAPI devuelve 422.

### QW-2: Comparación timing-safe del token (P1 #9, SEC-7)

- En `worker/app.py` (~línea 183): importar `hmac` y reemplazar `parts[1] != WORKER_TOKEN` por `not hmac.compare_digest(parts[1], WORKER_TOKEN)`.
- Verificar que los tests de autenticación siguen pasando.

### QW-3: Validación de inputs en handlers Windows (SEC-10, SEC-11, SEC-12)

- En `worker/tasks/windows.py`: crear helper `_validate_safe_name(value, max_len=64)` con regex `[A-Za-z0-9_.-]+`; lanzar `ValueError` si no cumple.
- Aplicar a `name` en `handle_windows_firewall_allow_port` antes de pasarlo a `netsh`.
- Aplicar a `username` en `handle_windows_add_interactive_worker_to_startup` antes de construir el path.
- Para `run_as_password` (SEC-10): no recibirlo por input HTTP; documentar en el handler o en docstring que se use env var (p. ej. `SCHTASKS_PASSWORD`) en la VM.
- Añadir tests unitarios para las validaciones.

### QW-5 (parte worker): Emitir task_queued en /enqueue

- En `worker/app.py`, endpoint POST `/enqueue`, después de `queue.enqueue(envelope)`: importar `ops_log` desde `infra.ops_logger` y llamar `ops_log.task_queued(task_id, body.task, body.team, body.task_type or "general", trace_id=trace_id)`.

### QW-6: Unificar rate limiter (P2 #13)

- Una sola variable de entorno: `RATE_LIMIT_RPM`. Eliminar `WORKER_RATE_LIMIT_PER_MIN` de `worker/config.py`.
- Mantener `worker/rate_limiter.py` como implementación activa; deprecar o eliminar `worker/rate_limit.py`.
- Migrar tests que importen `rate_limit` a usar `rate_limiter`; actualizar referencias en `worker/app.py` si hace falta.

---

## Criterios de éxito

- [ ] Sanitize aplicado en `/run` y `/enqueue`; _check_injection lanza ValueError.
- [ ] Auth usa `hmac.compare_digest` para el token.
- [ ] Windows: `name` y `username` validados; `run_as_password` no aceptado por HTTP.
- [ ] `ops_log.task_queued` llamado tras `queue.enqueue()` en `/enqueue`.
- [ ] Una sola env de rate limit (`RATE_LIMIT_RPM`); tests pasan.
- [ ] `pytest tests/ -q` pasa. PR abierto a main con título `fix(R21-102): audit quick wins — worker (sanitize, auth, Windows, task_queued, rate limiter)`.

---

## Restricciones

- No tocar `.env.example` ni scripts de Bitácora (los hace la rama config). No tocar `dispatcher/service.py` (lo hace la rama dispatcher).
- No mergear a main. Solo push de tu rama y abrir PR.
