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
