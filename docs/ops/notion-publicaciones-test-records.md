# Notion Publicaciones — Test Records

Registro de registros de prueba manuales creados en la DB `Publicaciones` para validar el flujo editorial antes de activar Rick.

---

## TEST-001 — Validación manual flujo editorial

| Campo | Valor |
|-------|-------|
| **Título** | TEST-001 — Validación manual flujo editorial |
| **Page URL** | [link](https://www.notion.so/TEST-001-Validaci-n-manual-flujo-editorial-c98af1420cd949a9a2ff128a76955b6e) |
| **publication_id** | TEST-001 |
| **trace_id** | TEST-001-manual-validation |
| **Canal** | linkedin |
| **Tipo de contenido** | linkedin_post |
| **Estado** | Borrador |
| **Etapa audiencia** | _(vacío)_ |
| **aprobado_contenido** | false |
| **autorizar_publicacion** | false |
| **gate_invalidado** | false |
| **content_hash** | _(vacío)_ |
| **idempotency_key** | _(vacío)_ |
| **Fuente primaria** | _(vacío)_ |
| **Fuente referente** | _(vacío)_ |
| **platform_post_id** | _(vacío)_ |
| **publication_url** | _(vacío)_ |
| **Fecha publicación** | _(vacío)_ |
| **Visual brief** | _(vacío)_ |
| **Visual asset URL** | _(vacío)_ |
| **visual_hitl_required** | false |
| **Publicación padre** | _(vacío)_ |
| **Proyecto** | _(vacío)_ |
| **Notas** | _(vacío)_ |

**Creado por**: David (manual)
**Fecha creación**: 2026-04-22
**Propósito**: Validar que el flujo editorial funciona con un registro real antes de activar Rick.

### Resultado de auditoría post-creación

- **Fecha**: 2026-04-22
- **Verdict**: **PASS** (0 blockers, 0 warnings, 19 info)
- **Observación**: La creación de un registro no afecta la estructura de la DB. El audit compara schema vs propiedades de la DB, no los registros individuales.

### Plan de validación con TEST-001

1. [x] Crear registro manual con campos mínimos (Título, Canal, Estado, publication_id, trace_id)
2. [ ] Verificar que el registro aparece en las vistas recomendadas (Pipeline editorial, Por canal)
3. [ ] Avanzar manualmente por la máquina de estados: Borrador → Revisión pendiente → Aprobado → Autorizado
4. [ ] Verificar que los gates humanos funcionan correctamente
5. [ ] Verificar que gate_invalidado se puede activar/desactivar
6. [ ] Marcar como Descartado al finalizar la validación

### Convención de nombres

- Prefijo `TEST-` para registros de prueba.
- Formato: `TEST-NNN` (numeración secuencial).
- Los registros de prueba se marcan como `Descartado` al terminar la validación, no se eliminan.

---

## Siguiente paso: primer contenido real candidato

Después de completar la validación con TEST-001, el siguiente paso es crear manualmente el primer contenido editorial real en Publicaciones.

**Reglas**:

- Crear manualmente en Notion. No usar Rick.
- No publicar. Mantener `aprobado_contenido=false` y `autorizar_publicacion=false`.
- Requiere fuente primaria (`Fuente primaria`) o marcar explícitamente que la fuente está pendiente.
- No calcular `content_hash` ni `idempotency_key` hasta que el contenido sea aprobado.
- Re-ejecutar auditoría read-only después de la creación.
- Documentar el candidato en este archivo o en un doc de seguimiento.
- Rick permanece inactivo. No activar runtime, workers, ni publicación.
