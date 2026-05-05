# Task 010 — Ola 1b: helper de traza `worker/tasks/_trace.py`

- **Date:** 2026-05-05
- **Assigned to:** copilot-vps
- **Depends on:** ADR `notion-governance/docs/adr/05-ola-1b-channel-adapters-and-traceability.md` §2.3
- **Related design:** `notion-governance/docs/roadmap/13-ola-1b-design-notion-mention-to-task.md` §5
- **Status:** ready
- **Estimated effort:** 1 sesión (~45 min, incluyendo tests + deploy + health check)

---

## Objetivo

Crear el módulo `worker/tasks/_trace.py` con un único helper público `append_delegation(record: dict) -> None` que escriba registros de delegación (ADR 05 §2.3) a un log JSONL append-only, con concurrencia segura y permisos restrictivos.

Esto desbloquea Tasks 011–014 de Ola 1b. El helper es invocado desde `dispatcher/rick_mention.py` (Task 011) y, opcionalmente, desde skills (Task 012).

## Scope concreto

### Archivo nuevo: `worker/tasks/_trace.py`

Contenido mínimo:

1. Constante `DEFAULT_LOG_PATH = Path(os.environ.get("UMBRAL_DELEGATIONS_LOG", "~/.local/state/umbral/delegations.jsonl")).expanduser()`.
2. Función `append_delegation(record: dict) -> None`:
   - Valida campos obligatorios: `from`, `to`, `intent`. Lanza `ValueError` si falta alguno.
   - Inyecta automáticamente `ts` (UTC ISO 8601) y `trace_id` (uuid4 hex) si no vienen.
   - Trunca `summary` a 200 chars (warning si se truncó).
   - Sanitiza: rechaza claves `text`, `secret`, `token`, `api_key`, `password` (raise `ValueError`).
   - Crea el directorio padre con `mkdir(parents=True, exist_ok=True)`.
   - Si el archivo NO existe: lo crea con `os.open(path, O_WRONLY|O_CREAT|O_APPEND, 0o600)` para garantizar `chmod 600` desde el inicio.
   - Si ya existe: verifica `stat().st_mode & 0o777 == 0o600`; si no, fuerza `os.chmod(path, 0o600)` y emite `logger.warning`.
   - Escribe usando `fcntl.flock(fd, LOCK_EX)` durante el `json.dumps(record) + "\n"`. `flock` es POSIX-only (acepta el límite, este código corre solo en VPS Linux).
   - `try/finally` para liberar `LOCK_UN`.

### Test nuevo: `tests/test_trace.py`

Mínimo 6 casos:

1. `append_delegation` crea archivo con permisos 600.
2. Escribe línea JSON válida con `ts` y `trace_id` autogenerados.
3. Respeta `trace_id` provisto.
4. Trunca `summary` a 200 chars.
5. Rechaza claves prohibidas (`text`, `secret`, `token`, `api_key`, `password`).
6. Concurrencia: 10 threads escriben 10 registros cada uno → archivo final tiene 100 líneas válidas, ninguna corrupta (parse `json.loads` por línea).

Usar `tmp_path` fixture para aislar.

## Plan de ejecución (Copilot-VPS)

1. **Pull en VPS:** `cd /home/rick/umbral-agent-stack && git pull origin main`.
2. **Branch local:** `git checkout -b copilot-vps/ola-1b-trace-helper`.
3. **Implementar** `worker/tasks/_trace.py` + `tests/test_trace.py`.
4. **Tests locales:** `source .venv/bin/activate && python -m pytest tests/test_trace.py -v` → todos verdes.
5. **No restart aún** — el helper no se usa hasta Task 011. Solo deploy de código.
6. **Commit + push** a `copilot-vps/ola-1b-trace-helper`.
7. **Abrir PR** a `main` con cuerpo enlazando a esta task y al ADR 05.
8. **Reporte de cierre** en este archivo (sección §6 abajo).

## Quality gate de la task

- ✅ `pytest tests/test_trace.py -v` → 6/6 verdes.
- ✅ `worker/tasks/_trace.py` no excede 100 líneas.
- ✅ Sin imports nuevos de terceros (solo stdlib: `os`, `fcntl`, `json`, `uuid`, `pathlib`, `datetime`, `logging`).
- ✅ Permisos 600 verificados en test.
- ✅ Concurrencia 100 escrituras sin corrupción.
- ✅ Cumple `secret-output-guard` (rechaza claves sensibles, no loggea contenido).

## Reportar al cerrar (§6)

Pegar al final de este archivo:

- Commit hash del PR mergeado.
- Output de `pytest tests/test_trace.py -v`.
- `ls -la ~/.local/state/umbral/` (debe NO existir aún si no se invocó el helper en runtime).
- Confirmación de que `umbral-worker.service` NO fue reiniciado (no hace falta).
