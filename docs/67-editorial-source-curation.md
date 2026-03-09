# 67 — Curacion editorial desde fuentes de autoridad

> Capa editorial para el proyecto embudo: detectar lo ultimo publicado por fuentes de referencia, filtrar por alineacion con la narrativa de David Moreira y convertir solo lo seleccionado en piezas para blog, newsletter, LinkedIn y X.

**Estado:** Diseno operativo
**Fecha:** 2026-03-09
**Relacionada con:** `docs/60-rrss-pipeline-n8n.md`, `docs/project-embudo-master-plan.md`, `docs/68-editorial-phase-1-manual.md`

---

## 1. Objetivo

Agregar al embudo una linea de automatizacion editorial que:

1. busque lo ultimo publicado por fuentes de autoridad concretas;
2. lo liste y rankee segun alineacion con la narrativa, propuesta y audiencia de David;
3. deje una shortlist para seleccion humana;
4. solo despues genere derivados editoriales en el estilo y estrategia de David.

El objetivo no es autopublicar resenas de terceros, sino usar esas fuentes como insumo curado para:

- newsletter;
- blog;
- LinkedIn;
- X;
- ideas de webinars, pilots y ofertas.

---

## 2. Fuentes iniciales de autoridad

Las primeras fuentes a monitorear son:

- [Gartner](https://www.gartner.com/)
- [McKinsey](https://www.mckinsey.com/)
- [Every](https://every.to/newsletter)
- [Ruben Substack](https://ruben.substack.com/)

Estas fuentes se tratan como "editorial inputs", no como canales de publicacion final.

## 2.1 Source of truth operativo

La lista oficial no debe quedarse fija en esta pagina. La fuente viva de verdad es:

- la pagina Notion `Fuentes`
- su base hija `Fuentes confiables`
- la base Notion `Referentes`

Estas fuentes cumplen funciones distintas y no deben mezclarse:

- **fuentes de autoridad / research / mercado**: marcos, estudios, reportes, credibilidad
- **fuentes de industria / instituciones / estandares**: openBIM, AECO, estandares, senales sectoriales
- **fuentes de divulgacion / estilo / comunicacion**: referencias de formato, framing y claridad
- **fuentes experimentales / observacion**: inputs secundarios que se observan antes de entrar al flujo base

## 2.2 Inventario validado para fase 1

Con la validacion operativa hecha con Rick, la fase 1 editorial manual debe priorizar:

- **fuentes piloto activas**
  - BuildingSMART INT
  - BuildingSMART CL
  - OpenAI
  - McKinsey
  - Ruben Substack
  - Every
- **referentes benchmark activos**
  - Ruben Substack
  - Every
  - Brian Solis
  - Marc Vidal
  - David Barco Moreno

Fuentes o entradas que por ahora deben quedar fuera o en segundo plano:

- Gartner, mientras siga bloqueada por 403
- OECD e IFC, salvo que se necesite respaldo institucional puntual
- referentes demasiado generales sin conexion clara con AECO, automatizacion o la propuesta de David

---

## 3. Regla editorial principal

El sistema debe seguir este orden:

1. capturar lo ultimo de las fuentes;
2. normalizar y resumir cada item;
3. puntuar alineacion con:
   - narrativa de David;
   - propuesta de valor;
   - segmentos priorizados;
   - pain-points ya detectados;
4. presentar shortlist;
5. esperar seleccion o aprobacion humana;
6. recien entonces proponer piezas derivadas.

No se debe pasar directo de "fuente encontrada" a "post publicado" sin una capa de seleccion.

---

## 4. Criterios de alineacion

Cada item capturado debe evaluarse contra:

- relevancia para AECO / BIM / automatizacion / agentes IA;
- utilidad para arquitectos, coordinadores BIM, responsables de transformacion o decision-makers;
- cercania con la narrativa de David:
  - automatizacion empatica;
  - puentes digitales;
  - citizen developer;
  - BIM + IA + automatizacion aplicada;
- potencial de transformarse en:
  - insight de mercado;
  - post de LinkedIn;
  - articulo de blog;
  - newsletter;
  - webinar o quick-win comercial;
- novedad o valor contrarian;
- posibilidad de aterrizarlo con ejemplos y tono propios de David.

### Score sugerido

Usar un score compuesto 0-100:

- `topic_fit` (0-30)
- `audience_fit` (0-20)
- `offer_fit` (0-20)
- `narrative_fit` (0-20)
- `reuse_potential` (0-10)

---

## 5. Output minimo por item curado

Cada item debe dejar, como minimo:

- `source_name`
- `source_url`
- `item_url`
- `title`
- `published_at`
- `author`
- `summary`
- `sample_quote`
- `alignment_score`
- `alignment_reason`
- `recommended_angle`
- `recommended_channel`
- `status`

Estados sugeridos:

- `captured`
- `screened_out`
- `shortlisted`
- `selected`
- `derived`
- `discarded`

---

## 6. Shortlist y seleccion humana

Antes de derivar contenido, el sistema debe producir una shortlist con:

- top items por score;
- por que cada item calza con la audiencia;
- que angulo editorial conviene tomar;
- que formato conviene:
  - post LinkedIn;
  - hilo X;
  - articulo blog;
  - newsletter;
  - webinar idea.

La shortlist debe quedar en un punto revisable por David:

- Notion;
- Linear;
- o una cola de aprobacion en n8n/Telegram.

Recomendacion operativa:

- `Notion` para shortlist editorial y comentarios;
- `Linear` para trazabilidad del frente de trabajo;
- `n8n` para schedule + captura + scoring + handoff.

---

## 7. Derivacion de contenido

Una vez seleccionado un item, el sistema puede proponer:

- resumen ejecutivo para newsletter;
- post LinkedIn con el tono de David;
- hilo o post para X;
- articulo o nota para blog;
- idea de webinar o recurso descargable.

La derivacion debe respetar:

- tono directo;
- enfoque tecnico-pragmatico;
- uso de datos y ejemplos;
- cero slop corporativo;
- adaptacion a los objetivos del embudo.

La pieza derivada no debe ser una copia del contenido fuente. Debe ser una reinterpretacion con:

- contexto para la audiencia de David;
- lectura propia;
- conexion con dolores reales;
- CTA alineado con sus servicios, formacion o producto.

---

## 8. Diseno n8n recomendado

Antes de pasar a esta capa, debe existir una fase manual estable.

## 7.1 Fase manual obligatoria antes de automatizar

No conviene saltar directo a n8n. Primero hay que operar una fase editorial manual y trazable para validar que la logica realmente sirve.

Cadencia minima recomendada:

- **lunes**: revision de fuentes oficiales e institucionales
- **miercoles**: revision de divulgacion y framing
- **viernes**: shortlist editorial semanal y decision de piezas

Checklist minimo por semana:

- revisar latest items de fuentes piloto
- capturar entre 5 y 10 senales relevantes
- rankear por narrativa, propuesta, audiencia y objetivos comerciales
- crear shortlist humana semanal
- seleccionar maximo 2 piezas candidatas
- decidir si derivan a newsletter, blog, LinkedIn o se descartan
- dejar trazabilidad en Linear

No pasar a implementacion n8n hasta que se cumplan estas condiciones:

- shortlist estable durante 3-4 semanas consecutivas
- scoring editorial suficientemente claro y repetible
- al menos 2 fuentes con captura consistente
- baja ambiguedad al seleccionar piezas
- evidencia de que la operacion manual ya consume demasiado tiempo

### Workflow editorial sugerido

1. `Editorial-Capture-Latest`
   - schedule;
   - fetch de latest items por fuente;
   - normalizacion;
   - dedupe.

2. `Editorial-Score-Alignment`
   - scoring semantico;
   - clasificacion por segmento, narrativa y potencial comercial.

3. `Editorial-Shortlist`
   - top N por ventana de tiempo;
   - salida a Notion / queue de revision.

4. `Editorial-Derivation`
   - solo para items `selected`;
   - genera draft para blog/newsletter/LinkedIn/X.

5. `Editorial-Review-And-Publish`
   - aprobacion humana;
   - handoff a pipeline RRSS o CMS.

### Regla de aprobacion

Las automatizaciones pueden:

- capturar;
- rankear;
- resumir;
- pre-redactar;

pero no deben asumir publicacion automatica sin validacion humana.

---

## 9. Estado por fuente

Cada fuente debe marcarse como:

- `viable_now`
- `partial`
- `blocked`

con una nota operativa, por ejemplo:

- RSS disponible;
- pagina publica viable;
- scraping delicado por ToS;
- requiere aprobacion humana o configuracion adicional.

Esto evita que Rick o n8n prometan automatizaciones inexistentes.

---

## 10. Relacion con el proyecto embudo

Esta capa editorial alimenta tres cosas del embudo:

1. **Awareness**
   - contenido basado en fuentes con autoridad externa.

2. **Consideration**
   - reinterpretacion aplicada a pain-points concretos de la audiencia.

3. **Conversacion comercial**
   - convertir tendencias y reportes en:
     - quick wins;
     - pilots;
     - workshops;
     - piezas de autoridad para cerrar reuniones.

---

## 11. Reglas de implementacion para Rick

Si Rick trabaja este frente, debe:

- leer primero Perfil + Segmentacion;
- tratar estas fuentes como insumo editorial, no como fin en si mismo;
- listar items antes de derivar contenido;
- pedir aprobacion o dejar shortlist revisable antes de asumir publicacion;
- dejar trazabilidad en Linear y en el archivo operativo del proyecto;
- marcar limitaciones reales por fuente.

---

## 12. Proximo entregable recomendado

Crear un documento operativo tipo:

`paso-x-curacion-editorial-fuentes-autoridad-v1.md`

que deje definidos:

- fuentes;
- metodo de captura;
- score de alineacion;
- formato de shortlist;
- mecanismo de aprobacion;
- outputs derivados;
- integracion con n8n, Notion, blog, newsletter, LinkedIn y X.
