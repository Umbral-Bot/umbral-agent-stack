---
name: linear-project-auditor
description: auditar un proyecto de linear contra evidencia real en repo, notion, vm y sesiones del agente. usar cuando se necesite verificar si el estado reportado en linear coincide con entregables reales, detectar fake progress, issues sin trazabilidad, pasos sin entregable, drift entre linear y archivos reales, o proyectos oficiales sin comentario de avance. producir una auditoria verificable con orden de herramientas, criterios de evidencia y formato de hallazgos respaldado por ids, rutas, paginas, comandos y fechas exactas.
---

# Linear Project Auditor

## Objetivo
Auditar un proyecto de Linear contra fuentes primarias de ejecucion real. Tratar Linear como fuente de afirmaciones, no como verdad. Priorizar la falsacion de claims de progreso antes que la narracion del proyecto.

Usar evidencia fuerte en este orden de preferencia:
1. estado real en VM o runtime
2. artefactos del repo y git
3. documentos vivos en Notion
4. sesiones del agente o transcriptos
5. comentarios y estados en Linear

No aceptar comentarios de progreso, resumenes de sesiones o texto aspiracional como prueba suficiente de ejecucion si no apuntan a un entregable real.

## Reglas base
- Identificar primero que dice Linear que ya existe, que esta en curso y que deberia estar listo.
- Verificar cada afirmacion contra artefactos concretos.
- Registrar exactamente donde se busco antes de concluir que falta evidencia.
- Separar siempre `sin evidencia encontrada` de `no verificado por falta de acceso`.
- Usar fechas exactas, ids exactos, rutas exactas y comandos exactos.
- Preferir contradicciones verificables sobre interpretaciones blandas.
- Mantener cada hallazgo anclado a una afirmacion puntual de Linear.
- Marcar la confianza del hallazgo segun la calidad de la evidencia.

## Orden de herramientas
Seguir este orden por defecto:
1. Linear connector o API de Linear
2. Repo discovery y git
3. Verificacion exacta con terminal, worker o VM
4. Notion
5. Transcriptos o sesiones del agente

## Hallazgos a clasificar
- fake progress
- issue sin trazabilidad
- paso sin entregable
- drift entre Linear y archivos reales
- proyecto oficial sin comentario de avance

## Checklist operativo
- Confirmar proyecto, equipo y ventana de auditoria.
- Confirmar accesos disponibles: Linear, repo, Notion, VM, sesiones.
- Extraer metadata del proyecto y lista de issues relevantes.
- Convertir estados y comentarios de Linear en claims verificables.
- Buscar evidencia en repo o git para cada claim.
- Buscar evidencia en VM o runtime para claims operativos.
- Buscar evidencia en Notion para claims documentales o de decision.
- Revisar sesiones del agente solo como soporte contextual.
- Evaluar trazabilidad fuerte, aceptable, debil o ausente.
- Clasificar hallazgos y asignar severidad.

## Formato de salida
Usar este formato salvo que el usuario pida otro:
1. alcance
2. veredicto ejecutivo
3. hallazgos
4. acciones correctivas

Cada hallazgo debe incluir:
- claim exacto de Linear
- fuentes revisadas
- evidencia encontrada
- evidencia ausente
- veredicto
- confianza
- accion sugerida
