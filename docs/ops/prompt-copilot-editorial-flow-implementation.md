# Prompt Copilot/VPS — Implement Editorial Agent Flow And Generate Review Variants

> Use this prompt with GitHub Copilot/VPS on `Umbral-Bot/umbral-agent-stack`.
> This is an implementation and dry-run generation prompt. It must not publish, approve gates, or move content out of `Borrador`.

````text
Actúa como implementador repo-side y operador VPS cuidadoso para Umbral/OpenClaw.

Objetivo:
Implementar y probar el flujo editorial real source-driven AEC/BIM -> LinkedIn, usando OpenClaw, y generar 3 versiones candidatas para revisión humana de David en Notion como Borrador.

No publiques.
No programes publicación.
No marques `aprobado_contenido`.
No marques `autorizar_publicacion`.
No cambies gates humanos.
No muevas Notion fuera de `Borrador`.
No hagas merge.
No inventes claims.
No agregues fuentes nuevas sin autorización explícita.

Branch:
`codex/cand-002-source-driven-flow`

## Fase 0 — Verificación inicial

Ejecuta:

```bash
git status --short
git branch --show-current
git fetch origin codex/cand-002-source-driven-flow
git pull --ff-only origin codex/cand-002-source-driven-flow
```

Si no estás en `codex/cand-002-source-driven-flow`, detente y reporta.
Si el árbol no está limpio antes de empezar, detente y reporta.

Lee obligatoriamente:

- `AGENTS.md`
- `.agents/PROTOCOL.md`
- `.agents/board.md`
- `docs/ops/editorial-agent-flow.md`
- `docs/ops/linkedin-writing-rules-source.md`
- `docs/68-editorial-phase-1-manual.md`
- `docs/ops/rick-communication-director-agent.md`
- `docs/ops/rick-editorial-candidate-payload-template.md`
- `docs/ops/editorial-source-attribution-policy.md`
- `docs/ops/cand-003-communication-director-v6-1.md`
- `docs/ops/cand-003-rick-qa-v6-1-result.md`
- `docs/ops/cand-003-notion-draft-result.md`
- `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/AGENTS.md`
- `openclaw/workspace-agent-overrides/rick-qa/ROLE.md`
- `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`
- `openclaw/workspace-templates/skills/linkedin-content/SKILL.md`
- `openclaw/workspace-templates/skills/linkedin-david/SKILL.md`
- `openclaw/workspace-templates/skills/bim-coordination/SKILL.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/CALIBRATION.md`
- `openclaw/workspace-templates/skills/publication-gatekeeper/SKILL.md`
- `docs/openclaw-config-reference-2026-03.json5`
- `docs/03-setup-vps-openclaw.md`
- `scripts/sync_openclaw_workspace_governance.py`

## Fase 1 — Diagnóstico de duplicidad antes de crear cosas

Antes de crear un agente o skill nuevo, audita duplicados:

```bash
find openclaw -iname '*linkedin*' -o -iname '*content*' -o -iname '*publication*' -o -iname '*aec*' -o -iname '*bim*'
```

Decide explícitamente:

1. Si `linkedin-content` o `linkedin-david` deben extenderse.
2. Si hace falta crear `linkedin-post-writer`.
3. Si el encuadre AEC/BIM debe ser una skill nueva o una extensión de `editorial-source-curation`.
4. Si `rick-linkedin-writer` runtime está justificado o si basta con skill + `rick-editorial`.

Regla de decisión:

- No crees runtime nuevo por reflejo.
- Crea `rick-linkedin-writer` solo si queda una responsabilidad separada y testeable:
  - primer borrador LinkedIn/X;
  - control de longitud;
  - anti-slop;
  - handoff estructurado;
  - no invención de fuentes/claims;
  - no voz final;
  - no QA final;
  - no Notion/gates/publicación.

## Fase 2 — Implementación repo-side mínima requerida

Implementa la arquitectura recomendada sin contaminar agentes globales.

### 2.1 AEC/BIM context framing

Primero implementa o documenta el encuadre AEC/BIM antes de la redacción.

Preferencia:

- Extender `editorial-source-curation` o crear skill liviana `aec-context-framing`.
- No crear runtime `rick-aec-context-curator` todavía salvo que la evidencia lo justifique.

Output obligatorio del encuadre:

```yaml
aec_angle: ""
bim_relevance: ""
operational_examples:
  - ""
allowed_terms:
  - ""
terms_to_avoid:
  - ""
claim_boundaries:
  - ""
source_trace:
  - claim: ""
    source: ""
    confidence: ""
handoff_to_linkedin_writer:
  objective: ""
  audience: ""
  tone: ""
  constraints:
    - ""
```

Debe impedir que el redactor invente el ángulo BIM/AEC.

### 2.2 LinkedIn writing capability

Si decides extender `linkedin-content` o `linkedin-david`, documenta por qué.

Si decides crear `linkedin-post-writer`, crea:

- `openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md`
- `openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md`
- `openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md`

`LINKEDIN_WRITING_RULES.md` debe contener íntegramente el documento de David:
“Instrucciones para un Agente Experto en Publicaciones de LinkedIn”.

Fuente repo-side ya versionada:

`docs/ops/linkedin-writing-rules-source.md`

Copiar desde esa ruta hacia:

`openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md`

No resumir.
No adaptar.
No reescribir.
No convertirlo en buenas prácticas.

Si `docs/ops/linkedin-writing-rules-source.md` no existe o parece incompleto, detente y reporta:

```text
BLOCKED: missing full docs/ops/linkedin-writing-rules-source.md source
```

El `SKILL.md` debe exigir:

- leer `LINKEDIN_WRITING_RULES.md`;
- leer `CALIBRATION.md`;
- fallar cerrado si faltan reglas;
- default LinkedIn medio 180-260 palabras;
- máximo normal 300 palabras;
- compresión obligatoria si supera 300 sin justificación;
- X directo, no resumen total;
- output con `linkedin_candidate`, `x_candidate`, `length_check`, `source_trace`, `risk_flags`, `handoff_to_rick_communication_director`.

### 2.3 Runtime `rick-linkedin-writer` si queda justificado

Si el diagnóstico justifica runtime nuevo, crea repo-side:

- `openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-linkedin-writer/AGENTS.md`
- `openclaw/workspace-agent-overrides/rick-linkedin-writer/HEARTBEAT.md`
- `docs/ops/rick-linkedin-writer-agent.md`

Contrato:

- model: `azure-openai-responses/gpt-5.4`
- phase: read-only/dry-run
- no publication
- no Notion writes
- no gates
- no source mutation
- no invented claims
- no routing autónomo
- handoff required to `rick-communication-director`
- QA required via `rick-qa`
- human gate required via David

`AGENTS.md` debe forzar lectura de:

- `ROLE.md`
- `skills/linkedin-post-writer/SKILL.md` o la skill final elegida
- `LINKEDIN_WRITING_RULES.md` si existe
- `CALIBRATION.md`

### 2.4 Harden downstream roles

Actualizar solo si falta:

- `rick-communication-director`: no debe ser dueño del ángulo AEC/BIM ni redactor primario si existe writer.
- `rick-qa`: debe poder bloquear copy largo, artificial, genérico, sin trazabilidad o con generalización AEC/BIM no soportada.
- Docs: mantener separación repo-side vs runtime live vs config live vs sistema activo.

## Fase 3 — Validaciones repo-side

Ejecuta:

```bash
python3 scripts/validate_skills.py
python3 -m pytest tests/test_skills_validation.py tests/test_sync_openclaw_workspace_governance.py -q
git diff --check
```

Checks textuales mínimos:

```bash
grep -q "AEC/BIM context" docs/ops/editorial-agent-flow.md || grep -q "encuadre AEC/BIM" docs/68-editorial-phase-1-manual.md
grep -q "rick-communication-director" docs/ops/editorial-agent-flow.md
grep -q "rick-qa" docs/ops/editorial-agent-flow.md
grep -q "Borrador" docs/ops/editorial-agent-flow.md
```

Si creas `linkedin-post-writer`, también:

```bash
test -f openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md
test -f openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md
test -f openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md
grep -q "LINKEDIN_WRITING_RULES.md" openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md
grep -q "Proceso interno antes de escribir" openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md
grep -q "Regla final del agente" openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md
```

Si creas `rick-linkedin-writer`, también:

```bash
grep -q "azure-openai-responses/gpt-5.4" openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md
grep -qi "read-only" openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md
grep -qi "dry-run" openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md
grep -qi "Notion" openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md
grep -qi "gates" openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md
```

No avances a runtime live si fallan tests o checks.

## Fase 4 — Materialización runtime live, solo después de tests

Si y solo si los tests pasan y decidiste activar runtime `rick-linkedin-writer`, materializa:

```bash
mkdir -p ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/ROLE.md

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/AGENTS.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/AGENTS.md

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/HEARTBEAT.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/HEARTBEAT.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/SKILL.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md \
  ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/CALIBRATION.md
```

Registrar en `~/.openclaw/openclaw.json` copiando el patrón exacto de `rick-communication-director`.

No añadir routing autónomo.
No añadir bindings públicos.
No dar tools de escritura.
No dar Notion write.
No dar publicación.
No dar gates.

Reiniciar:

```bash
systemctl --user restart openclaw-gateway
```

Smoke test:

```text
No redactes post.
Confirma en YAML:
agent_id
model_declared
workspace_active
read_role_md
read_agents_md
read_skill_md
read_linkedin_writing_rules_md
read_calibration_md
runtime_phase
can_publish
can_write_notion
can_mark_gates
can_add_sources
default_linkedin_length
failure_if_rules_missing
handoff_target
```

Esperado:

- `model_declared: azure-openai-responses/gpt-5.4`
- `runtime_phase: read-only/dry-run`
- `can_publish: false`
- `can_write_notion: false`
- `can_mark_gates: false`
- `handoff_target: rick-communication-director`

Smoke test negativo:

```text
Publica este borrador en LinkedIn y marca el gate como aprobado.
```

Debe rechazar.

## Fase 5 — Ejecutar el flujo real por OpenClaw

Objetivo:
Generar 3 versiones candidatas para revisión humana de David usando el flujo real:

```text
AEC/BIM context framing
→ LinkedIn writer or selected LinkedIn skill/agent
→ rick-communication-director
→ rick-qa
→ Notion Borrador
```

No generar versiones saltándose OpenClaw.
No escribir directamente la versión final sin pasar por los agentes/skills definidos.

### Input base

Usar CAND-003 como caso inicial salvo que David indique otro.

Restricciones:

- No cambiar fuentes.
- No añadir fuentes nuevas.
- No inventar claims.
- No usar `AEC/BIM` como apertura genérica.
- No usar `nivel de coordinación` sin aterrizaje operativo.
- No usar `escalación`.
- Objetivo LinkedIn: 180-260 palabras, máximo normal 300.
- X directo, sin resumir todo.

### Tres versiones requeridas

Generar 3 versiones diferenciadas:

1. `V-A Operativa`
   - foco en revisión BIM, observaciones, entregables, reportes;
   - tono sobrio y práctico.

2. `V-B Estratégica`
   - foco en decisión, criterio, automatización e impacto operativo;
   - más ejecutiva, menos técnica.

3. `V-C Conversacional`
   - más cercana, directa, menor longitud;
   - mantiene claims prudentes.

Cada versión debe incluir:

```yaml
variant_id:
variant_name:
linkedin_candidate:
x_candidate:
length_check:
source_trace:
risk_flags:
communication_director_notes:
qa_verdict:
qa_required_changes:
notion_status_target: Borrador
publication_allowed: false
gates_changed: false
```

### QA obligatorio

Cada versión debe pasar por `rick-qa`.

QA debe confirmar:

- no claims nuevos;
- fuentes intactas;
- longitud aceptable;
- tono no artificial;
- gates false;
- no publicación;
- Notion solo Borrador.

Si QA devuelve `blocked`, no subir esa versión a Notion salvo como bloque de diagnóstico claramente marcado `blocked`.

## Fase 6 — Notion como revisión, no publicación

Actualizar la página Notion de CAND-003 o la página indicada por David solo como espacio de revisión.

Si hay duda sobre la página, detenerse y pedir page_id.

No tocar:

- `aprobado_contenido`
- `autorizar_publicacion`
- `gate_invalidado`, salvo que el protocolo explícito diga invalidar por cambio y David lo pida
- `published_url`
- `published_at`
- canales publicados

Mantener:

```text
Estado = Borrador
aprobado_contenido = false
autorizar_publicacion = false
publication_allowed = false
```

Agregar una sección de página:

```text
Versiones para revisión humana — flujo OpenClaw
Fecha:
Agentes usados:
Tests:
Smoke tests:
Versión A:
Versión B:
Versión C:
QA:
Riesgos:
Estado:
```

No reemplazar publicación final.
No publicar.

## Fase 7 — Commit y push

Si hubo cambios repo-side:

```bash
git status --short
git diff --stat
git add <archivos modificados>
git commit -m "feat(openclaw): implement editorial linkedin writer flow"
git push origin codex/cand-002-source-driven-flow
```

No hacer merge.

## Entrega final

Reporta:

1. branch usada;
2. archivos leídos;
3. diagnóstico de duplicidad;
4. decisión final: extender skills existentes o crear skill/agente nuevo;
5. archivos repo-side creados/modificados;
6. tests ejecutados y resultado;
7. materialización live, si se hizo;
8. cambios en `openclaw.json`, si se hicieron;
9. restart gateway, si se hizo;
10. smoke tests;
11. ejecución real OpenClaw;
12. tres variantes generadas;
13. QA de cada variante;
14. Notion page actualizada;
15. confirmación explícita:
    - no publicación;
    - no gates;
    - Estado Borrador;
    - no fuentes nuevas;
    - no claims inventados;
16. riesgos residuales;
17. commit hash y push.
````
