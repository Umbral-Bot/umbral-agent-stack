---
name: vps-deploy-after-edit
description: Aplicar en la VPS de Umbral los cambios committeados en umbral-agent-stack y verificar health antes de cerrar la tarea. Úsala siempre tras editar archivos en worker/, dispatcher/, openclaw/, identity/, config/, o tras cambiar pyproject.toml. Cubre git pull, dependency install, service restart, y health check por servicio.
---

# Skill: vps-deploy-after-edit

## Purpose

Cerrar el gap entre "código committeado" y "código corriendo en producción" para los servicios de `umbral-agent-stack` que viven en la VPS de Umbral. Sin este skill, el riesgo recurrente es declarar tareas como `done` cuando en realidad solo están committeadas, dejando la VPS desincronizada del repo.

## When to invoke

- Después de cualquier commit que toque: `worker/`, `dispatcher/`, `openclaw/`, `identity/`, `client/` (si tiene consumidores internos), `config/`, o `pyproject.toml`.
- Antes de cerrar cualquier tarea cuyo criterio de éxito incluya "el cambio está aplicado en runtime".
- Cuando el usuario diga "deploy a VPS", "aplicá en la VPS", "restart el worker/dispatcher/openclaw", o equivalente.

## Inputs needed

- SSH access a la VPS (`ssh umbral@<vps-host>` o equivalente — usar el host configurado en `~/.ssh/config` si existe).
- El commit SHA o branch que se quiere desplegar (default: `main`).
- Lista de archivos cambiados (`git diff --name-only <previous>..<current>`) para decidir qué servicios restartear.

## Standard procedure (7 steps)

### Step 1 — Confirmar qué hay para desplegar

```bash
git log origin/main --oneline -5
git diff --name-only HEAD~1..HEAD  # o el rango relevante
```

Mapear los archivos cambiados a la tabla del `copilot-instructions.md` para saber qué servicios restartear.

### Step 2 — SSH a la VPS

```bash
ssh umbral@<vps-host>
cd /opt/umbral-agent-stack
```

(Ajustar el path real si difiere — verificar con `systemctl cat umbral-worker | grep WorkingDirectory`.)

### Step 3 — Pull del commit

```bash
git fetch origin
git status  # verificar que no hay cambios locales sin commitear
git pull origin main  # o checkout del branch específico si no es main
git log -1 --oneline  # confirmar HEAD esperado
```

Si hay cambios locales en la VPS sin commit, **PARAR** y reportar al usuario antes de hacer pull.

### Step 4 — Instalar dependencias si cambiaron

Solo si `pyproject.toml` cambió:

```bash
source .venv/bin/activate
pip install -e .
# o pip install -e ".[test]" si los tests también necesitan reinstall
```

### Step 5 — Restartear servicios afectados

Por cada servicio en la tabla del `copilot-instructions.md`:

```bash
sudo systemctl restart umbral-worker      # o el servicio correspondiente
sudo systemctl status umbral-worker --no-pager  # confirmar active (running)
```

Si el servicio no arranca, **NO** intentar más restarts. Capturar logs y reportar:

```bash
sudo journalctl -u umbral-worker -n 50 --no-pager
```

### Step 6 — Health check

| Servicio | Health check |
|---|---|
| `umbral-worker` | `curl -s -H "Authorization: Bearer $WORKER_TOKEN" http://localhost:8088/health \| jq` |
| `umbral-dispatcher` | revisar logs por `Dispatcher started`, sin errores `Connection refused` a Redis ni Worker |
| `umbral-openclaw` | `curl -s http://localhost:<openclaw-port>/health \| jq` (port según `openclaw.json`) |

Si algún health check falla, reportar y NO cerrar la tarea.

### Step 7 — Reportar al usuario

Formato:
- Servicios restarteados: `[lista]`.
- Commit SHA aplicado.
- Health checks: `[OK | FAILED + razón]`.
- Logs relevantes si hubo warnings.
- Tarea: `done` solo si todos los health checks pasaron.

## Critical rules

1. **Jamás hacer `git push --force` desde la VPS.** La VPS es consumidora del repo, no autora.
2. **Jamás dejar la VPS con cambios locales sin commit.** Si los hay, son drift y deben reportarse al usuario antes de cualquier pull.
3. **Jamás restartear todos los servicios "por las dudas".** Solo los afectados por los archivos cambiados.
4. **Aplicar [`secret-output-guard`](../secret-output-guard/SKILL.md) antes de citar contenido de logs al usuario** — los journalctl pueden contener tokens.
5. **Si el usuario está en mitad de una sesión Copilot Chat sobre la VPS, no asumir que SSH propio funciona** — verificar primero `whoami` y `pwd` antes de ejecutar comandos destructivos.

## Anti-patterns

- ❌ Cerrar tarea con "committeado" sin haber hecho los pasos 2-7.
- ❌ Hacer `systemctl restart` sin `systemctl status` posterior.
- ❌ Hacer `git pull` sobre worktree dirty (perdés cambios).
- ❌ Restartear servicios para edits que solo tocan `tests/`, `docs/`, `runbooks/`.

## Cross-references

- Banner runtime en [`copilot-instructions.md`](../../.github/copilot-instructions.md) — sección `⚠️ CRITICAL — Runtime lives on the VPS`.
- Runbooks operativos: [`runbooks/`](../../runbooks/).
- Configuración de servicios: typically `/etc/systemd/system/umbral-*.service` en la VPS.
- Reglas de coordinación cross-thread: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` §1.5 (Opción C).
