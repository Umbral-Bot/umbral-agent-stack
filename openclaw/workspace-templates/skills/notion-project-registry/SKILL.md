---

name: notion-project-registry

description: diseñar y mantener un registro maestro de proyectos en notion con vistas

  de tabla, kanban y timeline, enlazado a drive/gdrive, linear y entregables. usar

  cuando chatgpt necesite crear, migrar, auditar o actualizar una base de datos de

  proyectos; normalizar propiedades, estados y reglas de seguimiento; crear o actualizar

  registros de proyecto; dejar updates cronológicos; reflejar bloqueos o issues sin

  respuesta; o trabajar con tools de notion de bajo nivel y payloads raw sobre database/data

  source, page properties y blocks.

metadata:

  openclaw:

    always: true

    emoji: ??

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

2. Consultar `references/schema.md` y alinear el esquema antes de tocar páginas sueltas.

3. Usar el registro maestro como fuente única del estado cross-tool:

   - notion = vista de portfolio y dashboard;

   - linear = ejecución detallada e issues;

   - drive = archivos y entregables.

4. Crear o actualizar la fila del proyecto antes de editar documentos sueltos o dejar notas dispersas.

4.1. Si el output resultante es algo que David debe revisar (benchmark, reporte, borrador, pieza editorial, criterio, plan), no dejarlo como pagina suelta en Control Room:
   - primero actualizar la fila del proyecto;
   - luego crear o actualizar un registro en la base de entregables/revision;
   - y si tambien se registra una tarea operativa, enlazarla al `Proyecto` y al `Entregable` cuando la tool lo permita;
   - usar Control Room solo para coordinacion transversal o alertas.
   - si la tool acepta `icon`, usar el campo `icon` en vez de prefijar el `Nombre` con emojis.
   - para proyectos, tareas y entregables ligados al mismo proyecto, mantener un icono consistente para lectura rapida, salvo que haya una razon clara para diferenciarlo.
   - los entregables deben tener nombre natural en español y sin fecha en el título.
   - la fecha y la fecha limite sugerida deben vivir en columnas, no incrustadas en el nombre.
   - las filas creadas no deben quedar vacías por dentro: la pagina del proyecto, tarea o entregable debe tener cuerpo útil para revisión humana.

5. Mantener una página por proyecto con propiedades + cuerpo estructurado:

   - `links operativos`

   - `updates`

   - `handoff`

6. Revisar vistas y controles de calidad al final.



## Elegir el esquema correcto

- Preferir el esquema `api-stable` de `references/schema.md` cuando haya que trabajar con tools de bajo nivel o payloads raw.

- Preferir `select` para `Estado` por compatibilidad API. Solo reutilizar una propiedad `status` existente si ya está creada y no hay que mutar su esquema.

- Preferir `title`, `select`, `rich_text`, `multi_select`, `url` y `date` para campos operativos.

- Usar `people` o `relation` solo cuando el tool pueda resolver ids de usuarios o páginas de forma confiable.

- Usar ids de propiedad cuando el tool los exponga. No depender de nombres de columna si puede haber renombres.

- No usar el body de la page como sustituto del registro maestro; usarlo solo para historial, links secundarios y handoff.
- Aun así, no dejar cuerpos vacíos: cada página debe abrir con al menos resumen operativo, contexto y siguiente acción legible.



## Crear un registro nuevo o adaptar uno existente

### Crear desde cero

1. Crear el database container o data source.

2. Crear las propiedades canónicas del esquema.

3. Crear una plantilla de página con las secciones:

   - `links operativos`

   - `updates`

   - `handoff`

4. Crear las vistas recomendadas en la ui de notion. No asumir que la api puede gestionar vistas.

5. Cargar los primeros proyectos solo después de confirmar estados canónicos.



### Adaptar una base existente

1. Mapear propiedades existentes a las canónicas antes de crear columnas nuevas.

2. Renombrar o reutilizar columnas equivalentes; evitar duplicados como `owner`, `pm`, `responsable`.

3. Mantener una sola columna de estado canónica.

4. Rellenar huecos mínimos:

   - `Drive`

   - `Linear`

   - `Fecha objetivo`

   - `Ultimo update`

5. Marcar filas incompletas como deuda operativa en `Bloqueos` o `Issues abiertas o sin respuesta`, no como estado ambiguo.



## Crear o actualizar un proyecto

Al aparecer un proyecto nuevo:

1. Crear la fila el mismo día con el mínimo obligatorio:

   - `Proyecto`

   - `Estado`

   - `Responsable`

   - `Fecha inicio` o `Fecha objetivo` si existe

   - `Drive` y `Linear` si ya existen

2. Si algún link canónico aún no existe, dejar el campo vacío temporalmente y dejar constancia en el primer update.

3. Completar el resto de propiedades antes del siguiente corte semanal.

4. Crear o actualizar la página del proyecto con el template base.

5. Evitar crear una página suelta sin fila en el registro.



Al actualizar un proyecto existente:

1. Cambiar primero propiedades canónicas.

2. Luego añadir un update cronológico en el cuerpo de la página.

3. Si cambian links, reemplazar el link canónico en la propiedad correspondiente y registrar el cambio en el update.

4. Si cambia el milestone o aparece un bloqueo, actualizar también `Siguiente hito`, `Bloqueos`, `Issues abiertas o sin respuesta` y `Ultimo update`.



## Enlazar drive, linear y entregables

- Guardar un único link canónico de carpeta compartida en `Drive`.

- Guardar un único link canónico del proyecto en `Linear`.

- Guardar links secundarios, specs, entregables y docs en `Links relevantes` y/o en la sección `links operativos` del cuerpo.

- Tratar notion como índice maestro, no como espejo completo de linear o drive.

- No copiar todos los issues de linear. Resumir solo los abiertos o sin respuesta que afectan seguimiento.

- Mantener nombres consistentes entre notion, drive y linear cuando sea posible.

- Si no existe proyecto de linear todavía, dejar `Linear` vacío y explicitar `sin proyecto linear` en el último update. No inventar placeholders.



## Crear vistas útiles

Crear estas vistas mínimas en la ui de notion:

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

   - filtrar proyectos con `Bloqueos` no vacío o `Issues abiertas o sin respuesta` no vacío

   - opcional: incluir proyectos cuyo `Ultimo update` esté desactualizado



Crear una vista mínima de backlog solo si el equipo separa intake de proyectos activos. No usar backlog como sustituto del kanban principal.



## Dejar updates cronológicos

Mantener `Ultimo update` como fecha del update más reciente.

Añadir cada update nuevo al final de la sección `updates` de la página del proyecto, con fecha visible y formato mínimo.



Usar este formato mínimo:

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

- `en espera`: dejar al menos un update breve en cada revisión semanal indicando si sigue igual y qué dispara la reactivación.

- `cerrado`: dejar un update final de cierre y completar `Notas de handoff`.



## Reflejar bloqueos e issues sin respuesta

- Escribir bloqueos en términos accionables: qué bloquea, quién lo destraba y cuál es la siguiente acción.

- Escribir issues sin respuesta como lista corta y priorizada, con id o link si existe.

- No dejar `bloqueado` con `Bloqueos` vacío.

- No dejar `Issues abiertas o sin respuesta` lleno si el proyecto ya no requiere atención; limpiarlo cuando quede resuelto.

- Si el proyecto está `en espera` por decisión estratégica y no por dependencia, explicar el gatillo de reanudación en el update y no marcarlo como `bloqueado`.



## Distinguir estados sin ambigüedad

Usar estas definiciones:

- `activo`: el proyecto se está moviendo y existe una siguiente acción concreta.

- `bloqueado`: el proyecto no puede avanzar por una dependencia externa o decisión pendiente.

- `en espera`: el proyecto está pausado de forma intencional; no se espera movimiento hasta que ocurra un gatillo de reanudación.

- `cerrado`: el proyecto terminó o se canceló y ya no necesita seguimiento operativo semanal.



No inventar estados ambiguos como `moving`, `ok`, `pending`, `paused?`, `almost done`.



## Aplicar higiene semanal

En cada corte semanal:

1. Revisar todos los proyectos no `cerrado`.

2. Actualizar `Ultimo update`.

3. Confirmar que `Siguiente hito` tenga dueño o fecha.

4. Confirmar que `Drive` y `Linear` apunten a la ubicación canónica actual.

5. Limpiar `Bloqueos` e `Issues abiertas o sin respuesta` resueltos.

6. Mover a `cerrado` proyectos terminados y dejar handoff.

7. Detectar anti-patrones antes de cerrar la revisión.



## Corregir anti-patrones

Corregir de inmediato:

- páginas sueltas sin registro maestro

- filas duplicadas para el mismo proyecto

- links faltantes o rotos en drive o linear

- estado ambiguo o desactualizado

- updates en slack o comentarios que nunca llegan a notion

- `Ultimo update` viejo con un body muy reciente o viceversa

- handoff disperso en docs separados sin enlace desde la fila principal



## Consultar el esquema y las plantillas

Consultar `references/schema.md` para:

- propiedades recomendadas

- configuración sugerida de vistas

- template de página

- payloads raw de ejemplo



