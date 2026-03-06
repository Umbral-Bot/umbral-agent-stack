# R19 — Comando bash VPS, instrucciones Codex 096, revisión

## 1. Comando bash para probar el aviso Notion en el VPS

Ejecutar en el VPS (en una sola línea o por bloques):

```bash
cd ~/umbral-agent-stack && source ~/.config/openclaw/env && pkill -f "uvicorn worker.app" || true && sleep 2 && bash scripts/vps/supervisor.sh
```

O por pasos:

```bash
cd ~/umbral-agent-stack
source ~/.config/openclaw/env
pkill -f "uvicorn worker.app" || true
sleep 2
bash scripts/vps/supervisor.sh
```

Deberías ver algo como: `Worker: DOWN — restarting...`, `Worker: restarted (PID ...)`, y si el Worker tiene NOTION_API_KEY y NOTION_CONTROL_ROOM_PAGE_ID, `Alert posted to Notion`.

---

## 2. Nuevas instrucciones para Codex (tarea 096)

Pega esto a Codex:

```
Tarea 096 (R19): mejorar aviso Notion del supervisor y documentar.

Antes de empezar: git checkout main && git pull origin main. Crear rama: git checkout -b codex/096-supervisor-notion-alert.

IMPORTANTE: Trabaja SOLO en la rama codex/096-supervisor-notion-alert.

En main ya está:
- supervisor.sh llamando a POST /run (no /task).
- health-check.sh corregido a POST /run.

Haz lo siguiente:

1. En scripts/vps/supervisor.sh:
   - Añadir función post_notion_alert() que construya el payload JSON de forma segura (evitar que saltos de línea en ALERT rompan el JSON). Llamar a curl con ese payload para POST ${WORKER_URL}/run con task "notion.add_comment" e input {"text": "..."}.
   - Soporte opcional para NOTION_SUPERVISOR_ALERT_PAGE_ID: si está definida, pasar "page_id" en el input de notion.add_comment; si no, el Worker usará NOTION_CONTROL_ROOM_PAGE_ID por defecto.
   - Reemplazar el bloque actual de curl por la llamada a post_notion_alert().

2. En docs/62-operational-runbook.md (sección 1.4 o donde se documenten env del supervisor):
   - Dejar claro que para que el aviso Notion funcione el Worker debe tener NOTION_API_KEY y NOTION_CONTROL_ROOM_PAGE_ID (o NOTION_SUPERVISOR_ALERT_PAGE_ID si se usa otra página).

3. Abrir PR a main. Título: "fix(R19-096): supervisor Notion alert — JSON seguro y NOTION_SUPERVISOR_ALERT_PAGE_ID".

No cambiar lógica de reinicio (check_worker, restart_worker, etc.). Solo el bloque de envío del alert y la documentación.
```

---

## 3. Revisión del “diff” de Codex (no hay PR 096)

No existe en el repo un PR abierto de Codex para la tarea 096 (rama `codex/096-supervisor-notion-alert` no está en origin, y en `gh pr list` no aparece un PR 096). Por tanto no hay diff de PR que revisar.

Lo que Codex dijo que hizo (en su entorno) es coherente con lo que conviene tener en main:

| Cambio que Codex describió | Estado en main | Recomendación |
|----------------------------|----------------|---------------|
| POST /task → POST /run en supervisor.sh | ✅ Ya está en main | Nada |
| post_notion_alert() para serializar JSON correctamente | ❌ No está | Integrar: evita que saltos de línea en el mensaje rompan el payload |
| NOTION_SUPERVISOR_ALERT_PAGE_ID con fallback a NOTION_CONTROL_ROOM_PAGE_ID | ❌ No está | Integrar: permite destinar los avisos del supervisor a otra página |
| Reemplazar bloque de envío por llamada a la función | ❌ No está | Integrar junto con post_notion_alert() |
| health-check.sh: POST /task → POST /run | ✅ Ya corregido en main | Nada |

Conclusión: dar a Codex las instrucciones de la sección 2 para que suba esos cambios en una rama y abra el PR; así se puede revisar el diff real y mergear en main.
