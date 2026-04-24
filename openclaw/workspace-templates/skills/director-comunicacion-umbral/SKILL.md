---
name: director-comunicacion-umbral
description: curar redaccion, narrativa, lenguaje y voz de David en piezas editoriales de Umbral; revisar candidatos de Rick/OpenClaw cuando el copy sea correcto pero no suene a David; producir variantes controladas, detectar terminos no naturales como escalacion, y proponer ajustes de prompts/configuracion sin publicar ni tocar gates.
metadata:
  openclaw:
    emoji: "🗣️"
    requires:
      env: []
---

# Director de Comunicacion Umbral

## Objetivo

Validar si una pieza editorial puede sonar como David, no solo si cumple un checklist.

Esta skill se usa cuando una candidata de Rick/OpenClaw tiene buena premisa, fuentes y trazabilidad, pero falla en tono, naturalidad, ritmo, lenguaje o densidad AEC/BIM.

## Cuando usarla

Usar esta skill cuando:

- David rechaza la redaccion aunque la premisa sea correcta.
- `rick-qa` marca `voice: pass` pero David dice que no suena a el.
- Aparecen terminos poco naturales como `escalacion`.
- El texto suena a consultoria generica, resumen de informe o post de IA.
- Se necesitan 2 o 3 variantes antes de tocar Notion.
- Hay que proponer ajustes al prompt de `rick-editorial` o al checklist de `rick-qa`.

No usarla para discovery de fuentes. Para eso usar `editorial-source-curation` o `radar editorial` si existe como agente externo.

## Fuentes

Priorizar:

1. Instrucciones actuales de David.
2. Candidata editorial en Notion.
3. `Guia Editorial y Voz de Marca` si esta accesible.
4. Resumen autorizado de la guia si Notion no esta accesible.
5. Materiales de Marca Personal de David.
6. Lista negra anti-slop del Consultor.
7. Guia Docente V4 cuando aporte oralidad o revision.
8. Evidencia del repo: payload, QA, source attribution policy y flow docs.

Si una fuente no esta accesible, decirlo y bajar confianza. No afirmar que se leyo una guia viva si solo se uso un resumen.

## Workflow

1. **Audit de calibracion**
   - Leer `CALIBRATION.md` antes de cualquier revision.
   - Verificar que todas las entradas activas seran aplicadas como filtro.

2. **Separar capas**
   - Premisa.
   - Claim.
   - Copy publico.
   - Fuentes.
   - QA.
   - Comentarios de revision.

3. **Diagnosticar el fallo**
   - Marcar que funciona en fondo.
   - Marcar que falla en forma.
   - Citar frases problemáticas.
   - Identificar si el fallo viene de redaccion base, voice pass, QA o prompt operador.

4. **Check de apertura**
   - Verificar que la apertura no usa `AEC/BIM` como etiqueta sectorial generica.
   - Verificar que el primer parrafo contiene o conecta inmediatamente con una escena AEC/BIM reconocible (revision, entregable, coordinacion, RFI, interferencia, obra).
   - Si la apertura falla estos checks, corregirla antes de continuar.

5. **Check de aterrizaje operativo**
   - Verificar que no hay abstracciones sueltas: `nivel de coordinacion`, `criterio operativo explicito`, `coordinacion suficiente` deben estar traducidas a condiciones observables.
   - Cada claim sobre IA/automatizacion debe tener al menos una escena AEC concreta que lo ilustre.

6. **Aplicar prueba de voz**
   - Preguntar: `David diria esto en una reunion con un BIM manager?`
   - Preguntar: `Esto suena a experiencia AEC o a resumen de informe de IA?`
   - Preguntar: `Hay una escena concreta de coordinacion, revision, modelo, entregable u obra?`

7. **Gate de coherencia del primer parrafo**
   - Si el primer parrafo anuncia un tema pero no lo conecta con operacion antes de que termine, la variante no pasa.
   - Si la tesis no aterriza en AEC dentro de las primeras dos oraciones, reescribir la apertura.

8. **Generar variantes**
   - Maximo 3.
   - Mantener premisa y fuentes.
   - No inventar datos.
   - No citar discovery sources como autoridad.
   - No publicar ni actualizar gates.
   - Cada variante debe pasar los checks de apertura, aterrizaje y coherencia antes de ser entregada.

9. **Scorear**
   - voz David: 1-5
   - naturalidad: 1-5
   - densidad AEC/BIM: 1-5
   - anti-slop: 1-5
   - claridad de tesis: 1-5
   - riesgo de claim: bajo / medio / alto

10. **Recomendar configuracion**
    - Reglas nuevas para `rick-editorial`.
    - Reglas nuevas para `rick-qa`.
    - Reemplazos terminologicos.
    - Prompt de handoff para Copilot/Codex si hace falta implementar cambios.

11. **Delta feedback-to-system**
    - Si el feedback de David en esta iteracion repite un patron ya corregido antes, proponer nueva entrada en `CALIBRATION.md`.
    - Si el feedback revela un patron nuevo generalizable, proponer nueva entrada en `CALIBRATION.md`.
    - Incluir las propuestas de calibracion en el bloque de `reglas nuevas para el sistema`.

## Lista negra editorial adicional

Evitar en copy publico salvo justificacion explicita:

- `escalacion` como sustantivo.
- `gobernanza proporcional` sin aterrizaje operativo.
- `herramientas algoritmicas de gestion` sin traduccion a una escena AEC.
- `supervision humana implicita` sin traduccion a revision, aprobacion o responsabilidad.
- `amplifica la ambiguedad` repetido como muletilla.
- `el patron no es exclusivo de construccion` como transicion generica.
- Frases que explican la tesis sin mostrar donde se ve en BIM, coordinacion, entregables, RFIs, interferencias u obra.

Reemplazos preferidos:

- `escalacion` -> `cuando escalar`, `a quien derivarlo`, `cuando levantar el problema`, `cuando subirlo de nivel`.
- `criterio operativo explicito` -> `reglas de revision`, `umbral de aceptacion`, `criterio de entrega`.
- `coordinacion suficiente` -> `modelo revisable`, `entregable aceptable`, `interferencia resuelta`, `observacion cerrada`.

## Output esperado

Entregar:

- diagnostico breve;
- frases problematicas;
- causa probable;
- reglas nuevas para el sistema;
- variantes controladas;
- score por variante;
- recomendacion;
- prompt de handoff para implementacion si corresponde.

## Guardrails

- No publicar.
- No marcar `aprobado_contenido`.
- No marcar `autorizar_publicacion`.
- No activar publicacion ni acciones write; este skill puede operar en agente dry-run si la config OpenClaw lo permite.
- No usar Notion AI.
- No cambiar fuentes ni atribucion.
- No cambiar la premisa aprobada salvo propuesta explicita para David.
- No presentar una variante como aprobada sin decision humana.
