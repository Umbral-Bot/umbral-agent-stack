# 21 — VPS autosuficiente y VM opcional (doble Worker)

## Objetivo

- **VPS autosuficiente** cuando la VM no está: todo corre en la VPS (OpenClaw, Redis, Dispatcher, Worker local).
- **Cuando la VM está disponible**: el Dispatcher usa la VM para tareas que la requieren (`requires_vm: true`: improvement, lab); el resto sigue en el Worker de la VPS.
- La VPS **siempre** tiene su propio Worker (ping, notion, system, marketing, advisory); la VM suma capacidad para improvement/lab cuando está encendida.

## Cómo funciona

| Variable | Significado | Por defecto |
|----------|-------------|-------------|
| `WORKER_URL` | Worker **local** (VPS) — siempre usado para tareas que no requieren VM y como único Worker si no hay VM | `http://127.0.0.1:8088` |
| `WORKER_URL_VM` | Worker de la **VM** (opcional). Si está definido, el HealthMonitor comprueba si la VM está online. | — (vacío = no hay VM) |

**Routing:**

- Equipos con `requires_vm: false` (marketing, advisory, system) → siempre **Worker VPS** (localhost).
- Equipos con `requires_vm: true` (improvement, lab) → **Worker VM** si `WORKER_URL_VM` está definido y la VM está online; si la VM está caída, la tarea se **bloquea** hasta que vuelva (o podés no definir `WORKER_URL_VM` y esas tareas irían al Worker local en modo degradado si en el futuro se soporta).
- Sin `WORKER_URL_VM`: todo va al Worker local (VPS 100 % autosuficiente; improvement/lab se bloquean si no hay VM).

## Configuración en la VPS

### 1. Worker local siempre activo

- Levantar el Worker en la VPS (puerto 8088). Ver [runbooks/runbook-worker-on-vps.md](../runbooks/runbook-worker-on-vps.md) y `openclaw/systemd/openclaw-worker-vps.service.template`.
- Mismo `WORKER_TOKEN` que use el Dispatcher.

### 2. Variables del Dispatcher (ej. en `~/.config/openclaw/env`)

```bash
# Worker local (VPS) — obligatorio
WORKER_URL=http://127.0.0.1:8088
WORKER_TOKEN=tu_token

# Redis
REDIS_URL=redis://localhost:6379/0

# VM opcional: si la definís, el Dispatcher enviará improvement/lab a la VM cuando esté online
WORKER_URL_VM=http://100.109.16.40:8088
```

- Si **no** ponés `WORKER_URL_VM`: la VPS es autosuficiente; todo va al Worker local. Las tareas de improvement/lab se bloquean (requieren VM).
- Si **sí** ponés `WORKER_URL_VM`: cuando la VM está encendida y accesible, improvement/lab van a la VM; el resto a local.

### 3. Notion en la VPS (opcional)

Para que el Worker local pueda ejecutar tareas Notion (p. ej. poller, add_comment), configurá en el mismo entorno donde corre el Worker:

- `NOTION_API_KEY`
- `NOTION_CONTROL_ROOM_PAGE_ID`
- `NOTION_GRANOLA_DB_ID` (opcional; pipeline Granola; usa `NOTION_API_KEY` Rick)

## Resumen

| Escenario | Worker usado |
|-----------|----------------|
| Sin `WORKER_URL_VM` | Todo → Worker VPS (localhost). VPS autosuficiente. |
| Con `WORKER_URL_VM`, VM online | marketing/advisory/system → VPS; improvement/lab → VM. |
| Con `WORKER_URL_VM`, VM offline | marketing/advisory/system → VPS; improvement/lab → bloqueadas hasta que la VM vuelva. |

La VPS siempre tiene “sus propias cosas” (Worker local, Redis, OpenClaw, Dispatcher); la VM es un recurso adicional cuando está disponible.
