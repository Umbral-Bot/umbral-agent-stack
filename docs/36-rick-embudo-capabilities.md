# 36 — Rick: búsqueda alternativa y funciones útiles para proyecto embudo

## Búsqueda web para SIM / discovery

### Si Custom Search (Google) da 403

Google Custom Search puede devolver 403 en proyectos nuevos. **Azure Bing no está disponible** para cuentas nuevas (Microsoft deprecó la creación de recursos Bing Search). **Fallback:** Tavily Search API.

| Origen | Variable (VPS: `~/.config/openclaw/env`) | Free tier | Cómo obtener key |
|--------|------------------------------------------|-----------|------------------|
| **Tavily** | `TAVILY_API_KEY` | 1000 créditos/mes | [app.tavily.com](https://app.tavily.com) o [docs.tavily.com](https://docs.tavily.com) — API orientada a agentes AI |

**Uso:** `python scripts/web_discovery.py "keyword" [--count 5]` — intenta Google; si 403, usa Tavily. Con `--force-tavily` va directo a Tavily.

Rick usa el mismo flujo (keywords → resultados → hallazgos); el script elige motor según disponibilidad.

---

## Otras funciones útiles para el proyecto embudo

Funciones que Rick puede usar o a las que puedes darle acceso para el embudo de ventas (awareness → lead → nurturing → cierre → retención):

| Función | Para qué sirve | Cómo habilitarla |
|--------|----------------|------------------|
| **Notion (ya tiene)** | Dashboard, tareas, auditoría, mensajes para David | `NOTION_API_KEY`, bases y páginas en config (ver [auditoría Notion](auditoria-notion-env-vars.md)) |
| **Linear (ya tiene)** | Issues por iniciativa, asignación, roadmap | `LINEAR_API_KEY`, `linear.create_issue`, equipos |
| **Worker VM + windows.fs** | Entregables en Drive (G:\...), informes, bundles | Tareas `windows.fs.*`; servicio NSSM con usuario que ve G: |
| **GitHub** | PRs de mejoras, documentación, código del stack | `GITHUB_TOKEN` + deploy key SSH (doc 34) |
| **Hostinger API** | Estado de VPS, dominios, proyectos web | `HOSTINGER_API_TOKEN` (doc 35 / env) |
| **Tavily Search** | Discovery web cuando Custom Search falle (Bing no disponible cuentas nuevas) | `TAVILY_API_KEY` + `scripts/web_discovery.py` |
| **Google (Gemini/NL/Vertex)** | Resúmenes, análisis de texto, clustering (SIM) | Keys y proyecto en doc 35; Vertex con Service Account si se necesita |
| **Telegram** | Avisos a David, resúmenes ejecutivos | `TELEGRAM_BOT_TOKEN` + chat_id en env |
| **Calendario (Google/Outlook)** | Próximas reuniones, recordatorios de seguimiento | OAuth o API de calendario; opcional para Rick |
| **CRM ligero (Notion/Linear)** | Pipeline de leads, etapas, siguiente acción | Usar bases Notion o labels/estados en Linear |
| **Formularios / webhooks** | Captura de leads desde web (form → Notion/DB) | Página en Hostinger + webhook a endpoint que Rick escuche o a Notion |
| **Email (enviar)** | Secuencias de nurturing, recordatorios | SMTP o API (SendGrid, etc.); definir límites y uso |

### Prioridad sugerida para el embudo

1. **Ya en uso:** Notion, Linear, VM/Drive, GitHub, SIM (Reddit + búsqueda cuando esté).
2. **Siguiente:** Tavily como fallback de búsqueda (Custom Search 403; Bing deprecado); Telegram para resúmenes breves a David.
3. **Después:** Hostinger para estado de infra; opcional calendario + CRM en Notion/Linear; formularios/webhooks si hay landing.

---

## Referencias

- Custom Search / GCP: [docs/35-rick-google-cloud-apis.md](35-rick-google-cloud-apis.md)
- GitHub (Rick): [docs/34-rick-github-token-setup.md](34-rick-github-token-setup.md)
- Worker VM y Drive: [runbooks/runbook-vm-worker-setup.md](../runbooks/runbook-vm-worker-setup.md)
