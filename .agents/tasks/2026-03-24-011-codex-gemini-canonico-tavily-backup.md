---
id: "2026-03-24-011"
title: "Gemini canonico, Tavily backup y tracking de necesidad futura"
status: in_progress
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T10:05:00-03:00
updated_at: 2026-03-24T10:05:00-03:00
---

## Objetivo
Formalizar la decision operativa de discovery:

1. Gemini grounded search queda como backend canonico
2. Tavily queda como backup secundario y barato
3. Perplexity queda diferido solo si los casos reales muestran necesidad
4. dejar tracking minimo para contar cuantas veces `research.web` tuvo que salir de Gemini y caer a Tavily

## Contexto
- `2026-03-24-010` ya dejo Gemini primario en runtime y documentado el sizing para Perplexity
- falta aterrizar la decision final de negocio/operacion y dejar una señal cuantificable de necesidad futura

## Criterios de aceptacion
- [ ] Queda documentado que Gemini es el camino canonico y Tavily el backup secundario
- [ ] Perplexity queda explicitamente diferido como propuesta futura y no trabajo activo
- [ ] Se registra en el sistema cuantas veces `research.web` usa Tavily como fallback
- [ ] Hay tests para el tracking nuevo

## Log
### [codex] 2026-03-24 10:05
Tarea creada para capitalizar la decision operativa de provider routing y dejar tracking de fallback real.
