---
id: "2026-03-04-004"
title: "Hackathon: Integraciones — LiteLLM, métricas de cuotas, Notion verificación"
status: assigned
assigned_to: github-copilot
created_by: cursor
priority: high
sprint: S5
created_at: 2026-03-04T03:35:00-06:00
updated_at: 2026-03-04T03:35:00-06:00
---

## Objetivo
Activar las integraciones críticas del sistema: verificar que LiteLLM puede configurarse, implementar métricas de aprovechamiento de cuotas, y verificar la integración con Notion Control Room.

## Contexto
- Diagnóstico completo: `docs/40-hackathon-diagnostico-completo.md`
- LiteLLM está comentado en `infra/docker/docker-compose.hostinger.yml`
- Config existente: `infra/docker/litellm_config.yaml`
- QuotaTracker implementado en `dispatcher/quota_tracker.py`
- Las 5 suscripciones LLM no están siendo usadas por el sistema (0 requests)

## Tareas

### 1. Evaluar y documentar configuración LiteLLM (P0)
- Revisar `infra/docker/litellm_config.yaml` y determinar qué falta para activarlo
- Documentar las API keys necesarias por proveedor
- Si es posible, descomentar en docker-compose y preparar la configuración
- Si no es viable LiteLLM, proponer alternativa (usar API keys directamente en handlers)

### 2. Implementar dashboard de aprovechamiento de cuotas (P1)
Crear `scripts/quota_usage_report.py` que:
- Lee el estado de cuotas de Redis (`umbral:quota:*:used`, `umbral:quota:*:window_end`)
- Lee el ops_log para contar requests por modelo en las últimas 24h
- Genera un reporte de utilización: "Claude: 15/80 (19%), ChatGPT: 0/80 (0%)..."
- Identifica suscripciones infrautilizadas (>24h sin uso)
- Formato: stdout (para cron) y JSON (para integrar con dashboard)

### 3. Verificar Notion Control Room (P1)
- Si hay acceso a la VPS, verificar que `NOTION_CONTROL_ROOM_PAGE_ID` está configurado
- Probar `notion.poll_comments` vía Worker
- Probar `notion.add_comment` vía Worker
- Documentar resultado

### 4. Probar Linear end-to-end (P2)
- Si `LINEAR_API_KEY` está disponible, probar `linear.list_teams`
- Crear un issue de prueba y verificar que se puede actualizar estado

## Criterios de aceptación
- [ ] Documentación de configuración LiteLLM completa
- [ ] Script `quota_usage_report.py` funcional
- [ ] Al menos una integración externa (Notion o Linear) probada end-to-end
- [ ] Reporte de estado de integraciones documentado

## Log
