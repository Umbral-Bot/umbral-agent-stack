---
id: "2026-03-07-099"
title: "Fix token mismatch Dispatcher→Worker (P0 auditoría 2026-03-07)"
status: done
assigned_to: cursor
created_by: claude-code
priority: high
sprint: R21
created_at: 2026-03-07T22:45:00-03:00
updated_at: 2026-03-08T12:50:00-03:00
---

## Objetivo

Resolver el problema crítico descubierto en la auditoría comprensiva 2026-03-07:
el **Dispatcher no puede despachar tareas** porque su `WORKER_TOKEN` no coincide
con el token configurado en el Worker VPS (401 Unauthorized).

Mientras no se resuelva, el sistema procesa **0 tareas/día** vía Redis pipeline.

## Contexto

Auditoría en vivo (2026-03-07) reveló:

- **VPS Worker** corre en `http://127.0.0.1:8088` — arrancado por supervisor.sh
- **Dispatcher** usa `WORKER_TOKEN` del env para POST /run
- Ambos leen de `~/.config/openclaw/env` pero el token difiere entre lo que el
  dispatcher ve y lo que el worker fue inicializado con
- OpsLog (`~/.config/umbral/ops_log.jsonl`, 213 eventos): `task_failed` por 401
  en casi todas las entradas recientes
- Prueba directa: `source ~/.config/openclaw/env && curl ... Bearer $WORKER_TOKEN` → 200 OK
  Pero el Dispatcher → 401 (posiblemente el `export` prefix causa diferencia al leer)
- VM worker (100.109.16.40:8088) también rechaza con 401 — mismo problema

Documentos de referencia:
- `docs/audits/audit-results-2026-03-07.md` — scorecard completo
- `docs/audits/audit-plan-2026-03-comprehensive.md` — metodología

## Diagnóstico sugerido

En VPS, comparar el token que usa el Dispatcher vs el que acepta el Worker:

```bash
# 1. Ver cómo carga el env el Dispatcher
grep -n "environ\|WORKER_TOKEN\|env_file\|load_env" ~/umbral-agent-stack/dispatcher/service.py | head -20

# 2. Ver cómo arranca el worker (supervisor.sh)
grep -A5 "uvicorn\|WORKER_TOKEN" ~/umbral-agent-stack/scripts/vps/supervisor.sh

# 3. Comparar tokens (lengths, prefixes)
python3 -c "
import os, re
with open(os.path.expanduser('~/.config/openclaw/env')) as f:
    content = f.read()
tokens = re.findall(r'(?:export\s+)?WORKER_TOKEN=(.*)', content)
print('All WORKER_TOKEN occurrences:', [(t[:4]+'...'+t[-2:], len(t)) for t in tokens])
"
```

## Hipótesis más probable

El env file tiene `export WORKER_TOKEN=xxx` con el `export` prefix. El Dispatcher
lo lee con un método que no maneja `export` (e.g., `os.environ.get` after parsing
sin strip del prefix), o hay dos ocurrencias con valores distintos y la "última
gana" logic no funciona correctamente para el Dispatcher.

## Criterios de aceptación

- [ ] Identificado exactamente por qué el Dispatcher obtiene un token diferente al del Worker
- [ ] Fix aplicado (puede ser: corregir parsing de env en dispatcher, o unificar tokens)
- [ ] Test manual: encolar tarea `ping` via Redis → resultado OK en `umbral:task:{id}:result`
- [ ] OpsLog muestra `task_completed` (no `task_failed` por 401)
- [ ] PR con el fix, tests pasan

## Acciones secundarias (mismo sprint si hay tiempo)

- [ ] **Habilitar SSH en VM** (instrucciones en `audit-results-2026-03-07.md` §P1)
  — requiere que David entre por Hyper-V GUI y ejecute los comandos
- [ ] **Sincronizar branch** VPS `rick/vps` con `main` post-merge de PR #106
- [ ] **VM_TOKEN**: agregar en VPS env el token correcto para la VM worker
  (actualmente `VM_TOKEN=` está vacío; el Dispatcher usa el mismo WORKER_TOKEN para VM)

## Log

### [claude-code] 2026-03-07 22:45 -03:00
Tarea creada post-auditoría comprensiva.
Auditoría ejecutada en vivo: SSH VPS, HTTP VM worker.
Findings documentados en `docs/audits/audit-results-2026-03-07.md`.
PR #106 contiene plan de auditoría + resultados.
El token mismatch es el bloqueante P0 del sistema completo.

### [claude-code] 2026-03-08 12:50 -03:00
**RESUELTO.**

Causa raíz confirmada vía `/proc/PID/environ`:

- Dispatcher (arrancado 2026-03-04): token `!EN6V4zt...` (25 chars) — VIEJO
- Worker VPS (arrancado 2026-03-07): token `64e38901...` (48 chars) — ACTUAL del env
- El env file se actualizó entre el 4 y el 7 de marzo, pero el Dispatcher nunca se reinició

Fix aplicado: Dispatcher reiniciado en VPS con env completo (`set -a; source ~/.config/openclaw/env; set +a`).

Verificación E2E: `ping` encolado via `TaskQueue.enqueue()` → Dispatcher procesó en ~28s → `task_completed | ping | 2026-03-08T15:48:49` en OpsLog. **Pipeline Redis → Dispatcher → Worker funcional.**

Nota futura: el supervisor.sh solo verifica que el proceso existe, no que el token es correcto. Si el env se actualiza, hay que reiniciar el Dispatcher manualmente (o agregar al supervisor un health-check funcional tipo POST /run ping).
