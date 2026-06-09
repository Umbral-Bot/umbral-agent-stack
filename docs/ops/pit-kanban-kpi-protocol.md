# PIT — Protocolo Kanban + KPI

- **Status:** v1 (PIT-1 spec) — 2026-06-09.
- **Contratos:** [`docs/schemas/pit-spec-v1.schema.json`](../schemas/pit-spec-v1.schema.json) (entrada) + [`kpi-pack.schema.json`](../../openclaw/workspace-templates/pit-vault/templates/kpi-pack.schema.json) (salida por iteración).
- **Plantilla tablero:** [`kanban-lane.md`](../../openclaw/workspace-templates/pit-vault/templates/kanban-lane.md) (1 tablero por lane, en `pit/<pit_id>/lanes/<lane_id>/kanban/board.md`).
- **Visión:** [`product-innovation-tournament-vision-2026-06-09.md`](product-innovation-tournament-vision-2026-06-09.md).

---

## 1. Las 9 columnas canónicas

Los títulos son exactos — el estado del torneo se parsea de ellos. No renombrar, no reordenar, no añadir columnas en v1.

| # | Columna | Qué significa | Sale de la columna cuando |
|---|---------|---------------|---------------------------|
| 1 | `Backlog` | Trabajo identificado, sin empezar | la lane arranca la tarea |
| 2 | `Research` | Investigación según `research_profile` (academic / market_pain / competitive / mixed) | hay insumos suficientes para formular hipótesis |
| 3 | `Hypothesis` | Formulación de la hipótesis de la iteración | hipótesis registrada (variable + kpi_id + dirección) |
| 4 | `Prototype` | Construcción del prototipo (`prototype_output`: html v1) | prototipo navegable vía túnel + Mission Control |
| 5 | `KPI Track` | Medición de `kpi_achieved` contra `kpi_expected` | todas las mediciones de la iteración registradas |
| 6 | `Fulfillment` | Cálculo de `fulfillment_score` + escritura del `kpi_pack.json` | kpi_pack válido contra schema |
| 7 | `Review` | Lane + supervisor revisan: ¿hipótesis validada? ¿iterar o cerrar? | decisión tomada (próxima iteración → vuelve a Research/Hypothesis; cierre → Done) |
| 8 | `Done` | Iteración (o lane completa) cerrada | — |
| 9 | `Stuck` | Bloqueo que requiere a Rick o David | el bloqueo se resuelve (vuelve a su columna) o escala al outcome report |

**Regla Stuck:** una tarjeta que pasa más de 1 iteración completa en `Stuck` se reporta obligatoriamente en `pit_outcome_report.yaml` (sección `stuck_log`).

**Gate visual Magnific:** la generación visual (4:3) solo puede pedirse con la tarjeta en `Prototype` o con hipótesis ya validada — nunca en Research/Hypothesis. Ver [`pit-visual-magnific.md`](pit-visual-magnific.md).

---

## 2. Hipótesis ↔ KPI

Una hipótesis PIT **no** es una idea suelta: es **la variable clave que la lane cree correlacionada a un KPI del spec**, en forma falsable:

```text
Si cambio <variable> (ej. taps hasta completar el check-in),
espero mover <kpi_id> (ej. checkin_completion) hacia <dirección> (increase).
```

- Cada iteración tiene exactamente **una** hipótesis activa (campo `hypothesis` del kpi_pack).
- `hypothesis.kpi_id` debe existir en `kpi_definitions` del pit_spec.
- Al cerrar la iteración, `hypothesis.validated` se marca `true` (correlación observada), `false` (refutada) o `null` (inconclusa). Una hipótesis refutada **es resultado válido** — alimenta la siguiente iteración.
- `hypothesis_seed` del spec (si David lo dio) es solo el punto de partida de la iteración 1.

---

## 3. Fórmula fulfillment_score (0–1)

Implementación ejecutable: `compute_fulfillment()` en [`scripts/pit/pit_spec_validate.py`](../../scripts/pit/pit_spec_validate.py) (testeada en `tests/test_pit_spec_validate.py`).

Por cada KPI `i` con peso `w_i` (default 1.0):

```text
direction = increase:
    score_i = clamp01(kpi_achieved / kpi_expected)        # kpi_expected > 0
direction = decrease:
    score_i = 1.0                       si kpi_achieved <= kpi_expected
    score_i = clamp01(kpi_expected / kpi_achieved)        en caso contrario

fulfillment_score = Σ(w_i · score_i) / Σ(w_i)   redondeado a 2 decimales
```

Propiedades:

- **Acotado [0, 1]:** superar el objetivo no infla el score por encima de 1 (evita premiar overshoot de vanity metrics).
- **decrease sin división por cero:** `kpi_achieved = 0` con objetivo > 0 cae en la rama `<= expected` → 1.0.
- **increase exige `kpi_expected > 0`** (lo valida el spec); decrease admite objetivo 0 (solo se cumple con achieved 0).
- Los pesos vienen del spec (`kpi_definitions[].weight`) y se copian al kpi_pack para trazabilidad.

El **fulfillment de cierre de lane** es el `fulfillment_score` del kpi_pack de la **última iteración** (no el promedio histórico): mide dónde terminó el prototipo, no el camino. La serie completa queda en `iterations/*/kpi_pack.json` para el juez.

---

## 4. Ciclo por iteración (2–10 según spec)

```text
Research → Hypothesis → Prototype → KPI Track → Fulfillment → Review
   ▲                                                            │
   └────────────── siguiente iteración (n+1) ◄──────────────────┘
```

Por iteración `n`, la lane produce en `pit/<pit_id>/lanes/<lane_id>/iterations/<n>/`:

1. `kpi_pack.json` — válido contra `kpi-pack.schema.json` (**obligatorio**).
2. `prototype/` — fuentes del prototipo html (obligatorio desde la primera iteración que llega a Prototype).
3. Notas de research/decisiones en markdown (recomendado).

**Cierre de lane** (paralelo product del `PR_URL=` de D3, ver contraste en la [skill](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md)). El announce final de la lane termina con tres líneas literales:

```text
PROTOTYPE_URL=<url túnel/Mission Control>
KPI_PACK=pit/<pit_id>/lanes/<lane_id>/iterations/<última>/kpi_pack.json
FULFILLMENT=<score 0-1>
```

Sin esas tres líneas verificables la lane es `lane_incomplete`, aunque el agente reporte éxito (misma regla dura que docs/79 §4.1).

---

## 5. Señales y personas sintéticas

- Personas sintéticas: **permitidas** para señales tempranas, **siempre etiquetadas** (`kpis[].synthetic: true` + `synthetic_personas.labeled: true` en el kpi_pack — el schema no permite `labeled: false`).
- El juez pondera señales sintéticas como direccionales, nunca como validación de mercado.
- Ningún dato personal real en el vault; reglas de secretos en [`pit-vault-layout.md`](pit-vault-layout.md).
