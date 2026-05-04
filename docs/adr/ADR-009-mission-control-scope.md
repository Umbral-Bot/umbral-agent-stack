# ADR-009: Mission Control para OpenClaw — scope MVP

## Estado

Accepted — 2026-05-04

Deriva de: O13.0 del Plan Q2-2026 Platform-First (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`, sección O13). Esta ADR cierra el sub-objetivo `O13.0`. Las decisiones que congela habilitan el arranque de `O13.1` (dashboard read-only) en sesión S2.

## Contexto

El stack OpenClaw vive disperso entre:

- 74+ skills en `umbral-agent-stack/openclaw/workspace-templates/skills/` (incluye `openclaw-gateway`, `subagent-result-integration`, `granola-pipeline`, `multi-agent-tournament-orchestrator` planeada en O7).
- `openclaw.json` en VPS (`~/.openclaw/openclaw.json`, 1915 bytes) con agentes, bindings, channels.
- `config/teams.yaml` con 5 equipos (marketing, advisory, improvement, lab, system).
- Dispatcher + Worker FastAPI en `umbral-agent-stack` (port 8088) + Redis (port 6379).
- `scripts/openclaw-claude-quota.py` con fallback automático cuando se agota cuota Claude Pro.
- Tournaments O7 que lanzarán N sub-agentes Copilot CLI en sandboxes paralelos.

Sin una superficie unificada, cada operación requiere SSH al VPS + `cat openclaw.json` + `journalctl -u openclaw-gateway` + `redis-cli` + verificación Notion manual. Inviable a escala de 3 tournaments/semana (objetivo O7).

El Plan Q2 identificó 4 dimensiones de scope que requerían decisión antes de empezar a codear (O13.0): frontend, ubicación del código, auth, persistencia. Adicionalmente la pasada profunda del review 2026-04-30 levantó el riesgo de **over-engineering O13** y exigió un MVP estrictamente definido con quality gate de revert.

## Decisión

### D1 — Scope MVP estricto: dashboard read-only

El MVP de Mission Control es **únicamente lectura**. Cubre los sub-objetivos:

- `O13.1` — Dashboard FastAPI + HTMX con endpoints `/health`, `/agents`, `/quotas`, `/tournaments`, `/queue`.
- `O13.2` — Integración OpenClaw Gateway (lectura de `openclaw.json` + `sessions_list`).
- `O13.6` — Display de quotas (lectura de `scripts/openclaw-claude-quota.py`, sin bloqueo automático).
- `O13.7` — Documentación + runbook básico.

**Stretch (NO entran en MVP):**

- `O13.3` Sandbox de tournaments y `O13.4` Dispatcher: solo si retro S2 confirma que el dashboard se está mirando ≥2x/día (ver D6).
- `O13.5` Kill switch + alertas: post-MVP, condicionado a haber operado al menos 1 tournament real con dispatcher.
- `O13.8` Integración Notion (Mejora Continua, Asistentes Notion): Q3, no Q2.

Razón: el riesgo identificado en el plan ("FastAPI + dispatcher + sandboxes consume más tiempo del planeado") se mitiga sólo si el dispatcher requiere **evidencia de uso real** del dashboard antes de construirse. Construir dispatcher sin dashboard mirado es resolver un problema que no existe.

### D2 — Frontend: FastAPI + HTMX local en `:8089`

Opción (b) del plan. Stack ya conocido (FastAPI + Pydantic + uvicorn vive en `worker/` y `dispatcher/`). HTMX para interactividad mínima sin SPA. Vista accesible desde browser sin instalar nada en cliente. Reutiliza patrones de templates Jinja2 si hacen falta vistas más ricas.

**Descartadas:**

- (a) Panel CLI Python + Rich: no resuelve "vista cruzada", obliga a abrir terminal cada vez, no compartible vía URL.
- (c) Extender el worker existente: acopla observabilidad con ejecución, viola separación de responsabilidades, complica restart/deploy.

### D3 — Ubicación: `umbral-agent-stack/mission_control/` (módulo nuevo, mismo repo)

Anti-sprawl. Convive con `worker/`, `dispatcher/`, `openclaw/`, `identity/`, `client/`. Compartirá `pyproject.toml`, `.venv`, pre-commit hooks, tests bajo `tests/mission_control/`.

Estructura mínima propuesta:

```
mission_control/
├── __init__.py
├── app.py              # FastAPI entrypoint (puerto 8089)
├── routes/
│   ├── health.py
│   ├── agents.py
│   ├── quotas.py
│   ├── tournaments.py
│   └── queue.py
├── adapters/
│   ├── openclaw.py     # lee openclaw.json + sessions_list
│   ├── redis_queue.py  # cuenta tasks pendientes/in-flight/dead-letter
│   └── quota.py        # invoca scripts/openclaw-claude-quota.py
├── templates/          # HTMX (Jinja2)
├── snapshots/          # git-ignored (ver D5)
└── README.md
```

systemd user unit nueva: `mission-control.service` (siguiendo el mismo patrón que `umbral-worker.service` y `openclaw-dispatcher.service`).

### D4 — Auth: `MISSION_CONTROL_TOKEN` separado de `WORKER_TOKEN`

Token nuevo, separado. Permite revocar Mission Control sin romper Worker, y permite que David lea el panel desde browser local sin exponer el token de ejecución de tareas. Bearer header en todas las rutas excepto `/health` (anónimo, para healthchecks externos).

MVP es local-only (`bind 127.0.0.1:8089`); aún así el token es obligatorio para evitar que cualquier proceso local lea estado operativo. Si más adelante se expone vía túnel SSH, la separación de tokens ya está en su lugar.

### D5 — Persistencia: Redis efímero + snapshots filesystem (sin DB nueva)

Estado vivo en Redis (claves `mc:*` con TTL). Snapshots cada N minutos a `mission_control/snapshots/YYYY-MM-DD/HHMM.json`, git-ignored.

**No se crea DB nueva** (Postgres, SQLite, etc.). Si en Q3 se quiere histórico consultable, se evalúa entonces — el MVP no lo necesita.

### D6 — Quality gate de continuación (revert criteria)

Criterio binario para decidir si seguir construyendo el resto de O13 después del MVP:

- En la retro de S2 (post-`O13.1`+`O13.2`), si el dashboard **no se está mirando ≥2x/día durante los 3 días posteriores al deploy**, congelar O13.3-O13.5.
- "Mirar" cuenta como: David abre la URL, o un agente la lee programáticamente. Se mide vía counter en Redis (`mc:views:{date}`).
- Si se congela: operar SSH+manual hasta retro de S3. Si en S3 sigue sin uso, archivar el módulo y revertir la unit systemd.

### D7 — Capitalización (skills) condicional

Las dos skills planeadas se crean **sólo cuando hay consumidor real**:

- `mission-control-operator`: se capitaliza la primera vez que un agente externo (Codex u otro) la invoca para algo no-trivial. Si nadie la invoca en Q2, no se crea.
- `tournament-sandbox-design`: se capitaliza recién cuando se ejecuta el primer tournament real (depende de O7+O13.3). Si O13.3 queda fuera de scope por D6, esta skill tampoco se crea.

Esto cumple la regla anti-sprawl §6 del plan ("usar ≥1 vez en Q2 o entra a `experimental`") sin pre-capitalizar especulativamente.

## Consecuencias

### Positivas

- Camino claro y acotado para `O13.1` (S2): la sesión arranca sin re-discutir frontend/auth/ubicación.
- Mitigación explícita del riesgo "O13 over-engineering" levantado en pasada profunda 2026-04-30.
- Separación limpia entre lo que Mission Control hace (observa) y lo que NO hace (ejecuta agentes — eso sigue en Worker + OpenClaw Gateway + sub-agentes Copilot CLI).
- O7 no queda bloqueado: el primer tournament S2 puede ejecutarse manual (modo declarado en plan O7); el dispatcher de O13.4 sólo se construye si hay demanda probada.

### Negativas / aceptadas

- El MVP read-only no resuelve por sí solo el problema de "lanzar tournaments con cap y kill switch". Se acepta porque resolver ese problema requiere primero verificar que el dashboard se usa.
- Snapshot a filesystem en lugar de DB significa que análisis histórico fuera del día corriente requiere cargar JSONs manualmente. Aceptable para Q2.
- Dos tokens (`WORKER_TOKEN` + `MISSION_CONTROL_TOKEN`) aumentan superficie de gestión de secretos. Mitigación: ambos van al mismo `.env` con el mismo lifecycle de rotación.

### Lo que NO se decide en esta ADR

- Diseño detallado del schema de respuesta de cada endpoint (se define en `O13.1` con tests).
- Diseño de los sandboxes de tournaments (se define en `O13.3` si se llega).
- Política de retención de snapshots (se define cuando se acumulen ≥30 días).
- Integración con Notion `Mejora Continua` / `Asistentes Notion` (postergada a Q3 por D1).

## Dependencias

- **Bloquea:** O13.1, O13.2, O13.6, O13.7. O7 modo Mission Control (D6).
- **Depende de:** O1 (commits workspace-templates limpios — ✅ cerrado 2026-04-30 vía commit `76fde13` + ADR-003 codex-wip-resolution). O3.0 (registry de agentes — 🟡 partial al 2026-05-04, suficiente para listar lo que hay).

## Referencias

- Plan Q2: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` §O13.
- Riesgo "O13 over-engineering": mismo plan, tabla §riesgos.
- Retro Q2-W1 closeout: `notion-governance/docs/roadmap/retros/2026-05-01-friday-retro.md`.
- ADR-003 codex-wip-resolution: precedente de cierre defensivo de O1.
- ADR-002 notion-vs-queue: precedente de separación de canales.
- Skill `openclaw-gateway`: `umbral-agent-stack/openclaw/workspace-templates/skills/openclaw-gateway/`.
- Script de quota: `umbral-agent-stack/scripts/openclaw-claude-quota.py`.
