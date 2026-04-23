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

## CAND-002 — First Source-Driven Editorial Candidate

| Campo | Valor |
|-------|-------|
| **Título** | CAND-002 — La IA ya cambio de ritmo. En AEC, el cuello de botella sigue siendo la organizacion. |
| **Page URL** | [link](https://www.notion.so/CAND-002-La-IA-ya-cambio-de-ritmo-En-AEC-el-cuello-de-botella-sigue-siendo-la-organizacion-34b5f443fb5c81daabe1e586033ceed8) |
| **Page ID** | `34b5f443-fb5c-81da-abe1-e586033ceed8` |
| **publication_id** | CAND-002 |
| **trace_id** | CAND-002-source-driven-editorial-candidate |
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

**Creado por**: Copilot (technical operator), via OpenClaw flow
**Fecha creación**: 2026-04-23
**Propósito**: Primera candidata editorial source-driven, basada en fuentes seleccionadas por David desde DB Referentes.

### Flujo de creación

1. Copilot extrajo 25 referentes de la DB Referentes de Notion.
2. Copilot analizó publicaciones recientes de 4 fuentes públicas (The B1M, The Batch, Marc Vidal, Aelion.io).
3. `rick-orchestrator` generó payload CAND-002 con source_set, extraction_matrix, decantation, transformation_formula y editorial_decision.
4. `rick-qa` validó payload: **verdict: pass_with_changes** (0 blockers, 3 required changes menores, `ready_to_create_notion_draft: true`).
5. Copilot creó el registro en Notion DB Publicaciones como `Borrador`.
6. Copilot agregó 124 bloques al body con trazabilidad editorial completa.
7. Auditoría estructural post-write: **PASS** (0B/0W/19I).

### Body preview

- **Body preview added**: yes (2026-04-23)
- Page contains: propuesta LinkedIn, variante X, idea blog, brief visual, fuentes analizadas (4), matriz de extracción (evidencia/inferencia/hipótesis), decantación, fórmula de transformación, alternativas, riesgos, checklist David.
- 124 blocks in 3 batches.

### Para David

- Buscar en Notion: **CAND-002 — La IA ya cambio de ritmo**
- Revisar: propuesta LinkedIn, variante X, fuentes, fórmula, checklist.
- La trazabilidad editorial completa está en el body de la página.
- No está publicado. No hay gates marcados. No hay runtime activo.
- Ready for human review, not ready for publication.

### Evidence docs

- [`cand-002-source-intake.md`](cand-002-source-intake.md)
- [`cand-002-source-publications.md`](cand-002-source-publications.md)
- [`cand-002-rick-orchestrator-request.md`](cand-002-rick-orchestrator-request.md)
- [`cand-002-rick-orchestrator-result.md`](cand-002-rick-orchestrator-result.md)
- [`cand-002-payload.md`](cand-002-payload.md)
- [`cand-002-rick-qa-request.md`](cand-002-rick-qa-request.md)
- [`cand-002-rick-qa-result.md`](cand-002-rick-qa-result.md)
- [`cand-002-notion-draft-result.md`](cand-002-notion-draft-result.md)
- [`cand-002-source-driven-flow.md`](cand-002-source-driven-flow.md)
