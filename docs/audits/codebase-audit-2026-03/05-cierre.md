# Cierre de Auditoria — Umbral Agent Stack

**Fecha:** 2026-03-05
**Revisor:** Claude (Sonnet 4.6 + Opus 4.6)
**Branch:** `claude/090-implementar-notion-bitacora`

---

## Ambito

Se audito el repositorio completo `umbral-agent-stack`: worker/ (Execution Plane, FastAPI), dispatcher/ (Control Plane, Redis), client/, infra/, config/, scripts/ (60+), tests/ (866+ tests), y archivos de entorno. La revision cubrio estructura, bugs funcionales, seguridad, y mejoras arquitectonicas.

## Hallazgos mas importantes

**Bugs criticos (P0):** 3 raices, 4 bugs. Los handlers sincronos bloquean el event loop de asyncio impidiendo toda concurrencia (bugs #1/#2). El retorno de `sanitize_input()` se descarta, dejando inputs sin sanitizar (bug #3). Tareas se pierden silenciosamente si el key Redis expira entre BRPOP y GET (bug #4).

**Seguridad critica:** 3 hallazgos. Dos handlers de Windows pasan input HTTP directamente a comandos del sistema (`schtasks`, `netsh`) sin validacion (SEC-10, SEC-11). El WORKER_TOKEN se escribe en archivo de texto plano en la VM (SEC-1).

**Seguridad alta:** 5 hallazgos. Comparacion de token no es timing-safe (SEC-7). `config.py` sobreescribe todo `os.environ` desde archivo externo sin whitelist (SEC-4). Username de input construye paths del sistema sin validacion (SEC-12). IPs Tailscale de produccion en `.env.example` (SEC-2). Notion DB ID hardcodeado en scripts (SEC-3).

**Deuda estructural:** El worker depende circularmente del dispatcher (5 imports inline que fallan en deploys minimos). El rate limiter tiene dos implementaciones con dos env vars distintas. El evento `task_queued` nunca se emite, dejando un punto ciego en observabilidad. El in-memory task store se pierde en cada reinicio.

## Top 5 acciones recomendadas

1. **Aplicar retorno de sanitize_input + hacer _check_injection defensivo** (QW-1). Fix de 1 linea que cierra un P0 y un hallazgo de seguridad. Impacto inmediato en cada request.

2. **Envolver handlers en run_in_executor** (M-1). Elimina el bloqueo total del event loop (P0 #1/#2). Sin esto, una sola tarea lenta paraliza el servidor entero.

3. **Validar inputs en handlers de Windows** (QW-3). Cierra los 3 hallazgos de seguridad criticos/altos de command injection. Requiere solo un helper de validacion y aplicarlo en 3 puntos.

4. **Proteger tareas ante TTL expiry** (M-3). Evita perdida silenciosa de tareas (P0 #4). Incluir campos criticos en el item de cola para recuperacion.

5. **Timing-safe auth + limpiar .env.example** (QW-2 + QW-4). Dos cambios rapidos que cierran 4 hallazgos de seguridad (SEC-7, SEC-2, SEC-3, SEC-5).

## Proximos pasos

- **02-bugs.md:** Crear issues (Linear o GitHub) para los 4 bugs P0 y los 8 P1. Los P0 deben resolverse antes de cualquier deploy a produccion con carga real.
- **03-seguridad.md:** Ejecutar los 6 quick wins de seguridad en una sola sesion. Programar `pip-audit` en CI como primer paso de hardening continuo.
- **04-mejoras-estructurales.md:** Usar como backlog de sprint. Los 6 quick wins son candidatos para el proximo sprint; los 6 de mediano plazo cubren las siguientes 2 semanas.

---

## Checklist de seguimiento

**Inmediato (esta semana):**

- [ ] Corregir bug #3: `envelope.input = sanitize_input(envelope.input)` en `app.py:237` y `/enqueue`
- [ ] Corregir bug #9 / SEC-7: `hmac.compare_digest` en `app.py:183`
- [ ] SEC-11: validar `name` con allowlist en `windows.py` handler firewall
- [ ] SEC-12: validar `username` con allowlist en `windows.py` handler startup
- [ ] SEC-10: eliminar `run_as_password` como input HTTP; leer de env var
- [ ] SEC-2: reemplazar IPs Tailscale en `.env.example` con placeholders
- [ ] SEC-3: eliminar default hardcodeado de Notion DB ID en scripts
- [ ] SEC-5: agregar `LINEAR_WEBHOOK_SECRET` a `.env.example`
- [ ] Bug #5: emitir `ops_log.task_queued()` en endpoint `/enqueue`
- [ ] Bug #13: unificar rate limiter (eliminar `rate_limit.py` o `WORKER_RATE_LIMIT_PER_MIN`)

**Corto plazo (proximas 2 semanas):**

- [ ] Bugs #1/#2: envolver handlers sincronos en `run_in_executor`
- [ ] Bug #4: proteger dequeue ante TTL expiry (log + callback de fallo)
- [ ] Bug #6: envolver imports de `dispatcher.*` en try/except con 503
- [ ] Bugs #8/#14: Lua scripts atomicos para block_task y quota window reset
- [ ] SEC-15: generar lock files y agregar `pip-audit` a CI
- [ ] SEC-8/SEC-9: auth logging + rate limit por IP en fallos de auth

**Mediano plazo (1-2 meses):**

- [ ] Desacoplar worker/dispatcher en paquete compartido (M-2)
- [ ] Auth multi-nivel con scopes y rotacion (G-1)
- [ ] Worker async nativo + Redis Streams (G-2)
- [ ] Observabilidad Langfuse end-to-end (G-3)
- [ ] Containerizacion con CI/CD (G-4)

---

## Correcciones o notas de consistencia

1. **Conteo P0 en 02-bugs.md:** La tabla resumen dice "P0 count = 3" pero lista 4 numeros de bug (#1, #2, #3, #4). Esto es porque bugs #1 y #2 comparten la misma raiz (R3: sync handlers bloquean event loop) y se contaron como un solo problema. El conteo es correcto conceptualmente (3 problemas raiz), pero podria confundir al lector. El texto de `00-progreso.md` lo aclara agrupandolos como "event loop bloqueado".

2. Todas las demas referencias cruzadas entre documentos son correctas: los numeros de bug en `04-mejoras` coinciden con `02-bugs`, los IDs SEC-* coinciden con `03-seguridad`, y los riesgos R1-R10 de `01-mapa` se alinean con los origenes de bugs en `02-bugs`.
