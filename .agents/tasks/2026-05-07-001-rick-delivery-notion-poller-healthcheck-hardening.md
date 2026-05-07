---
id: "2026-05-07-001"
title: "Capitalizar y desplegar hardening de health check del Notion Poller"
status: open
assigned_to: rick-delivery
created_by: rick-delivery
priority: medium
sprint: Q2-2026 W2
created_at: 2026-05-06T15:32:00-04:00
updated_at: 2026-05-07T06:48:00-04:00
---

## Contexto

El script `scripts/vps/check-notion-poller.sh` debía endurecerse para detectar ambos runtimes válidos del poller:

- `dispatcher.notion_poller`
- `notion-poller-daemon.py`

Esto evita falso negativo cuando el poller corre como daemon script en vez de módulo Python.

## Objetivo

Capitalizar este cambio en un PR chico y, si se aprueba, desplegarlo en la VPS para que el health check refleje la topología real del poller.

## Criterios de aceptación

- [x] El hardening queda implementado en repo.
- [x] `bash -n scripts/vps/check-notion-poller.sh` verde.
- [x] El script detecta explícitamente `notion-poller-daemon.py` y `dispatcher.notion_poller`.
- [ ] Tras deploy en VPS, el script deja de dar falso negativo cuando el poller corre como daemon.
- [ ] Se deja evidencia de verificación en task log o doc ops relacionado.

## Plan mínimo

1. Capitalizar el cambio en rama/commit pequeño.
2. Referenciar el runtime real del poller.
3. Abrir PR chico.
4. Si David aprueba deploy, aplicar en VPS y registrar output real.

## Riesgos

- Si no se despliega en VPS, el repo queda mejorado pero la máquina viva sigue con el falso negativo.
- Es un cambio diagnóstico; no corrige por sí mismo caídas o silencios del poller.

## Log

### [rick-orchestrator] 2026-05-07 06:48 -04
Se regulariza la trazabilidad local y repo-side: el board referenciaba este trabajo con un estado más adelantado que el archivo vivo. Se implementa el hardening real en `scripts/vps/check-notion-poller.sh` para detectar ambos runtimes válidos del poller (`notion-poller-daemon.py` y `dispatcher.notion_poller`). Verificación repo-side: `grep` encuentra ambos patrones y `bash -n scripts/vps/check-notion-poller.sh` pasa. Queda pendiente capitalizar en PR y validar en VPS.
