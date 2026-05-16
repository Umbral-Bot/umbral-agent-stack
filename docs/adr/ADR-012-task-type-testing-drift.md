# ADR-012 — Resolución del drift `task_type="testing"`

- **Fecha**: 2026-05-15
- **Estado**: Aceptado
- **Autor**: Coordinador de Agentes (vía Copilot-VPS, repo only)
- **Relacionado**: OpenClaw E2E Cycle 000 (REPORT.md `sha256:9214f857843a8daa977f5234587cb9ac51ad3ec688f68854faf6061e57c6c9f4`)

## Contexto

El ciclo E2E 000 de OpenClaw detectó un drift de contrato entre el smoke script y el enum del Worker:

- [worker/models/__init__.py](../../worker/models/__init__.py) define `TaskType` con los valores:
  `coding | writing | research | critical | ms_stack | general | triage`.
- [scripts/test_s2_dispatcher.py](../../scripts/test_s2_dispatcher.py#L44) emitía
  `"task_type": "testing"`, valor inexistente en el enum.

Resultado observado en el ciclo 000: el Worker rechaza el envelope con HTTP 400
durante el smoke S2 vía Dispatcher. Una corrida posterior usando
`task_type="general"` validó el camino completo.

Audit del repo (read-only, `grep` recursivo sobre `*.py *.md *.json *.yaml *.yml *.sh`)
confirma una única aparición de `task_type="testing"` en todo el árbol:
[scripts/test_s2_dispatcher.py#L44](../../scripts/test_s2_dispatcher.py#L44).
No se detectaron consumers externos vivos (Make / n8n / webhooks / Notion) que
emitan `"testing"` como `task_type` en este repositorio.

## Opciones consideradas

### Opción A — Alinear el script al enum vigente (elegida)

- Cambiar [scripts/test_s2_dispatcher.py#L44](../../scripts/test_s2_dispatcher.py#L44)
  para usar `task_type="general"`, valor ya documentado como default en
  [docs/07-worker-api-contract.md](../07-worker-api-contract.md) (legacy → `general`).
- **Pros**: cambio mínimo, sin tocar runtime, sin migración de datos, sin
  modificar el contrato público del Worker. Mantiene el enum acotado a tipos
  con semántica de routing real.
- **Cons**: si existieran clientes externos no auditados emitiendo `"testing"`,
  no quedarían cubiertos (audit interno no detectó ninguno).

### Opción B — Restaurar `TESTING` en el enum del Worker

- Agregar `TESTING = "testing"` a `TaskType` y test asociado.
- **Pros**: backward-compat para cualquier consumer histórico.
- **Cons**: amplía el contrato del Worker para soportar un único smoke script
  interno; `testing` no es una categoría de routing LLM real (vs. coding /
  writing / research / critical / ms_stack), introduciría ambigüedad en el
  ModelRouter y en políticas de quota.

## Decisión

**Opción A**. El único call site identificado es un smoke script interno; el
enum del Worker debe reflejar categorías de routing reales. Se alinea el
script al valor `general`, consistente con el default documentado.

## Consecuencias

- Sin cambios de runtime, sin restart, sin migración de datos.
- Backward-compat preservada para el contrato público del Worker (enum
  inalterado).
- Próxima corrida de `scripts/test_s2_dispatcher.py` debe pasar el smoke S2
  end-to-end (validación corresponde a una tarea separada de runtime, no a
  este PR).
- Si en el futuro aparece un consumer externo emitiendo `"testing"`,
  reevaluar Opción B con evidencia.
