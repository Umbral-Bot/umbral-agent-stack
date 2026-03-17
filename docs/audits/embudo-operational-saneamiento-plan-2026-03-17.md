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
    - `Revisé el documento y está bien, aprobado pero necesito que agregues un informe detallado luego de que realices un estudio donde utilizas ingeniería inversa para extraer las estrategias, fórmulas y lógicas de automatización de Ruben para que podamos replicar en nuestro proyecto embudo`

- `Cierre crítico del estado real del proyecto embudo`
  - page id: `3245f443-fb5c-8101-8d34-d5f552b24e18`
  - estado revisión: `Pendiente revisión`
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
   - El comentario lo convierte en un frente derivado.
   - Se debe producir un informe de ingeniería inversa útil para replicación en el embudo.
2. `Cierre crítico` sí requiere retrabajo directo.
   - El feedback `no se entiende` invalida la forma actual, no necesariamente el tema.
3. `Kris` no debe seguir flotando como benchmark parcial ambiguo.
   - Ya está `Rechazado`.
   - No necesitaba comentario nuevo; necesitaba regularización semántica y trazabilidad correcta.

## Saneamiento operativo recomendado
Orden sugerido:

1. Traducir cada estado y comentario a una acción concreta en `Tareas`.
2. No reabrir todo el proyecto; trabajar solo sobre los tres entregables ya tocados.
3. Mantener el flujo:
   - `Proyecto -> Tarea -> Entregable -> Revisión`
4. Para `Ruben`, separar claramente:
   - benchmark aprobado
   - nuevo análisis derivado
5. Para `Cierre crítico`, reemplazar o reescribir la pieza hasta que sea entendible y orientada a decisión.
6. Para `Kris`, cerrar semánticamente el rechazo con criterio.

## Prompt corto recomendado
El mejor prompt para probar autonomía real de Rick en este caso fue:

```text
rick, revisa los comentarios que te dejé en los entregables del proyecto embudo y hazte cargo de regularizar ese frente dentro del flujo correcto.
```

## Diagnóstico corto sobre encoding
En las páginas revisadas del embudo (`Ruben`, `Cierre crítico`, `Kris`, `OpenClaw`) no apareció texto corrupto tipo `aprobación?`, `Revisión` rota o similar en bloques o comentarios actuales.

Eso sugiere que el problema de acentos no estaba hoy en estas piezas del embudo, sino en otro frente:
- archivos históricos del repo abiertos con encoding incorrecto desde terminal;
- o alguna otra página o flujo fuera de estos entregables.
