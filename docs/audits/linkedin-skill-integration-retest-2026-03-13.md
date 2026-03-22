## LinkedIn Skill Integration Retest — 2026-03-13

Ejecutado por: codex

### Objetivo

Integrar la skill nueva `linkedin-marketing-api-embudo` al repo y a los workspaces de Rick, y comprobar que pueda convivir con `competitive-funnel-benchmark` sin romper el benchmark competitivo del proyecto embudo.

### Insumo nuevo

Skill compartida cargada por David en:

- `Rick-David\Skills\linkedin-marketing-api-embudo`

### Integración realizada

La skill se integró al repo en:

- `openclaw/workspace-templates/skills/linkedin-marketing-api-embudo/SKILL.md`
- `openclaw/workspace-templates/skills/linkedin-marketing-api-embudo/references/capabilities-matrix.md`
- `openclaw/workspace-templates/skills/linkedin-marketing-api-embudo/references/oauth-and-scopes.md`
- `openclaw/workspace-templates/skills/linkedin-marketing-api-embudo/references/embudo-use-cases.md`
- `openclaw/workspace-templates/skills/linkedin-marketing-api-embudo/references/fallback-strategy.md`

Además se reforzó:

- `openclaw/workspace-templates/skills/competitive-funnel-benchmark/SKILL.md`

para dejar explícito que:

- el teardown público de funnel no debe ser reemplazado por la skill de API;
- la skill de API debe usarse cuando el caso cruce hacia permisos, product surfaces, analytics, organization posting, lead sync o capabilities oficiales.

### Validación estructural

Comando ejecutado:

- `python scripts/validate_skills.py`

Resultado:

- `All skills validated successfully`

### Despliegue a la VPS

La skill `linkedin-marketing-api-embudo` se sincronizó a:

- workspace principal de Rick
- `rick-orchestrator`
- `rick-tracker`
- `rick-delivery`
- `rick-qa`
- `rick-ops`

Y se reinició:

- `openclaw-gateway.service`

### Retest controlado

Se lanzó un retest contra `main` pidiendo a Rick:

1. retomar el caso Cristian Tala,
2. distinguir entre benchmark público real,
3. adaptación para Umbral,
4. y qué parte sí/no resolvería LinkedIn Marketing API.

### Evidencia de ejecución real

En la sesión principal se observó:

- benchmark público previo reutilizado
- nueva capa de análisis orientada a API oficial
- persistencia nueva en proyecto

Tools observadas en el tramo útil:

- `umbral_windows_fs_write_text`
- `umbral_linear_update_issue_status`
- `umbral_notion_upsert_project`

### Persistencia confirmada

Artefacto nuevo creado:

- `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\benchmark-cristian-tala-linkedin-vs-marketing-api-2026-03-13.md`

Verificación independiente:

- lectura directa al Worker remoto de la VM
- `ok: true`
- longitud: `10000`

### Trazabilidad confirmada

Linear:

- comentario agregado en la issue del proyecto con el nuevo artefacto

Notion:

- `Proyecto Embudo Ventas` actualizado otra vez vía `notion.upsert_project`

### Resultado

La integración fue exitosa.

Rick ahora puede:

- separar benchmark público visible de implementación oficial vía API;
- mantener la lógica correcta de embudo;
- y persistir el resultado dentro del proyecto, no solo responder en chat.

### Lectura operativa

La nueva skill no reemplaza `competitive-funnel-benchmark`.

Sirve para resolver la pregunta correcta:

- qué parte del sistema de LinkedIn se puede conectar con APIs oficiales,
- qué requiere aprobación,
- y qué sigue viviendo fuera de LinkedIn en el stack propio de Umbral.

Eso es exactamente el uso correcto para el proyecto embudo.
