---
id: "2026-02-27-001"
title: "VPS: arreglar Git (PAT/SSH), clonar repo, instalar deps y ejecutar tests"
status: done
assigned_to: antigravity
created_by: cursor
priority: high
sprint: S2
created_at: "2026-02-27"
updated_at: "2026-02-27"
---

## Objetivo

En la VPS (Hostinger) el clone del repo falló por autenticación Git. Hay que configurar acceso (PAT o SSH), clonar `umbral-agent-stack`, instalar dependencias del proyecto y ejecutar tests y scripts S1/S2. Reportar resultados.

## Contexto

- Antigravity intentó clonar y obtuvo: `Password authentication is not supported for Git operations` / `Authentication failed`.
- GitHub exige Personal Access Token (PAT) o SSH para HTTPS clone en repos privados.
- Después del clone, el directorio `umbral-agent-stack` no existía, por eso no se pudo correr ningún test del repo.
- Dependencias ya instaladas en la VPS (por pip3): redis, httpx, rich. Falta clonar y usar los `requirements.txt` del repo (worker, dispatcher, tests).

## Criterios de aceptación

- [x] En la VPS, Git configurado con PAT o SSH para `github.com` / org `Umbral-Bot`.
- [x] Repo clonado: `git clone https://github.com/Umbral-Bot/umbral-agent-stack.git` (o equivalente SSH) en un directorio conocido.
- [x] Dependencias instaladas desde el repo (ej. `pip3 install -r worker/requirements.txt` o las que usen los tests).
- [x] Ejecutar tests: `WORKER_TOKEN=test python -m pytest tests/ -q` (o equivalente) y anotar resultado (X passed, Y failed).
- [x] Si hay Redis en la VPS, ejecutar script S2: `REDIS_URL=... WORKER_URL=... WORKER_TOKEN=... python scripts/test_s2_dispatcher.py` y anotar resultado.
- [x] Añadir una entrada en el Log de este archivo con: resultado de pytest, resultado de S2 (si aplica), y cualquier error o bloqueo.

## Referencias

- Verificación auditoría Codex: `docs/16-audit-codex-verification.md`
- Protocolo agentes: `.agents/PROTOCOL.md`
- Tests: `tests/`, scripts: `scripts/test_s1_contract.py`, `scripts/test_s2_dispatcher.py`

## Log

### [cursor] 2026-02-27

Tarea creada tras verificar el output de Antigravity en la VPS. El clone falló por auth; no se ejecutó ningún test del repo. Objetivo: dejar la VPS en estado de repo clonado + tests ejecutables y documentar resultados.

### [antigravity] 2026-02-27 13:06

1. **Autenticación Git SSH configurada**: Se generó llave ed25519 en la VPS alojada en Hostinger y el desarrollador la añadió como *Deploy Key* en GitHub sin acceso de escritura temporal para habilitar el copiado seguro y autorizado con Git Pull/Clone.
2. **Repositorio descargado**: Debido a que ya había un directorio con código obsoleto local en VPS, se usó Git Checkouts y Git Pull sobre los remotos a SSH (`git@github.com:Umbral-Bot/umbral-agent-stack.git`) actualizandolo con las revisiones origin/main actualizadas al 27 de febrero.
3. **Dependencias**: Se creó virtualenv local `.venv` debido a restricciones de Python global manejado por apt `externally-managed-environment`. Dentro del entorno fueron instalados `worker/requirements.txt`, `dispatcher/requirements.txt`, `pytest` y dependencias adicionales omitidas.
4. **Pytest Run Results**:
   **Ejecutado**: `WORKER_TOKEN=test python -m pytest tests/ -q`
   **Resultados**: ✅ 45 passed in 1.30s
5. **test_s2_dispatcher.py Run Results**:
   **Ejecutado**: `REDIS_URL=redis://localhost:6379/0 WORKER_URL=http://localhost:8088 WORKER_TOKEN=test python scripts/test_s2_dispatcher.py` (Se tuvo que instalar Rich adicionalmente previamente).
   **Resultados**:
   ✅ `[1s] Status: done`
   `Result: {"ok": true, "task_id": "199a182f...b22f0622597", "task": "ping" }`
   La prueba S2 resultó Exitosa comunicándose Correctamente contra el Worker Local por encoladores Redis confirmando Dispatching Completado.
