# Integración rigurosa de Archivo legacy

Fecha: 2026-03-15

## Objetivo

Ordenar `🗃 Archivo legacy — entregables sueltos` y conectarlo con la estructura viva de Notion:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`

La meta no era migrar "todo" a `Entregables`, sino separar:

- entregables canónicos que sí deben revisarse o quedar como referencia vigente
- iteraciones intermedias que solo sirven como historial
- ruido histórico o duplicados que no conviene promover a entregable activo

## Diagnóstico

`Archivo legacy` contenía 30 páginas mezcladas de varios frentes:

- editorial
- laboral
- VM / browser / RPA / Freepik
- mejora continua
- embudo

El problema real no era solo visual. Había tres clases de contenido mezclado:

1. entregables ya canónicos o claramente migrables
2. iteraciones intermedias que no debían aparecer como entregables finales
3. duplicados / ruido histórico, especialmente cinco `OODA Weekly Report - 2026-03-10`

## Criterio aplicado

Se tomó esta regla:

- si la página legacy ya representa una pieza revisable o una referencia vigente del sistema, se refleja en `📬 Entregables Rick — Revisión`
- si solo documenta una iteración vieja, prueba puntual o estado ya superado, se mantiene en `Archivo legacy`
- si está duplicada o ya quedó absorbida por otra pieza más estable, se deja explícitamente como ruido histórico

## Backfill canónico realizado

Se crearon o completaron estos entregables canónicos desde `Archivo legacy`:

- `Vertical slice del sistema editorial automatizado`
- `Pack multicanal aprobado del sistema editorial automatizado`
- `Cola de aprobación de oportunidades laborales`
- `Perfil maestro del sistema laboral`
- `Sistema base de postulación laboral`
- `Reglas confirmadas del sistema laboral`
- `Validación typed exitosa del control de navegador en VM`
- `Bloqueo raíz del RPA GUI en VM`
- `Estado real de Freepik en VM`

Además, el archivo quedó conectado con entregables canónicos ya existentes:

- shortlist laboral
- auditoría de mejora continua
- cierre crítico del embudo
- framing tipo Veritasium aplicado al embudo
- benchmark Ruben Hassid

## Qué no se promovió a entregable activo

Se dejó solo como historial:

- revisiones humanas/editoriales intermedias
- pruebas aisladas como `Prueba LinkedIn VM + borrador correo`
- estados VM superados por validaciones posteriores
- la pieza `Proyecto Embudo Ventas — adaptación editorial desde Veritasium (2026-03-14)` por quedar absorbida por el framing aplicado canónico
- los cinco `OODA Weekly Report - 2026-03-10`

## Reorganización de la página legacy

La API de Notion no permitió reordenar físicamente los child pages sin tratarlos como eliminación o movimiento riesgoso.

Por eso se aplicó una solución segura:

- se preservó intacto el inventario histórico de child pages
- se añadió arriba un índice estructurado
- el índice enlaza a los entregables canónicos y explica el criterio
- la página pasó de ser un dump plano a un archivo legible y conectado con el sistema nuevo

## Recanalización física del legacy

Después de la clasificación inicial, se hizo un segundo paso: mover físicamente las 30 páginas históricas a tres subpáginas frías, sin cambiar sus URLs.

Contenedores creados:

- `🧭 Integrados o consolidados`
- `🪜 Iteraciones intermedias o superadas`
- `🗑 Duplicados o ruido histórico`

Resultado:

- la página principal `🗃 Archivo legacy — entregables sueltos` dejó de mostrar 30 child pages planas
- el archivo principal quedó reducido a un resumen, criterio de uso y solo tres subpáginas
- la información no se perdió: solo se recanalizó en subpáginas temáticas
- como las URLs de Notion no cambian al mover una página, cualquier referencia existente sigue siendo válida

## Rastreo de dependencias y referencias

Se revisaron referencias locales en el repo buscando:

- IDs legacy concretos
- menciones a `Archivo legacy`
- entregables canónicos asociados

Hallazgo:

- no apareció dependencia estructural del sistema que requiera que esas páginas permanezcan colgadas directamente del contenedor principal
- sí aparecieron referencias documentales en auditorías del repo a URLs de páginas del embudo ya consolidadas
- eso no es un problema, porque las URLs de Notion se mantienen al mover la página a otra ubicación

Conclusión:

- la recanalización física del legacy no rompe activos ni dependencias locales conocidas de Rick
- el único vínculo durable observado en repo son enlaces documentales, que siguen resolviendo bien

## Fase final: salida de OpenClaw

Para terminar de limpiar el dashboard operativo:

- se creó la página `🧊 Archivo histórico — Umbral`
- se movió `🗃 Archivo legacy — entregables sueltos` bajo ese archivo frío
- `OpenClaw` quedó mostrando solo el flujo activo
- la leyenda del dashboard dejó de mencionar `Archivo legacy` y pasó a referir `Archivo histórico — Umbral`

Resultado:

- `OpenClaw` queda reservado para operación
- el histórico queda preservado fuera del tablero principal
- no se perdió información ni se invalidaron enlaces previos

## Resultado

`Archivo legacy` ahora cumple un rol claro:

- histórico de outputs viejos
- índice de qué ya fue absorbido por `Entregables`
- cuarentena de iteraciones y ruido histórico que no deben volver a confundirse con piezas activas

El flujo de Notion queda así:

`Proyecto -> Tarea -> Entregable -> Revisión`

`Archivo legacy` ya no compite con ese flujo.

## Verificación

Se verificó en vivo:

- la página `🗃 Archivo legacy — entregables sueltos` con el nuevo índice estructurado
- la existencia y contenido de entregables canónicos creados desde legacy
- la consistencia del enlace entre `Archivo legacy` y `📬 Entregables Rick — Revisión`

## Pendiente residual

No se borró contenido legacy ni se hizo purga destructiva. Eso fue intencional.

Si más adelante se quiere reducir aún más el ruido histórico, el siguiente paso correcto es:

- agrupar o archivar fuera del foco los cinco `OODA Weekly Report - 2026-03-10`
- revisar si algunas iteraciones intermedias pueden moverse a un archivo aún más frío
