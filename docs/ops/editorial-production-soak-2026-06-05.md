# Editorial — Production soak end-to-end (2026-06-05)

- **Veredicto objetivo:** `EDITORIAL_PROD_SOAK_OK` | `EDITORIAL_PROD_SOAK_DEGRADED`
- **Propósito:** David evalúa un **resultado de producción desde cero**, no una página retocada manualmente.
- **Candidata nueva:** `CAND-PROD-001` (o `CAND-004` si secuencia numérica preferida)
- **No reemplaza CAND-002** — soak paralelo para comparar pipeline vs resultado manual.

## Realidad del stack (honesta)

| Capa | Estado hoy |
|------|------------|
| `rick-editorial` | design-only — **no** runtime activo |
| Producción real | `rick-orchestrator` + `rick-qa` + `rick-communication-director` (VPS OpenClaw) |
| Benchmark voz | ChatGPT asesor externo (`evals/editorial/benchmark-umbral-voice-v1.yaml`) |
| Variantes internas | Codex (repo `docs/ops/cand-*-variants-benchmark-*.md`) |
| Notion registro | Operador / Notion AI — **no** auto-write desde Rick aún |
| Worker `editorial.*` | Wave 2 — **no** implementado |

El soak valida el **flujo acordado**, no un botón único.

## Flujo producción (12 pasos)

```text
P0  David autoriza soak + tema/dedup
P1  Intake fuentes (Referentes DB o brief nuevo)
P2  rick-orchestrator → payload + Decision Brief YAML
P3  AEC framing + 3 variantes LinkedIn (orchestrator o Codex)
P4  Benchmark repo (evals + smoke + benchmark yaml)
P5  rick-qa: atribución
P6  rick-communication-director: voz (si copy público)
P7  rick-qa: voz + final
P8  ChatGPT: benchmark variantes → VARIANT_SELECTED
P9  Notion: nueva fila CAND-PROD-001 con Decision Brief template
P10 David revisa (premisa, fuentes, objetivo, copy) — gate 1 opcional
P11 Cursor: informe soak vs CAND-002
```

**Regla:** David **no** ve copy en Notion hasta P8 `VARIANT_SELECTED`.

## Tema sugerido CAND-PROD-001 (dedup vs CAND-002/003)

| CAND | Tesis |
|------|-------|
| CAND-002 | Capacidad vs preparación organizacional |
| CAND-003 | Criterio antes que automatización |
| **CAND-PROD-001** | **Trazabilidad y cierre de decisiones** antes de escalar IA en flujos BIM |

Ángulo distinto, misma DB Referentes permitida con dedup explícito.

## Criterios de éxito soak

| # | Criterio |
|---|----------|
| 1 | Decision Brief completo en Notion (secciones 1-7) sin edición manual de David |
| 2 | `Fuente primaria` poblada en propiedades |
| 3 | 3 variantes generadas; 1 seleccionada por benchmark |
| 4 | `rick-qa` final = pass o pass_with_changes resuelto |
| 5 | Copy sin anti-patrones FAIL del benchmark |
| 6 | Gates false; Estado = Revisión pendiente |
| 7 | Evidencia en `docs/ops/cand-prod-001-*` + run IDs OpenClaw |

## Gates David

```text
autorizo editorial production soak CAND-PROD-001
```

Opcional tema custom:

```text
autorizo editorial production soak CAND-PROD-001 tema: [tesis en una frase]
```

## Referencias

- `docs/ops/editorial-decision-brief-and-benchmark-2026-06-05.md`
- `docs/ops/editorial-agent-flow.md`
- `docs/ops/cand-003-source-driven-flow.md` (9 stages reference)
- `evals/editorial/benchmark-umbral-voice-v1.yaml`
