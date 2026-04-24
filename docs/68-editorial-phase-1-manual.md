# 68 - Fase editorial manual validada

> Resultado operativo validado con Rick antes de pasar a automatizacion n8n para el frente editorial del proyecto embudo.

**Estado:** Validado en vivo
**Fecha:** 2026-03-09
**Relacionada con:** `docs/67-editorial-source-curation.md`, `docs/60-rrss-pipeline-n8n.md`

---

## 1. Decision

La fase editorial 1 no debe comenzar con automatizacion.

Primero debe operar una capa manual, trazable y con shortlist humana para validar:

- si las fuentes realmente entregan senal util;
- si la audiencia y la narrativa de David quedan bien servidas;
- si las piezas candidatas sostienen valor editorial y comercial;
- y si el costo operativo manual justifica despues una capa n8n.

---

## 2. Canales priorizados

La validacion operativa dejo esta priorizacion:

- **blog**: canal prioritario
- **newsletter**: canal prioritario
- **LinkedIn**: canal de distribucion con take propio
- **X**: observacion, sin operacion prioritaria por ahora

---

## 3. Fuentes piloto activas

Fuentes activas para fase 1:

- BuildingSMART INT
- BuildingSMART CL
- OpenAI
- McKinsey
- Ruben Substack
- Every

Referentes benchmark activos:

- Ruben Substack
- Every
- Brian Solis
- Marc Vidal
- David Barco Moreno

Fuentes o entradas que por ahora deben quedar fuera o en segundo plano:

- Gartner, mientras siga bloqueada por 403
- OECD, salvo necesidad puntual de respaldo institucional
- IFC como fuente editorial recurrente
- scraping pesado de referentes de divulgacion

---

## 4. Cadencia semanal recomendada

- **Lunes**: revision de fuentes oficiales e institucionales
- **Miercoles**: revision de divulgacion, framing y formato
- **Viernes**: shortlist editorial semanal y decision de piezas

Regla:

- LinkedIn reutiliza material solo despues de shortlist aprobada
- X queda fuera del flujo principal hasta validar que vale la pena operarlo

---

## 5. Checklist operativo semanal

- revisar latest items de fuentes piloto
- capturar entre 5 y 10 senales relevantes
- rankear por narrativa, propuesta, audiencia y objetivos comerciales
- crear shortlist humana semanal
- seleccionar maximo 2 piezas candidatas
- decidir derivacion: newsletter, blog, LinkedIn o descarte
- dejar trazabilidad en Linear

---

## 6. Formato minimo de shortlist humana

Por cada item:

- fuente
- titulo o angulo
- tipo de fuente
- por que importa ahora
- alineacion con narrativa/propuesta/audiencia
- canal sugerido
- riesgo editorial
- decision: usar ahora / esperar / descartar

---

## 7. Piezas candidatas iniciales

### Newsletter

- base: Ruben Substack + Every
- angulo: IA sin criterio no resuelve procesos; como filtrar hype y priorizar automatizacion util en AECO
- objetivo: construir criterio editorial y posicionar una mirada propia

### Blog

- base: BuildingSMART INT + McKinsey
- angulo: que cambios realmente alteran coordinacion, trazabilidad y ROI en equipos BIM/AECO
- objetivo: producir una pieza de autoridad evergreen conectada con pain-points reales

---

## 8. Regla de reutilizacion en LinkedIn

LinkedIn no debe copiar la pieza larga.

Debe:

- tomar una sola tesis o insight;
- convertirla en take propio;
- cerrar con pregunta, observacion o CTA suave;
- evitar replicar estructura, tono o secuencia exacta de newsletter o blog.

---

## 9. Gate para pasar a n8n

Solo pasar a automatizacion cuando se cumpla esto:

- shortlist estable durante 3-4 semanas consecutivas
- scoring editorial claro y repetible
- al menos 2 fuentes con captura consistente
- baja ambiguedad al elegir piezas
- evidencia de que la operacion manual ya consume demasiado tiempo

Mientras eso no ocurra, no:

- autopublicar
- redactar piezas finales automaticamente
- derivar multicanal sin seleccion humana
- scrapear referentes de divulgacion de forma agresiva

---

## 10. Trazabilidad minima

Cada avance de este frente debe dejar:

- issue o comentario actualizado en Linear
- artefacto verificable en la carpeta del proyecto
- siguiente accion concreta
- estado coherente del frente

---

## 11. Flujo canonico por candidata source-driven

Cuando el sistema trabaje una candidata editorial con fuentes externas, usar esta secuencia:

1. fuentes y senales
2. extraccion y transformacion
3. borrador editorial base
4. validacion de atribucion y trazabilidad
5. pasada de voz contra Guia Editorial y Voz de Marca
5a. direccion de comunicacion / curaduria narrativa
6. QA editorial y tecnico
7. revision humana
8. aprobacion de contenido
9. autorizacion de publicacion

La etapa `5a` existe porque una pieza puede ser correcta, segura y trazable, pero aun asi no sonar a David.

`rick-communication-director` revisa naturalidad, ritmo, lenguaje, densidad AEC/BIM y frases que David probablemente no diria. No reemplaza a `rick-qa`: QA mantiene la validacion de fuentes, claims, schema, gates, seguridad y publicacion.

Regla de fase 1:

- `rick-communication-director` es runtime-registered, read-only y dry-run.
- tiene workspace dedicado para invocacion deliberada, pero no routing autonomo.
- no escribe en Notion
- no modifica repos
- no publica
- no marca gates
- entrega variantes, diagnostico y prompts de configuracion
