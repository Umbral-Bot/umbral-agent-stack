# ADR-010: Azure como CMS del blog editorial (Blob + Function + CDN)

## Estado

Proposed — 2026-06-08

Relacionado: [ADR-007](ADR-007-notion-como-hub-editorial.md) (Notion como hub
editorial), [ADR-008](ADR-008-orquestacion-editorial.md) (orquestación Agent
Stack core + n8n bordes).

## Contexto

El sistema editorial (ADR-007/008) usa Notion como hub humano y el Agent Stack
para orquestar. Falta la **capa de publicación del blog**: dónde vive la versión
canónica de cada artículo que se sirve en `umbralbim.io/noticias/:slug`.

Restricción de producto firme: el SaaS **Umbral BIM** (Supabase + Lovable) es
para chat/auth del producto, **no** para el blog editorial. El blog no debe
acoplarse a la base de datos del bot.

Modelo de canales (no renegociable):

- **Blog** = versión canónica completa (este ADR).
- **LinkedIn David** = teaser corto + link al blog.
- **LinkedIn Umbral BIM (empresa)** = texto sugerido para compartir.
- **X** = resumen + link.

Secuencia: **blog primero** → se inyecta `published_url` en las copies que lo
necesiten → luego RRSS (manual o semi-auto). El código nunca autopublica RRSS.

## Decisión

**Azure Blob Storage como almacén canónico del blog, detrás de una Azure
Function HTTP y (opcionalmente) Azure CDN.** Sin base de datos: el contenido es
JSON estático servido como blobs.

```
Notion (Copy Blog + metadata + gates)
  → Worker task web.publish_editorial_post   (valida + gate humano)
    → Azure Function POST /api/publish-editorial-post   (function key + x-worker-token)
      → Blob container editorial-posts/
          posts/{slug}.json   # post completo (schema_version 1)
          index.json          # listado liviano, published_at desc
  → SPA umbralbim.io fetch CDN/Blob público (handoff Lovable, repo aparte)

Operadores / Rick cleanup
  → Worker task web.unpublish_editorial_post   (sin gate de publicación)
    → Azure Function POST /api/unpublish-editorial-post
      → remove index.json entry + delete posts/{slug}.json idempotently
```

### Componentes

- **Storage**: cuenta dedicada `steditorial{env}`, container `editorial-posts`.
  Lectura pública vía **CDN** (preferido) o, si se habilita explícitamente,
  lectura anónima de blobs. El SPA solo hace `GET` de `index.json` y
  `posts/{slug}.json`.
- **Function** (Python 3.12, v2 model, Consumption): valida el payload, escribe
  el blob del post y hace **upsert idempotente** de `index.json` con
  concurrencia optimista por ETag. También expone `unpublish-editorial-post`,
  que remueve una entrada por `notion_page_id` o `slug` y borra el blob del post
  de forma idempotente. Idempotencia por `notion_page_id` / `content_hash` →
  re-publicar el mismo contenido no duplica el slug.
- **Identidad**: Managed Identity de la Function con *Storage Blob Data
  Contributor* (escribe blobs sin account key).
- **CDN** (opcional, `Standard_Microsoft`): origen = blob, compresión + caché
  para servir el JSON al SPA.

### Gates (heredados de ADR-007, reforzados en código)

El handler del Worker **nunca** llama a la Function sin
`autorizar_publicacion = true` en el payload validado (y `aprobado_contenido =
true` cuando la fuente es Notion). Si el gate no está abierto: `ok=false`,
`would_publish=false`, **sin llamada de red**. Esto refleja el espíritu de los
guardrails de `copilot_cli` (fail-closed) y la regla "solo David abre los gates".

`web.unpublish_editorial_post` es la operación inversa de limpieza/rollback y no
requiere `autorizar_publicacion`. No crea contenido público; solo quita una
entrada existente del índice y opcionalmente borra `posts/{slug}.json`.

### Post-publish: indexado RAG (Task B)

Tras un publish exitoso (no `dry_run`, gate abierto), el handler indexa
`body_markdown` en Azure AI Search **reutilizando `worker/tasks/rag.py`**
(`rag.index` → embeddings, sin duplicar lógica). Índice por defecto
`umbral-editorial` (env `EDITORIAL_RAG_INDEX_NAME`), `source_type =
editorial_blog`.

Es **best-effort**: si falta el env (`AZURE_SEARCH_*` / `AZURE_OPENAI_*`) o el
indexado falla, el publish **sigue `ok`** y la respuesta incluye
`rag_indexed=false` + `rag_skipped_reason` / `rag_error`. Flags de entrada:
`index_after_publish=true` (default), `skip_rag_index=false`. El blog ya está
publicado; el RAG enriquece pero nunca bloquea.

### Seguridad

- Auth de la Function: function key (`x-functions-key`) + opcional secreto
  compartido `x-worker-token` (`WORKER_TOKEN`).
- Secrets vía Key Vault / `@secure()` params / app settings — **nunca** en git.
- Sin deploy productivo desde el PR: solo `az bicep build` + `what-if`.

### Contrato de baja

`POST /api/unpublish-editorial-post` acepta:

```json
{
  "slug": "kebab-case",
  "notion_page_id": "uuid-opcional",
  "delete_post_blob": true
}
```

Debe venir `slug` o `notion_page_id`. Si viene `notion_page_id`, ese match tiene
precedencia; si no viene, se usa `slug`. La respuesta 200 incluye
`index_updated`, `removed_from_index` y `post_blob_deleted`. No encontrar la
entrada o el blob no es error, para permitir retries seguros.

## Alternativas consideradas

### 1. Supabase como CMS del blog

Rechazada (restricción de producto). Acopla el blog editorial a la base del SaaS
Umbral BIM, mezclando dominios (chat/auth del producto vs contenido público).
Aumenta el blast radius de cambios y los costos de RLS/políticas para contenido
que es, por naturaleza, estático y público.

### 2. Ghost / WordPress / CMS gestionado

Rechazada para v1. Introduce un servicio nuevo (hosting, updates, plugins,
backups, theming) y un segundo lugar de verdad fuera de Notion. El volumen
(~20-40 posts/mes) no justifica un CMS completo. Notion ya es el hub humano;
Azure Blob es suficiente como capa de entrega.

### 3. Commit de Markdown al repo del frontend (SSG)

Rechazada para v1. Requiere que el Worker haga PRs al repo del SPA y dispare
builds; acopla publicación a CI del frontend y a permisos de git. El blob +
`index.json` desacopla publicación de despliegue del frontend.

### 4. Azure Static Web Apps / base de datos (Cosmos/Table)

Diferida. Cosmos/Table sirve si necesitamos queries server-side, paginación
grande o búsqueda. Para un listado de decenas de posts, `index.json` en blob es
más simple y barato (sin RU/s). Migrable si el volumen crece.

## Consecuencias

### Positivas

- **Desacoplado del SaaS**: el blog no toca Supabase ni Lovable.
- **Barato y simple**: blobs estáticos + Function Consumption (scale-to-zero).
- **Idempotente**: re-publicar no duplica; ETag evita carreras en `index.json`.
- **Cacheable**: CDN sirve JSON al SPA con baja latencia.
- **Fail-closed**: imposible publicar sin el gate humano abierto.

### Negativas

- **Sin queries server-side**: filtrado/búsqueda es client-side sobre
  `index.json` (suficiente para el volumen actual).
- **`index.json` es un único objeto**: con miles de posts habría que paginar o
  migrar a una DB (documentado como límite v1).
- **Cuerpos largos desde Notion**: leer `Copy Blog` como propiedad rich_text
  tiene límites; cuerpos extensos que viven en el body de la página requieren un
  paso adicional (fuera de alcance v1; ver runbook).
- **Dos unidades de deploy** (Function + SPA) a coordinar vía contrato JSON.

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Carrera al actualizar `index.json` | Media | Medio | Concurrencia optimista por ETag + reintentos |
| Exposición pública no deseada de blobs | Baja | Medio | `enablePublicBlobRead=false` por defecto; preferir CDN |
| `index.json` crece demasiado | Baja (v1) | Medio | Límite documentado; migración a DB como plan B |
| Slug renombrado deja blob huérfano | Baja | Bajo | Upsert por `notion_page_id` quita la entrada vieja del índice (blob viejo queda sin listar; limpieza manual) |
| Cleanup manual rompe `index.json` | Media | Medio | Endpoint unpublish con ETag retry y smoke script; evitar edición manual salvo emergencia |
| Secreto `WORKER_TOKEN` filtrado | Baja | Medio | Key Vault / app settings; rotación documentada en runbook |

## Variables de entorno

| Variable | Dónde | Descripción |
|----------|-------|-------------|
| `EDITORIAL_BLOG_FUNCTION_URL` | Worker | URL completa del endpoint de la Function |
| `EDITORIAL_BLOG_FUNCTION_KEY` | Worker | function key (`x-functions-key`) |
| `EDITORIAL_BLOG_STORAGE_ACCOUNT` | Function | cuenta de storage (auth MI) |
| `EDITORIAL_BLOG_CDN_BASE_URL` | Function / SPA | base pública del CDN |
| `WORKER_TOKEN` | Worker + Function | secreto compartido `x-worker-token` |
| `EDITORIAL_RAG_INDEX_NAME` | Worker | índice RAG post-publish (default `umbral-editorial`) |
| `AZURE_SEARCH_*` / `AZURE_OPENAI_*` | Worker | requeridos por el hook RAG; si faltan, se omite |

## Referencias

- Infra: [`infra/azure/modules/editorial-blog.bicep`](../../infra/azure/modules/editorial-blog.bicep)
- Function: [`functions/editorial-publish/`](../../functions/editorial-publish/)
- Worker: [`worker/tasks/editorial_publish.py`](../../worker/tasks/editorial_publish.py)
- Runbook: [`docs/ops/azure-editorial-blog-runbook.md`](../ops/azure-editorial-blog-runbook.md)
- Modelo de contenido: [`docs/ops/notion-blog-linkedin-v3-content-model.md`](../ops/notion-blog-linkedin-v3-content-model.md)
- Handoff frontend: [`docs/lovable-handoffs/umbral-bim-noticias-azure-cdn.md`](../lovable-handoffs/umbral-bim-noticias-azure-cdn.md)
