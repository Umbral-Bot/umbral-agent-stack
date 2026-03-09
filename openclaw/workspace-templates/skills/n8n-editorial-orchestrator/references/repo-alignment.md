# Alineacion con dependencias externas

## Reutilizar la skill n8n
Reutilizar la skill `n8n` cuando la conversacion pase de arquitectura editorial a implementacion tecnica. Delegar alli:
- seleccion de nodos
- expresiones
- credenciales
- retries y manejo de errores
- json exportable del workflow

## Consultar docs del repo cuando existan
### docs/60-rrss-pipeline-n8n.md
Usarlo para alinear:
- nombres de etapas
- contratos entre workflows
- colas y handoffs
- observabilidad
- limites entre captura, shortlist y publicacion

### docs/67-editorial-source-curation.md
Usarlo para alinear:
- taxonomia de autoridad
- criterios editoriales
- scoring o priorizacion
- gobernanza y revision de fuentes
- condiciones para marcar viable/parcial/bloqueada

## Continuar aunque falten dependencias
Si la skill `n8n` o los docs del repo no estan disponibles:
- declararlo explicitamente
- usar las referencias internas como fallback
- no inventar como hechos nombres de tablas o convenciones del repo
- presentar cualquier estructura ausente como propuesta o supuesto
