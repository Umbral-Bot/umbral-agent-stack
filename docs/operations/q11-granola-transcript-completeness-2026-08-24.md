# Q11-T2 — ¿Entra la transcripción completa o el resumen? — 2026-08-24

Cierre de `PKG-MACRO-P5-Q11-T2`. Q11-T1 (#662) demostró **que** los archivos de
Drive llegan a Notion. Este pack demuestra **qué** llega: que el cuerpo que el
parser entrega a `granola.process_transcript` es la transcripción verbatim y no
el resumen AI de Granola.

La pregunta no es retórica. Los dos viven en la misma carpeta y con la misma
forma: Granola sabe copiar cualquiera de los dos, y
`parse_drive_transcript_md` toma lo que venga después de `Transcript:` sin
preguntar qué es.

## Auditoría de completitud (cero escrituras)

Herramienta nueva: `scripts/vm/granola_drive_transcript_audit.py` — read-only,
sin red, imprime **solo métricas**. Nunca emite contenido de reuniones, ni un
extracto: su salida está pensada para pegarse en un acta.

```bash
python scripts/vm/granola_drive_transcript_audit.py
```

### Los 12 ítems del gap

Gap re-derivado en vivo el 2026-08-24 contra la DB canónica (134 páginas,
`has_more=false`, 95 con `Fuente=granola_drive_md`): `{"create": 11,
"update_transcript": 1, "skip": 96, "review_ambiguous": 0}` — idéntico al de
T1, sin archivos nuevos en Drive desde entonces.

| # | Acción | Archivo | `Transcript:` | Me: | Them: | Turnos | Chars cuerpo | Bytes archivo | Ratio | Clase |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `update_transcript` | `BIM Forum - Automatización.md` | Y | 39 | 39 | 78 | 29 877 | 30 811 | 0.997 | **VERBATIM** |
| 2 | `create` | `BIM Forum - GT política, regulación y mandantes.md` | Y | 32 | 33 | 65 | 22 402 | 23 187 | 0.994 | **VERBATIM** |
| 3 | `create` | `BIM Forum MT Estandar BIM para proyectos Publicos.md` | Y | 6 | 6 | 12 | 30 828 | 31 708 | 0.996 | **VERBATIM** |
| 4 | `create` | `Conecta 3 -USM.md` | Y | 1 | 1 | 2 | 73 320 | 74 724 | 0.999 | **VERBATIM_APLANADO** |
| 5 | `create` | `konstruedu - Ajuste acuerdos.md` | Y | 109 | 110 | 219 | 31 618 | 32 659 | 0.997 | **VERBATIM** |
| 6 | `create` | `Konstruedu - Rafael.md` | Y | 28 | 28 | 56 | 29 548 | 30 358 | 0.997 | **VERBATIM** |
| 7 | `create` | `Konstruedu - Rolando Cedeño.md` | Y | 13 | 14 | 27 | 23 635 | 24 285 | 0.996 | **VERBATIM** |
| 8 | `create` | `MPS session - Umbralbilm - TrackingID#2606180040004341.md` | Y | 159 | 159 | 318 | 19 428 | 20 445 | 0.990 | **VERBATIM** |
| 9 | `create` | `Propuesta David - Agente Copilot.md` | Y | 467 | 466 | 933 | 65 793 | 68 203 | 0.998 | **VERBATIM** |
| 10 | `create` | `Rendair.md` | Y | 26 | 26 | 52 | 2 154 | 2 341 | 0.962 | **VERBATIM** |
| 11 | `create` | `Reunión Post konstruedu con Rolando.md` | Y | 78 | 79 | 157 | 17 081 | 17 776 | 0.993 | **VERBATIM** |
| 12 | `create` | `Revisión MCP.md` | Y | 186 | 185 | 371 | 25 257 | 26 530 | 0.996 | **VERBATIM** |

**11 de 12 son VERBATIM.** Los 12 traen encabezado `Transcript:`, ninguno está
vacío, y el ratio cuerpo/archivo va de 0.962 a 0.999 — es decir, prácticamente
todo el archivo cruza a Notion; no hay un bloque de resumen quedándose afuera.

### El único que no: `Conecta 3 -USM.md`

73 320 caracteres en **dos líneas**, una de ellas de 73 123. Un solo `Me:` y un
solo `Them:` en todo el cuerpo.

No es un resumen: 73 k caracteres son ~12 000 palabras, un orden de magnitud por
encima de cualquier resumen AI de Granola (la página `granola_mcp` de `BIM Forum
- Automatización`, por comparación, tiene 3 600). Lo que pasó es que el pegado
**perdió los saltos de línea** y todos los turnos quedaron concatenados en una
sola línea.

Contenido completo, forma degradada. Por eso la clase es `VERBATIM_APLANADO` y
no `SOLO_RESUMEN`: llamarlo resumen y descartarlo tiraría una reunión entera.
Aun así **queda fuera de la corrida** — la regla del paquete pide "varios
turnos", y este no los tiene de forma verificable. Se ejecuta cuando David
confirme (o repegue el archivo con sus saltos de línea).

### La carpeta entera (108 elegibles)

| Clase | N |
|---|---|
| `VERBATIM` | 100 |
| `VERBATIM_APLANADO` | 7 |
| `SOLO_RESUMEN` | 1 |

Los 7 aplanados son el mismo fenómeno que `Conecta 3`: cuerpos de 13 k a 85 k
caracteres en 1–5 líneas, **cero bullets y cero headers markdown** — o sea, sin
ninguno de los marcadores que Granola pone en sus resúmenes. Seis de los siete
ya están ingeridos (`skip`), así que no hay acción pendiente sobre ellos.

El único `SOLO_RESUMEN` es `BIM Forum 3.md`: 1 163 caracteres, 2 turnos. Ya
está en Notion como `skip` y no se toca en este pack.

**Conclusión de la auditoría: ningún archivo de la carpeta es un resumen AI
disfrazado de transcripción.** Lo que el parser manda a Notion es el cuerpo
verbatim.

## El hueco que la auditoría sí destapó

El parser no traga resúmenes. Pero **nada impedía que un cuerpo más corto
pisara una transcripción completa**, que es la misma pérdida por otra puerta:

- `replace_blocks_in_page` borra *todos* los bloques existentes antes de
  escribir los nuevos.
- `decide_reconciliation` lee cualquier diferencia de métricas como
  `reconcile` — más corto y más largo por igual.
- La única guarda del feeder, `drop_unparsed_transcripts`, sólo rechaza
  `char_count == 0`.

Un `.md` cuyo cuerpo tras `Transcript:` fuera un resumen (o un pegado que se
cortó a la mitad), clasificado `update_transcript`, reemplazaba la página
completa por el texto corto. Sin aviso, y sin que ninguna capa de abajo
objetara.

### `transcript_shrink_reason` — el feeder se niega a encoger

Nuevo guard en `scripts/vm/granola_drive_feeder.py`. El dry-run que el feeder
**ya hacía** antes de cada escritura devuelve `reconciliation.previous_metrics`
y `reconciliation.new_metrics`; el guard compara los dos `char_count` y declina
si el entrante queda por debajo del 90 % del existente. No cuesta un
round-trip extra.

- Un `create` nunca se bloquea: no hay nada que sobreescribir.
- Métricas ausentes son **rechazo**, no permiso. Leer un `previous_metrics`
  faltante como "no había nada" fallaría abierto justo en la dirección que
  pierde la transcripción.
- `previous == 0` sí pasa: no hay nada que perder.
- `--allow-shrink` deja al operador forzarlo para una corrida concreta.

El único update del backlog lo cruza sin problema: 3 600 → 29 877 caracteres.

### Por qué el guard mira tamaño y no turnos

La tentación era rechazar todo lo que no tenga estructura `Me:`/`Them:`. Los
datos dicen que no: **7 de 108 archivos reales están aplanados**, uno de ellos
de 84 843 caracteres en una sola línea. Un filtro por turnos los rechazaría a
los siete. El tamaño contra lo que ya está en Notion no tiene ese falso
positivo — y es exactamente la magnitud que importa cuando lo que está en juego
es perder contenido.

### `--exclude`, para correr sólo lo que la auditoría aprobó

El feeder no tenía forma de retener un ítem puntual. `--exclude` (repetible,
acepta el nombre suelto o la ruta `Granola/<nombre>`) lo agrega, y el ítem
queda **listado** en el reporte de la corrida, no descartado en silencio.

Es un flag y no un guard a propósito: bloquear de oficio todo lo no-prístino
significaría que una reunión real nunca llega a Notion. La decisión es de una
corrida, no una propiedad permanente del archivo.

De paso, los filtros (`drop_unparsed_transcripts`, `drop_excluded`) pasaron a
correr **antes** de los caps. Capear primero dejaba que un ítem retenido
consumiera uno de los diez cupos de creación del día y empujara una
transcripción buena a mañana.

## Corrida `--execute` acotada: BLOQUEADA (401), `written: 0`

```
$ python scripts/vm/granola_drive_feeder.py --execute --max-creates 10 \
    --max-updates 1 --exclude "Conecta 3 -USM.md"
{"drive_files": 108, "notion_pages": 134,
 "gap": {"create": 11, "update_transcript": 1, "skip": 96, "review_ambiguous": 0},
 "selected": 11, "deferred": 0, "excluded": 1, "unparsed_transcript": 0,
 "written": 0, "declined": 0, "failed": 11, "execute": true}
FAIL Granola/BIM Forum - Automatización.md: dry-run failed: worker returned 500
for granola.process_transcript: {"detail":"Task failed: Notion API error (401)
during read_database metadata: ... API token is invalid."}
```

Los 11 ítems VERBATIM fallan en el **dry-run**, así que ninguno llega siquiera
a intentar una escritura. `written: 0` con `execute: true` es la propiedad de
seguridad funcionando, igual que en T1.

T1 había probado el bloqueo con un solo ítem; acá se confirma sobre los 11.

### Alcance del bloqueo (verificado 2026-08-24)

| Superficie | Estado |
|---|---|
| Worker `127.0.0.1:8088` | vivo — `/health` 200 |
| Worker → Notion | **401 `API token is invalid`** en los 11 ítems |
| `NOTION_API_KEY` (env del worker) | 401 contra `/v1/users/me` |
| `NOTION_SUPERVISOR_API_KEY` | 401 contra `/v1/users/me` |
| Variables de entorno Windows (User/Machine) | ninguna Notion seteada |
| MCP `notion-api` | autenticado, pero es OAuth de sesión, no token de integración |

Las dos keys se probaron contra `GET /v1/users/me` con un script que imprime
sólo nombre de variable, huella `sha256[:8]` y status HTTP — nunca el valor.

El snapshot de 134 páginas de esta auditoría se leyó por el MCP `notion-api`
(read-only). Ese OAuth **no** sirve para que el worker escriba, y escribir por
MCP saltearía `granola.process_transcript` y toda su lógica de dedup/finality.
No se hizo.

**Desbloqueo (acción de David):** cargar un token de integración Notion válido
como `NOTION_API_KEY` en el env del worker y reiniciarlo. Con eso el comando de
arriba corre tal cual.

## Scheduled Task: NO registrada

`UmbralGranolaDriveFeeder` sigue sin existir (`Get-ScheduledTask` sólo devuelve
`GranolaVmRawIntake*`, de otro pipeline). Registrarla con `written: 0` sería
agendar un job que falla todos los días a las 08:30.

## Cero capitalización

Nada de este pack activa capitalización: `notify_enlace=False`,
`allow_legacy_raw_task_writes=False`, `Procesar con agente=False`. No se tocó
HITL-2, ni flags stage8/9, ni n8n, ni `openclaw.json`, ni crons del VPS. Cero
API de Granola: la fuente es la carpeta de Drive.

## Cambios de código

| Archivo | Cambio |
|---|---|
| `scripts/vm/granola_drive_transcript_audit.py` | **nuevo** — auditoría de completitud read-only, sólo métricas |
| `scripts/vm/granola_drive_feeder.py` | guard `transcript_shrink_reason` + `--allow-shrink` + `--exclude` + filtros antes de los caps |
| `tests/test_granola_drive_transcript_audit.py` | **nuevo** — 22 tests |
| `tests/test_granola_drive_feeder.py` | +22 tests (shrink guard, `--exclude`, orden filtro/cap) |

```
$ python -m pytest tests/ -q -k granola
426 passed
```
