# Calibration — Director de Comunicacion Umbral

## Proposito

Este archivo absorbe feedback humano recurrente sobre voz, apertura, naturalidad y coherencia editorial. Las reglas aqui documentadas son persistentes: el agente debe aplicarlas en cada revision sin esperar que David las repita.

## Como usar este archivo

1. Antes de generar variantes, leer todas las entradas activas.
2. Aplicar cada regla como filtro de aceptacion en la pasada de voz.
3. Si una variante viola una regla, corregirla o descartarla antes de entregarla.
4. Si David da feedback nuevo que contradice o extiende una regla, actualizar este archivo en el mismo PR o handoff.

## Entradas de calibracion

### CAL-001 — Apertura con etiqueta sectorial generica

- **Patron observado:** Abrir la pieza con `En AEC/BIM, ...` como etiqueta generica sin escena operativa.
- **Ejemplo rechazado:** `En AEC/BIM, el problema no suele ser la falta de IA.`
- **Ejemplo preferido:** `En AEC, el problema no suele ser la falta de IA.` o `Cuando un equipo BIM todavia no tiene definido que cuenta como revision valida...`
- **Razon:** `AEC/BIM` como binomio generico suena a etiqueta de informe, no a conversacion profesional. David puede decir `sector AEC`, `industria de la construccion`, `equipos BIM` o `En AEC` cuando conecta directamente con una escena reconocible.
- **Cuando aplica:** Siempre que la apertura use `AEC/BIM` como label inicial sin operacion concreta.
- **Cuando no aplica:** `AEC/BIM` puede aparecer en el cuerpo del texto cuando se refiere a la interseccion real de ambas disciplinas en una escena concreta, no como etiqueta de arranque.

### CAL-002 — Nivel de coordinacion abstracto

- **Patron observado:** Usar `nivel de coordinacion` como concepto abstracto sin bajar a condicion observable.
- **Ejemplo rechazado:** `que nivel de coordinacion es suficiente para avanzar`
- **Ejemplo preferido:** `que queda resuelto`, `que interferencia se acepta`, `que observacion se puede cerrar`, `que entregable ya es revisable`
- **Razon:** `nivel de coordinacion` no tiene significado operativo si no se traduce a algo que un coordinador BIM pueda verificar en un modelo, una sesion de coordinacion o un entregable.
- **Cuando aplica:** Siempre que `nivel de coordinacion` aparezca como abstraccion sin condicion observable adjunta.
- **Cuando no aplica:** Si la pieza define explicitamente que significa ese nivel (ej. `nivel de coordinacion medido por interferencias abiertas en el modelo federado`), puede mantenerse.

### CAL-003 — Coherencia del primer parrafo

- **Patron observado:** El primer parrafo anuncia un tema pero no lo conecta con una situacion reconocible en AEC/BIM antes de que termine.
- **Ejemplo rechazado:** `En AEC, el problema no suele ser la falta de IA. Suele ser la falta de criterio claro.` (correcto como tesis, pero si el segundo parrafo salta a automatizacion generica sin escena, la apertura queda suelta).
- **Ejemplo preferido:** `Si un equipo todavia no tiene definido que cuenta como una revision valida de un modelo BIM, meter automatizacion no ordena nada.` (la escena llega dentro de las primeras dos oraciones).
- **Razon:** David habla desde operacion, no desde abstraccion. La audiencia reconoce la pieza como suya cuando ve una escena de su dia a dia en los primeros segundos.
- **Cuando aplica:** Siempre. El primer parrafo debe contener o conectar inmediatamente con una escena AEC/BIM reconocible.
- **Cuando no aplica:** Piezas donde David deliberadamente elige una apertura provocadora fuera de AEC (poco frecuente, requiere decision explicita de David).

### CAL-004 — Feedback humano recurrente se convierte en regla

- **Patron observado:** David corrige el mismo problema mas de una vez en iteraciones distintas.
- **Accion requerida:** Si el feedback de David repite una correccion ya hecha en una iteracion anterior, el agente debe proponer una nueva entrada en este archivo como parte del handoff. No basta con corregir el copy; hay que corregir el sistema.
- **Razon:** El objetivo es que el agente aprenda, no que David repita.
- **Cuando aplica:** Siempre que el feedback de revision repita un patron ya corregido antes.
- **Cuando no aplica:** Feedback unico o especifico de una pieza que no es generalizable.

### CAL-005 — Muletillas de enfasis y repeticion (feedback CAND-001 2026-06-29)

- **"real"/"realidad" como muletilla de enfasis** -> reescribir con condicion observable. FLAG: `el riesgo real`, `lo real es`; OK: `decision real del equipo`.
- **"amplificar" repetido** -> variar el verbo o aterrizar en escena concreta (clash, RFI, entregable, sesion de coordinacion).
- **"no es solo X" sin Y operativo** -> eliminar; si no hay contraparte medible, la formula sobra.
- **Razon:** feedback recurrente CAND-001; refuerza C1 anti-muletilla del benchmark v1.
- **Cuando aplica:** revision de cualquier candidato editorial.
- **Cuando no aplica:** cita textual de fuente externa donde la palabra es parte del dato, no enfasis.

### CAL-006 — LinkedIn ALT 1 afirmativa (feedback David CAND-001 2026-06-29)

- **Patron preferido:** abrir con escena o afirmacion operativa, no con pregunta retorica inicial.
- **Ejemplo preferido (ALT 1):** `Un equipo BIM puede sumar un agente que revise modelos antes de definir que cuenta como una revision valida.`
- **Ejemplo a evitar como apertura:** `¿Ya esta suficientemente ordenado el proceso...?` cuando existe variante afirmativa con mas peso editorial.
- **Razon:** la audiencia AEC reconoce la escena antes que el marco abstracto; menos tono consultor.
- **Cuando aplica:** LinkedIn y hooks de blog cuando David pida variante afirmativa.
- **Cuando no aplica:** piezas donde David elige deliberadamente apertura interrogativa (decision explicita).

### CAL-007 — Sensibilidad y precision tecnica BIM (feedback David CAND-001 v3.1 2026-06-30)

- **Evitar:** "pocas personas" como marco de la automatizacion; "procesos lentos" o lecturas que aludan al lector como deficiente.
- **Evitar:** frases forzadas tipo "que fuente prevalece ante un conflicto" sin escena operativa clara.
- **Evitar:** atribuir al agente "mantener consistencia entre disciplinas" como si resolviera coordinacion por si solo.
- **Preferir:** apoyo a agrupar incidencias, resumir observaciones repetidas y preparar seguimiento de cambios, con criterios y validacion humana.
- **Terminologia:** usar "incidencias"/issues cuando se habla de clasificacion o gestion; reservar "interferencias"/clashes para deteccion geometrica.
- **Razon:** feedback humano v3.1; tono respetuoso con el lector y precision AEC sin sobreprometer capacidades del agente.
- **Cuando aplica:** blog y piezas largas de opinion operativa AEC/BIM.
- **Cuando no aplica:** citas textuales de fuente externa.
