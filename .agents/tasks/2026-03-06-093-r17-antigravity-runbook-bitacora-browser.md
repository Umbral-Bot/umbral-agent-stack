# Task R17 — Actualizar runbook con Bitácora y browser automation (Antigravity)

**Fecha:** 2026-03-06  
**Ronda:** 17  
**Agente:** Antigravity  
**Branch:** `antigravity/093-runbook-bitacora-browser` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Actualizar `docs/62-operational-runbook.md` (o el runbook operacional que exista) con referencias a los scripts de Bitácora y al plan de browser automation, para que ops sepa dónde está cada cosa.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b antigravity/093-runbook-bitacora-browser`.

2. **Runbook:** En `docs/62-operational-runbook.md` añadir (o ampliar) una sección tipo "Scripts y docs recuperados (R16)":
   - **Bitácora:** scripts `enrich_bitacora_pages.py`, `add_resumen_amigable.py`; env vars `NOTION_API_KEY`, `NOTION_BITACORA_DB_ID`; doc de uso `docs/bitacora-scripts.md`.
   - **Browser automation:** plan y skill en `docs/64-browser-automation-vm-plan.md` y `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md`. Una línea cada uno.
   - Si el runbook tiene checklist o troubleshooting, añadir una línea: "Ramas obsoletas: ver docs/guia-borrar-ramas-r16.md".

3. **No reescribir:** Solo añadir el bloque nuevo; no cambiar el resto del runbook salvo para mantener coherencia (títulos, formato).

4. **PR:** Abrir un único PR desde `antigravity/093-runbook-bitacora-browser` a main. Solo docs.

---

## Criterios de éxito

- [ ] Runbook actualizado con sección Bitácora + browser automation + guía ramas.
- [ ] PR abierto. Sin cambios a código.

---

## Restricciones

- Solo edición de `docs/62-operational-runbook.md` (o el runbook vigente). No tocar worker, dispatcher ni CI.
