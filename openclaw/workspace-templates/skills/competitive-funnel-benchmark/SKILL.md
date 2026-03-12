---
name: competitive-funnel-benchmark
description: estudiar en profundidad una persona, marca, perfil, post, landing, lead magnet o funnel externo y convertirlo en un teardown accionable para Umbral. usar cuando David pida analizar un caso como referencia, benchmark o competencia, especialmente si involucra LinkedIn, landing pages, CTAs, lead magnets o captacion. obliga a cubrir varias fuentes, separar evidencia de inferencia y no cerrar con una sola landing o una captura.
metadata:
  openclaw:
    emoji: "🧭"
    requires:
      env: []
---

# Competitive Funnel Benchmark

## Objetivo
Convertir un caso externo en un teardown reutilizable para Umbral, con evidencia real y con una separacion clara entre lo observado y lo inferido.

## Cuándo usarla
- cuando David pida estudiar a una persona o marca "en profundidad"
- cuando el caso incluya LinkedIn, perfil como landing, lead magnet, CTA, lead capture o funnel
- cuando el objetivo sea adaptar metodo, estructura o angulos al proyecto embudo

## Regla principal
No cerrar con una sola fuente.

Como minimo cubrir:
1. la fuente principal indicada por David
2. una segunda fuente independiente del mismo caso
3. una tercera señal si existe y es accesible:
   - perfil publico
   - comentarios
   - landing secundaria
   - pagina principal
   - lead magnet accesible

Si alguna fuente no es accesible:
- declararlo como `no verificado`
- no convertirlo en hecho

## Orden de trabajo
1. identificar el objeto principal del benchmark
2. revisar el estado real del proyecto Umbral donde esto impacta
3. capturar evidencia del caso externo
4. separar evidencia de inferencia
5. construir teardown
6. traducirlo a decisiones para Umbral
7. dejar trazabilidad real si el trabajo forma parte de un proyecto oficial

## Herramientas
- usar `web_fetch` o `web_search` para sitios, landings y fuentes publicas
- usar `umbral_browser_*` si la fuente principal requiere navegador real o interaccion
- no depender solo de una captura enviada por David si hay fuentes reales accesibles
- no usar browser si `web_fetch` ya cubre la evidencia necesaria y no hay friccion de acceso

## Checklist minimo de cobertura
Para considerar el benchmark suficientemente profundo, cubrir como minimo:
- hook principal
- promesa principal
- audiencia implicita
- oferta o lead magnet
- CTA
- siguiente paso del funnel
- prueba social o autoridad observable
- limitaciones o huecos de verificacion

## Formato obligatorio
Entregar siempre estas secciones:

### 1. Evidencia observada
- que se vio de forma directa
- de que fuente salio cada punto

### 2. Inferencias
- que se esta deduciendo
- por que esa inferencia es razonable
- nivel de confianza si hace falta

### 3. Teardown del funnel
- entrada
- captura
- promesa
- conversion
- continuidad

### 4. Adaptacion para Umbral
- que si conviene adaptar
- que no conviene copiar
- que falta para probarlo en el proyecto embudo

## Anti-patrones
- tratar una landing como si fuera todo el sistema
- confundir texto de marketing con evidencia del funcionamiento real
- decir "estudiado en profundidad" sin haber cubierto varias fuentes
- mezclar observacion e inferencia en la misma lista
- responder con opinion tactica sin teardown

## Salida minima sugerida
1. resumen ejecutivo
2. fuentes realmente consultadas
3. evidencia observada
4. inferencias
5. teardown
6. insights para Umbral
7. siguiente accion recomendada
