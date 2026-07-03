# Sprint 2026-07-02 — índice de prompts

> Orden sugerido de ejecución. Cada prompt va a un agente/superficie distinta.

| # | Agente | Superficie | MEGAPROMPT | Task |
|---|--------|------------|------------|------|
| 3 | **Codex/Cursor** | hilo nuevo | [`MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md`](MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md) | 2026-07-02-005 |
| 1 | **Copilot** | Windows | [`MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt`](MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt) | 2026-07-02-002-graphify |
| 2 | **Cursor** | lead | [`MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md`](MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md) | 2026-07-02-004 |
| — | Copilot-VPS | VPS | *(done — no rehacer)* | 2026-07-02-003 |

**Deuda Fase 2 voz:** [`MEGAPROMPT-rick-voice-realtime-phase2.md`](MEGAPROMPT-rick-voice-realtime-phase2.md)

---

## Prompt 1 — Copilot Windows · Graphify F3–F4 (clon Copilot)

```text
Autorizo G-GR-0. Ejecutá piloto Graphify F3–F4 según
docs/ops/MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt

=== PREFLIGHT CLON (obligatorio) ===
cd C:\GitHub\umbral-agent-stack-copilot
git remote get-url origin   # Umbral-Bot/umbral-agent-stack.git
git fetch origin main
git checkout main && git pull --ff-only origin main
git checkout -b copilot/graphify-pilot-f1-f4
# Verificar: .graphifyignore, graphify-out/graph.json, graphify-pilot-results, task 2026-07-02-002
pwd   # debe ser ...\umbral-agent-stack-copilot

Clone: C:\GitHub\umbral-agent-stack-copilot  (orden Copilot — NO umbral-agent-stack base)
Rama: copilot/graphify-pilot-f1-f4 · Modelo: Fable 5 · 1M

F1–F2 ya hechos aquí (Cursor): leaks=0, cost≈$3.52
Tu trabajo: gold-set A/B (F3), decisión F4, PR (.graphifyignore + results + task/board)
NO commitear graphify-out/. NO mergear PR. NO Copilot-VPS.
```

## Prompt 1b — Copilot Windows · Graphify F1–F4 completo (desde cero)

```text
Autorizo G-GR-0. Ejecutá F1–F4 completo según MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt

PREFLIGHT: cd C:\GitHub\umbral-agent-stack-copilot → fetch → pull main → rama copilot/graphify-pilot-f1-f4
Azure F2: oai-umbral-agents-prod · Superficie Copilot Windows ONLY · NO mergear PR.
```

---

## Prompt 2 — Cursor · Rick voz capitalización (después o sprint siguiente)

```text
Ejecutá capitalización Rick voz MVP según
docs/ops/MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md

Task: .agents/tasks/2026-07-02-004-capitalize-rick-voice-persona-mvp.md
NO rehacer smoke VPS. Commit solo si David autoriza.
```

---

## Prompt 3 — Codex/Cursor · Auditoría Notion MCP (hilo nuevo, paralelo)

```text
Modo diagnóstico read-only. Ejecutá auditoría Notion MCP según
docs/ops/MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md

=== PREFLIGHT CLON ===
cd C:\GitHub\umbral-agent-stack-copilot
git fetch origin main && git checkout main && git pull --ff-only origin main
git checkout -b codex/notion-mcp-opportunity-audit

Task: .agents/tasks/2026-07-02-005-notion-mcp-opportunity-audit.md

Contexto externo (leer):
https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0
(Notion MCP oficial: tools/list, create-pages, create-attachment, HTML embebible, mcp.notion.com OAuth)

Baseline interno obligatorio:
- .agents/tasks/2026-05-05-006 (Rick VPS NO tiene MCP Notion — REST Worker)
- ADR-007, editorial notion-schema, linkedin-publication-pipeline § audit MCP

Tu trabajo:
1. Inventario REST vs MCP en UAS (Worker, Poller, editorial, OpenClaw, IDE agents)
2. Gap matrix + top 10 oportunidades (quick win / strategic / defer)
3. Riesgos + roadmap O0–O3
4. Entregable: docs/audits/notion-mcp-opportunity-audit-2026-07-02.md

PROHIBIDO: writes Notion producción, VPS changes, secretos, schema changes.
Si tenés Notion MCP conectado: solo smoke read-only (fetch/search).

Respuesta: NOTION_MCP_AUDIT_READY | quick_wins=N | recomendacion_ola=O?
```

---

**No usar `umbralbim-resource`** — es del producto Umbral BIM. Rick/UAS **no tienen** recurso OpenAI propio aún.

Inventario + creación: [`azure-openai-umbral-agents-provisioning.md`](azure-openai-umbral-agents-provisioning.md)

**Recurso canónico a crear:** `oai-umbral-agents-prod` · RG `rg-umbral-agents-prod` · `eastus2`

**Portal crear Foundry:** https://portal.azure.com/#create/Microsoft.CognitiveServicesAIFoundry

**¿Exportar keys?** Solo para F2, y solo **después** de crear el recurso + deployment barato (`gpt-4o-mini`). F1 no necesita Azure.

Preflight Copilot (PowerShell):
```powershell
# ¿Existe el recurso UAS?
az cognitiveservices account show -g rg-umbral-agents-prod -n oai-umbral-agents-prod --query name -o tsv 2>$null
if (-not $?) { "STOP: crear oai-umbral-agents-prod primero (ver provisioning doc)" }

# Vars sesión (solo F2)
$env:AZURE_OPENAI_API_KEY
$env:AZURE_OPENAI_ENDPOINT   # https://oai-umbral-agents-prod.cognitiveservices.azure.com/
```

Keys (post-creación):
```powershell
az cognitiveservices account keys list -g rg-umbral-agents-prod -n oai-umbral-agents-prod --query key1 -o tsv
az cognitiveservices account show -g rg-umbral-agents-prod -n oai-umbral-agents-prod --query properties.endpoint -o tsv
```

Export sesión Copilot (F2):
```powershell
$env:AZURE_OPENAI_API_KEY = "<key1>"
$env:AZURE_OPENAI_ENDPOINT = "https://oai-umbral-agents-prod.cognitiveservices.azure.com/"
```
