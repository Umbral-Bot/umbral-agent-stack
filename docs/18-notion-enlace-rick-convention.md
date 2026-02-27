# 18 — Convención Enlace Notion ↔ Rick

> Cómo se coordinan el agente de Notion **"Enlace Notion ↔ Rick"** y el Control Plane (Rick) vía comentarios y el poller.

## Horarios

| Quién | Cuándo | Qué hace |
|-------|--------|----------|
| **Enlace Notion ↔ Rick** (agente en Notion) | Cada hora en punto (00:00, 01:00, 02:00, …) | Se activa; revisa comentarios de Rick y páginas del alcance; responde y actualiza Bandeja Puente. |
| **Rick** (poller en VPS) | A las **XX:10** de cada hora | Llama al Worker para hacer `notion.poll_comments` en la página Control Room; encola tareas por cada comentario nuevo (p. ej. responder "Rick: Recibido."). |

Rick revisa **10 minutos después** de Enlace para leer mensajes que Enlace (o David) dejaron para él.

## Configuración del poller

Por defecto el poller corre **una vez por hora a las XX:10** (minuto 10). No hace falta definir nada más.

- Para cambiar el minuto: `NOTION_POLL_AT_MINUTE=15` → Rick a las XX:15.
- Para modo continuo (poll cada N segundos): `NOTION_POLL_INTERVAL_SEC=300` → cada 5 min (se ignora `NOTION_POLL_AT_MINUTE`).

## Alcance de Enlace (resumen)

El agente **Enlace Notion ↔ Rick** solo lee/escribe en:

- OpenClaw, Asistentes Notion, LLMs personalizados, Referencias, Proyectos Activos, Bandeja Puente, Fuentes, Conceptos Fundamentales, etc.  
- Si algo sale de ese alcance, escala a David.

## Reglas de comunicación

- **Rick → Enlace:** Rick (o el sistema) comenta en las páginas del alcance; Enlace reacciona cuando corre (cada hora en punto). Para que Enlace responda, conviene que Rick use el formato que Enlace espera (p. ej. "Hola @Enlace," si aplica).
- **Enlace → Rick:** Enlace deja comentarios o ítems en Bandeja Puente; Rick (el poller) revisa a las XX:10 y procesa comentarios nuevos en la página que use el poller (p. ej. Control Room). En Notion, cuando se mencione a Rick, usar **@Rick** (usuario de Notion).
- Comentarios que empiezan por **"Rick:"** los ignora el poller (son respuestas automáticas nuestras) para no reaccionar en bucle.

## Bandeja Puente

Enlace mantiene estados: **Pendiente**, **En curso**, **Bloqueado**, **Resuelto**, y direcciones **Rick→Notion** / **Notion→Rick**. Rick (el stack) no lee hoy la Bandeja Puente por API; solo lee comentarios de la página configurada en el Worker (p. ej. Control Room). Si más adelante Rick debe reaccionar a ítems de Bandeja Puente, se puede añadir otro poll o integración.

## Referencia rápida del agente Enlace

- **Trigger principal:** cada vez que **@Rick** comenta en una página del alcance.
- **Formato que Enlace espera de Rick:** "Hola @Enlace," al inicio cuando Rick se dirija a Enlace.
- **Respuestas:** lenguaje natural, sin headers tipo reporte ni metadatos clave-valor.
- **Escalado:** si falta contexto o hay conflicto, Enlace pregunta a David.
