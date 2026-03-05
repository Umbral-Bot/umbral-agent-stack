# Task R13 — Runbook operacional y checklist de gobernanza

**Fecha:** 2026-03-04  
**Ronda:** 13  
**Agente:** GitHub Copilot / Antigravity / Cursor Agent Cloud  
**Branch:** `feat/operational-runbook`

---

## Contexto

El responsable de mantenimiento del sistema debe poder **revisar qué hacer y cómo evaluar** las operaciones. Hoy existen scripts dispersos (supervisor, dashboard, quota report, OODA, E2E validation) pero no hay un documento único que consolide procedimientos y checklist de gobernanza.

**Objetivo:** Crear un runbook operacional que documente procedimientos de mantenimiento y qué revisar para evaluar operaciones y medir estrategias.

---

## Tareas requeridas

### 1. `docs/62-operational-runbook.md`

Documento maestro con:

#### 1.1 Procedimientos de mantenimiento diario/semanal

| Procedimiento | Frecuencia | Comando / Script | Qué verificar |
|---------------|------------|------------------|---------------|
| Verificar salud de servicios | Diario | `scripts/vps/supervisor.sh` | Redis, Worker, Dispatcher UP |
| Dashboard Notion | Cada 15 min (cron) | `scripts/dashboard_report_vps.py` | Tareas recientes, estado |
| Quota report | Semanal | `scripts/quota_usage_report.py --notion` | Uso vs límites |
| OODA report | Semanal | `scripts/ooda_report.py --format markdown` | Resumen semanal |
| E2E validation | Diario o on-demand | `scripts/e2e_validation.py` | Enqueue, task history, Notion |
| Secrets audit | Mensual | `python scripts/secrets_audit.py` | Sin secretos en código |

#### 1.2 Checklist de gobernanza (qué revisar para medir estrategias)

- [ ] Ejecutar `scripts/governance_metrics_report.py --days 7` (cuando exista) o `scripts/ooda_report.py`
- [ ] Revisar tasa de éxito por team y por task
- [ ] Revisar uso de modelos (¿se está usando el routing esperado?)
- [ ] Revisar tareas fallidas: causas recurrentes
- [ ] Revisar ops_log: ¿trace_id presente? ¿eventos completos?
- [ ] Revisar Notion Control Room: tareas pendientes, bloqueos

#### 1.3 Troubleshooting común

| Síntoma | Qué revisar | Acción |
|---------|-------------|--------|
| Worker no responde | `curl http://127.0.0.1:8088/health` | Restart vía supervisor |
| Redis down | `redis-cli ping` | Reiniciar Redis |
| Cuota excedida | `GET /quota/status` | Ajustar quota_policy o esperar reset |
| Notion no actualiza | NOTION_API_KEY, NOTION_TASKS_DB_ID | Verificar credenciales |
| Langfuse sin traces | LANGFUSE_* env | Opcional; graceful degradation |

#### 1.4 Rutas de API relevantes para gobernanza

| Endpoint | Descripción |
|----------|-------------|
| GET /health | Estado del Worker |
| GET /task/{id}/status | Estado de tarea |
| GET /task/history | Historial paginado |
| GET /quota/status | Uso de cuotas |
| GET /providers/status | Estado de providers |
| GET /tools/inventory | Tasks y skills registrados |

---

### 2. Actualizar `.agents/board.md`

Agregar referencia al runbook en la sección de estado del sistema:
```markdown
| Runbook operacional | docs/62-operational-runbook.md |
```

---

## Criterios de éxito

- [ ] `docs/62-operational-runbook.md` — documento completo
- [ ] Procedimientos de mantenimiento documentados
- [ ] Checklist de gobernanza incluido
- [ ] Sección de troubleshooting
- [ ] Board actualizado
- [ ] PR abierto a `main`
