# 34 — Linear-first Operating Model (orden + trazabilidad + paralelización)

## Objetivo
Estandarizar la operación diaria de Rick y equipos para:
1. Mantener orden operativo.
2. Garantizar trazabilidad completa.
3. Permitir ejecución paralela sin perder control.
4. Aprovechar routing/cuotas de modelos por tipo de tarea.

## Decisiones

### 1) Workspaces (mínimos)
- **Core**: `umbral-agent-stack/` (infra, dispatcher, worker, docs, runbooks).
- **Proyectos**: `proyectos/<proyecto>/` (runs, entregables, investigación).
- **Sandbox opcional**: `proyectos/_sandbox/`.

> No crear workspaces por cada microtarea; solo por aislamiento real de archivos/operación.

### 2) Equipos (usar `config/teams.yaml` existente)
- `marketing`
- `advisory`
- `improvement`
- `system`
- `lab` (experimentos)

### 3) Regla de oro: Linear-first
Toda tarea relevante (que tome >15 min, implique coordinación, o produzca entregable) **debe** abrir issue en Linear antes de ejecutar.

## Convención de issue

Título sugerido:
`[<umbral_team>] <acción breve> — <resultado esperado>`

Descripción mínima obligatoria:
- `trace_id`
- `umbral_team`
- `owner_agent`
- `objective`
- `definition_of_done`
- `artifacts_path` (si aplica)

## Flujo operativo
1. Rick recibe instrucción.
2. Rick descompone en subtareas.
3. Crear 1 issue Linear por subtarea crítica.
4. Ejecutar en paralelo (3 hilos recomendados; máximo 5).
5. QA/cierre (ideal: equipo `improvement`).
6. Actualizar issue con resultado y artefactos.

## Límites de paralelización
- Recomendado: **3 hilos concurrentes**.
- Máximo operativo: **5 hilos**.
- Si no hay issue, no se ejecuta.

## Routing de modelos (alineado con S4)
- Tareas estratégicas/críticas: modelo premium.
- Tareas repetitivas/operativas: modelo costo-eficiente.
- Usar fallback por cuota según `config/quota_policy.yaml`.

## Implementación en repo
- Script utilitario: `scripts/linear_create_issue.py`
  - ya soporta creación directa o encolada.
  - ahora soporta metadata operativa (`trace_id`, `owner_agent`, `umbral_team`, `dod`).

## Checklist de cierre
- [ ] Issue creado en Linear
- [ ] `trace_id` presente
- [ ] DoD cumplido
- [ ] Artefactos/ruta anexados
- [ ] Estado reportado a David
