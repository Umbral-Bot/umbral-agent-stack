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

### CAL-005 — Penalizar tono de consultor o paper

- **Patron observado:** El borrador usa terminologia que suena a informe de consultoria o paper academico en vez de a profesional hablando con pares.
- **Ejemplo rechazado:** "La capacidad tecnologica ya existe", "criterio operativo explicito", "umbrales de decision", "amplificar la confusion", "impacto operativo", "sistemas algoritmicos para gestionar trabajo".
- **Ejemplo preferido:** "Las herramientas ya estan", "las reglas con que el equipo revisa", "cuando algo pasa o no pasa", "el desorden crece", "lo que cambia en la practica".
- **Razon:** David habla como profesional de AEC que trabaja en esto, no como consultor que presenta un framework. La audiencia nota la diferencia entre lenguaje vivido y lenguaje prestado de un informe.
- **Cuando aplica:** Siempre en copy publico LinkedIn/X. Especialmente en revisiones de voz donde el score de naturalidad baja de 4/5.
- **Cuando no aplica:** Documentacion interna, reportes tecnicos.

### CAL-006 — Contextualizar antes de tecnificar

- **Patron observado:** El borrador entra directamente a "modelo BIM", "modelo federado" o tecnologia especifica sin establecer primero el problema operativo general.
- **Ejemplo rechazado:** "Cuando un modelo BIM tiene errores de coordinacion, la automatizacion no ayuda."
- **Ejemplo preferido:** "Cuando nadie definio que revisar ni cuando algo esta listo, meter tecnologia no ordena nada. Eso se ve, por ejemplo, en la revision de modelos de coordinacion."
- **Razon:** La audiencia conecta primero con un problema que reconoce de su dia a dia. El termino tecnico funciona mejor como ejemplo que aterriza, no como puerta de entrada.
- **Cuando aplica:** Siempre en posts para audiencia AEC/BIM. Bloquear si "modelo BIM" aparece en las primeras dos oraciones sin contexto de proceso previo.
- **Cuando no aplica:** Posts tecnicos dirigidos a usuarios avanzados donde BIM es contexto compartido.
