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
