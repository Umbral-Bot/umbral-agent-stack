# Stage 11 — Observability Spec — Pipeline Editorial Métricas

**Hilo 6 / Wave 1 / Status: DRAFT — DO NOT MERGE**
**Owner**: Hilo 6 (S10/S11)
**Depends on**: `scripts/discovery/stageX_pipeline_dashboard.py`,
`scripts/discovery/lib/publish_guard.py`, `dedup.published_history`.

> ## ⚠️ Disclaimer literal — leerlo antes de cualquier discusión sobre métricas
>
> **`Pipeline Editorial — Métricas` mide observabilidad runtime; NO mide
> calidad editorial. Calidad = voice_match + gates humanos + engagement
> post-publish.**
>
> Este disclaimer es **obligatorio** y debe replicarse al inicio de la
> página `Pipeline Editorial — Métricas` en Notion (Subpage de `Control
> Room`). Cualquier interpretación de los counters de este dashboard
> como "el pipeline está bien" es incorrecta: counters altos sólo prueban
> que la maquinaria corre — no prueban que David esté contento con el
> output ni que las publicaciones generen impacto.

## 1. Inventario actual del dashboard

`stageX_pipeline_dashboard.py::collect_metrics(db_path)` produce un
`Metrics` dataclass con:

| Métrica                      | Tipo                | Origen SQL                                  | Cubre Hilo 6? |
|------------------------------|---------------------|---------------------------------------------|---------------|
| `total`                      | int                 | `SELECT COUNT(*) FROM proposals`            | parcial       |
| `status[<bucket>]`           | dict[str,int]       | `GROUP BY status`                           | parcial       |
| `image_status[<bucket>]`     | dict[str,int]       | `GROUP BY image_status`                     | no            |
| `linkedin_status[<bucket>]`  | dict[str,int]       | `GROUP BY linkedin_status`                  | sí (parcial)  |
| `last_24h_proposals`         | int                 | `WHERE ts >= now-24h`                       | parcial       |
| `last_24h_notion_pages`      | int                 | `WHERE notion_page_id IS NOT NULL`          | parcial       |
| `last_24h_linkedin`          | int                 | `WHERE linkedin_status IN (published, draft_ready)` | sí       |
| `cron_last_run`              | iso str             | `parse_last_cron_run(cron_log_path)`        | no            |
| `cron_next_run`              | iso str             | `compute_next_cron_run(now)`                | no            |
| `copy_review_pending`        | dataclass           | join sobre `copy_status`                    | parcial       |

## 2. Lo que falta para Hilo 6 — gaps de observabilidad

Estas métricas **no existen** hoy y son necesarias para responder
"¿el guard está funcionando?" y "¿estamos publicando duplicados?":

### 2.1 Métricas de publish_guard (read-only, ya escritas en ops_log)

| Métrica propuesta                         | Origen                                             | Refresh |
|-------------------------------------------|-----------------------------------------------------|---------|
| `publish_guard.pass / 24h`                | grep ops_log → `event=publish_guard.pass`           | hourly  |
| `publish_guard.block / 24h`               | grep ops_log → `event=publish_guard.block`          | hourly  |
| `publish_guard.block.by_reason{reason}`   | mismo, agrupado por `reasons[*]`                    | hourly  |
| `stage9c.published / 24h`                 | mismo → `event=stage9c.published`                   | hourly  |
| `stage9c.failed / 24h`                    | mismo → `event=stage9c.failed`                      | hourly  |

**Implementación propuesta** (no incluida en este PR): nuevo
`collect_ops_log_metrics(ops_log_path, *, since: datetime)` que parsea
JSONL y devuelve un counter. Riesgo: `ops_log.jsonl` puede crecer; para
producción se debe rotar (logrotate ya configurado en VPS).

### 2.2 Métricas dedup (lectura de `published_history`)

| Métrica                                   | Origen                                              | Refresh |
|-------------------------------------------|-----------------------------------------------------|---------|
| `published_history.total`                 | `SELECT COUNT(*) FROM published_history`            | hourly  |
| `published_history.by_platform{platform}` | `GROUP BY platform`                                 | hourly  |
| `published_history.last_24h`              | `WHERE published_at >= now-24h`                     | hourly  |
| `dedup.collisions / 24h`                  | grep ops_log → `event=publish_guard.block` AND `reasons CONTAINS contenido_duplicado` | hourly |

## 3. Métricas post-publish (engagement) — Hilo 8 / future

**Gap explícito**: hoy no hay forma de saber si un post publicado generó
engagement real. La aprobación de David es **previa** (gates) pero no
hay loop de feedback **posterior**.

### 3.1 Schema propuesto: `📈 Métricas post-publish` (Notion DB)

| Property              | Type      | Notes                                          |
|-----------------------|-----------|------------------------------------------------|
| Title                 | title     | Igual al `titular` original                    |
| `proposal_id`         | number    | FK a `proposals.id`                            |
| `post_urn`            | rich_text | URN devuelto por LinkedIn                      |
| `published_at`        | date      | Timestamp del POST 201                         |
| `voice_match_score`   | number    | El score que stage7.5 calculó pre-publish      |
| `impressions_n1`      | number    | Impresiones a +1 día                           |
| `impressions_n7`      | number    | Impresiones a +7 días                          |
| `impressions_n30`     | number    | Impresiones a +30 días                         |
| `likes_n7`            | number    | Likes acumulados a +7 días                     |
| `comments_n7`         | number    | Comments a +7 días                             |
| `shares_n7`           | number    | Shares a +7 días                               |
| `engagement_rate_n7`  | formula   | `(likes+comments+shares) / impressions`        |
| `david_rating`        | select    | 👍 / 👎 / 🤔 (manual, opcional)                 |
| `correlation_with_voice_match` | formula | indicador heurístico              |

### 3.2 Job que lo poblaría (no incluido)

Un cron `stage12_engagement_collector.py` que:

1. Lista posts publicados con edad ∈ {1d, 7d, 30d}.
2. Llama a `GET /v2/socialActions/{post_urn}` (LinkedIn).
3. Upsertea en la DB Notion.
4. Loggea `stage12.collected` al ops_log.

## 4. Correlación engagement ↔ voice_match (hipótesis)

Una vez que `📈 Métricas post-publish` tenga ≥30 datapoints, se puede
calcular Pearson(`voice_match_score`, `engagement_rate_n7`). Hipótesis:

* **Si correlación > 0.3** → `voice_match` es predictor útil; mantener
  el threshold actual.
* **Si correlación ≈ 0** → `voice_match` mide otra cosa (probablemente
  ortografía / coherencia formal, no resonancia con audiencia); habría
  que recalibrar el writer-voice eval.
* **Si correlación < 0** → señal de que el "voice match" sobreestima
  posts demasiado conservadores; revisar el prompt del writer.

Este análisis NO se ejecuta automáticamente — requiere revisión
humana periódica (mensual) y vive en `evals/` como notebook.

## 5. Qué NO entra en Hilo 6

* El job `stage12_engagement_collector` (Hilo 8).
* La DB Notion `📈 Métricas post-publish` (Hilo 8).
* Cualquier consumo de la API de LinkedIn más allá de `POST /v2/ugcPosts`.
* Modificación de la página `Pipeline Editorial — Métricas` actual:
  los gaps de §2 quedan documentados aquí pero **no** se implementan en
  este PR.

## 6. Roadmap de iteración

| Hilo  | Entrega                                                    | Status      |
|-------|------------------------------------------------------------|-------------|
| H6    | publish_guard + dry-run JSON contract + idempotency        | este PR     |
| H6.1  | `collect_ops_log_metrics` + render en dashboard            | follow-up   |
| H6.2  | `published_history` métricas en dashboard                  | follow-up   |
| H8    | `stage12_engagement_collector` + DB Notion                 | future      |
| H9    | Notebook de correlación voice_match ↔ engagement           | future      |
