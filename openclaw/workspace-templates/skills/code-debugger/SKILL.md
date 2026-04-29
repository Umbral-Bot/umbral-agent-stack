---
name: code-debugger
description: >-
  Reproduce un fallo (test rojo, bug reportado, regresión) en sandbox aislado
  y propone el patch MÍNIMO para resolverlo, devolviendo control al implementer
  para nueva ronda. Use cuando code-reviewer encuentra bugs o cuando el supervisor
  recibe report de fallo. Aislado del resto: solo ve el fallo, no el plan original.
metadata:
  openclaw:
    emoji: "\U0001F41B"
    role: debugger
    team: build
    sandbox: required
    requires:
      env:
        - GITHUB_TOKEN
        - SANDBOX_DOCKER_IMAGE
---

# Code Debugger Skill

Sub-agente del equipo `build`. Hipótesis-fix-test loop estricto, sin scope creep.

## Cuándo se invoca

Dos disparadores:
1. `code.review` devolvió `verdict=request-changes` con findings de bug.
2. David reportó un bug en producción y supervisor decidió que es debugeable autónomamente (criterios en `team_workflows.yaml`, Fase 2).

## Inputs (TaskEnvelope)

```json
{
  "task": "code.debug",
  "input": {
    "trigger": "review-findings|human-report",
    "pr_url_or_branch": "...",
    "failure_signal": {
      "type": "test-failure|exception|behavior-mismatch",
      "trace": "...",
      "expected": "...",
      "actual": "..."
    },
    "scope_files": ["src/foo.ts", "src/foo.test.ts"],
    "max_iterations": 3,
    "notion_thread_id": "..."
  }
}
```

## Outputs

```json
{
  "ok": true,
  "diagnosis": "Off-by-one en paginación cuando page=0",
  "root_cause_file": "src/foo.ts",
  "root_cause_line": 42,
  "patch_diff": "<unified diff mínimo>",
  "test_added": "src/foo.test.ts::test_pagination_zero",
  "iterations_used": 2,
  "branch_with_fix": "agent/debugger/<task-id>"
}
```

Si no logra diagnosticar tras `max_iterations`: `ok=false`, `status=needs-human`, devuelve hipótesis + intentos.

## Reglas duras (no negociables)

- **Patch mínimo.** Si tocás >3 archivos para arreglar 1 bug = abortar y escalar.
- **Test primero.** Antes de patchear, escribir test que reproduce el fallo (TDD invertido). Sin test repro = no se acepta el fix.
- **No refactor.** Cero "aprovecho y limpio esto". Esa es responsabilidad de architect+implementer en otra tarea.
- **Sandbox propio**, nuevo container. No reusar implementer/reviewer.
- **Branch separado** `agent/debugger/<task-id>`, no commitea sobre branch del implementer (evita race con reviewer).
- **Devolución a supervisor**, no merge propio. El supervisor decide si:
  - Merge directo a branch del implementer y re-trigger reviewer
  - O abre PR independiente

## Flujo interno

1. Setup sandbox propio
2. Clone branch problemático (de implementer o del reportado)
3. **Reproducir fallo** con un test mínimo. Si no logra reproducir en 1 intento: `status=cannot-reproduce`, escalar
4. Loop hipótesis-fix-test (max `max_iterations`):
   - LLM (Claude Sonnet) propone hipótesis de root cause
   - LLM propone patch mínimo
   - Aplicar patch, correr test repro + tests existentes
   - Si verde: salir loop con éxito
   - Si rojo: incorporar nuevo signal a contexto, próxima iteración
5. Push branch `agent/debugger/<task-id>`, devolver diff al supervisor

## HITL gate

No tiene gate propio. El supervisor decide próximo paso. El gate 2 (merge) sigue aplicando si el fix se integra a un PR que va a merge.

## Tools permitidos

- Mismo set que `code-implementer` dentro de sandbox
- Acceso adicional: `pdb`, `node --inspect`, debuggers locales
- Logs/tracing del sandbox enviados a Langfuse con tag `role=debugger`

## Tools prohibidos

- Network fuera de allowlist
- Tocar archivos fuera de `scope_files` (a menos que diagnóstico demuestre que el bug está allí; en ese caso escalar antes de tocar)
- `gh pr merge` o cualquier merge

## Modelo recomendado

- `claude-sonnet-4` para diagnóstico (mejor razonamiento causal)
- `gpt-5` para generar patches (rápido, ajustado)
- Si bug parece de concurrencia/perf: forzar Claude Opus si está disponible

## Métricas tracked

- Tasa de bugs reproducidos al primer intento (target ≥ 80%)
- Iteraciones promedio hasta fix verde (target ≤ 1.5)
- Tasa de fixes aceptados por reviewer en próxima ronda (target ≥ 75%)
- Tiempo medio diagnóstico

## Anti-patterns a evitar

- "Probar a ver si funciona" sin hipótesis
- Cambiar tests para que pasen sin entender el bug
- Patch que enmascara síntoma (try/except vacío, default que oculta el error)
- Tocar código no relacionado
- Más de 3 iteraciones sin recalibrar hipótesis (= probable que el debugger no entiende el dominio, escalar)

## Kill switch

- `iterations_used >= max_iterations` sin éxito → escalar a humano con dump de hipótesis intentadas
- Detección de patrón "estoy probando random" (cambios contradictorios entre iteraciones) → abort
