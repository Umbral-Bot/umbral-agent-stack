# Sweep de higiene: VPS canónico + VM (2026-08-10)

> **Pack:** PKG-UAS-HYGIENE-SWEEP-VPS-VM · rama `claude/pkg-uas-hygiene-sweep-vps-vm-20260810` ·
> base `b897446` (`origin/main`, tip = PR #619)
> **GO citado:** David 2026-08-10 — "higienizar VPS + revisar VM (merge/higiene)". Cursor ya
> limpió origin (10 pack-heads killed, confirmado por el `fetch --prune` de este pack) y
> avanzó los clones Windows a `b897446`.
> **Evidencia:** `~/.coord-ag-evidence/uas-hygiene-sweep-vps-vm-20260810/`

## Fase A — VPS canónico

### A1/A2 — main y origin

`main` local = `origin/main` = `b897446` (contiene #619). `git ls-remote --heads origin`:
**exactamente 2 heads** — `main` + `rick/stage7_5-multiformat` (intacta, no tocada). Cero
kills remotos necesarios (Cursor ya lo había hecho; el prune local de este pack solo
absorbió esos deletes).

### A3 — Ramas locales: 226 → 191

| Clase | N | Acción |
|---|---:|---|
| MERGED (tip ancestro de `origin/main`) | 25 | **DROP** — inventariadas una a una en evidencia (`a3-drops.txt`) antes de borrar |
| Packs `claude/pkg-*` + `claude/rescue-notion-poller-*` con tracking gone | 10 | **DROP** — cada una verificada contra su PR mergeado vía `gh` (#610–#619, #611) antes de borrar |
| Tips no alcanzables desde main (squash-históricas + WIP viejos, mar–jul) | 189 | **KEEP** — criterio del pack: no destruir UNIQUE sin evaluación individual; inventario completo en `a3-branches-{before,after}.txt` |

(191 = 189 KEEP + `main` + la rama de este pack.)

### A4 — Worktrees: 2, ambos legítimos

Solo el canónico + `rick-delivery/umbral-agent-stack-poller-hardening` (limpio, con 5+
commits propios no en main → **KEEP** como indica el pack). Los de `/tmp` y `archive/uas`
ya no existen (packs previos).

### A5 — Stashes: 17/17 KEEP, 0 drops nuevos

Los 17 re-listados con stat: ninguno vacío, ninguno volvió redundante con el avance de
main #610–#619 (esos PRs no tocaron los archivos de estos stashes). Mismo veredicto del
closeout: WIP real (stage7_5 copywriter, discovery, html_to_notion_blocks, tests,
task-docs). Tabla en `a5-stashes.txt`.

### A6 — Confirmaciones runtime (todas ✓)

| Check | Estado |
|---|---|
| `~/archive/uas` ausente | ✓ |
| `HEARTBEAT.md` live rick-tracker con prohibición Notion, md5 = repo-override | ✓ (`f885419b…`) |
| Crons dashboard/panel `+x` | ✓ |
| gateway / dispatcher / worker / mission-control | ✓ 4× active, sin restarts |
| Panel: residual live | 5 = 4 contenido + 1 heartbeat de hoy (matchea prefijo, cae en el próximo refresh). El `residual=20` que mostraba el log de las 12:20 se drenó después vía el trigger reactivo del panel. |

### A7 — Verify heartbeat (bono): 1 de 2 ciclos, señal mixta

El edit de `HEARTBEAT.md` aterrizó ~16:47 UTC. **Ciclo 17:33 UTC: el heartbeat PUBLICÓ
una página igual** (con la instrucción nueva ya en el prompt) — señal temprana de que el
hábito de la sesión persistente (`bd35d75c…`, ~100 publicaciones en su historial) compite
con la instrucción, exactamente el escenario del plan B del acta #619. Report local OK.
Criterio del acta = 2 ciclos; el segundo (18:33 UTC) quedaba fuera de la ventana de este
pack. **Plan B (compactar/rotar la sesión) NO ejecutado** — 1 ciclo no es evidencia
suficiente y el pack lo exige claro; queda armado para el siguiente turno si el ciclo 2
también publica. Mientras tanto el cleanup del panel archiva cada ocurrencia.

## Fase B — VM

### B1 — Identificada

**`pcrick`** — `100.109.16.40` vía Tailscale, Windows, **activa** (conexión directa,
tráfico reciente). Es el host de los workers VM (`WORKER_URL_VM{,_INTERACTIVE,_GUI}` en
env) y la misma máquina Windows donde Cursor ejecutó el closeout de clones del 07-08.
La otra máquina del tailnet (`tarro`) lleva 139 días offline — no es "la VM".

### B2/B3 — Alcance real y clasificación

| Vía | Resultado |
|---|---|
| Workers HTTP `:8088`/`:8089` `/health` | ✓ ambos `ok:true` v0.4.0 (530 y 12 tasks en memoria) |
| SSH (22) | TCP abre pero el handshake SSH cuelga (timeout) → **inaccesible** |
| `windows.fs.list` vía worker | Sandboxeado por policy (C:\GitHub y C:\Users\david **bloqueados por diseño**) — correcto, no se buscó bypass |
| Exec remoto genérico | No existe como tool del worker (por diseño) |

**Veredicto: `BLOCKED_VM_ACCESS`** (más preciso que BLOCKED_NO_VM: la VM existe, está
sana e identificada; lo que no hay es vía de inspección git desde la VPS sin crear
accesos nuevos — fuera del alcance de este pack).

| Ítem VM | Clase |
|---|---|
| Workers VM (:8088/:8089) | **KEEP** — runtime sano |
| Clone `C:\GitHub\umbral-agent-stack-codex` (host del `start_primary_worker.py`) | **KEEP** — runtime; Cursor verifica tip |
| Worktrees Codex (`C:/Users/david/.codex/worktrees/*` + `pr269-worktree` en Temp) | **DEFER → Cursor Windows** (dirty ya inventariados en closeout 07-08) |
| ~44 ramas locales gone no-pack Windows | **DEFER → Cursor Windows** |
| Stashes Windows (15 KEEP del closeout) | **DEFER → Cursor Windows** |
| SSH roto en pcrick (22 abre TCP, no responde) | **DEFER → David** — decidir si habilitar SSH real o dejarlo cerrado |

### B5 — Checklist para David/Cursor (residual Windows — NO tocado desde VPS)

1. Verificar que `C:\GitHub\umbral-agent-stack-codex` (runtime del worker) esté en un
   tip razonable y sin dirty accidental.
2. Podar los worktrees Codex listados KEEP-por-dirty en
   [uas-p1-hygiene-closeout-20260807.md](uas-p1-hygiene-closeout-20260807.md) §2 cuando
   sus diffs se evalúen (rescatar o descartar).
3. Ramas locales gone no-pack (~44) y 15 stashes Windows: mismo criterio que este pack
   (MERGED/PR-verificado → drop; UNIQUE → KEEP documentado).
4. Si David quiere inspección remota de la VM desde la VPS: arreglar el SSH de pcrick
   (hoy cuelga en handshake) — decisión de exposición, no técnica.

## Fase C — Nota Windows

La higiene Windows es **parcial y de Cursor**: este pack solo verificó origin (2 heads),
higienizó la VPS y dejó el residual VM/Windows arriba. No se afirma higiene Windows
completa.

## Gate

**`UAS_HYGIENE_SWEEP_VPS_VM_PASS = PARTIAL`** — Fase A completa (origin=2 heads, −35
ramas locales con verificación individual, worktrees/stashes inventariados, runtime ✓);
Fase B hecha hasta el límite real de acceso (`BLOCKED_VM_ACCESS` documentado con
checklist); PARTIAL (no Y) por los 17 stashes KEEP restantes inventariados + el verify
del heartbeat en 1 de 2 ciclos con señal de plan B. Nada UNIQUE destruido sin
inventario; `stage7_5` intacta.
