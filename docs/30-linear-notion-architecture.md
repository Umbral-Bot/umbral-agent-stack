# 30 — Arquitectura Linear + Notion

> Sugerencia de cómo integrar Linear (issues/proyectos) con Notion (visualización/control) y los agentes Rick, Cursor y Codex.

---

## 1. Responsabilidades

| Herramienta | Rol | Fuente de verdad |
|-------------|-----|------------------|
| **Linear** | Issues, proyectos, sprints, backlog, asignación | Sí (planning) |
| **Notion** | Dashboard, Control Room, documentación, Enlace | Sí (comms + docs) |
| **Redis** | Cola de ejecución (tasks pendientes/running) | Sí (execution) |
| **Tareas Umbral (Notion DB)** | Estado operativo: En cola, En curso, Hecho | Sí (runtime) |

---

## 2. Flujo

```
David -- Telegram / Notion Control Room --> Rick
Rick -- crea/actualiza issues --> Linear API
Rick -- encola tareas --> Redis
Rick -- comentarios/estado --> Notion

Linear -- webhook Issue create/update --> Dispatcher (/webhooks/linear)
Dispatcher -- map Issue -> TaskEnvelope --> Redis

Cursor/Codex -- MCP Linear --> lectura/seguimiento
Worker -- procesa TaskEnvelope --> notion.upsert_task + estado en Redis
```

---

## 3. Modelo de datos

### Linear (planning)
- **Issues**: qué hacer, descripción, equipo, prioridad, ciclo/sprint
- **Projects**: Marketing, Advisory, Lab, Infra
- **Assignee**: Rick (agente), Cursor, Codex, o "Equipo Marketing" (conceptual)
- **Labels**: `infra`, `lab`, `marketing`, `advisory`, etc.

### Notion (operational + visualization)
- **Dashboard Rick**: métricas (Workers, Redis, cuotas, tareas recientes) + **embeds de Linear** (vistas/roadmaps)
- **Control Room**: comentarios David ↔ Rick ↔ Enlace
- **Tareas Umbral**: estado de ejecución (En cola, En curso, Hecho, Bloqueado) — reflejo de Redis/Worker
- **📁 Proyectos — Umbral**: estado canónico por proyecto (portfolio)
- **📬 Entregables Rick — Revisión**: outputs revisables por David, ligados a proyectos
- **Bandeja Puente** (Enlace): Pendiente, En curso, Bloqueado, Resuelto

### Redis (execution)
- `umbral:tasks:pending`, `umbral:task:*` — cola y estado de tareas en tiempo real

---

## 4. Integración Linear ↔ Notion

### Opción A: Embed nativo (recomendado inicial)
- Pegar links de Linear en Notion → preview automático
- Escribir `/linear` en Notion para insertar vista/issue
- **Ventaja**: Sin coste extra, sin sync
- **Uso**: Dashboard Rick muestra vistas de Linear embebidas (por equipo, por sprint)

### Opción B: Unito / Zapier (sync bidireccional)
- Linear issues ↔ Notion DB items
- **Ventaja**: Un único Kanban visible en Notion
- **Inconveniente**: Pago, más complejidad

### Opción C: Solo Linear en Linear, Notion solo embeds
- Linear = único backlog
- Notion = Dashboard + Control Room + Tareas Umbral (operativo)
- Tareas Umbral ≠ espejo de Linear; Tareas Umbral = tareas **en ejecución** (Redis)

---

## 5. Roles de cada agente

### Rick (meta-orquestador)
- **Input**: Telegram, Control Room (Notion)
- **Acciones**:
  - Crear/actualizar issues en Linear (vía API)
  - Encolar tareas en Redis (Dispatcher)
  - Comentar en Notion
  - Delegar a equipos (Marketing, Advisory, Lab)
- **No**: Rick no edita código; delega a Cursor/Codex

### Cursor (este agente)
- **Input**: IDE local, `.agents/` tasks, **Linear MCP (solo lectura)**
- **Acciones**:
  - Leer issues, roadmaps, asignaciones en Linear
  - Editar código, PRs en umbral-agent-stack y repos de equipos
- **No**: Cursor no crea/actualiza issues en Linear ni encola tareas en Redis; eso lo hace Rick

### Codex (VM)
- **Input**: IDE en VM, `.agents/` tasks
- **Acciones**:
  - Ejecutar tareas que requieren VM (PAD, RPA, etc.) cuando el Dispatcher se las asigna
  - Código en repos de equipos
- **No**: Codex **no tiene acceso a Linear**; solo Worker y `.agents/`

### Enlace Notion ↔ Rick
- **Input**: Comentarios en páginas del alcance
- **Acciones**:
  - Leer comentarios de Rick
  - Pedir a Rick que cree/actualice issues en Linear
  - Mantener Bandeja Puente
- **Trigger**: Cada hora en punto (XX:00); Rick revisa a XX:10

---

## 6. Arquitectura recomendada

```
┌─────────────────────────────────────────────────────────────────────┐
│                         David (humano)                               │
│                    Telegram │ Notion Control Room                    │
└──────────────────────────┬──┴───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Rick (meta-orquestador, VPS)                       │
│  - Lee Telegram + Control Room                                        │
│  - Crea/actualiza issues en Linear (API)                              │
│  - Encola tareas en Redis                                             │
│  - Responde en Notion / Telegram                                      │
└──────┬───────────────────────────┬───────────────────────────────────┘
       │                           │
       │                           ▼
       │              ┌────────────────────────┐
       │              │  Redis (queue)         │
       │              │  Dispatcher → Worker   │
       │              └───────────┬────────────┘
       │                          │
       │              ┌───────────▼────────────┐
       │              │  Worker (VPS + VM)     │
       │              │  notion.upsert_task    │
       │              │  → Tareas Umbral       │
       │              └───────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Linear (planning)           │  Notion (comms + viz)                  │
│  - Issues, projects, sprints │  - Dashboard Rick (embeds Linear)      │
│  - Asignación                │  - Control Room                        │
│  - API + webhooks            │  - Tareas Umbral (estado ejecución)    │
└──────────────────────────────┴───────────────────────────────────────┘
       ▲
       │ MCP
       │
┌──────┴───────────────────────────────────────────────────────────────┐
│  Cursor (PC)  │  Codex (VM)                                          │
│  - Linear MCP: solo lectura                                           │
│  - Código, PRs                                                        │
│  - Codex: sin Linear; solo Worker / .agents/                          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Implementación gradual

### Fase 1 (actual)
- Notion: Dashboard Rick, Control Room, Tareas Umbral
- Redis + Worker: ejecución
- Rick: Telegram + Notion poller

### Fase 2 (añadir Linear)
1. Crear workspace Linear gratuito
2. Proyectos: Infra, Marketing, Advisory, Lab
3. Conectar Linear MCP en Cursor (y Codex en VM si aplica)
4. Rick: herramienta/skill para crear issues en Linear vía API
5. Dashboard Rick: añadir embeds de vistas Linear (por equipo/sprint)

### Fase 3 (R8 - implementado)
1. Webhook Linear -> Dispatcher: cuando se crea/actualiza un issue asignado a Rick, se encola automaticamente en Redis.
2. Filtro de seguridad:
   - Validacion de firma `Linear-Signature` (HMAC SHA256 con `LINEAR_WEBHOOK_SECRET`)
   - Solo eventos `Issue` con `action=create|update`
   - Solo assignee Rick (`LINEAR_RICK_IDENTIFIERS`, por defecto `rick`)
   - Label `no-auto` ignora el evento
3. Mapeo automatico a TaskEnvelope:
   - `task`: `llm.generate` por default (override con label `task:xxx`)
   - `task_type`: inferido por labels (`coding`, `writing`, `research`, etc.)
   - `team`: inferido por labels/equipo de Linear (`marketing`, `advisory`, `lab`, `system`)
   - `priority`: Linear 1/2 -> `high`, 3 -> `medium`, 4 -> `low`
4. Unito/Zapier: sync Linear <-> Notion (si hace falta)

### Configurar webhook en Linear (Settings)
1. Definir variables en el host del Dispatcher:
   - `REDIS_URL=redis://localhost:6379/0`
   - `LINEAR_WEBHOOK_SECRET=<secret_compartido_con_linear>`
   - `LINEAR_RICK_IDENTIFIERS=rick,rick@tu-dominio.com,<user-id-de-rick>`
2. Levantar endpoint webhook:
   - `python -m uvicorn dispatcher.linear_webhook:app --host 0.0.0.0 --port 8091`
3. En Linear:
   - `Settings -> API -> Webhooks -> Create webhook`
   - URL: `https://<dispatcher-host>/webhooks/linear`
   - Secret: mismo valor que `LINEAR_WEBHOOK_SECRET`
   - Events: `Issue` con `create` y `update`
4. Prueba rapida:
   - Crear issue con label `coding` y assignee Rick
   - Verificar que aparece en Redis (`umbral:tasks:pending`) con `source=linear_webhook`

---

## 8. Límites Linear gratuito

| Límite   | Valor  | Impacto                          |
|----------|--------|----------------------------------|
| Issues   | 250    | Aceptable para arrancar          |
| Equipos  | 2      | Crear 2 equipos: "Productivos" + "Lab" |
| Miembros | ∞      | Sin problema                     |

Si se superan 250 issues, archivar los completados o pasar a plan de pago.

---

## 9. Opción A – Identidades en Linear (recomendada hoy)

Rick crea issues en Linear y asigna a "Marketing Supervisor", "Advisory Supervisor", "Lab Researcher", etc. como assignees. El trabajo lo hace Rick al procesar, o David/Cursor bajo ese "rol". **No hay agentes autónomos**; son identidades conceptuales para trazabilidad y asignación.

### Estructura en Linear
- **Rick** (assignee principal)
- **Marketing Supervisor**, **Advisory Supervisor**, **Lab Researcher**, etc. (assignees o labels)
- **Proyectos**: Marketing, Advisory, Lab, Infra

### ¿Implementar ya?

| Criterio | Recomendación |
|----------|---------------|
| **Complejidad** | Baja — workspace Linear, API key para Rick, MCP read-only para Cursor |
| **Coste** | Gratis (plan gratuito) |
| **Beneficio** | Backlog centralizado, trazabilidad Rick → equipos, visibilidad Cursor |
| **Riesgo** | Bajo — no afecta flujo actual (Redis, Worker, Notion) |

**Recomendación:** **Sí, implementar cuando** quieras centralizar el backlog en Linear y que Rick empiece a crear issues al recibir instrucciones. No es urgente; el flujo Notion + Tareas Umbral + Redis ya funciona. Si tienes 1–2 horas para configurar Linear + API Rick, adelante. Si prefieres consolidar primero el uso actual, espera.

### Orden sugerido
1. Crear workspace Linear gratuito
2. Proyectos: Productivos (Marketing, Advisory, Infra), Lab
3. Assignees/labels: Rick, Marketing Supervisor, Advisory Supervisor, Lab Researcher
4. Rick: skill/herramienta para crear issues vía Linear API (OpenClaw o Worker task)
5. Cursor: Linear MCP read-only (solo lectura)
6. Dashboard Rick: embeds de vistas Linear

---

## 10. Sub-agentes autónomos (idea futura)

Posible implementación futura: sub-agentes LLM que ejecuten tareas asignadas en Linear de forma autónoma (Marketing Supervisor como agente real que hace SEO, Advisory como agente que genera informes, etc.).

### Desafíos
- Infraestructura por agente (LLM + API)
- Orquestación y prioridades
- Supervisión y corrección de errores
- Cuotas y coste (más tokens, más APIs)
- Coordinación entre agentes

### Cuándo evaluar
- Volumen alto y repetitivo de tareas por equipo
- Tareas bien definidas y acotadas
- Flujo actual (Rick + Linear identidades) estable
- Recursos para iterar y mantener

Dejar documentado; no implementar hasta que el flujo con identidades esté consolidado.
