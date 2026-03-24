---
id: "2026-03-24-010"
title: "Fallback VM no invasivo + Gemini grounded como primario de discovery"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T05:25:00-03:00
updated_at: 2026-03-24T05:25:00-03:00
---

## Objetivo
Resolver lo que se pueda sin intervencion humana en dos frentes:

1. opcion B para el execution plane de la VM sin tocar Hyper-V ni crear cambios de red invasivos
2. dejar Gemini grounded search como camino primario real para `research.web` y `web_discovery.py`, con pruebas usando las credenciales Google ya presentes si alcanzan

## Contexto
- El tailnet directo VPS -> VM sigue degradado post reboot.
- Ya existen scripts de reverse tunnel no invasivo en `scripts/vm/`.
- `research.web` aun deja Tavily como primario y Gemini como fallback, pero la decision actual es priorizar Gemini search real sobre conocimiento interno.

## Criterios de aceptacion
- [ ] Queda implementado o mejorado el fallback no invasivo hacia la VM, o documentado con precision el bloqueo tecnico real si falta acceso local.
- [ ] `research.web` y `scripts/web_discovery.py` quedan con Gemini grounded search como camino primario.
- [ ] Queda validado en runtime real con las credenciales Google disponibles, o documentado el faltante exacto si faltara alguna.
- [ ] Queda estimacion razonable del volumen mensual de busquedas para cotizar Perplexity como backend secundario.

## Log
### [codex] 2026-03-24 05:25
Tarea creada. Se empieza por inspeccion del fallback VM actual y luego se invierte discovery web a Gemini primario con smoke real en VPS.
