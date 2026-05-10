# Q2 2026 — Runtime focus & kill list (2026-05-10)

**Owner:** Copilot Chat (autonomous mandate, dm@umbralbim.cl)
**Hilo origen:** Coordinador de Agentes / Automatización Agentes
**Status:** PROPUESTA. Pendiente ratificación de David.
**Sponsorship clock:** $21,619 expira 2026-07-30 (~11 semanas desde hoy).

## TL;DR

Quedan ~7 semanas hasta el Friday retro 2026-06-26. Para llegar con 1 demo runtime real
a producción (Bot Umbral citando IFC con `aeco-kb-es-vYYYYMMDD`), hay que **freezear
todo lo que no entrega runtime esta ventana** y enfocarse exclusivamente en O16.2.

Lo que sigue es la lista de objetivos Q2 que **no entregan runtime esta ventana** y
deben pasar a "freeze" (sin trabajo nuevo) o "kill" (cierre formal).

## Estado real al 2026-05-10 (post-audit)

| Objetivo Q2 | Estado real | Acción propuesta |
|---|---|---|
| **O16.2** AECO KB → AgenteUB File Search | RBAC done, infra Bicep done, falta build/push 3 imágenes + run pipeline + portal wiring + smoke | **MANTENER. Es el único objetivo runtime de la ventana.** |
| O15 OpenClaw productivo gateway | Repo intent OK, pero VPS gateway corre versión npm-global no-repo (ver nota copilot-instructions) | **FREEZE.** No tocar hasta Q3. Documentar divergencia en runbook. |
| O7 Granola → Notion writer | Operacional (verificado en audits previos), funcional pero sin demos nuevas | **MANTENER en hold.** No requiere trabajo. |
| O8a Granola length instrumentation | Branch `copilot/feat-o8a-granola-length-instrumentation` abierta, sin merge | **KILL Q2.** Reabrir Q3. |
| O8i Notion poller cursor checkpoint | Branch `copilot/feat-o8i-notion-poller-cursor-checkpoint` abierta, sin merge | **KILL Q2.** Reabrir Q3. |
| O9 (delegates) | Branch `copilot/burn-q2-o7-o9-delegates` ya marcada burn-Q2 | **KILL.** Cerrar branches sin merge. |
| O13.1 Mission Control | Branch `copilot/feat-mission-control-o13-1` abierta | **KILL Q2.** No es runtime, es UI control room — sin urgencia sponsorship. |
| Editorial pipeline / Wave 1.5 / Wave 2A (RRSS) | Hilo paralelo activo (`rrss-wave2a/*`) — NO TOCAR desde este hilo | **NO APLICA.** Hilo separado bajo otro coordinador. |
| F8a diagnostics (varias branches `codex/f8a-*`) | Investigación abandonada / superada | **KILL.** Cerrar branches stale. |
| Tournament Phase 2 (varias branches `feat/tournament-phase2-*`) | Sin merge, sin runtime impact | **FREEZE Q2.** Decidir Q3 si vale resucitar. |

## Branches a cerrar (kill list operativa)

Lista de branches que recomiendo cerrar sin merge antes del 2026-05-17 para reducir
ruido de coordinación. **NO ejecutar sin confirmación de David** (algunos pueden tener
trabajo no committeado en local de otros agentes).

```
copilot/feat-o8a-granola-length-instrumentation
copilot/feat-o8i-notion-poller-cursor-checkpoint
copilot/feat-mission-control-o13-1
copilot/burn-q2-o7-o9-delegates
codex/f8a-diagnostic-mode-2026-05-06
codex/f8a-docker-stdin-fix-2026-05-06
codex/f8a-drop-no-banner-2026-05-06
codex/f8a-real-exec-path-2026-05-05
rick/f8a-diagnose-silent-exit-2026-05-06
rick/f8a-first-real-run-2026-05-05
rick/f8a-retry-after-no-banner-fix-2026-05-06
feat/tournament-phase2-*  (12 branches)
```

Total: ~24 branches stale candidatas a archivar.

## Branches que NO se tocan (hilos paralelos activos)

```
rrss-wave2a/*        ← Hilo Automatización RRSS (otro coordinador)
copilot-vps/*        ← Hilo VPS (Copilot-VPS, otro device)
codex/editorial-*    ← Hilo Editorial (Codex)
```

## Capacidad liberada estimada

Si se ejecuta esta kill list:

- ~24 branches archivadas → menos contexto de coordinación.
- ~6 frentes mentales reducidos a 1 (O16.2 buildingsmart-only).
- 7 semanas de calendario disponibles para 5 deliverables concretos:
  1. Build + push 3 imágenes a GHCR (1 día Docker disponible)
  2. `az deployment group create` Bicep umbrella (15 min)
  3. Run pipeline buildingsmart (30 min)
  4. Portal File Search wiring (1h manual)
  5. Smoke AgenteUB (15 min)

Total trabajo runtime real: **~1 día de bandwidth**, repartido en 7 semanas de
calendario. El resto del tiempo es wait + verify, no work.

## Decisión pendiente (David)

- [ ] Aprobar foco único Q2 = O16.2 buildingsmart-only.
- [ ] Aprobar kill list de 24 branches stale (delegar a Copilot-VPS la ejecución batch).
- [ ] Confirmar que hilo RRSS Wave 2A queda fuera de este coordinador.
- [ ] Confirmar que decisiones cross-thread requieren cita explícita de este doc.

## Referencias

- Decisión scope: [2026-05-10-o16-2-buildingsmart-only-decision.md](2026-05-10-o16-2-buildingsmart-only-decision.md)
- Plan ejecución: [2026-05-10-o16-2-execution-plan.md](2026-05-10-o16-2-execution-plan.md)
- Política cross-thread: [docs/runbooks/cross-thread-vps-concurrency.md](../runbooks/cross-thread-vps-concurrency.md)
