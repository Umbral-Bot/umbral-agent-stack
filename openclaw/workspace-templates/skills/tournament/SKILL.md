---
name: tournament
description: >-
  Tournament multi-agent pattern: exploración divergente con desarrollo completo
  + debate informado + consolidación por juez. Rick recibe un desafío, identifica
  2-5 enfoques distintos, los desarrolla completamente en paralelo, ejecuta un
  debate donde cada enfoque argumenta contra los rivales, y consolida con tabla
  comparativa + recomendación. Usa cuando "comparar enfoques", "explorar opciones",
  "analizar alternativas", "torneo de ideas", "qué camino tomar",
  "pros y contras de N opciones", "debate entre opciones".
  NO usar para torneo real, torneo de implementación, competir implementaciones
  en ramas o benchmark de código real — eso va por github-ops.
metadata:
  openclaw:
    emoji: "\U0001F3C6"
    requires:
      env:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
---

# Tournament Skill (Ideacional)

Rick ejecuta un torneo de ideas: exploración divergente → debate → consolidación.

**Este torneo es puramente textual.** No toca Git, no crea ramas, no genera código, no ejecuta validación. Produce texto comparativo y un veredicto.

> **¿David pidió torneo real, torneo de implementación, competir implementaciones en ramas o benchmark de código?** → Usar `github.orchestrate_tournament` desde la skill `github-ops`. Ver `docs/69-tournament-over-branches-runbook.md`.

## Cuándo usar

- David pide comparar múltiples enfoques para resolver un problema.
- Se necesita una decisión informada entre alternativas con trade-offs reales.
- Un problema complejo tiene más de un camino viable y no es obvio cuál elegir.

## Task

```json
{
  "task": "tournament.run",
  "input": {
    "challenge": "¿Cómo implementar autenticación SSO para UmbralBIM.io?",
    "num_approaches": 3,
    "debate_rounds": 1
  }
}
```

## Parámetros

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `challenge` | str | **requerido** | El problema o decisión a explorar |
| `num_approaches` | int | 3 | Número de enfoques distintos (2-5) |
| `approaches` | list[str] | auto | Nombres predefinidos de enfoques; si se omite, Rick los descubre |
| `models` | list[str] | ["azure_foundry"] | Modelos para cada contestante (rota si hay menos que `num_approaches`) |
| `judge_model` | str | primer modelo | Modelo para el juez/consolidación |
| `temperature` | float | 0.9 | Temp alta para diversidad en desarrollo |
| `max_tokens` | int | 2048 | Presupuesto de tokens por llamada LLM |
| `debate_rounds` | int | 1 | Rondas de debate (0 para omitir) |

## Flujo interno

1. **Descubrimiento** — Si no se pasan `approaches`, el LLM identifica N
   enfoques fundamentalmente distintos para el challenge.
2. **Desarrollo** — Cada enfoque se desarrolla completamente en una llamada
   LLM separada, con system prompt que fuerza el foco en ESE enfoque.
3. **Debate** — Cada contestante recibe las propuestas rivales y argumenta
   por qué su enfoque es superior, reconociendo ventajas genuinas del rival.
4. **Juez** — Consolida todo en tabla comparativa con columnas:
   Approach | Strengths | Weaknesses | Risk | Fit. Declara ganador con nivel
   de confianza, o `ESCALATE` si los trade-offs son genuinos y cercanos.

## Respuesta

```json
{
  "challenge": "...",
  "approaches": [
    {"id": 1, "approach_name": "...", "proposal": "...", "model_used": "..."},
    {"id": 2, "approach_name": "...", "proposal": "...", "model_used": "..."},
    {"id": 3, "approach_name": "...", "proposal": "...", "model_used": "..."}
  ],
  "debate": [
    {"id": 1, "round": 1, "approach_name": "...", "rebuttal": "...", "model_used": "..."}
  ],
  "verdict": {
    "text": "... tabla + recomendación ...",
    "winner_id": 2,
    "escalate": false
  },
  "meta": {
    "total_llm_calls": 7,
    "total_duration_ms": 45000,
    "models_used": ["gpt-5.4"]
  }
}
```

## Variaciones multi-modelo

Para máxima diversidad, asignar modelos distintos a cada contestante:

```json
{
  "task": "tournament.run",
  "input": {
    "challenge": "Stack de frontend para el dashboard de UmbralBIM.io",
    "num_approaches": 3,
    "models": ["azure_foundry", "claude_pro", "gemini_pro"],
    "judge_model": "claude_opus"
  }
}
```

Esto genera propuestas desde GPT, Claude y Gemini — genuinamente divergentes
porque cada modelo tiene sesgos y fortalezas diferentes.

## Integración con preferencias

La idea futura es que las decisiones de David sobre qué enfoque elegir
alimenten una base de preferencias en Notion, que el juez consulte para
ajustar su criterio en futuros torneos.
