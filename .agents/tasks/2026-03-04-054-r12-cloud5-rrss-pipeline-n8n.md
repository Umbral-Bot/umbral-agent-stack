# Task R12 — Cloud 5: Pipeline RRSS — LinkedIn, X, Instagram, WhatsApp (n8n + human-in-the-loop)

**Fecha:** 2026-03-04  
**Ronda:** 12  
**Agente:** Cursor Agent Cloud 5  
**Branch:** `feat/rrss-pipeline-n8n`

---

## Contexto

David quiere automatizar la publicación en redes sociales (RRSS) usando **n8n instalado en la VPS**. El flujo comienza con la **captura diaria de contenido** de páginas y perfiles de LinkedIn que él indique, luego **evaluación, filtrado y transformación** según los intereses de su audiencia, **adaptación del tono** para su público objetivo, y **publicación** en múltiples canales. Debe existir **revisión humana antes de publicar** con opción de indicar ajustes. Todo alineado con su **marca personal**.

**Archivos de referencia:**
- `openclaw/workspace-templates/skills/n8n/SKILL.md` — conocimiento de n8n
- `openclaw/workspace-templates/skills/linkedin-content/SKILL.md` — contenido LinkedIn
- `openclaw/workspace-templates/skills/marca-personal-david/SKILL.md` — tono y estilo de marca personal
- `openclaw/workspace-templates/skills/make-com/SKILL.md` — patrones de webhook y automatización
- `worker/tasks/make_webhook.py` — webhook existente para integración Rick ↔ flujos externos
- `docs/30-linear-notion-architecture.md` — patrones de integración Dispatcher/Worker

---

## Alcance del task (primera etapa: investigación y diseño)

Este task se centra en **investigar, proponer y documentar** el mejor pipeline. No implementar n8n en producción todavía; primero diseñar el flujo completo y validar arquitectura.

---

## Fases del pipeline a diseñar

### Fase 1: Captura de contenido

| Requisito | Detalle |
|-----------|---------|
| Fuente | Páginas y perfiles de LinkedIn indicados por David |
| Frecuencia | Diaria (horario configurable) |
| Método | Investigar: RSS de LinkedIn (limitado), API oficial, scraping vía Apify/Browserless, o alternativas como LinkedIn Sales Navigator API, PhantomBuster, etc. |
| Output | Items con: título, cuerpo, enlace, autor, fecha, tipo (post, artículo, video) |

**Entregable:** Tabla comparativa de métodos de captura (LinkedIn no tiene API pública de lectura de posts de terceros) con pros/contras, coste y legalidad.

---

### Fase 2: Evaluación y filtrado

| Requisito | Detalle |
|-----------|---------|
| Criterios | Relevancia para la audiencia de David (BIM, AEC, consultoría, docente, transformación digital) |
| Filtrado | Eliminar contenido duplicado, irrelevante o de baja calidad |
| Scoring | Propuesta de criterios para "puntuación" de relevancia (keywords, temática, formato) |
| LLM | Usar `llm.generate` o integración n8n ↔ Worker para evaluación semántica |

**Entregable:** Diseño de nodos n8n para filtrado (Set, If, Code, HTTP Request al Worker) con criterios de scoring.

---

### Fase 3: Transformación y adaptación de tono

| Requisito | Detalle |
|-----------|---------|
| Tono | Alineado con marca personal de David |
| Referencia | `openclaw/workspace-templates/skills/marca-personal-david/SKILL.md` y `linkedin-david` |
| Adaptación | Por canal: LinkedIn vs X vs Instagram (extensiones, hashtags, formato) |
| Output | Versiones del mismo contenido adaptadas a cada red |

**Entregable:** Prompt / plantilla para LLM que adapte el contenido manteniendo voz de marca. Tabla de restricciones por plataforma (caracteres, formato, hashtags).

---

### Fase 4: Human-in-the-loop (revisión antes de publicar)

| Requisito | Detalle |
|-----------|---------|
| Revisión | David debe poder revisar el contenido antes de publicar |
| Ajustes | Indicar cambios de texto, tono o selección (qué publicar y qué no) |
| Interface | Proponer: Notion (lista de posts pendientes + comentarios), Telegram (Rick envía borrador + botones Aprobar/Editar), o cola en n8n con webhook manual |
| Flujo | Captura → Filtrado → Cola de "pendientes de revisión" → David revisa → Aprobación/Edición → Publicación |

**Entregable:** Diagrama de flujo del human-in-the-loop y recomendación de la mejor UX (Notion vs Telegram vs otra) con pros/contras.

---

### Fase 5: Publicación multi-canal

| Canal | Detalle | API / Método |
|-------|---------|--------------|
| **LinkedIn** | Cuenta personal o de negocio (David indicará después) | LinkedIn Marketing API, o posting vía PhantomBuster/Zapier |
| **Página web tipo newsletter** | Desarrollada con Lovable | API de Lovable, o CMS headless (Strapi, etc.) que use Lovable como front |
| **X (Twitter)** | Cuenta @David (o la que use) | X API v2 (post creation) |
| **Instagram** | Cuenta de David | Instagram Graph API (business) o Creator API; restricciones por tipo de cuenta |
| **WhatsApp** | Canal de difusión con link a la pieza más interesante | WhatsApp Business API, o enlace en un grupo/canal existente |

**Entregable:** Tabla de APIs necesarias, requisitos de cuenta (Business, Creator, etc.), límites de rate y viabilidad. Indicar qué requiere aprobación de Meta/X.

---

### Fase 6: WhatsApp — selección de "más interesantes"

| Requisito | Detalle |
|-----------|---------|
| Criterio | Las piezas más interesantes/relevantes se envían a un canal de WhatsApp |
| Formato | Mensaje con link a la pieza (newsletter web o post original) |
| Tono | Mismo estilo comunicativo, alineado con marca personal |

**Entregable:** Criterios de selección (top N por score, o umbral mínimo). Diseño del mensaje (plantilla con link, emoji, CTA).

---

## Entregables del agente

### 1. Documento de diseño: `docs/60-rrss-pipeline-n8n.md`

Contenido mínimo:
- Diagrama Mermaid del pipeline completo (captura → filtrado → transformación → cola de revisión → aprobación → publicación)
- Sección por fase con tablas, criterios y decisiones
- Requisitos de APIs, credenciales y cuentas
- Restricciones legales y de ToS (LinkedIn, X, Instagram, WhatsApp)
- Riesgos y mitigaciones

### 2. Propuesta de arquitectura n8n

- Lista de workflows n8n sugeridos (puede ser 1 macro-workflow o varios en cadena)
- Nodos clave por fase
- Integración con Worker (webhooks `make.post_webhook` o equivalente para Rick)
- Cómo se integra la cola de revisión (Notion, Telegram, o formulario)

### 3. Comparativa de métodos de captura LinkedIn

- Tabla con: método, coste, legalidad, fiabilidad, mantenimiento
- Recomendación final con justificación

### 4. Recomendación human-in-the-loop

- Opción A: Notion (lista de posts + propiedades Aprobar/Rechazar/Editar)
- Opción B: Telegram (Rick envía borrador, botones inline)
- Opción C: Otra (especificar)
- Pros/contras de cada una
- Recomendación final

### 5. Checklist de requisitos previos

- Qué cuentas debe tener David (LinkedIn personal/company, X Developer, Meta Developer, WhatsApp Business, etc.)
- Qué credenciales configurar en n8n
- Orden sugerido de implementación (fases incrementales)

---

## Preguntas para David (el agente debe listarlas en el doc)

El agente debe identificar y documentar preguntas que solo David puede responder, por ejemplo:
- ¿LinkedIn personal o página de empresa?
- ¿URL de la página web newsletter (Lovable)?
- ¿Tiene acceso a APIs de Meta/X/WhatsApp o hay que solicitar aprobación?
- ¿Horario preferido para la captura diaria?
- ¿Canal de WhatsApp existente o hay que crear uno?

---

## Convenciones del proyecto

- **No implementar** workflows n8n completos en este task — solo diseño y documentación
- **Investigar** límites de APIs, ToS y alternativas antes de proponer
- **Ser realista** con las limitaciones de LinkedIn (no hay API pública para leer posts de terceros)
- **Rama:** `feat/rrss-pipeline-n8n`
- **PR:** con el documento `docs/60-rrss-pipeline-n8n.md` como entregable principal

## Criterios de éxito

- [x] `docs/60-rrss-pipeline-n8n.md` — documento completo con todas las secciones
- [x] Diagrama Mermaid del pipeline de extremo a extremo
- [x] Tabla comparativa de métodos de captura LinkedIn
- [x] Recomendación de human-in-the-loop con pros/contras
- [x] Lista de APIs y requisitos de cuentas
- [x] Sección de preguntas para David
- [x] PR abierto a `main`

## Log

### [cursor-agent-cloud-5] 2026-03-04 18:00
- Investigación completa: APIs de LinkedIn (Marketing API, scraping), X API v2, Instagram Graph API, WhatsApp Business API, Lovable/Supabase, n8n human-in-the-loop patterns
- Creado `docs/60-rrss-pipeline-n8n.md` con 17 secciones:
  - Diagrama Mermaid del pipeline completo (6 fases)
  - Diagrama de arquitectura n8n (6 workflows encadenados)
  - Tabla comparativa de 8 métodos de captura LinkedIn con coste, legalidad, fiabilidad
  - Recomendación human-in-the-loop: 3 opciones con pros/contras (Notion + Telegram recomendada)
  - Tabla de 10 APIs con cuentas, credenciales, permisos y costes
  - Restricciones legales por plataforma
  - Riesgos y mitigaciones (8 riesgos identificados)
  - Checklist de requisitos previos
  - 20 preguntas para David organizadas por categoría
  - Comparativa n8n vs Make.com
  - Estimación de costes ($65-295/mes)
- PR abierto a main
