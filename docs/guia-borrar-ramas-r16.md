# Guía para borrar ramas remotas — R16

> **Fuente:** `docs/analisis-contenido-perdido-r16.md` (PR #87)  
> **IMPORTANTE:** NO ejecutar sin revisión. Verificar que el contenido ya está en main o fue recuperado.

## Ramas a borrar

### Grupo 1 — Vacías (0 commits adelante de main)

Estas ramas ya fueron mergeadas a main por otra vía. Se pueden borrar sin riesgo.

```bash
git push origin --delete integracion-prs-69-70-71-73
git push origin --delete feat/claude-skill-builder-pipeline
git push origin --delete feat/claude-skills-validation
git push origin --delete feat/codex-skills-notion-windows
git push origin --delete feat/copilot-openclaw-proxy
git push origin --delete feat/copilot-skills-llm-make-obs
git push origin --delete feat/cursor-cloud-skills-figma
git push origin --delete feat/skills-coverage-single-word
git push origin --delete cursor/pytest-fastapi-lifespan-9a62
git push origin --delete cursor/tests-document-generator-dependencias-8af0
git push origin --delete cursor/workflow-ci-pytest-a6f3
```

### Grupo 2 — Destructivas (divergencias / intentos fallidos)

Contenido no valioso. Se pueden borrar sin pérdida.

```bash
git push origin --delete copilot/create-umbral-agent-stack-repo
git push origin --delete cursor/development-environment-setup-6340
git push origin --delete cursor/development-environment-setup-ac64
git push origin --delete cursor/fusi-n-prs-69-70-71-23e1
git push origin --delete cursor/integraci-n-de-prs-en-main-3876
git push origin --delete cursor/integraci-n-de-prs-y-pruebas-1084
git push origin --delete cursor/board-estado-actual-e573
git push origin --delete cursor/r16-cierre-y-documentaci-n-bc44
git push origin --delete cursor/cierre-integraci-n-main-4905
git push origin --delete feat/ci-readme-verificacion
git push origin --delete feat/r16-080-limpieza-prs-docs
```

### Grupo 3 — Contenido recuperado (borrar después de merge de PRs)

Borrar solo después de que los PRs de recuperación estén mergeados.

```bash
# Después de mergear PR #88 (ya mergeado ✅):
git push origin --delete feat/browser-automation-vm-research

# Después de mergear PR #89:
git push origin --delete cursor/bit-cora-contenido-enriquecido-4099

# Después de mergear PR #90:
git push origin --delete feat/copilot-azure-foundry-audio

# Contenido reemplazado por Task 083:
git push origin --delete copilot/082-capitalizar-cerrados
```

### Grupo 4 — Evaluar antes de borrar

```bash
# Contiene docs de Power BI (.pbix/.pbip) — registrar como KI antes de borrar:
git push origin --delete cursor/power-bi-libraries-formats-5c1b

# Contiene scripts populate_bitacora — verificar solapamiento con PR #89:
git push origin --delete feat/bitacora-populate

# Contiene diagnóstico hackathon — revisar si ya en main:
git push origin --delete cursor/diagn-stico-completo-del-sistema-5be1
```

## Cómo ejecutar

1. **Verificar** que estás en main: `git checkout main && git pull origin main`
2. **Copiar** los comandos del grupo deseado
3. **Ejecutar** uno a uno o en batch
4. **Actualizar** `.agents/board.md` con el conteo final de ramas

## Script batch (todos los grupos 1 + 2)

```bash
# Pegar en terminal. Borrar las 22 ramas de grupos 1 y 2:
for branch in \
  integracion-prs-69-70-71-73 \
  feat/claude-skill-builder-pipeline \
  feat/claude-skills-validation \
  feat/codex-skills-notion-windows \
  feat/copilot-openclaw-proxy \
  feat/copilot-skills-llm-make-obs \
  feat/cursor-cloud-skills-figma \
  feat/skills-coverage-single-word \
  cursor/pytest-fastapi-lifespan-9a62 \
  cursor/tests-document-generator-dependencias-8af0 \
  cursor/workflow-ci-pytest-a6f3 \
  copilot/create-umbral-agent-stack-repo \
  cursor/development-environment-setup-6340 \
  cursor/development-environment-setup-ac64 \
  cursor/fusi-n-prs-69-70-71-23e1 \
  cursor/integraci-n-de-prs-en-main-3876 \
  cursor/integraci-n-de-prs-y-pruebas-1084 \
  cursor/board-estado-actual-e573 \
  cursor/r16-cierre-y-documentaci-n-bc44 \
  cursor/cierre-integraci-n-main-4905 \
  feat/ci-readme-verificacion \
  feat/r16-080-limpieza-prs-docs
do
  git push origin --delete "$branch"
done
```
