# YouTube coverage diagnosis — 2026-05-08

**Author**: copilot-vps (sesión Claude Opus 4.7)
**Branch**: `copilot-vps/033-youtube-coverage-handle-parser-hardening`
**SQLite**: `~/.cache/rick-discovery/state.sqlite`
**Notion DB Referentes** (data_source): `afc8d960-086c-4878-b562-7511dd02ff76`
**Parser auditado**: `scripts/discovery/stage2_ingest.py::parse_youtube_channel_id`

## TL;DR

- **Cobertura actual**: 13/26 (50%) — 13 OK, 13 `sin_acceso`.
- **Causa de los 13 `sin_acceso`**: **100% gap de data entry en Notion** (columna
  `YouTube channel` vacía). 0 son bugs del parser.
- **Cobertura post-fix posible sin acción de David**: **13/26** (sin cambio).
  El hardening de código no puede recuperar items que no tienen URL en Notion.
- **Cobertura post-fix con acción de David** (rellenar 13 columnas): hasta
  **26/26 (100%)**, asumiendo que las URLs sean válidas.

## Repo dice X / VPS muestra Y (premisa de la consigna)

| Premisa de la consigna | Realidad VPS auditada |
|---|---|
| Parser falla por formatos no-URL (handle, /c/, /user/, channel_id) | **0 referentes** failing tienen URL no-estándar; **13/13** failing tienen `youtube_url=null` |
| Solución: hardening parser + tests + retry → ≥85% cobertura | Hardening parser **no recupera nada** (no hay URLs que parsear). La cobertura sólo subirá cuando David complete las 13 columnas vacías |
| Bucket (b) URL válida + parser falla | **0 casos** |
| Bucket (c) URL OK + API rechaza | **0 casos** |
| Bucket (d) Formato no-URL | **0 casos** |
| Bucket (a) NULL/vacío en Notion | **13/13 casos** |

## Estado actual SQLite (`fetch_log` last per referente)

```sql
SELECT status, COUNT(*) FROM (
  SELECT f.status FROM fetch_log f
  INNER JOIN (SELECT referente_id, MAX(id) as max_id
              FROM fetch_log WHERE canal='youtube'
              GROUP BY referente_id) m ON f.id = m.max_id
) GROUP BY status;
-- ok          13
-- sin_acceso  13
```

Todos los 13 `sin_acceso` tienen `error=''` (vacío) en `fetch_log`. Esto es
intencional en `process_channel()`: cuando `fetch_url is None` (ref.youtube_url
vacío) registra `sin_acceso` sin error. Ver `scripts/discovery/stage2_ingest.py:485-489`.

## Tabla completa (26 referentes)

Ordenada por `status, nombre`. `youtube_raw` = valor crudo de la columna
`YouTube channel` (Notion `url` type) leído via API `/v1/pages/<id>` 2026-05-08.

### OK (13/26) — todos formato URL handle estándar

| # | Nombre | YouTube raw | Bucket |
|---|---|---|---|
| 1 | Alex Freberg | `https://www.youtube.com/@AlexTheAnalyst` | OK |
| 2 | Andrew Ng | `https://www.youtube.com/@Deeplearningai` | OK |
| 3 | Bernard Marr | `https://www.youtube.com/@BernardMarr` | OK |
| 4 | Carlos Santana Vega | `https://www.youtube.com/@DotCSV` | OK |
| 5 | Cole Nussbaumer Knaflic | `https://www.youtube.com/@storytellingwithdata` | OK |
| 6 | Daniel Shiffman | `https://www.youtube.com/@TheCodingTrain` | OK |
| 7 | Fred Mills | `https://www.youtube.com/@TheB1M` | OK |
| 8 | Grant Sanderson | `https://www.youtube.com/@3blue1brown` | OK |
| 9 | José Luis Crespo | `https://www.youtube.com/@QuantumFracture` | OK |
| 10 | Lucas Dalto | `https://www.youtube.com/@SoyDalto` | OK |
| 11 | Milos Temerinski | `https://www.youtube.com/@BalkanArchitect` | OK |
| 12 | Nate Gentile | `https://www.youtube.com/@nategentile7` | OK |
| 13 | Ruth Pozuelo Martinez | `https://www.youtube.com/@curbal` | OK |

**Patrón**: 13/13 OK son formato `https://www.youtube.com/@handle`. 0 usan
`/c/`, `/user/`, `/channel/UC...`, handle suelto, ni m.youtube.com.

### sin_acceso (13/26) — TODOS bucket (a) NULL/vacío en Notion

| # | Nombre | Referente ID | YouTube raw | Bucket |
|---|---|---|---|---|
| 1 | Brian Solis | `a3d99a32-4d68-4d92-ba2b-0dbc9c3b8e07` | `null` | (a) NULL |
| 2 | Burcin Kaplanoglu | `4e95272a-7c59-46dd-9bbc-8a048a894992` | `null` | (a) NULL |
| 3 | David Barco Moreno | `950bb2fd-a303-4c8d-be77-c717222e0fab` | `null` | (a) NULL |
| 4 | Dion Hinchcliffe | `67508bbd-0d2d-4ed6-98cc-9c697e82f8b2` | `null` | (a) NULL |
| 5 | Ignasi Pérez Arnal | `fb782bdb-d247-4530-8f6b-381eb9280fbe` | `null` | (a) NULL |
| 6 |  Iván Gómez Rodríguez | `6a8c8e2c-fd42-439d-8356-b9d4054228fc` | `null` | (a) NULL |
| 7 | Marc Vidal | `2b1fd15f-3610-45d4-b180-74d95d9a5a17` | `null` | (a) NULL |
| 8 | Martín Arosa | `f135dd9b-5a29-4fb7-b7e7-d9f1ba54c688` | `null` | (a) NULL |
| 9 | Pascal Bornet | `8bad9f1b-427a-4647-8c65-be78cba7527a` | `null` | (a) NULL |
| 10 | Pascal Bornet (duplicado) | `b0f28af3-e449-4697-b385-09e0746386fc` | `null` | (a) NULL + posible dup |
| 11 | Rodrigo Rojo | `d7c9538e-d7ee-4147-8dd2-2a4b902d2e6a` | `null` | (a) NULL |
| 12 | Ruben Hassid | `178ee83c-752b-4a7b-b76b-2889726980d2` | `null` | (a) NULL |
| 13 | Sandeep Raut | `6fdd6c53-af49-4aee-8d44-cbaab0aa5a15` | `null` | (a) NULL |

**Notas para David**:
- **Pascal Bornet** aparece 2 veces (IDs `8bad9f1b...` y `b0f28af3...`). Posible
  duplicado a consolidar en Notion.
- Todos los demás son referentes únicos sin canal YouTube cargado.

## Acción requerida de David (gap data entry)

Para subir cobertura hacia 26/26, David debe:

1. **Identificar canal YouTube** (si existe) para cada uno de los 13 referentes
   listados arriba.
2. **Pegar URL** en columna `YouTube channel` de la DB Referentes en Notion.
   Formato preferido (basado en patrón actual): `https://www.youtube.com/@handle`.
3. **Si un referente no tiene canal YouTube**: marcar explícitamente (e.g.
   poner `none` o usar un flag en `Flags canales`) para distinguir "sin canal"
   de "data entry pendiente".
4. **Resolver duplicado** Pascal Bornet (mantener uno solo).

Próxima ejecución del cron `discovery-publish-cron.sh` (cada 6h) procesará
automáticamente los referentes recién completados. No se requiere acción
técnica adicional.

## Hardening defensivo del parser (esta PR)

Aunque NO recupera ningún ítem ahora, el parser actual sólo está testeado
contra `https://www.youtube.com/@handle`. Cuando David rellene los 13 vacíos,
podría usar formatos diversos:

- `https://m.youtube.com/@handle`
- `youtube.com/@handle` (sin scheme)
- `@handle` suelto
- `youtube.com/c/LegacyChannel`
- `youtube.com/user/legacyUser`
- `youtube.com/channel/UC...`
- URLs con trailing slash, query params (`?si=xxx`), fragment (`#about`)
- HTML escaped (`&amp;`)

Para evitar `parse_error` regresions cuando llegue ese momento, esta PR agrega
hardening defensivo:

- **Tests**: `tests/dispatcher/test_youtube_handle_parser.py` con casos para
  todos los formatos esperables.
- **Parser**: ajustes mínimos a `parse_youtube_channel_id` para soportar:
  - URL sin scheme
  - Handle suelto (`@username`)
  - Trailing slash, query, fragment
  - Mayúsculas mixtas en netloc
- **No cambios** a comportamiento actual para los 13 OK (regression-safe).

Backoff/retry NO se implementa en esta PR porque NINGÚN referente actual
está fallando por API/quota — todos los OK pasan en el primer intento. Es una
mejora prematura (YAGNI) que se difiere hasta que aparezca evidencia real de
rate-limit failures en `fetch_log`.

## Verificación post-PR

```bash
# 1. Parser tests verdes
pytest tests/dispatcher/test_youtube_handle_parser.py -v

# 2. Cobertura igual (sin regresion)
python3 -c "
import sqlite3
c = sqlite3.connect('/home/rick/.cache/rick-discovery/state.sqlite')
print(dict(c.execute('''
  SELECT status, COUNT(*) FROM (
    SELECT f.status FROM fetch_log f
    INNER JOIN (SELECT referente_id, MAX(id) as max_id FROM fetch_log
                WHERE canal=\"youtube\" GROUP BY referente_id) m ON f.id = m.max_id
  ) GROUP BY status
''').fetchall()))
# Esperado: {'ok': 13, 'sin_acceso': 13} (idéntico al pre-PR)
"
```

## Anexo: comando de diagnóstico

```bash
set -a && source ~/.config/openclaw/env && set +a
python3 - <<'PY'
import os, sqlite3, httpx
key = os.environ['NOTION_API_KEY']
H = {'Authorization': f'Bearer {key}', 'Notion-Version': '2025-09-03'}
c = sqlite3.connect("/home/rick/.cache/rick-discovery/state.sqlite")
c.row_factory = sqlite3.Row
sql = """SELECT f.referente_id, f.status FROM fetch_log f
INNER JOIN (SELECT referente_id, MAX(id) as max_id FROM fetch_log
            WHERE canal='youtube' GROUP BY referente_id) m ON f.id = m.max_id"""
for r in c.execute(sql):
    page = httpx.get(f"https://api.notion.com/v1/pages/{r['referente_id']}",
                     headers=H, timeout=15).json()
    yt = page.get("properties", {}).get("YouTube channel", {}).get("url")
    nm = "".join(t.get("plain_text","") for t in page.get("properties",{}).get("Nombre",{}).get("title",[]))
    print(f"{r['status']:12s} {yt or '(NULL)':50s} {nm}")
PY
```
