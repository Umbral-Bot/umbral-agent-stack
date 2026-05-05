# Task 006 — Audit MCP Notion integration de Rick (audit-only)

- **Created:** 2026-05-05
- **Assigned to:** Copilot VPS
- **Type:** read (audit-only, NO writes, NO restarts)
- **Blocking:** Ola 1b (diseño del primer caso cross-canal end-to-end)
- **Independent of:** task 005 (ya completada)

## Contexto

David confirmó que **Rick (runtime OpenClaw en VPS) tiene su propia MCP Notion integration** con su propio token, separada de:

1. La integration MCP que usa Copilot Chat desde Windows (`1f8d872b-594c-80a4-b2f4-00370af2b13f`).
2. El acceso Notion API directo del worker vía `NOTION_API_KEY` + `NOTION_*_DB_ID` (worker llama Notion REST API, no MCP).

Esa integration está **operativa** en la VPS pero **no está documentada en el repo**. Antes de diseñar Ola 1b necesitamos saber qué surfaces ve, con qué token, cómo se invoca desde los agents OpenClaw, y si requiere restricciones (David dijo "creo que le di acceso a todo").

**Esta task es audit-only.** NO modificar nada. NO reiniciar servicios. Solo recolectar evidencia y reportar.

## Objetivo

Producir un reporte completo en este mismo archivo (sección `## Resultado 2026-05-05`) que responda:

1. ¿Dónde vive la config de la MCP Notion integration de Rick? (path en VPS, archivo, sección)
2. ¿Cómo se invoca? (servidor MCP local, comando, transport stdio/http, puerto si aplica)
3. ¿Qué token usa? (variable de env o archivo — **NO copiar el valor**, solo el nombre/path)
4. ¿Qué pages/databases ve? (lista de IDs + títulos si la API los devuelve)
5. ¿Qué subagents OpenClaw la tienen declarada como tool? (`AGENTS.md`/`SKILL.md`/`TOOLS.md`/`agent.json` por subagent)
6. ¿Hay overlap funcional con `notion.upsert_*` del worker (NOTION_API_KEY)? ¿Cuál usar para qué?
7. Estado: ¿healthy / responde a un `list_resources` / `search` básico?
8. Recomendación de hardening: ¿hay surfaces que claramente NO debería ver? (ej: páginas personales de David fuera del workspace de Umbral)

## Pasos

### Paso 0 — sync repo (obligatorio)

```bash
cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
# Si hay cambios locales sin pushear, NO continuar con esta task antes de stash/commit.
git status --short
```

### Paso 1 — localizar config de la MCP integration

Buscar referencias a `notion` + `mcp` en lugares plausibles. Reportar findings (paths + snippets relevantes, **sin tokens**):

```bash
echo "=== 1.1 ~/.openclaw/openclaw.json — secciones mcp/notion ==="
jq '.. | objects | with_entries(select(.key | test("mcp|notion"; "i")))' ~/.openclaw/openclaw.json 2>&1 | head -80

echo "=== 1.2 ~/.openclaw/ — archivos mcp/notion ==="
find ~/.openclaw -maxdepth 4 -type f \( -iname "*mcp*" -o -iname "*notion*" \) 2>/dev/null | head -40

echo "=== 1.3 workspaces de subagents — refs MCP ==="
grep -rIli "notion.*mcp\|mcp.*notion" ~/.openclaw/workspace ~/.openclaw/workspaces 2>/dev/null | head -20

echo "=== 1.4 ~/.config/claude/ ~/.config/openclaw/ — settings MCP ==="
find ~/.config/claude ~/.config/openclaw -maxdepth 3 -type f \( -iname "*mcp*" -o -iname "settings.json" -o -iname "config.json" -o -iname "*.toml" \) 2>/dev/null | head -20
# Para cada match, mostrar SOLO claves relacionadas a notion (no valores de tokens):
# jq 'paths(scalars) as $p | select($p|tostring|test("notion";"i")) | $p' <archivo>

echo "=== 1.5 systemd user — servicios MCP ==="
systemctl --user list-units --all --no-pager 2>&1 | grep -iE "mcp|notion" | head -20
ls ~/.config/systemd/user/ 2>/dev/null | grep -iE "mcp|notion"

echo "=== 1.6 procesos vivos con 'notion' en cmdline ==="
ps -eo pid,user,cmd | grep -iE "notion|@notionhq" | grep -v grep | head -10
```

### Paso 2 — identificar el token (sin exponerlo)

```bash
echo "=== 2.1 vars de env mencionando NOTION (solo nombres) ==="
env 2>/dev/null | awk -F= '/NOTION/ {print $1}' | sort -u
grep -hE "^[A-Z_]*NOTION[A-Z_]*=" ~/.config/openclaw/env ~/.openclaw/env 2>/dev/null | awk -F= '{print "  " $1 " (length=" length($2) ")"}' || echo "(no matches)"

echo "=== 2.2 archivos que CONTENGAN secret_/ntn_ (token Notion patterns) — solo paths ==="
grep -rIl --exclude-dir=.git -E "secret_[A-Za-z0-9]{40,}|ntn_[A-Za-z0-9]{40,}" ~/.openclaw ~/.config 2>/dev/null | head -10
```

> **secret-output-guard**: NUNCA imprimir el valor del token. Solo nombre de var, path del archivo, longitud, y primeros 4 chars si hace falta diferenciar entre dos tokens distintos (`token[:4] + "***"`).

### Paso 3 — listar surfaces que la integration ve

Si encontraste el server MCP corriendo, intentar query básica. Si no, usar el token (vía la var, no copiándolo) contra Notion REST API directo:

```bash
echo "=== 3.1 search (page/db visibles) ==="
# Sustituir <VAR_DEL_TOKEN> por el nombre real encontrado en paso 2 (ej RICK_NOTION_TOKEN, NOTION_RICK_API_KEY, etc.)
TOKEN_VAR_NAME="<rellenar tras paso 2>"
TOKEN="${!TOKEN_VAR_NAME}"
[ -z "$TOKEN" ] && echo "ERROR: $TOKEN_VAR_NAME vacío en este shell" && exit 0

curl -s -X POST https://api.notion.com/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"page_size":50}' \
| jq '{count: (.results|length), results: [.results[] | {object, id, title: (.properties.Name.title[0].plain_text // .properties.title.title[0].plain_text // .child_page.title // .child_database.title // "(no title)"), url}]}'
```

### Paso 4 — declaración en subagents

```bash
echo "=== 4.1 subagents que declaran herramientas notion ==="
for ws in ~/.openclaw/workspace ~/.openclaw/workspaces/*/; do
  agent=$(basename "$ws")
  hits=$(grep -liE "notion\.(upsert|create|search|append|update)|mcp.*notion" "$ws"AGENTS.md "$ws"SKILL.md "$ws"TOOLS.md "$ws"IDENTITY.md 2>/dev/null | wc -l)
  if [ "$hits" -gt 0 ]; then
    echo "--- $agent ---"
    grep -hE "notion\.(upsert|create|search|append|update)|mcp.*notion" "$ws"*.md 2>/dev/null | sort -u | head -10
  fi
done
```

### Paso 5 — overlap worker vs MCP

```bash
echo "=== 5.1 worker handlers notion ==="
ls ~/umbral-agent-stack/worker/tasks/ 2>/dev/null | grep -i notion
echo "=== 5.2 NOTION_*_DB_ID en env (nombres) ==="
grep -hE "^NOTION_" ~/.config/openclaw/env 2>/dev/null | awk -F= '{print "  " $1}' | sort -u
```

### Paso 6 — append reporte

Append al final de este archivo una sección `## Resultado 2026-05-05` con:

- **6.1** Tabla: `surface | path/var | quién la consume`.
- **6.2** Diagrama de invocación de la MCP integration (¿server local? ¿spawn por agent? ¿remoto?).
- **6.3** Lista de page/db visibles del paso 3 (truncada a 50).
- **6.4** Lista de subagents que la usan (paso 4).
- **6.5** Overlap con worker (paso 5): qué hace cada uno, recomendación de "usar X para Y".
- **6.6** Health: ¿responde la API?, ¿el server está vivo en systemd/ps?
- **6.7** Recomendación de hardening (si la integration ve cosas claramente fuera de scope Umbral).
- **6.8** Open questions / lo que no pudiste verificar.

Después:

```bash
cd ~/umbral-agent-stack
git add .agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md
git -c user.name='copilot-vps' -c user.email='copilot-vps@users.noreply.github.com' \
  commit -m "report(.agents/006): audit MCP Notion integration de Rick (audit-only)"
git pull --rebase origin main
git push origin main
```

## Anti-patterns

- ❌ Imprimir, copiar, o pegar el valor del token Notion en logs/comments/reporte. Solo nombre de var + longitud.
- ❌ Hacer cualquier `POST`/`PATCH`/`DELETE` contra Notion API más allá del `/v1/search` de paso 3 (que es read-only).
- ❌ Reiniciar servicios. Esta task es audit-only.
- ❌ Editar IDENTITY.md, openclaw.json, env, o cualquier config. Solo lectura.
- ❌ Continuar si paso 0 (`git pull --ff-only`) falla.

## Notas

- Si paso 1 no encuentra nada plausible en `~/.openclaw/`, ampliar búsqueda a `~/.local/`, `/opt/`, o `~/code/`. Reportar dónde apareció.
- Si la integration vive como un MCP server npm-global (estilo `@notionhq/mcp-server-notion`), reportar versión: `npm ls -g --depth=0 2>/dev/null | grep -i notion`.
- Si encuentra que Rick tiene MÚLTIPLES integrations Notion (no solo una), listar todas con su scope respectivo.
- Si el reporte revela que la integration ve surfaces fuera de Umbral (ej: workspaces personales de David), recomendar pero NO ejecutar restricción — David decide.

---

## Resultado 2026-05-05

**Ejecutado por:** Copilot VPS (sesión Copilot Chat con shell local en VPS Hostinger `srv1431451`)
**Fecha/hora:** 2026-05-05 ~10:25 ART
**Modo:** AUDIT-ONLY. Cero escrituras a config/runtime. Único POST emitido: `https://api.notion.com/v1/search` (read-only).
**Branch:** `main` @ `3cbf344` (post sync `git pull --ff-only`).

### TL;DR (corrección de la premisa)

> La premisa de la task era "Rick tiene su propia MCP Notion integration en VPS". **Esa premisa no se sostiene en runtime.**

- `openclaw mcp list` → **"No MCP servers configured in /home/rick/.openclaw/openclaw.json"**.
- `openclaw mcp show` → `{}`.
- No hay ningún server `@notionhq/*` en npm-global, ni proceso MCP Notion vivo, ni unit systemd, ni archivo `mcp.json` / `claude_desktop_config.json` en el host.

Lo que **sí existe** en runtime es **dos Notion integrations vía REST API directa** (no MCP), consumidas por el worker FastAPI y por agents OpenClaw a través de tasks `notion.*` que el worker expone. Esto es lo que David probablemente recordaba como "MCP Notion de Rick".

---

### 6.1 Tabla — surface | path/var | quién la consume

| Surface / capacidad | Mecanismo | Token (var) | Quién la consume |
|---|---|---|---|
| Notion REST API (escritura masiva) | HTTP a `https://api.notion.com/v1/...` desde Python | `NOTION_API_KEY` (en `~/.config/openclaw/env`, len 50, prefix `ntn_***`) — bot **"Rick"** owner=workspace **Umbral BIM** | Worker (`worker/tasks/notion.py`) + dispatcher poller + scripts `scripts/vps/*notion*` |
| Notion REST API (escritura "supervisor") | HTTP idem | `NOTION_SUPERVISOR_API_KEY` (idem env, len 50, prefix `ntn_***`) — bot **"Supervisor"** owner=workspace **Umbral BIM** | Worker (paths supervisor/alert) — handler `supervisor_notion_alert` y similares |
| MCP Notion (estilo `@notionhq/mcp-server-notion`) | **NO EXISTE** | — | — |
| Skill `notion-project-registry` | Plugin OpenClaw declarado en `openclaw.json → skills.entries.notion-project-registry.enabled=true` | (heredado del worker) | Subagents al cargar skill |
| 13× `NOTION_*_DB_ID` y `NOTION_*_PAGE_ID` | env vars (path IDs únicamente, no secretos) | n/a | Worker handlers para targets fijos |

### 6.2 Diagrama de invocación

```
Subagent OpenClaw (rick-orchestrator/delivery/qa/tracker/ops)
   │
   │  declara en TOOLS.md:  notion.upsert_task / .update_dashboard / .create_report_page / .search_databases / .update_page_properties / ...
   ▼
OpenClaw gateway → dispatcher (ACP) → worker FastAPI (127.0.0.1:8088)
   │
   │  worker/tasks/notion.py + worker/notion_client.py
   ▼
HTTP Bearer  ──►  api.notion.com/v1/*   (NOTION_API_KEY=Rick bot)
                                         (NOTION_SUPERVISOR_API_KEY=Supervisor bot, paths puntuales)
```

**No hay capa MCP.** No hay server intermedio MCP. No hay stdio MCP. Es REST puro encapsulado por el worker, con tools expuestos al agent vía el catálogo de tasks del dispatcher.

### 6.3 Surfaces visibles para `NOTION_API_KEY` (bot "Rick")

`POST /v1/search` (sin filtro) → `count=50, has_more=true` (umbral page_size). Filtrado por `object=database` → **38 databases visibles, has_more=false** (lista completa abajo). Filtrado por `object=page` con título no vacío en primer batch → 5 páginas notables (root del workspace).

**Bot identity:** `users/me` → `{"name":"Rick","type":"bot","bot":{"workspace_name":"Umbral BIM","owner_type":"workspace"}}`.

`owner_type=workspace` significa que el bot está instalado a nivel workspace y ve cualquier página/DB que un admin del workspace haya compartido explícitamente con la integration. **NO accede a workspaces personales de David fuera de "Umbral BIM"** salvo que David los haya compartido.

**38 databases visibles (id → título):**

```
3c1112c3-…  Asesorías & Proyectos                                         (parent=workspace)
f7bfe838-…  Sesiones · Sergio del Castillo
87eb54af-…  Sesiones — Copilot 365 WSP España
8e5a7afe-…  Sesiones · Rolando Cedeño
3e5fef57-…  Sesiones · Rafael Lucki
6acc8a7b-…  Sesiones · David Moreira
dd8c27d7-…  Bandeja de revisión - Rick
0b8f4be3-…  Entradas Bitácora
e39e9667-…  Encargos
e6817ec4-…  Publicaciones
62287647-…  Clases — Especialización IA + Automatización AEC (Konstruedu)
70e78d45-…  Sesiones — Power Automate WSP España
3265f443-…d7…  Transcripciones Granola
517bfeb9-…  Registro de Tareas y Próximas Acciones (= NOTION_TASKS_DB_ID? prefix coincide)
b8431e57-…  Clientes y Partners
ee199156-…  Cronograma Máster AEC 4.0
ad60d4a0-…  Activos reutilizables
9b8aba7e-…  Conceptos clave
bad212d8-…  Fuentes y Referencias
18d5ec3d-…  📦 Archivado — Proyectos / Charlas
c1e7c3b5-…  Archivo histórico — sesiones de trabajo Umbral BIM
3265f443-…c6…  Bandeja Puente
2755f443-…  Páginas
7d0e8029-…  Clases del Curso
32f5f443-…  Recursos Pedagógicos ia.butic.es — Alternativa ChatGPT
afda99a3-…  Tareas — Umbral Agent Stack
d4098fa4-…  Proyectos técnicos - Rick
8d5fc698-…  Webinars y Ponencias
05f04d48-…  Referentes
f4712b91-…  Comparativa Proveedores de Hormigón Premezclado — Chile
7e8a5a66-…  Evaluación Módulo 3 - Generación Visual & Multimedia (Notion Opus 4.6)
38496038-…  Clases - Programación Visual con Dynamo
dfc197ad-…  Evaluación Módulo 1 - Asistentes Personalizados
2b55f443-…  Casos de Estudio
2105f443-…  Diplomado BIM +IA
2395f443-…  Borrador Máster BIM + IA
2b45f443-…85…  Reportes
2b45f443-…0c…  Fuentes confiables
```

**Páginas top-level relevantes** (primer batch del search general):

```
30c5f443-…  OpenClaw                                  (= NOTION_CONTROL_ROOM_PAGE_ID prefix coincide)
3575f443-…  [SUPERSEDED] CAND-004 — Prototipo navegación editorial
445e4220-…  Iniciativa 1: Observatorio licitaciones públicas (versión Word para GT)
3345f443-…  GT Política, Regulación y Mandantes
37706b0b-…  Iniciativa 1 (unificada con 6) — Observatorio BIM en Mercado Público
```

(El resto del primer batch eran páginas-fila de databases sin "Name"/"title" property → aparecen como "(no title)"; son ruido del endpoint search, no surfaces nuevas.)

### 6.4 Subagents que declaran tools `notion.*` en TOOLS.md

| Agent | Tools declaradas |
|---|---|
| `rick-delivery` | `notion.upsert_task`, `notion.update_dashboard`, `notion.create_report_page` |
| `rick-ops` | idem 3 |
| `rick-qa` | idem 3 |
| `rick-tracker` | idem 3 |
| `rick-orchestrator` | las 3 anteriores + `notion.search_databases`, `notion.update_page_properties` (catálogo más amplio porque orquesta) |
| `rick-communication-director` | sin `notion.*` declarado pero IDENTITY/AGENTS menciona Notion (probablemente delega a delivery) |
| `rick-linkedin-writer` | sin `notion.*` declarado, sólo menciona Notion en contexto |
| `main` (Rick CEO) | sin `notion.*` declarado (post task 005 sólo delega a `rick-orchestrator`) |

**Importante:** todos los `notion.*` que aparecen son **tasks del worker** (despachadas por OpenClaw → dispatcher → worker REST), **no son tools MCP**. La diferencia es relevante para Ola 1b: si en algún momento se quiere exponer Notion como **MCP tool nativo del agent** (ej. para que el LLM lo use sin pasar por el dispatcher), eso **no existe hoy** y habría que crearlo.

### 6.5 Overlap "MCP" vs worker

No hay overlap real porque **no hay MCP**. Lo que existe es un solo path:

| Capacidad | Implementado en | Recomendación |
|---|---|---|
| Crear/actualizar tasks/pages/dashboards/reports | `worker/tasks/notion.py` (~1000 líneas, 11 handlers `handle_notion_*`) | **Usar siempre** — está testeado, tiene retries, schema rígido |
| Search libre Notion / lectura ad-hoc | `notion.search_databases`, `notion.read_page`, `notion.read_database` (también worker) | Usar para queries del orchestrator antes de decidir handler de escritura |
| Polling de comments / inbox Notion | `dispatcher/notion_poller.py` (proceso Python vivo: pid 409021) | Ya está corriendo. No tocar. |
| MCP tool nativo Notion para agents (LLM → tool call directo, sin worker) | **NO EXISTE** | Si Ola 1b lo necesita, hay que diseñar y añadir (ver §6.7-6.8) |

### 6.6 Health

- ✅ `api.notion.com/v1/users/me` con `NOTION_API_KEY` → 200 OK, bot "Rick" en workspace "Umbral BIM".
- ✅ `api.notion.com/v1/users/me` con `NOTION_SUPERVISOR_API_KEY` → 200 OK, bot "Supervisor" en workspace "Umbral BIM".
- ✅ `api.notion.com/v1/search` → 38 dbs + páginas devueltas correctamente.
- ✅ `notion-poller-daemon.py` (pid 409021, user rick) corriendo.
- ❌ No hay server MCP que health-checkear porque no hay MCP.

### 6.7 Recomendación de hardening

**Scope actual (visto por `Rick` bot):** todo "Umbral BIM" workspace incluyendo databases muy sensibles operativamente:

- `Sesiones · David Moreira`, `Sesiones · Sergio del Castillo`, `Sesiones · Rolando Cedeño`, `Sesiones · Rafael Lucki` — transcripciones de sesiones 1:1 con clientes
- `Clientes y Partners` — CRM
- `Encargos`, `Publicaciones` — pipeline editorial/comercial
- `Transcripciones Granola` — captura cruda de meetings

**Riesgo:** cualquier subagent (`rick-delivery`, `rick-ops`, `rick-qa`, `rick-tracker`) puede invocar `notion.upsert_task` o `notion.update_page_properties` con cualquier `page_id` que el bot vea. No hay allowlist de DBs por subagent en runtime — sólo la disciplina del prompt.

**Recomendaciones (NO ejecutadas, audit-only):**

1. **Allowlist de DBs por subagent** en el worker (`worker/tasks/notion.py`): tabla `agent_id → set(allowed_db_ids)`. `rick-delivery` no debería poder escribir en `Sesiones · David Moreira`. Ola 2.
2. **Separar bot** para escrituras en surfaces editoriales vs operativas. Hoy el mismo `Rick` token puede escribir en `Bandeja de revisión - Rick` y en `Sesiones · David Moreira`. Considerar 3er token con scope reducido para `rick-delivery` cuando expanda capacidades.
3. **Audit log de mutaciones Notion** del worker: hoy se loggea en `~/.config/umbral/ops_log.jsonl` (verificar). Asegurar que cada `upsert_task`/`update_page_properties` deja registro con `agent_id` solicitante.
4. **No** revocar acceso a las DBs editoriales sin antes implementar (1), porque rompe el pipeline Granola.

### 6.8 Open questions / no verificado

1. **¿David quiere que exista un MCP server Notion nativo en OpenClaw?** Hoy no existe. La task asumía que sí. Si la respuesta es "sí, agregarlo", es trabajo de Ola 1b/2 y deshace parcialmente la utilidad del worker.
2. **Falta confirmar si `notion-project-registry` (skill plugin OpenClaw) usa el mismo `NOTION_API_KEY`** o si tiene otro mecanismo. Hay que leer el código del plugin (no estaba en `~/.openclaw/`, probablemente bundled en el binario).
3. **Verificar si Copilot Chat de Windows tiene su propia integration Notion** (la del enunciado, `1f8d872b-…-2b13f`). No la audité porque no es runtime VPS. Si esa integration apunta al mismo workspace "Umbral BIM" hay otro bot más con permisos similares.
4. **3 archivos de sesión** (`~/.openclaw/agents/rick-orchestrator/sessions/*.jsonl`, `~/.openclaw/agents/rick-ops/sessions/*.jsonl`) **contienen patrones que matchean `secret_/ntn_`**: probablemente capturas de tool outputs históricos donde el token se loggeó accidentalmente. Recomendación: rotar ambos tokens y limpiar esos jsonl. **Reportado, no ejecutado** (audit-only).
5. **No verifiqué qué DB ID corresponde a cada `NOTION_*_DB_ID` env var**, aunque por prefijo se puede inferir (ej. `NOTION_TASKS_DB_ID=afda***` ↔ DB `afda99a3-… Tareas — Umbral Agent Stack`). Mapeo completo queda como side-task si hace falta.

### Decisión recomendada para Ola 1b

Antes de "diseñar el primer caso cross-canal end-to-end" suponiendo MCP, resolver con David:

> **¿"MCP Notion de Rick" significa (A) las dos integrations REST que ya existen (Rick + Supervisor), o (B) un server MCP estilo `@notionhq/mcp-server-notion` que aún no instalamos?**

Si es (A), Ola 1b puede arrancar ya: el subagent invoca `notion.*` task vía dispatcher, end-to-end.  
Si es (B), Ola 1b se bloquea en una task previa: "Instalar `@notionhq/mcp-server-notion` + registrar en `openclaw mcp set` + decidir token + decidir scope".

