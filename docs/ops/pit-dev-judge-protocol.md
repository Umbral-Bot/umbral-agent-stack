# PIT-DEV — Protocolo de jueces ejecutores (judge-dev)

- **Status:** v2 (hardening postmortem `pit-dev-ifc-viewer`) — 2026-07-04.
  v1 (PIT-DEV FASE 4) — 2026-07-03.
- **Decisión David (visión §4):** al cierre de lanes, jueces subagentes
  (supervisados por seguridad) **instalan, ejecutan y evalúan** cada
  deliverable contra una rúbrica ejecutable.
- **Plantilla de rol:** [`ROLE.judge-dev.md`](../../openclaw/workspace-templates/pit-lane-agent/ROLE.judge-dev.md).
- **Schema del scorecard:** [`judge-scorecard.schema.json`](../../openclaw/workspace-templates/pit-vault/templates/judge-scorecard.schema.json) (v2).
- **Primitivas ejecutables:** `validate_scorecard` / `collect_scorecards` /
  `weighted_score` / `aggregate_ranking` en [`pit_dev_core.py`](../../scripts/pit/pit_dev_core.py).
- **Postmortem que originó el v2:** [`pit-dev-ifc-viewer-postmortem-2026-07-04.md`](pit-dev-ifc-viewer-postmortem-2026-07-04.md).

---

## 1. Cuándo y cuántos

- **N jueces efímeros** (`judge_count` del spec, default **2**), ids
  `judge-1..judge-N`, agentes `<pit_id>-judge-<n>`.
- Spawneados **POST-cierre de lanes, nunca antes** (el runner los registra
  junto al resto pero solo los spawnea tras el collect de lanes + veredicto
  security).
- Solo corren con **≥2 lanes elegibles** (paralelo a la regla v1 "judge solo
  con ≥2 lanes completas"). Elegible = `lane_complete` + `EGRESS_CLEAN` (o
  flagged con decisión explícita registrada).

## 2. Rúbrica ejecutable (por lane, por juez)

Cada juez trabaja en un workdir aislado
`pit/<pit_id>/judge/<judge_id>/<lane_id>/` (copia el deliverable, jamás lo
modifica in-place):

1. ¿**Instala limpio**? (siguiendo el README del deliverable) → `installed_clean`
2. ¿**Corre**? (arranca/responde) → `ran`
3. ¿**Pasa sus propios tests**? (re-ejecuta el `command` del `test_report.json`) → `own_tests_passed`
4. ¿**Cumple el spec funcional**? (`deliverable_spec` punto por punto)
   → `meets_functional_spec`. **Regla dura v2 (postmortem
   `pit-dev-ifc-viewer`):** `true` SOLO con **input real** — un fixture del
   propio deliverable (`mini-site.ifc`, 4.4 KB), un `curl` HTTP 200 o sus
   tests offline en verde NO son verificación funcional. Si es `true`, el
   scorecard DEBE incluir `functional_evidence: {real_input_used: true,
   input_description: "<input, tamaño, qué se observó>"}` — sin eso
   `validate_scorecard` lo invalida y no cuenta para el ranking.
5. Puntúa **criterios 0-1**: `funcionalidad`, `robustez`, `dx`, `docs`,
   `testabilidad` — los **pesos viven en el spec** (`rubric_weights`), no en el
   scorecard.

Salida: `pit/<pit_id>/judge/scorecards/<judge_id>--<lane_id>.json` válido
contra el schema. Un scorecard inválido **no cuenta** (el collect lo lista en
`scorecards_invalid`).

## 3. Supervisión security

Los jueces declaran su egress igual que las lanes
(`pit/<pit_id>/judge/<judge_id>/egress.jsonl`) y el security monitor los
audita con el mismo mecanismo ([`pit-security-egress-monitor.md`](pit-security-egress-monitor.md)).
Evaluar un deliverable no debería requerir egress; si lo requiere, se declara
y justifica.

## 4. Ranking agregado — NO decide

- El runner calcula por scorecard el score ponderado
  (`weighted_score`, pesos del spec) y por lane la media entre jueces
  (`aggregate_ranking`) → `pit/<pit_id>/judge/ranking.json`.
- **El ranking NO decide:** Rick consolida y **David da el gate de winner**
  (regla existente de PIT). El ranking ordena información para esa decisión.

## 5. Referencias

- Visión PIT-DEV: [`pit-dev-mode-vision-2026-07-03.md`](pit-dev-mode-vision-2026-07-03.md)
- Cierre de lane verificable (input del juez): visión §3 + [`pit_dev_core.py`](../../scripts/pit/pit_dev_core.py) (`verify_dev_lane`)
- Runner (fase judges): [`pit_dev_run.py`](../../scripts/pit/pit_dev_run.py)
