# OpenClaw Runtime Snapshot

- Generado: 2026-03-24T07:55:44.935694+00:00
- Ventana: 7 dias
- Eventos leidos: 29169
- Fuente OpenClaw: `openclaw_gateway`

## Resumen
- Eventos operativos OpenClaw: 12 (8 completados, 0 fallidos, 4 bloqueados)
- Eventos LLM trazados: 2
- Tokens LLM trazados: 319
- Costo proxy total: 0.000069 USD
- Lecturas Notion de paneles: 128
- Escrituras Notion de paneles: 120
- Snapshot de sesiones OpenClaw: si

## Paneles
### dashboard_rick
- updated/skipped/failed: 6/0/0
- Notion reads/writes: 18/6
- Worker calls: 24
- Ultimo estado: updated
- Ultimo trigger: deferreds
- Ultimo ts: 2026-03-24T07:48:51.844081+00:00

### openclaw_panel
- updated/skipped/failed: 6/2/0
- Notion reads/writes: 110/114
- Worker calls: 0
- Ultimo estado: updated
- Ultimo trigger: deferreds
- Ultimo ts: 2026-03-24T07:49:33.450003+00:00

## OpenClaw runtime
| Task | Completed | Failed | Blocked | Avg ms |
|------|-----------|--------|---------|--------|
| google.calendar.list_events | 2 | 0 | 0 | 586 |
| linear.list_teams | 2 | 0 | 0 | 264 |
| research.web | 2 | 0 | 0 | 5816 |
| composite.research_report | 1 | 0 | 0 | 21809 |
| llm.generate | 1 | 0 | 0 | 3380 |
| windows.fs.list | 0 | 0 | 4 | 0 |

## LLM usage
| Provider | Calls | Prompt | Completion | Total | Avg ms | Cost proxy USD |
|----------|-------|--------|------------|-------|--------|----------------|
| gemini | 2 | 64 | 44 | 319 | 3197 | 0.000069 |

### By usage component
| Component | Calls | Tokens | Cost proxy USD |
|-----------|-------|--------|----------------|
| composite.research_report.query_generation | 1 | 179 | 0.000055 |
| llm.generate | 1 | 140 | 0.000014 |

## Session usage
- Sessions root: `/home/rick/.openclaw/agents`
| Agent | Sessions | Input | Output | Total | Cache read | Cost proxy USD |
|-------|----------|-------|--------|-------|------------|----------------|
| main | 47 | 2466401 | 16848 | 1505398 | 1255340 | 0.791938 |
| rick-ops | 50 | 840202 | 14894 | 1276478 | 2504448 | 0.134967 |
| rick-orchestrator | 1 | 21010 | 581 | 21010 | 0 | 0.003500 |
| rick-tracker | 1 | 16079 | 12 | 16079 | 0 | 0.005640 |
| rick-qa | 1 | 13629 | 134 | 13629 | 0 | 0.002125 |
| rick-delivery | 1 | 13307 | 12 | 13307 | 0 | 0.002003 |

### By model
| Model | Provider | Sessions | Total | Cost proxy USD |
|-------|----------|----------|-------|----------------|
| gpt-5.3-codex | openai-codex | 52 | 1303414 | 0.139095 |
| gemini-2.5-flash | google | 37 | 1078078 | 0.720939 |
| gpt-5.4 | openai-codex | 8 | 393314 | 0.066044 |
| gpt-5.2-chat | azure-openai-responses | 1 | 21151 | 0.003236 |
| gpt-5.4-pro | azure-openai-responses | 1 | 21010 | 0.003500 |
| gemini-3.1-pro-preview | google-vertex | 1 | 16079 | 0.005640 |
| claude-opus-4-6 | anthropic | 1 | 12855 | 0.001719 |

## Limitations
- El snapshot cubre actividad de paneles y eventos LLM trazados en ops_log; no es facturacion exacta.
- research.web via Gemini grounded search no expone tokens en ops_log hoy, asi que su costo fino queda fuera del corte.
- La estimacion monetaria usa rates rough versionados en el repo y debe leerse como costo proxy, no como facturacion oficial.
- La vista de sesiones usa snapshots `sessions.json` de OpenClaw; refleja tokens acumulados por sesion y no reemplaza billing oficial por request.
- El costo proxy de sesiones usa solo input/output tokens; `cacheRead` y `cacheWrite` quedan fuera porque su billing depende del provider.

