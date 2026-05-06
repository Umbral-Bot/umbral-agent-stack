# Task 012 — Stage 1 LinkedIn: smoke REST live de DB Referentes

- **Date:** 2026-05-05
- **Assigned to:** copilot-vps
- **Type:** runtime verification (read-only contra Notion API, NO writes)
- **Depends on:**
  - PR #286 (mergeado a `main` en `5fa022d`) — script `scripts/smoke/referentes_rest_read.py`.
  - Snapshot vendored del registry en este mismo repo: `vendor/notion-governance/registry/notion-data-sources.template.yaml` (refrescado 2026-05-05 desde `notion-governance@1d1c3c6`). NO se requiere clonar `notion-governance` en la VPS.
  - Audit 006 (`2026-05-05-006-...`) — confirma que la autoridad runtime correcta es `worker.config.NOTION_API_KEY`, NO la MCP de Rick.
  - Notion: integration Rick (la del `NOTION_API_KEY` de la VPS) tiene share confirmado sobre la página/DB **Referentes** (verificado 2026-05-05). No requiere acción adicional en Notion.
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` §11.3 (Stage 1 smoke gate).
- **Status:** ready
- **Estimated effort:** ~15 min (sin debugging).

---

## Objetivo

Ejecutar **live** el smoke read-only `scripts/smoke/referentes_rest_read.py` desde el entorno worker de la VPS, contra la DB Notion Referentes (`data_source_id = afc8d960-086c-4878-b562-7511dd02ff76`), y reportar el JSON completo de salida en este archivo.

Este es el **gate de salida de Stage 1**. Sin un `overall_pass: true` (o un fail entendido y aceptado por David), no se procede a Stage 2 del plan LinkedIn.

## Pre-checks (antes de ejecutar)

1. **Repo sincronizado:**
   ```bash
   cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
   git log --oneline -1   # debe mostrar 5fa022d o más reciente
   git status --short     # debe estar limpio
   ```
2. **Registry vendored presente y con la entry esperada:**
   ```bash
   ls -la ~/umbral-agent-stack/vendor/notion-governance/registry/notion-data-sources.template.yaml
   grep -n "referencias_referentes:" ~/umbral-agent-stack/vendor/notion-governance/registry/notion-data-sources.template.yaml
   # Esperado: 1 match alrededor de línea 435.
   ```
   Si el archivo no existe: el `git pull` del pre-check 1 no trajo el snapshot. Verificar con `git log --oneline -- vendor/notion-governance/`. Abortar y notificar; NO clonar `notion-governance` ni reconstruir el registry desde cero.
3. **Env worker cargado** (mismo que usa `umbral-worker.service`):
   ```bash
   # NO imprimir el valor del token. Solo verificar presencia:
   python - <<'PY'
   from worker import config
   print("NOTION_API_KEY set:", bool(config.NOTION_API_KEY))
   PY
   ```
   Si imprime `False`: revisar que el shell tenga la misma fuente de env que el worker (`source ~/.config/openclaw/env` o equivalente).

## Comando de ejecución

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
set -a && source ~/.config/openclaw/env && set +a
mkdir -p reports
TS=$(date -u +%Y%m%dT%H%M%SZ)
python scripts/smoke/referentes_rest_read.py \
  --registry vendor/notion-governance/registry/notion-data-sources.template.yaml \
  --output reports/stage1-smoke-referentes-${TS}.json
echo "exit=$?"
```

## Criterios de éxito

- **Exit code:** `0`
- **JSON `overall_pass`:** `true`
- **`row_count`:** `26` (igual a `expected_row_count` del registry)
- **`checks.a_three_distinct_profiles_with_10_columns.pass`:** `true`
- **`checks.b_row_count_26.pass`:** `true`
- **`checks.c_linkedin_activity_feed_urls.pass`:** `true`
- **`checks.d_confianza_enum.pass`:** `true`
- **`checks.e_flags_enum.pass`:** `true`
- **`authority.mode`:** `notion_rest_read_only`
- **`authority.mutation_endpoints_used`:** `false`

## Si falla

- **Exit 3 (`setup_error`) con mensaje sobre registry key faltante:** el snapshot vendored no contiene la entry o no está sincronizado. Confirmar con `git log --oneline -1 -- vendor/notion-governance/registry/notion-data-sources.template.yaml`. Si el snapshot no fue refrescado, NO modificarlo en la VPS — abortar y notificar a David para que haga el refresh-and-push desde Windows.
- **Exit 3 (`setup_error`) con mensaje sobre `NOTION_API_KEY`:** falta env del worker. Resolver pre-check 3 y reintentar.
- **HTTP 404 / `object_not_found` desde Notion:** la integration Rick perdió share sobre la DB Referentes. NO reintentar, notificar a David para re-share.
- **Exit 4 (`runtime_error`):** error HTTP/red contra Notion. Pegar el `runtime_error` completo en el reporte; NO reintentar más de 2 veces.
- **Exit 2 (`overall_pass: false`):** algún check (a)-(e) falló. NO arreglar la DB en este task. Pegar el JSON completo y dejar a David decidir (puede ser data drift legítimo: nuevas filas, enums añadidos, URL inválida en una fila concreta).

En cualquier fallo: **NO** committear cambios al script, **NO** reiniciar servicios, **NO** tocar la DB Notion. Solo reportar.

## Restricciones operacionales

- **NO** PATCH/POST/DELETE contra Notion (el script ya los bloquea internamente).
- **NO** copiar el valor de `NOTION_API_KEY` ni en logs ni en el reporte.
- **NO** subir el JSON de reporte si contiene IDs de fila completos en algún caso edge — el script ya emite solo `row_id_tail` (últimos 8 chars), confirmar antes de pegar.
- **NO** dejar el repo VPS en branch distinta de `main` al cerrar.

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash del commit en `main` al momento de ejecutar (`git log --oneline -1`).
2. Path del archivo generado en `reports/`.
3. **JSON completo** de `report` (puede ser largo — está OK, es el deliverable principal).
4. Decisión sugerida: `PASS → notificar Stage 2 unblocked` / `FAIL → razón breve y si requiere acción de David`.

## Quality gate

- [ ] Pre-checks 1-3 verdes.
- [ ] Comando ejecutado, JSON generado en `reports/`.
- [ ] Reporte pegado en este archivo.
- [ ] Repo VPS en `main`, working tree clean al cerrar.
- [ ] Si pasó: David puede leer el JSON y decidir mergear el siguiente PR de Codex (Stage 2 ingest).

---

## Resultado 2026-05-05

**Ejecutor:** Claude (Copilot CLI) sobre VPS, branch `main`.

### 1. Hash del commit en `main` al momento de ejecutar

```
54720d7 task(stage1): copilot-vps live smoke read-only Referentes
```

### 2. Path del archivo generado

```
reports/stage1-smoke-referentes-20260505T215456Z.json
```

### 3. JSON completo del reporte

```json
{
  "overall_pass": false,
  "setup_error": "Registry key referencias_referentes not found in /home/rick/notion-governance-git/registry/notion-data-sources.template.yaml",
  "checks": {}
}
```

### 4. Decisión sugerida

**FAIL → setup_error (exit 3). Requiere acción de David.**

**Diagnóstico:**

- Pre-check 1 (repo en `main`, hash ≥ `54720d7`): ✅ verde.
- Pre-check 2 (registry sibling): ✅ archivo existe en `/home/rick/notion-governance-git/registry/notion-data-sources.template.yaml` (la ruta default `~/notion-governance/registry/...` no existe en esta VPS — se usó `--registry` explícito según permite el task).
- Pre-check 3 (`worker.config.NOTION_API_KEY`): ✅ `True`.
- Ejecución (1 sola vez, sin reintento — el error es determinístico y no se resuelve con reintento):
  - Exit code: `3` (`setup_error`).
  - El script localizó el registry, lo parseó como YAML válido, pero **no encontró la entrada `referencias_referentes`** ni en `critical_databases:` ni en `reference_systems:` (las dos secciones donde `_find_referentes_registry_entry` la busca, ver `scripts/smoke/referentes_rest_read.py:148-155`).

**Estado actual del registry en la VPS** (`/home/rick/notion-governance-git/registry/notion-data-sources.template.yaml`):

- `critical_databases:` contiene `granola_raw_intake` (y otros), **no** `referencias_referentes`.
- `reference_systems:` contiene `referencias_paginas_intake` (data_source `2755f443-fb5c-81ca-ab6d-000be11a33b3`), **no** `referencias_referentes`.
- Búsqueda de `data_source_id: afc8d960-086c-4878-b562-7511dd02ff76` (Referentes) en todos los YAML bajo `~/notion-governance-git`, `~/notion-governance-local`, y el resto de `~/`: **0 hits**.

**Restricciones respetadas:**

- ❌ No se modificó el script `scripts/smoke/referentes_rest_read.py`.
- ❌ No se modificó ningún archivo bajo `notion-governance-git/`.
- ❌ Cero llamadas HTTP a Notion (el script aborta antes del primer fetch al fallar el setup).
- ❌ El valor de `NOTION_API_KEY` no aparece en logs ni en este reporte.
- ❌ El JSON no contiene `row_id` completos (no aplica — el setup_error abortó antes de leer filas).

**Acción requerida de David / próximo paso:**

El gate Stage 1 requiere actualizar `notion-governance` para incluir la entrada `referencias_referentes` con `data_source_id: afc8d960-086c-4878-b562-7511dd02ff76` y los campos esperados por el script (`expected_row_count: 26`, `expected_columns`, `expected_confianza`, `expected_flags`). Una vez mergeado en `notion-governance` y propagado al sibling de la VPS (`/home/rick/notion-governance-git`), reabrir esta task y reintentar.

**No se procede a Stage 2 del plan LinkedIn.**

---

## Resultado 2026-05-05 (intento 2)

**Ejecutor:** Copilot-VPS, branch `main`.

### 1. Hash del commit en `main` al momento de ejecutar

```
0ad4566 (vendor: notion-governance snapshot @ 1d1c3c6 + task 012 vendored path)
```

### 2. Path del archivo generado

```
reports/stage1-smoke-referentes-20260506T033143Z.json
```

### 3. JSON completo del reporte

```json
{
  "overall_pass": true,
  "authority": {
    "mode": "notion_rest_read_only",
    "credential": "worker.config.NOTION_API_KEY",
    "api_version": "2025-09-03",
    "mutation_endpoints_used": false,
    "query_note": "Notion data source row reads use POST /data_sources/{id}/query as a read-only endpoint."
  },
  "registry": {
    "path": "vendor/notion-governance/registry/notion-data-sources.template.yaml",
    "data_source_id": "afc8d960-086c-4878-b562-7511dd02ff76",
    "database_id": "05f04d48c44943e8b4acc572a4ec6f19"
  },
  "data_source_id": "afc8d960-086c-4878-b562-7511dd02ff76",
  "row_count": 26,
  "checks": {
    "a_three_distinct_profiles_with_10_columns": {
      "pass": true,
      "reason": "Required ALTA/MEDIA/DUPLICADO samples and 10-channel columns are readable",
      "missing_sample_confidences": [],
      "missing_schema_columns": [],
      "sample_missing_columns": {}
    },
    "b_row_count_26": {
      "pass": true,
      "reason": "row_count=26, expected=26"
    },
    "c_linkedin_activity_feed_urls": {
      "pass": true,
      "reason": "All populated LinkedIn activity feed values are valid http(s) URLs",
      "invalid_count": 0
    },
    "d_confianza_enum": {
      "pass": true,
      "reason": "Confianza canales values are within enum",
      "invalid_values": []
    },
    "e_flags_enum": {
      "pass": true,
      "reason": "Flags canales values are within enum",
      "invalid_values": []
    }
  },
  "observed_enums": {
    "confianza_canales": [
      "ALTA",
      "BAJA",
      "DUPLICADO",
      "MEDIA"
    ],
    "flags_canales": [
      "ACTIVIDAD_BAJA",
      "CAMBIO_DE_PLATAFORMA",
      "DUP",
      "REQUIERE_VERIFICACION_MANUAL",
      "RSS_NO_CONFIRMADO",
      "SIN_LINKEDIN",
      "SLUG_DIFIERE"
    ]
  },
  "invalid_urls": [],
  "sample_rows": [
    {
      "row_id_tail": "98249eb0",
      "nombre": "Alex Freberg",
      "confianza_canales": "ALTA",
      "flags_canales": [
        "RSS_NO_CONFIRMADO"
      ],
      "channels_populated": [
        "LinkedIn activity feed",
        "YouTube channel",
        "Web / Newsletter",
        "RSS feed"
      ]
    },
    {
      "row_id_tail": "8a894992",
      "nombre": "Burcin Kaplanoglu",
      "confianza_canales": "MEDIA",
      "flags_canales": [
        "REQUIERE_VERIFICACION_MANUAL"
      ],
      "channels_populated": [
        "LinkedIn activity feed",
        "Otros canales"
      ]
    },
    {
      "row_id_tail": "cba7527a",
      "nombre": "Pascal Bornet",
      "confianza_canales": "DUPLICADO",
      "flags_canales": [
        "DUP",
        "SLUG_DIFIERE"
      ],
      "channels_populated": [
        "LinkedIn activity feed",
        "Web / Newsletter",
        "RSS feed",
        "Otros canales"
      ]
    }
  ]
}
```

### 4. Decisión sugerida

**PASS → Stage 2 unblocked.**

- Exit code: `0`
- `overall_pass`: `true`
- `row_count`: `26` (= expected)
- Checks (a)-(e): todos `pass: true`
- `authority.mode`: `notion_rest_read_only`
- `authority.mutation_endpoints_used`: `false`
- Cero PATCH/POST/DELETE de mutación contra Notion
- Cero secretos en este reporte
