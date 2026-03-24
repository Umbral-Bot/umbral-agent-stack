---
id: "2026-03-24-010"
title: "Fallback VM no invasivo + Gemini grounded como primario de discovery"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T05:25:00-03:00
updated_at: 2026-03-24T09:35:00-03:00
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

### [codex] 2026-03-24 09:35
Se cerraron los dos frentes dentro de lo que era posible sin intervenir la red local.

Archivos de codigo/documentacion:
- `worker/tasks/research.py`
- `worker/research_backends.py`
- `scripts/web_discovery.py`
- `scripts/research_web_smoke.py`
- `scripts/vm/start_vm_reverse_tunnel.ps1`
- `scripts/vm/ensure_vm_reverse_tunnel.ps1`
- `.env.example`
- `docs/35-rick-google-cloud-apis.md`
- `docs/36-rick-embudo-capabilities.md`
- `docs/62-operational-runbook.md`
- `docs/audits/vm-tailnet-operational-recovery-2026-03-15.md`
- `docs/audits/openclaw-deferreds-followup-2026-03-24.md`

Resultado VM fallback no invasivo:
- se mantuvo la opcion B como camino correcto: reverse tunnel host -> VPS, sin tocar Hyper-V ni crear nuevos routers virtuales
- los scripts de tunnel ya no dependen de la IP vieja `192.168.101.72`; ahora aceptan direccion por env (`OPENCLAW_VM_FALLBACK_ADDRESS`, `OPENCLAW_VM_TAILSCALE_IP`, `VM_TAILSCALE_IP`, `OPENCLAW_VM_INTERNAL_IP`) y prueban salud en `8088/8089` antes de arrancar
- validacion local del bloqueo real: `ensure_vm_reverse_tunnel.ps1` fallo limpiamente con `No VM candidate address responded on 8088/8089. Candidates tried: 100.109.16.40, 192.168.101.72`
- conclusion: el bloqueo ya no es de script ni de topologia propuesta; falta al menos una direccion host -> VM alcanzable

Resultado discovery Gemini primario:
- `research.web` quedo con Gemini grounded search como primario y Tavily como fallback secundario
- `scripts/web_discovery.py` quedo alineado al mismo orden
- se reforzo el prompt para exigir resultados obtenidos por Google Search en esa llamada, no conocimiento interno

Validacion:
- local: `python -m pytest tests/test_research_handler.py tests/test_web_discovery.py -q` -> `10 passed`
- VPS temporalmente en esta rama:
  - `bash scripts/vps/restart-worker.sh`
  - `PYTHONPATH=. python3 scripts/research_web_smoke.py --query "BIM automation trends 2026" --count 3` -> `engine=gemini_google_search`
  - `PYTHONPATH=. python3 scripts/web_discovery.py "BIM automation trends 2026" --count 3 --output json` -> `engine_used=gemini_google_search`, `result_count=3`

Estimacion Perplexity:
- `ops_log` VPS: `412` intentos terminales unicos de `research.web` en los ultimos `21` dias
- proyeccion mensual al ritmo actual: `~590` busquedas/mes
- envelope razonable para cotizar: `400-600` / mes
- si Gemini queda canonico y Perplexity se usa en reparto controlado ~mitad y mitad: `200-300` busquedas/mes por Perplexity
- nota operativa: la documentacion oficial actual de Perplexity indica API separada, pay-as-you-go, sin creditos API de cortesia incluidos en Pro
