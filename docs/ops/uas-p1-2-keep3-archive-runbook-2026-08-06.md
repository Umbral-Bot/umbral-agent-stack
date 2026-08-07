# P1.2 — ARCHIVE de la fila 3 (runbook multiformato) — 2026-08-06

> **Pack:** PKG-UAS-P1-2-KEEP3-ARCHIVE-RUNBOOK · rama `claude/pkg-uas-p1-2-keep3-archive-runbook-20260806` · base `29d55338`
> **GO de David:** ARCHIVE del runbook (+ report opcional) en `main`; **KEEP_INDEFINITE** de la
> rama `rick/stage7_5-multiformat` (no borrar). Cero merge de writer/evals/prompts/tests.
> **Precede:** [uas-p1-2-orphan-keep3-2026-08-06.md](uas-p1-2-orphan-keep3-2026-08-06.md) (brief,
> fila 3).

---

## 1. Fuente

- Rama: `origin/rick/stage7_5-multiformat` @ `a2635398` — verificada viva en el SHA esperado.
- Método: `git checkout origin/rick/stage7_5-multiformat -- <2 paths>` (solo esos, no cherry-pick
  del commit completo, que también toca writer/evaluator/prompts/tests prohibidos).

## 2. Archivos traídos (exactamente 2)

| Archivo | Líneas | Decisión |
|---|---|---|
| `docs/discovery/stage7_5-multiformat-runbook.md` | 166 (156 originales + 10 de marcador) | Obligatorio, traído |
| `reports/stage7_5_multiformat_real_v1.json` | 3663 | Opcional — **incluido tras revisión** (ver §3) |

### 2.1 Evaluación del report JSON antes de incluirlo

- **Tamaño:** 195 KB / 3663 líneas — no enorme.
- **Estructura:** `{generated_at, model, gateway_url, formats, fixture_ids, temperatures,
  n_calls, elapsed_sec, aggregate_per_format_temp, rows[]}`. 36 filas, cada una con
  `fixture_id, model, copy_text, rules, score, hard_pass_ratio, soft_pass_ratio, error, format,
  temperature`.
- **`gateway_url`:** `http://127.0.0.1:18789` — localhost, sin valor sensible.
- **`model`:** `openclaw/main` — nombre genérico de alias, no una credencial.
- **`copy_text`:** copy sintético generado a partir de fixtures de prueba (ej. tema BIM
  hospitalario / clash detection) — contenido de marketing de ejemplo, no dato real de cliente
  ni PII.
- **Grep de patrones de secretos** (`api[_-]?key|token|secret|password|bearer|sk-|ghp_|ghs_`):
  única coincidencia es la cadena literal `"No marketing-slop tokens"` (descripción de una regla
  de evaluación de texto, no un secreto).

**Decisión: incluir el JSON completo** — es evidencia real del experimento (36 llamadas reales,
scores por formato/temperatura), sin PII ni secretos, tamaño manejable.

## 3. Marcador HISTÓRICO

El runbook lleva una nota al inicio (10 líneas) explicando: `main` no adoptó el enfoque
multi-formato (adoptó un archivo por canal), el report queda como evidencia del experimento, y el
código (writer/evaluator/tests) permanece solo en la rama, sin mergear.

El report JSON no lleva nota inline (es un archivo de datos, no un doc) — su condición de
"evidencia histórica" queda establecida por el runbook, que lo referencia y enlaza explícitamente.

## 4. Confirmación de exclusión

```
git diff --stat origin/main
→ docs/discovery/stage7_5-multiformat-runbook.md |  166 ++
  reports/stage7_5_multiformat_real_v1.json      | 3663 ++++++++++++++++++++++++
  2 files changed, 3829 insertions(+)

git diff origin/main -- scripts/discovery/stage7_5_copy_writer.py
→ (vacío — diff 0, no tocado)
```

Ninguno de los paths prohibidos (`stage7_5_copy_writer.py`, `eval_stage7_5_copy.py`,
`run_stage7_5_multiformat_real.py`, `prompts/rick/*`, `tests/discovery/test_stage7_5_multiformat.py`,
fixtures) aparece en `git status`.

## 5. Rama fuente `rick/stage7_5-multiformat`

**KEEP_INDEFINITE — no se borra.** A diferencia de RESCUE1 y de la fila 1 (PIT), esta rama
conserva código real (writer/evaluator/tests) que **no** se trajo a `main` por decisión
explícita — es la implementación completa del experimento, no solo su documentación. Borrarla
perdería ese código sin que nadie lo haya evaluado. Ningún `git push --delete` se ejecutó ni se
propone para esta rama.

## 6. Prohibido (respetado)

- Cero touch a `scripts/discovery/stage7_5_copy_writer.py` (confirmado diff 0).
- Cero touch a `eval_stage7_5_copy.py`, `run_stage7_5_multiformat_real.py`, `prompts/rick/*`,
  `tests/discovery/test_stage7_5_multiformat.py`, fixtures.
- Cero `git push --delete rick/stage7_5-multiformat`.
- Cero self-merge.
