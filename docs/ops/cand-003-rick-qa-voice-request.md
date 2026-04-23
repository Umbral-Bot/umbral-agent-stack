Actúa como rick-qa. Esta es una validación de voz y calidad editorial para CAND-003.

Contexto:
CAND-003 es una candidata source-driven con tesis "Criterio antes que automatización". La pasada de voz fue aplicada como etapa separada (Stage 5) contra el resumen autorizado de la guía de voz de marca (la guía viva en Notion page 0192ad1f-3ca1-44ae-954d-0b738261258e no es accesible por la integración).

Cambios aplicados en la pasada de voz:
1. Apertura más directa: "Antes de sumar una herramienta más de IA, hay una pregunta que la mayoría de equipos AEC no se hacen..."
2. Segunda persona: "Si tu organización no tiene documentado..." (en vez de "una organización")
3. Transición menos expositiva: "El patrón no es exclusivo de construcción. Datos recientes muestran que..."
4. Más concreto AEC: "En construcción, esto se traduce en equipos..."
5. Línea agregada: "Entregables que se aceptan por inercia, no por verificación."
6. Cierre más directo: "la pregunta operativa es más básica:"
7. Copy X mantenido (ya era conciso y directo).

Copy LinkedIn (post-voice):
"Antes de sumar una herramienta más de IA, hay una pregunta que la mayoría de equipos AEC no se hacen: ¿tenemos criterio operativo explícito para lo que ya hacemos?

Si tu organización no tiene documentado qué constituye una revisión válida de un modelo BIM, qué dispara una escalación en coordinación, o qué criterio define que un entregable es suficiente, la IA no va a resolver eso. Va a ejecutar más rápido un proceso que nadie definió bien.

El patrón no es exclusivo de construcción. Datos recientes muestran que la mayoría de empresas europeas ya usan herramientas algorítmicas de gestión. Pero los estándares para auditar esas herramientas recién se están proponiendo. Las plataformas más avanzadas de agentes de IA asignan permisos y guardarraíles, pero la supervisión humana sigue siendo implícita.

En construcción, esto se traduce en equipos que incorporan automatización sin haber formalizado sus criterios de trabajo. Revisiones que dependen de quién las hace, no de qué criterio aplican. Coordinación que funciona por costumbre, no por protocolo. Entregables que se aceptan por inercia, no por verificación.

Automatizar eso no mejora el proceso. Lo acelera con ambigüedad incluida.

Antes de escalar con IA, la pregunta operativa es más básica: ¿mi equipo tiene criterio explícito para revisión, aceptación, escalación y coordinación? Si la respuesta es no, la herramienta no es el problema."

Copy X (post-voice):
"En AEC, la IA puede automatizar tareas. Pero si tu equipo no tiene criterio explícito para revisión, escalación y coordinación, lo que automatizas es la ambigüedad.

79% de empresas europeas ya usan herramientas algorítmicas de gestión. Los estándares para auditarlas recién se están proponiendo. Antes de más herramientas: más criterio."

Premisa: "En AEC, automatizar sin criterio operativo explícito no acelera: amplifica la ambigüedad. Antes de escalar con IA, hay que definir qué constituye una revisión válida, qué dispara una escalación y qué hace que la coordinación sea suficiente."

Valida específicamente:
1. Que el copy cumple la voz de marca: directo, operativo, concreto, sin slop.
2. Que no hay anti-slop violations: "En el mundo actual", "No es solo X es Y", em dashes en copy, consultant-speak, filler.
3. Que la segunda persona ("tu organización", "tu equipo") está bien aplicada sin sonar prescriptivo.
4. Que la conexión AEC sigue clara y concreta.
5. Que la tesis sigue sustentada tras la reescritura.
6. Que la ortografía española es correcta (tildes, ñ, puntuación).
7. Que no se introdujeron nombres de personas en copy público.
8. Que la pasada de voz fue documentada como aplicada contra resumen autorizado (no guía viva).

Devuelve resultado en formato YAML:

```yaml
qa_voice_result:
  verdict: pass | pass_with_changes | blocked
  voice_validation:
    brand_voice_compliance: true | false
    anti_slop_clean: true | false
    second_person_appropriate: true | false
    aec_connection_clear: true | false
    thesis_still_supported: true | false
    orthography_correct: true | false
    no_person_names_in_copy: true | false
    voice_pass_documented: true | false
    notes: ""
  voice_source: "authorized_summary | live_guide"
  voice_guide_accessible: false
  ready_for_final_qa: true | false
  blockers: []
  required_changes: []
  recommendations: []
```
