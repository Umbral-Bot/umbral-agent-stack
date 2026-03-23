---
id: "2026-03-23-013"
title: "GitLab sandbox mirror desde GitHub sin cambiar el tracker canonico"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-23T15:03:52-03:00
updated_at: 2026-03-23T15:17:00-03:00
---

## Objetivo
Habilitar un mirror/sandbox opcional en GitLab Free sin mover el seguimiento principal fuera de GitHub + Linear + Notion.

## Contexto
- El repo ya usa GitHub como origen canonico de codigo y PRs.
- El usuario quiere evaluar GitLab como mirror/sandbox, no como tracker principal.
- En GitLab Free, el pull mirroring desde GitHub no es la opcion adecuada para este caso; conviene empujar desde GitHub hacia GitLab.

## Criterios de aceptación
- [x] Existe un workflow de GitHub Actions para publicar `main` y tags a GitLab cuando se configure el secret.
- [x] Hay documentacion concreta de setup, gobernanza y recovery del mirror.
- [x] README deja claro que GitLab queda como mirror/sandbox opcional y no como tracker canonico.
- [x] Task y board quedan actualizados con resultado real.

## Log
### [codex] 2026-03-23 15:03
Inicio de trabajo. Voy a implementar el soporte repo-side para un mirror/sandbox de GitLab manteniendo GitHub + Linear + Notion como fuentes canonicas.

### [codex] 2026-03-23 15:17
Implementado soporte repo-side:

- workflow [`gitlab-mirror.yml`](C:/GitHub/umbral-agent-stack-codex/.github/workflows/gitlab-mirror.yml) para sincronizar `main` + tags hacia GitLab
- runbook [`docs/69-gitlab-sandbox-mirror.md`](C:/GitHub/umbral-agent-stack-codex/docs/69-gitlab-sandbox-mirror.md) con setup, gobernanza y recovery
- sección nueva en [`README.md`](C:/GitHub/umbral-agent-stack-codex/README.md)

Validación local:

- `git diff --check`
- inspección manual del workflow y del runbook

Nota honesta: la activación real del espejo sigue requiriendo pasos humanos fuera del repo:

1. crear proyecto vacío en GitLab
2. generar token con `write_repository`
3. cargar `GITLAB_MIRROR_PUSH_URL` en GitHub Secrets
