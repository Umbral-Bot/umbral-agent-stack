# Norte canónico — Umbral Agent Stack (2026-08-06)

> **Este documento es el norte.** Si algo de UAS contradice esto, gana esto — salvo el
> runtime vivo, que siempre gana sobre cualquier doc (ver §0.2).
>
> **Se reescribe entero, con fecha nueva en el nombre.** No se parchea in-place. Un doc
> que nadie se atreve a reescribir ya murió; parcharlo solo disimula el cadáver. El
> anterior queda como histórico y se marca superado en la primera línea.
>
> Pack: PKG-UAS-NORTH-CANON-DRAFT · rama `claude/pkg-uas-north-canon-draft-20260806` ·
> base `86ab72dc` · GO de David: "redactar norte PRIMERO; cierres masivos DESPUÉS".
> Inventario que lo sostiene: [uas-north-inventory-2026-08-06.md](uas-north-inventory-2026-08-06.md).

## 0. Cómo leer esto

### 0.1 Qué es y qué no es

Es **el estado y la dirección**: qué está vivo, qué está en pausa deliberada, qué es
deuda, y qué decisión está esperando a David. No es un tablero de tareas (eso se genera
on-demand con `scripts/ops_resume_board.py` desde los ledgers), no es un inventario
(ese es el doc citado arriba), y no es un plan de sprint.

### 0.2 Jerarquía de verdad

Cuando dos fuentes se contradicen, este es el orden:

| # | Fuente | Ejemplo de lo que manda |
|---|---|---|
| 1 | **Runtime vivo** (`journalctl`, la DB, la UI) | Si el gateway dice `refresh_token_invalidated`, da igual lo que diga `models status` |
| 2 | **Repo** (código, `docs/ops/*`, ledgers JSONL) | Ante discrepancia con Notion, manda el ledger |
| 3 | **Este norte** | Ante discrepancia con un doc viejo de `docs/ops`, manda este |
| 4 | **Notion / Control Room** | Espejo humano, nunca fuente |
| 5 | **Memoria de sesión de un agente** | La más frágil: envejece más rápido que el repo |

El nivel 5 no es teoría. El inventario del 06-ago encontró **cinco** PRs registrados en
memoria como OPEN que estaban MERGED (#555, #564, #565, #572, #581). Estado de PR se lee
con `gh`, nunca de memoria.

---

## 1. Runtime y autenticación — **CERRADO 2026-08-06**

### 1.1 Estado

| Gate | Valor | Fecha |
|---|---|---|
| `OPENCLAW_OPENAI_AUTH_PASS` | **Y** — device login completado | 2026-08-06 |
| `OPENCLAW_AUTH_ORDER_PASS` | **Y** — override aplicado | 2026-08-06 |

Orden de auth vigente para `--agent main`, provider `openai`:

1. `openai:david.a.moreira.m@gmail.com` ← el bueno, primero
2. `openai:umbral-rick` ← **zombi**: sigue en el store, detrás, **sin borrar a propósito**

El zombi no se elimina hasta que haya al menos un ciclo completo de operación normal
sobre el orden nuevo. Borrarlo el mismo día que se arregla el login es quitarse la red
antes de comprobar que el trapecio aguanta.

### 1.2 La trampa: `models status` puede mentir

**`openclaw models status` reportó `ok, expires in Nd` con el refresh token ya
invalidado.** No es un bug menor: es que el comando informa la *vigencia nominal del
token*, no la *validez del refresh*. Un diagnóstico de auth basado solo en `status`
concluye "todo bien" mientras cada turno interactivo se cae.

**El oráculo real es el journal del gateway:**

```bash
journalctl --user -u openclaw-gateway --since "30 min ago" --no-pager \
  | grep -Ei 'auth_permanent|refresh_token_invalidated|401'
```

Regla dura: **auth no se diagnostica con `status`.** `status` sirve para saber qué
identidades existen y en qué orden; para saber si *funcionan*, se lee el journal o se
manda una sonda real.

### 1.3 Re-auth headless (sin TTY)

El login por device-code exige TTY, y la VPS se opera por SSH no interactivo. La receta
que desbloqueó el incidente:

```bash
script -qfc "openclaw models auth login --provider openai --device-code" /dev/null
```

Si el prompt igual no drena, agregar un fifo. Y el orden importa:

- `--force` **solo antes** de un login limpio.
- **Post-login**, nunca `--force`: se fija el orden con
  `openclaw models auth order set --provider openai --agent main "<bueno>" "<zombi>"`.

Invertir esa secuencia vuelve a romper el runtime — el `--force` posterior al login
pisa la identidad recién creada.

### 1.4 Lo que este incidente dejó al descubierto

El login expirado **no degradó** el servicio: lo tumbó entero. Todo turno interactivo de
Rick caía, porque los tres modelos de la cadena son del mismo provider. Eso es §6.

---

## 2. Tester E2E de usuario — **ACTIVO, con un gate abierto**

### 2.1 Dónde está

Contrato: [user-e2e-tester-system-plan-2026-08-01.md](user-e2e-tester-system-plan-2026-08-01.md)
(15 prohibiciones del rol, §3.4 criterios de GO).
Operación: [user-e2e-tester-playbook-2026-08-02.md](user-e2e-tester-playbook-2026-08-02.md)
(suites, oráculos, ventanas). El playbook **superó al plan** en detalle: definió 4 sondas
de frescura donde el plan tenía un solo gate.

### 2.2 Estado real de las sondas P3

Conviene ser exacto, porque la cuenta rápida engaña:

| Sonda | Estado | Nota |
|---|---|---|
| **P3-01** — calendar hoy | **PASS** | MATCH de un dato que solo vivía en el *cuerpo* del evento, no en el título → descarta fabricación de forma no trivial |
| **P3-02** — evento fresco | **BLOCKED** (04→05-ago) | Falló por el login expirado de §1, **no** por el producto. Causa ya resuelta → es re-corrible hoy |
| **P3-03** — pieza fuente citada | **NUNCA CORRIÓ** | Depende de que Rick cite una URL de fuente en una respuesta; no está del todo bajo control del tester |
| **P3-04** — no-autopublish RRSS | **NUNCA CORRIÓ** | Casi trivial (mirar perfiles públicos); no se ejecutó porque el pack P4 lo prohibió explícitamente |

Es decir: **1 de 4 con veredicto**, 1 intentada y bloqueada por causa externa ya
resuelta, 2 sin tocar. La lectura "2/4" cuenta P3-02 como ejercida — es defendible
(la sonda corrió, el gateway la tumbó), pero para decidir el GO conviene la lectura
estricta: solo P3-01 produjo veredicto de producto.

### 2.3 El GO de capitalización sigue DIFERIDO

[user-e2e-p4-retro-decision-2026-08-04.md](user-e2e-p4-retro-decision-2026-08-04.md)
evaluó los 5 criterios de §3.4 con honestidad: **2 cumplidos, 1 PARCIAL (el criterio 1,
"roadmap P0→P3 completo"), 1 condicionado a ese, 1 que es la decisión misma de David.**
El plan dice "todos, no alguno". Por eso P4 recomendó **diferir**, y esa recomendación
sigue en pie: el criterio 1 no se cerró porque P3-02 se bloqueó.

**Lo que lo destraba es una sola sonda.** Re-correr P3-02 sobre el gateway
re-autenticado cierra el criterio 1 y, de paso, resuelve la hipótesis de circularidad
que P3-01 §4.2 dejó abierta (la misma task de calendar figura fallida a las 07:32 y
respondiendo a las 22:49).

**Si el GO se diera igual**, la recomendación de P4 §4 es clara y no cambia:
**actualizar `umbral-rick-runtime`**, no crear una skill `user-e2e-tester` separada —
las 5 corridas vivieron en un solo dominio, y crear exige ≥2 superficies distintas.

### 2.4 Hallazgos vivos que salieron del tester

No son ruido de test: son bugs de producción que nadie cerró.

1. **UX-01** — Rick vuelca errores crudos de herramienta al canal de David (2 veces).
2. **Urgencia incompleta** — Rick nombra 3 tareas reales pero omite 5 abiertas más
   antiguas, 3 de ellas prioridad Alta. Omisión, no invención.
3. **Anomalía CAND-001** — fila `Publicado` con `autorizar_publicacion=false`, y
   `aprobado_contenido=true` contra lo que pide su propio Decision Brief. Lleva
   ~3 semanas así.
4. **Discrepancia temporal de calendar** (P3-01 §4.2), sin explicación verificada.
5. **Drift Linear** — UMB-39 `In Progress` dentro de un proyecto en `Backlog`.

---

## 3. Editorial — **STANDBY DELIBERADO, no roto**

El frente está pausado, y conviene decirlo así de claro porque su aspecto engaña:
21 docs y 11 ramas dan sensación de obra abandonada. No lo es.

- **Sus 11 ramas tienen PR mergeado.** Cero huérfanas. La percepción contraria era un
  falso positivo del criterio "ahead" (ver §7.2).
- Contrato vigente: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md)
  (mergeado en #550) + [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md)
  + [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md).
- **Pendiente real:** la **Fila I** del gap-matrix sigue en `CONTRATO_OPUESTO` y el
  schema HÍBRIDO propuesto espera decisión de David desde el 22-jul. Es lo único que
  bloquea reanudar P1.
- Magnific P2.2 (#555) está **mergeado**, pero eso no significa activo: al momento del
  merge faltaba `MAGNIFIC_API_KEY` en la VPS. **Que el código esté en main no dice nada
  sobre si la credencial existe** — se verifica aparte.

El resto del árbol editorial (18 actas P21–P28) es histórico.

## 3bis. n8n — **ACTIVO**

Único frente que quedó corriendo mientras el resto se pausaba. #564 y #565 mergeados el
24-jul; **B1 y B3 ACTIVOS en la VPS con bot TEST desde el 25-jul**
(`infra/n8n/README.md`). N2/N4/B4/N3b siguen fuera de alcance. Regla que no se toca:
**n8n nunca escribe Notion directo** (ADR-011 #1) — pasa por el Worker.

---

## 4. Skills y registry — **ACTIVO**

### 4.1 Estado versionado

| Skill | Versión | Qué trajo |
|---|---|---|
| `umbral-rick-runtime` | **v0.3.0** (2026-08-04) | §"Verificación en rol usuario" + `references/reference-user-e2e.md` |
| `skills-capitalize` | **v0.1.8** (2026-08-06) | Gobierno de concurrencia del registry |
| `cursor-orchestrator` | **v0.8.0** (2026-08-06) | §2c superficie de evidencia |
| `pkg-receiver-protocol` | **v0.3.0** (2026-08-04) | Excepción `WIP_IN_PLACE` |

### 4.2 Single-writer — regla dura, nacida de un incidente real

El 2026-08-04 a las 20:28 el clone canónico del registry quedó **truncado**: el
`SKILL.md` de `umbral-rick-runtime` en 0 B y su `manifest.yaml` en 1 B; el deploy de
`cursor-orchestrator` revertido a v0.4.0 en el mismo segundo. Hipótesis: un segundo hilo
escribiendo sobre el mismo clone. `skills-capitalize` v0.1.8 codificó tres reglas:

1. **Un solo escritor** del clone canónico y de las superficies desplegadas, en todos los
   modos. `.sync-state.json` intacto **no** prueba ausencia de escritura — solo se mueve
   con ships.
2. **Scan de archivos ≤1 byte al arrancar.** 0 B / 1 B no es WIP: es corrupción. Restore
   desde HEAD solo con GO; nunca commitear ni shipear encima.
3. **Anti-fabricación de autoría.** No atribuir una escritura sin PID, log de tool o
   reporte del propio escritor. `mtime` y orden de eventos son correlación, no autoría —
   por eso la autoría de ese incidente quedó como hipótesis, no como acusación.

### 4.3 Regla de referencias

Las referencias solo se propagan desde **`<slug>/references/`**, nunca desde layout
plano en la raíz del slug. El tool siempre funcionó así; la creencia contraria costó
7 días de copias manuales que además quedaban fuera del drift-gate.

### 4.4 ~~Deuda estructural: `openclaw-vps-operator` no tiene SoT~~ → CERRADA

Ciclo completo 2026-08-06: registry [#15](https://github.com/Umbral-Bot/umbral-skills-registry/pull/15)
(SoT 0.1.0 + refs diagnose/mutate/auth) → UAS stubs [#584](https://github.com/Umbral-Bot/umbral-agent-stack/pull/584)
→ smoke SoT user + delete stubs [#585](https://github.com/Umbral-Bot/umbral-agent-stack/pull/585)
(`918dbe6d`). Detalle histórico en §8.

---

## 5. Deuda P0–P3

### P0 — mueve la aguja esta semana

| # | Ítem | Dueño |
|---|---|---|
| P0.1 | **Curar fechas del backlog Notion**: 20 tareas abiertas sin `Fecha objetivo`; cerrar las de abril ya resueltas | **David** |
| P0.2 | **Re-correr P3-02** sobre el gateway re-autenticado → cierra el criterio 1 del tester | Claude local (con GO) |

P0.1 es el único fix que cambia lo que Rick le responde a David mañana. Sin fechas, el
orden ascendente devuelve abril para siempre; arreglar Calendar y RAG antes que esto no
cambia nada de lo que David ve cada mañana.

### P1 — desbloquea trabajo de otros

| # | Ítem | Dueño |
|---|---|---|
| P1.1 | ~~**SoT de `openclaw-vps-operator`** (§8)~~ → **DONE** 2026-08-06 (#15 registry + #584/#585 UAS; smoke user SoT PASS) | — |
| P1.2 | ~~30 huérfanas + 26 worktrees Codex + 2 clones + KILL mergeadas~~ → MERGED_KILL **DONE** (192/192, #589) + worktrees Codex **DONE** (43→9) + huérfanas-con-merge-base **KILL DONE** (28/28, #591) + **RESCUE1 DONE** (2 docs, #592) + **fila 1 (PIT) ARCHIVE_DOCS_ONLY DONE** (#594) + **fila 2 RESCUE_SELECTIVE DONE** (#595) + **fila 3 ARCHIVE DONE** (runbook + report JSON multiformato archivados HISTÓRICO en `main`, [uas-p1-2-keep3-archive-runbook-2026-08-06.md](uas-p1-2-keep3-archive-runbook-2026-08-06.md); `stage7_5_copy_writer.py` de producción confirmado diff 0; rama `rick/stage7_5-multiformat` KEEP_INDEFINITE, conserva writer/evaluator/tests sin mergear) + **orphan58 analyze DONE** (58/58 reconfirmadas sin merge-base, 49 KILL_SAFE / 5 CHERRY_CANDIDATE / 4 KEEP_FOSSIL, [uas-p1-2-orphan58-analyze-capx-20260806.md](uas-p1-2-orphan58-analyze-capx-20260806.md); capitalización `pkg-receiver-protocol` 0.3.4→0.4.0 shipeada) + **KILL49 DONE** (49/49 borradas en origin, 0 fallidas, 9 protegidas — 5 CHERRY_CANDIDATE + 4 KEEP_FOSSIL — confirmadas vivas con SHA intacto, [uas-p1-2-orphan58-kill49-20260807.md](uas-p1-2-orphan58-kill49-20260807.md)). **Eje P1.2**: cherry-pick de las 5 CHERRY_CANDIDATE — **cherry5 brief DONE** (evaluación path a path
con recomendación por fila: 1 KILL_BRANCH, 3 ARCHIVE_DOCS_ONLY, 1 RESCUE_SELECTIVE + 1
DEFER_PRODUCT, [uas-p1-2-orphan58-cherry5-20260807.md](uas-p1-2-orphan58-cherry5-20260807.md)) —
**fila 1 KILL DONE** (`codex/wip-granola-v2-snapshot-2026-04-30` borrada en origin, GO "1 KILL" de
David — [uas-p1-2-orphan58-cherry1-kill-20260807.md](uas-p1-2-orphan58-cherry1-kill-20260807.md)) +
**filas 2/3/5 + #58 EXEC DONE** (GO "acepta recomendaciones del orquestador": fila 2
`rick/editorial-linkedin-writer-flow` archivada 21 paths + rama borrada; fila 3
`antigravity/sync-uncommitted-changes` 3 docs archivados + 5 skills `code-*`/`teams.yaml`
diferidos (`DEFERRED_PRODUCT`) + rama borrada; fila 5 `codex/notion-governance-v1-contract` 6 paths
V1 archivados + README de pivote + rama borrada; #58 `windows-dirty-rescue` borrada (subsumida por
fila 1) —
[uas-p1-2-orphan58-cherry25-exec-20260807.md](uas-p1-2-orphan58-cherry25-exec-20260807.md)) —
**fila 4 ARCHIVE+KILL DONE** (GO "aplica… opción d": hook archivado byte-idéntico bajo
`docs/archive/hooks-block-deployed-repo-writes-2026-04/` + README; **sin** `git add -f` ni wire en
`.claude/settings.json`; rama `rick/test-github-mvp-smoke` borrada —
[uas-p1-2-orphan58-cherry4-archive-kill-20260807.md](uas-p1-2-orphan58-cherry4-archive-kill-20260807.md)).
**Eje CHERRY P1.2 cerrado** (5/5 + #58). **fossil3 EXEC DONE** (GO "go a todo lo que indicas en
orden": `cursor/regression-test-coverage-b904` — 4 tests de seguridad rescatados a
`tests/test_security_regression.py`, 19/19 PASS, rama borrada; `cursor/power-bi-libraries-formats-5c1b`
— doc único rescatado a `docs/63-powerbi-librerias-formatos-pbix-pbip.md` con nota de vigencia
2026-08-07 verificada vía blog oficial de Microsoft, rama borrada; `feat/bitacora-populate` — KILL,
enfoque descartado en R14 a favor de `enrich_bitacora_page` —
[uas-p1-2-fossil3-exec-20260807.md](uas-p1-2-fossil3-exec-20260807.md)). Residual fuera del eje:
`rick/stage7_5-multiformat` KEEP_INDEFINITE (decisión de producto previa, sin tocar). **Las 90
ramas huérfanas originales de P1.2 quedan 100% resueltas** | Claude local (con GO) |
| P1.3 | **DISCARD DONE** + **F8A DISCARD DONE** (2026-08-07): clones hermanos limpios; worktree `f8a-prompt-quoting-fix` descartado (1 task staged mayo 2026) y removido; `-codex-coordinador` ahora en rama `main` @ tip `origin/main`. **Eje P1.3 cerrado** — [uas-p1-3-clone-wip-eval-20260807.md](uas-p1-3-clone-wip-eval-20260807.md) · [uas-p1-3-clone-wip-discard-20260807.md](uas-p1-3-clone-wip-discard-20260807.md) · [uas-p1-f8a-discard-20260807.md](uas-p1-f8a-discard-20260807.md) | Cursor local (GO David) |
| P1 (closeout) | **HIGIENE GIT CERRADA** (2026-08-07): closeout #608 + GO "GO F8A DISCARD" — Clone A y B en `main` @ tip `origin/main` limpios; `f8a` removido. Residual no bloqueante: worktrees KEEP restantes + 15 stashes KEEP inventariados; `rick/stage7_5-multiformat` KEEP_INDEFINITE. VPS higiene diferida (pedido David: "por ahora" solo F8A). — [uas-p1-hygiene-closeout-20260807.md](uas-p1-hygiene-closeout-20260807.md) · [uas-p1-f8a-discard-20260807.md](uas-p1-f8a-discard-20260807.md) | Cursor local (GO David) |
| P1 (VPS) | **HIGIENE VPS = PARTIAL** (2026-08-07, PKG-UAS-P1-VPS-HYGIENE + -EXEC, GO "GO VPS HYGIENE" + "GO A LO MAS RECOMENDABLE..."): Fase 1 inventario + Fase 2/3 ejecutadas. Hecho: cache npm 6.5G→838M, 4 líneas muertas de crontab fuera, P3.2 2/3 (`load.paths`+`umbral-tournament-github` vía edición JSON quirúrgica con backup, gateway reload limpio confirmado por log; `trustedProxies` intacto por regla dura), 2 worktrees oauth podados (mergeados, dirty descartado), 2 worktrees `hb` con fix real del poller Notion (loop de reprocesamiento bot/echo) rescatados en PR #611 (mergeado 2026-08-07/08, deployado en runtime — dispatcher reiniciado, active) y podados tras el rescate. `~/archive/uas` sigue BLOCKED por `G-WH-VPS-2` (no citado, no reabierto). Transcripts huérfanos: ver fila propia abajo (2026-08-08). — [uas-p1-vps-hygiene-20260807.md](uas-p1-vps-hygiene-20260807.md) · [PR #611](https://github.com/Umbral-Bot/umbral-agent-stack/pull/611) | Claude VPS (GO David, sin self-merge) |
| P1 (transcripts) | **HIGIENE VPS transcripts = PARTIAL** (2026-08-08, PKG-UAS-P1-VPS-TRANSCRIPTS, GO "go con el siguiente"): CLI oficial encontrado (`openclaw sessions cleanup --dry-run`, no `doctor --fix`) pero su `--enforce` es **delete permanente sin backup** (confirmado por `openclaw docs` — el rename-a-`.deleted.*` que `doctor` promete es de la deleción explícita vía API, no de la poda automática de huérfanos), así que falla la condición "solo rename, no delete hard" del pack y **no se ejecutó**. Dimensionado sin mutar: 1005 huérfanos en `main` (370MB), ~16.4k / ~2GB si se incluyen los 8 agentes. Sin presión de disco. Decisión de alcance/autorización de delete permanente queda con David. — [uas-p1-vps-hygiene-20260807.md](uas-p1-vps-hygiene-20260807.md#transcripts-huérfanos--cierre-del-residual-pkg-uas-p1-vps-transcripts-2026-08-08) | Claude VPS (PARTIAL, pendiente decisión David) |
| P1.4 | **UX-01** — investigar por qué el stream `tool` del gateway llega crudo al canal | Lane operador |

### P2 — sanea sin urgencia

| # | Ítem | Dueño |
|---|---|---|
| P2.1 | ~~Decidir **#541**~~ → **DONE** 2026-08-07: mergeado como registro HISTÓRICO (`470706c9`, inventario/plan/inputs sys-diag 2026-07-17). Cifras S14 de ramas quedan superadas por P1.2. Rama head borrada. | — |
| P2.2 | ~~Releer **#521**~~ → **DONE** 2026-08-07: mergeado como registro HISTÓRICO (`d12da293`, audit models.json hygiene 2026-07-04). Auth vigente: §1 de este norte. Rama head borrada. | — |
| P2.3 | Marcar vigencia en ~330 docs de `ops`+`audits` (header `CANONICO\|HISTORICO`, sin borrar) | Claude local (con GO) |
| P2.4 | **Anomalía CAND-001** y **drift Linear UMB-39** | David / lane operador |
| P2.5 | Fixes 3–6 de [diag-rick-frescura-2026-08-01.md](diag-rick-frescura-2026-08-01.md): alinear `model_router` (declara providers inexistentes, 65 warnings/día), aprobar o desactivar el nodo VM (679 pairings fallidos/día), cortar el ruido de escalación a Linear, reactivar RAG (apagado desde ~abril) | Lane operador |

### P3 — housekeeping

| # | Ítem | Dueño |
|---|---|---|
| P3.1 | **`.agents/board.md`**: borrarlo, o generarlo desde `ops_resume_board.py`. Sin tocar desde 2026-07-14 | **David** |
| P3.2 | Higiene de config: `plugins.entries.umbral-tournament-github` (stale), `load.paths` redundante, `gateway.trustedProxies` sin configurar | Lane operador |
| P3.3 | `publication_id` de filas históricas no sigue el formato `shortlist-<alternativa_id>` | Lane operador |

---

## 6. DECISIÓN PENDIENTE — fallback cross-provider

**Estado: abierta. Es de David, no del agente.**

Hoy la cadena de modelos es **100% mono-provider (OpenAI)**. Los tres modelos —
principal y ambos fallbacks — cuelgan de la misma identidad. Eso no es un fallback: es
tres nombres para el mismo punto único de fallo, y el 2026-08-06 lo demostró en
producción — un refresh token invalidado tumbó todo turno interactivo de Rick.

Agrava el cuadro que `model_router` **ya declara providers que no existen**
(`preferred=azure_foundry, fallback=[claude_pro, gemini_pro, gemini_flash]`), 65
warnings/día, con todas las tasks saliendo con `model=` vacío. Es decir: **hoy el
sistema aparenta tener fallback cross-provider en su config y no lo tiene en la
realidad.** La configuración miente en la misma dirección que mentía `models status`.

Lo que hay que decidir (una sola pregunta, tres salidas):

| Opción | Qué implica | Costo |
|---|---|---|
| **A — Cross-provider real** | Habilitar ≥1 provider distinto (Anthropic / Gemini / Azure) con credencial propia y cadena verificada | Credencial nueva + smoke de failover + gasto |
| **B — Mono-provider asumido** | Dejarlo así, **borrar del router los providers fantasma** y documentar que un incidente de auth es una caída total | Bajo — pero exige aceptar el riesgo por escrito |
| **C — Mono-provider + detección** | Sin provider nuevo, pero con alerta temprana: sonda periódica que lea el journal y avise antes de que David lo descubra conversando | Medio — es el punto intermedio |

**Recomendación:** **C ahora, A cuando haya presupuesto.** B es honesto pero deja a David
descubriendo las caídas por conversación, que es exactamente como se descubrió esta.
Lo que **no** es aceptable es el estado actual: config que promete fallback y runtime que
no lo tiene.

Adyacente a esta decisión (misma sesión de trabajo, no la misma pregunta): correr
`openclaw doctor --fix` y limpiar el `umbral-tournament-github` stale (P3.2).

---

## 7. Anti-patrones — lo que este sistema ya demostró que falla

Cada uno tiene evidencia en este repo. No son máximas: son cicatrices.

### 7.1 El board estático mantenido a mano se pudre

`.agents/board.md` lleva **23 días** sin tocar, con tres fechas internas
contradictorias; los dashboards Q2 de `notion-governance` están congelados desde
mayo/junio. La corrección **no** es actualizarlo más seguido — es dejar de tener un
archivo que alguien mantiene a mano y generar el tablero on-demand desde ledgers
append-only (`ops_resume_board.py`).

### 7.2 "ahead ≠ 0" leído como "trabajo sin integrar"

Bajo squash-merge una rama conserva sus commits y queda *ahead* de main aunque su
contenido esté 100% integrado. De 119 ramas, **70 figuran ahead con su PR ya mergeado**.

**Criterio correcto para cualquier barrida de ramas de este repo:**

```bash
# NO:  git rev-list --count origin/main..<rama>        ← 70 falsos positivos
# SÍ:  cruzar headRefName contra los PRs mergeados
gh pr list --state merged --limit 600 --json headRefName -q '.[].headRefName' > merged.txt
grep -qxF "<rama>" merged.txt && echo "KILL seguro" || echo "requiere leer el diff"
```

Y para las que no tienen PR: **nunca `KILL` sin `git diff origin/main...<rama>` primero**,
sobre todo las de divergencia de 3–4 cifras (ramificadas de un main viejo, jamás
rebaseadas: el número no es trabajo propio).

### 7.3 El PR docs-only sin dueño ni caducidad se duerme

**#541**: 20+ días abierto, `+2692/-0`, `MERGEABLE`, sin conflicto, esperando respuestas
multi-IA que nunca llegaron. No se murió por conflicto técnico ni por desacuerdo: se
murió porque nadie era su dueño y nada lo obligaba a resolverse.

**Regla:** todo entregable docs-only lleva **dueño + fecha de revisión**, o se cierra.
Un PR sin dueño a los 14 días es deuda, no trabajo en curso.

### 7.4 Cerrar un frente con `docs/ops/*.md` cuando lo que se pidió era runtime

Un plan no es un sistema andando. Vale al revés también: **mergear código no es
activarlo** — #555 está en main y `MAGNIFIC_API_KEY` puede seguir sin existir; #565 está
en main y el estado ACTIVE de los workflows se lee del runtime, no del PR.

### 7.5 Leer una herramienta de estado como si fuera un oráculo de verdad

`models status` dice `ok` con el refresh invalidado. La config del router declara
providers que no existen. `.sync-state.json` intacto no prueba que nadie escribió.
**Un comando de estado informa lo que registró, no lo que pasa.** El oráculo siempre es
externo: journal, DB, UI, una sonda real.

### 7.6 La memoria de sesión como fuente de estado

Cinco PRs registrados como OPEN estaban MERGED. Las memorias son observaciones
fechadas, no estado vivo.

### 7.7 Dos escritores sobre el mismo clone canónico

El incidente "vaciador" del 04-ago dejó `SKILL.md` en 0 B. Y su corolario: **no
atribuir autoría sin PID o log** — `mtime` es correlación.

---

## 8. Propuesta — SoT única para `openclaw-vps-operator`

*(Ejecutada 2026-08-06. Esta sección queda como registro del plan; el estado vivo es §4.4 CERRADA / P1.1 DONE.)*

### 8.1 El problema no es el que parecía

El inventario lo llamó "2 copias divergentes". Leídas ambas, **no son copias del mismo
texto: son dos skills distintas que comparten el `name:`**.

| | `.agents/skills/openclaw-vps-operator/SKILL.md` | `.claude/skills/openclaw-vps-operator/SKILL.md` |
|---|---|---|
| Último commit | **2026-05-13** (`ef053c35`), nunca actualizada | **2026-06-01** (`39bacc9f`), 3 commits |
| Líneas | 170 | 155 |
| Alcance | **Mutar** el runtime de forma reversible | **Entender** el runtime sin inventar arquitectura |
| Secciones | Preflight obligatorio (7 checks), Operaciones permitidas con autorización, Operaciones PROHIBIDAS, Evidencia, Rollback, Stop conditions | Superficies canónicas, Referencias oficiales, Flujo operativo (leer estado vivo → topología → superficie de edición), Antipatrones |
| Destinatario declarado | Copilot/VPS, usuario `rick` | Claude |
| `journalctl` | **Sí** (líneas 76, 145) — como smoke post-patch | No |
| `models status` | No | **Sí** (línea 82) — en el checklist, **sin advertencia** |
| `models auth login` / `order set` | No | No |

La copia `.claude` **se declara a sí misma no canónica**: "para operaciones runtime con
backup/patch/restart/rollback: preferir la skill canónica de repo
`.agents/skills/openclaw-vps-operator/SKILL.md`". O sea, ya hay una jerarquía declarada
— pero apunta al archivo **más viejo y nunca actualizado**, y el `name:` idéntico
significa que un host que cargue ambas resuelve por precedencia de directorio, no por
esa nota.

Y el hallazgo que más importa: **ninguna de las dos cubre la re-auth de §1.** La
`.agents` usa `journalctl` para verificar un patch, no para diagnosticar auth. La
`.claude` lista `openclaw models status` en su checklist mínimo justo con la trampa que
§1.2 documenta. Capitalizar los 5 aprendizajes sin resolver esto primero los metería en
un archivo que otro host puede no estar cargando.

### 8.2 Propuesta: una skill en el registry, dos secciones, cero copias en UAS

**SoT elegida: `umbral-skills-registry/skills/openclaw-vps-operator/`.**

Fundamento: es la única superficie con un solo escritor gobernado (regla dura 8 de
`skills-capitalize` v0.1.8), con drift-gate, versionado y sync a los hosts. Dejar la SoT
dentro de UAS reproduce exactamente el problema — dos directorios de skills en el mismo
repo, sin gate, sin versión, sin dueño.

Estructura propuesta:

```
skills/openclaw-vps-operator/
├── SKILL.md            # marco: superficies canónicas, cuándo aplica, antipatrones
├── manifest.yaml       # version 0.1.0, notes con la procedencia de ambas copias
└── references/
    ├── reference-diagnose.md   # de la copia .claude: estado vivo, topología, no inventar
    ├── reference-mutate.md     # de la copia .agents: preflight, autorización, rollback
    └── reference-auth.md       # NUEVO: los 5 aprendizajes de re-auth (§1)
```

Las dos copias actuales **no se pierden ni compiten**: se vuelven las dos referencias de
una sola skill, que es lo que siempre fueron — diagnosticar y mutar son dos modos del
mismo trabajo, no dos skills.

### 8.3 Plan de deprecación de la divergente

Cinco pasos ejecutados (estado al cierre):

| # | Paso | Estado |
|---|---|---|
| 1 | Crear el slug en el registry (`0.1.0` + 3 refs) | **DONE** — registry PR #15 |
| 2 | Ship a hosts habilitados (`~/.claude`, `~/.cursor`, `~/.codex`) | **DONE** — post-merge #15 |
| 3 | Stubs en UAS (puntero al SoT) | **DONE** — UAS PR #584 (`a16b5b54`) |
| 4 | Smoke: runtime carga SoT user (no stub repo); trampa `models status` / `reference-auth` | **DONE** — `OPENCLAW_VPS_STUBS_SMOKE_PASS=Y` en PKG-UAS-OPENCLAW-STUBS-CLOSE |
| 5 | Borrar stubs locales en UAS | **DONE** — UAS PR #585 (`918dbe6d`); SoT user intacto |

Ciclo norte SoT: **#582 inventario → #583 norte → #15 registry → #584 stubs → #585 delete**.

### 8.4 Qué NO se propone

No fusionar el texto de las dos copias en un solo `SKILL.md` corrido: perdería la
separación diagnosticar/mutar, que es justamente la que evita que un agente en modo
"entender" termine parcheando `openclaw.json`. No crear una skill nueva `uas-north-governance`
(ver el inventario §7): los aprendizajes tienen destino natural en skills existentes.

---

## 9. Los canónicos que este norte no reemplaza

Este documento resume y decide; **no sustituye** a los contratos. Si necesitás el detalle:

| Tema | Doc |
|---|---|
| Reingreso tras pausa, cadencia de ledger | [ops-resume-reentry-2026-08-02.md](ops-resume-reentry-2026-08-02.md) |
| Spec del ledger JSONL | [../operations/README.md](../operations/README.md) |
| Rol tester usuario (contrato) | [user-e2e-tester-system-plan-2026-08-01.md](user-e2e-tester-system-plan-2026-08-01.md) |
| Suites y oráculos del tester | [user-e2e-tester-playbook-2026-08-02.md](user-e2e-tester-playbook-2026-08-02.md) |
| Decisión de capitalización del tester | [user-e2e-p4-retro-decision-2026-08-04.md](user-e2e-p4-retro-decision-2026-08-04.md) |
| Línea base de frescura + 7 fixes | [diag-rick-frescura-2026-08-01.md](diag-rick-frescura-2026-08-01.md) |
| Contrato del norte editorial | [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) |
| Brecha editorial norte vs actual | [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md) |
| Roadmap editorial P1–P3 | [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) |
| Política de clone canónico | [uas-main-clone-sanitize-2026-07-23.md](uas-main-clone-sanitize-2026-07-23.md) |
| Inventario que sostiene este norte | [uas-north-inventory-2026-08-06.md](uas-north-inventory-2026-08-06.md) |

---

## 10. Lo que este documento no hace

No borra ramas, PRs ni worktrees. No escribe en Notion, en la VPS ni en el registry de
skills. No ejecuta `skills-capitalize`. No toca el zombi `openai:umbral-rick`. No corre
sondas contra el gateway. No abre gates ni publica. La cola de cierre de 15 ítems vive
en el inventario §8 y espera su propio GO.
