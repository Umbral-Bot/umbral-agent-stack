# ADR-006: Capa Visual Editorial — Nano Banana Pro, Freepik y Diagramas

## Estado

Proposed — 2026-04-21 (actualizado con hallazgos UA-13)

## Contexto

El sistema editorial de Rick necesita generar assets visuales para cada pieza publicada: portadas, imágenes con texto, iconografía, diagramas, screenshots. La investigación UA-11 evaluó Nano Banana Pro (Gemini 3 Pro Image de Google) y Freepik como opciones, incluyendo pricing, capacidades, licencias y riesgos.

UA-13 evaluó la factibilidad de automatizar herramientas visuales con cuentas de usuario, navegador y RPA. El hallazgo clave: **API-first es obligatorio**. Las AUP de Freepik, Midjourney, Adobe Firefly y Gemini app prohíben automatización con bots/external tools/RPA sobre sus interfaces de usuario, incluso con cuenta propia.

La decisión es: ¿Rick llama a Google directo, pasa por Freepik, o combina ambos?

## Decisión

**Arquitectura híbrida de dos capas + herramientas deterministas. API-first obligatorio.**

### Principio rector: API-first (UA-13)

- **Toda interacción programática con herramientas visuales de terceros debe usar APIs oficiales o MCPs autorizados**.
- **Prohibido**: automatizar UI de Freepik, Midjourney, Adobe Firefly, Gemini app o cualquier herramienta visual con Playwright, PAD, OpenClaw browser, Comet, RPA o scripts de scraping. Las AUP de estos servicios prohíben explícitamente bots, external tools y automatización sobre la interfaz web.
- **RPA/browser automation solo permitido**: para apps propias (n8n, OpenClaw Control UI, Notion desktop), flujos internos del VPS, o asistencia manual donde los ToS lo permitan. Nunca para bypass de login, captcha, paywall o anti-bot.
- **Freepik API y Freepik MCP oficial** son las vías autorizadas para acceder a Freepik programáticamente. Make/n8n con API key de Freepik también es válido.

### Capa 1 — AI primaria: Vertex AI con `gemini-3-pro-image-preview`

- Generación AI para portadas, imágenes con texto legible, assets de blog y X.
- Acceso directo vía Vertex AI (no Gemini API consumer) por mejor SLA, data-residency configurable, y billing paid-by-default (sin training sobre prompts).
- Hasta 14 reference images para consistencia de estilo (6 objetos + 5 personajes).
- Batch API con 50% descuento para volumen.
- Pricing: $0.134/imagen 1K-2K standard, $0.067 batch.
- **Restricción preview (UA-13)**: `gemini-3-pro-image-preview` y modelos en estado preview no deben ser el proveedor primario de producción hasta alcanzar GA e IP indemnification. Vertex AI con billing suaviza esto pero mantiene SLA reducido. Usar con awareness de que puede haber breaking changes.

### Capa 2 — Fallback y stock: Freepik API + stock

- Vectores SVG editables, iconografía, Flaticon.
- Fallback AI si Vertex no disponible: endpoint `nano-banana-pro` (mismo modelo, cap 3 referencias).
- Modelos complementarios: Ideogram 3 para tipografía fuerte, Mystic para fotorealismo con LoRAs.
- Pay-per-use independiente de suscripción Freepik.
- **Acceso autorizado**: solo vía Freepik API, Freepik MCP oficial o Make/n8n con API key. No automatizar Freepik UI/web.

### Capa 3 — Herramientas deterministas (nunca AI)

- **Diagramas**: Mermaid, Excalidraw, tldraw, Graphviz, draw.io.
- **Screenshots**: capturas reales anotadas con Excalidraw o CleanShot.
- **Charts de datos**: matplotlib, Power BI export.
- **Carruseles**: templates Figma con Figma API.

### Regla anti-AI-slop

- Sin personas foto-real generadas por AI.
- Si existe dato verificable → gana el diagrama o screenshot.
- AI solo para atmósfera, concepto o titular.
- SynthID siempre activo (no removible). Nunca declarar como foto real.

### HITL para assets visuales (UA-13)

- **Publicación final** de cualquier asset visual requiere HITL (gate `autorizar_publicacion`).
- **HITL obligatorio adicional** para:
  - Assets con personas reconocibles o marcas de terceros.
  - Cambio de proveedor visual (nuevo modelo, nuevo servicio).
  - Assets generados por modelos en estado preview.

## Alternativas consideradas

### 1. Solo Freepik (API + stock + UI)

Rechazada como primaria. Freepik wrapper de NBP tiene cap de 3 reference images (vs 14 en Google directo). No expone batch API, thinking config ni grounding. Pricing por imagen mayor que Google directo. Valor real de Freepik está en stock/vector/iconografía, no en generación AI como canal principal.

### 2. Solo Gemini API consumer (no Vertex)

Rechazada. Gemini API consumer-tier no incluye indemnización, tiene SLA reducido para modelos preview, y en tier unpaid/free Google usa prompts para entrenar. Vertex AI resuelve todo esto con billing activo.

### 3. Midjourney

Rechazada. Sin API pública estable. Estética "hypervisual" incompatible con línea editorial sobria. No automatizable desde Rick. **AUP prohíbe automatización con bots/external tools (UA-13).**

### 4. DALL-E / GPT Image (OpenAI)

Rechazada como base. Calidad inferior a NBP para caso editorial técnico. Mayor costo por imagen (créditos altos en Freepik). Sin multi-reference comparable.

### 5. Solo herramientas deterministas (cero AI)

Considerada viable pero limitante. Diagramas y screenshots cubren ~60% de los casos, pero portadas y hero images requieren producción visual que AI resuelve de forma más eficiente que stock genérico o diseño manual.

### 6. Fal.ai / Replicate como proxy de Gemini

Rechazada. Re-sellers con data residency incierta y ToS que pueden no cubrir uso comercial del modelo subyacente.

### 7. Automatizar Freepik/Midjourney/Adobe UI con RPA (UA-13)

**Rechazada**. Las AUP de Freepik, Midjourney y Adobe Firefly prohíben explícitamente el uso de bots, external tools y automated access sobre la interfaz web. Esto aplica incluso con cuenta propia pagada. Freepik API y MCP oficial son las vías autorizadas.

## Consecuencias

### Positivas

- Acceso al mejor modelo actual para texto en imagen (diferencial de Gemini 3 Pro Image).
- Consistencia visual via reference pack versionado.
- Capa de abstracción permite swap de provider sin tocar callers.
- Stock Freepik cubre iconografía y SVG que AI no resuelve bien.
- Herramientas deterministas para diagramas = cero alucinación, trazabilidad total.
- API-first elimina riesgo de ban/suspensión por UI automation.

### Negativas

- **Riesgo preview**: `gemini-3-pro-image-preview` está en estado preview. ToS de Gemini API prohíbe uso en producción. Vertex AI suaviza esto pero mantiene SLA reducido.
- Requiere cuenta Google Cloud con billing activo y configuración de Vertex AI.
- Dos proveedores (Google + Freepik) = dos cuentas, dos facturaciones, dos monitoreos.
- SynthID invisible en todas las imágenes — trazabilidad obligatoria.

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Gemini 3 Pro Image sale de preview con breaking changes | Media | Alto | Wrapper abstraction en Rick; version-lock del model ID; fallback a Freepik |
| Preview → GA cambia pricing significativamente | Baja-Media | Medio | Batch API reduce 50%; Freepik como alternativa |
| AI slop reputacional (manos raras, rostros uncanny) | Media | Alto | Regla fuerte: sin personas foto-real AI; priorizar diagramas y abstracciones |
| Rate limit Vertex (Tier 1: 150-300 RPM) | Baja | Bajo | Volumen editorial bajo (~40 assets/mes); Tier 1 suficiente |
| Freepik API cambia pricing o depreca endpoint NBP | Baja | Bajo | Freepik es agregador; alternativas disponibles (Fal.ai, Replicate) |
| Licencia AI excluida de protección legal Freepik | Baja | Medio | Nunca generar con prompts que incluyan nombres, marcas o personajes; guardar log de prompts |
| Suspensión de cuenta por UI automation (UA-13) | **Eliminado** | — | API-first elimina este riesgo; UI automation prohibida |

## Fuentes Perplexity

- **UA-11**: `Perplexity/Umbral Agent Stack/11_ Evaluación Visual Nano Banana vs Freepik/capa-visual-rick-v1.md` — comparativa completa, pricing, licencias, riesgos, arquitectura visual
- **UA-13**: `Perplexity/Umbral Agent Stack/13_  Automatización Visual con Cuentas de Usuario/UA-13_automatizacion_visual.md` — API-first obligatorio, prohibición UI automation, Freepik API/MCP como vía autorizada, HITL para assets con personas/marcas/cambio de proveedor
- **UA-08**: `Perplexity/Umbral Agent Stack/08_ Comparacion Visual Nano Banana Pro y Freepik/capa_visual_editorial.md` — versión previa (histórica, sustituida por UA-11)
- **UA-04**: `Perplexity/Umbral Agent Stack/04_ Direccion Visual para Contenido Tecnico/` — dirección visual general
