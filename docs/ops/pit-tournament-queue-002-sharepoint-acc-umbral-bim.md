# PIT — Cola torneo #2: SharePoint ↔ ACC → Umbral BIM 2 + Foundry

- **Status:** QUEUED — no arrancar hasta gates previos (§2).
- **Registrado:** 2026-06-12 (David, post-revisión piloto `pit-salud-mental-pilot`).
- **Tipo:** torneo real PIT-2b (no dry-run) con prompt NL auténtico de David.
- **Relacionado:** [pit-process-index.md](pit-process-index.md) · [product-innovation-tournament-vision-2026-06-09.md](product-innovation-tournament-vision-2026-06-09.md) · repo producto [`umbral-bim-2`](https://github.com/Umbral-Bot/umbral-bim-2) (confirmar org/path exacto antes del spawn).

---

## 1. Prompt NL canónico de David (verbatim — no parafrasear en specs)

```text
Hola Rick, inicia un torneo de 3 agentes con gasto en tokens de 150 usd en total , para crear una aplicacion que me permita conectar Sharepoint con Autodesk Construction Claud, para que un asistente llm alojado en ai foundry peuda acceder a esas integraciiones y pueda por ejemplo pasar info desde un modelo en ACC a una tabla en Sharepoint o que pueda validare información de incidencias en base a criterios de un documento alojado en sharepoint, necesito la solucion que me permita aregar ae esa capacidad a mi app de mi repo umbral-bim-2
```

**Parser Rick debe extraer explícitamente:**

| Campo | Valor |
|-------|-------|
| N lanes | 3 |
| budget_usd | 150 (total torneo) |
| output | aplicación / capacidad integrable en producto existente |
| dominio | SharePoint + Autodesk Construction Cloud (ACC) + Azure AI Foundry |
| casos de uso | modelo ACC → tabla SharePoint; validar incidencias vs criterios en doc SharePoint |
| producto destino | repo **`umbral-bim-2`** (extender app, no greenfield aislado) |
| gate spawn | literal `ok, arranca` (sin gate no corre) |

---

## 2. Gates previos (orden obligatorio)

| # | Gate | Owner | Estado |
|---|------|-------|--------|
| G1 | **P5.2b Judge UX v2** merge + deploy VPS (`/pit/access`, preview fix) | Copilot Windows → Copilot-VPS | ✅ `802f431` |
| G2 | Cierre piloto `pit-salud-mental-pilot` (winner + outcome) — recomendado, no bloqueante duro | David + Copilot-VPS | pendiente |
| G3 | **Read access repo producto** en VPS | Copilot-VPS / David | **BLOCKED** — `Umbral-Bot/umbral-bim-2` no existe en GH; candidato local `umbral-bim` / `umbral-bot-copilot` |
| G4 | **Copilot CLI broker** + modelos CLI (no OpenClaw azure/codex directo para código) | Rick skill + Worker `copilot_cli.run` | pendiente — corregir lanes.yaml |
| G5 | Spec + lanes YAML en `examples/pit-sharepoint-acc-umbral-bim.yaml` validado con `pit_spec_validate.py` | Claude / Copilot Windows | pendiente |

---

## 3. Lecciones del piloto #1 (aplicar en #2)

| Piloto salud mental | Torneo #2 debe |
|---------------------|----------------|
| Prototipos HTML muy básicos | Prototipos tipo **producto**: flujos ACC↔SP plausibles, UI alineada a umbral-bim-2, no landing genérica |
| KPI 100 % synthetic | Etiquetar synthetic; judge prioriza **arquitectura + integrabilidad en repo** sobre métricas simuladas |
| Prompt “de laboratorio”, no voz David | Usar **verbatim** §1 como input Rick |
| Modelos ligeros / perfil coding único | **Un modelo pesado distinto por lane** (§4) |
| Sin contexto repo producto | Lanes leen **`umbral-bim-2`** (stack, edge functions, Foundry hooks existentes) |

---

## 4. Asignación de modelos — arquitectura David (2026-06-12, corregir spec Rick)

**Regla:** las lanes **NO programan** con LLM de proveedor directo (azure-openai-responses, openai/gpt-5.3-codex en OpenClaw).
Rick/lanes **orquestan**; la **implementación de código** va por **broker GitHub Copilot CLI** (`copilot_cli.run` en Worker), con modelos pesados vía `--model`:

| Lane | Rol cognitivo | Copilot CLI model (intent) | OpenClaw lane model |
|------|---------------|----------------------------|---------------------|
| A arquitectura Foundry/tools | diseño, contratos | `gpt-5.5` + `--reasoning-effort high` | ligero / Rick only |
| B prototipo integrable | código en sandbox | `gpt-5.5` max o equivalente CLI | ligero |
| C QA / encaje repo | review + paths | Fable 5 Max vía CLI si GH lo expone; si no, `Claude Opus 4.7` o slug documentado en `copilot-cli-models-and-tools` | ligero |

Patrón = mismo broker que Magnific visual ([pit-visual-magnific.md](pit-visual-magnific.md) + [copilot-cli-autonomy-vision-roadmap.md](../copilot-cli-autonomy-vision-roadmap.md)).
**Estado runtime:** `copilot_cli.run` hoy es **read-only** (view/grep/glob); write/PR = F9+ con gates. Torneo #2 puede arrancar en modo **research + prototipo HTML fuera del repo** + patch-plan como artefacto, o esperar gate F9 si David exige código en sandbox.

**Acción skill:** actualizar `product-innovation-tournament/SKILL.md` §Broker + lanes.yaml campo `coding_broker: copilot_cli` + `copilot_model`. Owner: post-torneo o PR bloqueante si David lo exige antes del spawn.

---

## 4b. Asignación anterior (OBSOLETA — no usar OpenClaw directo)

| Lane (propuesta) | Ángulo hipótesis | Modelo intent | Contexto |
|------------------|------------------|---------------|----------|
| **lane-data-connector** | ACC Data Connector + Power Platform / Fabric hacia SharePoint; mínimo código custom | **GPT-5.5 High** (1M) o alias Foundry equivalente | docs ACC Data Connector, tablas CDC |
| **lane-foundry-tools** | Azure AI Foundry agent + tools directas (Graph SharePoint + ACC APIs) embebidas en umbral-bim-2 | **Codex** (OpenClaw alias VPS) | repo umbral-bim-2, Foundry SDK |
| **lane-orchestrator** | Orquestación n8n/Make + Foundry como cerebro; MVP rápido integrando capacidades al bot | **Fable 5 Max** (1M) | patrones umbral-agent-stack, embudos existentes |

**Pre-flight obligatorio (Copilot-VPS):** listar aliases reales en `openclaw.json` / Foundry; si un alias no existe, reportar `PIT7_MODEL_BLOCKED:<alias>` antes del gate — no sustituir silenciosamente por default barato.

---

## 5. Tres ángulos de lane (seed para `*.lanes.yaml`)

1. **Data Connector / analítica relacional** — export ACC → tabla/lake → sync SharePoint list; Foundry consulta ambos.
2. **Foundry-native tools** — agent en Foundry con tools HTTP/Graph; PR conceptual hacia umbral-bim-2 (supabase/functions o Azure sidecar).
3. **Orquestación low-code** — n8n/Make como bus; Foundry valida incidencias leyendo criterios desde biblioteca SharePoint.

Cada lane debe entregar en iteración final: prototipo navegable + notas de **cómo encaja en umbral-bim-2** (paths concretos, no slide deck).

---

## 6. Acceso repo `umbral-bim-2`

| Actor | Acceso | Notas |
|-------|--------|-------|
| Rick (orquestador) | **read** mínimo; write solo vía PR post-torneo si David autoriza | clone en VPS o mount read-only |
| Lanes efímeras | read del repo vía Rick broker; **no** push directo a main | citar paths en `notes.md` |
| Judge (David) | MC v2 `/pit/judge/pit-sharepoint-acc-umbral-bim` | post P5.2b |

Tarea pre-torneo sugerida: `git clone` read-only en `~/umbral-bim-2` o symlink documentado; verificar `.env` / secrets **no** copiados al vault PIT.

---

## 7. KPIs judge (borrador — refinar en spec YAML)

Priorizar señales **de producto**, no solo fulfillment sintético:

- ¿El flujo ACC→SharePoint está diagramado y es implementable en umbral-bim-2?
- ¿La validación de incidencias vs documento SP tiene criterios explícitos y demo?
- ¿Research cita fuentes ACC/Graph/Microsoft oficiales?
- ¿Prototipo HTML demuestra 2 casos de uso del prompt David?
- ¿Coste estimado vs budget $150 documentado en notes?

---

## 8. Megaprompt Copilot-VPS (cuando G1–G5 verdes)

```text
autorizo torneo PIT #2 SharePoint-ACC-umbral-bim — gate ok, arranca

Spec: examples/pit-sharepoint-acc-umbral-bim.yaml (+ .lanes.yaml)
Prompt David verbatim: docs/ops/pit-tournament-queue-002-sharepoint-acc-umbral-bim.md §1
Budget: 150 USD total · N=3 · modelos pesados §4 (audit aliases antes de spawn)
Repo read: ~/umbral-bim-2 (read-only)
Runner: bash scripts/pit/pit_tournament_run.sh ... --gate "ok, arranca"
PROHIBIDO: spawn si P5.2b judge UX no deployado o modelos no verificados.
Veredicto: PIT7_RUN_PASS | BLOCKED:<motivo>
```

---

## 9. Rick — formato de respuesta Telegram (roadmap PIT-7 / skill)

**Problema observado (2026-06-12):** Rick respondió con spec YAML largo en chat. David necesita **resumen ejecutivo** + enlaces al detalle.

**Regla deseada para gate PIT y updates de torneo:**

```text
Telegram (máx ~12 líneas):
  • Estado: listo / bloqueado
  • pit_id, lanes, iter, budget
  • Bloqueos (si hay) — 1 línea c/u
  • Acción requerida de David (si hay)
  • Link/evidencia: vault path o MC judge URL (túnel)
Detalle completo: pit/<pit_id>/spec/pit_spec.yaml + lanes.yaml en vault (no volcar en chat).
```

**Tarea follow-up:** actualizar `product-innovation-tournament/SKILL.md` §Fase de confirmación con plantilla Telegram ejecutiva. Owner: Copilot Windows (PR chico post-torneo #2).

---

## 10. Trazabilidad

| Evento | Fecha | Notas |
|--------|-------|-------|
| Encolado por David | 2026-06-12 | Tras revisar prototipos piloto #1; pide casos realistas + modelos pesados |
| Rick spec en vault | 2026-06-12 | `pit-umbral-bim2-sharepoint-acc` validate pass; repo blocked; modelos OpenClaw directo — corregir a Copilot CLI broker |
| | | |
