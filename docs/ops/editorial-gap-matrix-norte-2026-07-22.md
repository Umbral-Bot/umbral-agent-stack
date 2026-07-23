# Matriz de brecha editorial — Norte (2026-07-22) vs Actual

> **Estado:** diagnóstico read-only consolidado (gate `EDITORIAL_GAP_MATRIX_READY`).
> **Contrato derivado:** [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md).
> **Método:** lectura de contratos del repo + verificación adversarial + 3 páginas
> Notion leídas read-only. Sin writes de producción, sin gates, sin publish.

## Resumen

De 11 filas del norte (estado original del diagnóstico read-only 2026-07-22;
fila D pasó de AUSENTE a PARCIAL con la implementación P2.5, ver abajo): **0
OK · 10 PARCIAL · 0 AUSENTE · 1 CONTRATO_OPUESTO (I)**.
Solo la "cola" del pipeline está cableada: publish **Blog**→Azure ([ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md), doble gate),
gate visual read-only (`resolve_visual_asset_urls`), discovery→**Referentes** (no
Publicaciones) y dashboard. La mitad "pre-aprobación" (alternativas con arco + pie
de estructura de discurso, HITL-1 de 4 salidas, loop de aprendizaje) es
prácticamente greenfield.

## Matriz A–K

| Fila | Distancia | Titular | Evidencia clave |
|------|-----------|---------|-----------------|
| **A** Curado + alternativas V1 | PARCIAL | Regla fuente-pieza existe pero no se aplica; **pie de estructura de discurso + arco = AUSENTE**; superficie de alternativas no definida | [67:133-149](../67-editorial-source-curation.md), [scoring-schema.md:12-13](../../openclaw/workspace-templates/skills/editorial-source-curation/references/scoring-schema.md), [attribution-policy:92](editorial-source-attribution-policy.md) |
| **B** HITL-1 Archivar | PARCIAL | Solo `Descartado`; no hay Archivar≠Descartar | [schema:148,382](../../notion/schemas/publicaciones.schema.yaml) |
| **C** HITL-1 Observar | PARCIAL | `Revisión pendiente` + comentarios nativos; sin salida "Observar" nombrada; loop de comentarios solo post-aprobación | [schema:132,400](../../notion/schemas/publicaciones.schema.yaml) |
| **D** HITL-1 Descartar + aprendizaje | PARCIAL (era **AUSENTE**) | Captura implementada en P2.5 (poller+handler, DEFAULT OFF) + store local consultable (`find_similar_negatives`); falta habilitar en producción y cablear el consumo en el prompt de `rick-qa` (P2.8-style, GO David aparte) | [editorial_negative_capture.py](../../worker/tasks/editorial_negative_capture.py), [sync_negative_examples.py](../../scripts/editorial/sync_negative_examples.py), [editorial-negative-loop-p25-2026-07-23.md](editorial-negative-loop-p25-2026-07-23.md) |
| **E** HITL-1 Aprobar → dispara V2 | PARCIAL | Gate existe; disparo de V2 al aprobar = "Cron futuro" | [v2-visual-gates:281,285](notion-publicaciones-v2-visual-gates-schema.md) |
| **F** V2 Copy Blog largo + medios | PARCIAL | Columnas `Copy *` + `apply_publication_copy.py` (manual, extendido en P2.3: `--write-body`/`--emit-worker-payload` resuelven el límite rich_text; `Copy LinkedIn empresa` escrita si el YAML la trae); falta que David cree la columna viva (P1) y que Rick produzca el campo en runtime | [v3:66-97](notion-blog-linkedin-v3-content-model.md), [apply_publication_copy.py](../../scripts/editorial/apply_publication_copy.py), [roadmap P2.3](editorial-roadmap-norte-p1-p3-2026-07-22.md) |
| **G** V2 cinco imágenes | PARCIAL | `Alt 1..5` + selección + resolver read-only cableados; **generación Magnific NO cableada** | [sync_visual_asset_from_selection.py:22](../../scripts/editorial/sync_visual_asset_from_selection.py), [magnific-editorial-setup:116,118](magnific-editorial-setup-2026-06-06.md) |
| **H** HITL-2 imagen → publish blog | PARCIAL | Gate imagen bloquea (fail-closed) pero **no dispara**; publish = operador tras `autorizar_publicacion` | [editorial_publish.py:619](../../worker/tasks/editorial_publish.py), [ADR-010 §Gates](../adr/ADR-010-azure-editorial-blog-cms.md) |
| **I** Autopublish LinkedIn + X | **CONTRATO_OPUESTO** ✔ | Contratos prohíben autopublish RRSS; X sin adaptador; LinkedIn fail-closed → **ajustado a Fila I = B** | [ADR-010 §Contexto](../adr/ADR-010-azure-editorial-blog-cms.md), [ADR-005 §LinkedIn/§X](../adr/ADR-005-publicacion-multicanal.md), [stage10-publish-safety-spec.md:171](../editorial-pipeline/stage10-publish-safety-spec.md) |
| **J** Dedupe vs Publicaciones | PARCIAL | Idempotencia de publish sí (sin cambios); dedupe de candidato/tema vs backlog implementado en P2.4 (poller+handler, DEFAULT OFF) — falta habilitar en producción y que Rick esté cableado para consultarlo al curar (P2.8) | [test_stage9c_idempotency.py:200](../../tests/discovery/test_stage9c_idempotency.py), [editorial_dedupe.py](../../worker/tasks/editorial_dedupe.py), [editorial-candidate-dedupe-2026-07-23.md](editorial-candidate-dedupe-2026-07-23.md) |
| **K** Compatibilidad schema | PARCIAL | DB viva ya cubre V2/publish; faltan campos de alternativas + HITL-1 4-estados + DB Shortlist; schema solo-David | [notion-schema.md:23](../editorial-pipeline/notion-schema.md), [ADR-007:44,90-92](../adr/ADR-007-notion-como-hub-editorial.md) |

## Recomendación de schema

**HÍBRIDO**: BD Shortlist (alternativas V1 + HITL-1 4-estados + negativos) que al
`Aprobar` promueve (write vía Worker/core, [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1)
a la Publicaciones existente. Campos exactos propuestos y justificación:
[editorial-norte-hitl-contract-2026-07-22.md §6](editorial-norte-hitl-contract-2026-07-22.md).

## Conflictos internos detectados (resueltos en el contrato §7)

1. `gate_invalidado` "editar invalida" **vs** production-flow-v2 "editar = verdad final" → gana **production-flow-v2**.
2. ADR-005 "blog automatización completa" **vs** ADR-010 operador-trigger → gana **ADR-010**.
3. Rename de gates spec-only + drift S4: master-plan:33 dice "📰 Publicaciones" pero el código (`stage4_push_notion.py:2`) escribe en "📰 Publicaciones de Referentes" (la editorial la escribe S7) → claves canónicas = campos wired; S4 → Publicaciones de Referentes.
4. production-flow-v2 §5 "auto RRSS" **vs** ADR-005/010 "nunca auto RRSS" → **Fila I = B**.
