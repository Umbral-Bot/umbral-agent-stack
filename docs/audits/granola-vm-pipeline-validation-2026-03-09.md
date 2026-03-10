# Granola VM Pipeline Validation — 2026-03-09

## Objetivo

Validar y dejar operativo el flujo base de Granola para David:

1. captura de una transcripción en la VM,
2. procesamiento vía Worker local,
3. escritura en la base de Notion de transcripciones,
4. comentario a `@Enlace` en OpenClaw,
5. propuesta de follow-up sin actuar en nombre de David sin autorización.

## Resumen ejecutivo

El flujo base quedó operativo en la VM sin usar PAD:

- `C:\Granola\exports` queda monitoreado por `GranolaWatcher`.
- El watcher corre contra el Worker local `http://127.0.0.1:8088`.
- Una transcripción de prueba fue creada en `exports`, procesada automáticamente, movida a `processed`, escrita en Notion y notificada a `@Enlace`.
- El proyecto de Linear `Proyecto Granola` existe y `UMB-52` quedó asociado al proyecto.
- Rick revalidó el estado y propuso correctamente un siguiente paso proactivo sin ejecutarlo.

## Qué hizo Rick

- Detectó el primer bloqueo real: faltaba `NOTION_GRANOLA_DB_ID` para el flujo automático.
- Validó la base de Notion y el comentario a `@Enlace` por bypass manual.
- Creó la issue `UMB-52`.
- Creó/actualizó el artefacto compartido:
  - `G:\Mi unidad\Rick-David\Proyecto-Granola\estado-real-pipeline-granola-v1.md`
- Revalidó al final el estado operativo del pipeline y propuso:
  - “hago un borrador de correo de seguimiento por ti?”

## Qué arreglé yo

### 1. Worker/Notion

- Añadí `NOTION_GRANOLA_DB_ID` al entorno de la VPS.
- Corregí `worker/notion_client.py` para que `create_transcript_page()` resuelva dinámicamente el schema real de la DB de Granola.
- El helper ya no depende de propiedades hardcodeadas `Name/Source/Date`.

### 2. Pipeline Granola

- Ajusté `worker/tasks/granola.py` para que la notificación vaya a la Control Room usando `add_comment(page_id=None, ...)`.
- El comentario ahora arranca con `Hola @Enlace, ...`, que era el convenio pedido por David.

### 3. Allowlist VM

- Extendí `config/tool_policy.yaml` para permitir inspección de:
  - `C:\Granola`
  - `C:\Users\rick\AppData\Roaming\Granola`

### 4. Watcher en VM

- Confirmé que el watcher no estaba instalado ni configurado.
- Creé:
  - `C:\Granola\`
  - `C:\Granola\exports\`
  - `C:\Granola\exports\processed\`
  - `C:\Granola\.env`
- Actualicé el servicio `openclaw-worker` de la VM para incluir:
  - `NOTION_API_KEY`
  - `NOTION_CONTROL_ROOM_PAGE_ID`
  - `NOTION_GRANOLA_DB_ID`
  - `NOTION_TASKS_DB_ID`
- Registré la tarea programada `GranolaWatcher`.
- Instalé `watchdog` para que el watcher corra en modo reactivo y no solo polling.

### 5. Hardening del watcher

- `scripts/vm/granola_watcher.py`
  - ahora asegura el repo root en `sys.path` para poder importarse bien cuando se ejecuta como script directo en Windows.
- `scripts/vm/granola_watcher_env_loader.py`
  - ahora lee `.env` con `utf-8-sig` para tolerar BOM UTF-8 generado por PowerShell.

## Validaciones ejecutadas

### A. VPS Worker directo

Se validó:

- `notion.write_transcript`
- `granola.process_transcript`
- `granola.create_followup` con:
  - `proposal`
  - `email_draft`

Resultados:

- se creó una página de transcripción en Notion,
- se creó una propuesta como subpágina de reporte,
- se generó un borrador de correo y se posteó como comentario en la transcripción,
- el intento de Gmail draft real quedó como dependencia de credenciales Gmail.

### B. VM Worker directo

Se validó:

- `GET /health` local en `127.0.0.1:8088`
- `granola.process_transcript` directo al Worker local

Resultado:

- el Worker local de la VM procesa y escribe en Notion con el entorno correcto.

### C. Watcher manual en VM

Prueba:

- se dejó `watcher-smoke.md` en `C:\Granola\exports`
- se ejecutó `granola_watcher.py --once`

Resultado:

- la página se creó en Notion,
- el comentario a `@Enlace` se envió,
- el archivo se movió a `processed`.

### D. Watcher en segundo plano vía tarea programada

Prueba:

- se arrancó `GranolaWatcher`,
- se dejó `granola-background-test.md` en `exports`,
- no se ejecutó el watcher manualmente,
- se esperó el procesamiento automático.

Resultado:

- la tarea quedó `Running`,
- el log mostró modo `Watchdog`,
- el archivo fue procesado y movido solo,
- la página se creó en Notion,
- la notificación a `@Enlace` se envió.

## Linear

Estado final verificado:

- Proyecto:
  - `Proyecto Granola`
  - `https://linear.app/umbral/project/proyecto-granola-6567006704df`
- Issue:
  - `UMB-52`
  - quedó asociada al proyecto correcto

## Artefactos relevantes

- Carpeta compartida:
  - `G:\Mi unidad\Rick-David\Proyecto-Granola\estado-real-pipeline-granola-v1.md`
- Carpeta VM:
  - `C:\Granola\exports\`
  - `C:\Granola\exports\processed\`
  - `C:\Granola\.env`
  - `C:\Granola\watcher.log`

## Tests locales

Comandos relevantes:

```bash
python -m pytest tests/test_granola.py tests/test_notion_transcript_page.py -q
python -m pytest tests/test_granola_watcher.py -q
```

Cobertura agregada:

- compatibilidad con schema real de la DB de transcripciones,
- comentario a `@Enlace`,
- tolerancia a `.env` con BOM UTF-8.

## Pendientes reales

### No bloqueantes para el flujo base

- `action_items_created` sigue en `0`:
  - el pipeline base funciona,
  - pero la sincronización automática de action items a la DB de tareas de Notion no quedó cerrada en esta iteración.
- algunos títulos/logs muestran problemas menores de codificación de acentos.

### Siguiente capa útil

1. cerrar el follow-up proactivo como propuesta, no ejecución:
   - correo,
   - presupuesto,
   - evento de calendario,
2. revisar el mapeo de la DB de tareas si se quiere reactivar `action_items_created`,
3. testear una transcripción más parecida a una reunión real de David.

## Veredicto

El objetivo principal del test quedó logrado:

- pipeline base operativo en VM,
- Notion operativo,
- comentario a `@Enlace` operativo,
- proyecto trazado en Linear,
- follow-up proactivo ya soportado al menos como propuesta/draft.
