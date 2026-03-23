---
id: "2026-03-22-003"
title: "Fix hallazgos del super diagnóstico — VM /run y auto-issues"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: R21
created_at: 2026-03-22T00:00:00-06:00
updated_at: 2026-03-22T00:00:00-06:00
---

## Objetivo

Arreglar los hallazgos críticos del super diagnóstico (2026-03-22-002) que Codex puede resolver por código. Los arreglos de VPS (git pull, matar dispatcher duplicado, levantar Notion Poller) los hace David/Rick manualmente; esta tarea se centra en:

1. **VM Worker — contrato /run:** Asegurar que el Worker de la VM acepte el contrato canónico (TaskEnvelope) además del legacy.
2. **Auto-issues — reducir ruido:** El sistema actual crea issues en Linear para toda tarea fallida, generando ruido fuera del flujo canónico de Agent Stack. Refinar cuándo escalar.

---

## Contexto (hallazgos del super diagnóstico)

- VM acepta solo contrato legacy en `/run` → Dispatcher envía envelope; puede haber rechazo o mal parseo.
- Sistema de auto-issues genera ruido fuera del flujo canónico de Agent Stack.

---

## Tareas

### 1. VM Worker — contrato /run

1.1. **Verificar compatibilidad**
   - Revisar `worker/app.py` y `worker/models/__init__.py`: el Worker debe aceptar tanto `{task, input}` (legacy) como TaskEnvelope completo.
   - Revisar qué envía el `WorkerClient.run()`: construye `{task, input, ...envelope_fields}`. ¿El Worker lo parsea bien?
   - Si el VM Worker está desactualizado: documentar que debe ejecutarse `scripts/deploy-vm.ps1` (o equivalente) para actualizar el Worker en la VM. No es responsabilidad de Codex ejecutarlo en la VM; sí documentar el paso.

1.2. **Asegurar robustez**
   - Si hay diferencias de contrato entre lo que envía el Dispatcher y lo que acepta el Worker, unificar.
   - Añadir tests que validen: (a) legacy `{task, input}` funciona, (b) envelope con `schema_version`, `task_id`, `team`, etc. funciona.
   - Si el Worker ya acepta ambos: verificar que el VM tenga la misma versión que main. Documentar en el informe.

1.3. **Documentación**
   - Actualizar runbook o doc operativa: "Para que la VM acepte el contrato canónico, el Worker debe estar actualizado. Ejecutar `.\scripts\deploy-vm.ps1` en la VM."

### 2. Auto-issues — reducir ruido

2.1. **Análisis actual**
   - Revisar `dispatcher/service.py`: `_escalate_failure_to_linear()`, `ESCALATE_FAILURES_TO_LINEAR`.
   - Hoy: toda tarea fallida (salvo `linear.*`) crea una issue. No hay filtro por fuente ni por flujo.

2.2. **Propuesta de refinamiento**
   - Escalar solo cuando la tarea proviene del **flujo canónico** (Dispatcher → Redis → Worker). Criterio: `envelope.get("source")` o `source_kind` que indique origen canónico.
   - Excluir tareas de fuentes "ruidosas": ej. crons de SIM, digest, o tareas one-off que no son parte del Agent Stack.
   - Alternativa: usar label o proyecto en Linear. Crear issues solo en el proyecto "Mejora Continua Agent Stack" y con label `incident` o `stack-engineer`.
   - Documentar la lógica y los criterios de exclusión.

2.3. **Implementación**
   - Añadir filtros en `_escalate_failure_to_linear()`:
     - Si `source_kind` o `source` indica flujo no canónico, no escalar (o escalar solo a nivel log).
     - Opcional: env var `ESCALATE_ONLY_CANONICAL=true` para activar el filtro.
   - Asignar issues al equipo/proyecto correcto (Mejora Continua Agent Stack) y con labels adecuados.
   - Añadir tests para el nuevo comportamiento.

### 3. Validación

- Ejecutar `python -m pytest tests/ -v`.
- Si hay `scripts/e2e_validation.py`, ejecutarlo y documentar resultado.
- Dejar nota en el Log sobre si el VM necesita deploy manual.

---

## Criterios de aceptación

- [ ] Worker acepta legacy y envelope; tests añadidos/actualizados.
- [ ] Documentación: cómo actualizar el Worker en la VM para contrato canónico.
- [ ] Auto-issues: filtros implementados para reducir ruido (solo flujo canónico o criterio definido).
- [ ] Tests pasan.
- [ ] PR abierto a main.
- [ ] Log actualizado con resumen.

---

## Fuera de scope (David/Rick)

- Ejecutar `git pull origin main` en la VPS.
- Matar proceso dispatcher duplicado.
- Levantar Notion Poller.
- Cuota Tavily agotada (requiere cuenta/billing).
- Ejecutar `deploy-vm.ps1` en la VM (Codex documenta; David ejecuta).

---

## Referencias

- Super diagnóstico: `docs/audits/super-diagnostico-2026-03-22.md` (en PR #126)
- Task 2026-03-22-002
- `dispatcher/service.py` — `_escalate_failure_to_linear`
- `worker/app.py` — `/run`, parse envelope vs legacy
- `client/worker_client.py` — payload que se envía

---

## Log

### [cursor] 2026-03-22
Tarea creada. Fix VM /run contract y reducción de ruido en auto-issues según hallazgos del super diagnóstico.
