# Mission Control — Architecture

Estado: MVP (S2 del Plan Q2-2026, sub-objetivo O13.1).
Decisiones congeladas: [`ADR-009`](../adr/ADR-009-mission-control-scope.md).

## Componentes

```
┌─────────────────────────────────────────────────────────────┐
│   Browser (David)                                            │
│   http://127.0.0.1:8089/  + Bearer MISSION_CONTROL_TOKEN     │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTMX poll cada 10-30s
                  ▼
┌─────────────────────────────────────────────────────────────┐
│   mission_control.app  (FastAPI :8089, bind 127.0.0.1)       │
│   ─ /health  (anónimo)                                       │
│   ─ /agents, /quotas, /queue, /tournaments  (bearer)         │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
   adapters/          adapters/           adapters/
   openclaw.py        redis_queue.py      quota.py
       │                  │                   │
       ▼                  ▼                   ▼
   ~/.openclaw/       redis://localhost   ~/.config/openclaw/
   openclaw.json      :6379/0             claude-quota-state.json
                       (compartido con
                        dispatcher)
```

## Principios

1. **Read-only**: ninguno de los adapters modifica las fuentes. Si una fuente no
   existe, el endpoint devuelve `available: false` + error legible (no 500).
2. **Fail-closed en auth**: si `MISSION_CONTROL_TOKEN` no está seteado, todas las
   rutas autenticadas responden 503. Nunca un dashboard sin auth por accidente.
3. **Aislamiento de runtime**: corre en su propio service `mission-control.service`,
   en su propio puerto (8089), con su propio token. Restart no afecta worker
   ni dispatcher.
4. **Persistencia mínima**: estado vivo en Redis (futuro), snapshots a filesystem.
   No se crea DB nueva (D5).

## Quality gate (D6)

Métrica de retención del MVP: `mc:views:{YYYY-MM-DD}` en Redis, incrementado por
middleware en cada hit a `/`. Si tras 3 días post-deploy el conteo medio es <2/día,
se revierte el systemd unit y se congela O13.3-O13.5.

## Lo que NO hace

- No spawnea agentes (eso queda en O13.4 si se llega).
- No mata procesos (eso queda en O13.5 si se llega).
- No reemplaza GitHub UI ni Notion `Mejora Continua`.
- No escribe en `openclaw.json` ni en config files.

## Próximos pasos (post-MVP, condicionales)

- O13.3 — definir formato sandbox tournaments.
- O13.4 — endpoint `/tournament/launch` (write).
- O13.5 — kill switch + alertas.
- O13.8 — integración Notion (Q3, no Q2).
