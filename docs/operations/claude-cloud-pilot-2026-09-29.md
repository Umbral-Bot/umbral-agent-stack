# Piloto supervisado Claude Code cloud — 29-sep-2026 UTC

Estado: implementación del piloto 1 aceptada tras revisión independiente; sin merge ni despliegue. Primera entrega requirió cambios. Las fases 2 (coordinación UAS) y 3 (skills) son siguientes en ese orden, no ejecutadas por este paquete.

## Encargo y transporte

- Autorización: David pidió ejecutar desde terminal una prueba supervisada de la promoción, medirla y después seguir la secuencia propuesta.
- PKG-UAS-CLOUD-PILOT-01-20260929; sesión https://claude.ai/code/session_01BzLY3ZVrhRvW6hYznaDxcv.
- Claude CLI 2.1.280, autenticación claude.ai/firstParty/Max, nube Linux Python 3.11.15; revisión local Windows Python 3.13.7/pytest9.1.1.
- Contrato b4d0622f3dfbc81575e2703c5abf9e43762f40b4; primera entrega 6fee367fc9c2dc09ca19593145c133fd490680dd; reparación 9b934f1f6242e691b26853de28fcb9c1e5d2f591.
- Creación con --cloud necesitó PTY. Primer intento con pipes falló explícitamente antes de crear sesión; segundo creó una sola sesión tras confianza de la carpeta. Seguimiento con -p MENSAJE --cloud SESSION_ID funcionó y reutilizó esa sesión.
- Modelo solicitado y observado: Opus 5.5. Esfuerzo solicitado: high. Selector de nube observado: Medio; el agente remoto no lo tenía expuesto. No afirmar high efectivo.
- Git Windows necesitó core.longpaths local al repositorio para preparar el worktree. No se cambió configuración global ni permisos.

## Mediciones

| Dato | Resultado y alcance |
|---|---|
| Inicio remoto declarado | 00:54:09Z |
| Primer push declarado | 00:58:06Z; 3m57s desde inicio |
| Corrección remota declarada | 01:00:40Z a 01:02:13Z; 1m33s |
| Inicio a segundo push | 8m04s, incluye espera por revisión; no es tiempo activo medido |
| Límite original | 20min; dos rondas permitidas, una usada |
| Saldo antes/después visible | USD250 → USD248, caída mostrada de USD2; UI redondeada, no coste exacto por sesión |
| Uso de sesión del plan | 1% → 2%; bolsa compartida, no atribuir entero a este piloto |
| Uso semanal | 66% antes y después a precisión UI |
| Contexto UI al finalizar | 105.9k / 1M (11%); ocupación de contexto, no tokens facturados |
| Gasto adicional / recarga | Desactivados, sin cambios |
| Facturación exclusiva a promoción | Promoción disminuyó durante piloto; no existe cota credit-only comprobada ni desglose exacto por sesión |

La cuenta tenía otra sesión listada esperando entrada. La variación del saldo es observación de cuenta durante la ventana y no una atribución contable perfecta. No se usó API key ni se habilitó gasto adicional. No hay coste de cómputo, tokens de entrada/salida/cache o tiempo activo remoto desglosados disponibles. La ficha remota anotó un fin estimado 01:02:30Z antes del push; su REPORT corrigió a 01:02:13Z, conservado como declaración del ejecutor.

## Revisión independiente y corrección

Primera entrega: Claude reportó Linux 24/24 PASS. Windows dio 20 PASS, 2 FAIL y 2 SKIP: colisión a.txt/A.TXT en filesystem insensible y fixtures alterados por core.autocrlf. Codex reprodujo además tres fallos con datos sintéticos: junction fuera de raíz devolvía PASS y leía un payload exterior; enumeración con PermissionError devolvía PASS incompleto; salida JSON exterior enlazada por hardlink sobrescribía el input y devolvía exit0.

Una ronda corrigió los cinco casos: fixture portable y atributos Git limitados a sus bytes; detección de junction/name-surrogate sin bloquear por esa sola razón placeholders regulares; enumeración que falla si es incompleta; salida JSON por creación exclusiva, sin sobrescribir archivos existentes ni aliases de inputs.

Verificación final:
- Windows real: 35 PASS / 3 SKIP, 38 casos recogidos; se ejecutó la regresión de junction real. Los tres omitidos corresponden a symlinks POSIX.
- Linux remoto: 37 PASS / 1 SKIP según REPORT; omitido junction Windows. No sumar plataformas como pruebas únicas.
- Codex repitió sus tres contrapruebas: junction FAIL con cero archivos exteriores hasheados; inventario incompleto FAIL; hardlink de salida exit2 y input abc intacto.
- Los fixtures viejos del checkout CRLF se preservaron fuera del paquete antes de materializar los blobs de nuevo con los atributos corregidos. Un pull que solo agrega atributos puede dejar bytes viejos en un checkout existente; no confundir esto con un fallo de hash normalizado ni modificar materiales reales.
- Solo biblioteca estándar para la CLI; pytest instalado en venv scratch de nube. No Worker/Redis ni APIs externas, Drive, cuentas empresariales o materiales de clase usados por el piloto.

## Aceptación y límites

El verificador acredita integridad de bytes/manifiesto y reglas explícitas de nombres. Mantiene native_gui=NOT_RUN y student_download=NOT_RUN. No acredita Power BI, Revit, acceso de alumno, sincronización Drive ni detección semántica completa de soluciones. Validar copias estables: la carrera concurrente entre inspección y lectura sigue documentada. Estado de producción y material C26 intactos.

## Secuencia autorizada siguiente

2. Coordinación UAS: partir del código vigente, claims/checkpoints existentes y sus pruebas; reproducir un fallo concreto antes de cambiar. Contrato separado, una rama/sesión acotada, sin dispatch real ni servicios; probar duplicados, reanudación y aceptación solo con evidencia correspondiente al artefacto. No crear otro scheduler por disponibilidad de créditos.
3. Skills: después de 2, incorporar hallazgos comprobados a la fuente canónica y sus verificaciones/mirrors; distinguir selección solicitada de runtime observado, transporte emitido de ACK y resultado de aceptación. No declarar una instalación/carga remota solo por editar archivos.

Estas fases requieren su propia admisión basada en saldo vigente y contrato; no heredan el PASS del piloto ni autorizan despliegue o gasto adicional.
