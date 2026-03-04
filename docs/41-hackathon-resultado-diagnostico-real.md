# 41 — Hackathon: Resultado del Diagnóstico Real (datos vivos)

> **Fecha:** 2026-03-04  
> **Coordinador:** Cursor (Lead, esta sesión)  
> **Método:** Diagnóstico con acceso real a VPS (SSH via Tailscale), VM (Hyper-V local), Notion API, Linear API, Hostinger API  
> **Complementa:** doc 40 (diagnóstico desde código, por agente Cursor Cloud)

---

## 1. Estado Real de la Infraestructura

### VPS Hostinger (Control Plane)

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| **Servidor** | Running | Ubuntu 24.04, 2 CPU, 8 GB RAM, 100 GB disco. CPU ~1%, RAM ~23%, disco ~11%. Uptime ~6 días |
| **Redis** | OK | `redis-cli ping` → PONG. 16 task keys + 8 quota keys en Redis |
| **Worker VPS** | OK | v0.3.0, 11 tasks registradas (ping, notion.*, system.*, linear.*). 330 tasks en memoria |
| **Dispatcher** | Corriendo pero inactivo | PID 147872 activo. Procesó 5 tareas el 27/02 (2 fallaron por 401 en VM, 3 completaron como ping en VPS). Desde entonces: **solo health check failures** (37,000+ líneas de log, casi todas "Health check failed: timed out") |
| **Dashboard cron** | Roto → arreglado | `Permission denied` en `dashboard-cron.sh` tras git pull (permisos de ejecución perdidos). **Fix aplicado:** `chmod +x`. Dashboard se actualiza correctamente tras fix |
| **n8n** | OK | Servicio systemd activo desde 2026-03-03 12:29 |
| **Tailscale** | OK | Responde ping desde host TARRO (691ms latencia) |

### VM OpenClaw (Execution Plane)

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| **Hyper-V VM** | Running | Estado "Funcionamiento normal", IP 192.168.155.86 |
| **Worker VM** | OK | v0.3.0, 22 tasks registradas (incluye windows.fs.*, linear.*, system.*). 23 tasks en memoria |
| **Tailscale en host** | Recién instalado | No estaba instalado en TARRO. David lo instaló durante el hackathon |
| **Conectividad host→VM** | OK | Worker responde en http://192.168.155.86:8088 |

### Notion

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| **API Key** | OK | Autenticación correcta |
| **Dashboard Rick** | Funcional | Última actualización: 2026-03-04. Contenido: tablas de infra, cuotas, equipos, tareas. Pero métricas en cero (0 tareas, 0% éxito) |
| **Control Room** | SIN ACCESO | HTTP 404 — la integración Notion no tiene permiso. La página existe pero no fue compartida con la integración. **Pendiente: David debe compartirla** |

### Linear

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| **API Key** | OK | Funciona |
| **Team Umbral** | OK | 1 team, key UMB |
| **Issues** | 12 activos | 8 Backlog + 4 Todo. **Todos sin asignar**, sin prioridad real, sin labels de equipo |

---

## 2. Hallazgos Críticos (con datos reales)

### Lo que el diagnóstico de código (doc 40) dijo vs la realidad:

| Doc 40 dijo | Realidad verificada |
|------------|-------------------|
| "0 tareas procesadas" | **Parcialmente cierto**: El Dispatcher procesó 5 tareas el 27/02 (3 OK, 2 fallaron por auth). Después: 0 |
| "Dashboard no funciona" | **El cron existía pero perdió permisos de ejecución** tras un git pull. El script funciona correctamente; solo faltaba `chmod +x`. Ya arreglado |
| "Cuotas LLM sin usar" | **Confirmado**: Redis tiene keys de quota (claude, chatgpt, gemini, copilot) pero todas vacías. 0 requests a LLMs |
| "Dispatcher no corre" | **Corre** (PID activo) pero está en un loop infinito de health check failures hacia la VM (IP Tailscale incorrecta o no alcanzable desde VPS). No procesa tareas nuevas |
| "Redis no conectado" | **Falso**: Redis está OK, tiene 16 task keys y quota keys. Está conectado y funcional |
| "Ops log vacío" | **Confirmado**: No existe archivo ops_log. El OpsLogger nunca se activó en producción |

### Problemas raíz descubiertos:

1. **Dispatcher está atrapado en health check loop**: Intenta verificar la VM en `http://100.109.16.40:8088` (IP Tailscale) cada 10s. Falla siempre (timeout). Tiene 33+ failures acumulados. Esto bloquea el procesamiento de tareas que requieren VM. Las tareas VPS-only (system, marketing, advisory) no se ven afectadas por esto, pero el Dispatcher no las procesa porque la cola está vacía (nadie encola tareas nuevas).

2. **Nadie encola tareas**: El flujo esperado (Notion → Rick → queue → Dispatcher → Worker) no funciona porque:
   - La Control Room no es accesible para la integración Notion (falta compartir).
   - El Notion Poller solo hace eco ("Recibido.") sin crear tareas.
   - No hay ningún cron ni script que genere tareas automáticamente.

3. **Cron del dashboard se rompe con cada git pull**: Porque git no preserva permisos de ejecución en scripts `.sh`. Solución: añadir `chmod +x` al cron o usar `bash script.sh` en vez de `./script.sh` en el crontab.

---

## 3. Fixes Aplicados en Este Hackathon

| Fix | Estado |
|-----|--------|
| `.env` local limpiado (basura NULL, duplicados, WORKER_URL sobreescrito) | HECHO |
| `chmod +x dashboard-cron.sh` en VPS | HECHO |
| Dashboard ejecutado manualmente → Notion actualizado | HECHO |
| Tailscale instalado en host TARRO | HECHO (David) |
| VPS confirmada viva (SSH, Redis, Worker, Dispatcher, n8n) | HECHO |
| VM confirmada viva (Worker health, 22 tasks) | HECHO |

---

## 4. Acciones Pendientes por Prioridad

### P0 — Hoy (desbloquean el sistema)

| Acción | Responsable | Detalle |
|--------|------------|---------|
| **Compartir Control Room con integración Notion** | David | 1 click en Notion: página OpenClaw → "..." → "Add connections" → seleccionar integración |
| **Actualizar WORKER_URL_VM en env de VPS** | Rick / Cursor | La VPS apunta a IP Tailscale de VM que puede no ser alcanzable. Actualizar a la IP correcta |
| **Arreglar crontab: usar `bash` en vez de ejecutable** | Cursor | Cambiar crontab a `bash ~/umbral-agent-stack/scripts/vps/dashboard-cron.sh` para que no se rompa con git pull |

### P1 — Esta semana (que el sistema haga algo útil)

| Acción | Responsable |
|--------|------------|
| Notion Poller inteligente (clasifica comentarios → encola tareas) | Antigravity |
| Encolar al menos 1 tarea real desde un cron (ej. SIM research diario) | Codex |
| Conectar al menos 1 LLM al sistema (Gemini via API key existente) | Copilot |
| Linear issues con prioridad, labels, asignación | Cursor |

### P2 — Próximos días (tracking y mejora continua)

| Acción | Responsable |
|--------|------------|
| Activar OpsLogger en Dispatcher (para que ops_log tenga datos) | Codex |
| Health check automático diario (script que verifique todo) | Cursor |
| Langfuse para observabilidad de LLM calls | Copilot |

---

## 5. Métricas Actuales vs Objetivo

| Métrica | Actual (real) | Objetivo hackathon |
|---------|--------------|-------------------|
| Tareas procesadas/día | 0 (5 total histórico, todas el 27/02) | >10 |
| Modelos LLM activos | 0 | ≥1 |
| Dashboard actualizado | Cada 15 min (arreglado hoy) | Cada 15 min |
| Cuotas aprovechadas | 0% | >10% |
| Equipos con actividad | 0 | ≥1 |
| Notion Control Room funcional | No (sin permisos) | Sí |
| Ops log con eventos | 0 | >20 |
| Linear issues con asignación | 0/12 | 8/8 (los reales) |
