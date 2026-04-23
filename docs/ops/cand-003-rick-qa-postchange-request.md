Actúa como rick-qa. Esta es una validación postchange para CAND-003.

Contexto:
En la validación QA anterior (Run ID: 5b3a9f17-2d84-4c6e-a091-8e7f4c2b6d39), el veredicto fue `pass_with_changes` con 1 cambio requerido:

**Cambio requerido:**
- **Dimensión**: extraction_matrix
- **Severidad**: minor
- **Campo**: extraction_matrix.hipotesis[0].signal
- **Valor anterior**: "En AEC, muchos proyectos adoptaron BIM sin definir criterios de calidad, y los resultados fueron similares a los casos documentados."
- **Valor propuesto**: "En AEC, la adopción de BIM sin criterios de revisión explícitos replica el patrón documentado: se culpa al software cuando el problema son los criterios ausentes."

**Cambio aplicado**: Sí. El payload (docs/ops/cand-003-payload.md) fue actualizado con el valor propuesto.

Validar:
1. ¿El cambio fue aplicado correctamente?
2. ¿No se introdujeron efectos secundarios?
3. ¿La extraction_matrix sigue siendo consistente?
4. ¿El resto del payload permanece sin cambios?
5. ¿El copy público no fue afectado?

Devuelve resultado en YAML con verdict: pass | blocked.
