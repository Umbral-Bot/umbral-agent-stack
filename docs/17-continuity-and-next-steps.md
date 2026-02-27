# 17 — Continuidad y próximos pasos (post-Antigravity S0–S3)

> Fecha: 2026-02-27  
> Contexto: Implementación S0/S1/S2 (y parte S3) con Antigravity; decisión de **testear antes de seguir**. Resumen de la conversación y recomendación de cómo continuar.

---

## 1. Resumen de lo hecho con Antigravity

| Sprint | Estado | Qué hay |
|--------|--------|---------|
| **S0** | ✅ | Normalización, plan maestro v2.8, ADRs, arquitectura, roadmap S0–S7 |
| **S1** | ✅ | TaskEnvelope v0.1 en código, Worker acepta envelope + legacy, tests |
| **S2** | ✅ | Dispatcher (queue Redis, HealthMonitor, TeamRouter), service loop, script `test_s2_dispatcher.py` |
| **S3** | 🟡 En medio | Equipos + Notion operativo — **pausado para testear** |

Decisión explícita en la conversación: *“testear antes de continuar”* — validar E2E (VPS + Redis + Dispatcher + VM Worker) y luego seguir con S3 y siguientes.

---

## 2. Estado real VPS y VM (de la conversación)

### VPS (Hostinger, usuario `rick`)

- **OpenClaw**: instalado (npm global), Telegram configurado.
- **Redis**: instalado y corriendo (`redis://localhost:6379/0`).
- **Repo**: en un momento **no** estaba clonado (Git auth falló con HTTPS y SSH). Luego se usó **`update.zip`** (dispatcher + scripts) copiado por `scp` y descomprimido en `~/umbral-agent-stack`, por lo que en la VPS puede haber **carpeta sin `.git`** (solo archivos sueltos). Eso explica `fatal: not a git repository` al hacer `git pull` desde `~` o desde `~/umbral-agent-stack` si esa carpeta salió del zip.
- **Dispatcher**: llegó a correr (`python3 -m dispatcher.service`), HealthMonitor OK, cola Redis, y `test_s2_dispatcher.py` completó con resultado mock (`llm_only_vps`). Es decir: flujo Dispatcher → Redis → (mock local) funcionó; no se validó aún Dispatcher → **Worker real en VM** en esa sesión.

### VM Windows (Execution Plane)

- **Worker**: escucha en `0.0.0.0:8088`, accesible por Tailscale (ej. `100.109.16.40:8088`). En la conversación se levantó manualmente con `WORKER_TOKEN=test-token-12345` y `uvicorn worker.app:app`.
- **Servicio NSSM** (`openclaw-worker`): existe; no está claro si en la VM está actualizado con el código modular (`worker.app:app`) y el mismo token.

### Tu máquina Windows (donde hablas con Cursor)

- Repo en `C:\GitHub\umbral-agent-stack` con `main` al día. Aquí sí hay `.git`, pytest y todo el código.

---

## 3. Cómo puedo “auditar” VM y VPS

Yo (Cursor) **no tengo acceso directo por SSH** a tus máquinas. Solo trabajo sobre el workspace que tenés abierto en Cursor (y la terminal asociada a ese workspace). Por eso:

### Opción A — Conectarte y que yo “trabaje” en cada entorno (recomendada si podés)

1. **VPS**: En Cursor, **Remote-SSH** al VPS (ej. `rick@187.77.60.169` o la IP Tailscale) y abrí la carpeta `~/umbral-agent-stack` (o `~` si el repo está en home).  
   En esa ventana, la terminal que uses será **en la VPS**. Yo te voy pidiendo comandos (por ejemplo `git status`, `systemctl --user status openclaw`, `redis-cli ping`, `ls ~/umbral-agent-stack`) y podés pegarlos ahí; con eso hago la auditoría del estado real del VPS.

2. **VM**: Igual: si abrís Cursor en la VM (o Remote-SSH a la VM) con el repo o la carpeta del worker, la terminal será de la VM y puedo auditar qué hay instalado, si el servicio NSSM está con el módulo correcto, si el worker responde, etc.

Así “me conectás” en el sentido de que **el contexto de Cursor es esa máquina**; yo no ejecuto SSH por mi cuenta.

### Opción B — Vos (o Antigravity) ejecutá scripts y pegá resultados

Yo preparo un **runbook de auditoría** (lista de comandos para VPS y para VM). Vos o Antigravity los corren en cada máquina y pegan la salida en el repo (por ejemplo `docs/audits/vps-YYYY-MM-DD.txt` y `docs/audits/vm-YYYY-MM-DD.txt`). Yo leo esos archivos y armo el plan (estado actual, drift, P0/P1/P2).

---

## 4. Recomendación de orden para continuar

Dado tu objetivo (testear antes de seguir; luego S3, S4… y tu intención Rick / equipos / multi-modelo / lab), el orden que te recomiendo. **Objetivo de tiempo: 2–5 días** (14 días solo como techo si algo se complica).

1. **Auditar una vez VM y VPS**  
   - Con **Opción A**: abrís Cursor en VPS y en VM por turno y yo te guío con comandos.  
   - Con **Opción B**: ejecutás el runbook de auditoría y subís las salidas al repo.

2. **Documentar estado y drift**  
   - Un doc corto (o actualizar este): “Estado VPS” y “Estado VM” (qué está instalado, qué corre, si hay `.git` en el repo del VPS, versión del worker en VM, etc.) y **drift** respecto al repo (docs/scripts que ya marcamos en la auditoría Codex, doc 16).

3. **Dejar VPS con repo real por Git**  
   - Configurar en la VPS acceso a GitHub (PAT o SSH key) y hacer **clone** (o `git init` + `remote add` + `pull` si ya tenés carpeta del zip). Así `git pull` en la VPS es la fuente de verdad y no dependés del zip.

4. **Cerrar P0 de la auditoría (doc 16)**  
   - Token en `deploy-vm.ps1` (no dejar `test-token-12345` en producción).  
   - Si usás S1 en producción: que `test_s1_contract.py` use env o config para URL/token (no hardcodeados).  
   - (Opcional pero útil) Dispatcher enviando envelope completo al Worker y arreglar filtro `team` en GET `/tasks` — son P1 pero mejoran trazabilidad.

5. **Re-ejecutar el test E2E “real”**  
   - En VPS: Redis + Dispatcher corriendo, `WORKER_URL` apuntando a la VM por Tailscale, `WORKER_TOKEN` coherente con la VM.  
   - En VM: Worker corriendo (servicio o manual) con el mismo token.  
   - En VPS: `python3 scripts/test_s2_dispatcher.py` con `team=improvement` (o el que requiera VM) y confirmar que la tarea se ejecuta **en la VM** y el resultado vuelve por Redis (no mock).  
   - Dejar eso documentado (por ejemplo en este doc o en un runbook “Validación S2 E2E”).

6. **Plan corto (objetivo: 2–5 días; 14 días como techo si algo se complica)**  
   - Con el estado y drift ya documentados, armar el plan P0/P1/P2 usando doc 16 + hallazgos de las auditorías VM/VPS.  
   - Reanudar **S3** (equipos + Notion) con la base estable y testeada.

---

## 5. Próximo paso concreto

- Si elegís **Opción A**: la siguiente acción es abrir Cursor contra la VPS (Remote-SSH a `rick@...`) con la carpeta del repo (o home) y decirme “listo, estoy en la VPS”; yo te paso los primeros comandos de auditoría y vamos anotando.
- Si elegís **Opción B**: decime “prepará el runbook de auditoría” y te dejo en el repo un `docs/runbooks/audit-vps-vm.md` (o similar) con los comandos para cada máquina; cuando tengas las salidas, las subís y yo armo el estado + plan.

En ambos casos, el resultado será: **estado claro de VPS y VM**, **plan priorizado** alineado con tu intención, y una base estable para seguir con S3 y lo que siga.
