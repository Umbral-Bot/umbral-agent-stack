# Postmortem — PIT-DEV `pit-dev-ifc-viewer` (2026-07-04)

- **Status:** cerrado con acciones — quality gates implementados (PR quality-gates-20260704).
- **Decisión David (2026-07-04):** el **cierre administrativo queda** (TRACE_COMPLETE,
  Drive, gate literal); el **fulfillment de producto se RECHAZA**. NO se abre
  slice de integración con el zip ganador actual.
- **Vault (VPS, evidencia read-only):** `~/umbral-pit-vault/pit/pit-dev-ifc-viewer/`
  (`outcome/pit_outcome_report.yaml`, `deliverables/`,
  `judge/scorecards/judge-1--lane-performance-open-stack.json`).

---

## 1. Qué pasó

El torneo PIT-DEV `pit-dev-ifc-viewer` cerró **proceduralmente verde**:
trazabilidad `TRACE_COMPLETE`, deck subido a Drive, gate literal de David
registrado. Sin embargo, el producto entregado era **inaceptable**: el visor
IFC del winner usa un parser casero que degrada archivos IFC reales a **cajas
fallback** (sin tessellation real, sin picking 3D — limitaciones admitidas en
el propio README del winner), y ninguna pieza del pipeline lo detectó.

El sistema optimizó para cerrar el proceso, no para entregar producto.

## 2. Fallas observadas → root cause → gate nuevo

| # | Falla (evidencia vault) | Root cause | Gate que lo bloquea desde ahora |
|---|---|---|---|
| 1 | "50 USD" engañoso: `budget_usd: 50` (techo) leído como gasto; `usd_estimated_spent: 0.0`; `tokens_total: not_reported` | Nadie corría el collector de tokens; el outcome/deck/pack no distinguían techo de gasto | `pit_collect_tokens.py --update-outcome` puebla `budget.tokens_total` + `usd_estimated_spent` (+`pricing_source`); el deliver PIT-DEV **FALLA** con `tokens_total_not_reported`; deck y Telegram dicen "gasto estimado X / techo Y", nunca "0/50" |
| 2 | KPIs falsamente verdes: todos los KPI con `synthetic_share: 1.0` (solo fixture/tests) | Ningún check exigía señal no sintética para cerrar | Gate QA producto (`pit_dev_human_qa_gate.py`): IFC real >100 KB (denylist `mini-site.ifc`), ≥1 elemento parseado, sin error fatal — registrado en `human_qa` del outcome |
| 3 | Visor no usable: IFC real → cajas fallback; upload UI sin validar en juez | La "verificación funcional" fue fixture 4.4 KB + `curl` HTTP 200 + tests offline | `human_qa.real_ifc_upload` obligatorio (auto con playwright o evidencia validada); deliver **FALLA** sin `QA_PASS`/`QA_SKIPPED_WITH_REASON` |
| 4 | Deck vacío: `pit-dev-ifc-viewer-outcome-deck.pptx` con 7 slides y **0 imágenes** (`ppt/media/` vacío) | El builder solo generaba texto; no había evidencia visual que embeber | `human_qa.screenshots` exige ≥3 PNG reales en `deliverables/qa-screenshots/`; `pit_build_outcome_deck.py` los embebe como slides (soporte `image_path` en `document.create_presentation`); deliver re-verifica los PNG en disco |
| 5 | Jueces demasiado laxos: `meets_functional_spec: true` con fixture 4.4 KB + HTTP 200 + 10/10 tests offline | El scorecard no pedía evidencia del input usado | Scorecard v2: `meets_functional_spec: true` **exige** `functional_evidence {real_input_used: true, input_description}`; `validate_scorecard` lo invalida sin eso (check duro + jsonschema); ROLE.judge-dev endurecido |
| 6 | Cierre procedural leído como aceptación de producto | El outcome no tenía un campo de fulfillment de producto separado del cierre admin | `fulfillment_decision.product_fulfillment` (accepted \| rejected \| pending_validation) **obligatorio** en PIT-DEV para el deliver; visible en deck y Telegram ("Producto: fulfillment X · QA Y") |

## 3. Qué NO falló

- La cadena procedural (runner, trazabilidad, gate literal, Drive, comms
  policy) funcionó como estaba diseñada. El problema fue de **diseño de
  gates**, no de ejecución: "verde procedural" no medía producto.
- El README del winner fue honesto sobre sus limitaciones — la información
  existía, ningún gate la consumía.

## 4. Decisiones registradas

1. Cierre admin de `pit-dev-ifc-viewer` **queda** (no se reabre el torneo).
2. `fulfillment_decision.product_fulfillment: rejected` para
   `pit-dev-ifc-viewer` — backfill en el vault VPS (ver §5).
3. **No** se abre slice de integración con el zip ganador actual.
4. Todo torneo PIT-DEV futuro pasa por los 4 gates nuevos (billing truth,
   QA producto, fulfillment explícito, jueces con evidencia) — fail-closed en
   `pit_deliver_telegram_pack.py`.

## 5. Backfill pendiente en la VPS (operador, NO automático)

El vault vive en la VPS; este repo solo define los gates. Tras el deploy:

```bash
# 1. Ledger + billing truth retroactivo del torneo incidentado (best-effort):
python scripts/pit/pit_collect_tokens.py --pit-id pit-dev-ifc-viewer --update-outcome

# 2. Registrar el rechazo de producto en el outcome (edición manual, 2 claves):
#    fulfillment_decision.product_fulfillment: rejected
#    fulfillment_decision.product_fulfillment_reason: >
#      Visor inusable con IFC reales (fallback boxes, sin tessellation ni
#      picking); KPIs 100% sintéticos; deck sin evidencia visual. Decisión
#      David 2026-07-04.

# 3. Sync de templates/skills al workspace vivo (schema scorecard v2 + SKILL).
```

## 6. Referencias

- Gates: [`pit_deliver_telegram_pack.py`](../../scripts/pit/pit_deliver_telegram_pack.py) ·
  [`pit_dev_human_qa_gate.py`](../../scripts/pit/pit_dev_human_qa_gate.py) ·
  [`pit_collect_tokens.py`](../../scripts/pit/pit_collect_tokens.py)
- Jueces: [`pit-dev-judge-protocol.md`](pit-dev-judge-protocol.md) ·
  [`judge-scorecard.schema.json`](../../openclaw/workspace-templates/pit-vault/templates/judge-scorecard.schema.json) (v2)
- Proceso: SKILL [`product-innovation-tournament`](../../openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md) §Post-torneo
- Visión PIT-DEV: [`pit-dev-mode-vision-2026-07-03.md`](pit-dev-mode-vision-2026-07-03.md)
