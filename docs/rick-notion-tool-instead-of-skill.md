# Notion como Tool (no Skill) en OpenClaw

> Rick indica que Notion debe configurarse como **Herramienta (Tool)**, no como Skill. Las Skills son directrices de uso; las Tools son capacidades que el sistema invoca directamente (como `read` o `browser`).

---

## 1. Diferencia Tool vs Skill

| Tipo   | Descripción                                                                 |
|--------|-----------------------------------------------------------------------------|
| **Tool** | Capacidad que el agente invoca directamente (read, browser, exec, Worker tasks) |
| **Skill** | Directriz/documentación (SKILL.md) que enseña cuándo y cómo usar herramientas |

**Notion en Umbral:** Las tareas `notion.*` son ejecutadas por el **Worker** y documentadas en `TOOLS.md`. Rick las invoca delegando al Dispatcher → Worker. Eso es la "herramienta" Notion.

---

## 2. Quitar el skill de Notion

### 2.1 Desde el dashboard (Control UI)

1. Conecta al dashboard: túnel SSH `ssh -N -L 18789:127.0.0.1:18789 rick@VPS_IP` y abre `http://localhost:18789`.
2. Entra en **Config** (editar `~/.openclaw/openclaw.json`).
3. Busca la sección `skills.entries` y elimina la entrada `notion` si existe:

   ```json
   "skills": {
     "entries": {
       "notion": { ... }   // ← ELIMINAR este bloque
     }
   }
   ```

4. Aplica los cambios (botón Apply / config.apply) y reinicia si lo pide.

### 2.2 Desde la VPS (CLI)

Edita `~/.openclaw/openclaw.json` y elimina `skills.entries.notion`:

```bash
# Backup
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak

# Editar (usa nano, vim o tu editor)
nano ~/.openclaw/openclaw.json
```

### 2.3 Quitar la carpeta del skill instalada (si usaste clawhub)

Si instalaste el skill con `clawhub install notion`, la carpeta está en el workspace:

```bash
rm -rf ~/.openclaw/workspace/skills/notion
```

(La carpeta puede estar en `~/.openclaw/skills/` o `~/.openclaw/workspace/skills/` según tu configuración.)

---

## 3. Configurar Notion como herramienta (Tool)

**Notion como Tool = Worker tasks** `notion.*`. No hace falta un plugin de OpenClaw; el Worker ya ejecuta las tareas.

### 3.1 Qué debe estar configurado

| Variable                   | Dónde                  | Uso                              |
|----------------------------|------------------------|----------------------------------|
| `WORKER_URL`               | `~/.config/openclaw/env` | URL del Worker (VPS o VM)       |
| `WORKER_TOKEN`             | `~/.config/openclaw/env` | Token Bearer para el Worker     |
| `NOTION_API_KEY`           | Worker (env del Worker)  | Token de integración Notion     |
| `NOTION_CONTROL_ROOM_PAGE_ID` | Worker               | Página Control Room por defecto |
| `NOTION_DASHBOARD_PAGE_ID` | Worker (opcional)        | Dashboard Rick                  |

Rick aprende de `TOOLS.md` y `AGENTS.md` en el workspace que puede invocar `notion.add_comment`, `notion.poll_comments`, etc. El Dispatcher encola en Redis y el Worker ejecuta.

### 3.2 Dashboard: verificar configuración

- **Config**: Revisa `openclaw.json` y asegúrate de que no haya `skills.entries.notion`.
- **Skills**: No añadas Notion como skill; no lo necesitas.
- **Tools**: OpenClaw no tiene un plugin "Notion" nativo. La capacidad Notion viene del Worker vía Dispatcher.

---

## 4. Referencias

- **Worker tasks Notion**: `worker/tasks/notion.py`, `worker/notion_client.py`
- **TOOLS.md**: Documenta las tasks disponibles, incluida la familia `notion.*`
- **Config Reference**: https://docs.openclaw.ai/gateway/configuration-reference
- **Plugin Agent Tools**: https://docs.openclaw.ai/plugins/agent-tools — para crear un plugin propio que registre tools (avanzado)
