---
name: bim-expert
description: >-
  Experto en gestion de informacion BIM segun ISO 19650. Genera documentacion,
  guias, glosarios y analisis alineados con estándares internacionales y
  buenas practicas BIM Forum.
  Use when "ISO 19650", "BIM", "estandar BIM", "gestion informacion",
  "plan ejecucion BIM", "BEP", "CDE", "modelo informacion".
metadata:
  openclaw:
    emoji: "\U0001F3D7"
    requires:
      env: []
---

# BIM Expert — ISO 19650 & Gestion de Informacion

Rick usa este skill para generar documentacion tecnica BIM, responder consultas sobre ISO 19650, redactar guias de implementacion y producir documentos alineados con estandares internacionales.

## Glosario ISO 19650 — Terminos clave

### Actores y organizacion

| Termino | Definicion |
|---------|-----------|
| **Actor** | Persona, organizacion o unidad involucrada en un proceso de construccion |
| **Parte contratante (appointing party)** | Receptor de informacion. UK: client / asset owner |
| **Parte contratada (appointed party)** | Proveedor de informacion. UK: supplier |
| **Equipo de entrega (delivery team)** | Parte contratada principal y sus subcontratados |
| **Equipo de tarea (task team)** | Individuos reunidos para una tarea especifica |
| **Cliente (client)** | Actor que inicia un proyecto y aprueba el brief |

### Gestion de informacion

| Termino | Definicion |
|---------|-----------|
| **BIM** | Uso de una representacion digital compartida de un activo para facilitar procesos de diseno, construccion y operacion |
| **CDE (Entorno Comun de Datos)** | Fuente acordada de informacion para un proyecto, con flujo de trabajo y solucion tecnologica |
| **Modelo de informacion (information model)** | Conjunto de contenedores de informacion estructurados y no estructurados |
| **PIM** | Modelo de informacion del proyecto (fase de entrega) |
| **AIM** | Modelo de informacion del activo (fase operativa) |
| **Contenedor de informacion** | Conjunto nombrado recuperable: subdirectorio, archivo, subconjunto |
| **Federacion** | Crear un modelo compuesto a partir de contenedores separados |
| **Nivel de necesidad de informacion** | Marco que define extension y granularidad (prevenir exceso de informacion) |

### Requisitos de informacion (jerarquia)

| Acronimo | Nombre | Relacion |
|----------|--------|----------|
| **OIR** | Requisitos de informacion organizacional | Objetivos de la organizacion |
| **AIR** | Requisitos de informacion del activo | Operacion del activo |
| **PIR** | Requisitos de informacion del proyecto | Entrega del activo |
| **EIR** | Requisitos de intercambio de informacion | Contrato/encargo especifico |

### Ciclo de vida

| Termino | Definicion |
|---------|-----------|
| **Ciclo de vida** | Desde definicion de requisitos hasta terminacion de uso |
| **Fase de entrega** | Diseno, construccion y comision |
| **Fase operativa** | Uso, operacion y mantenimiento |
| **Evento desencadenante** | Evento que cambia el activo o su estado, requiriendo intercambio de informacion |
| **Punto de decision clave** | Momento de decision crucial sobre direccion o viabilidad |

### Equivalencias UK/ISO

| ISO 19650 | UK |
|-----------|-----|
| Appointed party | Supplier |
| Appointing party | Client (proyecto) / Asset owner (activo) |
| EIR | Employer's information requirements |
| Level of information need | Level of definition (LOD) |
| Federation strategy | Volume strategy |

## ISO 19650 — Resumen por partes

### Parte 1: Conceptos y principios

Establece el marco para la gestion de informacion BIM. Conceptos clave: ciclo de vida del activo, niveles de necesidad de informacion, federacion de modelos, capacidad tecnica (capability) vs operativa (capacity). Aplica a todo tipo de activo construido.

### Parte 2: Fase de entrega

Define el proceso de gestion de informacion durante diseno y construccion:
1. Evaluacion y necesidades (OIR > AIR > PIR)
2. Licitacion (EIR, BEP pre-contrato, evaluacion capacidad/capacidad)
3. Ejecucion (BEP detallado, CDE, produccion, revision, entrega)
4. Cierre (modelos as-built, traspaso a operaciones)

### Parte 3: Fase operativa

Gestion de informacion durante uso y mantenimiento del activo. Foco en: actualizacion del AIM, eventos desencadenantes (mantenimiento, renovacion, demolicion), vinculacion con sistema de gestion de activos.

### Parte 5: Seguridad de la informacion

Evaluacion de sensibilidad de la informacion BIM. Clasificacion de niveles de seguridad, control de acceso al CDE, protocolos de comparticion con terceros.

### Parte 6: Seguridad y salud

Gestion de informacion para salud y seguridad durante el ciclo de vida. Vinculacion de riesgos con elementos del modelo, registro de informacion de seguridad en el AIM.

## Guia de redaccion BIM

### Principios

- **Precision tecnica:** Usar terminologia ISO 19650 consistentemente. Incluir referencias normativas.
- **Accesibilidad:** Escribir para profesionales con distintos niveles de madurez BIM. Explicar terminos en primera aparicion.
- **Practicidad:** Orientar hacia aplicacion en proyectos reales con casos de uso concretos.

### Terminologia

- Espanol con ingles entre parentesis en primera aparicion: "El entorno comun de datos (CDE) es..."
- Definir acronimos en primera aparicion, usar solo el acronimo despues
- Evitar anglicismos cuando hay equivalente: delivery > entrega, workflow > flujo de trabajo, stakeholder > parte interesada, milestone > hito, handover > traspaso

### Formato

- Max 4-5 oraciones por parrafo, una idea principal
- Oraciones de max 25 palabras
- Listas con vinetas (sin orden) o numeradas (secuencia), max 7 elementos
- Tablas para comparaciones o informacion estructurada
- Citar ISO con formato: "segun ISO 19650-1, paragrafo 12.2"

### Restricciones de lenguaje

| Evitar | Alternativa |
|--------|-------------|
| Potenciar, optimizar, revolucionar | Verbo especifico + resultado |
| Robusto, holistico, sinergico | Descripcion concreta |
| Cabe destacar, es importante mencionar | Afirmacion directa |
| En el mundo actual, en el panorama actual | Omitir o especificar |
| Preguntas retoricas como introduccion | Afirmacion directa |
| "No solo X, tambien Y" | Afirmacion directa |

## Estructura de documentos tipo

### Guia de implementacion

1. Titulo y metadata (version, fecha, autores)
2. Introduccion (proposito, audiencia, alcance)
3. Contexto normativo (referencias ISO)
4. Conceptos previos
5. Pasos de implementacion (responsable + entregable por paso)
6. Errores comunes
7. Checklist de implementacion
8. Referencias normativas

### Documento de buenas practicas

1. Resumen ejecutivo (2-3 parrafos)
2. Introduccion y alcance
3. Buenas practicas (BP-01, BP-02...: descripcion, justificacion, ejemplo)
4. Practicas a evitar
5. Indicadores de exito
6. Referencias

### Checklist de verificacion

1. Informacion del proyecto
2. Categorias con tabla: #, Verificacion, Cumple, N/A, Observaciones
3. Resumen (total, cumplidos, no cumplidos, N/A)
4. Firma de conformidad

### Caso de estudio

1. Ficha del proyecto (tipo, ubicacion, escala, participantes, anio)
2. Contexto y objetivo
3. Solucion implementada (estructura informacion, tecnologia, gobernanza)
4. Resultados (beneficios con metricas, desafios y resoluciones)
5. Lecciones aprendidas y recomendaciones

### Matriz de seleccion

| Necesidad | Plantilla |
|-----------|-----------|
| Explicar como hacer algo paso a paso | Guia de implementacion |
| Dar recomendaciones con experiencia | Buenas practicas |
| Verificar cumplimiento de requisitos | Checklist |
| Resolver dudas comunes | FAQ |
| Documentar experiencia real | Caso de estudio |

## Perspectiva para iniciativas BIM

### Nicho diferenciador

La interseccion **Automatizacion + BIM** en espanol esta practicamente vacia.

| Expertise | Competidores | Oportunidad |
|-----------|-------------|-------------|
| Power BI | Ruth Pozuelo (no BIM) | Libre |
| Revit/Dynamo | Milos Temerinski (no automatizacion) | Libre |
| BIM + Automatizacion + IA | — | **Sin competencia** |

### Frameworks de evaluacion

1. **Puentes Digitales:** Preferir iniciativas que conecten silos (Diseno<>Construccion, Datos<>Decisiones, Campo<>Oficina)
2. **Automatizacion Empatica:** Evaluar impacto humano, no solo eficiencia tecnica
3. **Construccion 4.0 en 3 capas:** Datos conectados > Procesos automatizados > Decisiones asistidas

### Criterios alta prioridad

- Combina BIM + Automatizacion o BIM + IA
- Construye puente entre silos de informacion
- Reduce tareas repetitivas cuantificables
- Accesible para no programadores (Citizen Developer)
- Aplicable a contexto LATAM

### Metricas de referencia (Chile)

| Metrica | Valor |
|---------|-------|
| Proyectos BIM con problemas coordinacion | ~67% |
| Tiempo coordinador BIM en tareas repetitivas | 147 horas/mes |
| RFIs semanales en proyecto tipico 50 dptos | 20-30 |

### Temas de alto interes

1. ISO 19650 + Power Platform
2. ACC + Power BI dashboards
3. IA aplicada a coordinacion BIM
4. Dynamo para no programadores
5. Transformacion digital en PyMEs AEC
