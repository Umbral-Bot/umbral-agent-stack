# REPORT PKG-DIHR-COMPARATIVA-01 — sesión «Auditoría de comparativa ciega de asistentes» (Remote Control, bypass; equipo PCRick declarado)
Recibido por cross-session-message en «Control remoto de hilos Claude Code», 2026-11-09 ~05:45Z. Texto del emisor; no verificado por el coordinador salvo donde se indique.

ACK PKG-DIHR-COMPARATIVA-01 | sin rama (paquete solo lectura, sin git) | base 46aa07c (main local, behind origin/main; no tocado)

(1) Protocolo y documentos que rigen
- Protocolo V3, preparado 2026-11-04 (UTC). Raíz Drive "Benchmark agentes 2026-11-04": https://drive.google.com/drive/folders/1looehfycFx9rvzQvOLuy5l4Qnp0Rh3ux
- Coordinación privada (no entregar al juez): carpeta 1CXIBz_T…(id truncado). Docs: "01 Protocolo y coordinación — benchmark 2026-11-04" (mod. 2026-11-05T00:32Z), "02 Fuentes mínimas y estado" (mod. 2026-11-05T00:32Z), "03 Referencias reservadas y eventos futuros — NO PARTICIPANTES" (mod. 2026-11-04T23:40Z).
- Paquete exclusivo del juez: https://drive.google.com/drive/folders/1zNX6a55ZJyfRkaFyaHmocvQyiFxC0n6n con "01 Instrucciones y rúbrica", "02 Pruebas y manifiesto de ejecución", "03 Prompt definitivo Claude Code — juez ciego" (los tres mod. 2026-11-04T23:22Z). Rúbrica: completitud 20, exactitud 20, honestidad 15, seguimiento 15, herramientas 10, permisos 10, frescura 5, recuperación 5; escala 0-5 o NO_EVALUABLE.
- Entradas de participantes: carpeta 1A6hHWxI…(id truncado). Banco sintético PREP-1A5A33DE5266 rev. 2, 12 casos (4 por familia C1/C2/C3), congelado 2026-11-04T23:38:31Z con SHA-256 por caso en el doc 02 de coordinación.

(2) Pruebas reales vs sintéticas
- Todos los casos son SINTÉTICOS por diseño (declarado en cada doc). No hay caso real inédito aprobado; Azure sigue excluido por exposición previa.
- Pruebas realmente ejecutadas: un pre-ensayo del 2026-11-05 FUERA del protocolo (sin run_id, T0, sorteo, fase, presupuestos ni trazas). Existen 4 piezas en la carpeta de recepción 1xK6vmAj…(id truncado): una respuesta a C1-V1, una a C2-V2, una a C2-V3 y una revisión de esa última por el otro candidato. Subidas por la cuenta del operador entre 01:43 y 03:31 UTC. Autoría reportada por nombre de archivo, no verificada. Ningún bloque tiene a ambos candidatos sobre el mismo caso: comparación competitiva imposible.
- Continuidad (C3): existe un archivo de prueba de continuidad creado 2026-11-05T04:48Z y modificado 2026-11-06T17:39Z (cambio observable a +36,8 h) y un doc "PRUEBA DESECHABLE" del 2026-11-05. Ningún candidato dejó salida. C3 = NO_EVALUABLE.
- P5 transporte, P6 recuperación, P7 concurrencia: sin evidencia de ejecución.
- Casos ya expuestos (solo regresión en adelante): C1-V1, C2-V2, C2-V3. Sin exposición registrada: C1-V2/V3/V4, C2-V1/V4, C3-V1..V4 (con transferencia de aprendizaje declarada por estructura compartida).

(3) Preparado para el juez
- Subcarpeta R1_Paquete_regresion_2026-11-09 (id 1iH72pO_fPH998vbtTXQ4qPF2zEQycr37) dentro del paquete del juez, creada 2026-11-09T03:01Z. 14 archivos txt: manifiesto real, matriz de conformidad con V3, registro de exposición/contaminación, trazas (inexistentes; autodeclaraciones listadas), versiones y hashes, 3 enunciados, 4 piezas anonimizadas con códigos opacos aleatorios por bloque y orden aleatorio, prompt para sesión juez, plan mínimo de faltantes.
- Correspondencia de códigos en coordinación privada: "CORRESPONDENCIA_CODIGOS_R1_2026-11-09_NO_ENTREGAR_AL_JUEZ.txt" (id 144VGO…(id truncado por el coordinador; archivo NO_ENTREGAR_AL_JUEZ)).
- Originales intactos; hashes SHA-256 de originales y anonimizados registrados; verificación byte a byte de una pieza subida; comprobación automática de fugas de nombres = 0.
- Cumple: casos congelados antes de ejecución, sintéticos identificados, originales conservados, anonimización y orden aleatorio, registro de exposición. No cumple: enunciado idéntico para ambos candidatos, sorteo congelado, manifiesto con run_id/T0/corte, fase declarada, presupuestos, tiempos de extremo a extremo, inversión de roles, trazas separadas, continuidad 72 h. No verificable: congelación previa a revisión, autoría.
- Evaluación de regresión ya realizada el 2026-11-09 por una sesión juez independiente (Claude Code, fresca, solo lectura): modelo claude-fable-5-1, esfuerzo "high" (ultracode no disponible ni verificable). Resultado: las 5 piezas PARCIAL sin fallo crítico; C3 NO_EVALUABLE; sin ganador ni comparación.

(4) Bloqueado / pendiente / decisiones de David
- Bloqueado: modo ultracode (no seleccionable ni verificable; se trabajó en "high"). Aislamiento técnico del juez (misma cuenta de Drive; solo procedimental). Comparación entre candidatos (sin pares de respuestas).
- Pendiente del plan mínimo (archivo 91 del paquete R1): sorteo congelado de variantes no expuestas a celdas fase A/B × rol; manifiesto real con run_id, T0_UTC, corte, presupuesto y herramientas autorizadas; entrega simultánea con registro de tiempos independiente del candidato; trazas por candidato en archivo separado; congelación de ejecuciones antes de revisión y revisión solo sobre piezas anonimizadas; T0 formal y responsable de liberar el evento para C3; para completar la matriz C2 faltan al menos 2 variantes nuevas congeladas.
- Decisiones de David que faltan: (a) aceptar evaluación en esfuerzo "high" declarado, o esperar ultracode; (b) mecanismo de aislamiento: copia a cuenta/unidad separada vs. aceptar aislamiento procedimental declarado; (c) autorizar el sorteo y el T0 de la primera comparación inédita; (d) vía de transporte a los participantes. Nada de esto se ha iniciado.

(5) Equipo, cuenta y accesos
- Equipo: PCRick (Windows 11), sesión Claude Code en C:\Github\umbral-agent-stack, modelo claude-fable-5-1, esfuerzo "high", permisos bypass en la sesión de preparación; la sesión juez hija corrió con permisos por defecto.
- Cuenta: conector Google Drive de la cuenta personal de David (propietaria de toda la carpeta del benchmark). No se accedió a TARRO. No se usaron credenciales adicionales, Notion, correo, Slack ni VPS.
- Accesos usados: lectura de Drive, creación de 15 archivos txt y 1 carpeta en Drive (R1 + correspondencia), scripts locales en scratchpad para hash y anonimización. Sin compartir, mover, editar ni borrar nada preexistente. Sin git.

ESTADO_COMPARATIVA = PARCIAL [E] 5 piezas de regresión puntuadas 2026-11-09; 0 bloques comparables; C3 NO_EVALUABLE.
TU TURNO: 1) David decide (a) y (b) del punto 4. 2) Con eso, autorizar sorteo + T0 de la primera comparación inédita.
