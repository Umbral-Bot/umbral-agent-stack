Actúa como rick-qa. Esta es una validación de voz, ortografía y premisa para CAND-003.

Contexto:
CAND-003 fue escrita con ortografía española correcta desde el inicio (tildes, ñ, puntuación) y con voz editorial alineada a David desde la primera versión. Esto es una mejora sobre CAND-002, que requirió pasada de corrección post-hoc.

Validar:

1. Ortografía: ¿todas las tildes, ñ, y puntuación son correctas en copy público y en el payload?
2. Voz: ¿es consistente con David? Directa, operativa, AEC-focused, sin slop.
3. Anti-slop: ¿está libre de patrones prohibidos?
   - No "En el mundo actual"
   - No "No es solo X, es Y"
   - No em-dash en copy
   - No consultant-speak
   - No hype ("revolucionario", "game changer", "disruptivo")
4. Premisa: ¿es fuerte, clara, condensada y cumple con estar tanto en propiedad DB como visible en body?
5. Atribución: ¿se mantiene la política? ¿No se reintrodujeron nombres de personas?
6. Tesis: ¿sigue siendo "criterio antes que automatización" y se diferencia de CAND-002?
7. Calidad editorial: ¿el copy es apto para LinkedIn awareness en AEC?

Copy LinkedIn:
"Hay una pregunta que falta en casi toda conversación sobre automatización en AEC:

¿Cuál es tu criterio?

No qué herramienta usás. No qué modelo probaste. Sino: ¿qué definiste como suficientemente bueno? ¿Cuándo se escala? ¿Quién revisa qué?

En infraestructura, el patrón se ve claro. Una ciudad prometió una olimpíada sin autos, pero cuando los criterios reales no sostuvieron la ambición, el plan retrocedió. Un rascacielos se construyó sin criterios de integración urbana — el rechazo duró 50 años y la reparación cuesta €300M.

En IA, el patrón se repite. Las plataformas de gestión de agentes más avanzadas no funcionan 'en general': definen permisos, umbrales, evaluación y escalamiento antes de ejecutar. Las arquitecturas que no definen criterios producen outputs incorrectos. Y cuando una tecnología impresionante no tiene criterios operativos sostenibles, se cancela.

En AEC pasa algo similar. Se adoptan herramientas con lógica aspiracional: mucha expectativa, poco criterio definido. Cuando no entregan valor, se culpa al software.

Pero el problema suele estar antes:
— no había un umbral de calidad explícito,
— no había criterio de revisión definido,
— no había proceso de escalamiento claro.

La automatización amplifica lo que hay. Si hay criterio, amplifica orden. Si no, amplifica caos.

Antes de sumar más tecnología, quizá convenga responder una pregunta más básica:
¿tenés los criterios operativos para que funcione?"

Copy X:
"En AEC, la pregunta correcta antes de automatizar no es qué herramienta usar.

Es qué criterio tenés definido.

¿Qué es suficientemente bueno? ¿Quién revisa? ¿Cuándo se escala?

Sin eso definido, la automatización amplifica desorden, no lo resuelve."

Premisa:
"Antes de automatizar, definí qué es 'suficientemente bueno'. Sin criterios operativos explícitos — qué revisar, cuándo escalar, con qué umbrales medir — la automatización amplifica el desorden en vez de resolverlo."

Devuelve resultado en YAML.
