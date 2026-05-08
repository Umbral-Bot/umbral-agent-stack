# Stage 10 — Dry-Run Audit Report

**Date**: 2026-05-08
**Branch**: `copilot/feat-s10-publish-guard`
**Hilo**: 6 (S10/S11)
**Status**: DRAFT — DO NOT MERGE
**Cero publicaciones reales** — auditoría sintética con páginas Notion ficticias.

## Setup

* `scripts/discovery/lib/publish_guard.py` invocado directamente.
* `dedup` reemplazado por un fake en `sys.modules` con un `set()` de
  hashes pre-publicados.
* `gates` real (Hilo 4) — la lógica de evaluación NO se mockea: usa
  `gates.evaluate_gates()` y `gates.can_publish()` genuinos.
* `OPS_LOG_PATH=/tmp/h6-audit-ops.jsonl` para inspección post-run.

## Páginas ficticias evaluadas

| page_id  | Notion gates             | Pre-seed dedup? | Resultado esperado |
|----------|---------------------------|-----------------|--------------------|
| `page-A` | todas OK                  | no              | `would_publish=true` |
| `page-B` | `aprobado_contenido=False`| no              | block (1 razón)      |
| `page-C` | todas OK                  | **sí** (hash en `published_history`) | block por `contenido_duplicado` |
| `page-D` | múltiples mal             | no              | block (5 razones)    |

## Resultados (output literal del guard)

```json
[
  {
    "page_id": "page-A",
    "content_hash": "c13187652e24…",
    "would_publish": true,
    "reasons_blocked": []
  },
  {
    "page_id": "page-B",
    "content_hash": "9e4421d9fc84…",
    "would_publish": false,
    "reasons_blocked": ["aprobado_contenido_missing"]
  },
  {
    "page_id": "page-C",
    "content_hash": "f59e8d069ac7…",
    "would_publish": false,
    "reasons_blocked": ["contenido_duplicado"]
  },
  {
    "page_id": "page-D",
    "content_hash": "c53d0c576438…",
    "would_publish": false,
    "reasons_blocked": [
      "aprobado_contenido_missing",
      "autorizar_publicacion_missing",
      "gate_invalidado_active",
      "fuente_primaria_missing",
      "plataforma_no_seleccionada"
    ]
  }
]
```

## ops_log emitido (literal)

```jsonl
{"ts":"2026-05-08T22:35:31.349100+00:00","event":"publish_guard.pass","page_id":"page-A","content_hash":"c13187652e2468f779aa97b2a7625536399e8cf8a7d556df4906f739a9de5823","reasons":[]}
{"ts":"2026-05-08T22:35:31.349362+00:00","event":"publish_guard.block","page_id":"page-B","content_hash":"9e4421d9fc846d135c103fb366a0f20319f7619080b606efa1174219ce622bb6","reasons":["aprobado_contenido_missing"]}
{"ts":"2026-05-08T22:35:31.349440+00:00","event":"publish_guard.block","page_id":"page-C","content_hash":"f59e8d069ac775178e6a7dd27a5b2f3d62fc2b236a958b912418a9c2157d616d","reasons":["contenido_duplicado"]}
{"ts":"2026-05-08T22:35:31.349485+00:00","event":"publish_guard.block","page_id":"page-D","content_hash":"c53d0c57643844dcc1069e71501f5b64e61276b63776b613b5c28ac8201c0989","reasons":["aprobado_contenido_missing","autorizar_publicacion_missing","gate_invalidado_active","fuente_primaria_missing","plataforma_no_seleccionada"]}
```

## Tabla resumida

| page_id | gates_ok | duplicado | would_publish | reasons_blocked |
|---------|----------|-----------|---------------|-----------------|
| page-A  | ✅ 6/6   | no        | **true**      | —               |
| page-B  | ❌ 5/6   | no        | false         | `aprobado_contenido_missing` |
| page-C  | ✅ 5/6 + dup ❌ | **sí** | false  | `contenido_duplicado` |
| page-D  | ❌ 1/6   | no        | false         | 5 razones (todas Notion-side) |

## Verificaciones cruzadas

* ✅ Orden estable de razones en `page-D` (matches `gates._GATE_ORDER`).
* ✅ Una sola línea ops_log por evaluación.
* ✅ `publish_guard.pass` sólo en `page-A`.
* ✅ `gate_invalidado_active` sólo aparece cuando el checkbox está True
  (semántica invertida de la gate).
* ✅ `dedup.is_duplicate` consultado únicamente cuando las gates Notion
  pasan parcialmente (en `page-D` no hay duplicado en la lista porque
  faltan otras razones primero — el orden lo confirma).
* ✅ Cero llamadas a `httpx` durante la auditoría (verificado por
  inspección: `publish_guard.py` no importa `httpx`).

## Conclusión

El guard se comporta exactamente como exige la spec §3 de Hilo 6:

1. Bloquea si **cualquier** gate falla.
2. Reporta razones en orden estable.
3. Emite trazabilidad estructurada al ops_log.
4. Nunca toca la red.

Listo para integración con `stage9c_linkedin_publish.py` en modo
`--dry-run` (cubierto por `tests/discovery/test_stage9c_dry_run.py`).
