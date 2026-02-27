# 22 — Dashboard gerencial en Notion (Dashboard Rick)

## Objetivo

Un **dashboard siempre actualizado** en Notion para que vos (o alguien no técnico) vea el estado del proyecto Umbral a nivel gerencial. La página se llama **Dashboard Rick** y puede seguir siendo privada (solo visible para quien vos definas); el sistema la actualiza vía API usando la integración de Notion.

## Qué es Control Room

**Control Room** es la **página de Notion** que usamos como centro de comunicación entre Rick (el stack en la VPS), el agente de Notion "Enlace Notion ↔ Rick" y vos. Ahí se hacen comentarios: Rick escribe y Enlace lee cuando corre; Enlace deja mensajes y el poller de Rick los lee a las XX:10. El ID de esa página es `NOTION_CONTROL_ROOM_PAGE_ID`. Puede ser la misma página "OpenClaw" o otra que elijas como sala de control. El **Dashboard Rick** es una página **distinta**, solo para mostrar el estado (métricas); no se usa para comentarios.

## Página e integración configuradas

- **URL:** [Dashboard Rick](https://www.notion.so/umbralbim/Dashboard-Rick-0fd13978b220498e9465b4fb2efc5f4a)
- **ID de página (para NOTION_DASHBOARD_PAGE_ID):** `0fd13978-b220-498e-9465-b4fb2efc5f4a`
- **Integración en Notion:** "Dashboard Rick" (integraciones internas). Tiene acceso a la página Dashboard Rick bajo OpenClaw; permisos: leer/actualizar/insertar contenido y comentarios.
- **Llave de integración:** Configurarla **solo en el entorno** (VPS/VM) como `NOTION_API_KEY`. No commitearla nunca. Si esta integración es solo para el dashboard, usala en el Worker que actualiza el dashboard; si ya tenés otra integración para Control Room, podés usar la misma y darle acceso a ambas páginas.

## Revisión de la página actual

**No puedo ver el contenido** de tu página [OpenClaw en Notion](https://www.notion.so/umbralbim/OpenClaw-30c5f443fb5c80eeb721dc5727b20dca) (es privada). Lo que el repo asume:

- Es la **Control Room** (o la contiene): ahí se hacen comentarios y el poller de Rick lee a las XX:10; Enlace Notion ↔ Rick también trabaja en ese alcance (doc [18](18-notion-enlace-rick-convention.md)).
- El Worker usa `NOTION_CONTROL_ROOM_PAGE_ID` para `notion.add_comment` y `notion.poll_comments`.

**Qué comprobar / modificar (vos o la IA de Notion):**

1. **Que la página siga siendo la Control Room** para comentarios (misma página que tiene `NOTION_CONTROL_ROOM_PAGE_ID` en el Worker). Si movés cosas, actualizá ese ID en el entorno del Worker (VPS/VM).
2. **Separar “comunicación” de “dashboard”** (recomendado):
- Crear una página dedicada **“Dashboard Rick”** (subpágina de OpenClaw o donde prefieras). Esa página será **privada** como el resto del workspace; el sistema la actualiza vía API usando la integración de Notion (`NOTION_API_KEY`). Solo hace falta que esa integración tenga acceso a la página.

---

## Contenido sugerido del dashboard (vista gerencial)

Para alguien no informático, conviene mostrar:

| Bloque / Campo | Descripción | Origen de los datos |
|----------------|-------------|----------------------|
| **Última actualización** | Fecha y hora del último refresh | VPS al ejecutar el job |
| **Estado general** | Verde / Amarillo / Rojo + una frase (ej. “Operativo”, “Solo VPS”, “Revisar”) | Regla a partir de Worker, VM, Redis, sprints |
| **Sprints** | Tabla o lista: S0–S7 con estado (Hecho / En progreso / Pendiente) | Repo (README o `docs/11-roadmap-next-steps.md`) o fichero generado |
| **Worker VPS** | OK / Error | Health del Worker local (VPS) |
| **Worker VM** | OK / No disponible | Health del Worker VM si `WORKER_URL_VM` está configurado |
| **Cola (Redis)** | Ej. “3 pendientes” o “Vacía” | Redis desde VPS |
| **Tareas recientes (agentes)** | Resumen de últimas tareas (ej. “001 y 002 completadas”) | Repo `.agents/board.md` o Redis |

Si preferís **una base de datos** en Notion (tabla “Dashboard”):

- **Métrica** (nombre), **Valor** (texto), **Actualizado** (fecha).
- El script/VPS crea o actualiza filas (una por métrica). Vista por defecto: tabla, ordenada por “Actualizado” o por un orden fijo de filas.

---

## Cómo mantener el dashboard actualizado

Dos enfoques posibles; el recomendado es el **1**.

### 1. Actualización desde la VPS (recomendado)

- **Qué hace:** Un job en la VPS (cron o systemd timer) cada X minutos (ej. 15–30) que:
  1. Recoge estado (Worker local, Redis, opcionalmente VM, y si tenés un fichero de estado en el repo o lo generáis).
  2. Llama al Worker (localhost) con una tarea tipo `dashboard.report` (o `notion.update_dashboard`) que escribe en Notion (base de datos o página del dashboard) vía Notion API.
- **Ventajas:** La VPS tiene la verdad (Redis, health, servicios). No dependés de que un agente de Notion “decida” cuándo correr; el cron es predecible.
- **Requisitos:** Notion API key y ID de página o de base de datos del dashboard en el entorno del Worker (VPS). El Worker ya usa Notion para comentarios; es la misma integración, solo otra página/DB.

Referencia Notion API: [Append block children](https://developers.notion.com/reference/patch-block-children), [Update a block](https://developers.notion.com/reference/update-a-block); para bases de datos, crear/actualizar páginas (filas) en esa DB.

### 2. Automatización con un agente de Notion (MCP / programado)

- **Qué hace:** Un Custom Agent en Notion que se ejecuta cada X tiempo (o al recibir un correo, etc.), y que:
  - Con **MCP conectado a GitHub** ([MCP connections for Custom Agents](https://www.notion.com/help/mcp-connections-for-custom-agents)) puede leer el repo (p. ej. `.agents/board.md`, README, o un `status.json` que la VPS suba al repo).
  - Con esa información, el agente actualiza una página o base de datos “Dashboard” en Notion.
- **Ventajas:** Todo dentro de Notion; podés combinar con otros disparadores (email, etc.).
- **Limitaciones:** El estado “en vivo” (Redis, health de Worker/VM) no está en GitHub; solo podrías mostrar lo que la VPS haya volcado al repo (p. ej. un `status.json` que un cron en la VPS genere y haga commit/push). Además, cada conexión MCP es por agente y requiere plan Business/Enterprise.

**Conclusión:** Para un dashboard **siempre actualizado** con datos de la VPS (cola, health, VM), la opción más directa es **1 (VPS + Notion API)**. La opción 2 sirve como complemento (p. ej. que el agente lea el repo y añada resúmenes de commits o de tareas de `.agents/` si eso lo generamos desde la VPS).

---

## Qué implementamos en el repo

1. **Config:** Variable de entorno `NOTION_DASHBOARD_PAGE_ID` (ID de la subpágina o página que actúa como dashboard). El Worker la usa solo para la tarea `notion.update_dashboard`.
2. **Worker:** Tarea `notion.update_dashboard`: recibe `input.metrics` (dict nombre → valor), archiva el contenido actual de esa página y escribe un nuevo bloque con “Última actualización” + todas las métricas (doc 22). Handlers en `worker/notion_client.py` y `worker/tasks/notion.py`.
3. **VPS:** Script `scripts/dashboard_report_vps.py` que recoge estado (Worker local, Redis cola pendiente, opcional Worker VM, resumen de sprints desde README) y llama al Worker con `notion.update_dashboard`. Ejecutarlo por cron o systemd timer cada 15–30 min.

**Variables necesarias en la VPS** (donde corre el Worker y/o el script):

- Para el Worker: `NOTION_API_KEY`, `NOTION_DASHBOARD_PAGE_ID` (y las que ya usa: `NOTION_CONTROL_ROOM_PAGE_ID`, etc.).
- Para el script: `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL`; opcional `WORKER_URL_VM`.

**Ejemplo de cron (cada 30 min):**

```bash
# Cargar env (ej. desde ~/.config/openclaw/env)
cd ~/umbral-agent-stack && source .venv/bin/activate && export $(grep -v '^#' ~/.config/openclaw/env | xargs) && export PYTHONPATH=. && python scripts/dashboard_report_vps.py
```

Con eso el dashboard en Notion queda actualizado desde la VPS y la Control Room sigue siendo solo el canal de comunicación Rick ↔ Enlace.

---

## Webhooks de Notion (opcional)

Los [webhooks de Notion](https://developers.notion.com/reference/webhooks) sirven para que **Notion avise a tu servidor** cuando algo cambia (p. ej. página editada, comentario nuevo). Para el **Dashboard Rick** no hacen falta: nosotros **empujamos** el estado desde la VPS cada X minutos. Los webhooks serían útiles si quisieras que la VPS reaccione en tiempo real a cambios en Notion (p. ej. un comentario nuevo en Control Room sin esperar al poll de las XX:10). Para eso necesitarías un endpoint público (HTTPS) en la VPS que reciba el POST de Notion, verificar la firma con el `verification_token` y opcionalmente encolar una tarea. Por ahora el flujo de comentarios sigue con el poller; los webhooks se pueden añadir más adelante si los querés.

---

## Crear la página “Dashboard Rick” (privada)

La página **Dashboard Rick** debe crearla alguien con acceso al workspace (vos o la IA de Notion). El sistema no puede crear páginas en tu cuenta; solo puede **actualizar** una página que ya exista y a la que la integración de Notion tenga acceso.

### Pasos

1. **Crear la página:** En Notion, creá una **página nueva** llamada **Dashboard Rick** (por ejemplo como subpágina de OpenClaw o donde prefieras). Dejarla vacía o con un texto tipo “Actualizado por Rick cada X min”. La página puede seguir **privada** (mismo nivel de acceso que el resto de tu workspace).
2. **Dar acceso a la integración:** En Configuración de la página → Conectar con la **integración** que usa tu `NOTION_API_KEY` (la misma que usa el Worker para comentarios en Control Room). Así el Worker podrá escribir en Dashboard Rick sin que la página sea pública.
3. **Copiar el ID de la página:** Del enlace de la página, el ID es la parte después del nombre, antes de `?`:  
   `https://www.notion.so/umbralbim/Dashboard-Rick-XXXXXXXXXX` → el ID es `XXXXXXXXXX` (con guiones, 32 caracteres).
4. **Configurar en el Worker:** En el entorno del Worker (VPS/VM), añadí  
   `NOTION_DASHBOARD_PAGE_ID=el_id_que_copiaste`  
   (por ejemplo en `~/.config/openclaw/env`).

### Prompt para la IA de Notion

Si querés que la IA de Notion cree la página, podés pegarle esto:

> Creá una página nueva llamada **Dashboard Rick** como subpágina de OpenClaw (o de la página que usamos como Control Room). La página debe seguir siendo privada; solo tiene que estar conectada a la integración de Notion que usa el equipo para que el sistema pueda actualizar su contenido por API. No hace falta poner contenido inicial; el sistema lo reemplazará. Cuando esté creada, indicame el **ID de la página** (el que aparece en la URL, 32 caracteres con guiones) para configurarlo en el Worker.
