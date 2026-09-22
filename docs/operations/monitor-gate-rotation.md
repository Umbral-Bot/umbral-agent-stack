# Verificar una ventana conservada tras rotación

El gate lee el registro activo y los archivos rotados como una sola instantánea
ordenada. No genera canarios, avisos, eventos ni modificaciones de producción.
El inicio automático se obtiene del último `release_deploy` real para el SHA pedido.

```bash
python3 scripts/vps/verify_monitor_gate.py --autoprueba
python3 scripts/vps/verify_monitor_gate.py \
  --ops /ruta/ops_log.jsonl \
  --archive /ruta/archivo/ops_log.jsonl.1.gz \
  --release SHA_COMPLETO
```

Repetir `--archive` para otros archivos externos. Rotados adyacentes con sufijo
numérico, con o sin `.gz`, se descubren automáticamente. No se carga un archivo de
entorno para encontrar rutas. El informe incluye nombres, tamaños y SHA-256 de las
fuentes leídas, además de solapes eliminados. Un archivo explícito ausente,
corrupto, con JSON inválido o que cambia durante su lectura impide el veredicto.

La deduplicación elimina copias exactas **entre fuentes** y conserva la mayor
multiplicidad en una fuente: dos avisos idénticos registrados en el mismo archivo
no desaparecen. Eventos diferentes en el mismo instante tampoco se colapsan.

La versión inicial existía solo como evidencia de un paquete. El 20-sep-2026
produjo `NO_SUPERADO` porque buscaba el despliegue únicamente en el registro
activo, después de que la rotación trasladara el inicio de la ventana al gzip.
La evaluación corregida debe guardarse como adenda, conservando aquel resultado;
no se añade un despliegue ficticio ni se reinicia el reloj por un fallo del lector.

Un PASS acredita exclusivamente la ventana indicada. No cierra incidentes,
no prueba salud posterior y no activa despacho proactivo. Los criterios de salud
y cadencia de la versión inicial se conservan; el origen cron sigue inferido por
su intervalo temporal, no por una identidad explícita del emisor.

Pruebas sin red:

```bash
python -m unittest discover -s tests -p test_monitor_gate_rotation.py -v
```
