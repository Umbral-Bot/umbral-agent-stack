# 36 — Rick: búsqueda alternativa y funciones útiles para proyecto embudo

## Búsqueda web para SIM / discovery

### Backend operativo actual

**Tavily Search API** es el backend primario de discovery web en este stack.

Si Tavily queda sin cuota, el path operativo real ahora cae a **Gemini grounded search**
usando `GOOGLE_API_KEY` / `GOOGLE_API_KEY_NANO`. Google Custom Search se mantiene
solo como ruta legada/experimental porque los diagnosticos repetidos han dado `403`
en proyectos nuevos o sin acceso historico. **Azure Bing no esta disponible**
para cuentas nuevas (Microsoft depreco la creacion de recursos Bing Search).

| Origen | Variable (VPS: `~/.config/openclaw/env`) | Free tier | Cómo obtener key |
|--------|------------------------------------------|-----------|------------------|
| **Tavily** | `TAVILY_API_KEY` | 1000 créditos/mes | [app.tavily.com](https://app.tavily.com) o [docs.tavily.com](https://docs.tavily.com) — API orientada a agentes AI |
| **Gemini grounded search** | `GOOGLE_API_KEY` / `GOOGLE_API_KEY_NANO` | según proyecto/plan Gemini | Google AI Studio / Gemini API |
| **Google Custom Search (legado)** | `GOOGLE_CSE_API_KEY_RICK_UMBRAL` + `GOOGLE_CSE_CX` | n/a | Solo para pruebas explícitas; requiere `--allow-google-legacy` o `WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1` |

**Uso:** `python scripts/web_discovery.py "keyword" [--count 5]` — usa Tavily por defecto y cae a Gemini grounded search si Tavily falla. Con `--force-tavily` obliga Tavily y salta cualquier fallback. Solo con `--allow-google-legacy` (o `WEB_DISCOVERY_ENABLE_GOOGLE_CSE=1`) intentará Google CSE como tercer intento.

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
| **Tavily Search** | Discovery web primario del stack | `TAVILY_API_KEY` + `scripts/web_discovery.py` |
| **Google (Gemini/NL/Vertex)** | Resúmenes, análisis de texto, clustering (SIM) | Keys y proyecto en doc 35; Vertex con Service Account si se necesita |
| **Telegram** | Avisos a David, resúmenes ejecutivos | `TELEGRAM_BOT_TOKEN` + chat_id en env |
| **Calendario (Google/Outlook)** | Próximas reuniones, recordatorios de seguimiento | OAuth o API de calendario; opcional para Rick |
| **CRM ligero (Notion/Linear)** | Pipeline de leads, etapas, siguiente acción | Usar bases Notion o labels/estados en Linear |
| **Formularios / webhooks** | Captura de leads desde web (form → Notion/DB) | Página en Hostinger + webhook a endpoint que Rick escuche o a Notion |
| **Email (enviar)** | Secuencias de nurturing, recordatorios | SMTP o API (SendGrid, etc.); definir límites y uso |

### Prioridad sugerida para el embudo

1. **Ya en uso:** Notion, Linear, VM/Drive, GitHub, SIM (Reddit + búsqueda cuando esté).
2. **Siguiente:** mantener Tavily como backend primario de búsqueda, Gemini grounded search como fallback real y usar Telegram para resúmenes breves a David.
3. **Después:** Hostinger para estado de infra; opcional calendario + CRM en Notion/Linear; formularios/webhooks si hay landing.

---

## Referencias

- Custom Search / GCP: [docs/35-rick-google-cloud-apis.md](35-rick-google-cloud-apis.md)
- GitHub (Rick): [docs/34-rick-github-token-setup.md](34-rick-github-token-setup.md)
- Worker VM y Drive: [runbooks/runbook-vm-worker-setup.md](../runbooks/runbook-vm-worker-setup.md)
