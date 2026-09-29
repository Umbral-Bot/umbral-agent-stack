---
id: "2026-09-29-001"
title: "Piloto supervisado Claude Cloud: verificador de paquetes docentes"
status: assigned
assigned_to: claude
created_by: codex
priority: high
created_at: "2026-09-29T00:52:00Z"
updated_at: "2026-09-29T00:52:00Z"
---

# PKG-UAS-CLOUD-PILOT-01-20260929

## Autorización y alcance
David autorizó expresamente que Codex use Claude Code en terminal para iniciar un piloto supervisado en la nube, medirlo y aprovechar su promoción. Secuencia: (1) verificador docente; (2) coordinación UAS; (3) skills. Este encargo ejecuta SOLO el primer piloto; no inicia otros agentes, sesiones, Rutinas ni Proyectos. Codex coordina por este encargo, aunque el board remoto histórico diga Cursor. No requiere pegado manual adicional.

Repositorio: https://github.com/Umbral-Bot/umbral-agent-stack.git.
Base observada: 97f2d879bf69b6007ab4dded9b4c715c4abc4676.
La rama de preparación codex/cloud-docente-pilot-20260929 contiene este contrato. Trabaja en la rama de sesión que asigne el servicio, sin force-push ni merge a main. Verifica repo/base/contrato al empezar. Lee AGENTS.md, .agents/PROTOCOL.md y board como contexto, sin retomar tareas ajenas.

## Objetivo pequeño y verificable
Crear una utilidad offline y de solo lectura que valide un paquete docente contra un manifiesto CSV (columnas ruta,bytes,sha256) y emita resumen legible y JSON. Evitar nuevas dependencias si la biblioteca estándar basta. Busca brevemente reutilización existente; scripts/maintenance/check_skill_mirrors.py comprueba hashes de texto normalizado, lo que NO sustituye SHA-256 de bytes de materiales.

Implementación propuesta: scripts/validate_teaching_package.py, pruebas tests/test_validate_teaching_package.py, documentación docs/operations/teaching-package-validator.md. Puedes añadir solo fixtures sintéticos pequeños dentro de tests/fixtures/teaching_package/ si aportan claridad.

## Contrato funcional
- CLI: directorio raíz, manifiesto explícito y rol docente/alumno (teacher/student). Leer UTF-8/UTF-8 con BOM, CSV con quoting; SHA-256 sobre bytes reales, por streaming.
- Detectar falta de archivo, tamaño/hash incorrecto, filas malformadas, hash inválido, tamaños inválidos/negativos, rutas duplicadas y archivos extra no declarados. Excluir únicamente el propio manifiesto cuando esté dentro de la raíz. No excluir arbitrariamente documentación o carpetas.
- Rechazar antes de leer payload cualquier ruta absoluta POSIX/Windows/UNC, recorrido .. o enlace simbólico que escape de la raíz; funcionar con separadores Windows y POSIX. No leer contenido exterior para generar hallazgos. Definir y probar política coherente para enlaces internos.
- Modo alumno: detectar archivos docentes por componentes de ruta/nombres convencionales (docente, teacher, solucion, clave) y/o lista explícita de rutas prohibidas. No prometer detección semántica de toda solución. Reportar la regla concreta; tratar nombres ambiguos explícitamente, no inventar certeza.
- Estado global PASS o FAIL para integridad del paquete. La salida debe mantener native_gui=NOT_RUN y student_download=NOT_RUN; integridad no acredita Power BI, Revit, acceso alumno ni sincronización de Drive.
- No modificar originales; no extraer ZIP ni ejecutar scripts del paquete. Salida JSON a stdout o ruta explícita fuera de la raíz, evitando que el informe cambie el inventario. Diagnósticos no deben imprimir el contenido de archivos ni secretos.
- Exit0 paquete válido; exit1 hallazgos; exit2 invocación/configuración inválida. Documentar los límites.
- Datos y pruebas SOLO sintéticos. No acceder a Drive, Notion, correo, materiales reales de alumnos, cuentas empresariales o credenciales.

## Pruebas y entrega
Pruebas positivas y negativas de los criterios anteriores; incluir BOM/quoting/espacios/separadores, duplicados, archivo extra, escape Windows/POSIX, symlink exterior cuando el SO lo soporte, corrupción de hash/tamaño, fuga docente y prueba de que los archivos de entrada quedan byte a byte intactos. Ejecutar suite focalizada; no instalar todo el stack ni levantar Worker/Redis. Ejecutar CLI en un ejemplo sintético sano y uno defectuoso, conservar salidas pequeñas en el informe o documentación. No pruebas que solo repliquen internamente el algoritmo.

Límites: 20 minutos de ejecución desde acceso listo, máximo dos rondas de reparación de pruebas. Si no cabe, entregar estado parcial y checkpoint sin reiniciar reloj. No cambios de facturación, seguridad, despliegue, producción ni ficheros ajenos; no agregar servicios. El coordinador observa saldo, tiempo y presupuesto. No inferir coste o tokens si no se exponen.

Al inicio responder ACK con paquete, UTC, repo, rama, commit base, runtime/Python y modelo/esfuerzo SI son visibles (no adivinarlos). Actualizar esta ficha con checkpoint. Al finalizar: REPORT con estado, UTC de inicio/fin, pruebas/comandos/salidas reales, archivos, límites y SHA del commit. Hacer commit y push de la rama de sesión si está disponible; no crear ni fusionar PR (Codex revisará y abrirá borrador). No afirmar que el saldo promocional se descontó sin evidencia; esa comprobación corresponde al coordinador.

## Plan posterior, sin despacho en este paquete
2. Robustecer coordinación: deduplicación de encargos, contratos/checkpoints y pruebas de transiciones basadas en evidencia.
3. Mejorar skills: detectar contradicciones y verificar contratos con fixtures, tomando como fuente el registry existente.
Se reevalúan después del coste y aceptación de este piloto. No implementar fases2/3 aquí.

## Log
### Codex — preparación
Contrato autónomo, inventario sintético y límites definidos. Material real C26 y sus verificaciones permanecen intactos. CLI local 2.1.280 autenticada claude.ai/firstParty/Max; saldo UI inicial USD250/250, semana66%, sesión1%, créditos de uso desactivados y recarga automática desactivada. La promoción es observada, no cota de coste por tarea.

