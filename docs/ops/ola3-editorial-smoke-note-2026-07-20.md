# Ola 3 — Nota de smoke del pipeline editorial (2026-07-20)

> Estado: **FASE A completada (PASS)**. Docs-only. No activa runtime, no publica, no
> abre gates humanos, no toca Notion ni Azure. Base en `main`: `136a1a47` (PR #544,
> Ola 2 — stage9c/stage8 fail-closed).

## Objetivo

Demostrar que el camino **blog / editorial valida localmente sin tocar la red de
publicación**, respetando todas las prohibiciones de la Ola 3.

## Qué se corrió

### 1. pytest focalizado (offline, sin secretos reales)

```
WORKER_TOKEN=test python -m pytest \
  tests/test_editorial_publish.py \
  tests/test_editorial_unpublish.py \
  tests/test_editorial_function_shared.py \
  tests/test_editorial_production.py \
  tests/test_editorial_gold_set.py -q
```

Resultado: **114 passed, 0 failed** (2.33 s).

- `WORKER_TOKEN=test` es un valor **dummy** que el propio docstring de
  `tests/test_editorial_publish.py` prescribe para verificar el header
  `x-worker-token`. No es un secreto real.
- Sin red: los tests **mockean `urllib` y `notion_client`** (declarado en el
  encabezado del test). `test_editorial_production` y `test_editorial_gold_set`
  son puramente file-based (validan `evals/editorial/*.yaml` + guard de modelo).

### 2. Demo dry-run del handler `web.publish_editorial_post` (offline)

Script local `smoke_editorial_dryrun.py` (fuera del repo, en scratchpad de sesión)
que invoca el handler con `urllib.request.urlopen` **parcheado para abortar
cualquier egress de red**. Resultado **3/3 PASS**:

| Caso | Entrada | Salida | Red |
|---|---|---|---|
| Gate cerrado | `autorizar_publicacion=false`, `aprobado_contenido=false`, `dry_run=true` | `ok=false`, `would_publish=false`, `error=publication_not_authorized` | ninguna |
| Gate abierto + dry-run | gates `true`, `dry_run=true` | `ok=true`, `would_publish=true`, `dry_run=true`, `blob_path`/`published_url` calculados | ninguna |
| Unpublish dry-run | `slug`, `dry_run=true` | `ok=true`, `would_unpublish=true` | ninguna |

Confirma el comportamiento **fail-closed** documentado en `ADR-010` y en el
docstring del handler: sin `autorizar_publicacion=true` (y `aprobado_contenido=true`
desde Notion) **no hay llamada de red**.

## Resultado

**PASS** para el alcance permitido (validación offline / dry-run del pipeline
editorial). La única cobertura no realizada es la **llamada de red real a la Azure
Function** de publish/unpublish: queda **NO ejecutada por diseño** — está
explícitamente prohibida en el smoke de esta ola y además requeriría secretos
ausentes (`EDITORIAL_BLOG_FUNCTION_URL` / `EDITORIAL_BLOG_FUNCTION_KEY` /
`WORKER_TOKEN` reales). No se inventaron credenciales. Esto no es un fallo: es el
límite de alcance de la Ola 3.

## Prohibiciones del smoke — verificación

- [x] Sin llamar la Azure Function de publish/unpublish con contenido real.
- [x] Sin abrir gates `aprobado_contenido` / `autorizar_publicacion`.
- [x] Sin POST LinkedIn (stage9c) ni Google Image (stage8).
- [x] `RICK_LINKEDIN_ORG_PUBLISH_ENABLED` y `RICK_STAGE8_GOOGLE_IMAGE_ENABLED`
      **no seteados** — siguen default-off / fail-closed (verificado read-only en
      `scripts/discovery/lib/linkedin_org_guard.py` y
      `scripts/discovery/lib/image_provider_guard.py`; guards Ola 2 intactos).
- [x] Sin SSH / VPS / deploy / reinicios.
- [x] Sin escritura a Notion `Publicaciones`.
- [x] Sin rotar secretos ni tocar `env.rick` / `vm_script` / token-map / auth store.

## Referencias

- Contrato: `docs/ops/editorial-agent-flow.md`
- CMS blog: `docs/adr/ADR-010-azure-editorial-blog-cms.md` · `worker/tasks/editorial_publish.py`
- Criterios de orquestación: `docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md`
- Pitches (FASE B): `docs/ops/ola3-editorial-5-pitches-2026-07-20.md`
