---
id: "2026-03-22-002"
title: "Super diagnóstico exhaustivo del sistema Umbral Agent Stack"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: R21
created_at: 2026-03-22T00:00:00-06:00
updated_at: 2026-03-22T00:00:00-06:00
---

## Objetivo

Ejecutar un **super diagnóstico exhaustivo** de todo el sistema Umbral Agent Stack. Codex tiene acceso a VPS y VM desde su terminal (SSH, curl, etc.). Para las partes que **no pueda hacer** (PowerShell con permisos admin, APIs sin key, etc.), debe **declararlo explícitamente** y dejarlo como pendiente para David o para otro agente.

**Evaluar uso de subagentes:** Si alguna fase beneficia de paralelización o especialidad (ej. un subagente para tests, otro para APIs), Codex debe decidir y documentarlo.

---

## Nombre genérico para agentes de implementación

Para el punto 5 (sistema de reportes de incidencias asignables): usar el rótulo **"Stack Engineers"** para referirse a los agentes que implementan, depuran y mantienen el stack (Codex, Cursor, Antigravity, Claude Code, GitHub Copilot). En Linear, las issues de reparación pueden asignarse a "Stack Engineers" o dejarse sin asignar para que David asigne según disponibilidad.

---

## Plan paso a paso

### Fase 1 — Funcionamiento completo del sistema

1. **VPS — Servicios y crons**
   - Conectar por SSH a la VPS. Verificar: Redis, Dispatcher, Worker local (si existe), Notion Poller daemon.
   - Listar crons activos (`crontab -l`). Verificar que los 12 crons documentados en el board estén presentes y ejecutándose.
   - Verificar rama `rick/vps` vs `main`. Estado de `git status` en la VPS.
   - **Bloqueos:** Si no hay acceso SSH, documentar.

2. **VM — Worker y conectividad**
   - Health check al Worker de la VM: `curl http://<VM_TAILSCALE_IP>:8088/health`
   - Probar `ping` vía `POST /run` con `WORKER_TOKEN`.
   - Verificar conectividad Tailscale VPS ↔ VM.
   - **Bloqueos:** Si no hay acceso a la VM, documentar.

3. **Dispatcher → Worker E2E**
   - Ejecutar flujo completo: enqueue → dispatch → worker → completion.
   - Verificar que Redis reciba y despache tareas.
   - Revisar logs del Dispatcher y del Worker si están accesibles.
   - **Bloqueos:** Cuotas Redis vacías u otros (ver board).

---

### Fase 2 — Testeo

4. **pytest**
   - `WORKER_TOKEN=test python -m pytest tests/ -v`
   - Registrar número de tests, passed, failed, skipped.
   - Identificar tests que fallen y causa.

5. **Tests de integración específicos**
   - `tests/test_linear.py`, `tests/test_notion*.py`, `tests/test_granola.py`, etc.
   - Ejecutar y documentar resultados.
   - **Bloqueos:** Tests que requieran APIs reales sin keys configuradas.

---

### Fase 3 — Pruebas de APIs y conexiones

6. **APIs externas**
   - **Notion:** `notion.add_comment` o `notion.poll_comments` (requiere `NOTION_API_KEY`).
   - **Linear:** `linear.list_teams` o `linear.list_agent_stack_issues` (requiere `LINEAR_API_KEY`).
   - **Google CSE / Tavily:** Si hay keys, probar `research.web` o script de discovery.
   - **n8n:** Verificar que `N8N_URL` y `N8N_API_KEY` permitan listar workflows (si configurado).
   - **Figma, Gmail, etc.:** Según keys disponibles.
   - **Documentar** cuáles funcionan, cuáles fallan por falta de key o permiso.

7. **Conexiones internas**
   - Redis: `redis-cli ping` o script que use Redis.
   - Worker local vs Worker VM: diferencias de respuesta.
   - OpenClaw Gateway (si corre en VPS): estado del servicio.

---

### Fase 4 — Verificación de uso de modelos (multi-LLM) y OpenClaw

8. **ModelRouter y proveedores**
   - Revisar `config/quota_policy.yaml`, `config/teams.yaml`.
   - Verificar qué modelos están configurados (Gemini, Claude, Azure/OpenAI, etc.).
   - Probar una tarea que use LLM (ej. `llm.generate` o `research.web`) y verificar qué modelo se selecciona.
   - Revisar logs de ModelRouter si existen.
   - **Documentar** cuáles modelos responden OK, cuáles 403 o error.

9. **OpenClaw**
   - Estado del gateway y de Rick en la VPS.
   - Modelos disponibles en OpenClaw (Claude vía proxy, etc.).
   - Verificar `openclaw status --all` si está instalado.
   - **Bloqueos:** Si OpenClaw requiere entorno interactivo o config no accesible, documentar.

---

### Fase 5 — Sistema de reportes automáticos de incidencias

10. **Estado actual**
    - Revisar `ESCALATE_FAILURES_TO_LINEAR` y lógica en `dispatcher/service.py`.
    - Verificar si las tareas fallidas ya crean issues en Linear.
    - Revisar proyecto "Mejora Continua Agent Stack" en Linear y labels existentes.

11. **Diseño objetivo**
    - Definir: cuándo Rick o un agente debe crear una notificación/solicitud de reparación en Linear.
    - Asignación: a **Stack Engineers** (genérico) o sin asignar para que David asigne.
    - Propuesta de labels (ej. `incident`, `quota`, `api-down`, `stack-engineer`).
    - Documentar brecha entre estado actual y objetivo.
    - **Oportunidad de automatización:** flujo para que, ante ciertas condiciones, se cree automáticamente la issue.

---

### Fase 6 — Análisis de funcionamiento real vs expectativas de David

12. **Expectativas iniciales**
    - Revisar: `docs/00-overview.md`, `docs/14-codex-plan.md`, `README.md`.
    - Principios: "Solo David manda", "Resiliencia", "Auditable", "Equipos como config".
    - Roadmap S0–S7 y estado documentado.

13. **Comparación real vs esperado**
    - Por cada principio y cada componente del roadmap: ¿se cumple en la práctica?
    - Tabla: Componente | Esperado | Real | Brecha.
    - Incluir hallazgos de fases 1–4.

---

### Fase 7 — Proyectos estancados

14. **Identificación**
    - Revisar Linear (proyectos con pocos avances, issues abiertas hace tiempo).
    - Revisar Notion (proyectos, entregables, tareas pendientes).
    - Revisar `docs/audits/`, `G:\Mi unidad\Rick-David\` (vía Worker si hay acceso) para proyectos mencionados (Embudo, Granola, Auditoría, etc.).

15. **Causas y propuestas**
    - Para cada proyecto estancado: hipótesis de causa (falta de integración, bloqueo técnico, prioridad, etc.).
    - Propuestas concretas de solución.
    - **Bloqueos:** Si no hay acceso a rutas de la VM o a ciertas DBs, documentar.

---

### Fase 8 — Trazabilidad

16. **Estado actual**
    - Revisar `task_queued` (¿se emite? — ver auditoría codebase).
    - OpsLogger, Langfuse, Redis como fuentes de trazabilidad.
    - Flujo: Ingress → ModelRouter → Queue → Worker → Audit.
    - Documentar gaps (ej. evento `task_queued` nunca emitido).

17. **Recomendaciones**
    - Qué eventos faltan o están incompletos.
    - Cómo mejorar trazabilidad end-to-end.

---

### Fase 9 — Oportunidades de mejora

18. **Listado priorizado**
    - Mejoras técnicas (código, infra, observabilidad).
    - Mejoras operativas (crons, alertas, runbooks).
    - Mejoras de proceso (coordinación Rick ↔ agentes, asignación de issues).
    - Prioridad: P0, P1, P2.

---

### Fase 10 — Debugging

19. **Herramientas y logs**
    - Dónde están los logs (Dispatcher, Worker, Poller, supervisor).
    - Cómo reproducir un fallo típico.
    - Scripts de diagnóstico existentes (`scripts/verify_stack_vps.py`, `scripts/hackathon_diagnostic.py`, etc.).
    - Propuestas de mejoras para debugging (más logging, métricas, dashboards).

---

### Fase 11 — Seguridad

20. **Revisión**
    - Secretos: `.env` no en git, `env.rick` ignorado. ¿Hay fugas en logs o en issues?
    - Tokens: rotación, permisos mínimos.
    - Worker: auth Bearer, rate limiting.
    - Tailscale: sin puertos públicos.
    - Webhooks: validación de firma (Linear, etc.).
    - Documentar hallazgos y recomendaciones.

---

### Fase 12 — Skills y MCPs (Codex, Claude Desktop, Cursor, Antigravity)

21. **Inventario**
    - Listar skills disponibles en cada herramienta (según lo que Codex pueda inspeccionar).
    - Listar MCPs configurados en cada una.
    - Fuentes: configs en `~/.cursor/`, `~/.claude/`, workspace de Antigravity, etc.
    - **Documentar** qué tiene cada uno y para qué sirve en el contexto Umbral.

22. **Análisis de uso**
    - Qué skills/MCPs son más útiles para operar Umbral Agent Stack.
    - Redundancias o conflictos.
    - Gaps: qué falta para operar mejor.

---

### Fase 13 — Oportunidades de skills/MCPs para Rick

23. **Skills**
    - Revisar `openclaw/workspace-templates/skills/` (73+ skills).
    - Cuáles usa Rick, cuáles están obsoletas o duplicadas.
    - Propuestas: nuevas skills que ayudarían a Rick (ej. diagnóstico automático, reporte de incidencias, integración con Linear).

24. **MCPs**
    - Rick corre en OpenClaw. ¿Qué MCPs tiene configurados?
    - Propuestas de MCPs que mejorarían la operación (Notion, Linear, n8n, etc.).
    - Limitaciones: qué no se puede agregar y por qué.

---

## Entregables

1. **Documento principal:** `docs/audits/super-diagnostico-2026-03-22.md` con:
   - Resumen ejecutivo (1 página).
   - Resultados por fase (tablas, listas, conclusiones).
   - Bloqueos explícitos (qué no pudo hacer Codex y por qué).
   - Recomendaciones priorizadas.
   - Propuesta de sistema de reportes de incidencias (punto 5).

2. **Actualización del task file:** Log con resumen de ejecución, subagentes usados (si aplica), y enlace al documento.

3. **Opcional:** Issues en Linear para hallazgos críticos (si Codex tiene `LINEAR_API_KEY` y David lo autoriza).

---

## Criterios de aceptación

- [ ] Fases 1–13 ejecutadas en la medida de lo posible.
- [ ] Bloqueos documentados con claridad (PowerShell admin, APIs sin key, etc.).
- [ ] Documento `docs/audits/super-diagnostico-2026-03-22.md` creado.
- [ ] Propuesta de sistema de incidencias asignable a Stack Engineers.
- [ ] Evaluación de subagentes documentada en el Log.
- [ ] Log del task actualizado con resumen.

---

## Referencias rápidas

- Board: `.agents/board.md`
- Runbook: `docs/62-operational-runbook.md`
- Plan Maestro: `docs/14-codex-plan.md`
- Visión: `docs/00-overview.md`
- Worker API: `docs/07-worker-api-contract.md`
- Escalación Linear: `dispatcher/service.py` (ESCALATE_FAILURES_TO_LINEAR)
- Skills Rick: `openclaw/workspace-templates/skills/`
- Auditorías previas: `docs/audits/`

---

## Log

### [cursor] 2026-03-22
Tarea creada. Super diagnóstico exhaustivo en 13 fases. Codex tiene acceso a VPS y VM; debe declarar bloqueos para lo que no pueda ejecutar. Nombre genérico para agentes: "Stack Engineers".
