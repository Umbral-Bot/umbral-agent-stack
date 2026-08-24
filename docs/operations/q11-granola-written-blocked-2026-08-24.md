# Q11-T3 — Intento de `written>=1`: BLOQUEADO por el mismo 401 — 2026-08-24

Cierre de `PKG-MACRO-P5-Q11-T3`. T2 (#663) dejó la auditoría y el guard
anti-encogido; faltaba la escritura real. No ocurrió: **el token de Notion no
cambió desde T2**.

## El worker, identificado

No asumido — leído del proceso que escucha en el puerto.

| | |
|---|---|
| Puerto | `127.0.0.1:8088`, `/health` 200 |
| PID | 18504, **arrancado 2026-08-21 09:47** |
| Comando | `python.exe C:\GitHub\umbral-agent-stack-codex\scripts\vm\start_primary_worker.py` |

Ese bootstrap carga el entorno en dos pasos: `scripts/env_loader.load()` (el
`.env` de la raíz de ese clone) y `granola_watcher_env_loader.load_env()`
(`C:\Granola\.env`). Ambos usan `setdefault`, así que gana el primero que
defina la variable. `C:\Granola\.env` no define ninguna variable Notion, así
que la única fuente de `NOTION_API_KEY` para este worker es
`C:\GitHub\umbral-agent-stack-codex\.env`.

`worker/config.py:51` la lee **en import time**, no por request: cambiar el
archivo no basta, hay que reiniciar el proceso.

## Por qué sigue en 401

Tres hechos independientes, todos verificables sin abrir el archivo:

| Señal | Estado |
|---|---|
| `mtime` de `C:\GitHub\umbral-agent-stack-codex\.env` | **2026-03-27** — sin tocar |
| `.env*` modificados en los últimos 4 días (los tres clones + `C:\Granola`) | **ninguno** |
| Variables Windows `NOTION*` (User y Machine) | **ninguna** |
| PID del worker | **18504**, el mismo que en T2 — sin reinicio |
| Huella `sha256[:8]` de `NOTION_API_KEY` | `6c512bda` — **idéntica a la de T2** |

```
$ python probe_notion_keys.py     # imprime nombre + huella + status, nunca el valor
NOTION_API_KEY             origin=...-codex\.env  fp=6c512bda  len=50  status=401 unauthorized
NOTION_SUPERVISOR_API_KEY  origin=...-codex\.env  fp=261430c0  len=50  status=401 unauthorized
```

`401 unauthorized` contra `GET /v1/users/me` fija la capa: es **credencial**,
no permiso. Un token válido sin acceso a la DB devolvería 404 al consultarla,
no 401 en `users/me`.

## Corrida `--execute`: `written: 0`

```
$ python scripts/vm/granola_drive_feeder.py --execute --max-creates 10 --max-updates 1 \
    --exclude "Conecta 3 -USM.md" \
    --exclude "Lleve la IA al flujo de trabajo… y al flujo empresarial.md" \
    --exclude "Promueva el crecimiento con la productividad y seguridad basada en IA .md" \
    --exclude "Webinar Microsoft Transforme su pequeña o mediana empresa en una Frontier Firm.md"
{"drive_files": 118, "notion_pages": 134,
 "gap": {"create": 21, "update_transcript": 1, "skip": 96, "review_ambiguous": 0},
 "selected": 11, "deferred": 7, "excluded": 4, "unparsed_transcript": 0,
 "written": 0, "declined": 0, "failed": 11, "execute": true}
FAIL ...: dry-run failed: worker returned 500: Notion API error (401) ... "API token is invalid."
```

`selected: 11` = 10 `create` + 1 `update_transcript`, **los 11 VERBATIM**
(verificado con `granola_drive_transcript_audit.py --only`, uno por ítem).
`executed: 0`: los 11 mueren en el dry-run, ninguno llega a intentar escribir.

## La carpeta se movió durante la corrida

Entre el dry-run (16:54 UTC) y el `--execute` (16:57 UTC), Drive sincronizó
transcripciones nuevas: **108 → 118 archivos elegibles**, gap de 11 a 21
`create`. David estaba pegando en ese momento (mtimes 12:55–12:57 local).

Dos consecuencias que conviene tener presentes cuando el token se arregle:

1. **La selección es por orden de nombre de archivo, no por antigüedad.** Con
   21 creates y un cap de 10, cuáles entran depende del alfabeto. No hay
   pérdida — el resto queda en `deferred` y entra en la corrida siguiente —
   pero no leer el cap como "los 10 más viejos".
2. **Un archivo a medio sincronizar puede entrar.** Uno de los nuevos apareció
   con **0 bytes** y quedó fuera por `MIN_FILE_BYTES`, pero un pegado a mitad
   de camino con 20 KB pasaría el filtro. No es silencioso: `detect_truncation`
   lo marca y la página queda con `truncation_detected=true`.

De los 10 archivos nuevos, 3 son `VERBATIM_APLANADO` (webinars pegados sin
saltos de línea) y quedaron excluidos de la corrida junto a `Conecta 3 -USM.md`.

Auditoría de la carpeta al cierre (118 elegibles): 107 `VERBATIM`,
10 `VERBATIM_APLANADO`, 1 `SOLO_RESUMEN`.

## Scheduled Task: NO registrada

`UmbralGranolaDriveFeeder` sigue sin existir. Con `written: 0` sería agendar un
job que falla todos los días a las 08:30.

## Dos defectos que aparecieron al usar las herramientas

Ninguno de los dos se ve leyendo el código; los dos aparecieron ejecutándolo.

### `--only` partía por comas, y un nombre real tiene una

`BIM Forum - GT política, regulación y mandantes.md`. Al auditar los 11 ítems
seleccionados, el filtro devolvió **10** — y el JSON decía `count: 10` sin más
señal de que faltaba uno. Una herramienta cuyo trabajo entero es demostrar
completitud no puede reportar en silencio sobre menos de lo que le pidieron.

`--only` ahora es repetible (una bandera por archivo, sin split) y **aborta**
si algún nombre no matchea.

### Un `--exclude` mal escrito escribía el archivo que debía retener

`drop_excluded` era un filtro puro: un nombre que no matchea no hace nada. Eso
falla **abierto en la dirección de escritura** — el operador cree que el archivo
está retenido, la corrida lo escribe, y Notion cambia sin que nadie lo haya
decidido. La asimetría importa: el mismo typo en un filtro que sólo *selecciona*
no cuesta nada.

`unmatched_exclusions` + abort antes de cualquier llamada al worker. Lo cazó de
inmediato en esta misma sesión: mi lista de excludes venía de un archivo con
CRLF y los nombres llegaron con `\r` pegado. Por eso las exclusiones ahora se
normalizan con `strip()` — un `\r` pegado no es un typo, y el abort tiene que
dispararse con los typos de verdad.

El chequeo mira el **inventario de Drive**, no el batch. Contra el batch, el
`--exclude` permanente de la Scheduled Task fallaría todas las mañanas desde el
día en que el archivo retenido finalmente se ingiera y pase a `skip`.

## Desbloqueo

Acción de David, en una sola línea:

1. Poner un token de integración Notion válido como `NOTION_API_KEY` en
   `C:\GitHub\umbral-agent-stack-codex\.env`.
2. **Reiniciar el worker** (PID 18504) — la key se lee en import time.
3. Reintentar el comando de arriba.

Con `written>=1` recién corresponde registrar la Scheduled Task.
