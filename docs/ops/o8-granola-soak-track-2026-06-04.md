# O8 — Granola soak track (2026-06-04)

- **Veredicto Cursor (sin VPS en este turno):** `GRANOLA_SOAK_DEGRADED` — heredado de D5.3; **requiere** corrida fresca Copilot-VPS
- **Separado de:** D5.3 poll bootstrap (`D53_RUNTIME_APPLIED_OK`) — poller comentarios OK ≠ pipeline Granola capitalización

## Estado conocido (evidence última corrida)

| Señal | Estado |
|-------|--------|
| `notion.poll_comments` / poller | OK post-5e (pid, cursor_used) |
| `ops_log` eventos Granola Jun 01–02 | Sin actividad reciente (D53 diag) |
| Soak histórico | `D53_GRANOLA_SOAK_DEGRADED` |

## Objetivo O8

Cerrar O8a (métricas truncamiento), O8d (validador automático), decisión O8f (capitalización hooks) — ver spine `notion-governance` D5.3.

## Prompt Copilot-VPS (ejecutar David)

```text
Sos Copilot-VPS. O8 Granola soak read-only — corrida fresca 2026-06-04.
Responder en espanol. NO restart poller/worker salvo: autorizo restart O8 soak

EV=~/.coord-ag-evidence/O8
mkdir -p "$EV"
date -Iseconds | tee "$EV/run-start.txt"

# 1) Poller vivo (no confundir con Granola)
pgrep -af notion_poller | tee "$EV/poller-ps.txt"
redis-cli GET "notion:poll:cursor:$(echo PAGE_ID_CONTROL_ROOM)" 2>/dev/null | head -c 200 | tee "$EV/sample-cursor.txt" || true

# 2) ops_log Granola últimos 7 días
grep -i granola ~/.config/umbral/ops_log.jsonl 2>/dev/null | tail -50 | tee "$EV/ops-log-granola-tail.txt"
wc -l "$EV/ops-log-granola-tail.txt" | tee "$EV/ops-log-granola-count.txt"

# 3) Worker health
curl -sf http://127.0.0.1:8088/health | tee "$EV/worker-health.json"

# 4) Si existe script soak Granola en repo, ejecutar read-only
cd ~/umbral-agent-stack
git log -1 --oneline | tee -a "$EV/run-start.txt"
ls scripts/vps/*granola* scripts/**/*granola* 2>/dev/null | tee "$EV/granola-scripts.txt"

Criterio GRANOLA_SOAK_OK:
- ops_log con eventos Granola recientes O script soak documenta OK explícito
- sin error auth Notion en worker

Si ops_log vacío y sin pipeline Granola activo: GRANOLA_SOAK_DEGRADED + 3 bullets causa.

VEREDICTO: GRANOLA_SOAK_OK | GRANOLA_SOAK_DEGRADED
```

## Acción tras veredicto

| Resultado | Siguiente |
|-----------|-----------|
| OK | Actualizar spine O8a; charter validador O8d |
| DEGRADED | Issue Linear/Notion; no bloquear D3.6 ni editorial HITL |

## Referencias

- `docs/ops/d53-poll-bootstrap-followup-2026-06-02.md`
- `notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md` D5.3
