---
id: "2026-07-02-002"
title: "Piloto Graphify F1–F4 — instalación local, grafo, gold-set A/B, decisión GO/NOGO"
status: review
assigned_to: copilot
created_by: cursor
priority: medium
sprint: graphify-pilot
created_at: "2026-07-02"
updated_at: "2026-07-02T21:15"
---

## Objetivo

Ejecutar el piloto local de Graphify sobre `umbral-agent-stack` y producir una decisión GO / GO parcial / NOGO firmada por David (G-GR-1), según el plan y las directrices predefinidas.

## Contexto

- Evaluación: `docs/ops/graphify-obsidian-eval-2026-07-02.md` (UAS-GRAPHIFY-OBSIDIAN-EVAL-v0.2)
- Plan + matriz de escenarios: `docs/ops/graphify-pilot-plan-2026-07-02.md` (UAS-GRAPHIFY-PILOT-PLAN-v1)
- Gold-set: evaluación §3 (10 preguntas con respuesta verificada)
- `.graphifyignore` propuesto: evaluación §9

## Precondiciones

- [ ] G-GR-0 firmado (David pega MEGAPROMPT Copilot Windows)
- [ ] Umbral de coste fijado por David
- [ ] No es el día del cutover Azure (7-jul)

## Criterios de aceptación

- [ ] F1: `graphify --version` OK (global via uv tool; nada en pyproject)
- [ ] F2: `.graphifyignore` creado ANTES de la primera pasada; grafo generado con `--backend azure`; auditoría de seguridad `leaks=0`; coste anotado
- [ ] F3: gold-set 10 preguntas brazo A (graph-first) y brazo B (baseline) con registros por pregunta
- [ ] F4: variables P/C/S/U/O calculadas; escenario S1–S8 identificado; directriz R* aplicada; veredicto en board firmado por David
- [ ] Evidencia en `C:\coord-ag-evidence\graphify-pilot\`
- [ ] Solo `.graphifyignore` (+ docs) commiteados; `graphify-out/` jamás

## Kill-switches (no negociables)

- Fuga de secretos → R0: STOP + purge + máx 1 reintento
- Máx 2 pasadas totales de generación
- Timebox 14 días desde G-GR-0 → si no, `blocked: no priorizado`
- Nada en VPS; sin `graphify install`; sin hooks

## Log

### [cursor] 2026-07-02
Tarea creada. Plan y matriz de escenarios en `docs/ops/graphify-pilot-plan-2026-07-02.md`. Pendiente de firma G-GR-0 por David.

### [cursor] 2026-07-02 20:10
Azure: creado `oai-umbral-agents-prod` + deployment `gpt-4.1-mini` (100 RPM).
Graphify F1–F2 ejecutados localmente: graph 10414 nodes, cost ~$3.52, leaks=0.
Resultados: `docs/ops/graphify-pilot-results-2026-07-02.md`. Copilot continúa F3–F4.

### [copilot] 2026-07-02 21:15
F3–F4 completados en Windows (rama `copilot/graphify-pilot-f1-f4`):
- Gold-set A/B: **A (graph-first) 8.0/10** (29 queries, 1 read, ~38s) vs **B (baseline) 9.5/10** (~20 búsquedas, ~2.2s). Detalle: `C:\coord-ag-evidence\graphify-pilot\goldset-results.md`.
- Seguridad: re-audit leaks=0 (F3 y post-`graphify update`).
- O: `graphify update` AST-only 75.7s (ligera), pero infla nodos 10.4k→20k sin etiquetas semánticas; regen canónica = pasada LLM completa.
- Hallazgo: `runbooks/` = 0 nodos en grafo F2 (gap por chunks 429) → costó 0.5 en A-Q9.
- F4: P alta · C ok ($3.53) · S limpio · **U nula/negativa** · O ligera → **S7 → R6**.
- Veredicto propuesto: `GRAPHIFY_PILOT_GO_PARTIAL | goldset=8/10 | cost=$3.53 | leaks=0 | escenario=S7 | directriz=R6` — uso local opcional, sin skill/AGENTS.md/artefactos compartidos; revisión 30 días.
- **Pendiente: firma G-GR-1 de David** → al firmar, pasar status a done y registrar veredicto final en board.
