# Task R16 — Capitalizar ramas (Codex)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Codex  
**Branch:** `codex/081-capitalizar-ramas` ← **trabaja solo en esta rama** (crear desde `main` actualizado).

---

## Contexto

Tras muchas ramas y PRs cerrados, parte del trabajo valioso (docs, skills, board) sigue solo en ramas y no en `main`. Objetivo: **capitalizar** — identificar qué hay en cada rama, unificar la información y recuperar lo valioso sin romper main.

---

## Tareas

1. **Listar ramas con commits que no están en main:**  
   `git branch -r` y para cada rama remota (excluyendo `origin/main`), comprobar si tiene commits no mergeados en main (`git log main..origin/nombre-rama --oneline`). Anotar rama y número de commits (o "0" si ya está en main).

2. **Inventario:** Crear (o actualizar) un único documento, p. ej. `docs/informe-ramas-pendientes.md`, con una tabla: **rama remota** | **PR asociado (si aplica)** | **resumen en 1 línea** | **recomendación** (merge / cherry-pick doc / skip). Priorizar ramas que tengan contenido único: browser automation (`feat/browser-automation-vm-research` o similar), Power BI (`cursor/power-bi-*` o `feat/*power*`), Bitácora/board (`cursor/bit-cora-*`, `cursor/board-*`), CONTRIBUTING/README.

3. **Recuperar 1–2 cosas seguras:** Elegir una o dos ramas que sean **solo docs** (p. ej. Power BI, browser automation plan) y que no toquen código de aplicación. En tu rama `codex/081-capitalizar-ramas`, hacer cherry-pick de los commits de documentación o copiar los archivos nuevos a la rama y hacer un commit. Objetivo: un solo PR desde `codex/081-capitalizar-ramas` que añada al repo esos docs, sin duplicar lo que ya está en main.

4. **No refactorizar:** No cambiar dependencias, no tocar tests ni código de worker/dispatcher. Solo inventario + recuperación de documentos.

---

## Criterios de éxito

- [ ] Documento `docs/informe-ramas-pendientes.md` (o similar) con tabla de ramas y recomendaciones.
- [ ] Rama `codex/081-capitalizar-ramas` con al menos un commit que aporte docs recuperados (si hay algo seguro que recuperar).
- [ ] PR abierto desde `codex/081-capitalizar-ramas` hacia `main` con descripción breve.

---

## Restricciones

- Trabajar **solo** en la rama `codex/081-capitalizar-ramas` (crear desde `main`, no desde otra feature).
- No mergear otras ramas a main desde esta tarea; solo documentar y, si aplica, subir un PR con docs recuperados.
