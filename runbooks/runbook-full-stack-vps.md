# Runbook: Levantar todo el sistema en la VPS

## Pre-requisitos

- SSH a VPS configurado (`vps-umbral` o `rick@srv...`)
- `~/.config/openclaw/env` con `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL` (y opcional `WORKER_URL_VM`, `NOTION_*`)

## Pasos

### 1. Sincronizar repo y levantar todo

```bash
ssh vps-umbral 'cd ~/umbral-agent-stack && git pull origin main && bash scripts/vps/full-stack-up.sh'
```

### 2. Verificar identidad Rick en OpenClaw

Los archivos `IDENTITY.md` y `SOUL.md` se copian de `openclaw/workspace-templates/` a `~/.openclaw/workspace/` si no existen. OpenClaw los lee al iniciar.

```bash
ssh vps-umbral 'ls -la ~/.openclaw/workspace/'
```

Debe existir `IDENTITY.md` y `SOUL.md`.

### 3. Dispatcher (obligatorio para E2E)

Metodo canonico:

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh start
bash scripts/vps/dispatcher-service.sh status
```

Si detectas drift entre `systemctl` y procesos reales:

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh reconcile
```

La operacion canonica del dispatcher en VPS queda solo por `systemd`. No usar `nohup python3 -m dispatcher.service` como camino normal.

### 4. Notion poller (opcional)

En sesion separada o como servicio:

```bash
cd ~/umbral-agent-stack && source .venv/bin/activate && set -a && source ~/.config/openclaw/env && set +a
export PYTHONPATH=$HOME/umbral-agent-stack
python3 -m dispatcher.notion_poller
```

### 5. Test E2E

```bash
cd ~/umbral-agent-stack
bash scripts/vps/dispatcher-service.sh smoke
```

## Restart tras merge — dispatcher y mission-control (C2)

> Añadido 2026-07-17 (sys-diag). **Motivo**: el diagnóstico encontró que
> `openclaw-dispatcher.service` y `mission-control.service` corrían con el
> ejecutable Python marcado `deleted` (procesos del 3-jul): el repo estaba en
> `main` limpio pero **los servicios no habían recargado el HEAD**. No existe un
> paso "restart tras merge" en el ritmo de deploy — esta sección lo define.
>
> **Handoff**: la ejecución live la hace Copilot VPS. NO ejecutar desde la
> sesión de diagnóstico. Un servicio Python solo carga código nuevo al
> reiniciarse; hacer `git pull` a main **no** basta.

**Prechecks (read-only):**
```bash
cd ~/umbral-agent-stack
git fetch origin && git log --oneline -1               # HEAD local
git rev-parse HEAD && git rev-parse origin/main         # deben coincidir (main limpio)
git status --short                                      # árbol limpio
systemctl --user is-active openclaw-dispatcher.service mission-control.service
# ¿El proceso corre código viejo? (Python 'deleted' = binario borrado bajo el PID)
for u in openclaw-dispatcher mission-control; do
  pid=$(systemctl --user show -p MainPID --value "$u.service")
  [ "$pid" != 0 ] && ls -l "/proc/$pid/exe" 2>/dev/null | grep -q deleted && echo "$u: corre binario DELETED (necesita restart)"
done
```

**Deploy del commit aprobado** (solo si prechecks OK y el commit es el aprobado por David):
```bash
cd ~/umbral-agent-stack
bash scripts/vps/ensure-main-for-run.sh    # gate: main limpio y sincronizado
```

**Restart ordenado** (dispatcher primero, luego mission-control):
```bash
systemctl --user restart openclaw-dispatcher.service
sleep 3
systemctl --user restart mission-control.service
```

**Health checks:**
```bash
systemctl --user is-active openclaw-dispatcher.service mission-control.service   # active
curl -fsS http://127.0.0.1:8089/ >/dev/null && echo "mission-control OK"          # dashboard
bash scripts/vps/dispatcher-service.sh smoke                                       # dispatcher E2E
```

**Comprobación commit == runtime** (el PID ya no debe apuntar a un binario `deleted`):
```bash
for u in openclaw-dispatcher mission-control; do
  pid=$(systemctl --user show -p MainPID --value "$u.service")
  echo "$u PID=$pid"; ls -l "/proc/$pid/exe" 2>/dev/null
done
git rev-parse HEAD    # anotar el SHA en servicio ahora corriendo
```

**Rollback** (si un smoke/health falla):
```bash
cd ~/umbral-agent-stack
git checkout <SHA_ANTERIOR_BUENO>          # el SHA previo anotado antes del deploy
systemctl --user restart openclaw-dispatcher.service && sleep 3 && systemctl --user restart mission-control.service
bash scripts/vps/dispatcher-service.sh smoke
git checkout main                          # volver a main tras estabilizar
```
Si el rollback tampoco levanta, degradar a proceso supervisado (`dispatcher-service.sh reconcile`) y escalar a David; no dejar el servicio en bucle de restart.
