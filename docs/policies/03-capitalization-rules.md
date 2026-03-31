# 03 - Capitalization Rules

> Reglas V1 para pasar de `raw` a `sesion capitalizable` y de ahi a bases canonicas sin duplicar ni tocar la fuente equivocada.

## 1. Ambito

- Estas reglas aplican a cualquier automatizacion o trabajo asistido por Rick, Notion AI o el thread de `umbral-agent-stack`.
- La politica cubre tanto creacion como actualizacion de objetos canonicos.

## 2. Reglas no negociables

1. `raw` nunca es el destino final.
2. No se capitaliza directo desde `raw` a una superficie humana compartida salvo excepcion tecnica documentada.
3. Toda capitalizacion parte desde una sesion capitalizable.
4. Sin target verificado, no hay `edit`.
5. Si hay ambiguedad, el resultado correcto es comentario de revision y estado bloqueado.
6. Toda escritura canonica deja trazabilidad a la sesion capitalizable y a la fuente `raw`.

## 3. Anclas requeridas antes de editar

Antes de cualquier `edit`, deben existir estas anclas:

- `raw_source_id` o `source_external_id`
- `source_url` o referencia equivalente a la fuente
- `capitalizable_session_id`
- `object_type` destino confirmado
- `target_page_id` o permiso explicito de creacion

Si falta cualquiera de esas anclas y el caso no es trivial, no se actualiza.

## 4. Orden de resolucion del target

El runtime debe intentar resolver el target en este orden y detenerse al primer match fuerte:

1. `page_id` o relacion explicita ya guardada en la sesion capitalizable.
2. `source_url` o `source_external_id` ya asociado al objeto canonico.
3. clave canonica exacta dentro del mismo tipo y mismo contexto padre.
4. alias o mapping humano aprobado y persistido.
5. si nada anterior aplica, no editar y dejar comentario de revision.

No se permite resolver target solo por similitud debil de titulo.

## 5. Politica por tipo de objeto

| Tipo de objeto | Crear permitido | Update permitido | Si hay ambiguedad |
| --- | --- | --- | --- |
| `capitalizable_session` | Si, desde `raw` verificado | Si, mientras siga en staging | comentario y `Bloqueada por ambiguedad` |
| `task` | Si, cuando la accion sea explicita y el contexto sea claro | Si, con target verificado o si la tarea es runtime-propia | comentario en sesion; no crear tarea |
| `deliverable` | Si, cuando el artefacto sea propio o claramente derivado de la sesion | Si, con target verificado | propuesta o comentario; no sobreescribir entregable ajeno |
| `client_opportunity` | Solo con payload comercial explicito o target ya verificado | Si, con target verificado y campos acotados | comentario; no crear lead u oportunidad por inferencia |
| `project` | Solo con instruccion humana explicita o mapping verificado desde CRM | Si, con target verificado | comentario; no crear proyecto nuevo por deduccion |
| `program_course` | Solo con instruccion humana explicita | Si, con target verificado | comentario; no crear programa nuevo |
| `resource` | Si, con `source_url` o fuente verificable y taxonomia minima | Si, con target verificado o registro runtime-propio | propuesta o comentario |
| `research` | Si, con evidencia verificable y estado minimo | Si, con target verificado o registro runtime-propio | propuesta o comentario |

## 6. Regla central de ambiguedad

Si existe cualquiera de estas dudas, no se actualiza:

- no esta claro si el target correcto es `cliente`, `oportunidad` o `proyecto`
- el mismo titulo aparece en mas de un objeto candidato
- el objeto parece sensible o protegido
- no esta claro si corresponde crear nuevo o actualizar existente
- la sesion mezcla varios temas sin decision humana sobre el contenedor final

En esos casos se debe:

1. dejar comentario estructurado de revision
2. marcar la sesion capitalizable como `Bloqueada por ambiguedad`
3. listar la decision faltante

## 7. Comentario minimo de revision

```text
[Revision requerida]
motivo: <ambiguous_target | duplicate_risk | protected_surface | missing_anchor>
sesion: <capitalizable_session_name_or_id>
fuente: <raw_source_id_or_url>
decision_humana_pendiente: <que falta confirmar>
candidatos: <lista corta si aplica>
```

## 8. Trazabilidad minima por capitalizacion exitosa

Toda capitalizacion exitosa debe dejar:

- relacion o referencia a la `capitalizable_session`
- `source_url` o `source_external_id`
- fecha de capitalizacion
- comentario o nota breve que explique que cambio se hizo

La sesion capitalizable debe poder responder:

- que objetos toco
- si creo o actualizo
- con que evidencia

## 9. Dedupe minimo

- Una sesion capitalizable no debe crear dos objetos canonicos equivalentes del mismo tipo.
- Si el runtime detecta un match fuerte, actualiza el objeto existente y no crea otro.
- Si el runtime detecta dos candidatos fuertes, no elige; comenta.

## 10. Nota de compatibilidad con el stack actual

- El repo ya tiene handlers que resuelven tramos concretos:
  - `granola.promote_curated_session`
  - `granola.create_human_task_from_curated_session`
  - `granola.update_commercial_project_from_curated_session`
  - `notion.upsert_task`
  - `notion.upsert_project`
  - `notion.upsert_deliverable`
  - `notion.upsert_bridge_item`
- `granola.capitalize_raw` se considera un slice legado o tecnico.
- En V1 humano oficial, `granola.capitalize_raw` no reemplaza el gate `raw -> sesion capitalizable -> capitalizacion`.
