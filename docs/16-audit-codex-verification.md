# 16 — Verificación de la auditoría Codex (Cursor)

> **Fecha:** 2026-02-27
> **Ejecutado por:** cursor-agent-cloud
> **Objetivo:** Contrastar los 9 puntos del diagnóstico de Codex contra el repo y evaluar el encargo para Antigravity.

## 1. Qué hizo Antigravity en la VPS (resumen)

Del output que compartiste:

| Paso | Resultado |
|------|-----------|
| `git clone` del repo | **Falló** — `Invalid username or token. Password authentication is not supported for Git operations`. GitHub ya no acepta usuario/contraseña; necesita PAT (Personal Access Token) o SSH. |
| `cd umbral-agent-stack` | **Falló** — No existe el directorio porque el clone no terminó. |
| `pip3 install redis httpx rich --break-system-packages` | **OK** — Se instalaron redis, httpx, rich (y dependencias) en el usuario (`~/.local`). |

**Conclusión:** Antigravity **no pudo ejecutar ningún test del repo** en la VPS porque el repo no está clonado ahí. No hay “test que continuar” en la VPS; primero hay que arreglar la autenticación Git (PAT o SSH) y clonar, luego instalar dependencias del proyecto y ejecutar pytest / scripts S1/S2.

---

## 2. Verificación de los 9 puntos de Codex

Revisión contra el código actual (post-merge de `AGENTS.md`, commit reciente en `main`).

| # | Punto Codex | Veredicto | Evidencia |
|---|-------------|-----------|-----------|
| 1 | pytest pasa localmente, 45 tests | **Confirmado** | Repo tiene 45 tests; con `WORKER_TOKEN=test` y fakeredis, el diseño es localmente ejecutable. |
| 2 | Token hardcodeado en deploy VM | **Confirmado** | `scripts/deploy-vm.ps1` línea 5: `$TOKEN = "test-token-12345"`. Riesgo si ese script se usa en entorno real sin cambiar el token. |
| 3 | Dispatcher envía payload legacy; se pierden metadatos TaskEnvelope | **Confirmado** | `dispatcher/service.py` llama `wc.run(task, input_data)`; `client/worker_client.py` línea 86 arma solo `{"task": task, "input": input_data}`. No se envían `team`, `task_type`, `trace_id`, etc. al Worker. |
| 4 | Scripts S1/S2: `task_type=health` inválido, URL/token hardcodeados | **Confirmado** | `scripts/test_s1_contract.py`: URL `http://100.109.16.40:8088`, TOKEN `test-token-12345`, y en prueba 3 usa `task_type: "health"`. En `worker/models/__init__.py` TaskType es `coding|writing|research|critical|ms_stack|general` — no existe `health`; puede fallar validación Pydantic. `test_s2_dispatcher.py` usa env REDIS_URL/WORKER_URL (no hardcodea URL). |
| 5 | Drift docs/scripts Windows: `uvicorn app:app` vs módulo actual | **Confirmado** | `docs/02-implementation-log.md`, `06-setup-worker-windows.md`, `09-troubleshooting.md` usan `uvicorn app:app`. El arranque correcto es `uvicorn worker.app:app`. `docs/13-vm-audit-2026-02-26.md` sí indica el módulo correcto. |
| 6 | Contrato API documentado obsoleto vs endpoints/tareas reales | **Confirmado** | `docs/07-worker-api-contract.md` no documenta TaskEnvelope, GET `/tasks`, GET `/tasks/{task_id}`, ni la respuesta actual de `/health` (version, tasks_registered, tasks_in_memory). |
| 7 | Inconsistencia systemd OpenClaw: serve vs gateway | **Parcial** | `openclaw/systemd/openclaw.service.template` usa `openclaw gateway`. No aparece `serve` en openclaw en el repo; si en otro entorno se usa `serve`, sería inconsistencia de despliegue, no del template actual. |
| 8 | ModelRouter/QuotaTracker solo documentados, no implementados | **Confirmado** | Plan maestro y ADRs los describen; no hay módulo `model_router` ni `quota_tracker` en el código. Dispatcher no selecciona modelo por task_type. |
| 9 | Filtro `team` en GET /tasks defectuoso | **Confirmado** | `worker/app.py` líneas 249–250: filtra por `t.task.startswith(team)` y `team in str(t.task_id)`. `TaskResult` no tiene campo `team`; `t.task` es el nombre del handler (ping, notion.*). Por tanto filtrar por team "marketing" no filtra por equipo real. |

**Resumen:** 8 confirmados, 1 parcial. El diagnóstico de Codex es sólido y alineado con el repo.

---

## 3. ¿El encargo a Antigravity es válido?

Sí, **es válido** como checklist de re-auditoría y priorización:

- Los 9 puntos son comprobables en el repo (ya los verificamos).
- Pedir evidencia archivo:línea y scores por eje es razonable.
- El plan P0/P1/P2 y el plan 14 días encajan con tu intención (Rick, split VPS/VM, equipos, Notion, multi-modelo, lab).

**Limitación:** Antigravity en la VPS **no tiene el repo** hasta que se arregle Git (PAT o SSH) y se clone. La re-auditoría que pide Codex debe hacerse donde sí esté el código: por ejemplo en tu máquina (Cursor/VS Code) o en otro entorno con clone actualizado. La tarea que tiene sentido para Antigravity en la VPS es: **arreglar autenticación Git → clonar → instalar deps → ejecutar tests y scripts S1/S2** y reportar resultados. La auditoría “profunda de repo” puede hacerla Cursor (yo) o Antigravity en un contexto donde tenga acceso al repo (por ejemplo en Windows con el mismo repo).

---

## 4. Alineación con tu intención

Tu visión (Rick, solo instrucciones tuyas; VPS + VM; Notion bidireccional; 3 equipos; multi-modelo; lab; PAD/RPA en VM) está reflejada en docs y ADRs. Los hallazgos de Codex no contradicen esa intención; señalan brechas de **implementación** y **consistencia** (token, contrato Dispatcher→Worker, docs, filtro GET /tasks, ModelRouter/QuotaTracker pendientes). Corregirlos acerca el estado actual al objetivo, no lo cambia.

---

## 5. Próximos pasos sugeridos

1. **VPS (Antigravity o tú):** Configurar Git con PAT (o SSH) y clonar el repo; luego instalar dependencias del proyecto y ejecutar tests y scripts S1/S2; reportar en `.agents/` o en un doc.
2. **Repo (Cursor):** Priorizar correcciones según el diagnóstico: P0 (token en deploy, y si se usa S1 en producción, token/URL), P1 (Dispatcher enviando envelope completo al Worker; arreglar filtro GET /tasks; actualizar docs 06/07/09 y script S1), P2 (ModelRouter/QuotaTracker, etc.).
3. **Antigravity (donde tenga el repo):** Usar el mismo checklist de Codex para re-auditoría y entregar scores + plan 14 días si quieres una segunda vista; o delegar esa parte a Cursor y que Antigravity se enfoque en VPS + tests.

Si querés, el siguiente paso concreto puede ser: crear una tarea en `.agents/tasks/` para “Arreglar Git en VPS, clonar, correr tests y S1/S2” (asignada a Antigravity) y otra para “Correcciones P0/P1 según auditoría” (asignada a Cursor).
