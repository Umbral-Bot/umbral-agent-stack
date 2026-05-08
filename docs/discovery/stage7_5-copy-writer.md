# Stage 7.5 — LLM copywriter for LinkedIn (transformer core)

Pipeline position:

```
Stage 6 (LLM combinator → idea editorial)
  ↓
Stage 7 (Notion page con body raw)
  ↓
Stage 8 (hero image)
  ↓
Stage 7.5 (THIS) — LLM copywriter rellena `Copy LinkedIn` y setea Estado='En revisión'
  ↓ (David revisa y autoriza desde Notion)
Stage 9 (LinkedIn draft → publish, sólo cuando Estado='Autorizado')
```

Stage 7.5 es el transformer core: lee la idea editorial de la página de
Notion (titular + ángulo + body raw + fuente) y produce un texto
publicable de LinkedIn vía el gateway local de OpenClaw. Nunca publica;
sólo escribe a Notion y deja el row listo para review humano.

## Architecture

- **Entrada:** filas en `proposals` (SQLite `state.sqlite`) con
  `notion_page_id IS NOT NULL` y `image_status='ok'`.
- **LLM transport:** OpenAI-compatible Chat Completions contra
  `http://127.0.0.1:18789/v1/chat/completions` (gateway local OpenClaw),
  modelo por defecto `openclaw/main` (alias). Token leído de
  `~/.openclaw/openclaw.json` o env `OPENCLAW_GATEWAY_TOKEN`.
- **Cache:** SQLite en `~/.cache/rick-discovery/llm_cache.sqlite`,
  shared con Stage 6 pero con prefijo de key `stage7_5:` para evitar
  colisiones. TTL 7 días.
- **Salida:** PATCH `/v1/pages/{page_id}` en Notion seteando
  `Copy LinkedIn` (rich_text fragmentado en segmentos ≤ 2000 chars) y
  `Estado='En revisión'`. Más persistencia local en `proposals`
  (`copy_status='copy_ready'`, `copy_text`, `copy_model_used`,
  `copy_cost_usd_estimate`, `copy_last_attempt_at`).

## Schema (state.sqlite — ALTER TABLE idempotente)

| Column | Type | Semantics |
|---|---|---|
| `copy_status` | TEXT | `pending` \| `copy_ready` \| `failed` \| `skipped_no_image` |
| `copy_last_attempt_at` | INTEGER | epoch seconds del último intento |
| `copy_last_error` | TEXT | razón de fallo (ver "Failure modes") |
| `copy_text` | TEXT | cache local del último copy (humano o LLM) |
| `copy_model_used` | TEXT | modelo que generó el copy |
| `copy_cost_usd_estimate` | REAL | costo estimado del run (telemetría) |

Migración corre al inicio de `main()` (`ensure_copy_columns`) — segura
de re-correr.

## Schema validation Notion (live, NO auto-fix)

Al inicio del run, el script trae el data source vía
`/v1/data_sources/{ds_id}` (default `dc833f1f-07d9-49d0-82ec-fdfad1c808c4`)
y verifica:

1. La propiedad `Copy LinkedIn` existe y es de tipo `rich_text`.
2. La propiedad `Estado` existe y tiene la opción `En revisión`
   (válido tanto para `select` como `status`).

Si falla cualquiera de las dos: cada row se marca `copy_status='failed'`
con error explícito (`notion_property_missing:Copy LinkedIn`,
`notion_estado_option_missing:En revisión`) y NO se llama al LLM. Hilo C
maneja el cambio de schema; este stage nunca lo modifica.

## Validaciones del output LLM

Antes de escribir a Notion, el copy debe cumplir:

- `400 ≤ len(copy) ≤ 3000` chars (tope LinkedIn UGC = 3000).
- Contiene la URL de fuente como sub-string (salvo `--allow-no-source`).
- No contiene tokens prohibidos: `[TODO]`, `__`, `<` (placeholders típicos
  de outputs LLM mal terminados).

Falla de validación → `copy_status='failed'`, `copy_last_error=...`,
NO escribe a Notion.

## Cost guard

- Hard abort del row si `len(system_prompt) + len(user_prompt)` excede
  `10_000` tokens estimados (≈ 40k chars). Las páginas reales son
  pequeñas (body truncado a 3000 chars), así que esto sobra.
- `copy_cost_usd_estimate` se calcula con tarifas configurables
  (`--cost-per-1k-input-usd`, `--cost-per-1k-output-usd`,
  default $0.005 / $0.015 — Azure gpt-5.4 class, ajustable).

## CLI flags

| Flag | Default | Función |
|---|---|---|
| `--max-copies N` | 3 | Cap por run |
| `--dry-run` | off | Lista candidatos, NO llama LLM ni escribe Notion |
| `--force` | off | Ignora `copy_status` (procesa también `copy_ready`) |
| `--force-overwrite` | off | Sobrescribe `Copy LinkedIn` no vacío en Notion |
| `--allow-no-source` | off | Relaja validación de URL fuente |
| `--model <alias>` | `openclaw/main` | Alias del gateway |
| `--proposal-id N` | — | Procesa sólo ese row |
| `--state-db PATH` | `~/.cache/rick-discovery/state.sqlite` | |
| `--cache-db PATH` | `~/.cache/rick-discovery/llm_cache.sqlite` | |
| `--ops-log PATH` | `~/.config/umbral/ops_log.jsonl` | |
| `--gateway-url URL` | `http://127.0.0.1:18789/v1/chat/completions` | |
| `--publicaciones-ds-id UUID` | `dc833f1f-…` | |
| `--cost-per-1k-input-usd` | 0.005 | Tarifa estimada |
| `--cost-per-1k-output-usd` | 0.015 | Tarifa estimada |

## Selección de candidatos

```sql
WHERE notion_page_id IS NOT NULL
  AND image_status = 'ok'
  AND ( copy_status IS NULL
        OR (copy_status = 'failed'
            AND (copy_last_attempt_at IS NULL
                 OR copy_last_attempt_at < now - 24h)) )
ORDER BY id ASC
LIMIT --max-copies
```

`--force` quita el guard de `copy_status` y `copy_last_attempt_at`.

## Skip silencioso si Notion ya tiene copy

Si `Copy LinkedIn` viene no vacío del page response, el row se marca
local como `copy_status='copy_ready'` con `copy_text` = el copy humano,
y se loggea `stage7_5.skip_existing_copy`. Esto evita pisar trabajo
manual cuando un humano ya armó el copy.

`--force-overwrite` ignora ese skip.

## Eventos en `ops_log.jsonl`

| Event | Cuándo |
|---|---|
| `stage7_5.input.loaded` | Tras leer candidatos al inicio |
| `stage7_5.skip_existing_copy` | Page tiene Copy LinkedIn no vacío |
| `stage7_5.cost.aborted` | Hard abort por cost guard |
| `stage7_5.cache.hit` | Cache LLM golpeado |
| `stage7_5.validation.failed` | Output LLM invalido |
| `stage7_5.copy_written` | Notion patcheado OK |

Ejemplo de línea exitosa:

```json
{"ts":"2026-05-08T14:30:12.123456+00:00","event":"stage7_5.copy_written","proposal_id":1,"notion_page_id":"3595f443-fb5c-8169-97df-e85af74a25da","copy_len":1742,"model":"openclaw/main","cost_usd":0.001543}
```

## Failure modes

| `copy_last_error` | Causa | Acción |
|---|---|---|
| `notion_property_missing:Copy LinkedIn` | DB sin esa propiedad | Hilo C: agregar property rich_text |
| `notion_estado_option_missing:En revisión` | Estado sin esa opción | Hilo C: agregar opción al select/status |
| `cost_guard_aborted:N>10000` | Body raw muy grande | revisar Stage 7 / truncar más en `build_copy_prompt` |
| `validation_failed:too_short:...` | LLM devolvió < 400 chars | re-prompt o `--force` |
| `validation_failed:too_long:...` | LLM > 3000 chars | re-prompt |
| `validation_failed:missing_source_url` | LLM no incluyó la URL | re-prompt o `--allow-no-source` |
| `validation_failed:prohibited_token:...` | LLM emitió placeholder | re-prompt |
| `llm_error:...` | gateway down / timeout | revisar `openclaw status` |
| `notion_write_http_4XX/5XX` | Notion API error | revisar `NOTION_API_KEY` y reintentar |

Failures con `copy_status='failed'` se reintentan automáticamente luego
de 24 h; antes de eso, `--force` los rehace.

## Prompt placeholder (Hilo B)

```
SYSTEM: Sos Rick, copywriter editorial de Umbral BIM. Voz: directa, AECO,
sin jerga corporativa. Idioma: español rioplatense neutro.
Hashtags: 3-5 relevantes (#BIM #AECO #Construccion etc según disciplinas).

USER: Convertí esta idea editorial en un post LinkedIn publicable.
Hook ≤120 chars, cuerpo 600-1800 chars, atribución a fuente al final,
hashtags al final.
  Titular: {titular}
  Ángulo: {angulo}
  Disciplinas: {disciplinas}
  Body raw: {body_truncado_3000_chars}
  Fuente: {fuente_url}
Devuelvé SOLO el texto del post (sin meta-comentarios).
```

Punto de extensión: `build_copy_prompt(proposal_row, page_props)`.
Hilo B reemplaza el cuerpo de esa función para refinar voz, restricciones
y formato sin tocar el resto del pipeline. La firma de retorno es
`(system_prompt, user_prompt)`.

## Operaciones típicas

```bash
# Listar candidatos sin llamar LLM ni escribir Notion
python scripts/discovery/stage7_5_copy_writer.py --dry-run --max-copies 10

# Generar copies para los próximos 3 candidatos
set -a; source ~/.config/openclaw/env; set +a
python scripts/discovery/stage7_5_copy_writer.py

# Re-procesar un row específico (después de fix manual)
python scripts/discovery/stage7_5_copy_writer.py --proposal-id 4 --force

# Sobrescribir un copy humano (peligroso)
python scripts/discovery/stage7_5_copy_writer.py --proposal-id 4 --force-overwrite
```

## Troubleshooting

- **`ERROR: NOTION_API_KEY not set`**: cargar env con
  `set -a; source ~/.config/openclaw/env; set +a`.
- **`ERROR: no gateway token available`**: idem, o exportar
  `OPENCLAW_GATEWAY_TOKEN` directamente.
- **`cannot fetch Publicaciones schema`**: probablemente el ds_id está
  mal o el token no tiene permiso; correr
  `curl -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2025-09-3
  https://api.notion.com/v1/data_sources/<ds_id>` para diagnosticar.
- **Notion 429**: el cliente reintenta con backoff exponencial hasta 5
  veces. Si persiste, bajar el throughput con `RATE_LIMIT_SLEEP_S` o
  espaciar runs.
- **LLM gateway 5xx**: `openclaw status` y `openclaw models status`.
  Si el modelo principal está caído, pasar `--model openclaw/fallback`
  (o el alias correspondiente).

## Tests

`tests/discovery/test_stage7_5_copy_writer.py` — 21 tests cubriendo
selección, retry, validaciones, schema gaps, cost guard, dry-run, cache,
chunking rich_text, retry HTTP 429 y migración idempotente.

```bash
python -m pytest tests/discovery/test_stage7_5_copy_writer.py -v
```
