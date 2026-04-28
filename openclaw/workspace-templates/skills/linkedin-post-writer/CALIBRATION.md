# Calibracion — linkedin-post-writer

> Reglas persistentes derivadas de feedback humano. El agente debe leer este archivo antes de redactar cualquier borrador.

## Formato de entrada

Cada regla sigue esta estructura:

- **patron observado**: que se detecto.
- **ejemplo rechazado**: como se veia el error.
- **ejemplo preferido**: como debe sonar.
- **razon**: por que importa.
- **cuando aplica**: contexto de aplicacion.
- **cuando no aplica**: excepciones.

---

## CAL-LW-001 — No abrir con etiqueta sectorial generica

- **patron observado**: el borrador abre con "En AEC/BIM..." o "En el sector de la construccion..." como primera linea.
- **ejemplo rechazado**: "En AEC, la automatizacion no entrega valor cuando falta infraestructura invisible."
- **ejemplo preferido**: "Cuando un equipo todavia no tiene claro si un modelo esta realmente listo para revision, hablar de automatizacion es adelantarse un paso."
- **razon**: David no habla asi. Su audiencia AEC no necesita que le recuerden en que sector trabajan. El contexto debe surgir de la escena operativa, no de una etiqueta.
- **cuando aplica**: siempre que el post va a audiencia AEC/BIM en LinkedIn o X.
- **cuando no aplica**: si el post es para audiencia general fuera del sector y necesita encuadre.

---

## CAL-LW-002 — No usar "escalacion" como sustantivo en copy publico

- **patron observado**: el borrador usa "escalacion" como sustantivo.
- **ejemplo rechazado**: "La escalacion de estas herramientas requiere criterio."
- **ejemplo preferido**: "Para escalar estas herramientas, primero hay que definir el criterio."
- **razon**: "escalacion" suena a jerga de sistema, no a lenguaje natural de David.
- **cuando aplica**: siempre en copy publico (LinkedIn, X).
- **cuando no aplica**: en documentacion interna del sistema Rick.

---

## CAL-LW-003 — Cierre con pregunta o reflexion concreta, no con frase formulada

- **patron observado**: el cierre usa frases como "Ese es el punto" o "Empieza en otra parte" sin aterrizar.
- **ejemplo rechazado**: "Empieza en otra parte: que criterio usa el equipo."
- **ejemplo preferido**: "Antes de escalar con IA, la conversacion util no empieza en la herramienta. Empieza en que criterio usa el equipo para revisar, cerrar observaciones y aceptar un entregable."
- **razon**: David prefiere cierres que aterricen la idea en accion concreta, no en frase de efecto.
- **cuando aplica**: siempre en LinkedIn.
- **cuando no aplica**: en X, donde la brevedad justifica un cierre mas seco.

---

## CAL-LW-004 — Longitud: comprimir si supera 300 palabras sin justificacion

- **patron observado**: borradores que exceden 300 palabras por redundancia, no por complejidad del tema.
- **ejemplo rechazado**: repetir la misma idea con distintas formulaciones para rellenar.
- **ejemplo preferido**: una sola formulacion clara, eliminar repeticiones, mantener ritmo.
- **razon**: el formato LinkedIn medio (180-260 palabras) es el default. Exceder 300 solo se justifica por complejidad real del tema.
- **cuando aplica**: siempre por default.
- **cuando no aplica**: cuando el usuario pide explicitamente formato largo (300-600).

---

## CAL-LW-005 — Contextualizar antes de tecnificar

- **patron observado**: el borrador menciona "modelo BIM", "modelo federado" o tecnologia especifica antes de establecer el problema general (proceso, revision, entregable, observaciones, decision).
- **ejemplo rechazado**: "Cuando un modelo BIM tiene errores de coordinacion, la automatizacion no ayuda."
- **ejemplo preferido**: "Cuando el equipo no definio que revisar ni cuando algo esta listo, meter tecnologia no ordena nada. Eso se ve, por ejemplo, en la revision de modelos de coordinacion."
- **razon**: la audiencia conecta primero con el problema operativo que reconoce de su dia a dia. El termino tecnico funciona mejor como ejemplo que aterriza, no como entrada.
- **cuando aplica**: siempre en posts LinkedIn para audiencia AEC/BIM.
- **cuando no aplica**: posts tecnicos dirigidos a usuarios avanzados donde el termino BIM es contexto compartido desde la primera linea.

---

## CAL-LW-006 — No repetir la palabra nucleo mas de dos veces

- **patron observado**: "criterio" (o la palabra central de la tesis) aparece 5 o mas veces en el post.
- **ejemplo rechazado**: "El criterio no esta claro. Sin criterio, la automatizacion no tiene criterio. Definir criterio es el primer paso."
- **ejemplo preferido**: usar sinonimos operativos ("reglas de revision", "que se acepta", "como se cierra", "que es suficiente") despues de la segunda mencion.
- **razon**: la repeticion excesiva convierte el texto en mantra. Suena formulado, no hablado.
- **cuando aplica**: siempre.
- **cuando no aplica**: si la repeticion es deliberada como recurso retorico y David la aprueba.

---

## CAL-LW-007 — Evitar frases que suenan a consultor o paper

- **patron observado**: uso de terminologia que suena a informe o presentacion de consultoria, no a profesional hablando con pares.
- **ejemplo rechazado**: "La capacidad tecnologica ya existe", "criterio operativo explicito", "umbrales de decision", "amplificar la confusion", "impacto operativo".
- **ejemplo preferido**: "Las herramientas ya estan", "las reglas con que el equipo revisa", "cuando algo pasa o no pasa", "el desorden crece", "lo que cambia en la practica".
- **razon**: David habla como profesional que trabaja en esto, no como consultor que lo presenta en una slide. La audiencia nota la diferencia.
- **cuando aplica**: siempre en copy publico LinkedIn/X.
- **cuando no aplica**: documentacion interna, reportes tecnicos, materiales de formacion.

---

## CAL-LW-008 — Cierre sin moraleja ni llamada generica

- **patron observado**: el post cierra con una frase moralizante, una leccion abstracta o una pregunta tan amplia que no invita respuesta real.
- **ejemplo rechazado**: "El verdadero desafio no es la tecnologia, sino el criterio." / "¿Estas listo para el cambio?"
- **ejemplo preferido**: "En tu flujo actual, ¿que criterio sigue sin estar definido por escrito?" / "¿Que observacion se cierra hoy en tu equipo sin que nadie haya definido cuando cerrarla?"
- **razon**: un cierre especifico invita a que la persona piense en su situacion real. Un cierre generico se siente como slogan.
- **cuando aplica**: siempre en LinkedIn.
- **cuando no aplica**: en X, donde la brevedad justifica un cierre mas seco.

---

## CAL-LW-009 — Preferir vocabulario operativo sobre vocabulario abstracto

- **patron observado**: el borrador usa sustantivos abstractos donde existen equivalentes operativos mas concretos.
- **ejemplo rechazado**: "automatizacion", "proceso", "criterio", "decision" como bloques repetidos sin aterrizaje.
- **ejemplo preferido**: rotar con "revision", "observaciones", "entregables", "reportes", "rehacer", "aceptar", "decidir", "cerrar", "avanzar de etapa".
- **razon**: el vocabulario operativo es el lenguaje de trabajo real de la audiencia. Los sustantivos abstractos son validos como tesis, pero el desarrollo debe aterrizar en verbos y escenas que un coordinador o jefe de proyecto reconozca.
- **cuando aplica**: siempre en el desarrollo y cierre del post.
- **cuando no aplica**: la tesis inicial puede usar un termino abstracto si el resto del post lo traduce.
