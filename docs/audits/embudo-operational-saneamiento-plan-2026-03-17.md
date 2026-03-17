# Saneamiento operativo del embudo - 2026-03-17

## Objetivo
Convertir los nuevos estados de revisión y comentarios dejados por David en una secuencia operativa clara para Rick, sin rehacer manualmente el trabajo por él.

## Verificación de comentarios en Notion
Se leyó el estado real directamente desde la API de Notion usando el stack activo en la VPS.

### Proyecto
- `Proyecto Embudo Ventas`
  - page id: `31e5f443-fb5c-8125-a21c-e5333fb32a03`
  - comentarios visibles: `0`

### Entregables del embudo
- `Benchmark del sistema de contenido y funnel de Ruben Hassid`
  - page id: `3245f443-fb5c-8152-89cf-cf8c381ada0a`
  - estado revisión: `Aprobado con ajustes`
  - comentario visible:
    - `Revisé el documento y está bien, aprobado pero necesito que agregues un informe detallado luego de que realices un estudio donde utilizas ingenieria inversa para extraer las estrategias, forumlas y logicas de automatización de Ruben para que podamos replicar en nuestro proyecto embudo`

- `Cierre crítico del estado real del proyecto embudo`
  - page id: `3245f443-fb5c-8101-8d34-d5f552b24e18`
  - estado revisión: `Pendiente revision`
  - comentario visible:
    - `no se entiende`

- `Benchmark parcial de Kris Wojslaw para el embudo`
  - page id: `3265f443-fb5c-81c0-9565-e442a9b70d50`
  - estado revisión: `Rechazado`
  - comentario visible:
    - `trabajo incompleto`

## Lectura operativa
El cuello de botella ya no es de infraestructura sino de cierre editorial y de gobernanza:

1. `Ruben` ya no es un benchmark para corregir mínimamente.
   - El comentario lo convierte en un frente derivado:
   - producir un informe de ingeniería inversa útil para replicación en el embudo.
   - Recomendación:
     - no degradar el benchmark aprobado;
     - crear una tarea y, si sale algo sustantivo, un entregable derivado nuevo.

2. `Cierre crítico` sí requiere retrabajo directo.
   - El feedback `no se entiende` invalida la forma actual, no necesariamente el tema.
   - Recomendación:
     - mantener el entregable vivo;
     - pedir reescritura con formato más claro y orientado a decisión.

3. `Kris` no debe seguir flotando como benchmark parcial ambiguo.
   - Ya está `Rechazado`.
   - Recomendación:
     - que Rick deje explícita la regularización:
       - o propone redo con umbral de evidencia real;
       - o lo deja cerrado como referencia descartada por incompleta.
     - No dejarlo en limbo.

## Saneamiento operativo recomendado
Orden sugerido:

1. Traducir cada estado/comentario a una acción concreta en `Tareas`.
2. No reabrir todo el proyecto; trabajar solo sobre los tres entregables ya tocados.
3. Mantener el flujo:
   - `Proyecto -> Tarea -> Entregable -> Revisión`
4. Para `Ruben`, separar claramente:
   - benchmark aprobado
   - nuevo análisis derivado
5. Para `Cierre crítico`, reescribir sobre la misma pieza.
6. Para `Kris`, cerrar semánticamente el rechazo con criterio.

## Prompt recomendado para Rick
```text
rick, revisa los comentarios que te dejé en los entregables del proyecto embudo y regulariza ese frente dentro del flujo correcto.

no rehagas todo ni abras frentes paralelos.
quiero que traduzcas cada estado y comentario en la siguiente acción correcta para el proyecto:
- si algo requiere retrabajo, haz el retrabajo donde corresponda
- si algo aprobado deriva en una pieza nueva, sepáralo bien
- si algo rechazado debe cerrarse o reencauzarse, déjalo resuelto con criterio

trabaja sobre los entregables ya existentes, deja trazabilidad real y al final dime corto:
- qué comentario leíste en cada caso
- qué hiciste de verdad
- qué quedó actualizado
- qué tarea o entregable nuevo hizo falta crear
- y qué sigue pendiente de verdad
```

## Diagnóstico corto sobre encoding
En las páginas revisadas del embudo (`Ruben`, `Cierre crítico`, `Kris`, `OpenClaw`) no apareció texto corrupto tipo `aprobaci?n`, `RevisiÃ³n` o similar en bloques o comentarios actuales.

Eso sugiere que el problema de acentos no está hoy en estas piezas del embudo, sino en otro frente:
- archivos históricos del repo abiertos con encoding incorrecto desde terminal,
- o alguna otra página/flujo fuera de estos entregables.

Conviene seguir el rastreo con un ejemplo exacto de la página donde hoy se vea el texto roto.
