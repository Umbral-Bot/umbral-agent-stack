# Notion Publicaciones — Read-Only Audit Report

- **Schema**: `notion/schemas/publicaciones.schema.yaml`
- **Actual source**: `notion:e6817ec4698a4f0fbbc8fedcf4e52472`
- **Verdict**: **WARN**
- **Total differences**: 33
- **Blockers**: 0
- **Warnings**: 12
- **Info**: 21

## Differences

| Severity | Field | Issue | Detail |
|----------|-------|-------|--------|
| WARNING | Creado por | missing_property | Expected property 'Creado por' (created_by) not found in Notion DB. |
| WARNING | Fecha publicación | missing_property | Expected property 'Fecha publicación' (date) not found in Notion DB. |
| WARNING | Fuentes confiables | missing_property | Expected property 'Fuentes confiables' (relation) not found in Notion DB. |
| WARNING | Notas | missing_property | Expected property 'Notas' (rich_text) not found in Notion DB. |
| WARNING | platform_post_id | missing_property | Expected property 'platform_post_id' (rich_text) not found in Notion DB. |
| WARNING | Proyecto | missing_property | Expected property 'Proyecto' (relation) not found in Notion DB. |
| WARNING | Publicación padre | missing_property | Expected property 'Publicación padre' (relation) not found in Notion DB. |
| WARNING | publication_url | missing_property | Expected property 'publication_url' (url) not found in Notion DB. |
| WARNING | trace_id | missing_property | Expected property 'trace_id' (rich_text) not found in Notion DB. |
| WARNING | Última edición | missing_property | Expected property 'Última edición' (last_edited_time) not found in Notion DB. |
| INFO | Ángulo editorial | extra_property | Property 'Ángulo editorial' (rich_text) exists in Notion but not in local schema. |
| INFO | canal_publicado | extra_property | Property 'canal_publicado' (select) exists in Notion but not in local schema. |
| INFO | Claim principal | extra_property | Property 'Claim principal' (rich_text) exists in Notion but not in local schema. |
| INFO | Comentarios revisión | extra_property | Property 'Comentarios revisión' (rich_text) exists in Notion but not in local schema. |
| INFO | Copy Blog | extra_property | Property 'Copy Blog' (rich_text) exists in Notion but not in local schema. |
| INFO | Copy LinkedIn | extra_property | Property 'Copy LinkedIn' (rich_text) exists in Notion but not in local schema. |
| INFO | Copy Newsletter | extra_property | Property 'Copy Newsletter' (rich_text) exists in Notion but not in local schema. |
| INFO | Copy X | extra_property | Property 'Copy X' (rich_text) exists in Notion but not in local schema. |
| INFO | Creado por sistema | extra_property | Property 'Creado por sistema' (checkbox) exists in Notion but not in local schema. |
| INFO | error_kind | extra_property | Property 'error_kind' (select) exists in Notion but not in local schema. |
| INFO | Prioridad | extra_property | Property 'Prioridad' (select) exists in Notion but not in local schema. |
| INFO | publish_error | extra_property | Property 'publish_error' (rich_text) exists in Notion but not in local schema. |
| INFO | published_at | extra_property | Property 'published_at' (date) exists in Notion but not in local schema. |
| INFO | published_url | extra_property | Property 'published_url' (url) exists in Notion but not in local schema. |
| INFO | Repo reference | extra_property | Property 'Repo reference' (url) exists in Notion but not in local schema. |
| INFO | Responsable revisión | extra_property | Property 'Responsable revisión' (people) exists in Notion but not in local schema. |
| INFO | Resumen fuente | extra_property | Property 'Resumen fuente' (rich_text) exists in Notion but not in local schema. |
| INFO | Última revisión humana | extra_property | Property 'Última revisión humana' (date) exists in Notion but not in local schema. |
| WARNING | Estado | missing_options | Missing options in Notion: ['Revisión pendiente']. |
| INFO | Estado | extra_options | Extra options in Notion: ['Revisión']. |
| INFO | Etapa audiencia | extra_options | Extra options in Notion: ['retention']. |
| WARNING | Tipo de contenido | missing_options | Missing options in Notion: ['cta_variant', 'news_reactive', 'raw_idea', 'reference_post', 'source_signal', 'technical_explainer', 'thought_leadership']. |
| INFO | Tipo de contenido | extra_options | Extra options in Notion: ['artículo', 'carrusel', 'hilo', 'newsletter', 'otro', 'post', 'visual']. |
