# Ensayar alertas sin modificar su estado productivo

`UMBRAL_ALERT_DRY_RUN=1` simula la entrega de alertas. No realiza su POST al Worker
y no lee el archivo de entorno ni carga sus credenciales. Las escrituras de
estado, latidos, captura y registro se fuerzan a un sandbox, aunque el entorno
heredado contenga rutas productivas. Una alerta simulada nunca compra silencio
para el siguiente ciclo de producción.

Al cargar la biblioteca se crea un directorio temporal nuevo. Para ensayar
varios pasos sobre la misma máquina de estados se puede definir explícitamente
`UMBRAL_ALERT_DRY_RUN_DIR` fuera de las rutas de producción. Sus salidas son:

- `monitor/`: estado de alertas y latidos simulados.
- `ops/ops_log.jsonl`: eventos del ensayo.
- `notificaciones-simuladas.jsonl`: mensajes que se habrían enviado.

Las rutas antiguas `UMBRAL_MON_STATE_DIR`, `UMBRAL_OPS_LOG_DIR` y
`UMBRAL_ALERT_CAPTURE` se sustituyen dentro del proceso de ensayo. Un sandbox
que se solape con producción, o con enlaces de salida, se rechaza antes de
escribir allí. El modo `fallo` simula una entrega fallida sin abrir silencio.

**Alcance:** este es el modo de prueba de **alertas**, no un health-check offline.
Si se ejecuta `health-check.sh`, sus comprobaciones HTTP/Redis y su inferencia
canaria siguen siendo reales. Para pruebas sin proveedores reales se usan los
tests con stubs. El estado simulado no se mezcla con el registro canónico y no
acredita una ventana productiva del gate.

Una variable definida y vacía permanece vacía al cargar el entorno en modo
normal. El archivo de entorno no puede encender ni apagar el modo de prueba.
