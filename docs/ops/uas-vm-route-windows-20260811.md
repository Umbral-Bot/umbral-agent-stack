# PKG-UAS-VM-ROUTE-WINDOWS — windows.* del cron llega a pcrick (2026-08-11)

> **Pack:** PKG-UAS-VM-ROUTE-WINDOWS · rama `claude/pkg-uas-vm-route-windows-20260811` ·
> base `1b24740` (`origin/main`, tip = PR #626)
> **GO David:** que `windows.*` del cron rick-ops llegue a pcrick (viva en
> `100.109.16.40:8088`), no al worker Linux. Env: inventariar, no reescribir.
> **Evidencia:** `~/.coord-ag-evidence/uas-vm-route-windows-20260811/` (scan de
> secretos limpio; tokens jamás impresos).

## FASE 0 — Runtime + prueba del bug

- HEAD `1b24740` (#626). `dispatcher.task_routing` importa con python3 de sistema
  (lección #626 verificada antes de tocar nada).
- Repro unitario en evidencia (`f0-bug-repro.txt`):
  `task_requires_vm(False, "windows.fs.list") == False` — con team normalizado a
  `system` (no requiere VM), el early-return por equipo dejaba todo `windows.*`
  en el worker Linux.

## FASE 1 — Fix de ruteo (código + tests + review): **CODE_PASS = Y**

Contrato ajustado en `task_requires_vm` (documentado en docstring):
1. `_LOCAL_ONLY_PREFIXES` → VPS siempre (igual que antes).
2. `_VM_REQUIRED_PREFIXES` (`windows.`/`browser.`/`gui.`) → **VM siempre, aunque
   el equipo no la requiera** (se elimina el early-return por equipo).
3. Tasks sin prefijo conocido → `requires_vm` del equipo (igual que antes).

`normalize_envelope_identity` intacta (el fix del 400 sigue). Cero imports de
`worker.models`/pydantic (verificado con python3 de sistema).

Tests: parametrize actualizado (casos `(False, windows/browser/gui) → True`,
`(False, custom.task) → False` para fijar el fallback) + test end-to-end del caso
rick-ops (`test_normalized_cron_envelope_routes_to_vm`). **19/19 routing +
88 dispatcher verdes.**

Code-review (3 revisores paralelos sobre el diff): **cero issues bloqueantes**.
Dos observaciones documentadas a propósito:
- **Cambio de comportamiento con VM caída (intencional):** antes, `windows.*` de
  un equipo sin VM completaba `ok:false "Solo disponible en Windows"` en Linux;
  ahora, si pcrick/tailnet cae, la task se **bloquea con alerta** (guard
  existente de `service.py`/`router.py`) hasta que la VM vuelva. Es exactamente
  lo que pide el GO (el fallback Linux ES el bug) y da visibilidad; recomendación
  futura: test de integración del escenario VM-offline.
- **Deployments sin `WORKER_URL_VM`:** el fix no-opea (cae al worker local, el
  comportamiento viejo) — no es regresión; en este runtime la var está definida.
- Contexto histórico verificado: la "Regla 1" eliminada venía del commit
  `3b12971` (2026-03-12) y cubría la dirección inversa (local-only en equipos
  VM); el revert está razonado y testeado, no es arbitrario.

## FASE 2 — Inventario VM_URL vs WORKER_URL_VM (read-only, env NO tocado)

| Dónde | Variable | Valor (host) | ¿Rompe algo si VM_URL sigue en 127.0.0.1? |
|---|---|---|---|
| `~/.config/openclaw/env` (EnvironmentFile del dispatcher) | `WORKER_URL` | `127.0.0.1:8088` | — correcto (worker local) |
| ídem | `WORKER_URL_VM` | `100.109.16.40:8088` | — correcto: es la URL que el dispatcher usa para rutear a pcrick (`service.py:829`) y que da 200 |
| ídem | `VM_URL` | `127.0.0.1:8088` | **No rompe nada: 0 lectores** en código del repo y en el plugin del gateway (greps en evidencia). Es vestigial y solo engaña a humanos/probes (acta #624 cayó ahí) |
| `openclaw-gateway.service` (unit) | `WORKER_URL`, `WORKER_URL_VM`, `WORKER_URL_VM_GUI/INTERACTIVE` (8089), `VM_URL` | mixto | el gateway usa las WORKER_*; su `VM_URL=127.0.0.1` tampoco tiene lectores |

Conclusión: **ningún consumidor roto → default se mantiene: env intacto.**
Checklist opcional para David (no ejecutado): borrar `VM_URL` del env y de la
unit del gateway (o renombrarla apuntando al tailnet) para eliminar la trampa.

## FASE 3 — Deploy + smokes: **PASS**

Restart SOLO dispatcher: active, PID 2922287 → **2930054**. Sin crash (import de
sistema pre-verificado).

| Smoke | Qué | Resultado |
|---|---|---|
| A | POST directo worker, team=ops/type=cron | **HTTP 400** ("2 validation errors") — contrato intacto ✅ |
| B | Cola Redis: `windows.fs.list` ops/cron, path real del cron | journal: `Envelope normalizado … 'ops' -> 'system'` → **`Executing … -> VM`** → **`completed via VM Worker`**. Resultado de pcrick: **`WinError 3` — la ruta `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas` no existe en la VM** (error Windows honesto; ni 400 ni `ok:false` Linux) ✅ |
| C | Control: `ping` team=system | `Executing … -> VPS` → completed via VPS Worker ✅ |
| D | Panel | residual=0, `ok=true` ✅ |
| E | PIDs | worker 85942, gateway 2300605, mission-control 3313840 **intactos**; solo dispatcher nuevo ✅ |

**Hallazgo para David (fuera de alcance de este pack):** el path del cron real no
existe hoy en pcrick (G: no montado o carpeta ausente). El cron ya llega a
Windows; hasta que exista `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas` (o
rick-ops apunte a otra ruta), devolverá ese WinError honesto. La policy NO se
tocó (el path está permitido; el problema es el filesystem de la VM).

## Gates

- **`UAS_VM_ROUTE_WINDOWS_CODE_PASS = Y`** — tests verdes, code-review sin
  bloqueantes, import python3 de sistema OK.
- **`UAS_VM_ROUTE_WINDOWS_PASS = Y`** — Smoke A=400, B llegó a la VM real
  (WinError de Windows), C local, dispatcher active, panel limpio, PIDs intactos.

## TU TURNO (≤2)

1. Cursor mergea la PR (fix + tests + acta + inventario) — al mergear, main == runtime.
2. David decide: (a) crear/montar `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas`
   en pcrick o cambiar el path del cron de rick-ops; (b) opcional "go env" para
   eliminar la `VM_URL` vestigial — este pack no la tocó.
