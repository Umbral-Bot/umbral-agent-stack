---
id: "2026-02-27-001"
title: "VPS: arreglar Git (PAT/SSH), clonar repo, instalar deps y ejecutar tests"
status: pending
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

- [ ] En la VPS, Git configurado con PAT o SSH para `github.com` / org `Umbral-Bot`.
- [ ] Repo clonado: `git clone https://github.com/Umbral-Bot/umbral-agent-stack.git` (o equivalente SSH) en un directorio conocido.
- [ ] Dependencias instaladas desde el repo (ej. `pip3 install -r worker/requirements.txt` o las que usen los tests).
- [ ] Ejecutar tests: `WORKER_TOKEN=test python -m pytest tests/ -q` (o equivalente) y anotar resultado (X passed, Y failed).
- [ ] Si hay Redis en la VPS, ejecutar script S2: `REDIS_URL=... WORKER_URL=... WORKER_TOKEN=... python scripts/test_s2_dispatcher.py` y anotar resultado.
- [ ] Añadir una entrada en el Log de este archivo con: resultado de pytest, resultado de S2 (si aplica), y cualquier error o bloqueo.

## Referencias

- Verificación auditoría Codex: `docs/16-audit-codex-verification.md`
- Protocolo agentes: `.agents/PROTOCOL.md`
- Tests: `tests/`, scripts: `scripts/test_s1_contract.py`, `scripts/test_s2_dispatcher.py`

## Log

### [cursor] 2026-02-27

Tarea creada tras verificar el output de Antigravity en la VPS. El clone falló por auth; no se ejecutó ningún test del repo. Objetivo: dejar la VPS en estado de repo clonado + tests ejecutables y documentar resultados.
