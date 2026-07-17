---
fuente: Cursor (agente Auto, multi-root local)
prompt_origen: Prompt 3 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: reglas .cursor, roots/clones, skills locales, hilos activos
modo: read-only
estado_completitud: PARTIAL_TOOL_BLOCKED (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

```yaml
reglas:
  - path: 'C:\GitHub\notion-governance\.cursor\rules\governance-contract.mdc'
    resumen: 'Define Notion como runtime humano, el repositorio como fuente estructural y exige gobernanza previa a cambios.'
    contradice: false
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\notion-governance\AGENTS.md'
    resumen: 'Prioriza claridad, baja duplicación, reversibilidad y sincronización de políticas con hooks y reglas.'
    contradice: false
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-agent-stack\.cursor\rules\agent-coordination.mdc'
    resumen: 'Asigna a Cursor el rol de orquestador y obliga a revisar board, protocolo y tareas.'
    contradice: false
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-agent-stack\AGENTS.md'
    resumen: 'Describe coordinación multiagente y operación de Worker, Dispatcher, Redis y pruebas.'
    contradice: false
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-agent-stack-codex-coordinador\.cursor\rules\agent-coordination.mdc'
    resumen: 'Copia de las reglas de coordinación del stack principal.'
    contradice: false
    conflicto: 'Duplicación exacta o casi exacta con umbral-agent-stack.'
    etiqueta: DUPLICATE

  - path: 'C:\GitHub\umbral-agent-stack-codex-coordinador\AGENTS.md'
    resumen: 'Copia del contrato operativo y de coordinación de umbral-agent-stack.'
    contradice: false
    conflicto: 'Puede divergir silenciosamente del repositorio principal.'
    etiqueta: DUPLICATE

  - path: 'C:\GitHub\umbral-bot-copilot\AGENTS.md'
    resumen: 'Define el cutover Azure, Cursor como coordinador operativo y Copilot como Merge Master.'
    contradice: 'PARCIAL'
    conflicto: 'El bloque de cutover Azure convive con el modelo anterior que presenta Lovable como coordinador central; además, la fecha objetivo 2026-07-07 ya pasó.'
    etiqueta: OBSOLETE

  - path: 'C:\Users\david\.claude\plugins\cache\claude-plugins-official\netlify-skills\1.1.0\cursor\rules\netlify-skills-router.mdc'
    resumen: 'Regla global que presupone despliegue en Netlify y enruta tareas hacia skills de esa plataforma.'
    contradice: true
    conflicto: 'Contradice el destino Azure declarado por umbral-bot-copilot si se aplica indiscriminadamente a ese root.'
    etiqueta: OBSOLETE

  - path: 'C:\GitHub\umbral-bot-codex-clean\{.cursor\rules,.cursorrules,AGENTS.md,CLAUDE.md}'
    resumen: 'No fue posible comprobar si existen reglas locales.'
    contradice: UNKNOWN
    etiqueta: UNKNOWN

roots:
  - path: 'C:\GitHub\notion-governance'
    git_detectado: true
    dirty: UNKNOWN
    diagnostico: 'Root canónico de gobernanza y workspace actualmente activo.'
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-agent-stack'
    git_detectado: true
    dirty: UNKNOWN
    diagnostico: 'Repositorio principal del stack multiagente.'
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-agent-stack-codex-coordinador'
    git_detectado: true
    dirty: UNKNOWN
    diagnostico: 'Nombre y reglas indican clon especializado del stack principal; riesgo alto de divergencia.'
    etiqueta: DUPLICATE

  - path: 'C:\GitHub\umbral-bot-copilot'
    git_detectado: true
    dirty: UNKNOWN
    diagnostico: 'Clon con rol explícito de Merge Master y gateway Azure.'
    etiqueta: ACTIVE_HEALTHY

  - path: 'C:\GitHub\umbral-bot-codex-clean'
    git_detectado: false
    dirty: UNKNOWN
    diagnostico: 'Está abierto como root, pero Cursor no lo detectó como repositorio Git.'
    etiqueta: ORPHAN

  - path: 'C:\GitHub\notion-governance-cursor'
    existe: UNKNOWN
    dirty: UNKNOWN
    etiqueta: UNKNOWN

  - path: 'C:\GitHub\notion-governance-antigravity'
    existe: UNKNOWN
    dirty: UNKNOWN
    etiqueta: UNKNOWN

  - path: 'C:\GitHub\notion-governance-temp'
    existe: UNKNOWN
    dirty: UNKNOWN
    etiqueta: UNKNOWN

  - path: 'C:\GitHub\notion-governance-rick-v1-draft'
    existe: UNKNOWN
    dirty: UNKNOWN
    etiqueta: UNKNOWN

  - path: 'C:\GitHub\_wt*'
    existe: UNKNOWN
    dirty: UNKNOWN
    diagnostico: 'No se pudo ejecutar git worktree list ni enumerar directorios.'
    etiqueta: UNKNOWN

skills:
  notion-governance:
    base: 'C:\GitHub\notion-governance\.agents\skills'
    items:
      - { nombre: agents-canonical-registry, proposito: 'Mantener el registro canónico de agentes.', duplicado: 'Sí, también existe globalmente.', etiqueta: ACTIVE_HEALTHY }
      - { nombre: cursor-hooks-sync, proposito: 'Sincronizar políticas, reglas y hooks de Cursor.', duplicado: 'Sí, también existe globalmente.', etiqueta: ACTIVE_HEALTHY }
      - { nombre: delegate-to-copilot-vps, proposito: 'Delegar operaciones VPS a Copilot.', duplicado: false, etiqueta: ACTIVE_HEALTHY }
      - { nombre: notion-context-routing, proposito: 'Enrutar trabajo al contexto canónico de Notion.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-contextual-email-draft, proposito: 'Crear borradores de correo con contexto Notion.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-duplicate-consolidation, proposito: 'Detectar y consolidar duplicados en Notion.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-governance-expert, proposito: 'Aplicar el contrato integral de gobernanza Notion.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-normalize-page, proposito: 'Normalizar páginas según estructura canónica.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-page-audit, proposito: 'Auditar páginas y detectar problemas estructurales.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-session-capitalization, proposito: 'Capitalizar sesiones en objetos canónicos.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: notion-system-card, proposito: 'Crear o mantener fichas de sistemas.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: q-friday-retro, proposito: 'Ejecutar retrospectivas periódicas.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: read-codex-handoffs, proposito: 'Leer handoffs producidos por Codex.', duplicado: 'Sí, existe copia global.', etiqueta: DUPLICATE }
      - { nombre: secret-output-guard, proposito: 'Evitar exposición de secretos en salidas.', duplicado: 'Sí, existe en ambos stacks.', etiqueta: DUPLICATE }

  umbral-agent-stack:
    base: 'C:\GitHub\umbral-agent-stack'
    items:
      - { nombre: notion-governance-runtime, proposito: 'Aplicar gobernanza Notion desde el runtime.', duplicado: 'Sí, copia en codex-coordinador.', etiqueta: DUPLICATE }
      - { nombre: openclaw-vps-operator, proposito: 'Operar OpenClaw en VPS.', duplicado: 'Sí, copia en codex-coordinador.', etiqueta: DUPLICATE }
      - { nombre: openclaw-foundry-activation, proposito: 'Activar integración OpenClaw/Foundry.', duplicado: 'Sí, copia en codex-coordinador.', etiqueta: DUPLICATE }
      - { nombre: secret-output-guard, proposito: 'Proteger secretos en salidas.', duplicado: 'Sí, múltiples roots.', etiqueta: DUPLICATE }
      - { nombre: vps-deploy-after-edit, proposito: 'Desplegar al VPS después de cambios autorizados.', duplicado: 'Sí, copia en codex-coordinador.', etiqueta: DUPLICATE }
      - { nombre: windows-vps-execution-split, proposito: 'Separar ejecución local Windows y VPS.', duplicado: 'Sí, copia en codex-coordinador.', etiqueta: DUPLICATE }

  umbral-agent-stack-codex-coordinador:
    base: 'C:\GitHub\umbral-agent-stack-codex-coordinador'
    proposito: 'Contiene las mismas seis skills locales que umbral-agent-stack.'
    duplicado: true
    etiqueta: DUPLICATE

  umbral-bot-copilot:
    items: UNKNOWN
    etiqueta: UNKNOWN

  umbral-bot-codex-clean:
    items: UNKNOWN
    etiqueta: UNKNOWN

hilos:
  - titulo: UNKNOWN
    estado: 'No se pudieron leer transcripts recientes ni boards de tareas.'
    etiqueta: UNKNOWN

oportunidades:
  - accion: 'Validar y retirar umbral-bot-codex-clean del workspace si realmente carece de .git.'
    esfuerzo: '5-10 minutos'
    etiqueta: ORPHAN

  - accion: 'Comparar umbral-agent-stack-codex-coordinador con umbral-agent-stack y reemplazarlo por una rama o worktree documentado.'
    esfuerzo: '20-40 minutos'
    etiqueta: DUPLICATE

  - accion: 'Auditar notion-governance-{cursor,antigravity,temp,rick-v1-draft}; conservar únicamente clones con commits exclusivos o trabajo dirty.'
    esfuerzo: '30-60 minutos'
    etiqueta: UNKNOWN

  - accion: 'Revisar git worktree list y podar worktrees _wt* cuya rama ya esté integrada.'
    esfuerzo: '15-30 minutos'
    etiqueta: UNKNOWN

  - accion: 'Limitar la regla global de Netlify a proyectos Netlify y actualizar o archivar el bloque temporal de cutover Azure.'
    esfuerzo: '15-25 minutos'
    etiqueta: OBSOLETE

unknowns:
  - 'git status --short de todos los roots.'
  - 'Existencia y estado de clones notion-governance-* y worktrees _wt*.'
  - 'Inventario completo de CLAUDE.md, .cursorrules y reglas no incluidas en el contexto.'
  - 'Chats, Composer sessions, boards y tareas recientes.'
  - 'Causa: el hook protect-canonical.py falló en modo fail-closed con MainThreadShellExec not initialized y bloqueó todas las lecturas y comandos.'
  - 'No se leyó ni reprodujo ningún archivo .env.'
```
