# Product Innovation Tournament (PIT) — Visión y decisiones

- **Status:** v1 — 2026-06-09. Consolidado en PIT-1 (este doc no existía en `main`; integra las decisiones David de la sesión 2026-06-09).
- **Owner de visión:** David. **Orquestación:** Rick / OpenClaw.
- **Spec PR:** PIT-1 (`claude/feat-pit-1-spec-magnific-43`).
- **Relacionados:** [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md) (D3 code — intacto), [`d35-tournament-judge-kit-2026-06-04.md`](d35-tournament-judge-kit-2026-06-04.md), [`copilot-cli-autonomy-vision-roadmap.md`](../copilot-cli-autonomy-vision-roadmap.md) (broker futuro), [`ADR-011`](../adr/ADR-011-pit-product-tournament-scope.md) (draft).

---

## 1. Qué es PIT

El formato torneo de Umbral (1 problema → N lanes paralelas → 1 winner) aplicado a **producto** en vez de código: las lanes no compiten escribiendo PRs sobre `main`, compiten **investigando, formulando hipótesis, prototipando y midiendo KPI** en iteraciones cortas. El juez no lee diffs: lee `fulfillment_score` y evidencia de KPI.

```text
David ──"ok, arranca"──► Rick (parser + broker)
                            │ pit_spec.yaml validado
                            ▼
                  spawn N agentes EFÍMEROS (2–5)
            lane-a          lane-b          lane-c
              │ × iteration_count (2–10):
              │ Research → Hypothesis → Prototype → KPI Track → Fulfillment → Review
              ▼
   cierre lane: PROTOTYPE_URL= + KPI_PACK= + FULFILLMENT=
                            │
                            ▼
              judge (fulfillment + scorecard) ──gate David──► outcome report
                            │
              handoff mejora continua + archive + (PIT-7 audit)
```

## 2. Dos modos de torneo (decisión)

| Modo | Salida de lane | Protocolo |
|---|---|---|
| **D3 code** | `PR_URL` verificable con `gh pr view` | docs/79 (sin cambios — PIT no lo rompe) |
| **PIT product** | `PROTOTYPE_URL` + `KPI_PACK` + `FULFILLMENT` | este doc + [`pit-kanban-kpi-protocol.md`](pit-kanban-kpi-protocol.md) |

Ambos comparten las primitivas OpenClaw (spawn desde `main` standalone, G-D1b, ISSUE-001, 2–5 lanes) y el principio de cierre verificable: la lane está completa solo con artefactos verificables, nunca por `finalStatus=success`.

## 3. Decisiones David (2026-06-09) — registro canónico

1. **Dos modos:** D3 code (PR_URL) | PIT product (PROTOTYPE_URL + KPI).
2. **`iteration_count` variable 2–10**, siempre desde input David.
3. **`budget_usd` SIEMPRE desde input David** — el runtime no aplica default silencioso.
4. **Invocación:** NL + alias `/torneo_producto` → mismo parser → gate literal **"ok, arranca"** antes de spawn ([skill](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md)).
5. **Agentes efímeros nuevos por torneo** — Rick genera prompts/skills/accesos y los desactiva al cierre ([generator](pit-ephemeral-agent-generator.md)).
6. **Research tiers:** `academic | market_pain | competitive | mixed`.
7. **Obsidian:** vault **`umbral-pit-vault` separado** del vault personal pull-only; writes acotadas a `pit/` ([layout](pit-vault-layout.md)).
8. **Kanban 9 columnas:** Backlog, Research, Hypothesis, Prototype, KPI Track, Fulfillment, Review, Done, Stuck ([protocolo](pit-kanban-kpi-protocol.md)).
9. **KPI:** `kpi_expected`/`kpi_achieved` con unidad variable; `fulfillment_score` 0–1 (fórmula ejecutable en `scripts/pit/pit_spec_validate.py`).
10. **Hipótesis** = variable clave correlacionada a un KPI (falsable, una por iteración).
11. **Handoff mejora continua** (improvement-supervisor): proceso documentado, **no** auto-merge de prompts ([handoff](pit-handoff-mejora-continua.md)).
12. **PIT-7:** revisión general de procesos post-construcción (checklist en [process index](pit-process-index.md)).
13. **Preview:** túnel + Mission Control, **NO URL pública**.
14. **Personas sintéticas:** permitidas, **siempre etiquetadas**.
15. **Prototipo v1: html**; variable `prototype_output: html | figma | both`.
16. **Plantillas:** "guarda como plantilla PIT `<nombre>`" → `templates/pit-<nombre>.yaml` del vault.
17. **Magnific PIT: `aspect_ratio` default "4:3"** — canónico Umbral junto con editorial LinkedIn y blog hero ([visual](pit-visual-magnific.md), [estilo v1](umbral-bim-magnific-visual-style-v1.md)).

## 4. Contratos (PIT-1, este PR)

| Pieza | Archivo |
|---|---|
| Spec de entrada | [`docs/schemas/pit-spec-v1.schema.json`](../schemas/pit-spec-v1.schema.json) + validador [`scripts/pit/pit_spec_validate.py`](../../scripts/pit/pit_spec_validate.py) |
| Ejemplo canónico | [`examples/pit-salud-mental-pilot.yaml`](../../examples/pit-salud-mental-pilot.yaml) (N=3, iter=5, html, 200 USD, mixed) |
| KPI por iteración | [`kpi-pack.schema.json`](../../openclaw/workspace-templates/pit-vault/templates/kpi-pack.schema.json) |
| Tablero | [`kanban-lane.md`](../../openclaw/workspace-templates/pit-vault/templates/kanban-lane.md) |
| Cierre de torneo | [`pit_outcome_report.yaml`](../../openclaw/workspace-templates/pit-vault/templates/pit_outcome_report.yaml) |
| Skill Rick/Telegram | [`product-innovation-tournament/SKILL.md`](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md) |
| Rol lane efímera | [`pit-lane-agent/ROLE.template.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.template.md) |
| Vault | [`pit-vault-layout.md`](pit-vault-layout.md) + `pit_vault_init.sh` + `pit_vault_check.py` |

## 5. Roadmap PIT

| Hito | Contenido | Estado |
|---|---|---|
| **PIT-1** | Spec + contratos + kanban/KPI + skill + vault + Magnific 4:3 (este PR) | **en PR** |
| **PIT-2** | Research sandbox: `pit.research_fetch` (interface/stub primero, sin runtime pesado), fuentes por tier | post-merge |
| **PIT-3** | Deploy pit-vault VPS + sync plantillas + check verde | post-merge (con D3.5b) |
| **PIT-4** | Generador de agentes efímeros ejecutable (wiring OpenClaw) | a definir |
| **PIT-5** | Broker visual Magnific operativo (Rick) + Mission Control preview | a definir |
| **PIT-6** | Primer torneo piloto real (`pit-salud-mental-pilot`) con gate David | requiere PIT-2..5 |
| **PIT-7** | Auditoría general de procesos post-construcción (checklist §PIT-7 del [índice](pit-process-index.md)) | tras PIT-6 |

## 6. Guardrails de visión

- PIT **no** modifica el protocolo D3 ni sus skills; convive como modo hermano.
- Nada de runtime pesado en PIT-1: `pit.research_fetch` y el wiring de spawn son interface/doc hasta PIT-2/PIT-4.
- Todos los gates humanos de Umbral aplican: spawn (`ok, arranca`), fulfillment/winner (frase David), publicación (nunca automática desde PIT).
