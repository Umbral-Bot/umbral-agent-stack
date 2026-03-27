# 61 - Granola promotion candidates

> Inventario repo-side para decidir que reuniones raw siguen pendientes de capitalizacion y cuales ya no merecen lote manual.

## 1. Objetivo

`scripts/list_granola_promotion_candidates.py` existe para responder una pregunta simple antes de armar otro batch:

- que raw pages siguen siendo candidatas reales
- cuales ya fueron promovidas
- cuales son duplicados de una raw ya promovida
- cuales son smoke tests o ruido tecnico

Esto evita curar lotes a mano revisando siempre la misma cola.

## 2. Clasificaciones

El script clasifica cada raw page como una de estas:

- `candidate`
- `promoted`
- `duplicate_of_promoted`
- `smoke_or_test`

## 3. Reglas actuales

### `promoted`

Se usa cuando la URL de la raw page aparece ya en `URL fuente` de la DB humana curada.

### `duplicate_of_promoted`

Se usa cuando:

- hay mas de una raw page con el mismo par `titulo_normalizado + fecha`
- y una de esas raw pages ya aparece promovida

Esto cubre el caso actual del duplicado raw de `Reunion Con Jorge de Borago`.

### `smoke_or_test`

Se usa cuando el titulo parece claramente tecnico, por ejemplo:

- `smoke`
- `manual-watcher`
- `test`
- `prueba`

### `candidate`

Todo lo demas.

## 4. Uso

```powershell
python scripts/list_granola_promotion_candidates.py
python scripts/list_granola_promotion_candidates.py --json
```

## 5. Resultado observado al 2026-03-27

Estado final del inventario despues de limpiar duplicados operativos:

- `raw_count = 9`
- `candidate_count = 0`
- `promoted_count = 3`
- `duplicate_of_promoted_count = 0`
- `smoke_or_test_count = 6`

Los tres casos productivos quedaron absorbidos:

- `Konstruedu`
- `Reunion Con Jorge de Borago`
- `Asesoria discurso`

Y la cola restante visible corresponde solo a smoke tests historicos.

Conclusion operativa:

- no queda un lote productivo pendiente hoy
- el siguiente lote depende de nuevas reuniones raw reales
- la cola ya no tiene duplicados operativos abiertos

## 6. Nota sobre deduplicacion curada

El inventario mira la capa raw contra la curada usando `URL fuente`, no el titulo de la sesion curada.

Eso importa por dos razones:

- una sesion curada puede haber sido renombrada por el humano sin romper el inventario
- un payload live con encoding roto ya no deberia crear una sesion curada nueva si el raw ya estaba promovido, porque `granola.promote_curated_session` ahora resuelve primero por `URL fuente`

## 7. Referencias

- `scripts/list_granola_promotion_candidates.py`
- `tests/test_list_granola_promotion_candidates.py`
- `docs/56-granola-promote-curated-session.md`
- `docs/60-granola-operational-batch-runner.md`
