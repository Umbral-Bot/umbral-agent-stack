# Q11-T1 — Feeder Drive→Notion recurrente (Granola) — 2026-08-23

Cierre de `PKG-MACRO-P5-Q11-T1`. Convierte el catch-up **one-shot** P1.1b
(#532/#533, 2026-07-16) en una **recurrencia** en esta máquina Windows.

Decisión de entrevista Q11 = A*: el feeder Drive gana sobre el reconteo fila 8
("ruta oficial API/MCP/CSV primero"). Aquí **no se usa la API ni el MCP de
Granola**: la fuente es la carpeta Drive donde David pega los transcripts.

## Por qué existía la brecha

Tres hechos que sólo juntos explican el silencio:

1. **P1.1b nunca fue recurrente.** 95 archivos, 13 lotes a mano, y los drivers
   por lote (`.tmp/loteN_driver.py`) nunca se commitearon. Al cerrarse, no
   quedó nada que volviera a correr.
2. **El `gap-check` del VPS (cron 08:00) mira Notion, no Drive.** Grita
   `STALE: Granola intake looks dead` — y tiene razón, pero por el motivo
   equivocado: no ve la carpeta, ve que no entra nada.
3. **El VPS no tiene `G:\`.** La carpeta sólo existe en este Windows. Por eso
   la recurrencia es una Scheduled Task local y **no** un cron nuevo en el VPS.

Resultado: desde 2026-07-16 David siguió pegando transcripts y **ninguno**
llegó a Notion.

## Inventario (2026-08-23)

Carpeta: `G:\Mi unidad\07_Sesiones y Transcripciones\Notas y Transcripciones\Granola`

| | |
|---|---|
| `.md` totales | 109 |
| Elegibles | 108 |
| Excluidos | 1 — `Comgrap - MCP.md` (0 bytes, `< MIN_FILE_BYTES`) |
| Sin fecha parseable | 0 |

Los 3 más nuevos (por fecha de reunión, no por `mtime` de sync):

| Fecha | Archivo |
|---|---|
| 2026-08-06 | `Conecta 3 -USM.md` |
| 2026-08-05 | `konstruedu - Ajuste acuerdos.md` |
| 2026-08-04 | `MPS session - Umbralbilm - TrackingID#2606180040004341.md` |

## Gap-check Drive→Notion (dry-run, cero escrituras)

Snapshot Notion en vivo: **134 páginas**, `has_more=false`. De ellas 95 con
`Fuente=granola_drive_md` — exactamente las 95 de P1.1b, confirmando que no
entró nada nuevo desde entonces.

```
{"create": 11, "update_transcript": 1, "skip": 96, "review_ambiguous": 0}
```

**11 create** — todo el backlog posterior a P1.1b, del 2026-07-17 al 2026-08-06:
`BIM Forum - GT política, regulación y mandantes`, `Konstruedu - Rolando Cedeño`,
`Propuesta David - Agente Copilot`, `Reunión Post konstruedu con Rolando`,
`Konstruedu - Rafael`, `Revisión MCP`, `Rendair`,
`BIM Forum MT Estandar BIM para proyectos Publicos`, `MPS session - Umbralbilm`,
`konstruedu - Ajuste acuerdos`, `Conecta 3 -USM`.

**1 update_transcript** — `BIM Forum - Automatización` (2026-07-13). Es
literalmente el pendiente que el cierre P1.1b dejó anotado: *"sin `.md` en Drive
aún"*. David lo depositó después. La página existe con `Fuente=granola_mcp` y
sólo 3.600 caracteres (resumen AI); el archivo trae 29.877 verbatim.

**96 skip** — 94 ya ingeridos y sin cambios + 2 que este pack rescató de un
falso positivo (abajo).

### Hallazgo: renombres en Drive reaparecían como update en cada corrida

Dos archivos clasificaban `update_transcript` sin tener nada que actualizar:

- `Copilot 365 - WPS - Susana Millan.md` — es el mismo archivo ya ingerido como
  `Copilot_365_WPS_Susana_Millan.md`, renombrado.
- `Sesión de seguimiento WSP (2).md` — copia `(2)` de uno ya ingerido.

Al cambiar el nombre cambia `shared_folder_path`, así que los tiers 1/2 (ruta +
sha1 juntos) dejan de reconocerlos para siempre y caen a título+fecha, que sólo
sabe decir "actualizá". En un one-shot eso costaba dos ítems de más; en un feeder
diario reaparecen **todos los días**.

Tier nuevo, `sha1_different_path`: **mismos bytes bajo otra ruta → `skip`**. El
`sha1` es el del texto del archivo, que un renombre no cambia, así que identifica
el caso de forma exacta — sin ventana de tolerancia y sin depender de ninguna
propiedad de display. Una página escrita desde otra fuente (un resumen AI) no
tiene `sha1`, así que este tier no puede saltearla nunca.

> **Corrección sobre el costo.** La primera versión de este pack usaba
> `Longitud Notion` como proxy de identidad y justificaba el tier diciendo que
> sin él se reescribirían "cientos de bloques por día". Eso era falso:
> `compare_metrics` devuelve `identical_hash_and_char_count` y
> `decide_reconciliation` resuelve `noop` antes de tocar un solo bloque
> (`worker/tasks/granola_finality.py`). El costo real es más chico y más
> aburrido — dos round-trips desperdiciados por día y un reporte de gap que
> miente sobre cuánto falta. El tier sigue valiendo la pena por eso, no por el
> daño que yo había afirmado.

## Recurrencia

`scripts/vm/granola_drive_feeder.py` encadena los scripts que ya existían
(no los reimplementa) y agrega lo que un one-shot no necesitaba:

1. **Dry-run por defecto.** `--execute` es la única forma de escribir.
2. **Confirmación por ítem antes de cada escritura.** Cada payload va primero
   como `dry_run`; sólo se escribe si el veredicto del worker coincide con
   nuestra clasificación. Un `create` que el worker dice que ya existe no se
   escribe. Es la guarda que P1.1b introdujo a mano en el lote 10, hecha
   estructural.
3. **Trabajo acotado.** `--max-creates` / `--max-updates` (10 por defecto). El
   resto queda **listado** en el reporte de la corrida, no descartado en silencio.

Registro de la tarea: `scripts/vm/register_granola_drive_feeder_task.ps1`
(diaria, `-Execute` opcional, credenciales nunca escritas en la definición).

```bash
python scripts/vm/granola_drive_feeder.py
```

Pieza nueva necesaria: `scripts/vm/granola_notion_raw_snapshot.py`. El gap-check
siempre necesitó un snapshot de Notion y P1.1b lo armaba a mano por lote. Pagina
la DB entera (obligatorio: cruzó 100 páginas durante P1.1b) y delega el parseo
de cada página a `worker/tasks/granola.py::_build_existing_raw_candidate`, la
misma función que el worker usa al ejecutar — así la pre-clasificación no puede
discrepar en silencio con la autoridad.

## Corrida `--execute` acotada: BLOQUEADA

No se escribió nada. **El token de integración Notion del worker es inválido.**

```
$ python scripts/vm/granola_drive_feeder.py --execute --max-creates 1 --max-updates 0
{"drive_files": 108, "notion_pages": 134, "gap": {...}, "selected": 1,
 "deferred": 11, "written": 0, "failed": 1, "execute": true}
FAIL Granola/BIM Forum - GT política, regulación y mandantes.md: dry-run failed:
worker returned 500 for granola.process_transcript: {"detail":"Task failed:
Notion API error (401) during read_database metadata: ... API token is invalid."}
```

Alcance verificado del bloqueo:

| Superficie | Estado |
|---|---|
| Worker `127.0.0.1:8088` | vivo (`/health` 200, `ping` 200) |
| Worker → Notion | **401 `API token is invalid`** (falla incluso el dry-run) |
| `NOTION_API_KEY` en `.env` (coordinador y codex) | 401 |
| `NOTION_SUPERVISOR_API_KEY` | 401 |
| Variables de entorno Windows (User/Machine) | ninguna seteada |
| `WORKER_URL_VM` / `..._INTERACTIVE` (100.109.16.40) | ConnectTimeout; Tailscale caído |
| Worker VPS | escucha en su propio `127.0.0.1`, no alcanzable desde Windows |

El MCP `notion-api` **sí** está autenticado — por eso el snapshot de 134 páginas
es real y en vivo. Pero es un OAuth de sesión, no un token de integración: no
sirve para que el worker escriba, y escribir por el MCP saltearía
`granola.process_transcript` y toda su lógica de dedup/finality. No se hizo.

**Desbloqueo (acción de David):** cargar un token de integración Notion válido
en el env del worker (`NOTION_API_KEY`) y el id de la DB
(`NOTION_GRANOLA_DB_ID`, ver `.env.example`). Con eso, el comando de arriba
corre tal cual.

`written: 0` con `execute: true` es la propiedad de seguridad funcionando: la
confirmación previa falló, así que no hubo escritura.

## Cero capitalización

Ningún payload activa capitalización: `notify_enlace=False`,
`allow_legacy_raw_task_writes=False`, y el worker escribe
`Procesar con agente=False`. No se tocó HITL-2, ni flags stage8/9, ni n8n, ni
`openclaw.json`, ni crons del VPS. Promover un raw a tarea/proyecto/publicación
sigue siendo una decisión humana aparte
(`docs/54-granola-capitalize-raw-slice.md`, skill `notion-governance-runtime`).

## Cambios de código

| Archivo | Cambio |
|---|---|
| `scripts/vm/granola_drive_feeder.py` | **nuevo** — orquestador recurrente |
| `scripts/vm/granola_notion_raw_snapshot.py` | **nuevo** — snapshot paginado de la DB raw |
| `scripts/vm/register_granola_drive_feeder_task.ps1` | **nuevo** — registro de la Scheduled Task |
| `scripts/list_granola_drive_ingest_gap.py` | tier `sha1_different_path` |
| `scripts/vm/granola_drive_md_ingest.py` | `--output` (UTF-8) + `resolve_meeting_date()` + prefijo de ruta derivado de la carpeta |
| `scripts/vm/send_granola_drive_batch.py` | `post_task` conserva el body del error |

`--output` no es cosmético: el dump a stdout revienta en Windows
(`UnicodeEncodeError`, cp1252) apenas un transcript trae un emoji — con 108
archivos reales, revienta. Una corrida agendada moría ahí. El feeder además
fuerza UTF-8 en sus propios `stdout`/`stderr`, porque sus líneas de FAIL
imprimen nombres de archivo acentuados.

### Lo que encontró el `/code-review`

Siete ángulos en paralelo sobre el diff. Lo que cambió a raíz de eso:

| Hallazgo | Corrección |
|---|---|
| `DEFAULT_YEAR = 2026` hardcodeado en un job **recurrente** | En enero 2027 estamparía 2026 en cada transcript, y título+fecha resolvería a la reunión del año pasado: sobreescritura, no alta. Ahora `resolve_meeting_date()` deriva el año del mtime del archivo, con rollback para reuniones de diciembre pegadas en enero |
| El tier usaba longitud como proxy de identidad | Reemplazado por `sha1` exacto (arriba). Elimina de paso la dependencia de `Longitud Notion`, que el worker escribe como `number` **o** `rich_text` y bajo tres nombres distintos — cualquiera de esas variantes desactivaba el tier en silencio |
| El tier no miraba `fuente` | Una página `granola_mcp` de longitud parecida quedaba `skip` para siempre y perdía el transcript. Con `sha1` no puede pasar: esas páginas no tienen `sha1` |
| Import top-level rompió el CLI del gap-check | `python scripts/list_granola_drive_ingest_gap.py` moría con `ModuleNotFoundError`. El tier `sha1` no necesita ese import; el CLI volvió a andar |
| La guarda fallaba **abierta** en `create` | `bool(result.get("matched_existing"))` leía "el worker no contestó" como "confirmado, no existe". Ahora una clave ausente es desacuerdo |
| La guarda no miraba **qué** página emparejó el worker | Su ladder es más ancha que la del gap-check; podían resolver páginas distintas y el execute sobreescribía una que nadie eligió |
| No se verificaba que el dry-run **fuera** dry-run | Si el worker no confirma `dry_run=true`, el POST #1 pudo ser una escritura y el #2 sería la segunda |
| `main()` sin manejo de errores | `G:\` sin montar al arrancar dejaba traceback y **cero** reporte. Ahora siempre queda un `run-*.json`, y el reporte se flushea después de cada ítem |
| Snapshot vacío = "creá todo" | Un snapshot vacío o con la forma equivocada ahora aborta |
| Transcript que no parsea | Si Granola cambia la etiqueta `Transcript:`, un `.md` grande parsea a vacío y el update reemplazaría la página por 76 caracteres. Se excluye y se reporta |
| Cap negativo = ilimitado | `--max-creates -1` habilitaba un drenaje completo desatendido. Se clampea |
| Exit 1 por una guarda que funcionó | Un ítem "declined" ponía la tarea en rojo todos los días. Ahora sólo los errores reales fallan la corrida |
| `written` contaba POSTs, no escrituras | Ahora excluye `noop`/`defer` |
| Prefijo `Granola/` hardcodeado | Con `--root` apuntando a una copia, las claves de dedup colisionaban con las de producción. Se deriva del nombre de la carpeta |
| `.ps1`: `-EnvFile` documentado pero inexistente | Eliminado; se documenta el mecanismo real y por qué `LogonType Interactive` es obligatorio (Drive monta `G:\` por sesión interactiva) |
| `.ps1`: `-At '08:30'` + `-StartWhenAvailable` | Registrar a las 3pm disparaba una corrida `--execute` desatendida a los minutos. Ahora se ancla a la próxima ocurrencia |
| Bodies de error a disco sin redactar | `_redact()` enmascara bearer tokens antes de que un error llegue al reporte o a la terminal |

Tests: 87 nuevos (`tests/test_granola_drive_feeder.py`,
`tests/test_granola_notion_raw_snapshot.py`, más los agregados a ingest / gap /
sender).

## Pendiente

- **Token Notion del worker** — único bloqueo de la corrida `--execute`.
- **11 create + 1 update** esperando ese desbloqueo.
- **Registrar la Scheduled Task** — el `.ps1` está versionado pero no se
  registró en esta máquina: registrar una tarea que hoy fallaría todos los días
  sólo generaría ruido. Registrar después del desbloqueo.
