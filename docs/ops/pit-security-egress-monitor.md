# PIT-DEV — Security-egress monitor (rol seguridad por torneo)

- **Status:** v1 (PIT-DEV FASE 3) — 2026-07-03.
- **Decisión David (visión §3):** toda comunicación exterior de las lanes
  (búsquedas web, fetches) queda **monitoreada**: un agente exclusivo con rol
  de seguridad (o Rick) audita el log de egress por lane.
- **Plantilla de rol:** [`ROLE.security-monitor.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.security-monitor.md).
- **Primitivas ejecutables:** `parse_egress_file` / `consolidate_egress` /
  `security_verdict_state` en [`pit_dev_core.py`](../../scripts/pit/pit_dev_core.py).

---

## 1. El agente

- **1 agente efímero `<pit_id>-security` por torneo.** NO compite, NO escribe
  en lanes. Mismo ciclo de vida que los demás efímeros: registro → spawn →
  kill + desregistro al cierre (runner).
- **Write scope:** `pit/<pit_id>/security/` — ahí viven `egress_log.md`
  (análisis), `verdict.md` (veredictos) y `egress_ledger.jsonl` (consolidado).
- Supervisa **también a los jueces** (mismo mecanismo declarativo).

## 2. Contrato de egress (v1 pragmática)

Toda búsqueda/fetch externo de una lane se registra como evento:

```json
{"lane_id": "lane-<slug>", "iteration": 2, "url_or_query": "https://…", "purpose": "docs oficiales MCP", "timestamp": "2026-07-03T14:00:00Z"}
```

- **Las lanes DECLARAN su egress** en un archivo por iteración:
  `pit/<pit_id>/lanes/<lane_id>/iterations/<n>/egress.jsonl` (un evento JSON
  por línea). Iteración sin egress = sin archivo (o archivo vacío).
- **Los jueces declaran igual** en `pit/<pit_id>/judge/<judge_id>/egress.jsonl`
  (evento con `judge_id` en lugar de `lane_id`; `iteration` opcional).
- El runner **consolida mecánicamente** todo en
  `pit/<pit_id>/security/egress_ledger.jsonl` (`consolidate_egress`).
- El security agent **contrasta** lo declarado contra los logs reales
  disponibles: audit JSONL del broker (`copilot_cli.run`, metadata
  `pit_id`/`lane_id` — contrato P4) y logs del gateway si el operador los
  exporta. **Divergencia = flag** (egress real no declarado, propósito que no
  cierra, destino fuera de scope).

## 3. Veredictos

`pit/<pit_id>/security/verdict.md` — UNA línea literal por lane:

```text
lane-stdio-first: EGRESS_CLEAN
lane-http-first: EGRESS_FLAGGED(fetch a dominio no declarado; 3 eventos sin purpose)
```

Efectos (fail-closed):

- **El judge NO corre sobre una lane `EGRESS_FLAGGED`** sin decisión explícita
  de Rick (+ gate David si es grave). En el runner: la lane queda fuera del
  set elegible; incluirla exige `--judge-flagged-lanes "<motivo>"` y el motivo
  queda registrado en `run-metrics.json`.
- **Sin `verdict.md` no hay fase judge** (veredicto ausente ≠ limpio).

## 4. Límite del rol (importante)

El enforcement duro de red sigue siendo del **operador VPS** (L3/L4,
`--network=none` del sandbox Docker del broker): este rol es **AUDITORÍA +
veredicto, no firewall**. El security agent no abre ni pide abrir ningún gate
de runtime. La skill tampoco (regla existente P5).

## 5. Referencias

- Visión PIT-DEV: [`pit-dev-mode-vision-2026-07-03.md`](pit-dev-mode-vision-2026-07-03.md)
- Runner (fases): [`pit_dev_run.py`](../../scripts/pit/pit_dev_run.py)
- Broker audit (contraste): [`pit-p4-broker-contract-20260621.md`](pit-p4-broker-contract-20260621.md)
- Trazabilidad (egress como eslabón): [`pit-traceability-agent.md`](pit-traceability-agent.md)
