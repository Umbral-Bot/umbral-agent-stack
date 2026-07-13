---
id: "2026-07-13-001"
title: "Higiene repos H0 — prune de metadatos de worktrees huérfanos (solo metadatos, cero borrado de archivos)"
status: assigned
assigned_to: fable
created_by: fable
priority: medium
sprint: b0004
created_at: 2026-07-13T17:30:00Z
updated_at: 2026-07-13T17:30:00Z
---

## Objetivo

Ejecutar la Fase H0 del programa de higiene de repos (plan:
`docs/audits/repo-hygiene-plan-windows-vps__2026-07-13__b0004__src-fable.md`):
limpiar los 12 registros de worktree huérfanos en
`C:\GitHub\umbral-agent-stack\.git\worktrees\` cuyos directorios ya no existen
en la ruta registrada (fueron movidos a `C:\GitHub\_archive\uas\` en la
Fase A de G-WH-1, 2026-07-03, o eliminados).

**H0 NO toca archivos de trabajo.** Solo elimina metadatos git que apuntan a
rutas inexistentes. Los directorios archivados en `_archive\uas\` quedan
intactos como árboles de archivos inertes (protegidos por G-WH-2 hasta su
ventana de 30 días).

## Contexto

- Evidencia (2026-07-13): `git -C C:\GitHub\umbral-agent-stack worktree prune --dry-run -v`
  lista exactamente 12 entradas, todas con motivo
  `gitdir file points to non-existent location`:
  `umbral-agent-stack-cand001-v31`, `umbral-agent-stack-p2c-egress-repo`,
  `umbral-agent-stack-pit-closure`, `umbral-agent-stack-pit-p10`,
  `umbral-agent-stack-pit-p3`, `umbral-agent-stack-pit-p5`,
  `umbral-agent-stack-pit-p6`, `umbral-agent-stack-pit-readiness`,
  `umbralbim-didactic-fortnight`, `umbralbim-legendary-dollop`,
  `umbralbim-stunning-fiesta`, `_wt-editorial-pr-492`.
- Las 12 corresponden 1:1 con directorios archivados en Fase A
  (`C:\GitHub\_archive\uas\` + `WHY.md`). Sus ramas locales siguen existiendo
  en el canónico y NO se tocan en H0.
- Worktrees vivos que NO deben aparecer en el prune (verificar en dry-run):
  `.tmp-gd52-adr-scopes`, `umbral-agent-stack-b0004`,
  `umbral-agent-stack-b0004-oauth`, `reo`, `wah`, `weo`.

## Prerequisitos (verificados 2026-07-13 por Fable)

- [x] Dry-run ejecutado y las 12 entradas coinciden con el archivo de Fase A.
- [x] Ninguna de las 12 tiene directorio vivo en la ruta registrada.
- [x] Las ramas asociadas siguen en `refs/heads` del canónico (el prune no borra ramas).

## Comandos

```powershell
cd C:\GitHub\umbral-agent-stack
# 1. Confirmar que el dry-run sigue mostrando exactamente las 12 entradas esperadas
git worktree prune --dry-run -v
# 2. Ejecutar
git worktree prune -v
# 3. Verificar estado final: deben quedar solo los worktrees vivos
git worktree list

# 4. Mismo tratamiento en el clone codex (1 entrada prunable propia:
#    umbral-agent-stack-codex-pit-v2-contract, dir archivado en Fase A)
git -C C:\GitHub\umbral-agent-stack-codex worktree prune --dry-run -v
git -C C:\GitHub\umbral-agent-stack-codex worktree prune -v
# OJO: los ~16 worktrees de C:\Users\david\.codex\worktrees\* son hijos VIVOS
# del clone codex — el prune NO debe listarlos; si alguno aparece en el dry-run
# es porque su dir ya no existe (ok prunear). No tocar dirs existentes.
```

## Rollback

- El prune solo borra `.git\worktrees\<nombre>\` (metadatos). Si un worktree
  archivado se quisiera reconectar después: `git worktree add <ruta> <rama>`
  (la rama sigue viva) y copiar encima el contenido archivado si hiciera falta.
- No hay pérdida de commits, ramas, stashes ni archivos de trabajo posible en H0.

## Criterios de aceptación

- [ ] `git worktree prune -v` ejecutado sin errores.
- [ ] `git worktree list` muestra solo: canónico + `.tmp-gd52-adr-scopes` +
      `umbral-agent-stack-b0004` + `umbral-agent-stack-b0004-oauth` +
      `reo` + `wah` + `weo` (7 entradas).
- [ ] Cero archivos modificados/borrados fuera de `.git\worktrees\`.
- [ ] Log actualizado en esta tarea con la salida del comando.

## Log

### [fable] 2026-07-13 17:30
Tarea creada como parte del plan H0–H6. Dry-run verificado (12 entradas,
match 1:1 con Fase A). Pendiente de ejecución — H0 está clasificada
`destructive: false` y no requiere gate de David según la matriz del plan.
