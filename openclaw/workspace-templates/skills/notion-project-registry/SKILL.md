---
name: notion-project-registry
description: diseÃ±ar y mantener un registro maestro de proyectos en notion con vistas
  de tabla, kanban y timeline, enlazado a drive/gdrive, linear y entregables. usar
  cuando chatgpt necesite crear, migrar, auditar o actualizar una base de datos de
  proyectos; normalizar propiedades, estados y reglas de seguimiento; crear o actualizar
  registros de proyecto; dejar updates cronolÃ³gicos; reflejar bloqueos o issues sin
  respuesta; o trabajar con tools de notion de bajo nivel y payloads raw sobre database/data
  source, page properties y blocks.
metadata:
  openclaw:
    emoji: 🗂️
    requires:
      env: []
---

# Notion Project Registry

## Seguir este flujo
1. Identificar el modo de trabajo:
   - crear un registro nuevo;
   - adaptar una base existente;
   - mantener registros y updates semanales;
   - operar con tools low-level o payloads raw.
2. Consultar `references/schema.md` y alinear el esquema antes de tocar pÃ¡ginas sueltas.
3. Usar el registro maestro como fuente Ãºnica del estado cross-tool:
   - notion = vista de portfolio y dashboard;
   - linear = ejecuciÃ³n detallada e issues;
   - drive = archivos y entregables.
4. Crear o actualizar la fila del proyecto antes de editar documentos sueltos o dejar notas dispersas.
5. Mantener una pÃ¡gina por proyecto con propiedades + cuerpo estructurado:
   - `links operativos`
   - `updates`
   - `handoff`
6. Revisar vistas y controles de calidad al final.

## Elegir el esquema correcto
- Preferir el esquema `api-stable` de `references/schema.md` cuando haya que trabajar con tools de bajo nivel o payloads raw.
- Preferir `select` para `Estado` por compatibilidad API. Solo reutilizar una propiedad `status` existente si ya estÃ¡ creada y no hay que mutar su esquema.
- Preferir `title`, `select`, `rich_text`, `multi_select`, `url` y `date` para campos operativos.
- Usar `people` o `relation` solo cuando el tool pueda resolver ids de usuarios o pÃ¡ginas de forma confiable.
- Usar ids de propiedad cuando el tool los exponga. No depender de nombres de columna si puede haber renombres.
- No usar el body de la page como sustituto del registro maestro; usarlo solo para historial, links secundarios y handoff.

## Crear un registro nuevo o adaptar uno existente
### Crear desde cero
1. Crear el database container o data source.
2. Crear las propiedades canÃ³nicas del esquema.
3. Crear una plantilla de pÃ¡gina con las secciones:
   - `links operativos`
   - `updates`
   - `handoff`
4. Crear las vistas recomendadas en la ui de notion. No asumir que la api puede gestionar vistas.
5. Cargar los primeros proyectos solo despuÃ©s de confirmar estados canÃ³nicos.

### Adaptar una base existente
1. Mapear propiedades existentes a las canÃ³nicas antes de crear columnas nuevas.
2. Renombrar o reutilizar columnas equivalentes; evitar duplicados como `owner`, `pm`, `responsable`.
3. Mantener una sola columna de estado canÃ³nica.
4. Rellenar huecos mÃ­nimos:
   - `Drive`
   - `Linear`
   - `Fecha objetivo`
   - `Ultimo update`
5. Marcar filas incompletas como deuda operativa en `Bloqueos` o `Issues abiertas o sin respuesta`, no como estado ambiguo.

## Crear o actualizar un proyecto
Al aparecer un proyecto nuevo:
1. Crear la fila el mismo dÃ­a con el mÃ­nimo obligatorio:
   - `Proyecto`
   - `Estado`
   - `Responsable`
   - `Fecha inicio` o `Fecha objetivo` si existe
   - `Drive` y `Linear` si ya existen
2. Si algÃºn link canÃ³nico aÃºn no existe, dejar el campo vacÃ­o temporalmente y dejar constancia en el primer update.
3. Completar el resto de propiedades antes del siguiente corte semanal.
4. Crear o actualizar la pÃ¡gina del proyecto con el template base.
5. Evitar crear una pÃ¡gina suelta sin fila en el registro.

Al actualizar un proyecto existente:
1. Cambiar primero propiedades canÃ³nicas.
2. Luego aÃ±adir un update cronolÃ³gico en el cuerpo de la pÃ¡gina.
3. Si cambian links, reemplazar el link canÃ³nico en la propiedad correspondiente y registrar el cambio en el update.
4. Si cambia el milestone o aparece un bloqueo, actualizar tambiÃ©n `Siguiente hito`, `Bloqueos`, `Issues abiertas o sin respuesta` y `Ultimo update`.

## Enlazar drive, linear y entregables
- Guardar un Ãºnico link canÃ³nico de carpeta compartida en `Drive`.
- Guardar un Ãºnico link canÃ³nico del proyecto en `Linear`.
- Guardar links secundarios, specs, entregables y docs en `Links relevantes` y/o en la secciÃ³n `links operativos` del cuerpo.
- Tratar notion como Ã­ndice maestro, no como espejo completo de linear o drive.
- No copiar todos los issues de linear. Resumir solo los abiertos o sin respuesta que afectan seguimiento.
- Mantener nombres consistentes entre notion, drive y linear cuando sea posible.
- Si no existe proyecto de linear todavÃ­a, dejar `Linear` vacÃ­o y explicitar `sin proyecto linear` en el Ãºltimo update. No inventar placeholders.

## Crear vistas Ãºtiles
Crear estas vistas mÃ­nimas en la ui de notion:
1. `master`
   - layout: table
   - mostrar propiedades clave
   - ordenar por `Estado`, luego `Fecha objetivo`, luego `Ultimo update` descendente
2. `seguimiento`
   - layout: board
   - agrupar por `Estado`
   - ordenar grupos: `activo`, `bloqueado`, `en espera`, `cerrado`
   - mostrar `Responsable`, `Siguiente hito`, `Fecha objetivo`, `Ultimo update`
3. `roadmap`
   - layout: timeline
   - usar `Fecha inicio` + `Fecha objetivo` como rango si la base lo soporta; si no, usar `Fecha objetivo`
   - filtrar a proyectos no `cerrado`
4. `atencion`
   - layout: table o list
   - filtrar proyectos con `Bloqueos` no vacÃ­o o `Issues abiertas o sin respuesta` no vacÃ­o
   - opcional: incluir proyectos cuyo `Ultimo update` estÃ© desactualizado

Crear una vista mÃ­nima de backlog solo si el equipo separa intake de proyectos activos. No usar backlog como sustituto del kanban principal.

## Dejar updates cronolÃ³gicos
Mantener `Ultimo update` como fecha del update mÃ¡s reciente.
AÃ±adir cada update nuevo al final de la secciÃ³n `updates` de la pÃ¡gina del proyecto, con fecha visible y formato mÃ­nimo.

Usar este formato mÃ­nimo:
```text
[yyyy-mm-dd] estado: <activo|bloqueado|en espera|cerrado>
hecho desde el ultimo update:
siguiente hito:
bloqueos:
issues sin respuesta:
links o entregables actualizados:
siguiente accion / owner:
```

Aplicar estas reglas:
- `activo`: dejar update semanal obligatorio.
- `bloqueado`: dejar update semanal obligatorio y cada vez que cambie el bloqueo.
- `en espera`: dejar al menos un update breve en cada revisiÃ³n semanal indicando si sigue igual y quÃ© dispara la reactivaciÃ³n.
- `cerrado`: dejar un update final de cierre y completar `Notas de handoff`.

## Reflejar bloqueos e issues sin respuesta
- Escribir bloqueos en tÃ©rminos accionables: quÃ© bloquea, quiÃ©n lo destraba y cuÃ¡l es la siguiente acciÃ³n.
- Escribir issues sin respuesta como lista corta y priorizada, con id o link si existe.
- No dejar `bloqueado` con `Bloqueos` vacÃ­o.
- No dejar `Issues abiertas o sin respuesta` lleno si el proyecto ya no requiere atenciÃ³n; limpiarlo cuando quede resuelto.
- Si el proyecto estÃ¡ `en espera` por decisiÃ³n estratÃ©gica y no por dependencia, explicar el gatillo de reanudaciÃ³n en el update y no marcarlo como `bloqueado`.

## Distinguir estados sin ambigÃ¼edad
Usar estas definiciones:
- `activo`: el proyecto se estÃ¡ moviendo y existe una siguiente acciÃ³n concreta.
- `bloqueado`: el proyecto no puede avanzar por una dependencia externa o decisiÃ³n pendiente.
- `en espera`: el proyecto estÃ¡ pausado de forma intencional; no se espera movimiento hasta que ocurra un gatillo de reanudaciÃ³n.
- `cerrado`: el proyecto terminÃ³ o se cancelÃ³ y ya no necesita seguimiento operativo semanal.

No inventar estados ambiguos como `moving`, `ok`, `pending`, `paused?`, `almost done`.

## Aplicar higiene semanal
En cada corte semanal:
1. Revisar todos los proyectos no `cerrado`.
2. Actualizar `Ultimo update`.
3. Confirmar que `Siguiente hito` tenga dueÃ±o o fecha.
4. Confirmar que `Drive` y `Linear` apunten a la ubicaciÃ³n canÃ³nica actual.
5. Limpiar `Bloqueos` e `Issues abiertas o sin respuesta` resueltos.
6. Mover a `cerrado` proyectos terminados y dejar handoff.
7. Detectar anti-patrones antes de cerrar la revisiÃ³n.

## Corregir anti-patrones
Corregir de inmediato:
- pÃ¡ginas sueltas sin registro maestro
- filas duplicadas para el mismo proyecto
- links faltantes o rotos en drive o linear
- estado ambiguo o desactualizado
- updates en slack o comentarios que nunca llegan a notion
- `Ultimo update` viejo con un body muy reciente o viceversa
- handoff disperso en docs separados sin enlace desde la fila principal

## Consultar el esquema y las plantillas
Consultar `references/schema.md` para:
- propiedades recomendadas
- configuraciÃ³n sugerida de vistas
- template de pÃ¡gina
- payloads raw de ejemplo

