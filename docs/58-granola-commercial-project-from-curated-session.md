# 58 - Granola update_commercial_project_from_curated_session

> LEGACY V1 / SUPERSEDED: este slice depende de la capa curada retirada del flujo operativo normal. Mantener solo como referencia para residuos V1.

> Slice conservador para actualizar `Asesorías & Proyectos` desde una sesion curada sin inferir campos comerciales desde texto libre.

## 1. Objetivo

`granola.update_commercial_project_from_curated_session` cubre el tramo:

- sesion curada humana
- proyecto comercial humano ya identificado
- actualizacion comercial explícita y trazable

No crea proyectos comerciales nuevos.
No adivina el siguiente paso comercial.

## 2. Qué hace

Parte desde una sesion curada existente y:

- lee la pagina real como evidencia
- requiere `NOTION_COMMERCIAL_PROJECTS_DB_ID`
- usa `project_page_id` explicito o la relacion `Proyecto` heredada desde la sesion curada
- inspecciona el schema vivo de `Asesorías & Proyectos`
- solo actualiza campos comerciales realmente soportados
- deja trazabilidad por comentario entre sesion curada y proyecto comercial

## 3. Qué no hace

- no crea un proyecto comercial desde cero
- no intenta hacer match por nombre si no tiene un objetivo claro
- no escribe notas libres en la DB comercial si no existe un campo para ello
- no infiere `Estado` o `Acción Requerida` desde texto libre
- no reemplaza la revisión humana del pipeline comercial

## 4. Payload mínimo útil

```json
{
  "curated_session_page_id": "<curated-session-page-id>",
  "estado": "Propuesta enviada"
}
```

Esto solo funciona si la sesion curada ya tiene la relacion `Proyecto`.

## 5. Payload recomendado

```json
{
  "curated_session_page_id": "<curated-session-page-id>",
  "estado": "Propuesta enviada",
  "accion_requerida": "Revisar contrato",
  "add_trace_comments": true
}
```

## 6. Campos que intenta mapear

Solo si el schema vivo los soporta:

- `Estado`
- `Acción Requerida`
- `Fecha`
- `Plazo`
- `Monto`
- `Tipo`
- `Cliente`

Si ninguno de esos campos se pasó explícitamente, el handler falla.

## 7. Estado operativo actual

Al 2026-03-27:

- `NOTION_COMMERCIAL_PROJECTS_DB_ID` ya es reachable con Rick
- la relacion `Proyecto` desde la sesion curada ya es utilizable como target humano
- el handler ya puede actualizar el proyecto comercial por `page_id`
- la trazabilidad por comentarios ya quedó validada

## 8. Piloto live validado

Validación ejecutada el 2026-03-27 con:

- sesion curada:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- proyecto comercial:
  - `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Payload aplicado:

- `Estado = Propuesta enviada`
- `Acción Requerida = Revisar contrato`

Resultado verificado:

- `Estado = Propuesta enviada`
- `Acción Requerida = Revisar contrato`
- comentario en la sesion curada apuntando al proyecto comercial
- comentario en el proyecto comercial apuntando a la sesion curada

## 9. Criterio de uso

Usar este handler cuando:

- ya existe sesion curada
- ya existe proyecto comercial relacionado
- el cambio comercial está claro y cabe en un campo canónico del proyecto

No usarlo cuando:

- el proyecto aún no está identificado
- el cambio comercial solo existe como texto ambiguo
- la actualización correcta sería una tarea humana, no un cambio de estado/proximidad comercial

## 10. Referencias

- `worker/tasks/granola.py`
- `tests/test_granola.py`
- `docs/50-granola-notion-pipeline.md`
- `docs/53-granola-raw-curated-promotion-plan.md`
- `docs/57-granola-human-task-from-curated-session.md`
