Actúa como rick-qa. Esta es una validación de voz, ortografía y premisa para CAND-002.

Contexto:
Se aplicaron correcciones de ortografía española (tildes, ñ, puntuación) y ajustes de voz editorial al copy de CAND-002. También se agregó la propiedad Premisa a la DB Publicaciones y se pobló para CAND-002.

Cambios aplicados:
1. Ortografía corregida en todo el body de la página Notion: tildes (á, é, í, ó, ú), ñ, signos de puntuación.
2. Copy LinkedIn reescrito con voz más directa, más AEC, más operativa:
   - "distintas conversaciones sobre IA" → "muchas conversaciones sobre IA en construcción"
   - "No estoy seguro de que ese sea" → "No creo que ése sea"
   - "adopción tecnológica en construcción" → "adopción tecnológica en el sector"
   - Se añadió "en obra o en coordinación" como filtro práctico AEC
   - "Eso incluye roles..." → "Roles, criterio de revisión, trazabilidad..." (más directo)
3. Copy X reescrito con ortografía y voz corregida.
4. Premisa agregada: "En AEC, más herramientas de IA no garantizan más valor. El cuello de botella es organizacional: roles, procesos y criterio de revisión no están diseñados para absorber la velocidad que la tecnología ya ofrece."
5. Propiedades actualizadas: Título, Ángulo editorial, Claim principal, Resumen fuente, Comentarios revisión, Notas.

Copy LinkedIn actualizado:
"Hay una idea que se repite en muchas conversaciones sobre IA en construcción: que el problema es encontrar la herramienta correcta.

No creo que ése sea el cuello de botella real en AEC.

Cuando cruzas señales recientes sobre equipos AI-native, productividad y adopción tecnológica en el sector, aparece un patrón: la brecha no está entre quienes tienen acceso a IA y quienes no. Está entre la capacidad disponible y la preparación real para usarla.

No es un problema nuevo. La paradoja de la productividad lleva décadas mostrando que más tecnología no garantiza más retorno. En construcción, donde el filtro práctico siempre ha sido si algo genera valor en obra o en coordinación desde el primer día, esa tensión se siente con más fuerza.

Si juntas esas señales, aparece una lectura incómoda: la barrera no parece ser la falta de IA, sino la falta de preparación organizacional para usarla bien.

Roles, criterio de revisión, trazabilidad, procesos capaces de absorber otra velocidad de trabajo.

Por eso muchas organizaciones pueden incorporar más automatización y aun así no capturar más valor.

No porque la tecnología falle.
Sino porque el sistema de trabajo sigue diseñado para otra etapa.

En AEC, quizá la pregunta ya no es quién está probando IA.
La pregunta es quién está rediseñando su forma de operar para que esa IA realmente produzca impacto."

Copy X actualizado:
"En AEC, el cuello de botella de la IA puede no ser la herramienta.

Puede ser la organización.

La paradoja de la productividad sigue vigente: más tecnología no garantiza más retorno. En construcción, si el filtro siempre ha sido generar valor en obra desde el primer día y los equipos siguen operando igual, la captura de valor depende menos del hype y más de roles, criterio, revisión y procesos."

Premisa: "En AEC, más herramientas de IA no garantizan más valor. El cuello de botella es organizacional: roles, procesos y criterio de revisión no están diseñados para absorber la velocidad que la tecnología ya ofrece."

Anti-slop checklist:
- ¿Hay "En el mundo actual"? No.
- ¿Hay "No es solo X, es Y"? No.
- ¿Hay "Aquí es donde entra X"? No.
- ¿Hay "partner estratégico", "solución integral", "revolucionar", "potenciar", "apalancar", "desbloquear"? No.
- ¿Hay em dash "—" en el copy público (LinkedIn/X)? No.
- ¿Hay pregunta retórica seguida de su respuesta inmediata? No (la pregunta del cierre queda abierta).

Reglas de voz de David:
- Directo, técnicamente preciso, ligeramente informal: SÍ
- Operativamente concreto (nombra procesos reales): SÍ (roles, criterio de revisión, trazabilidad, obra, coordinación)
- AEC-enfocado: SÍ (construcción, AEC, obra, coordinación, BIM managers)
- Creíble, sobrio: SÍ (sin hipérbole, tesis formulada como "no parece ser")
- Fricción real: SÍ (reconoce la tensión sin simplificar)

Valida específicamente:
1. Que la ortografía española es correcta (tildes, ñ, puntuación).
2. Que la voz es consistente con David (directa, operativa, AEC, sin slop).
3. Que la premisa es fuerte, clara y condensada.
4. Que la política de atribución se mantiene (no se reintrodujeron nombres de personas).
5. Que la tesis sigue sustentada.
6. Que el copy mantiene calidad editorial y no pierde fuerza.
7. Que no hay detalles internos del sistema Rick en el copy.
8. Que gates siguen false y ready_for_publication=false.

Devuelve tu resultado en formato YAML:

```yaml
qa_voice_result:
  verdict: pass | pass_with_changes | blocked
  previous_verdict: pass
  voice_validation:
    orthography_correct: true | false
    voice_consistent_with_david: true | false
    anti_slop_clean: true | false
    premisa_strong_and_clear: true | false
    attribution_policy_maintained: true | false
    thesis_still_supported: true | false
    editorial_quality_maintained: true | false
    no_internal_details_exposed: true | false
    notes: ""
  ready_for_human_review: true | false
  ready_for_publication: false
  blockers: []
  required_changes: []
  recommendations: []
  validation_summary:
    orthography: pass | fail
    voice: pass | fail
    anti_slop: pass | fail
    premisa: pass | fail
    attribution_policy: pass | fail
    editorial_quality: pass | fail
    governance: pass | fail
  residual_risks: []
  next_action: ""
```
