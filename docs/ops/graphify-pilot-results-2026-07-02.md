# Graphify pilot results — 2026-07-02 (F1–F4)

> F1–F2 por Cursor (preflight Azure + grafo). F3–F4 por Copilot Windows (Claude Fable 5).
> **Veredicto: `GRAPHIFY_PILOT_GO_PARTIAL | goldset=8/10 | cost=$3.53 | leaks=0 | escenario=S7 | directriz=R6`** — **G-GR-1 firmado por David 2026-07-02**: uso local opcional, sin skill/install/artefactos compartidos (R6+R7), revisión 30 días; gap `runbooks/` documentado sin re-generar.

## Azure provisioning ✅

| Item | Valor |
|------|--------|
| Recurso | `oai-umbral-agents-prod` @ `rg-umbral-agents-prod` |
| Endpoint | `https://oai-umbral-agents-prod.cognitiveservices.azure.com/` |
| Deployment | `gpt-4.1-mini` · capacity **100 RPM** |
| Doc | `docs/ops/azure-openai-umbral-agents-provisioning.md` |

## F1 ✅

- `graphify 0.9.5` via `uv tool install graphifyy[openai]`

## F2 ✅ (parcial aceptable)

| Métrica | Valor |
|---------|--------|
| `.graphifyignore` | creado en raíz |
| Pasada 1 | AST 651 code files |
| Pasada 2 | 686 docs semantic (retry tras subir quota) |
| Chunks fallidos | 2/23 (429 rate limit residual) |
| `graph.json` | 10 414 nodes · 19 184 edges · 882 communities |
| Coste est. | **USD 3.52** (< umbral USD 10) |
| Auditoría leaks | **0** (rg secret patterns en graph.json) |
| `GRAPH_REPORT.md` | generado (`graphify cluster-only`) |

Evidencia: `C:\coord-ag-evidence\graphify-pilot\` (logs run + retry)

## F3 — Gold-set A/B ✅ (Copilot Windows, 2026-07-02)

Mismas 10 preguntas (eval §3), misma sesión, brazo A primero. Detalle por pregunta en `C:\coord-ag-evidence\graphify-pilot\goldset-results.md`.

| Métrica | Brazo A (graph-first) | Brazo B (baseline grep/glob) |
|---------|----------------------|------------------------------|
| Score | **8.0/10** (6×1, 4×0.5) | **9.5/10** (9×1, 1×0.5) |
| Operaciones | 29 queries + 1 lectura | ~20 búsquedas, 0 lecturas |
| Tiempo total | ~38 s (~1.3 s/query) | ~2.2 s |
| Coste marginal | $0 (grafo ya pagado) | $0 |

Fallos A (0.5): Q3 (no surfaceó `docs/15` ni rate-limiting), Q5 (solo 1 de 4 archivos Notion Bridge), Q6 (ModelRouter solo via test node), Q9 (`runbooks/` = **0 nodos en grafo F2** — gap de cobertura, no de query). Fallo B (0.5): Q7 (granola no matchea por grep).

**Dónde A ganó:** Q7 — 1 query devolvió handlers exactos con línea + tests + vecindad (grep necesitó 3 pasadas y perdió granola). El valor real del grafo es la *vecindad relacional*, no la búsqueda puntual.

Seguridad F3: re-audit `graph.json` → **leaks=0** (patrones sk-/ghp_/bearer/AKIA/BEGIN y paths .env/sessions/auth-profiles = 0).

### Medición O — regen incremental

`graphify update .` (AST-only, sin LLM): **75.7 s** → O ligera. ⚠️ Side-effects: 10 414 → 20 025 nodos (indexó `openclaw/` 2 591, `runbooks/` 244 y tests que F2 había perdido), nuevos nodos sin etiqueta semántica (community numérica), graph.json 11.8→20.1 MB. `.graphifyignore` respetado (0 nodos de dirs excluidos). El update barato degrada consistencia semántica → la regen canónica sigue siendo pasada completa con LLM (~$3.5).

## F4 — Decisión ✅ (matriz plan §4)

| Var | Valor | Nivel |
|-----|-------|-------|
| P | 8.0/10 | **alta** (≥8) |
| C | $3.53 < $10 | **ok** |
| S | leaks=0 (F2 + F3 + post-update) | **limpio** |
| U | A: 8.0, 38 s, 30 ops · B: 9.5, 2.2 s, 20 ops | **nula/negativa** |
| O | 75.7 s AST-only | **ligera** |

**Escenario S7** (P alta · U nula) → **directriz R6**: GO parcial como techo — uso opcional por agente en local, **sin** skill, **sin** AGENTS.md, **sin** artefactos compartidos ni Obsidian obligatorio.

```
GRAPHIFY_PILOT_GO_PARTIAL | goldset=8/10 | cost=$3.53 | leaks=0 | escenario=S7 | directriz=R6
motivo=U-nula: baseline grep/glob fue más preciso (9.5 vs 8.0) y ~17× más rápido con $0;
el grafo solo aporta en exploración relacional (vecindad de handlers, impacto)
```

**Siguiente paso (plan §5, rama GO parcial):** revisión a **30 días** — si hubo uso real y valioso (registro cualitativo en board), reabrir F5–F7; si no → degradar a NOGO silencioso (desinstalar opcional). **G-GR-1 firmado por David (2026-07-02)**: PR entra en limpieza workspace (task `2026-07-02-006`); task 002 → done al merge.

### Hallazgos capitalizables

1. Gap de cobertura F2: `runbooks/` quedó fuera del grafo (2/23 chunks 429) — cualquier re-run debe verificar cobertura de dirs clave, no solo leaks.
2. `graphify query` ancla por keyword y devuelve vecindades enormes (77–314 nodos); el modo útil es `explain <nodo>` cuando conocés el nombre — exige conocer el repo, lo que erosiona el caso de uso onboarding.
3. `graphify path` mezcla aristas INFERRED ruidosas (7 hops irrelevantes en 2/2 usos).
4. `cost.json` no existe en graphify 0.9.5 — el coste sale del log de extract (`est. cost (~azure): $3.5209`).

## Notas F1–F2 (Cursor)

- Primera pasada falló 22/23 chunks con capacity=10 RPM; recreado deployment a 100 RPM.
- `gpt-4o-mini` deprecated en tenant; usado `gpt-4.1-mini` (2025-04-14).
