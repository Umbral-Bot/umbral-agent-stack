# PIT-DEV — Agente de trazabilidad (post-torneo)

- **Status:** v1 (PIT-DEV FASE 5) — 2026-07-03.
- **Decisión David (visión §6):** un agente de trazabilidad revisa post-torneo
  que TODO el proceso quedó trazable. Gaps → informe a Rick → Rick propone la
  estrategia de trazabilidad automática (entra a mejora continua).
- **Plantilla de rol:** [`ROLE.traceability.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.traceability.md).
- **Script ejecutable:** [`pit_traceability_check.py`](../../scripts/pit/pit_traceability_check.py)
  — lo corre el agente **o el operador** directamente.

---

## 1. La cadena verificada

```text
spec → lanes.yaml → agents.yaml → workspace init → iterations
  (egress.jsonl + test_report.json) → announce.md → judge scorecards
  → outcome report → deck deliverables
```

Cada eslabón recibe un estado:

| Estado | Significado |
|---|---|
| `PRESENT` | el artefacto existe y es parseable/válido |
| `MISSING` | el artefacto no existe |
| `UNVERIFIABLE` | existe pero no valida (JSON roto, schema inválido, egress malformado) |

## 2. Ejecución

```bash
# Operador o agente (post-outcome/deck):
python scripts/pit/pit_traceability_check.py --pit-id <pit_id> \
  --vault-path "$PIT_VAULT_PATH"

# Spawn del agente vía runner (fase separada, post-outcome):
python scripts/pit/pit_dev_run.py <spec.yaml> --phase traceability \
  --gate "ok, arranca"
```

- Output: `pit/<pit_id>/traceability/report.md` (tabla de eslabones + gaps) y
  veredicto **`TRACE_COMPLETE`** | **`TRACE_GAPS(<lista>)`**.
- Exit codes: `0` completa · `1` gaps · `2` error de entrada.
- La fase corre **post-outcome**: outcome report y deck son eslabones de la
  cadena, así que el agente solo tiene sentido cuando Rick ya consolidó.

## 3. Con TRACE_GAPS: el agente NO arregla nada

1. El agente **informa a Rick** (announce `TRACE_VERDICT=TRACE_GAPS(...)` +
   report en el vault). No recrea artefactos, no completa announces, no edita
   el outcome: diagnóstico ≠ reparación.
2. **Rick redacta la propuesta** de estrategia de trazabilidad automática
   (qué eslabón falló, cómo se automatiza su captura) y la registra vía el
   handoff de mejora continua existente
   ([`pit-handoff-mejora-continua.md`](pit-handoff-mejora-continua.md) §5) —
   proposals del outcome report, revisión humana, vía PR, sin auto-merge.

## 4. Eficiencia (loop con mejora continua)

El análisis de trazabilidad se acompaña del análisis de **eficiencia** del
torneo (tokens/costo por lane con
[`pit_collect_tokens.py`](../../scripts/pit/pit_collect_tokens.py), tiempo por
fase desde `run-metrics.json`, comparativa vs torneo anterior) — detalle en
[`pit-handoff-mejora-continua.md`](pit-handoff-mejora-continua.md) §5. Rick
rinde ambos a David en el cierre (plantilla ≤15 líneas del SKILL §PIT-DEV).

## 5. Referencias

- Visión PIT-DEV: [`pit-dev-mode-vision-2026-07-03.md`](pit-dev-mode-vision-2026-07-03.md)
- Runner (fase traceability): [`pit_dev_run.py`](../../scripts/pit/pit_dev_run.py)
- Token ledger (P6): [`pit-p6-token-ledger-20260622.md`](pit-p6-token-ledger-20260622.md)
