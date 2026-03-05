# Task R17 — Script dry-run para borrado de ramas (Codex)

**Fecha:** 2026-03-06  
**Ronda:** 17  
**Agente:** Codex  
**Branch:** `codex/091-script-borrado-ramas` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Crear un script que lea la lista de ramas en `docs/guia-borrar-ramas-r16.md` (o `docs/ramas-recomendadas-borrar-r16.md`) y **genere** los comandos `git push origin --delete <rama>` para que el maintainer los revise y ejecute. **No ejecutar** borrados; solo imprimir los comandos (dry-run).

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b codex/091-script-borrado-ramas`.

2. **Script:** Crear `scripts/borrar_ramas_r16_dry_run.py` (o `.sh`/`.ps1` si prefieres): lee el doc de ramas a borrar, extrae los nombres de rama (por regex o por sección) y escribe por stdout o a un archivo `scripts/ramas_a_borrar_commands.txt` la lista de comandos, uno por línea, p. ej. `git push origin --delete feat/nombre-rama`. Si el formato del doc es tabla o listas, parsear de forma robusta. Incluir al inicio del output un comentario tipo "Revisar y ejecutar manualmente. Dry-run."

3. **README o doc:** Añadir en `docs/guia-borrar-ramas-r16.md` (o en el script como docstring) una línea que diga cómo ejecutar el script para generar los comandos. Ej.: `python scripts/borrar_ramas_r16_dry_run.py`.

4. **PR:** Abrir un único PR desde `codex/091-script-borrado-ramas` a main. Solo script + doc; no ejecutar ningún `git push --delete`.

---

## Criterios de éxito

- [ ] Script que genera la lista de comandos de borrado a partir del doc.
- [ ] Instrucción de uso en el doc o en el script.
- [ ] PR abierto; ningún borrado real de ramas.

---

## Restricciones

- No ejecutar `git push origin --delete` ni modificar ramas remotas. Solo generación de comandos.
