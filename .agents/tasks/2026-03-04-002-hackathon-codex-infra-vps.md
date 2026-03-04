---
id: "2026-03-04-002"
title: "Hackathon: Verificar y activar infraestructura VPS (Redis, Dispatcher, Dashboard cron)"
status: done
assigned_to: cursor
created_by: cursor
priority: high
sprint: S5
created_at: 2026-03-04T03:35:00-06:00
updated_at: 2026-03-04T06:30:00-06:00
closed_by: cursor
---

## Objetivo
Verificar y activar la infraestructura en la VPS para que el sistema opere 24/7. El diagnóstico del hackathon reveló que el sistema está "operativamente inactivo" a pesar de tener código funcional.

## Contexto
- Diagnóstico completo: `docs/40-hackathon-diagnostico-completo.md`
- La VPS debería tener: Redis, Worker, Dispatcher, cron del dashboard
- Variables de entorno en `~/.config/openclaw/env`
- Script de verificación: `scripts/verify_stack_vps.py`
- n8n ya fue confirmado como instalado (2026-03-03)

## Tareas
1. **Conectar a la VPS** (SSH o Tailscale) y verificar estado actual de servicios
2. **Redis**: confirmar que está corriendo (`redis-cli ping`). Si no, instalarlo y activarlo
3. **Variables de entorno**: verificar que `~/.config/openclaw/env` tiene todas las necesarias:
   - `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL`
   - `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_DASHBOARD_PAGE_ID`
   - `LINEAR_API_KEY` (opcional pero deseable)
4. **Worker VPS**: verificar que está corriendo como servicio (`systemctl --user status openclaw-worker-vps`)
5. **Dispatcher**: verificar servicio (`systemctl --user status openclaw-dispatcher`). Si no está activo, activarlo
6. **Dashboard cron**: verificar con `crontab -l` si el cron está instalado. Si no, instalar **sin sobrescribir** (usar `crontab -l | grep -v dashboard; echo "*/15 * * * * ..."`)
7. **Ejecutar `scripts/verify_stack_vps.py`** y reportar resultado completo
8. **Probar flujo end-to-end**: encolar un ping via Redis y verificar que el Dispatcher lo procesa

## Criterios de aceptación
- [ ] Redis confirmado activo en VPS
- [ ] Variables de entorno configuradas
- [ ] Worker VPS respondiendo a /health
- [ ] Dispatcher procesando tareas de la cola
- [ ] Dashboard cron instalado (cada 15 min)
- [ ] verify_stack_vps.py ejecutado con resultado OK
- [ ] Al menos 1 tarea procesada end-to-end (enqueue → dequeue → execute)

## Log
- **2026-03-04 06:30 UTC** — Tarea completada por **cursor** durante el hackathon (originalmente asignada a codex, pero cursor la ejecutó directamente vía SSH a la VPS). Resultados: Redis OK, env vars OK, Worker OK (24 handlers), Dispatcher procesando tareas, dashboard cron arreglado, verify_stack_vps.py OK, flujo e2e verificado con 14+ tareas procesadas. VM con red caída (APIPA) requiere intervención manual.
