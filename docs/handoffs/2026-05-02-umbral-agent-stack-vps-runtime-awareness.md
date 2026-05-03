# Handoff — VPS runtime awareness para `umbral-agent-stack`

**Fecha:** 2026-05-02
**Origen:** retro Friday Q2-W1 (1-may-2026), continuación 2-may.
**Destino:** Copilot Chat de la VS Code session que se conecta vía SSH a la VPS de Umbral y trabaja sobre el repo `umbral-agent-stack`.
**Contexto:** detectado en `notion-governance` que el agente que opera sobre `umbral-agent-stack` no tiene una regla explícita que le recuerde que ese repo **es runtime en VPS**, no solo código. Modificar el repo no aplica el cambio hasta que se haga `git pull` + restart del servicio en la VPS. Esto genera el riesgo de que el agente cierre tareas pensando que están aplicadas cuando en realidad solo están committeadas.

Este handoff contiene **3 entregables** para que el Copilot de la VPS los implemente él mismo en `umbral-agent-stack`:

1. Bloque a agregar en `umbral-agent-stack/.github/copilot-instructions.md`.
2. Skill nueva `umbral-agent-stack/.agents/skills/vps-deploy-after-edit/SKILL.md`.
3. Prompt completo (al final) para pegarle al Copilot de la VPS.

---

## Entregable 1 — Bloque para `umbral-agent-stack/.github/copilot-instructions.md`

Insertarlo **al inicio del archivo**, justo después del título `# Umbral Agent Stack — Copilot Instructions`, como primera sección antes de `## Project Overview`. Marcar como bloque destacado para que sea imposible de ignorar.

````markdown
## ⚠️ CRITICAL — Runtime lives on the VPS, not in this repo

This repository is the **source code** of services that run on a remote VPS under systemd. Editing files here does NOT apply changes to the running system. A code change is only "applied" once the VPS has pulled the new commit AND the affected service has been restarted AND a health check confirms it's healthy.

### Files whose changes require VPS deploy

| Path edited | Service to restart on VPS |
|---|---|
| `worker/**` | `systemctl restart umbral-worker` (FastAPI on `:8088`) |
| `dispatcher/**` | `systemctl restart umbral-dispatcher` |
| `openclaw/**` | `systemctl restart umbral-openclaw` (gateway) |
| `identity/**` | restart whichever service consumes it (typically worker + dispatcher) |
| `client/**` | no service restart needed if SDK is consumed by external apps; if used internally, restart consumer service |
| `config/**` | restart all services that read the changed file |
| `scripts/**` | no restart; scripts are invoked on demand |
| `tests/**`, `docs/**`, `runbooks/**`, `reports/**`, `.agents/**`, `.claude/**`, `.cursor/**` | no deploy needed (repo-only) |

### Mandatory protocol after editing a runtime file

1. Commit + push to `main` (or feature branch then PR).
2. SSH into VPS (`ssh umbral@<vps-host>`).
3. `cd /opt/umbral-agent-stack && git pull origin main`.
4. If dependencies changed (`pyproject.toml`): `source .venv/bin/activate && pip install -e .`.
5. Restart the affected service(s) per the table above.
6. Run health check (see runbook for the specific service).
7. **Only then** report the task as done.

### When this protocol does NOT apply

- Edits to `tests/`, `docs/`, `runbooks/`, `reports/`, `.agents/`, `.claude/`, `.cursor/` — repo-only.
- PRs in draft state — deploy only after merge.
- Local-only experimentation that won't be committed.

### Skill that implements this

[`.agents/skills/vps-deploy-after-edit/SKILL.md`](../.agents/skills/vps-deploy-after-edit/SKILL.md) — invocable end-to-end procedure with health-check commands per service.

---
````

---

## Entregable 2 — Skill `umbral-agent-stack/.agents/skills/vps-deploy-after-edit/SKILL.md`

Crear el directorio si no existe y poner este contenido:

````markdown
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
````

---

## Entregable 3 — Prompt completo para el Copilot de la VPS

Pegar este prompt **tal cual** en la sesión de VS Code Copilot Chat conectada por SSH a la VPS, con el repo `umbral-agent-stack` abierto:

````text
Tarea de gobernanza cross-repo. Origen: notion-governance (handoff committeado el 2026-05-02 en docs/handoffs/2026-05-02-umbral-agent-stack-vps-runtime-awareness.md).

Contexto: detectamos que vos (el agente Copilot Chat que opera este repo desde VS Code SSH) no tenés una regla explícita que te recuerde que este repositorio es runtime en VPS, no solo código fuente. Eso genera el riesgo de cerrar tareas como "hechas" cuando solo están committeadas, sin haberse aplicado en el sistema corriendo.

Lo que tenés que hacer (en este orden, sin saltarte pasos):

1. Hacer `git fetch origin` y verificar que estás en `main` actualizado. Si hay cambios locales sin commit en este worktree, PARAR y reportar antes de seguir.

2. Abrir y leer en su totalidad el archivo `docs/handoffs/2026-05-02-umbral-agent-stack-vps-runtime-awareness.md` del repo notion-governance. Como vos no tenés ese repo abierto en este workspace, pedirle al usuario que te pegue el contenido completo, o cloná notion-governance temporalmente si tenés permisos. NO inventes el contenido.

3. Aplicar el "Entregable 1" del handoff: insertar el bloque markdown completo al inicio de `.github/copilot-instructions.md` en este repo, justo después del título `# Umbral Agent Stack — Copilot Instructions` y antes de `## Project Overview`. NO modificar ninguna otra sección del archivo. NO reformatear secciones existentes.

4. Aplicar el "Entregable 2" del handoff: crear el archivo `.agents/skills/vps-deploy-after-edit/SKILL.md` con el contenido exacto que trae el handoff. Crear el directorio si no existe.

5. Verificar que ambos archivos quedaron sintácticamente correctos:
   - El markdown del banner se renderiza bien (sin tablas rotas, sin code fences mal cerrados).
   - El frontmatter YAML del skill (`---` ... `---`) está bien delimitado.

6. Commit con mensaje:
   `governance: add VPS runtime awareness banner + vps-deploy-after-edit skill`
   con descripción que mencione el handoff de origen (notion-governance@<sha>) y la fecha 2026-05-02.

7. NO hacer push automático. Mostrarme el diff y pedir confirmación explícita antes del push.

8. Después del push (cuando lo confirme): aplicar la skill recién creada a sí misma como dogfooding — es decir, NO hace falta restartear servicios porque solo cambiaste `.github/` y `.agents/` (que son repo-only según la tabla del banner). Confirmar que sabés que en este caso no se ejecuta deploy y reportar `tarea cerrada sin deploy necesario` siguiendo el formato del Step 7 de la skill.

9. Recordar (esto es importante): a partir de ahora, en CADA tarea futura sobre este repo, leer el banner del `copilot-instructions.md` antes de declarar nada como "hecho". Si el usuario te pide deploy explícito, invocar la skill `vps-deploy-after-edit`.

Reglas de seguridad:
- No leakear tokens, paths internos, ni contenido de `.env` en ningún output. Aplicar el guardrail user-level `secret-output-guard` antes de cada respuesta visible.
- No tocar nada fuera de los dos archivos especificados en pasos 3 y 4.
- Si encontrás un conflicto (ej: ya existe un banner de runtime distinto en el copilot-instructions), PARAR y reportar antes de sobreescribir.

Reportá al final:
- Archivos modificados/creados.
- SHA del commit local (antes de push).
- Confirmación de que el banner y el skill quedan sintácticamente correctos.
- Si el dogfooding del paso 8 disparó alguna duda sobre la skill, listarla.
````

---

## Notas operativas

- Este handoff queda committeado en `notion-governance` para trazabilidad. No se replica automáticamente a `umbral-agent-stack` — el agente VPS lo aplica vía el prompt del Entregable 3.
- Si al ejecutarlo aparecen ajustes (ej: el path real del repo en VPS no es `/opt/umbral-agent-stack`, o el nombre del servicio systemd difiere), el agente VPS debe reportarlos para refinar la skill antes de declarar `done`.
- Este handoff resuelve la decisión "punto aparte VPS" de la retro Friday Q2-W1 (1-may-2026).
