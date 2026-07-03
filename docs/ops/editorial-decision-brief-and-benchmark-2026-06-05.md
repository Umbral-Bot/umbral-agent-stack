# Editorial — Decision Brief + Benchmark (2026-06-05)

- **Veredicto:** `BENCHMARK_EDITORIAL_VALIDATED` (ChatGPT 2026-06-05) · repo: `evals/editorial/benchmark-umbral-voice-v1.yaml`
- **Owner lead:** Cursor · **Benchmark voz:** ChatGPT (asesor externo) · **Implementación:** Codex + Rick QA
- **Gate:** David no ve copy final hasta pasar benchmark + decision brief completo

## Problema detectado (CAND-002)

La premisa existe en propiedad Notion `Premisa`, pero la página mezcla 124+ bloques (fuentes, matriz, QA, política) sin un **bloque de decisión** arriba. `Fuente primaria` / `Fuente referente` vacías en DB. David no puede decidir en 2 minutos: premisa → por qué → fuentes → objetivo → copies.

## CAND-002 — Premisa canónica (una frase)

> **En AEC, más herramientas de IA no garantizan más valor. El cuello de botella es organizacional: roles, procesos y criterio de revisión no están diseñados para absorber la velocidad que la tecnología ya ofrece.**

**Claim principal (inferencia editorial, no hecho):** La barrera principal para capturar valor de IA en AEC no parece ser la falta de herramientas, sino la falta de preparación organizacional.

**Ángulo:** Capacidad vs preparación (`pattern_synthesis`).

## CAND-002 — De dónde salió (trazabilidad mínima)

| Capa | Qué | Dónde |
|------|-----|-------|
| Señal de entrada | 25 referentes curados por David | DB Referentes, vista `71d3f67e…` |
| Fuentes analizadas | The B1M, The Batch, Marc Vidal, Aelion | Body CAND-002 + `docs/ops/cand-002-source-driven-flow.md` |
| Citables en público | The B1M (original_article), DeepLearning.AI/The Batch (analysis_source) | Política atribución |
| Solo discovery interno | Marc Vidal, Aelion/Ivan Gomez | No citar como autoridad en copy |
| Pipeline | rick-orchestrator → rick-qa (pass) → Notion manual | `docs/ops/cand-002-notion-draft-result.md` |

## Objetivo comercial (CAND-002)

| Objetivo | Intensidad | Notas |
|----------|------------|-------|
| Visibilidad / posicionamiento | **Alta** | awareness, tesis sectorial |
| Confianza técnica | Media | voz sobria, sin hype |
| Venta directa | **Baja** | sin CTA comercial duro |
| Conversión embudo | Baja v1 | sin lead magnet en esta pieza |

---

## Estructura obligatoria en Notion (Decision Brief)

Toda candidata en `Publicaciones` debe tener **esta secuencia en el cuerpo**, antes de matrices largas:

```markdown
## 1. Premisa (decisión en 10 segundos)
[1-2 frases. La tesis que justifica publicar.]

## 2. Por qué ahora
[Señal externa o gap de conversación — 2-3 bullets]

## 3. Fuentes y confianza
| Fuente | Rol | Citable en público | Claim que soporta |
|--------|-----|-------------------|-------------------|
| ... | primary / discovery / contextual | sí / no | ... |

**Fuente primaria (propiedad DB):** [URL o org]
**Fuente referente (propiedad DB):** [DB Referentes / selección David]

## 4. Relación con mi visión / pilares
- Pilar Umbral tocado: [Automatización empática | Puentes digitales | Citizen dev AECO | BIM+IA aplicado]
- Conexión con oferta: [consultoría | Umbral BIM | docencia | ninguna directa]

## 5. Objetivo de la pieza
| Objetivo | Prioridad | KPI suave |
|----------|-----------|-----------|
| visibilidad | alta/media/baja | ... |

## 6. Redacciones por canal (solo tras benchmark)
### LinkedIn — variante seleccionada
[copy]

### X — variante seleccionada
[copy]

## 7. Qué NO hacer todavía
🛑 No marcar gates. No publicar.

## 8. Evidencia / anexo (colapsable mental)
Matriz extracción, QA runs, alternativas descartadas → debajo o subpágina.
```

### Propiedades DB requeridas antes de `Revisión pendiente`

| Propiedad | Obligatoria source-driven |
|-----------|---------------------------|
| `Premisa` | sí |
| `Claim principal` | sí |
| `Ángulo editorial` | sí |
| `Fuente primaria` | sí (o `claim_type=opinión`) |
| `Fuente referente` | recomendado |
| `Objetivo comercial` | **nuevo** — select multi: visibilidad, posicionamiento, confianza, venta, comunidad |
| `claim_type` | **nuevo** — evidencia / inferencia / hipótesis / opinión |
| `ready_for_human_review` | **nuevo** — checkbox (solo QA/operador) |

---

## Pipeline: nada llega a David sin benchmark

```text
Fase 0 — Intake + Decision Brief (sin copy público)
Fase 1 — AEC framing (escenas operativas, límites de claim)
Fase 2 — Generación N variantes LinkedIn (N≥3, internas)
Fase 3 — Benchmark automático (evals/editorial + smoke tests)
Fase 4 — Benchmark ChatGPT (voz David, anti-patrones IA)
Fase 5 — Communication director selecciona 1 variante
Fase 6 — Rick QA (pass obligatorio)
Fase 7 — Operador registra en Notion (Decision Brief + 1 copy por canal)
Fase 8 — David: gate 1
```

**Regla:** Fases 2-6 ocurren **antes** de que David abra la página para decidir. La página Notion se crea/actualiza en Fase 7.

---

## Benchmark editorial (repo + ChatGPT)

### A. Repo-side (Codex / evals)

- Casos: `evals/editorial/gold-set-minimum.yaml`
- Dimensiones: `evals/editorial/dimensions.yaml`
- Smoke LinkedIn: `docs/ops/editorial-linkedin-quality-smoke-tests.md`
- Umbral mínimo por variante: **promedio ≥ 0.70**, ninguna dimensión < 0.50, `anti_ai_slop` pass

### B. ChatGPT-side (calibración voz David)

Benchmark validado por ChatGPT con:
- Guía Editorial y Voz de Marca (si accesible)
- Memoria de estilo del usuario
- Lista anti-patrones IA (ver abajo)
- 3 variantes internas → puntúa → elige o rechaza todas

### Anti-patrones IA (fail automático en benchmark)

- "En el mundo actual…"
- "No es solo X, es Y" / "No es esto, es esto otro"
- "Aquí es donde entra…"
- "capturar valor", "impacto" sin aterrizaje (salvo 1 uso calibrado)
- "preparación organizacional" repetido >2 veces sin concreción
- "equipos AI-native" sin escena AEC en párrafo 1-2
- Em dash en copy público
- Hook abstracto ("el problema real es el criterio operativo")
- Mini-ensayo (>1 idea central)
- Pregunta retórica + respuesta inmediata

### PASS patterns (referencia)

Ver `editorial-linkedin-quality-smoke-tests.md` PASS-001 a PASS-004.

---

## Prompts operativos

Ver sección "Prompt pack" al final — entregados en conversación Cursor para copy-paste.

## Referencias

- `docs/ops/cand-002-source-driven-flow.md`
- `docs/ops/editorial-source-attribution-policy.md`
- `docs/ops/editorial-agent-flow.md`
- `docs/ops/editorial-wave2-plan-2026-06-04.md`
- `notion/schemas/publicaciones.schema.yaml`
