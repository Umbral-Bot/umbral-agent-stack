# 39 — Make + n8n para Rick: potenciar análisis de mercado (SIM / embudo)

## Objetivo

Aprovechar la suscripción de **Make.com** y de **n8n** que tenés, dando a Rick capacidad de orquestar y disparar escenarios/flujos desde la VPS para **potenciar el trabajo de análisis de mercado** (SIM: Reddit, tendencias, Tavily, informes). Prioridad: **Make** — tenés 10.000 créditos que se renuevan en ~3 días; el objetivo es usarlos (o el máximo posible) en ese lapso en tareas de análisis de mercado.

## Estado actual del análisis de mercado (Rick)

- **SIM**: Reddit + tendencias + búsqueda web (Tavily cuando Custom Search da 403). Ver [docs/36-rick-embudo-capabilities.md](36-rick-embudo-capabilities.md) y [docs/35-rick-google-cloud-apis.md](35-rick-google-cloud-apis.md).
- **Scripts**: `web_discovery.py` (keywords → resultados), crons en la VPS, Worker VM para entregables (Drive).
- **Salidas**: informes en Notion/Drive, Linear (issues UMB-6…), Dashboard Rick.

## Cómo Rick puede usar Make (prioridad: 3 días)

Make tiene **API** y **webhooks** para controlar escenarios sin usar la interfaz.

### Opción 1: Webhooks (más simple)

1. En Make creás uno o varios escenarios con **Webhook** como disparador (instantáneo).
2. Make te da una URL por escenario, ej. `https://hook.eu1.make.com/xxxxxxxx`.
3. Rick (o un script/cron en la VPS) hace **POST** a esa URL con un JSON (ej. `{"keywords": ["agencia vs freelance", "embudo servicios"], "source": "sim"}`).
4. El escenario en Make corre (HTTP, módulos de Make, etc.) y consume créditos; puede devolver resultado por webhook de respuesta o escribir a Notion/Sheets/Webhook que Rick escuche.

**Ventaja:** No hace falta API token; solo guardar la URL del webhook en env (ej. `MAKE_WEBHOOK_SIM_RUN`). Rick o un script hace POST y dispara el escenario.

### Opción 2: API de Make (control completo)

1. En Make: **Profile → API** (o [developers.make.com](https://developers.make.com)) creás un **API token** con permisos para ejecutar escenarios.
2. La API permite listar escenarios, **ejecutar un escenario por ID**, ver historial. Header: `Authorization: Token <token>`.
3. Rick (script en la VPS) usa ese token para **run scenario** con o sin datos de entrada.

**Ventaja:** Un solo token; podés disparar cualquier escenario por ID y pasar parámetros. Documentación: [Make API Reference](https://developers.make.com/api-documentation/api-reference/scenarios).

### Ideas de escenarios Make para análisis de mercado (usar créditos en 3 días)

- **SIM diario ampliado**: Escenario que cada X horas (o al recibir webhook) tome una lista de keywords (desde Notion, Google Sheet o body del webhook), llame a una API de búsqueda (o a un webhook tuyo que ejecute `web_discovery.py`), agregue resultados y escriba un resumen en Notion o en un Sheet que Rick lea después.
- **Reddit + tendencias**: Make puede orquestar llamadas HTTP (Reddit API, o tu Worker que ya hace algo de Reddit), combinar con otro módulo (ej. Google Trends si hay conector), y volcar a Notion/Linear.
- **Pipeline keywords → búsqueda → informe**: Webhook recibe keywords → Make ejecuta varios pasos (HTTP a Tavily o a tu script, formateo, Notion/Sheets). Cada ejecución consume créditos; con 10k podés hacer muchas corridas en 3 días si cada run no es excesivo.

Recomendación: arrancar con **1–2 escenarios** en Make (ej. uno “SIM run” por webhook con keywords, otro “resumen semanal” programado). Rick recibe las URLs de webhook (o el API token) y las usa desde la VPS (cron + curl o script Python).

## Cómo Rick puede usar n8n

n8n en la VPS (doc [37](37-n8n-vps-automation.md)) ya está instalado. Para que Rick lo use sin interfaz:

- **Webhooks**: En un workflow n8n ponés un nodo **Webhook**; n8n te da una URL (ej. `http://localhost:5678/webhook/sim-trigger`). Rick o un cron en la VPS hace POST a esa URL (por Tailscale si el trigger es desde otra máquina) y dispara el workflow.
- **API de n8n**: Si tu instancia tiene API habilitada, se puede ejecutar un workflow por ID vía `POST /api/v1/workflows/:id/run` con API key. Requiere configurar `N8N_API_KEY` y `N8N_URL` en el env de Rick.

Prioridad menor que Make para el “sprint” de 3 días; n8n sirve para flujos recurrentes que no consuman Make (ej. notificaciones, sync Notion–Linear, informes que corren en la VPS y solo notifican por n8n).

## Cómo pasar las APIs a Rick (seguro)

Igual que con Linear, Hostinger y Notion: **nunca en el repo**. Rick tiene un mecanismo para que le envíes credenciales por canal (ej. Telegram) y las guarda en `~/.config/openclaw/env` en la VPS sin exponerlas.

### Para Make

1. **Si usás solo webhooks:** Creá el escenario en Make, activalo, copiá la URL del webhook. Enviásela a Rick en un mensaje privado (ej. Telegram). Rick la guarda como por ejemplo `MAKE_WEBHOOK_SIM_RUN=https://hook.eu1.make.com/xxxx`.
2. **Si usás API:** En Make (Profile → API o developers.make.com) generá un **API token**. Enviáselo a Rick; él lo guarda como `MAKE_API_TOKEN=xxx` en `~/.config/openclaw/env`. No compartas el token en canales públicos ni lo commitees.

### Para n8n (opcional en este sprint)

- Si Rick va a disparar n8n por webhook: creá el workflow con nodo Webhook, obtené la URL (ej. `http://IP_VPS:5678/webhook/...`). Pasale a Rick la URL; si n8n está en la VPS, puede ser `http://127.0.0.1:5678/webhook/...` para llamadas locales.
- Si usás API de n8n: generá una API key en n8n (Settings) y pasale a Rick `N8N_URL` y `N8N_API_KEY`.

### Variables de entorno (VPS: `~/.config/openclaw/env`)

| Variable | Uso |
|----------|-----|
| `MAKE_API_TOKEN` | Token de Make (Authorization: Token xxx) para ejecutar escenarios por API. |
| `MAKE_WEBHOOK_SIM_RUN` | (Opcional) URL del webhook de Make que dispara el escenario “SIM run”. Rick o script hace POST aquí. |
| `MAKE_WEBHOOK_*` | Otras URLs de webhook si tenés más escenarios (ej. resumen semanal). |
| `N8N_URL` | (Opcional) Base URL de n8n, ej. `http://127.0.0.1:5678` en la VPS. |
| `N8N_API_KEY` | (Opcional) API key de n8n para ejecutar workflows por API. |

Las plantillas del repo (`.env.example`, `openclaw/env.template`) incluyen placeholders para no commitear valores reales.

## Resumen de pasos (vos + Rick)

1. **Vos (Make):** Crear 1–2 escenarios en Make que hagan algo útil para análisis de mercado (ej. webhook → HTTP/connectors → salida a Notion o Sheet). Anotar URL del webhook y/o crear API token.
2. **Vos:** Enviar a Rick por canal seguro la URL de webhook y/o el `MAKE_API_TOKEN`. Rick guarda en `~/.config/openclaw/env` sin exponerlas.
3. **Rick:** Usar en los próximos 3 días esos créditos: desde crons o scripts en la VPS, disparar los escenarios (POST al webhook o llamada a la API de Make con el token) con parámetros de keywords/fuentes que potencien el SIM. Opcional: conectar salidas de Make con Notion/Linear (ya documentado en el stack).
4. **n8n:** Mientras tanto o después: si querés que Rick también dispare workflows n8n, añadir `N8N_URL` + webhook URL o `N8N_API_KEY` y documentar en este doc el flujo concreto.

## Referencias

- Make API: [developers.make.com](https://developers.make.com/api-documentation/api-reference/scenarios)
- Make webhooks: al añadir módulo “Webhook” en un escenario, Make te da la URL.
- n8n en VPS: [docs/37-n8n-vps-automation.md](37-n8n-vps-automation.md)
- SIM y búsqueda: [docs/36-rick-embudo-capabilities.md](36-rick-embudo-capabilities.md), [docs/35-rick-google-cloud-apis.md](35-rick-google-cloud-apis.md)

---

## Texto para enviar a Rick (cuando tengas las APIs)

Cuando tengas el **API token de Make** y/o la **URL del webhook** del escenario que quieras que Rick dispare, enviáselo por el canal seguro (ej. Telegram). Podés usar este texto como guía (rellenando los valores reales en el siguiente mensaje, sin pegarlos aquí):

**Mensaje 1 (instrucción):**  
«Rick: te doy acceso a Make para que potencies el análisis de mercado (SIM) en los próximos días. En el repo está la doc en `docs/39-make-n8n-rick-market-analysis.md`. Necesito que guardes en `~/.config/openclaw/env` (sin exponerlas) las variables que te envío en el siguiente mensaje: `MAKE_API_TOKEN` y/o `MAKE_WEBHOOK_SIM_RUN` (URL del webhook del escenario que quiero que dispares). Objetivo: usar los créditos de Make en escenarios que ayuden al SIM (keywords, búsquedas, resúmenes). Si tenés n8n en la VPS y querés disparar también un workflow por webhook, te paso además la URL del webhook de n8n.»

**Mensaje 2 (solo los valores, sin explicación en canales públicos):**  
Enviar en un mensaje aparte (o por canal privado) solo las líneas para que Rick las agregue al env, por ejemplo:  
`MAKE_API_TOKEN=tu_token_aqui`  
y/o  
`MAKE_WEBHOOK_SIM_RUN=https://hook.eu1.make.com/xxxx`  
(Reemplazar por los valores reales; no commitear ni pegar en el repo.)
