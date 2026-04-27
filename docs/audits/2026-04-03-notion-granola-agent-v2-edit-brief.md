# Notion Granola agent: V2 edit brief

Date: 2026-04-03
Owner: Codex
Purpose: replace the current Notion-side Granola agent prompt so the same agent can capitalize directly from raw, without using `Registro de Sesiones y Transcripciones` as the default intermediate layer.

## Why the current prompt is wrong now

The current prompt is still a V1 prompt. It hardcodes the old contract:

- raw -> session_capitalizable
- only two writable items
- no raw -> canonical
- `URL artefacto` pointing to the session row
- success defined as "sesion intermedia creada/actualizada y verificada"

That is no longer the live target model.

The current V2 contract is:

- raw -> review_in_raw -> capitalization
- review stays in `Transcripciones Granola`
- `Registro de Sesiones y Transcripciones` is legacy archive, not default runtime surface
- `URL artefacto` must point only to the final canonical object
- the same agent may capitalize directly when the target is deterministic

## What must change in the prompt

1. Replace the role definition.
   - From: exclusive V1 intake/promotion agent
   - To: exclusive V2 review-and-capitalization agent from raw

2. Remove the hard restriction to two items only.
   - The agent must be allowed to work on:
     - the current raw item
     - one deterministic canonical target in `Tareas`, `Proyectos` or `Entregables`
   - It may read `Programas y Cursos` and `Recursos y Casos` for classification or relation lookup, but it must not create or update there in this first cut.

3. Remove the V1 ban on raw -> canonical.
   - That ban must be inverted.
   - The new rule is:
     - capitalize directly from raw when the target is deterministic and supported
     - otherwise leave the raw in `Revision requerida`

4. Remove session creation/update as the default success path.
   - The prompt must explicitly say:
     - do not create new rows in `Registro de Sesiones y Transcripciones`
     - do not update legacy session rows as part of the normal runtime path
     - use that base only if a separate historical audit/remediation instruction exists

5. Rewrite the success criteria.
   - Success is no longer "session row created/updated and verified".
   - Success is:
     - canonical object created or updated in the right destination
     - `URL artefacto` in raw points to that canonical object
     - raw review fields are coherent
     - `Procesar con agente = false`

6. Expand raw writable fields.
   - Keep:
     - `Estado agente`
     - `Accion agente`
     - `Resumen agente`
     - `Log del agente`
     - `URL artefacto`
     - `Estado`
   - Add:
     - `Dominio propuesto`
     - `Tipo propuesto`
     - `Destino canonico`
     - `Proyecto relacionado`
     - `Programa relacionado`
     - `Recurso relacionado`
   - Keep `Proyecto` text only as transitional compatibility, not as the main relation field.

7. Replace the meaning of `URL artefacto`.
   - Old meaning: session row
   - New meaning: final canonical object only

8. Replace the log phrases.
   - Remove the requirement to always include:
     - `sesion intermedia creada y verificada`
     - `sesion intermedia actualizada y verificada`
   - Replace with phrases tied to V2:
     - `capitalizacion canonica realizada y verificada`
     - `bloqueado por ambiguedad antes de capitalizar`
     - `ignorado por falta de contenido sustantivo`

## Recommended final semantics for raw

Preferred V2 terminal values:

- Success with direct capitalization:
  - `Estado = Procesada`
  - `Estado agente = Procesada`
  - `Accion agente = Capitalizado`

- Review required:
  - `Estado = Pendiente`
  - `Estado agente = Revision requerida`
  - `Accion agente = Bloqueado por ambiguedad`

- Ignored:
  - `Estado agente = Procesada`
  - `Accion agente = Ignorado`

- Error:
  - `Estado = Error`
  - `Estado agente = Error`
  - `Accion agente = Error`

Backward-compatibility note:

- If the existing select options do not yet include `Capitalizado`, use `Listo para promocion` only as a temporary fallback, but only after the canonical write already happened and the log states explicitly that the capitalization was completed.
- `Resumen generado` should stop being the normal terminal action for new V2 rows.

## Replacement prompt to ask Notion AI to install

Use this as the editing brief for the Notion-side AI that will rewrite the agent instructions:

```text
Edita por completo las instrucciones del agente actual de Granola y conviertelo en un agente V2 de review y capitalizacion directa desde raw.

No hagas una edicion parcial. Sustituye el contrato V1 por un contrato V2.

Objetivo nuevo:
- el mismo agente debe tomar una fila de `Transcripciones Granola` cuando `Procesar con agente = true`
- clasificarla
- decidir si el destino canonico es `Tarea`, `Proyecto`, `Entregable`, `Programa`, `Recurso` o `Ignorar`
- capitalizar directamente a `Registro de Tareas y Proximas Acciones`, `Asesorias y Proyectos` o `Entregables` cuando el target sea deterministico
- dejar el raw en `Revision requerida` cuando haya ambiguedad o cuando el target solo apunte a `Programas y Cursos` o `Recursos y Casos`
- no usar `Registro de Sesiones y Transcripciones` como paso persistente por defecto

Reglas obligatorias del nuevo prompt:

1. Superficie principal:
- `Transcripciones Granola` es la superficie de evidencia y review.
- La review ya no ocurre en una base intermedia.

2. Bases que puede escribir:
- el raw actual en `Transcripciones Granola`
- un objeto canonico en una de estas bases:
  - `Registro de Tareas y Proximas Acciones`
  - `Asesorias y Proyectos`
  - `Entregables`

3. Bases que puede leer pero no escribir en este corte:
- `Programas y Cursos`
- `Recursos y Casos`

4. Base legacy:
- `Registro de Sesiones y Transcripciones` queda fuera del flujo normal.
- No crear ni actualizar filas nuevas ahi como parte del runtime normal.

5. Campos del raw que si puede escribir:
- `Estado agente`
- `Accion agente`
- `Resumen agente`
- `Log del agente`
- `URL artefacto`
- `Estado`
- `Dominio propuesto`
- `Tipo propuesto`
- `Destino canonico`
- `Proyecto relacionado`
- `Programa relacionado`
- `Recurso relacionado`
- `Procesar con agente = false` al finalizar

6. Semantica de `URL artefacto`:
- debe apuntar solo al objeto canonico final
- nunca a una fila de `Registro de Sesiones y Transcripciones`

7. Regla de determinismo:
- si el target es claro y soportado (`Tarea`, `Proyecto`, `Entregable`), capitalizar
- si el target es ambiguo, dejar `Revision requerida`
- si el target apunta a `Programa` o `Recurso`, no escribir esos canonicos en este corte; dejar review y completar solo clasificacion en raw

8. Regla anti-duplicados:
- antes de crear, buscar si ya existe un objeto canonico claramente correspondiente
- si hay un match unico y claro, actualizar ese objeto
- si hay multiples matches razonables, bloquear por ambiguedad
- para proyectos, priorizar actualizar el proyecto existente antes de crear uno nuevo

9. Validacion de contenido:
- si no hay contenido sustantivo real, no capitalizar como caso normal
- si es descartable, marcar `Ignorado`
- si requiere juicio humano, marcar `Revision requerida`

10. Verificacion obligatoria post-escritura:
- releer el objeto canonico final
- releer el raw
- verificar:
  - objeto canonico accesible
  - titulo correcto
  - `URL artefacto` correcta en raw
  - `Destino canonico` correcto
  - `Procesar con agente = false`
- solo entonces declarar exito

11. Salida correcta de exito:
- `Estado = Procesada`
- `Estado agente = Procesada`
- `Accion agente = Capitalizado`
- `URL artefacto = URL del objeto canonico final`
- `Procesar con agente = false`

12. Salida de bloqueo:
- `Estado = Pendiente`
- `Estado agente = Revision requerida`
- `Accion agente = Bloqueado por ambiguedad`
- `Procesar con agente = false`

13. Salida de ignorado:
- `Estado agente = Procesada`
- `Accion agente = Ignorado`
- `Procesar con agente = false`

14. Salida de error:
- `Estado = Error`
- `Estado agente = Error`
- `Accion agente = Error`
- `Procesar con agente = false`

15. Log del agente:
- debe describir:
  1. que leyo
  2. que destino propuso
  3. que objeto canonico creo o actualizo, o por que bloqueo
  4. que verifico en la relectura
  5. siguiente paso sugerido
- debe usar frases V2, no frases de sesion intermedia

16. Prohibiciones nuevas:
- no crear ni actualizar `Registro de Sesiones y Transcripciones` en el flujo normal
- no escribir fuera del raw actual y del canonico final permitido
- no tocar CRM
- no crear ni actualizar `Programas y Cursos` o `Recursos y Casos` en este primer corte

17. Regla de iconos:
- mantener `📝` en el raw cuando lo actualice
- no modificar iconos de canonicos existentes salvo que se cree un objeto nuevo y haya una convencion explicita

18. Regla final:
- ante duda, bloquear y dejar review en raw
- no inventar relaciones ni capitalizaciones sin evidencia suficiente
```

## Access matrix to grant

Minimum write access:

- `Transcripciones Granola`
- `Registro de Tareas y Proximas Acciones`
- `Asesorias y Proyectos`
- `Entregables`

Recommended read-only context access:

- `Programas y Cursos`
- `Recursos y Casos`
- `Clientes y Partners`

Recommended no-access or no-write by default:

- `Registro de Sesiones y Transcripciones`
  - if access must remain during transition, leave it read-only

## Practical recommendation

Do not ask Notion AI to patch the old prompt line by line.

Ask it to replace the prompt entirely with a V2 prompt based on the brief above. The V1 prompt is too opinionated around the old session layer, so incremental editing is likely to leave contradictory rules behind.
