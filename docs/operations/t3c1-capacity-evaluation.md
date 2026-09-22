# T3-C1: capacidad observada y propuestas, sin despacho

El evaluador `dispatcher.capacity_evaluator` transforma una instantánea explícita
en un recibo reproducible. No importa clientes de red, Redis, el scheduler ni el
router. Su CLI lee un JSON y escribe el resultado en stdout. No reserva capacidad
real ni crea trabajos: `dispatch_allowed` siempre es `false`, incluso al proponer.

## Uso

```powershell
python -m scripts.evaluate_capacity snapshot.json
python -m pytest tests/test_capacity_evaluator.py -q
```

Un JSON inválido devuelve exit 2 sin volcar su contenido. Una evaluación HOLD/IDLE
válida devuelve exit 0: estar sin trabajo apto no es un fallo de proceso. El recibo
lleva `decision_id` derivado de la instantánea completa y su hora explícita. Repetir
la misma instantánea devuelve el mismo recibo, sin efectos. Cambiar hora, revisión
o evidencia requiere una nueva decisión. No hay caché persistente ni lock: esto
no es deduplicación de un despacho futuro.

## Contratos

`Evaluation` admite solo campos conocidos. Todas las fechas tienen zona horaria;
los números son finitos, no negativos, y no aceptan booleanos o strings. IDs
duplicados de tarea, ruta, bolsa/ventana o compromisos invalidan la instantánea.

- **Observation:** producto, referencia opaca de cuenta, bolsa compartida, ventana,
  unidad/total/restante, origen tool/UI/fixture, confianza, disponibilidad explícita
  y referencia de evidencia. Fechas de observación, recepción, caducidad y reinicio.
- **Route:** correspondencia con producto/cuenta/bolsa, todas las ventanas limitantes
  y certeza de que la relación entre bolsas es conocida. Uso incluido verificado
  por separado. Señales de credencial, permiso, salud, capacidad, host y lease; GUI
  requiere además su propia señal. Un rechazo/429 actual tiene prioridad.
- **Commitments:** foto fechada de compromisos activos por bolsa y cada ventana.
  Cero debe ser observado y explícito; ausencia no significa cero. Costes y
  compromisos se expresan en las unidades de su ventana, sin conversión implícita.
- **Candidate:** dueño, fuente canónica, estado/revisión, autorización, utilidad,
  dependencias listas y cota de coste con evidencia. Un trabajo cerrado se excluye
  antes de evaluar recursos. Estos campos son afirmaciones del productor de la
  instantánea: el evaluador no demuestra por sí mismo su veracidad.

TTL máxima de cuota: cinco minutos desde observación para tool/fixture y quince
para UI, limitada también por `expires_at` y `resets_at`. Leer de nuevo el archivo
no renueva su vigencia. Una fecha de reinicio pasada invalida la cuota, nunca la
rellena. Las señales de ruta y compromisos tienen caducidad explícita que debe
establecer el lector según el ciclo real de su fuente. No reutilizar un preflight
de otro operador ni un éxito anterior a un rechazo posterior.

Para cada ventana: disponible = restante − 20% de reserva mínima − 5% de margen
mínimo − compromisos − propuestas anteriores de la misma bolsa. Nunca sumar
bolsas distintas ni asignar una capacidad por bot. Se comprueban todas las ventanas
conocidas; los conjuntos de ventanas de ruta, observaciones, compromisos y costes
deben coincidir. Una cuota de confianza simulada también bloquea en modo observado,
aunque declare origen tool o UI. Se ordena por entrega,
incidente, pendiente, aprendizaje y plazo, con ID como desempate estable. Se proponen
como máximo tres trabajos; el gasto incremental autorizado sigue siendo cero.

## Lectura nativa y límites de integración

`codex_observations` recibe la respuesta capturada de `get_usage_limits`; no llama
al proveedor. Selecciona únicamente el bucket `codex`, nunca suma `gpt-reserve` ni
créditos. Preserva ventanas faltantes y denegaciones del proveedor. La referencia
de cuenta se aporta sin secretos; no se presume que TARRO y PCRick compartan cuenta.
Una ventana secundaria nula no demuestra que no exista: `windows_complete` queda
a cargo de evidencia adicional. Para Grok/Claude se admite el mismo contrato con
origen UI y fecha original, sin inventar un lector privado ni reutilizar cookies.

El `QuotaTracker` existente continúa sin cambios: mide requests estimadas y su
lectura puede reiniciar contadores en Redis. No se usa como lector de suscripciones.
Tampoco se cambian los routers, fallback, configuración, credenciales o monitores.

Los ejemplos observados son expedientes de evaluación, no otra fuente canónica de
estado. Los resultados se resumen en el ledger de programa existente y Notion.
Una integración posterior podrá registrar recibos en `ops_log.jsonl`; este módulo
no escribe ese log ni sanea su historia. T3-C1 no instala cron o servicios.

## Evaluación de tres pendientes existentes · 22-sep-2026

`examples/t3c1/observed-snapshot.json` y `observed-receipt.json` conservan una
evaluación histórica a las12:12:56UTC. La captura nativa reportó76% restante en
la ventana principal Codex; no es un presupuesto disponible para despachar.
No se conocen aquí todas las ventanas, los compromisos concurrentes ni la relación
con cuentas en otros hosts. Los datos caducaron cinco minutos después: reproducir
el ejemplo usa su hora histórica, nunca acredita cuota actual.

| Candidato existente | Decisión | Siguiente acción |
|---|---|---|
| C24, regresión recibida por Rick | HOLD: ya terminado | Conservar recepción; no repetir GUI. |
| UMB-276, testigo externo | HOLD: dependencia no resuelta | Concretar host/latido/canal independiente y verificar recepción. |
| Registry PR61, mejora Dynamo recibida en TARRO | HOLD: ya terminado | No regenerar; recepción por otros hosts conserva su alcance aparte. |

Resultado IDLE, cero encargos, cero inferencias de prueba. La lectura de cuotas
no representa consumo por las pruebas locales. No se afirma ahorro atribuible:
el porcentaje de uso compartido también puede variar por otros hilos.

## Criterio para el siguiente piloto

Un resultado PROPOSED_ONLY no autoriza ejecución. Antes del único piloto posterior
faltan evidencia actual de cobertura/testigo externo, presupuesto y reserva de
admisión atómica, idempotencia durable y recuperación del ejecutor. UMB-276 sigue
abierto. La distribución 60/20/20 es una intención de cartera; aquí se impone la
reserva mínima, no una cuota obligatoria de gasto ni un reparto temporal 60/20.
