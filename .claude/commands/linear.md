# Linear — Umbral Agent Stack

Gestión de issues, proyectos y workflows en Linear para el proyecto Umbral.
MCP Linear ya conectado vía OAuth en Claude Code.

## Contexto del workspace

**Team:** `Umbral` (ID: `a586e97e-6ca8-45d7-8a38-bbd0c5cdb0cc`)
**Usuario:** David Moreira (assignee: `"me"`)

**Proyectos activos:**
- `Mejora Continua Agent Stack` — routing, evals, drift operativo
- Listar todos: `list_projects` con team Umbral

**Labels frecuentes:** System, Agent Stack, Mejora Continua, Drift, Infra

**Convención de branch:** `claude/<issue-id>-<descripcion-corta>`
Ejemplo: `claude/umb-77-model-routing-config`

## Operaciones frecuentes

### Ver mis issues activos
```
list_issues: assignee="me", state=["In Progress", "Todo", "Backlog"]
```

### Ver backlog del proyecto
```
list_issues: project="Mejora Continua Agent Stack", includeArchived=false
```

### Crear issue nuevo
```
save_issue:
  team: Umbral
  title: [Slice N] Verbo — Componente
  description: |
    ## Contexto
    <por qué existe este issue>

    ## Hallazgos
    <evidencia concreta>

    ## Criterios de cierre
    - [ ] criterio 1
    - [ ] criterio 2
  priority: 2  # 1=Urgent, 2=High, 3=Normal, 4=Low
  labels: ["System", "Agent Stack"]
  project: <nombre o ID del proyecto>
```

### Actualizar issue existente
```
save_issue:
  id: UMB-XX
  status: "In Progress"
  description: <nuevo contenido>
```

### Agregar comentario
```
save_comment:
  issueId: UMB-XX
  body: "Implementado en branch claude/umb-xx-...\n\nResultados: ..."
```

## Workflow estándar del repo

1. **Issue existe en Linear** → crear branch `claude/<id>-<desc>`
2. **Implementar** → commitear con `Closes UMB-XX` en el mensaje
3. **Abrir PR** → el título del PR debe reflejar el issue
4. **Al cerrar PR** → issue se cierra automáticamente si usaste `Closes UMB-XX`

## Convención de títulos de issues
- `[Slice N] Verbo — Descripción` para trabajo iterativo
- `[Spike] Tema` para investigación/diagnóstico
- `[Hotfix] Componente: problema` para bugs críticos
- `[Audit] Frente: descripción` para auditorías

## Prioridades
- `1 Urgent` — sistema caído o bloqueante de producción
- `2 High` — impacta operación real, resolver esta semana
- `3 Normal` — mejora planificada, puede esperar al próximo sprint
- `4 Low` — nice to have, backlog

## Archivos de referencia
- `docs/67-linear-agent-stack-protocol.md` — protocolo Linear del stack
- `docs/61-audit-traceability-governance.md` — gobernanza de auditorías
- `AGENTS.md` — coordinación inter-agentes con Linear
