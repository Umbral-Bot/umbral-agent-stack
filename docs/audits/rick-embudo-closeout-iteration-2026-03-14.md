# Rick Embudo Closeout Iteration — 2026-03-14

## Objetivo

Cerrar la desviación detectada en Rick al analizar el experimento editorial/comercial del proyecto embudo:

- antes diagnosticaba y ejecutaba parcialmente;
- pero no cerraba el experimento con:
  - crítica explícita,
  - selección de pieza ganadora,
  - CTA canónico provisional,
  - corrección de drift en Linear/Notion,
  - y salida revisable desde Notion.

## Ajustes aplicados al runtime

Se endurecieron los prompts base de Rick en:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`

Cambios relevantes:

1. **Cierre de experimento = crítica y selección**
   - Si David pide validar/cerrar/elegir, Rick debe decir qué está fuerte, qué está flojo, qué pieza gana, cuál CTA queda provisional/canónico y qué sigue pendiente.

2. **Drift de estado = corregir, no solo narrar**
   - Si hay progreso real pero Linear/Notion están desalineados, Rick debe intentar corregirlo en la misma iteración o declarar explícitamente el bloqueo.

Estos cambios se sincronizaron al workspace vivo en VPS y se reinició `openclaw-gateway.service`.

## Intervención directa en la sesión de Rick

Se inyectaron turnos directamente en la sesión Telegram de Rick (`agent:main:telegram:slash:1813248373`) con mensajes en español y estilo natural, simulando al usuario.

Turno clave inyectado:

> cerrar el experimento como proyecto real dentro del embudo, no solo como lote de piezas; revisar críticamente lo producido; elegir pieza ganadora; definir si `diagnóstico operativo gratuito` queda canónico; corregir drift en Linear/Notion; dejarlo revisable desde Notion.

Turno de remate:

> dejar explícito que el proyecto de Linear sigue en backlog si no podía mutarlo con tools; no inventar; responder corto y ejecutivo.

## Evidencia de ejecución real

### Cambios reales hechos por Rick

1. **Seleccionó pieza principal**
   - pieza ganadora: `landing-umbralbim-io.html`

2. **Normalizó CTA provisional en el hub real**
   - archivo:
     - `proyectos/venta-servicios-embudo/landing-umbralbim-io.html`
   - cambios verificados:
     - `Agendar diagnóstico operativo`
     - `Agendar diagnóstico operativo de 30 min`
     - `mailto:...subject=Diagnostico%20operativo%20Umbral%20BIM`

3. **Escribió cierre crítico en repo**
   - `proyectos/venta-servicios-embudo/docs/40_cierre_critico_experimento_embudo_2026-03-14.md`

4. **Escribió cierre crítico en carpeta compartida**
   - `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\informes\40_cierre_critico_experimento_embudo_2026-03-14.md`

5. **Corrigió la issue principal en Linear**
   - `UMB-39` pasó a `In Progress`
   - comentario de trazabilidad agregado con:
     - avance
     - artefactos
     - verificación
     - siguiente acción
     - estado propuesto

6. **Creó project update en Linear**
   - proyecto: `Proyecto Embudo Ventas`

7. **Actualizó el proyecto en Notion**
   - `https://www.notion.so/Proyecto-Embudo-Ventas-31e5f443fb5c8125a21ce5333fb32a03`

8. **Creó una página Notion revisable del cierre**
   - `https://www.notion.so/Cierre-cr-tico-Proyecto-Embudo-Ventas-2026-03-14-3235f443fb5c81f880cdd59aada7d3b7`

### Verificación adicional

Se verificó directamente:

- lectura del hub actualizado;
- presencia del CTA nuevo en líneas concretas del HTML;
- lectura de la página Notion de cierre;
- lectura de `linear.list_project_issues`.

## Resultado del test

### Antes

Rick:

- comparaba bien;
- producía piezas;
- dejaba trazabilidad parcial;
- pero no cerraba el experimento como proyecto real.

### Después

Rick:

- hizo crítica explícita;
- eligió pieza principal;
- dejó CTA canónico provisional;
- corrigió la issue principal en Linear;
- dejó el cierre fácil de revisar en Notion;
- y declaró el drift residual sin inventar mutaciones no soportadas.

## Drift residual real

Sigue pendiente un desalineamiento:

- el proyecto `Proyecto Embudo Ventas` en Linear todavía aparece con `state: backlog`
- mientras `UMB-39` ya quedó en `In Progress`

Rick no lo ocultó. Lo dejó explícito como drift pendiente porque no tenía una mutación confiable de project state con las tools disponibles.

También siguen pendientes reales del frente:

- mecanismo real de captura;
- prueba social verificable;
- frente editorial vivo;
- cierre comercial completo del CTA final.

## Veredicto

El comportamiento de Rick en este frente quedó **suficientemente corregido**.

No solo respondió mejor: ejecutó el cierre esperado con:

- repositorio,
- carpeta compartida,
- Linear,
- Notion,
- y una respuesta final alineada con la evidencia.

El residual ya no es de comprensión ni de disciplina básica del loop, sino de capacidades disponibles para mutar el estado del proyecto Linear y de decisiones humanas pendientes sobre el CTA/comercialización final.
