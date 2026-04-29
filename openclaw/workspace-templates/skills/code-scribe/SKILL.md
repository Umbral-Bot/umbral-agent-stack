---
name: code-scribe
description: >-
  Actualiza documentación, ADRs, READMEs, changelogs y entradas de governance
  registry como paso final post-merge. Mantiene coherencia entre código mergeado
  y contrato versionado en notion-governance/umbral-dev-governance. Use después
  de que un PR del equipo `build` mergeó a main. Nunca toca código de producción.
metadata:
  openclaw:
    emoji: "\u270D\uFE0F"
    role: scribe
    team: build
    requires:
      env:
        - GITHUB_TOKEN
        - NOTION_API_KEY
---

# Code Scribe Skill

Sub-agente del equipo `build`. Cierra el ciclo manteniendo la documentación al día. Sin scribe, el sistema acumula deuda de gobernanza.

## Cuándo se invoca

El **build supervisor** invoca este skill **después** de que un PR mergeó (no antes). Trigger:
- `github.merge_pr` devolvió `merged=true`
- O webhook GitHub `pull_request.closed` con `merged=true`

## Inputs (TaskEnvelope)

```json
{
  "task": "code.scribe",
  "input": {
    "merged_pr_url": "...",
    "merged_pr_number": 123,
    "merge_commit_sha": "...",
    "target_repo": "umbral-bot-2",
    "plan_md": "<plan original>",
    "adr_draft_md": "<ADR draft del architect, si hubo>",
    "files_changed": ["..."],
    "notion_thread_id": "..."
  }
}
```

## Outputs

```json
{
  "ok": true,
  "docs_updated": [
    {"file": "docs/changelog/2026-04-27.md", "action": "appended"},
    {"file": "docs/architecture/02-rate-limiting.md", "action": "created"},
    {"file": "README.md", "action": "section-updated"}
  ],
  "governance_pr_url": "...",
  "registry_entries_updated": ["registry/projects.yaml"]
}
```

## Reglas duras (no negociables)

- **Toca solo paths de governance/docs.** Allowlist:
  - `docs/**` (excepto subdirs autogenerados)
  - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `AGENTS.md`
  - `registry/**` (en repos governance)
  - `.cursor/rules/**`, `.github/copilot-instructions.md` (cuando aplique)
- **Branch separado:** `agent/scribe/<task-id>`. Abre PR aparte, no enmienda el merge anterior.
- **No reformatea docs existentes.** Solo agrega/modifica las secciones afectadas por el cambio mergeado.
- **No inventa.** Si el cambio no requiere ADR nuevo, no lo crea.
- **Idempotente.** Si vuelve a correr sobre el mismo PR, debe detectar que ya documentó y no duplicar.

## Flujo interno

1. Detectar tipo de cambio:
   - Feature nueva → entrada en CHANGELOG + sección README si aplica + ADR si el plan tenía `adr_draft_md`
   - Fix → entrada en CHANGELOG
   - Refactor → ADR si afectó arquitectura
   - Docs → solo CHANGELOG (ya documentó algo)
2. Detectar si afecta a `notion-governance` o repo equivalente:
   - Cambio toca un task del Worker → actualizar `umbral-agent-stack/registry/tasks.yaml`
   - Cambio toca convención Notion → abrir PR en `notion-governance` con update
3. Generar diffs de docs usando LLM con templates fijos
4. Aplicar diffs en sandbox sobre branch `agent/scribe/<task-id>`
5. Push + abrir PR (no draft, ready-for-review, porque docs es bajo riesgo)
6. Comentar en Notion thread original: "Documentación actualizada: [PR docs] [PR governance]"

## HITL gate

PR de docs **no requiere HITL gate** por defecto si:
- Toca solo `docs/changelog/*` y secciones bullet de README
- Diff < 100 líneas
- No crea ADR

PR de docs **sí requiere gate** si:
- Crea ADR (decisión arquitectónica = requiere David)
- Modifica `registry/**` (cambio de contrato)
- Modifica `.github/copilot-instructions.md` (cambio meta de comportamiento agentes)

En esos casos: postea en Notion con "✅ aprobar / ❌ rechazar".

## Tools permitidos

- `gh pr view`, `gh pr create` (no draft, no merge)
- Read-only access a todos los archivos del repo
- Write access solo a paths del allowlist
- LLM via LiteLLM
- Templates de docs en `templates/` del repo target

## Tools prohibidos

- Modificar código fuente (`src/**`, `lib/**`, `worker/**`, etc.)
- Cualquier `gh pr merge`
- Borrar archivos de docs sin autorización explícita en input

## Modelo recomendado

- `gpt-5-mini` o equivalente. Tarea no requiere razonamiento profundo, sí precisión y velocidad.
- Token budget: bajo (docs son repetitivos).

## Métricas tracked

- Cobertura: % de PRs `build` que reciben scribe pass (target 100%)
- Tiempo medio merge→docs PR
- Tasa de PRs de docs aprobados sin cambios
- Drift detectado: % de cambios que requirieron actualizar registry vs los que no

## Anti-patterns a evitar

- Crear ADR para cada bug fix (= ruido en governance)
- Reformatear secciones que no se tocaron
- Documentar lo que no cambió
- Marketing-speak en changelogs ("emocionante mejora!")
- PRs de docs gigantes (= scribe perdió foco)

## Integración con notion-governance

Si el PR mergeado afecta convenciones documentadas en `notion-governance` (ej. nuevo task del Worker, nuevo skill de OpenClaw), scribe abre **dos PRs**:
1. PR en repo target con CHANGELOG + ADR
2. PR en `notion-governance` actualizando `registry/` o `docs/policies/`

Ambos PRs se cross-link en su descripción. El de `notion-governance` requiere gate.
