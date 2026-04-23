Actúa como rick-qa. Esta es la validación editorial completa para CAND-003.

Contexto:
CAND-003 es la segunda candidata editorial source-driven del flujo canónico de 9 etapas. Tesis: "Criterio antes que automatización". Diferenciada de CAND-002 (gap diagnosis) en que CAND-003 es prescriptiva.

Payload de referencia: `docs/ops/cand-003-payload.md`
Fuentes: `docs/ops/cand-003-source-publications.md`
Matriz de extracción: en el payload (6 evidencia, 3 inferencia, 1 hipótesis)
Clasificación de fuentes: `docs/ops/cand-003-source-reclassification.md`

Criterios de validación:

1. **Schema**: ¿El payload tiene todas las propiedades requeridas según el schema de Publicaciones?
2. **Fuentes**: ¿Las fuentes son reales, verificables, y correctamente clasificadas?
3. **Extraction matrix**: ¿La clasificación evidencia/inferencia/hipótesis es correcta y no hay inflación?
4. **AEC relevance**: ¿El contenido es relevante para la audiencia AEC? ¿El ángulo "criterio" está bien anclado?
5. **Editorial quality**: ¿El copy es publicable para LinkedIn awareness? ¿La premisa es fuerte?
6. **Governance**: ¿Gates en false? ¿No se asume publicación?
7. **Internal disclosure**: ¿Fuentes discovery/contextual permanecen solo en trazabilidad interna?

Payload resumido:
- Title: "Criterio antes que automatización: en AEC, la preparación real no empieza por la herramienta."
- Premisa: "Antes de automatizar, definí qué es 'suficientemente bueno'. Sin criterios operativos explícitos — qué revisar, cuándo escalar, con qué umbrales medir — la automatización amplifica el desorden en vez de resolverlo."
- Extraction matrix: 6 evidencia, 3 inferencia, 1 hipótesis
- Transformation formula: "Criterio como infraestructura" (pattern_synthesis)
- Claim principal: inferencia_con_fuentes

Devuelve resultado en YAML con verdict: pass | pass_with_changes | blocked, y detalle por dimensión.
