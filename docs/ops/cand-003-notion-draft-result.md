# CAND-003 — Notion Draft Blueprint

> **Date**: 2026-04-23
> **Operation**: PENDING — page not yet created (design-only state)
> **Database**: Publicaciones (`e6817ec4698a4f0fbbc8fedcf4e52472`)
> **Note**: Notion page creation requires HITL. This document specifies the page structure.

## Deduplication Check

- **publication_id**: CAND-003
- **Existing pages in DB**: CAND-001, CAND-002
- **Conflict**: none — CAND-003 is unique

## Properties to Set

| Property | Value |
|----------|-------|
| **Title** | CAND-003 — Criterio antes que automatización: en AEC, la preparación real no empieza por la herramienta. |
| **publication_id** | CAND-003 |
| **Estado** | Borrador |
| **Canal** | linkedin |
| **Tipo de contenido** | linkedin_post |
| **Etapa audiencia** | awareness |
| **Prioridad** | media |
| **Premisa** | Antes de automatizar, definí qué es 'suficientemente bueno'. Sin criterios operativos explícitos — qué revisar, cuándo escalar, con qué umbrales medir — la automatización amplifica el desorden en vez de resolverlo. |
| **Copy LinkedIn** | (see payload) |
| **Copy X** | (see payload) |
| **Ángulo editorial** | La capacidad tecnológica ya existe. Pero en AEC, la automatización no entrega valor cuando falta la infraestructura invisible: criterios operativos explícitos. |
| **Claim principal** | En AEC, la preparación real para automatizar no empieza por la herramienta. Empieza por definir criterios operativos explícitos. |
| **Comentarios revisión** | Segunda candidata source-driven. Tesis prescriptiva: criterio antes que automatización. Diferenciada de CAND-002. |
| **Notas** | Fuentes: The B1M (LA Olympics, Tour Montparnasse), The Batch (#343 Frontier, #347 Claude Code/Sora). Discovery: Vidal → OECD/Solow. Contextual: Aelion.io. |

## Gates and Safety

| Field | Value |
|-------|-------|
| aprobado_contenido | false |
| autorizar_publicacion | false |
| gate_invalidado | false |
| Creado por sistema | false |
| visual_hitl_required | true |

## Publication Fields (all empty)

| Field | Value |
|-------|-------|
| published_url | (empty) |
| published_at | (empty) |
| platform_post_id | (empty) |
| publication_url | (empty) |
| canal_publicado | (empty) |
| publish_error | (empty) |
| error_kind | (empty) |
| content_hash | (empty) |
| idempotency_key | (empty) |

## Body Content Plan

Estimated ~100 blocks in 3 batches:

### Batch 1: Editorial content (~30 blocks)
- Estado del borrador
- Premisa
- Propuesta LinkedIn (copy completo)
- Variante X (copy completo)
- Idea blog (pendiente)
- Brief visual

### Batch 2: Fuentes y extracción (~35 blocks)
- Fuentes analizadas (4 sources) con clasificación [CITABLE] / [DISCOVERY] / [CONTEXTUAL]
- Matriz de extracción: Evidencia (6 rows), Inferencia (3 rows), Hipótesis (1 row)
- Decantación: descartado, conservado, combinado

### Batch 3: Fórmula y checklist (~35 blocks)
- Fórmula de transformación: "Criterio como infraestructura"
- Alternativas consideradas
- Riesgos y supuestos
- Política de atribución aplicada
- Checklist David
- No hacer todavía

## Action Required

Page creation in Notion requires human authorization or runtime activation. This blueprint documents the exact content for manual creation or future automated creation when HITL gates are approved.
