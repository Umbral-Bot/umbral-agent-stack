# Stage 7.5 multiformat — inventario para la decisión (PKG-MACRO-P5-S75-T1, 2026-08-14)

**GO de David (orquestador):** INVENTARIO. No mergear a main. No borrar la rama
KEEP. No tocar OpenClaw ni cron.

Q13 (entrevista 2026-08-13) fijó: **merge con tests o kill antes del
2026-08-27**. Este pack es el que junta la evidencia para esa decisión. **No la
toma.** Las tres opciones quedan abiertas para el orquestador.

Todo lo de abajo se midió en esta sesión sobre un **worktree detached de sólo
lectura** de `origin/rick/stage7_5-multiformat`. La rama no se tocó: ni push, ni
checkout, ni rebase, ni merge.

## 1. La rama

| | |
|---|---|
| SHA | `a263539884627ea12184ca540ea7200f1fc739c2` — **confirmado, no cambió** |
| Commits únicos vs `main` | **7** |
| `main` por delante | **399** |
| Merge-base | `f808edb1` — **2026-05-08**, hace ~3 meses |

Los 7 commits son un experimento coherente y cerrado: 6 prompts → fixtures →
writer con `FORMATS` → evaluator con `--format` → 31 tests → driver real →
runbook.

## 2. Blobs: `main` vs rama

Comparación blob a blob, no triple-dot. Importa la distinción: el triple-dot
compara contra el merge-base y marca como `A` archivos que **`main` sí tiene**
(el runbook y el report json aparecen ahí como añadidos, y no lo son).

| Path | Estado | UNIQUE_REAL | Evidencia |
|---|---|:--:|---|
| `prompts/rick/blog-system.md` | MISSING | **sí** | 2.921 B en la rama, ausente en `main` |
| `prompts/rick/blog-user.md` | MISSING | **sí** | 746 B |
| `prompts/rick/linkedin-share-system.md` | MISSING | **sí** | 2.514 B |
| `prompts/rick/linkedin-share-user.md` | MISSING | **sí** | 954 B |
| `prompts/rick/linkedin-standalone-system.md` | MISSING | **sí** | 3.172 B |
| `prompts/rick/linkedin-standalone-user.md` | MISSING | **sí** | 689 B |
| `scripts/discovery/run_stage7_5_multiformat_real.py` | MISSING | **sí** | 6.288 B, driver de la eval real |
| `tests/discovery/test_stage7_5_multiformat.py` | MISSING | **sí** | 19.350 B, los 31 tests |
| `scripts/discovery/stage7_5_copy_writer.py` | DIFFERENT | **sí** | `main` 1.260 L vs rama 1.433 L |
| `scripts/discovery/eval_stage7_5_copy.py` | DIFFERENT | **sí** | `main` 1.373 L vs rama **564 L** |
| `tests/discovery/fixtures/stage7_5_proposals.json` | DIFFERENT | **sí** | `main` 97 L vs rama 132 L |
| `tests/discovery/fixtures/stage7_5_golden_copies.json` | DIFFERENT | **sí** | `main` 76 L vs rama 89 L |
| `docs/discovery/stage7_5-multiformat-runbook.md` | DIFFERENT | no | `main` 166 L vs rama 156 L: `main` es el mismo doc **+ la cabecera HISTÓRICO** |
| `reports/stage7_5_multiformat_real_v1.json` | **IDENTICAL** | no | mismo blob `44894606` |

**12 de 14 son UNIQUE_REAL.** Los dos que no lo son son justamente los que
`main` ya archivó en su momento.

> Corrección al reconteo: la fila 13 estimaba el writer en ~1.111 L (`main`) y
> ~1.272 L (rama). Los números reales hoy son **1.260** y **1.433**. `main`
> siguió moviéndose.

## 3. El writer: fork, no additive

`main` tiene 6 símbolos que la rama **no**:

```
NON_REPARABLE_HR   _import_evaluator          build_repair_instruction
estado_live_name   build_voice_source_payload generate_copy_with_voice_retry
```

Eso es el ciclo de reparación de **voice-v3** completo. La rama aporta 10
símbolos propios (`FORMATS`): `build_format_prompt`, `generate_format`,
`process_proposal_pack`, `validate_format_copy`, `parse_formats_arg`,
`_persist_format_result`, `_read_prompt_file`, `PROMPT_DIR_DEFAULT`, `_H1_RE`,
`_HASHTAG_RE`.

De las **27 funciones comunes**, 23 son idénticas y **4 divergen** — y divergen
en la dirección que importa, con la rama más corta porque parte de la base vieja:

| Función | `main` | rama |
|---|--:|--:|
| `process_proposal` | 295 L | 180 L |
| `build_copy_prompt` | 63 L | 28 L |
| `main` | 133 L | 177 L |
| `write_copy_to_notion` | 26 L | 20 L |

**Riesgo de clobber: SÍ.** Un merge del archivo entero le sacaría a producción
`generate_copy_with_voice_retry` y `build_repair_instruction`, además de
revertir `process_proposal` a una versión 115 líneas más corta. `main` tocó ese
archivo en **4 commits** desde el merge-base.

El evaluador está peor: `main` 1.373 L vs rama **564 L**, y `main` tiene ~40
símbolos que la rama no — `check_v3_hr2_unsupported_fact` .. `hr5`,
`_score_david_voice_fit`, `verify_source`, `score_batch`, y los diccionarios
AECO. La rama aporta 7 (`SCORERS_BY_FORMAT`, `score_copy_blog/share/standalone`,
`_format_overrides`, `_maybe_swap_url_rule`, `FORMAT_NAMES_EVAL`). **Traer ese
archivo borraría 809 líneas de `main`.**

## 4. Los tests corren — y pasan

```
31 passed in 0.99s
```

Corridos **dentro del worktree**, con `PYTHONPATH` apuntando ahí. El repo está
instalado como editable (`__editable__.umbral_agent_stack-0.4.0.pth` → apunta a
`/home/rick/umbral-agent-stack`), así que el aislamiento se **verificó** antes de
correr, no se supuso:

```
scripts.discovery.stage7_5_copy_writer.__file__ → <worktree>/scripts/... ✓
```

Esto corrige el `dudoso` de la fila 13: **la rama no está rota.** Está
desactualizada, que es un problema distinto. Los 31 tests importan los dos
módulos enteros (`stage7_5_copy_writer` y `eval_stage7_5_copy`), así que no son
portables por separado: dependen de que `FORMATS` exista del otro lado.

## 5. `main` ya archivó el experimento

Confirmado: `docs/discovery/stage7_5-multiformat-runbook.md` en `main` abre con
**«Estado: HISTÓRICO»** y **«DO NOT MERGE»** (PKG-UAS-P1-2-KEEP3-ARCHIVE-RUNBOOK,
2026-08-06), y dice explícitamente que el pipeline vigente es un archivo por
canal. Verificado en `main`: `blog-copy-system.md`, `linkedin-copy-system.md`,
`x-copy-system.md`, `newsletter-copy-system.md` — y **ninguno** de los 6 prompts
`FORMATS` de la rama.

El report json es **el mismo blob** en los dos lados. La evidencia del
experimento ya está en `main`; lo que sigue sólo en la rama es el código.

## 6. Recomendación

**Kill de la rama, conservando los 6 prompts y el report como registro.**

El razonamiento en una línea: el valor del experimento —la evidencia— ya está en
`main` y archivado como histórico; lo único que quedaría por traer es código que
`main` superó en dos archivos (el evaluador de la rama tiene 809 líneas menos y
le falta voice-v3 entero), y `main` ya decidió otro pipeline hace tres meses.

Las otras dos opciones, honestamente:

- **Cherry-pick additive sin el writer** — viable pero de valor bajo: los 8
  paths MISSING entran limpios, pero los 31 tests importan ambos módulos, así
  que sin portar `FORMATS` al writer y al evaluador de `main` no corren. Se
  quedaría con prompts y un driver que nada ejecuta.
- **Merge con rebase** — es el más caro y el único que puede romper producción:
  hay que rehacer a mano 4 funciones divergentes del writer y reconciliar un
  evaluador que perdió 809 líneas, contra un `main` que avanzó 399 commits.
  Sólo tiene sentido si David quiere el pipeline multi-formato **de vuelta**, y
  esa es una decisión de producto, no de deuda técnica.

**Este pack no ejecuta ninguna.** La sentencia sobre la rama KEEP la decide el
orquestador con David, antes del 2026-08-27.

---

Evidencia en `~/.coord-ag-evidence/pkg-macro-p5-s75-t1/`. Worktree de lectura
eliminado al cerrar el pack; la rama `rick/stage7_5-multiformat` quedó en
`a2635398`, intacta.
