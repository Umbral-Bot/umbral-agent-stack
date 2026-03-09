# Modelo de estado de fuentes

## Registro minimo de fuentes
Persistir, como minimo:
- identificador de fuente
- nombre
- tipo de autoridad
- topics cubiertos
- metodo de acceso
- patron de captura
- estado actual
- motivo del estado
- owner editorial
- fecha de ultima revision
- fecha de proxima revision

## Definir viable
Marcar `viable` cuando exista acceso estable, formato parseable, relevancia sostenida y riesgo legal aceptable.

Consecuencia operativa:
- captura automatica normal
- monitoreo y revision periodica

## Definir parcial
Marcar `parcial` cuando la fuente tenga valor pero tambien friccion relevante:
- estructura irregular
- metadatos pobres
- paywall o autenticacion fragil
- indisponibilidad frecuente
- ruido alto
- limpieza manual recurrente

Consecuencia operativa:
- bajar peso o frecuencia
- exigir chequeos extra o revision humana

## Definir bloqueada
Marcar `bloqueada` cuando no deba automatizarse la captura:
- restricciones legales o de TOS
- anti-bot o bloqueo tecnico
- fiabilidad insuficiente
- falta de permiso editorial o de compliance

Consecuencia operativa:
- excluir de la captura automatica
- permitir solo seguimiento manual si aporta contexto

## Dictamen trazable
Cada clasificacion debe incluir:
- `status`
- `status_reason`
- evidencia o sintoma observado
- consecuencia operativa
- accion siguiente
