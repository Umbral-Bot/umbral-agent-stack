---
name: linear-delivery-traceability
description: fuerza trazabilidad minima por paso de proyecto en linear y carpetas
  de workspace. usar cuando chatgpt vaya a reportar avance, mover estado, redactar
  o publicar un comentario de issue, o afirmar que existe progreso en una entrega.
  verificar por tool calls frescas que el proyecto sea oficial segun la fuente vigente
  declarada por david, que la issue sea la correcta, que exista comentario de avance,
  que haya artefacto verificable con ruta exacta, que la siguiente accion este definida
  y que el estado sea coherente. rechazar progreso sin evidencia fresca o sin artefacto.
metadata:
  openclaw:
    emoji: 📌
    requires:
      env: []
---

# Linear Delivery Traceability

## Overview
Usar este skill como guardarrail antes de cualquier afirmacion de progreso. Sin issue correcta, comentario de avance, artefacto verificable, siguiente accion y estado coherente, no declarar avance.

## Flujo obligatorio
1. Resolver el proyecto oficial.
2. Resolver la issue correcta.
3. Recolectar evidencia fresca.
4. Verificar el artefacto.
5. Verificar o publicar el comentario de avance.
6. Fijar la siguiente accion.
7. Determinar el estado coherente.
8. Declarar o bloquear.

## Comentario minimo obligatorio
Usar este bloque como comentario de avance o verificar que exista:

```text
avance: [cambio verificable]
artefacto: [ruta exacta]
verificado con: [tool call fresco o evidencia directa]
siguiente accion: [accion concreta]
estado propuesto: [estado real del workflow]
```

## Veredicto minimo
Entregar siempre:
- proyecto
- issue
- artefacto
- siguiente accion
- estado
- veredicto: `ok para declarar progreso` o `no declarar progreso`

## Anti-patrones
- Declarar progreso sin tool calls frescas.
- Declarar progreso con solo conversacion o intencion.
- Marcar `done` sin artefacto final o con `siguiente accion` abierta.
- Usar un comentario generico sin ruta exacta.
- Reutilizar evidencia vieja para un cambio nuevo.
- Hardcodear la lista de proyectos oficiales de David.
- Aceptar una issue ambigua, fuera de proyecto o no oficial.
- Decir `subido`, `listo` o `avanzado` sin verificar carpeta e issue.

