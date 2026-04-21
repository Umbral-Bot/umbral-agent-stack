# ADR-006: Capa Visual Editorial — Nano Banana Pro, Freepik y Diagramas

## Estado

Proposed — 2026-04-21

## Contexto

El sistema editorial de Rick necesita generar assets visuales para cada pieza publicada: portadas, imágenes con texto, iconografía, diagramas, screenshots. La investigación UA-11 evaluó Nano Banana Pro (Gemini 3 Pro Image de Google) y Freepik como opciones, incluyendo pricing, capacidades, licencias y riesgos.

La decisión es: ¿Rick llama a Google directo, pasa por Freepik, o combina ambos?

## Decisión

**Arquitectura híbrida de dos capas + herramientas deterministas.**

### Capa 1 — AI primaria: Vertex AI con `gemini-3-pro-image-preview`

- Generación AI para portadas, imágenes con texto legible, assets de blog y X.
- Acceso directo vía Vertex AI (no Gemini API consumer) por mejor SLA, data-residency configurable, y billing paid-by-default (sin training sobre prompts).
- Hasta 14 reference images para consistencia de estilo (6 objetos + 5 personajes).
- Batch API con 50% descuento para volumen.
- Pricing: $0.134/imagen 1K-2K standard, $0.067 batch.

### Capa 2 — Fallback y stock: Freepik API + stock

- Vectores SVG editables, iconografía, Flaticon.
- Fallback AI si Vertex no disponible: endpoint `nano-banana-pro` (mismo modelo, cap 3 referencias).
- Modelos complementarios: Ideogram 3 para tipografía fuerte, Mystic para fotorealismo con LoRAs.
- Pay-per-use independiente de suscripción Freepik.

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

## Alternativas consideradas

### 1. Solo Freepik (API + stock + UI)

Rechazada como primaria. Freepik wrapper de NBP tiene cap de 3 reference images (vs 14 en Google directo). No expone batch API, thinking config ni grounding. Pricing por imagen mayor que Google directo. Valor real de Freepik está en stock/vector/iconografía, no en generación AI como canal principal.

### 2. Solo Gemini API consumer (no Vertex)

Rechazada. Gemini API consumer-tier no incluye indemnización, tiene SLA reducido para modelos preview, y en tier unpaid/free Google usa prompts para entrenar. Vertex AI resuelve todo esto con billing activo.

### 3. Midjourney

Rechazada. Sin API pública estable. Estética "hypervisual" incompatible con línea editorial sobria. No automatizable desde Rick.

### 4. DALL-E / GPT Image (OpenAI)

Rechazada como base. Calidad inferior a NBP para caso editorial técnico. Mayor costo por imagen (créditos altos en Freepik). Sin multi-reference comparable.

### 5. Solo herramientas deterministas (cero AI)

Considerada viable pero limitante. Diagramas y screenshots cubren ~60% de los casos, pero portadas y hero images requieren producción visual que AI resuelve de forma más eficiente que stock genérico o diseño manual.

### 6. Fal.ai / Replicate como proxy de Gemini

Rechazada. Re-sellers con data residency incierta y ToS que pueden no cubrir uso comercial del modelo subyacente.

## Consecuencias

### Positivas

- Acceso al mejor modelo actual para texto en imagen (diferencial de Gemini 3 Pro Image).
- Consistencia visual via reference pack versionado.
- Capa de abstracción permite swap de provider sin tocar callers.
- Stock Freepik cubre iconografía y SVG que AI no resuelve bien.
- Herramientas deterministas para diagramas = cero alucinación, trazabilidad total.

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

## Fuentes Perplexity

- **UA-11**: `Perplexity/Umbral Agent Stack/11_ Evaluación Visual Nano Banana vs Freepik/capa-visual-rick-v1.md` — comparativa completa, pricing, licencias, riesgos, arquitectura visual
- **UA-08**: `Perplexity/Umbral Agent Stack/08_ Comparacion Visual Nano Banana Pro y Freepik/capa_visual_editorial.md` — versión previa (histórica, sustituida por UA-11)
- **UA-04**: `Perplexity/Umbral Agent Stack/04_ Direccion Visual para Contenido Tecnico/` — dirección visual general
