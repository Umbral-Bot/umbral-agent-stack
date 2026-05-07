# INPUTS — Contrato de entrada `rick-linkedin-writer`

> **Status:** design-only. Define qué consume el agente en cada Stage. Implementación viva: `scripts/discovery/stage5_rank_candidates.py` (Stage 5) y `scripts/discovery/stage6_aec_combine.py` (Stage 6 stub).

## Stage 5 — Ranking determinístico (input)

### 1. SQLite items candidatos

**Source:** `~/.cache/rick-discovery/state.sqlite` tabla `discovered_items`.

**Filtro:** `WHERE promovido_a_candidato_at IS NOT NULL AND ranking_score IS NULL` (default; opcional `--rerank` para re-rankear todo).

**Schema relevante:**

| Columna | Tipo | Uso en ranking |
|---|---|---|
| `url_canonica` | TEXT PK | Identidad del item |
| `referente_id` | TEXT | Lookup de `referente_priority` |
| `referente_nombre` | TEXT | Logging / reasoning trace |
| `canal` | TEXT | `youtube`, `rss`, `web_rss`, `linkedin`, `otros` (afecta `referente_priority`) |
| `titulo` | TEXT | Input principal de `keyword_match` |
| `publicado_en` | TEXT (ISO8601) | Input de `recency_bonus` |
| `contenido_html` | TEXT | Texto adicional para `keyword_match` (stripped) |

**Columnas nuevas que el script agrega vía `ALTER TABLE` idempotente:**

- `ranking_score REAL` — score ∈ [0, 1].
- `ranking_reason TEXT` — JSON con breakdown por peso.
- `ranking_at TEXT` — ISO8601 timestamp del ranking.

### 2. Configuración de keywords AEC

**Source:** `config/aec_keywords.yaml`

```yaml
weights:
  w1_core_aec: 0.4
  w2_adyacente: 0.3
  w3_recency: 0.2
  w4_referente: 0.1

buckets:
  core_aec: [...]
  adyacente: [...]
  voz_david: [...]   # Reservado para Stage 6/7 (no usado en Stage 5 v0)
```

### 3. CLI flags

```
--db PATH                    # default ~/.cache/rick-discovery/state.sqlite
--config PATH                # default config/aec_keywords.yaml
--top-n INT                  # default 10
--rerank                     # re-rankea items con score existente
--commit                     # escribe ranking_score/reason/at; default dry-run
--report-dir PATH            # default reports/
--seed INT                   # determinismo, no usado (heurística pura)
```

### 4. Perfil David (implícito en config)

El "perfil David" se materializa via los buckets `core_aec`, `adyacente`, `voz_david` en `config/aec_keywords.yaml`. **No hay archivo de perfil separado**: cualquier ajuste de calibración pasa por editar el YAML.

## Stage 6 — Combinación AEC (input)

> **Stub hoy. Documentado para que la fase LLM tenga contrato claro.**

### 1. Top-N de Stage 5

JSON shape (idéntico al output de Stage 5, ver `OUTPUTS.md`):

```json
{
  "items": [
    {
      "url_canonica": "...",
      "ranking_score": 0.87,
      "ranking_reason": {...},
      "titulo": "...",
      "referente_nombre": "...",
      "is_aec": true
    }
  ]
}
```

### 2. Catálogo AEC adicional

Para items **no-AEC**, Stage 6 debe poder consultar items AEC alternativos del mismo `top-N` (o del `top-N*2`) para evaluar puente.

### 3. Decisión de combinar

Output del LLM debe incluir:

- `combine: true | false`
- Si `true`: `partner_url`, `bridge_type` ∈ `{mecanismo, problema, consecuencia_operativa, contraste}`, `bridge_justification` (1-2 frases).
- Si `false`: `transformation_path` (cómo aterrizar el item solo, en voz David).

## Stage 7 — Candidato Notion (input)

> **Pendiente. No implementado en este PR.**

Recibe la salida de Stage 6 + perfil de voz David + schema `Publicaciones` (DB ID `e6817ec4698a4f0fbbc8fedcf4e52472`) y produce el payload final tipo `editorial-candidate-payload` (ver `rick-editorial/ROLE.md` §"Output contract").

## Validación de inputs

`stage5_rank_candidates.py` debe:

1. Fallar limpio si `~/.cache/rick-discovery/state.sqlite` no existe (exit 2 + mensaje).
2. Fallar limpio si `config/aec_keywords.yaml` está malformado (exit 3 + mensaje).
3. Tolerar `titulo IS NULL`, `contenido_html IS NULL`, `publicado_en IS NULL` (score = 0 en esos componentes, log warning).
4. Tolerar 0 items (exit 0, escribe report vacío).
