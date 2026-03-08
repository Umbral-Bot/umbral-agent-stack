# Mensajes para Rick (David / Cursor)

> Rick: cuando hagas `git pull` en la VPS, revisá este archivo por si hay instrucciones o avisos para vos.

---

## 2026-03-07 — Conectarte a la VM desde la VPS por SSH

Rick, conectate a la VM **desde la VPS** usando SSH. No necesitás contraseña; la clave `vps-umbral` ya está configurada en la VM.

### Cómo conectarte

**1. Abrí una terminal en la VPS** (SSH a rick@srv1431451 o `rick@100.113.249.25`).

**2. Ejecutá:**
```bash
ssh rick@100.109.16.40
```
Debería entrar directo (sin pedir contraseña). El prompt pasará a ser de la VM (ej. `rick@PCRick` o similar).

**3. Para salir de la VM:** escribí `exit`.

### Comandos útiles

| Acción | Comando |
|--------|---------|
| Entrar a una sesión en la VM | `ssh rick@100.109.16.40` |
| Ejecutar un solo comando sin entrar | `ssh rick@100.109.16.40 "hostname"` |
| Ejecutar PowerShell en la VM | `ssh rick@100.109.16.40 "powershell -Command \"Get-ComputerName\""` |

**IP de la VM:** `100.109.16.40` (PCRick por Tailscale). Si la VM está apagada o Tailscale desconectado, el SSH hará timeout.

Documentación: [62-operational-runbook.md](../docs/62-operational-runbook.md) sección 7.2.1.

---

## 2026-03-08 — Token y herramientas

### Token (WORKER_TOKEN)

Sí, procedé con la corrección. El token en `~/.config/openclaw/env` debe coincidir en:
- Worker VPS (localhost:8088)
- Dispatcher
- Worker VM (100.109.16.40:8088)

Actualizá `WORKER_TOKEN` en `~/.config/openclaw/env` al valor que acepta el Worker VPS, reiniciá Dispatcher (y Worker VPS si hace falta) para que las actualizaciones a Notion (Bandeja Puente, Dashboard, OODA) vuelvan a funcionar.

### Herramientas que podés usar

| Herramienta | Uso |
|-------------|-----|
| **notion** | Leer/escribir Notion vía API. Usá esta para leer páginas. |
| **read / write / edit** | Archivos locales en el workspace |
| **exec / process** | Comandos shell (local o remoto vía nodes) |
| **nodes** | Control de nodos remotos (ej. VM PCRick) |
| **memory_search / memory_get** | Búsqueda en memoria persistente |
| **message** | Enviar mensajes (Telegram, etc.) |
| **cron** | Programar tareas |
| **browser** | Fallará si no hay frontend gráfico en el entorno |

Para leer contenido de Notion: usá la herramienta **notion** (API), no browser. Si David necesita que leas una página, puede pedirte explícitamente "usa notion para leer la página X" o pegar el contenido.

### Rutas de Drive (VM)

- Reportes: `G:\Mi unidad\Rick-David\Perfil de David Moreira\Reportes_Mercado` (bulk_market_report.md, competitor_report.md)
- `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas` está vacía

### Agente Gpt-Rick (Azure AI Foundry)

Podés delegar tareas al agente **Gpt-Rick** vía Responses API. Endpoints:

- **Responses API:** `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/applications/Gpt-Rick/protocols/openai/responses?api-version=2025-11-15-preview`
- **Activity Protocol:** para Teams/M365.

**Variables:** `GPT_RICK_API_KEY` o `AZURE_OPENAI_API_KEY` en env. **Test:** `python3 scripts/test_gpt_rick_agent.py`
