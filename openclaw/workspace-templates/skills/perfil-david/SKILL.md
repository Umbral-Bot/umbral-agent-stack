---
name: perfil-david
description: >-
  Contexto profesional de David Moreira Mercado. Proyectos activos, clientes,
  servicios, pricing, prioridades estrategicas, stack tecnologico, red profesional.
  Use when "proyecto", "cliente", "propuesta", "pricing", "perfil", "conviene",
  "prioridad", "pipeline", "servicio", "portafolio", "caso de exito", "metrica",
  "certificacion", "experiencia", "consultor", "butic", "comgrap", "wsp",
  "dessau", "netzun", "umbral bim", "fondef", "borago", "oxxo", "delporte",
  "duma", "bim forum", "utfsm", "n8n embajador", "marca personal",
  "modelo de negocio", "tarifario", "cotizacion", "cotizar".
metadata:
  openclaw:
    emoji: "\U0001F9ED"
    notion_page_id: "1dbd687490a94ba29b19f0daec70c68e"
    cache_ttl_hours: 24
    requires:
      env: []
---

# Perfil David — Contexto Operativo para Rick

Este skill permite a Rick acceder al contexto profesional de David bajo demanda.

## Fuente de verdad

**Notion Page ID:** `1dbd687490a94ba29b19f0daec70c68e`
**Titulo:** "Perfil David Moreira -- Arquitecto, Consultor BIM, Docente, Educador y Comunicador"
**Ubicacion:** Dentro de OpenClaw en Notion
**Mantenido por:** David + Enlace (sync desde "Mi Perfil")

## Cuando activar este skill

Rick debe cargar este contexto cuando el mensaje del usuario:
- Mencione proyectos, clientes o servicios especificos
- Pida evaluar oportunidades, priorizar o cotizar
- Requiera datos de perfil profesional (bio, credenciales, metricas)
- Necesite contexto para redactar propuestas, emails comerciales o contenido de marca
- Mencione nombres de organizaciones conocidas (COMGRAP, WSP, Butic, etc.)

## Que contiene la pagina

1. Resumen ejecutivo
2. Analisis como consultor (metodologia, frameworks, casos de exito)
3. Analisis como docente (programas activos, metodologia pedagogica)
4. Analisis como comunicador (ejes, tono, posicionamiento)
5. Stack tecnologico completo
6. Conclusion y perspectiva de valor
7. Certificaciones y credenciales
8. Trayectoria profesional
9. Proyectos activos y productos propios (estados actualizados)
10. Infraestructura y suscripciones
11. Red profesional y organizaciones

## Como usar

Rick llama `notion.get_page_content` con el page_id e inyecta el resultado
como contexto adicional en el system prompt antes de generar la respuesta.
No inyectar siempre -- solo cuando el skill match lo requiera.
