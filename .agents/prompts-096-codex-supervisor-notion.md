# Prompt R19 — Codex: Supervisor Notion alert (096) + Pasos en el VPS

**Antes de empezar:** `git checkout main && git pull origin main`. Luego: `git checkout -b codex/096-supervisor-notion-alert`.

---

## Para Codex — Tarea 096

```
Tarea 096: verificar aviso Notion del supervisor y documentar. Sigue EXACTAMENTE .agents/tasks/2026-03-07-096-r19-supervisor-notion-alert.md.

Antes de empezar: git checkout main && git pull origin main. Luego: git checkout -b codex/096-supervisor-notion-alert.

IMPORTANTE: Trabaja SOLO en la rama codex/096-supervisor-notion-alert.

Haz solo:
1. Documentar en docs/62-operational-runbook.md (o en comentario del script) que para que el aviso Notion del supervisor funcione, el Worker debe tener: NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID (y opcionalmente page_id en el input si se usa otra página).
2. Si tienes acceso a VPS o local con Worker + Notion: verificar que POST /run con notion.add_comment devuelve 200 y que el comentario aparece en Control Room. Si no puedes ejecutar: deja la doc lista para que alguien verifique en VPS.
3. Abrir PR a main. Título: docs(R19-096): verificar/documentar aviso Notion del supervisor.

Solo documentación. No cambiar lógica del supervisor.
```

---

## Pasos en el VPS (qué hacer tú en el servidor)

Sigue esto en el VPS para aplicar el fix del supervisor y comprobar que el aviso a Notion funciona.

### 1. Traer el cambio del supervisor (URL /run)

```bash
cd ~/umbral-agent-stack
git pull origin main
```

Así el script usará **POST /run** en lugar de `/task`.

### 2. Variables de entorno del Worker (necesarias para Notion)

El Worker es quien ejecuta `notion.add_comment`. Tiene que tener en su entorno (el mismo que usa cuando arranca, p. ej. el que carga `supervisor.sh` desde `~/.config/openclaw/env`):

- **NOTION_API_KEY** — API key de Notion (Integration).
- **NOTION_CONTROL_ROOM_PAGE_ID** — ID de la página de Notion donde quieres que caigan los avisos (Control Room).

Comprueba que están en el archivo que usa el supervisor y el Worker:

```bash
# Ver qué archivo usa el supervisor (por defecto)
grep -E "NOTION_|WORKER_TOKEN" ~/.config/openclaw/env
```

Si faltan, añádelas a `~/.config/openclaw/env`:

```bash
# Ejemplo (sustituir por tus valores reales)
echo 'export NOTION_API_KEY="secret_xxx"' >> ~/.config/openclaw/env
echo 'export NOTION_CONTROL_ROOM_PAGE_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"' >> ~/.config/openclaw/env
```

El Worker debe arrancar **después** de que ese archivo tenga las variables (el supervisor hace `source` de ese archivo antes de levantar el Worker).

### 3. Reiniciar el Worker para que cargue las variables

Si acabas de añadir NOTION_* a `env`:

```bash
cd ~/umbral-agent-stack
source ~/.config/openclaw/env
bash scripts/vps/supervisor.sh
```

Eso comprobará estado y, si el Worker estaba caído, lo reiniciará con el env actualizado. Si el Worker ya estaba arriba, no lo reinicia; en ese caso para forzar reinicio:

```bash
pkill -f "uvicorn worker.app" || true
sleep 2
bash scripts/vps/supervisor.sh
```

### 4. Probar el aviso a Notion a mano

Con el Worker arriba y el env cargado en la misma sesión:

```bash
cd ~/umbral-agent-stack
source ~/.config/openclaw/env
curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "http://127.0.0.1:8088/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"notion.add_comment","input":{"text":"Test supervisor alert desde VPS"}}'
```

- Si ves **HTTP_CODE:200** y un JSON con `"ok": true` (y algo como `comment_id`), el comentario se creó. Revisa la página Control Room en Notion.
- Si ves **401**: el `WORKER_TOKEN` no coincide con el que usa el Worker (mismo valor en `~/.config/openclaw/env` y Worker arrancado después de guardar ese archivo).
- Si ves **500** o error en el body: suele ser falta de `NOTION_API_KEY` o `NOTION_CONTROL_ROOM_PAGE_ID` en el proceso del Worker, o página/permisos incorrectos en Notion.

### 5. Probar el flujo completo del supervisor

Solo tiene sentido si algo se reinicia (el script solo envía el alert cuando reinicia Worker o Dispatcher):

```bash
# Simular que el Worker estaba caído para que el supervisor lo reinicie y envíe el alert
pkill -f "uvicorn worker.app" || true
sleep 2
bash scripts/vps/supervisor.sh
```

En la salida deberías ver algo como:

- `Worker: DOWN — restarting...`
- `Worker: restarted (PID ...)`
- `Alert posted to Notion`

Si ves `Failed to post Notion alert`, revisa: Worker ya levantado, mismo `WORKER_TOKEN`, y NOTION_* en el env del Worker (pasos 2 y 3).

### Resumen rápido

| Paso | Acción |
|------|--------|
| 1 | `git pull origin main` en el repo |
| 2 | En `~/.config/openclaw/env`: tener `WORKER_TOKEN`, `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID` |
| 3 | Reiniciar Worker (o ejecutar supervisor) para que cargue el env |
| 4 | Probar con el `curl` a `/run` y comprobar 200 y comentario en Notion |
| 5 | Opcional: forzar reinicio con supervisor y comprobar "Alert posted to Notion" |
