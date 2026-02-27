# 28 — Rick: cuenta GitHub y workflow de PRs (Opción A)

## Resumen

Rick tiene cuenta propia en GitHub y propone cambios vía **Pull Requests**. David (o Cursor) revisa y mergea. No hay push directo a `main` sin revisión.

---

## Pasos para implementar

### 1. Crear cuenta GitHub para Rick

- Crear cuenta (ej. `rick-umbral` o `umbral-rick`).
- Usar email dedicado (no el personal de David).
- Configurar 2FA si aplica.

### 2. Invitar como collaborator

En el repo `Umbral-Bot/umbral-agent-stack`:

1. Settings → Collaborators → Add people
2. Invitar a la cuenta de Rick con rol **Write**
3. Rick acepta la invitación

Con **Write**, Rick puede: push a ramas, abrir PRs, crear issues. No puede: borrar ramas protegidas ni mergear PRs si hay branch protection.

### 3. Configurar branch protection en `main`

1. Settings → Branches → Add branch protection rule
2. Branch name: `main`
3. Activar:
   - **Require a pull request before merging** (mín. 1 aprobación si quieres)
   - **Require status checks to pass** (ej. CI si tienes)
   - **Do not allow bypassing** (opcional)

Así nadie (incluido Rick) mergea sin pasar por PR.

### 4. Flujo de trabajo de Rick

1. Rick (o el agente que actúe como Rick) trabaja en una rama: `rick/feature-x` o `rick/fix-y`
2. Push a su rama
3. Abre PR hacia `main`
4. David (o Cursor) revisa, comenta, aprueba
5. Merge del PR a `main`

### 5. Acceso de Rick al repo

Rick necesita:

- Token o SSH key para push (si corre en VM/VPS, configurar credenciales allí)
- Instrucciones claras: "Siempre trabajar en ramas, nunca push a main, abrir PR para todo cambio"

---

## Con quién trabajar qué: David ↔ Cursor vs Rick

### Trabajar directamente contigo (David ↔ Cursor / Codex)

- **Arquitectura y decisiones de diseño**
- **Configuración de repos, GitHub, CI/CD**
- **Revisión y merge de PRs de Rick**
- **Debugging complejo** y análisis de root cause
- **Cambios sensibles**: secretos, permisos, seguridad
- **Orquestación general**: qué hace Rick, qué hace cada equipo
- **Configuración de Rick** (prompts, equipo, herramientas)

### Trabajar con Rick (vía Notion, Telegram, PRs)

- **Implementación de tareas** ya definidas
- **Cambios de código** acotados (features, fixes)
- **Actualización de docs** según tareas asignadas
- **Ejecución de flujos** (ej. generar reporte, procesar cola)
- **Propuestas de cambio** vía PR para que tú revises

### Línea divisoria (resumen)

| Si es… | Mejor con |
|--------|-----------|
| Decidir qué hacer, cómo estructurarlo | David + Cursor |
| Implementar algo ya acordado | Rick (PR) |
| Revisar y aprobar cambios | David + Cursor |
| Configurar cuentas, tokens, permisos | David + Cursor |
| Escribir código/PRs de tareas asignadas | Rick |
| Debugging profundo, arquitectura | David + Cursor |
| Tareas operativas (ej. “actualiza el Kanban”) | Rick |

---

## Reglas para Rick

1. **Nunca push directo a `main`.** Solo ramas y PRs.
2. **Una rama por tarea o fix.** Nombrar claro: `rick/add-feature-x`, `rick/fix-issue-123`.
3. **PR con descripción** breve: qué cambia, por qué, cómo probarlo.
4. **Responder a feedback** en el PR antes de que se mergee.
5. **No tocar** secretos, tokens ni configuración sensible sin instrucción explícita.

---

## Checklist inicial

- [ ] Cuenta GitHub para Rick creada
- [ ] Rick invitado como collaborator (Write)
- [ ] Branch protection en `main` configurada
- [ ] Rick tiene credenciales para push (token/SSH)
- [ ] Rick tiene instrucciones: ramas + PR, no push a main
