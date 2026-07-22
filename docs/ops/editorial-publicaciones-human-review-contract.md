# Contrato: revisión humana de publicaciones editoriales

Estado: vigente desde Fase 2 (versioning editorial). Surface repo-only.

## Propósito

Definir qué debe existir **antes** de Gate 1 y qué reglas de voz aplican en producción.
Backward-compatible: no cambia pipeline v1; añade precondiciones de artefacto.

## Capacidades de versionado

- **C1 — Anti-muletilla:** `evals/editorial/benchmark-umbral-voice-v1.yaml`
- **C2 — Claim ledger:** `evals/editorial/claim-ledger.schema.yaml`
- **C3 — Revision log:** `evals/editorial/revision-log.template.md`
- **Canal:** `evals/editorial/channel-criteria-v1.yaml`
- **Modelo:** `config/editorial-model.yaml` + `docs/editorial-pipeline/editorial-model-contract.md`

## Precondiciones de Gate 1

1. C2 claim ledger generado para la publicación.
2. C3 revision log para la versión propuesta (vN → vN+1).
3. Benchmark C1 sin `fail_automatico` sin resolver.
4. Redacción generada con `azure-openai-responses/gpt-5.5` vía OpenClaw o fallo explícito documentado.

## Regla operativa

Rick no escribe copy en Notion sin ledger (C2) y revision log (C3) cuando el flujo versioning está activo.
Los gates `aprobado_contenido` y `autorizar_publicacion` son solo de David.

## Postcondiciones de publicación (Fila I = B)

Tras el publish del blog (Azure, [ADR-010 §Gates](../adr/ADR-010-azure-editorial-blog-cms.md)), el sistema:

1. Inyecta `published_url` + copy de Notion en las copies de RRSS.
2. Marca **`listo_rrss` (checkbox en Publicaciones) = true** — estado terminal RRSS.
3. **No** publica en LinkedIn/X: el post lo hace un humano (manual/semi-auto).

Bajo Fila I = B el código nunca autopublica RRSS. Ver contrato norte [§5.I](editorial-norte-hitl-contract-2026-07-22.md).

## Sensibilidad editorial (preventivo)

Aplicar en revision humana y en generacion (ver CAL-007 en `director-comunicacion-umbral/CALIBRATION.md`):

- Evitar formular la automatizacion como reemplazo de personas o reduccion de dependencia de "pocas personas".
- Enfocar la IA como apoyo a procesos, trazabilidad, revision, sintesis, priorizacion y criterio compartido.
- Evitar frases que hagan sentir al lector que su proceso actual es lento, atrasado o deficiente.
- En BIM/AEC: distinguir interferencias/clashes de incidencias/issues gestionables.
- No atribuir al agente "mantener consistencia entre disciplinas" sin criterios, responsables y validacion humana.
