# ADR-005: Adoptar flujo raw -> sesion capitalizable -> capitalizacion

## Estado
Aprobado - 2026-03-31

## Contexto

El workspace de David Moreira tiene tres realidades al mismo tiempo:

- Notion es la capa principal de operacion humana.
- Rick coordina el sistema y necesita escribir en Notion con seguridad.
- El mayor riesgo no es perder velocidad, sino duplicar o tocar la fuente canonica equivocada.

El repo ya dispone de slices de runtime que pueden:

- crear raw en Notion
- promover a una sesion curada
- crear tareas humanas
- actualizar una superficie comercial
- escribir entregables o items puente

Pero esos slices no sustituyen una regla de gobernanza global para todo el workspace.

## Decision

Se adopta como flujo oficial V1:

`raw -> sesion capitalizable -> capitalizacion`

Con estas reglas:

1. `raw` es append-only y no es destino final.
2. La interpretacion ocurre en una sesion capitalizable unica por caso.
3. La capitalizacion solo toca bases canonicas con target verificado o permiso explicito de creacion.
4. Si hay ambiguedad, no se actualiza; se deja comentario de revision.
5. Cada capitalizacion debe dejar trazabilidad hacia `raw` y hacia la sesion capitalizable.

## Razones

1. Separa captura, interpretacion y escritura final.
2. Reduce el riesgo de escribir sobre el objeto equivocado.
3. Permite que Rick y Notion AI operen sin sustituir el criterio humano de canon.
4. Mantiene compatibilidad con el runtime existente, porque los handlers actuales ya cubren partes del flujo.
5. Facilita que Cursor implemente el schema live sin inventar otro stack.

## Consecuencias

- Debe existir una superficie canonica de `sesion capitalizable`.
- Las bases finales se protegen mejor porque la interpretacion no ocurre dentro de ellas.
- `granola.promote_curated_session` queda alineada con la etapa oficial `raw -> sesion capitalizable`.
- `granola.create_human_task_from_curated_session` y `granola.update_commercial_project_from_curated_session` quedan alineadas con capitalizacion.
- `granola.capitalize_raw` sigue existiendo, pero se trata como slice legado o tecnico; no como camino humano canonico V1.
- Los IDs y `data_source_id` reales quedan fuera del repo hasta verificacion live.

## Alternativas consideradas

### A. Capitalizar directo desde raw a cada base final

Descartada.

Riesgo demasiado alto de:

- duplicar objetos
- escribir sobre el objeto equivocado
- mezclar captura bruta con canon humano

### B. Dejar que cada superficie interprete su propio raw

Descartada.

Genera interpretaciones duplicadas, reglas inconsistentes y mayor fragilidad de permisos.

## Referencias

- `docs/architecture/02-operating-model-v1.md`
- `docs/policies/02-permissions-by-surface.md`
- `docs/policies/03-capitalization-rules.md`
- `registry/runtime-bridge-contract.yaml`
- `registry/taxonomies-v1.yaml`
