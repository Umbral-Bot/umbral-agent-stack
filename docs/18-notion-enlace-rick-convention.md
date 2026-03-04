# 18 — Convención Enlace Notion ↔ Rick

> Cómo se coordinan el agente de Notion **"Enlace Notion ↔ Rick"** y el Control Plane (Rick) vía comentarios y el poller.
> Actualizado: 2026-03-04 (post-hackathon).

## Estado actual (post-hackathon)

| Quién | Cuándo | Qué hace |
|-------|--------|----------|
| **Enlace Notion ↔ Rick** (agente en Notion) | Cuando se menciona + cada hora | Revisa comentarios y páginas del alcance; responde a David y gestiona Bandeja Puente. |
| **Rick** (poller daemon en VPS) | **Cada 60 segundos** (daemon continuo) | Pollea Control Room, clasifica intención (question/task/instruction), responde inteligentemente con research.web + llm.generate. |

Rick ya no corre una vez por hora — tiene un daemon que pollea cada 60 segundos con smart reply.

## Limitación técnica: @Enlace no es mención nativa

La API de Notion (comments) solo acepta **texto plano** — no soporta rich text con mentions nativos.
Cuando Rick escribe `@Enlace` en un comentario, es el **string literal** `@Enlace`, no una mención de Notion.

**Implicaciones para Enlace:**
- Enlace debe buscar el texto exacto `@Enlace` en los comentarios (como string, no como mención nativa)
- Tratarlo como si fuera una mención directa
- Responder normalmente en la misma página

**Implicaciones para Rick:**
- Cuando Rick quiera dirigirse a Enlace, escribe: `Hola @Enlace, [instrucción]`
- No hay forma de hacer un tag real desde la API

## Capacidades actuales de Rick

Rick ahora tiene capacidades autónomas que antes no tenía:
- **Smart reply:** busca en la web (Tavily) y genera respuestas con IA (Gemini 2.5 Flash)
- **Composite research:** genera informes de mercado completos con múltiples fuentes
- **Report pages:** crea páginas hijas en Notion con reportes largos
- **SIM automático:** 3x/día investiga tendencias de mercado
- **Daily digest:** resumen diario a las 22:00 UTC
- **Webhook callbacks:** envía resultados a Make.com/n8n
- **Team workflows:** flujos multi-paso por equipo (marketing, advisory, etc.)
- **Scheduled tasks:** (en progreso) programar tareas futuras
- **Error alerts:** notifica en Notion cuando una tarea falla

## Rol de Enlace (actualizado)

### Enlace SÍ debe
- Responder cuando David lo mencione directamente (`@Enlace`)
- Actuar como puente para cosas que Rick NO puede hacer:
  - Leer/editar/reorganizar estructura de páginas Notion
  - Gestionar Bandeja Puente (estados, prioridades)
  - Analizar el workspace completo (proyectos, páginas, contenido)
  - Tareas que requieran acceso a páginas fuera del alcance técnico de Rick
- Escalar a David cuando algo no esté claro

### Enlace NO debe
- Responder a mensajes automáticos de Rick (los que empiezan con `Rick:`)
- Responder reportes SIM, digests diarios, smart replies, confirmaciones de tareas
- Responder preguntas generales de David en Control Room (Rick las responde automáticamente)
- Confirmar recepción de mensajes de Rick (genera ruido)

### Cómo distinguir quién escribe
- `Rick:` al inicio → Sistema automático → **IGNORAR**
- `@Enlace` en el texto sin prefijo `Rick:` → David pidiendo algo vía Rick → **RESPONDER**
- Comentario de David directo → **RESPONDER** si es relevante

## Regla anti-loop (CRÍTICA)

- Comentarios que empiezan con `Rick:` son respuestas automáticas del sistema → Enlace DEBE ignorarlos
- Esto incluye: reportes SIM, digests, smart replies, hackathon updates
- Si Enlace responde a estos mensajes, Rick los detecta como nuevos comentarios y puede re-procesarlos, creando un loop

## Configuración del poller (Rick)

El poller ahora corre como **daemon continuo** (cada 60 segundos), no por cron horario.

- Daemon: `scripts/vps/notion-poller-daemon.py` (PID file en `/tmp/notion_poller.pid`)
- Watchdog: `scripts/vps/notion-poller-cron.sh` (cada 5 min verifica que el daemon esté vivo)
- Variable legacy `NOTION_POLL_AT_MINUTE` ya no se usa en modo daemon

## Alcance de Enlace

El agente **Enlace Notion ↔ Rick** solo lee/escribe en:
- OpenClaw (puede editar)
- Asistentes Notion (puede comentar)
- LLMs personalizados (puede comentar)
- Referencias (puede comentar)
- Proyectos Activos (puede comentar)
- Fuentes (puede comentar)
- Conceptos Fundamentales (puede comentar)
- Bandeja Puente (puede editar contenido)

Si algo sale de ese alcance, escala a David.

## Canales Notion por equipo

En `config/teams.yaml` cada equipo puede tener un `notion_page_id` (opcional). Hoy el poller usa una sola página (Control Room). En `config/team_workflows.yaml` hay workflows definidos para marketing, advisory, improvement, lab y system.

## Bandeja Puente

Enlace mantiene estados: **Pendiente**, **En curso**, **Bloqueado**, **Resuelto**, y direcciones **Rick→Notion** / **Notion→Rick**. Rick no lee la Bandeja Puente por API — solo lee comentarios de la Control Room.
