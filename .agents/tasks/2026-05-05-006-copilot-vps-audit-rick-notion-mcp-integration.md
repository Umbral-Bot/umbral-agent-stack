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
