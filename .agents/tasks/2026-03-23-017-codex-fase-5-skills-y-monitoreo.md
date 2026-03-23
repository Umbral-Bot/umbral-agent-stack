---
id: "2026-03-23-017"
title: "Fase 5: skills reales faltantes y monitoreo continuo del stack"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T20:16:37-03:00
updated_at: 2026-03-23T23:31:00-03:00
---

## Objetivo
Cerrar el hueco real de skills detectado en el super diagnostico de interconectividad y dejar una base de monitoreo continuo proporcional, sin duplicar skills ya cubiertas por el arbol actual.

## Contexto
- `docs/audits/super-diagnostico-interconectividad-2026-03-23.md`
- `reports/skills-coverage-r12.md`
- `scripts/skills_coverage_report.py`
- `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md`
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`
- `worker/tasks/google_audio.py`
- `worker/tasks/gui.py`
- `worker/tasks/windows.py`

## Criterios de aceptacion
- [ ] Existe una skill repo-native `system-interconnectivity-diagnostics`.
- [ ] Existe una skill repo-native `google-audio-generation`.
- [ ] `browser-automation-vm` cubre de forma operativa `gui.*` y `windows.open_url`.
- [ ] `notion-project-registry` queda endurecida para operacion registry-first sin ambiguedad.
- [ ] `scripts/skills_coverage_report.py` y `reports/skills-coverage-r12.md` reflejan la nueva cobertura.
- [ ] Validacion de skills y tests relevantes en verde.

## Log
### [codex] 2026-03-23 20:16
Inicio de Fase 5 desde `main` en rama `codex/fase-5-skills-y-monitoreo`. Se formaliza el trabajo para cerrar los huecos reales de skills (`google.audio.generate`, `gui.*`, `windows.open_url`) y dejar anotados como diferidos post-fases los temas de tracking repo-side de OpenClaw y atribucion fina de costo/tokens por componente.

### [codex] 2026-03-23 23:31
Fase 5 cerrada. Se crearon las skills `system-interconnectivity-diagnostics` y `google-audio-generation`; se endurecieron `browser-automation-vm` y `notion-project-registry`; se alinearon `openclaw/workspace-templates/AGENTS.md`, `linear`, `n8n`, `notion` y `google-cloud-vertex` para que la cobertura estricta de task names tambien quede limpia. Se corrigio `scripts/skills_coverage_report.py` para imprimir bien en Windows y mapear `google.audio.generate`, `gui.*` y `windows.open_url`. Validacion: `python scripts/validate_skills.py` OK, `python scripts/skills_coverage_report.py` -> 80/80 (100%), `python -m pytest tests/test_skills_validation.py tests/test_skills_coverage.py -q` -> 93 passed, `WORKER_TOKEN=test python -m pytest tests -q` -> 1219 passed, 4 skipped.
