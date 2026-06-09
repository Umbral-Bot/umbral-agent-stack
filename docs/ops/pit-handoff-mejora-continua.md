# PIT — Handoff de mejora continua (improvement-supervisor)

- **Status:** v1 (PIT-1 spec) — 2026-06-09.
- **Decisión David:** el handoff a mejora continua es un **proceso documentado** con revisión humana — **no** hay auto-merge de prompts/skills. Ninguna propuesta de mejora cambia el runtime por sí sola.

---

## 1. Qué captura

Cada torneo PIT produce, además del resultado de producto, señal sobre el **propio sistema**: prompts de lane que confunden, columnas kanban que se saltean, KPIs mal definidos, gates que friccionan de más o de menos. Ese material se canaliza, no se pierde ni se aplica en caliente.

## 2. Flujo

```text
torneo cerrado
  └─► pit_outcome_report.yaml § improvement_handoff.proposals[]   (escribe Rick)
        └─► improvement-supervisor (revisión asíncrona, NO bloquea el cierre)
              ├─ clasifica: prompt | skill | proceso | contrato/schema
              ├─ descarta lo anecdótico (1 torneo ≠ patrón)
              └─► propuesta concreta como PR contra el repo
                    └─► revisión + merge HUMANO (David / judge normal del repo)
```

Reglas:

1. **Origen único:** las propuestas nacen en `improvement_handoff.proposals[]` del [outcome report](../../openclaw/workspace-templates/pit-vault/templates/pit_outcome_report.yaml). Una mejora que no está ahí no entra al ciclo (evita lore oral).
2. **Umbral de patrón:** cambios a plantillas/prompts canónicos (`ROLE.template.md`, SKILL.md, schemas) requieren señal en ≥2 torneos **o** un fallo claro de guardrail en 1. Excepción: correcciones de seguridad, siempre.
3. **Vía PR, siempre:** la propuesta aterriza como PR normal del repo (las plantillas canónicas viven en el repo, no en el vault). Sin PR no hay cambio.
4. **Sin auto-merge:** ni Rick ni el improvement-supervisor mergean. Gate humano estándar.
5. **Versionado de plantilla:** si cambia `ROLE.template.md` o el SKILL, anotar en el PR qué torneos motivaron el cambio (trazabilidad outcome → mejora).

## 3. Roles

| Rol | Hace | No hace |
|---|---|---|
| Lane efímera | señala fricciones en `notes.md` de su iteración | proponer cambios de sistema |
| Rick | consolida fricciones → `improvement_handoff.proposals[]` | editar plantillas en caliente |
| improvement-supervisor | clasifica, filtra, redacta el PR de mejora | mergear |
| David | aprueba/rechaza el PR | — |

## 4. Relación con PIT-7

PIT-7 (revisión general de procesos post-construcción) consume los `improvement_handoff` de todos los torneos corridos hasta entonces y audita el sistema completo con el checklist del [índice de procesos](pit-process-index.md). Este handoff es el flujo continuo; PIT-7 es la auditoría de cierre de fase.
