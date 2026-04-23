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

Antes de crear CAND-001, se define `rick-editorial` como agente design-only (`openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`).

La primera candidata real debe ser:
- Preparada por `rick-editorial` (cuando se active) o mediante simulación explícita de su contrato de output.
- Created using the payload template: [`docs/ops/rick-editorial-candidate-payload-template.md`](rick-editorial-candidate-payload-template.md).
- Registrada manualmente en Notion por David o un operador autorizado.
- Validada por `rick-qa` contra los criterios de aceptación del contrato.

**Reglas**:

- No usar Rick para publicar. Rick sigue inactivo.
- No publicar. Mantener `aprobado_contenido=false` y `autorizar_publicacion=false`.
- Notion AI no opera contenido editorial; solo apoyó el setup inicial del hub y la DB.
- Requiere fuente primaria (`Fuente primaria`) o marcar explícitamente que la fuente está pendiente.
- No calcular `content_hash` ni `idempotency_key` hasta que el contenido sea aprobado.
- Re-ejecutar auditoría read-only después de la creación.
- Documentar el candidato en este archivo o en un doc de seguimiento.
- David revisa antes de cualquier aprobación.

---

## CAND-001 — First Real Editorial Candidate

| Campo | Valor |
|-------|-------|
| **Título** | CAND-001 — Automatizar sin gobernanza escala el desorden |
| **Page URL** | [link](https://www.notion.so/CAND-001-Automatizar-sin-gobernanza-escala-el-desorden-34b5f443fb5c81dd8338cb0b46699250) |
| **Page ID** | `34b5f443-fb5c-81dd-8338-cb0b46699250` |
| **publication_id** | CAND-001 |
| **trace_id** | CAND-001-v2-editorial-candidate |
| **Canal** | linkedin |
| **Tipo de contenido** | linkedin_post |
| **Estado** | Borrador |
| **Etapa audiencia** | awareness |
| **Prioridad** | media |
| **aprobado_contenido** | false |
| **autorizar_publicacion** | false |
| **gate_invalidado** | false |
| **visual_hitl_required** | true |
| **Creado por sistema** | false |
| **Proyecto** | Sistema Editorial Rick |

**Creado por**: Codex (technical operator), via OpenClaw flow
**Fecha creación**: 2026-04-23
**Propósito**: Primera candidata editorial real para revisión humana por David.

### Flujo de creación

1. `rick-orchestrator` generó payload v2 simulando `rick-editorial` (aplicando decisión editorial de David).
2. `rick-qa` validó payload v2: **verdict: pass** (0 blockers, 0 required changes, `ready_to_create_notion_draft: true`).
3. Codex creó el registro en Notion DB Publicaciones como `Borrador`.
4. Auditoría estructural post-write: **PASS** (0B/0W/19I).

### Para David

- Buscar en Notion: **CAND-001 — Automatizar sin gobernanza escala el desorden**
- Revisar copy LinkedIn, copy X, ángulo editorial y visual brief.
- No está publicado. No hay gates marcados. No hay runtime activo.
- Ready for human review, not ready for publication.

### Evidence docs

- [`cand-001-v2-rick-orchestrator-request.md`](cand-001-v2-rick-orchestrator-request.md)
- [`cand-001-v2-rick-orchestrator-result.md`](cand-001-v2-rick-orchestrator-result.md)
- [`cand-001-v2-payload.md`](cand-001-v2-payload.md)
- [`cand-001-v2-rick-qa-request.md`](cand-001-v2-rick-qa-request.md)
- [`cand-001-v2-rick-qa-result.md`](cand-001-v2-rick-qa-result.md)
- [`cand-001-notion-draft-result.md`](cand-001-notion-draft-result.md)
