# OpenClaw: skill openclaw-gateway para Rick y asignación de modelos por agente

> Actualización operativa 2026-03-08:
> - `main`, `rick-orchestrator`, `rick-delivery`, `rick-qa`, `rick-tracker` y `rick-ops` quedaron fijados en `google/gemini-2.5-flash` para estabilidad.
> - Claude quedó deshabilitado temporalmente vía `UMBRAL_DISABLE_CLAUDE=true`.
> - Rick consume GPT/Kimi/Azure, Vertex 3.1, Notion, Linear, Tavily y audio Azure/Google principalmente a través del plugin `umbral-worker`.
> - El estado validado y los resultados E2E quedaron documentados en [docs/audits/vps-openclaw-llm-audio-validation-2026-03-08.md](audits/vps-openclaw-llm-audio-validation-2026-03-08.md).

> **Actualización 2026-04-19 — modelo y tools por rol:**
> Las secciones 2, 3 y 4 de este documento (asignación de modelos y JSON de `agents.list`) reflejan la configuración planeada a 2026-03-08 y ya no coinciden con el runtime actual. El runtime real migró a `azure-openai-responses/gpt-5.4` como primary para orchestrator, delivery y qa.
>
> **Fuente canónica para tools y modelo por runtime role:** cada `ROLE.md` en `openclaw/workspace-agent-overrides/<agent>/ROLE.md` (PR #227). La fuente canónica para la config viva es `~/.openclaw/openclaw.json` en la VPS.
>
> Las secciones 1 (skill deployment) y 5 (Kimi-K2.5 setup) siguen vigentes.

## 1. Que Rick tenga el skill `openclaw-gateway`

El skill está en el repo en `openclaw/workspace-templates/skills/openclaw-gateway/`. Para que Rick lo use en la VPS, debe existir en `~/.openclaw/workspace/skills/openclaw-gateway/` (workspace de Rick).

### Opción A — Desde tu máquina (con SSH/SCP al VPS)

Solo si estás en **tu PC (Windows)** y quieres subir los skills por SCP. Necesitas `VPS_HOST` (ej. `vps-umbral` o `rick@IP`) o pasar `--vps-host`:

```bash
cd c:\GitHub\umbral-agent-stack
python scripts/sync_skills_to_vps.py --dry-run   # ver lista de skills
python scripts/sync_skills_to_vps.py --execute   # copia todos los skills al VPS
```

Eso copia **todos** los skills del repo a `~/.openclaw/workspace/skills/` en la VPS, incluido `openclaw-gateway`. Si solo quieres ese:

```bash
scp -r openclaw/workspace-templates/skills/openclaw-gateway USUARIO@VPS_HOST:~/.openclaw/workspace/skills/
```

### Opción B — Directamente en la VPS (tras git pull)

En la VPS (Linux) usa rutas Unix y `python3`; **no** uses rutas tipo `c:\` ni el comando `python`:

```bash
cd ~/umbral-agent-stack
git pull origin main
mkdir -p ~/.openclaw/workspace/skills
cp -r openclaw/workspace-templates/skills/openclaw-gateway ~/.openclaw/workspace/skills/
ls -la ~/.openclaw/workspace/skills/openclaw-gateway/SKILL.md
```

Tras eso, OpenClaw cargará el skill desde `<workspace>/skills` (prioridad sobre managed/bundled). No hace falta reiniciar el gateway; el próximo turno que necesite configurar agentes/sesiones/workspace lo tendrá disponible.

*Nota: `sync_skills_to_vps.py` está pensado para ejecutarse desde tu PC; en la VPS usa la Opción B (cp).*


---

## 2. Asignación de modelos por agente (Vertex vs AI Foundry)

> **Superseded (2026-04-19).** La tabla y recomendaciones de esta sección reflejan el plan de 2026-03-08. El runtime actual usa `azure-openai-responses/gpt-5.4` como primary para orchestrator, delivery y qa. Consultar cada `ROLE.md` en `openclaw/workspace-agent-overrides/<agent>/ROLE.md` para el estado observado actual. Se conserva el contenido original abajo como referencia histórica.

En tu config ya tienes:

- **Vertex:** `google-vertex/gemini-2.5-flash` disponible para herramientas del Worker.
- **OpenAI Codex:** `openai-codex/gpt-5.4` (primary) y `gpt-5.3-codex`.
- **Anthropic / Google** en fallbacks.

“AI Foundry” en tu stack suele referirse a **Azure AI Foundry** (Azure OpenAI). Si en OpenClaw tienes un provider de Azure/Foundry configurado en auth y en `agents.defaults.models`, puedes asignar ese modelo a los agentes que quieras. Si aún no, dejas esos agentes con el primary o con Vertex.

### Recomendación por rol

| Agente              | Modelo recomendado        | Motivo |
|---------------------|----------------------------|--------|
| **main**            | primary (gpt-5.4)          | Cara al usuario; mantener default. |
| **rick-orchestrator** | **AI Foundry** (Azure)    | Planificación y delegación; modelo fuerte en mismo ecosistema. |
| **rick-delivery**   | **Vertex**                 | Ejecución y artefactos; Gemini va bien en tareas estructuradas. |
| **rick-qa**         | **Vertex**                 | Validación y DoD; consistencia. |
| **rick-tracker**    | **Google 2.5 Flash**      | Linear, issues, trazabilidad; respuestas cortas y estructuradas con provider ya autenticado en OpenClaw. |
| **rick-ops**        | **AI Foundry** (Azure)     | Operación VPS/runbooks; mismo tenant que el resto de Azure. |

- **Google 2.5 Flash** → rick-tracker.
- **Vertex** → usarlo desde `llm.generate` / `umbral_llm_generate` cuando se necesite la cuota GCP del Worker.
- **AI Foundry (Azure OpenAI / Foundry)** → rick-orchestrator, rick-ops.

Si aún no tienes el provider de Azure/Foundry en OpenClaw, deja rick-orchestrator y rick-ops con el primary (`openai-codex/gpt-5.4`) o con Vertex hasta que lo configures.

---

## 3. JSON de `agents.list` con modelos por agente

> **Superseded (2026-04-19).** Este JSON refleja el plan de 2026-03-08 (Gemini/Vertex para delivery y qa). La config viva en `~/.openclaw/openclaw.json` ya divergió. No usar este bloque como referencia para editar la config actual. Se conserva como referencia histórica.

Pega este bloque dentro de `agents` en tu `openclaw.json` (sustituye o fusiona con tu `agents.list` actual). Los que no llevan `model` heredan el default (primary + fallbacks).

```json
"agents": {
  "defaults": {
    "model": {
      "primary": "openai-codex/gpt-5.4",
      "fallbacks": [
        "openai-codex/gpt-5.3-codex",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
        "anthropic/claude-haiku-4-5",
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "google-vertex/gemini-2.5-flash"
      ]
    },
    "models": { ... },
    "workspace": "/home/rick/.openclaw/workspace",
    "contextPruning": { "mode": "cache-ttl", "ttl": "1h" },
    "compaction": { "mode": "safeguard" },
    "heartbeat": { "every": "1h" }
  },
  "list": [
    {
      "id": "main",
      "default": true,
      "name": "Rick Main",
      "workspace": "/home/rick/.openclaw/workspace"
    },
    {
      "id": "rick-orchestrator",
      "name": "Rick Orchestrator",
      "workspace": "/home/rick/.openclaw/workspace",
      "model": "openai-codex/gpt-5.4"
    },
    {
      "id": "rick-delivery",
      "name": "Rick Delivery",
      "workspace": "/home/rick/.openclaw/workspace",
      "model": "google/gemini-2.5-flash"
    },
    {
      "id": "rick-qa",
      "name": "Rick QA",
      "workspace": "/home/rick/.openclaw/workspace",
      "model": "google-vertex/gemini-2.5-flash"
    },
    {
      "id": "rick-tracker",
      "name": "Rick Tracker",
      "workspace": "/home/rick/.openclaw/workspace",
      "model": "google-vertex/gemini-2.5-flash"
    },
    {
      "id": "rick-ops",
      "name": "Rick Ops",
      "workspace": "/home/rick/.openclaw/workspace",
      "model": "openai-codex/gpt-5.4"
    }
  ]
}
```

- **Google 2.5 Flash** (`google/gemini-2.5-flash`): rick-tracker.
- **Vertex** (`google-vertex/gemini-2.5-flash`): disponible como provider del Worker para `llm.generate`, no como modelo base obligatorio del agente.
- **Primary por ahora** (`openai-codex/gpt-5.4`): rick-orchestrator, rick-ops — cuando tengas el provider de **Azure AI Foundry** en OpenClaw, sustituye por el id de ese modelo (ej. `azure-openai/gpt-4o` o el que tengas en auth/defaults).
- **main** sigue con el default (gpt-5.4 + fallbacks).

---

## 4. Resumen

> **Superseded (2026-04-19).** Este resumen refleja el plan original. Para el estado actual de modelo y tools por rol, ver cada `ROLE.md` en `openclaw/workspace-agent-overrides/<agent>/ROLE.md`.

1. **Skill para Rick:** copiar `openclaw/workspace-templates/skills/openclaw-gateway` a `~/.openclaw/workspace/skills/` en la VPS (Opción A con `sync_skills_to_vps.py` o Opción B con `cp` tras `git pull`).
2. **Google 2.5 Flash:** rick-tracker.
3. **Vertex en el Worker:** disponible para `llm.generate` / `umbral_llm_generate` cuando quieras usar la cuota GCP.
4. **AI Foundry (cuando lo tengas):** rick-orchestrator, rick-ops; mientras tanto usan primary (gpt-5.4).

---

## 5. Agregar Kimi-K2.5 (Azure Cognitive Services)

Endpoint: `https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5/chat/completions?api-version=2024-05-01-preview`

### Dónde poner la clave

- **Recomendado (daemon OpenClaw):** en la VPS, en `~/.openclaw/.env` (el gateway la lee al arrancar):
  ```bash
  echo 'KIMI_AZURE_API_KEY=TU_CLAVE_AQUI' >> ~/.openclaw/.env
  ```
  Sustituye `TU_CLAVE_AQUI` por la clave que muestra el portal de Azure (Detalles → Clave; icono de copiar).

- **Alternativa:** si el gateway se levanta con variables de `~/.config/openclaw/env`, añade ahí:
  ```bash
  echo 'export KIMI_AZURE_API_KEY="TU_CLAVE_AQUI"' >> ~/.config/openclaw/env
  ```
  Luego reinicia el gateway para que cargue la variable.

- **Por agente (auth-profiles.json):** si prefieres no usar env global, la clave puede ir en `~/.openclaw/agents/<agentId>/agent/auth-profiles.json` del agente que use Kimi; la estructura depende del runtime (ver [Authentication - OpenClaw](https://docs.openclaw.ai/gateway/authentication)). Lo más simple es usar `~/.openclaw/.env` como arriba.

### Config en `openclaw.json`

En OpenClaw el modelo se referencia como **`azure-openai-responses/kimi-k2.5`**. Añade o ajusta el provider `azure-openai-responses` dentro de `models.providers`:

```json
"models": {
  "mode": "merge",
  "providers": {
    "azure-openai-responses": {
      "baseUrl": "https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5",
      "api": "openai-responses",
      "auth": "api-key",
      "apiKey": "${KIMI_AZURE_API_KEY}",
      "headers": {
        "api-key": "${KIMI_AZURE_API_KEY}"
      },
      "models": [
        { "id": "kimi-k2.5", "name": "Kimi K2.5 (Azure)" }
      ]
    }
  }
}
```

Azure Cognitive Services usa el header `api-key` (no `Authorization: Bearer`); por eso está `headers.api-key`. Si tu versión de OpenClaw ya envía la clave en ese header con `auth: "api-key"`, puedes probar primero sin el bloque `headers` y añadirlo solo si falla con 401.

Si el gateway exige `api-version` en la URL, usa en su lugar:
`"baseUrl": "https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5?api-version=2024-05-01-preview"`

**Si no funciona con `api: "openai-responses"`:** prueba con el adaptador estándar de chat y base URL por deployment:
```json
"azure-openai-responses": {
  "baseUrl": "https://cursor-api-david.cognitiveservices.azure.com/openai/v1",
  "api": "openai-completions",
  "auth": "api-key",
  "apiKey": "${KIMI_AZURE_API_KEY}",
  "headers": {
    "api-key": "${KIMI_AZURE_API_KEY}"
  },
  "models": [
    { "id": "kimi-k2.5", "name": "Kimi K2.5 (Azure)" }
  ]
}
```
En Azure el nombre del deployment en la petición debe coincidir con el del portal (`Kimi-K2.5`). Si el runtime envía `model: "kimi-k2.5"` y Azure rechaza, puede que el provider deba mapear el id a `Kimi-K2.5` (consulta la doc de tu versión de OpenClaw).

### Instrucciones en el portal de Azure (campo «Instrucciones»)

En la ficha del deployment Kimi-K2.5 → **Instrucciones**, pega algo como:

```
Eres un asistente de IA del stack Umbral. Ayudas con ejecución de tareas (Delivery), validación de calidad (QA) y operación de sistemas (Ops: runbooks, VPS, VM). Responde en español. Sé conciso y orientado a resultados. Las instrucciones detalladas de cada agente (Rick Delivery, QA, Ops) las recibe por contexto del workspace de OpenClaw; aquí solo se define el tono y el idioma.
```

Versión más corta (si el campo tiene límite):

```
Asistente de IA del stack Umbral. Ayudas en tareas de ejecución, validación y operación. Responde en español. Sé conciso.
```

### Probar desde Python (OpenAI SDK)

Para validar el endpoint y la clave sin OpenClaw:

```python
from openai import OpenAI
import os

# Usar cognitiveservices.azure.com (no openai.azure.com) si tu recurso es Cognitive Services
endpoint = "https://cursor-api-david.cognitiveservices.azure.com/openai/v1/"
deployment_name = "Kimi-K2.5"
api_key = os.environ.get("KIMI_AZURE_API_KEY", "<your-api-key>")

client = OpenAI(base_url=endpoint, api_key=api_key)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[{"role": "user", "content": "What is the capital of France?"}],
    temperature=0.7,
)

print(completion.choices[0].message.content)
```

Si tu recurso está en el dominio `*.openai.azure.com`, cambia `endpoint` a `https://cursor-api-david.openai.azure.com/openai/v1/`.

### Kimi como recurso solo (no para agentes en Telegram)

En la práctica Kimi **no se puede elegir** como modelo desde el chat de Telegram/OpenClaw (no aparece en el selector). Se deja como **recurso solo para uso por API**: automatizaciones con n8n, scripts o el Worker cuando Rick (u otro flujo) necesite llamar a Kimi sin pasar por el chat.

- **En `openclaw.json`:** Mantén el provider `azure-openai-responses` en `models.providers` (endpoint y clave). **No** asignes `model: "azure-openai-responses/kimi-k2.5"` en `agents.list`; los agentes de chat usan Codex 5.3, GPT 5.4, Gemini, etc.
- **Uso desde n8n/scripts:** Llamar al endpoint de Azure por HTTP o usar `scripts/test_kimi_azure.py` como referencia. Ver **`docs/kimi-recurso-n8n.md`** para URL, headers y cuerpo para n8n.

### Si no funciona: checklist

1. **Variable de entorno:** En la VPS, `grep KIMI_AZURE_API_KEY ~/.openclaw/.env` o `~/.config/openclaw/env` debe mostrar la clave (sin mostrarla en logs). Reinicia el gateway después de añadirla: `systemctl --user restart openclaw`.
2. **Adaptador:** Si falla con `api: "openai-responses"`, cambia a `api: "openai-completions"` y `baseUrl` a `https://cursor-api-david.cognitiveservices.azure.com/openai/v1` (ver bloque alternativo arriba).
3. **Header api-key:** Azure exige el header `api-key`. Si ves 401, asegura que en el provider tengas `headers: { "api-key": "${KIMI_AZURE_API_KEY}" }`.
4. **Nombre del deployment:** El id del modelo en OpenClaw es `kimi-k2.5` (minúsculas); en Azure el deployment se llama `Kimi-K2.5`. Si tu runtime envía el id tal cual, Azure puede requerir exactamente `Kimi-K2.5` — en ese caso en `models` usa `{ "id": "Kimi-K2.5", "name": "Kimi K2.5 (Azure)" }` para que el id coincida con el portal.
5. **Probar fuera de OpenClaw:** Ejecuta el script Python de la sección «Probar desde Python» en la VPS con `KIMI_AZURE_API_KEY` exportada; si ahí falla, el problema es clave/endpoint/firewall, no OpenClaw.
