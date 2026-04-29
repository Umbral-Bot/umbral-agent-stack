# 06 — Codegen Team Design (Director → Sub-agentes en sandbox)

> Diseño del equipo `build` para que Rick coordine sub-agentes que producen código real (web apps, plataformas, software a medida) de forma segura, observable y con human-in-the-loop. Aprovecha los $15K USD de créditos Azure + Copilot.

Estado: **Draft 0.1 — propuesta para revisión humana antes de implementar Fase 1.**

---

## 1. Decisiones arquitectónicas (cerradas)

1. **Un solo OpenClaw**, en VPS. La VM Windows y el nuevo nodo de codegen son Workers, no orquestadores paralelos.
2. **Director único = Rick.** El humano (David) habla con Rick por Notion/Telegram. Rick selecciona el supervisor `build` cuando la tarea es de software.
3. **Sub-agentes son tasks del Worker**, no procesos huérfanos. Mismo TaskEnvelope, misma observabilidad (Langfuse + Redis), misma rate-limit policy.
4. **Cada sub-agente corre dentro de un sandbox Docker efímero.** Nunca toca el repo original; trabaja sobre un clon fresco con allowlist de paths (ya implementada en `worker/sandbox/workspace.py`).
5. **Branches `agent/<role>/<task-id>`.** Convención análoga a `rick/` pero por rol. Nunca push directo a `main`. Nunca merge automático.
6. **HITL gates obligatorios** en 2 puntos: aprobación de plan (architect) y aprobación de PR (reviewer). Rick mergea solo después de OK humano vía Notion.
7. **Azure burst opcional**, no obligatorio. Tareas chicas corren en VPS. Tareas grandes (refactor cross-repo) lanzan Container Apps Job con créditos Azure.

## 2. Diagrama lógico

```
┌─────────────────────── HUMANO (David) ───────────────────────┐
│                  Notion · Telegram · VS Code                 │
└──────────────────────────┬───────────────────────────────────┘
                           │ comentario / mensaje
                           ▼
┌──────────────────────── RICK (Director) ─────────────────────┐
│  Detecta intent "build" → carga supervisor `build`           │
└──────────────────────────┬───────────────────────────────────┘
                           │ TaskEnvelope
                           ▼
┌──────────────── BUILD SUPERVISOR (orquesta) ─────────────────┐
│  Plan: architect → [HITL gate 1] → implementer → reviewer    │
│        → [HITL gate 2] → merge → scribe                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ delega cada step como TaskEnvelope
        ┌──────────────────┼──────────────────┬───────────────┐
        ▼                  ▼                  ▼               ▼
  Worker VPS Linux   Worker VPS Linux   Worker VPS Linux  Worker Windows
  (code.architect)   (code.implement)   (code.review)     (PAD/RPA si
                                                           hace falta)
                           │
                           │ corre dentro de sandbox Docker:
                           ▼
            ┌─────────────────────────────────┐
            │  /workspace ← clon fresco repo  │
            │  Tools:  gh · claude · copilot  │
            │          node · python · git    │
            │  Network: allowlist (gh, npm,   │
            │          pypi, azure, openai)   │
            │  Token:  PAT scoped a repo+branch│
            └─────────────────────────────────┘
                           │
                           ▼
              PR draft `agent/<role>/<task-id>` → GitHub
                           │
                           ▼
               Notion comment (HITL gate)
                           │
                           ▼
                     David aprueba
                           │
                           ▼
                  Rick ejecuta `gh pr merge`
```

## 3. Roles del equipo `build`

| Rol | Task del Worker | Toca código | Salida | HITL gate |
|-----|----------------|-------------|--------|-----------|
| **architect** | `code.architect` | No | Plan markdown + ADR draft + lista de archivos a tocar | ✅ Sí (antes de implementer) |
| **implementer** | `code.implement` | Sí (sandbox) | PR draft con diff + tests passing | No (auto si tests OK) |
| **reviewer** | `code.review` | No (lee diff) | Comentarios en PR + score riesgo | ✅ Sí (antes de merge) |
| **debugger** | `code.debug` | Sí (sandbox) | Patch mínimo + repro test | No (genera otra ronda implementer) |
| **scribe** | `code.scribe` | Sí (governance only) | Update README/ADR/changelog/registry | No |

**Anti-acoplamiento:** ningún rol puede invocar a otro directamente. Solo el supervisor compone la secuencia. Esto evita loops y debate libre.

**Límite de turnos:** máximo 2 ciclos `reviewer→debugger→implementer` por tarea. Si al 3er ciclo no pasa, escala a David.

## 4. Sandbox: contrato de seguridad

Reusamos `worker/sandbox/workspace.py` que ya tiene:
- Allowlist de directorios top-level
- Defense-in-depth en paths (`Path.resolve()` antes de escribir)
- Blacklist de basenames (`.env*`, `.git`, `node_modules`, etc.)

**Lo que falta agregar (Fase 1):**
- Imagen Docker `umbral/codegen-sandbox:0.1` con: `git`, `gh`, `node 22`, `python 3.12`, `claude` CLI, `copilot` CLI, `pytest`, `vitest`, `eslint`.
- Network policy: `iptables` interno que solo permite `api.github.com`, `objects.githubusercontent.com`, `registry.npmjs.org`, `pypi.org`, `*.openai.azure.com`, `api.anthropic.com`. Nada más.
- Token scoping: PAT generado per-task con `repo:write` solo al repo target y solo al branch `agent/<role>/<task-id>`. TTL 1 hora.
- Tiempo máximo de ejecución por sandbox: 15 min. Mata y reintenta una vez.
- No volumen mount del repo real. Siempre `gh repo clone` adentro.

## 5. Worker code-gen en VPS — qué cambia

Hoy el único Worker corre en VM Windows. Agregamos un Worker Linux en la misma VPS.

```
VPS Hostinger
├── OpenClaw (control plane)
├── Dispatcher
├── Redis
├── LiteLLM
├── Worker Linux NUEVO (port 8089)  ← code-gen tasks
│    └── Docker daemon → sandboxes efímeros
└── Notion poller
```

**Mismo binario `worker/app.py`, distinta config:**
- `WORKER_PORT=8089`
- `WORKER_TASKS_ENABLED=code.architect,code.implement,code.review,code.debug,code.scribe,github.*`
- `SANDBOX_BACKEND=docker`
- `WORKER_TOKEN` distinto al de la VM (scope separation)

**El Worker Windows queda como está.** Sigue manejando `windows.*`, `gui.*`, `pad.*`, browser automation con UI.

**Routing en Dispatcher:** si `task` empieza con `code.` → Worker VPS:8089. Si empieza con `windows.`/`gui.`/`pad.` → Worker VM. El resto sigue regla actual.

## 6. Azure burst (Fase 3)

Para tareas grandes (ej. refactor entero de `umbral-bot-2`), Rick lanza un Container App Job:
- Imagen: misma `umbral/codegen-sandbox` publicada en ACR
- Variables: `TASK_ENVELOPE`, `WORKER_CALLBACK_URL`, `BRANCH_NAME`
- Ejecución: aislada, paralela, hasta N jobs simultáneos
- Resultado: el job hace push del branch + abre PR + llama callback al Worker VPS para registrar resultado en Redis/Langfuse
- Costo: imputa a tus $15K crédito Azure, no consume capacidad de VPS

**Fase 3 NO bloquea Fase 1/2.** Mismo patrón, distinto runner.

## 7. HITL gates (cómo funcionan)

**Gate 1 — Aprobación de plan:**
1. `code.architect` produce plan markdown
2. Worker llama `notion.add_comment` en página Control Room: "Plan listo: [link]. Responder ✅ para aprobar, ❌ para descartar."
3. Notion poller (ya existe) detecta respuesta de David
4. Si ✅ → Dispatcher encola `code.implement`
5. Si ❌ → Rick pide refinamiento al architect (max 2 rondas)

**Gate 2 — Aprobación de merge:**
1. `code.review` deja comentarios en PR draft + posteo en Notion: "PR listo: [link], riesgo bajo/medio/alto. ✅ para mergear."
2. David revisa PR en GitHub, contesta en Notion
3. Si ✅ → Rick ejecuta `gh pr merge --squash`
4. Si ❌ → escala a debugger con feedback

**Timeout:** si no hay respuesta en 24 h, Rick manda recordatorio Telegram. A las 72 h, marca tarea como `paused-awaiting-human` y libera workers.

## 8. Observabilidad

Reusamos lo que ya existe:
- **Langfuse** — cada sub-agente loggea trace con `task_id`, `parent_task_id`, tokens, costo
- **Redis** — estado de tarea + cola
- **Notion Dashboard** — métricas agregadas (tareas completas/día, gates pendientes, tiempo medio plan→merge)
- **Tracing TaskEnvelope** — ya tiene `parent_id`, `correlation_id`

Métrica clave Fase 1: **% de tareas que llegan a merge sin intervención humana fuera de los 2 gates**. Target ≥ 70% al mes 1.

## 9. Seguridad — checklist no-negociable

- [ ] PAT scoped per-task, TTL 1h
- [ ] Sandbox sin acceso a Tailscale (no hace falta para code-gen)
- [ ] Network allowlist a nivel iptables, no solo aplicación
- [ ] Logs scrubbed: `_sanitize_stderr` ya redacta tokens, extender a outputs de claude/copilot CLI
- [ ] Branches `agent/*` con branch protection: no force-push, no delete sin revisión
- [ ] PRs requieren al menos 1 approval humano (configurar en GitHub repo settings de los repos target)
- [ ] Dependabot + secret scanning activos en repos target
- [ ] OWASP LLM Top 10: especialmente LLM01 (prompt injection en issues/PRs/comentarios) y LLM06 (sensitive info disclosure en logs)

## 10. Plan de adopción (3 fases)

**Fase 1 — Walking skeleton (semana 1)**
- Equipo `build` en `teams.yaml`
- 5 skills `code-*` en `openclaw/workspace-templates/skills/`
- Worker Linux en VPS con `code.architect` (no toca código, riesgo bajo)
- Smoke test: pedirle a Rick "diseñá un endpoint nuevo en umbral-bot-2 para X" → recibir plan en Notion
- Criterio éxito: 1 plan generado, aprobado por David, tiempo total < 10 min

**Fase 2 — Implementer + reviewer (semana 2)**
- `code.implement` con sandbox Docker funcional
- `code.review` con LLM-as-judge + ejecución de tests
- HITL gate 2 funcionando vía Notion
- Smoke test: feature chica end-to-end en umbral-bot-2 (ej. agregar campo opcional a un componente)
- Criterio éxito: 1 PR mergeado, tests pasando, sin regresión

**Fase 3 — Azure burst + scale (semana 3-4)**
- ACR con imagen sandbox publicada
- Container Apps Job + callback
- Scribe + debugger funcionando
- Cargas paralelas: hasta 5 sub-agentes simultáneos
- Criterio éxito: refactor mediano completado en 1 día (ej. migración de un módulo de umbral-agent-stack)

## 11. Qué NO hace este diseño (anti-scope)

- No reemplaza a Lovable como Merge Master de `umbral-bot-2`. Rick propone PRs, Lovable/Copilot mergean siguiendo el protocolo existente del repo.
- No reemplaza a OpenClaw. Lo extiende con un equipo más.
- No introduce LangGraph en producción todavía. Si la investigación de Perplexity confirma que conviene, se evalúa en Fase 4 (post-MVP).
- No autoriza merge automático bajo ninguna circunstancia.

## 12. Próximos archivos a crear

1. `openclaw/workspace-templates/skills/code-architect/SKILL.md`
2. `openclaw/workspace-templates/skills/code-implementer/SKILL.md`
3. `openclaw/workspace-templates/skills/code-reviewer/SKILL.md`
4. `openclaw/workspace-templates/skills/code-debugger/SKILL.md`
5. `openclaw/workspace-templates/skills/code-scribe/SKILL.md`
6. Diff a `config/teams.yaml` agregando equipo `build`
7. `runbooks/runbook-codegen-fase1-smoke.md`
8. `docs/roadmap/codegen-rollout-phases.md` (resumen ejecutivo)

Decisión humana requerida antes de Fase 2: presupuesto de tiempo, confirmar bind ports, decidir si publicamos imagen sandbox a ACR ya en Fase 1 o esperamos.
