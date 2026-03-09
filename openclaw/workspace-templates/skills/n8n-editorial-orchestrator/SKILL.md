---
name: n8n-editorial-orchestrator
description: disenar y revisar workflows de n8n para curacion editorial con schedule,
  captura, normalizacion, scoring, shortlist, revision humana y handoff a publicacion.
  usar cuando chatgpt deba convertir una operacion editorial o de rrss en una automatizacion
  con fuentes de autoridad, clasificacion de fuentes como viable, parcial o bloqueada,
  colas de aprobacion y entrega a un cms, newsletter o canal de publicacion sin asumir
  autopublicacion. reutilizar la skill n8n para detalles de nodos, expresiones, credenciales
  y json de workflows. consultar docs/60-rrss-pipeline-n8n.md y docs/67-editorial-source-curation.md
  cuando existan en el workspace.
metadata:
  openclaw:
    emoji: 🧬
    requires:
      env: []
---

# N8n Editorial Orchestrator

## Enfocar el trabajo
Usar esta skill para disenar la logica editorial, los estados, los objetos de datos, la gobernanza y los puntos de aprobacion.

Reutilizar la skill `n8n` cuando el trabajo requiera:
- mapeo nodo por nodo
- expresiones, credenciales, paginacion, retries o manejo de errores de n8n
- json exportable o implementacion concreta del workflow

Mantener esta skill como capa de orquestacion editorial. Mantener la skill `n8n` como capa de implementacion tecnica del workflow.

## Cargar el contexto correcto
1. Consultar `docs/60-rrss-pipeline-n8n.md` cuando exista.
2. Consultar `docs/67-editorial-source-curation.md` cuando exista.
3. Cargar referencias incluidas:
   - `references/recommended-workflow-patterns.md`
   - `references/source-status-playbook.md`
   - `references/repo-alignment.md`
4. Declarar cualquier supuesto si faltan docs del repo o la skill `n8n`.

## Secuencia editorial recomendada
1. schedule
2. captura
3. normalizacion y deduplicacion
4. scoring
5. shortlist
6. revision humana
7. handoff a publicacion

## Entidades minimas
### registro de fuentes
- `source_id`
- `source_name`
- `authority_type`
- `coverage_topics`
- `access_method`
- `fetch_pattern`
- `status`
- `status_reason`
- `editorial_owner`
- `last_reviewed_at`
- `next_review_at`
- `notes`

### candidato editorial
- `candidate_id`
- `source_id`
- `captured_at`
- `canonical_url`
- `title`
- `summary`
- `topics`
- `freshness_score`
- `authority_score`
- `relevance_score`
- `uniqueness_score`
- `compliance_flag`
- `final_score`
- `shortlist_status`
- `review_status`
- `handoff_status`

## Reglas clave
- Usar exactamente `viable`, `parcial` y `bloqueada` para el estado operativo de fuentes.
- No asumir autopublicacion.
- Exigir aprobacion humana antes de cualquier handoff.
- Preferir patrones editoriales antes que detalle nodo por nodo.

## Formato de salida
1. objetivo editorial
2. entidades y tablas
3. workflow principal
4. workflows auxiliares
5. modelo de scoring
6. modelo de fuentes y estado
7. gate de revision humana
8. handoff a publicacion
9. riesgos, supuestos y siguientes pasos

