# Mega-diagnóstico general 2026-08 — F2 Runtime VPS (acta de ejecución)

> **Status:** ACTA de ejecución, solo lectura. Fase 2 (F2) del programa macro de David
> 2026-08-11/12 (`docs/operations/megadiag-plan-2026-08-12.md`, PKG-MACRO-MEGADIAG-PLAN,
> #629).
> **Emitido por:** PKG-MACRO-MEGADIAG-F2 (Claude Code, VPS Remote-SSH).
> **Rama:** `claude/macro-megadiag-f2-20260812`, base `main` @ `5b2cc8a117a2958c4c7792fb182b9e5f8b5530fc`.
> **Fecha de captura:** 2026-08-12, ventana ~05:00–05:50 UTC.
> **PR:** draft docs-only, label `do-not-merge`.
> **Modo:** solo lectura. Cero mutación, cero restart, cero edición de `openclaw.json`,
> cero imprensión de secretos/tokens. Ningún STOP condition del plan se disparó durante
> la captura.

## 0. Alcance de esta acta

F2 = E2 (runtime VPS) + E4-VPS (drift skills repo↔runtime) + E5 (Notion/n8n MCP) + E7
lado VPS (transcripts, evidencia cron/path pcrick). E1/E3/E6/E7-Windows y E4-Windows
quedan fuera — corresponden a F1 (Windows, en paralelo) y F3/F4 (fases posteriores).

Nota de método: donde el hallazgo de un eje contradice o refina lo que citan
`CLAUDE.md`, `.agents/PROTOCOL.md` o el propio plan, se marca explícitamente como
divergencia repo-dice vs VPS-muestra (regla R6 de
`docs/runbooks/cross-thread-vps-concurrency.md`), no se oculta.

## 1. Resumen ejecutivo

- **Runtime core sano:** los 4 servicios `systemd --user` relevantes (gateway,
  worker, dispatcher, mission-control) están `active (running)` sin restarts
  necesarios; worker `/health` responde 200 en ~2ms; `openclaw status --all` no
  reporta secretos expuestos ni canal caído.
- **Drift real y grande en skills:** el runtime OpenClaw solo tiene 6 de las 86
  skills canónicas del repo desplegadas (~7%), y las 6 desplegadas difieren
  byte-a-byte de su plantilla actual en `main`. El plan cita "42/86 de julio" como
  contexto histórico (no heredado como hecho) — la remedición de agosto da 6/86, una
  caída fuerte si esa cifra de julio era correcta.
- **La skill que este mismo diagnóstico debía usar (`openclaw-vps-operator`) no
  existe en `main`.** Vive solo en la branch protegida `rick-delivery/poller-healthcheck-hardening`
  (no tocada, leída vía `git show`), en una versión más vieja y sin el modo
  "diagnose" que el plan asume. `CLAUDE.md` y `.agents/PROTOCOL.md` citan un path
  (`.agents/skills/openclaw-vps-operator/SKILL.md`) que no existe en `main`.
- **Notion PASS, n8n BLOCKED por instancia incorrecta:** el fetch directo a la
  página "Control Room" (vía `NOTION_CONTROL_ROOM_PAGE_ID`) funciona y devuelve
  contenido vivo y reciente. El conector MCP de n8n disponible en esta sesión
  responde pero apunta a un workspace distinto (temática AEC/Speckle/Workshop) del
  que declara el env VPS (`N8N_URL=http://127.0.0.1:5678`) — no se puede confirmar
  estado B1/B3 desde aquí.
- **Transcripts confirmados en ~16 GB**, pero el desglose es más preciso que la cifra
  heredada de mayo: 9.2G son transcripts reales por agente (`agents/`), 5.1G son
  caché `npm` de proyectos codex/MCP (no transcripts). El camino pcrick vía tailnet
  (100.109.16.40) está sano y activo (587 polls exitosos hoy); WinError 3 no se
  reprodujo en la ventana revisada del lado VPS.

## 2. E2 — Runtime VPS

| Ítem | Estado observado | Evidencia [E] | ¿Pide decisión? |
|---|---|---|---|
| `openclaw-gateway.service` | ACTIVE (running) · PID 2300605 · unidad reporta v2026.6.10 · activo desde 2026-08-07 20:17:37 -04 (4 días) · mem 1.8G (peak 4.4G) · CPU 6h52m · procesos hijos incluyen varias instancias `codex app-server` | `systemctl --user status openclaw-gateway` 2026-08-12 ~05:37 UTC | No |
| `umbral-worker.service` | ACTIVE (running) · PID 85942 · activo desde 2026-07-25 21:30:38 -04 (2 semanas 3 días) · mem 118.9M · Drop-In `copilot-cli.conf` presente (no auditado a fondo en esta pasada) | `systemctl --user status umbral-worker` | Sí — auditar contenido del drop-in `copilot-cli.conf` queda pendiente para un eje posterior |
| `openclaw-dispatcher.service` | ACTIVE (running) · PID 2930054 · activo desde 2026-08-11 10:53:20 -04 (~14h, consistente con hotfixes recientes #625–#627) · mem 61.2M | `systemctl --user status openclaw-dispatcher` | No |
| `mission-control.service` | ACTIVE (running) · PID 3313840 · activo desde 2026-07-19 13:55:52 -04 (~3 semanas) · mem 35.2M | `systemctl --user status mission-control` | No |
| Worker health | `HTTP 200` · `{"ok":true,"version":"0.4.0","tasks_registered":[…~150 tasks]}` · latencia 2ms | `curl -fsS -w '%{http_code} %{time_total}s' http://127.0.0.1:8088/health` | No |
| `openclaw status --all` | Version `2026.7.1-2` · Node `24.18.0` · Gateway local `ws://127.0.0.1:18789` reachable 88ms, auth token · Tailscale exposure **off** · Agents: 8 total, 0 bootstrapping, 2 activos, 31 sesiones · Secrets: **none** · Config warning: `plugins.load.paths` tiene una entrada redundante apuntando al dir de plugins ya empaquetado (`openclaw doctor --fix` lo resuelve) | output completo del comando (sin Environment) | Sí — fix trivial (`openclaw doctor --fix`), candidata a paso 5, no aplicado aquí |
| `crontab -l` | 14 entradas, todas `scripts/vps/*-cron.sh` (o `ops_log_rotate.py`) del repo canónico, log a `/tmp/*.log`. Sin tokens/secretos embebidos — nada que redactar | output completo de `crontab -l` | No |
| `du -sh` ops_log | `~/.config/umbral` (dir real de `ops_logger.py`, default sin override `UMBRAL_OPS_LOG_DIR`) = **22M** | `du -sh ~/.config/umbral` | No |
| `du -sh` transcripts | Ver detalle en §5 (E7) — `~/.openclaw` total **16G** | `du -h --max-depth=1 ~/.openclaw` | Ver E7 |

**E2 gate:** todas las filas con [E], cero servicios failed, cero restart necesario. **PASS.**

## 3. E4-VPS — Drift skills repo↔runtime

| Ítem | Estado observado | Evidencia [E] | ¿Pide decisión? |
|---|---|---|---|
| Skills desplegadas en runtime vivo (`~/.openclaw/skills/`) | **6** activas: `linear-project-auditor`, `linear-delivery-traceability`, `linear-issue-triage`, `n8n-editorial-orchestrator`, `subagent-result-integration`, `editorial-source-curation`. Ninguna trae campo de versión en el frontmatter (solo `name` + `description`) | `find ~/.openclaw/skills -mindepth 1 -maxdepth 1 -type d` | No |
| Skills canónicas en repo (`openclaw/workspace-templates/skills/`) | **86** directorios en `main`@`5b2cc8a` | `find .../openclaw/workspace-templates/skills -mindepth 1 -maxdepth 1 -type d \| wc -l` = 86 | — |
| Ratio desplegado/canónico | **6/86 (~7%)**. El plan cita "42/86 de julio" como contexto histórico explícitamente no heredable como hecho (§0 del plan); esta remedición de agosto da 6/86 — si la cifra de julio era correcta, hay una caída fuerte, no re-observada hasta ahora | cálculo directo sobre los dos `find` anteriores | **Sí** — David decide si el runtime debe re-sincronizarse contra el repo, y si la caída 42→6 amerita causa raíz (candidata a escalar en F2 si se confirma como bug, no solo staleness) |
| Fidelidad de las 6 desplegadas vs plantilla actual | Las 6 **difieren** byte-a-byte de su plantilla en repo — `SKILL.md` en las 6, más `references/*.md` en las 2 que los tienen (`n8n-editorial-orchestrator`, `editorial-source-curation`). Naturaleza exacta del diff no inspeccionada línea a línea (fuera de alcance de una captura de solo lectura) | `diff -rq <template> <deployed>` por cada una de las 6 — las 6 reportan "differ" | Sí — mismo punto que arriba: ¿re-sync o aceptar drift documentado? |
| Skill `openclaw-vps-operator` (la que este diagnóstico debía usar, "modo diagnose") | **Ausente** de `openclaw/workspace-templates/skills/` (no es parte del set de 86 — es un artefacto de otra familia, `.claude/skills/`, pensado para sesiones Claude Code, no para agentes OpenClaw). **Ausente de `main`** en `.claude/skills/` y en `.agents/skills/`. Presente **solo** en la branch protegida `rick-delivery/poller-healthcheck-hardening`, en `.claude/skills/openclaw-vps-operator/SKILL.md` — leída vía `git show <branch>:<path>` (plumbing de solo lectura, el worktree de esa branch en `/home/rick/.openclaw/workspaces/rick-delivery/umbral-agent-stack-poller-hardening` **no fue tocado**). Esa versión no trae campo de versión explícito ni el archivo `references/reference-diagnose.md` que el plan asume que existe | `find` vacío en main; `git ls-tree -r rick-delivery/poller-healthcheck-hardening --name-only \| grep openclaw-vps-operator`; `git show <branch>:<path>` | **Sí** — decidir dónde debe vivir la versión canónica de esta skill y si el modo "diagnose" con `reference-diagnose.md` existe en algún otro lugar no explorado en esta pasada |
| `umbral-skills-registry` (repo canónico versionado citado por el plan, ej. "openclaw-vps-operator 0.1.1", "pkg-receiver 0.5.0") | **No existe** como repo bajo el org `Umbral-Bot` — `gh api repos/Umbral-Bot/umbral-skills-registry` → `404 Not Found`; `gh repo list Umbral-Bot` solo devuelve `umbral-agent-stack` (public) y `notion-governance` (private) | `gh api` + `gh repo list Umbral-Bot --limit 100` | **BLOCKED capa acceso-repo** — no se puede fijar el "tip" canónico citado por el plan para diffear versión; puede ser un repo bajo otro org/host no probado en esta sesión, o un nombre desactualizado |
| Documentación stale (repo dice ≠ runtime muestra) | `CLAUDE.md` (`Working Defaults`) y `.agents/PROTOCOL.md` (§"Para Copilot-VPS") citan `.agents/skills/openclaw-vps-operator/SKILL.md` como lectura obligatoria — ese path **no existe en `main`** | lectura directa de ambos archivos en `main`@`5b2cc8a` | Sí — actualizar la referencia en ambos docs o restaurar el archivo en `main` |
| Bonus (mismo eje, otro subsistema) | `openclaw status --all` reporta warning de config: entrada redundante en `plugins.load.paths` apuntando al dir de plugins ya empaquetado | ver §2, fila `openclaw status --all` | Ya contabilizado arriba |

**E4-VPS gate:** todas las filas con [E] o `BLOCKED` con capa nombrada. **PASS** (como
captura de diagnóstico — el contenido del drift es el hallazgo, no un fallo de la
medición).

## 4. E5 — Notion / n8n (MCP, solo lectura)

| Ítem | Estado observado | Evidencia [E] | ¿Pide decisión? |
|---|---|---|---|
| Notion — página "Control Room" (`NOTION_CONTROL_ROOM_PAGE_ID=30c5f443fb5c80eeb721dc5727b20dca`) | Fetch exitoso. La página real se titula **"OpenClaw"** (no "Control Room" literal — confirma un hallazgo histórico de abril 2026 ya documentado: no existe página con ese título exacto). Página padre: "Sistemas y Automatizaciones". Contenido vivo y reciente: callout "Estado del panel · Actualizado: **2026-08-10 22:00 UTC** · Revisión: 0 · Proyectos: 10"; 10 proyectos con atención, 7 items en Bandeja Puente, 0 entregables pendientes. Vincula bases canónicas reales y activas: 📁 Proyectos — Umbral, 🗂 Tareas — Umbral Agent Stack, 📬 Entregables Rick — Revisión, Alertas del Supervisor, Bandeja Puente, Dashboard Rick, Transcripciones Granola | `notion-fetch id=30c5f443fb5c80eeb721dc5727b20dca` 2026-08-12 ~05:00 UTC | No — funcional. Nota de higiene menor: el nombre del env var (`CONTROL_ROOM`) no coincide con el título real de la página (`OpenClaw`) |
| Notion — búsqueda por texto "Control Room" | Solo devuelve resultados de GitHub (docs/PRs indexados vía el conector), **cero páginas Notion nativas** en el resultado — el backend de búsqueda semántica no indexó la página real por ese término | `notion-search query="Control Room" query_type=internal` | No — mitigado con fetch directo por ID conocido; documentar que la búsqueda por nombre no es confiable para esta página específica |
| n8n — workflows B1/B3 | **BLOCKED capa permiso-cliente/instancia incorrecta.** El conector MCP n8n de esta sesión responde y lista 20 workflows reales, recientes y activos, pero pertenecen a un workspace de temática AEC/Speckle/Workshop docente ("Clasificar y alertar incidencias AEC", "Captura AEC — Incidencias y Fotos", "[S13 Master AEC] Bitácora de incidencias BIM", subworkflows "B-6 Cloud migration (D-058)"…) — **cero coincidencias** para "B1" o "B3" por nombre/descripción. El env VPS declara `N8N_URL=http://127.0.0.1:5678` (loopback local del VPS); el contenido devuelto por el conector MCP no corresponde a esa instancia local | `search_workflows(query="B1")` → 0 · `search_workflows(query="B3")` → 0 · `search_workflows()` sin filtro → 20 resultados ajenos · `grep N8N_URL ~/.config/openclaw/env` | **Sí** — David decide si esta sesión debe recibir el conector n8n correcto (dmbutic/umbralbim), o si el probe B1/B3 queda fuera de alcance de Claude Code hasta que se reconfigure el MCP |
| n8n — bot TEST vs prod, últimas ejecuciones | No resoluble desde este conector (mismo bloqueo de instancia de la fila anterior); no se llamó `search_executions` porque ya había evidencia suficiente de instancia incorrecta y hacerlo no habría agregado señal sobre B1/B3 | ver fila anterior | Ídem |

**E5 gate:** 2 filas con [E] resuelto (Notion), 2 filas `BLOCKED capa permiso-cliente/instancia`
con capa nombrada y evidencia (n8n). **PASS** por criterio del plan (BLOCKED con capa
nombrada cuenta como fila cerrada, no como FAIL de la fase).

## 5. E7 (lado VPS) — Transcripts + evidencia cron/path pcrick

| Ítem | Estado observado | Evidencia [E] | ¿Pide decisión? |
|---|---|---|---|
| Tamaño total `~/.openclaw` | **16G** | `du -h --max-depth=1 ~/.openclaw` | — |
| Desglose — transcripts reales (`agents/`) | **9.2G**, por identidad: `rick-ops` 4.4G, `main` 1.8G, `rick-orchestrator` 1.0G, `rick-qa` 860M, `rick-delivery` 532M, `rick-tracker` 347M, `rick-communication-director` 279M, `rick-linkedin-writer` 49M (última sesión hace 44 días, inactiva), más colas residuales de torneos PIT (~1–2M cada una, varias) | `du -h --max-depth=1 ~/.openclaw/agents` | **Sí** — la cifra heredada de mayo ("transcripts ~16GB") mezclaba dos cosas distintas; con el desglose de hoy, David puede decidir podar `agents/rick-ops` (el mayor, 4.4G) o rotar identidades inactivas como `rick-linkedin-writer` |
| Desglose — caché `npm` (no son transcripts) | **5.1G** en `~/.openclaw/npm` — proyectos node_modules por sesión codex/MCP (ej. `openclaw-npm/projects/openclaw-codex-*`), visibles también como procesos hijos del gateway en §2 | mismo `du` que arriba | Sí — candidato de limpieza independiente de transcripts, no evaluado a fondo aquí |
| `ops_log` (no confundir con transcripts) | 22M — ver §2 | `du -sh ~/.config/umbral` | No |
| Evidencia cron/path hacia pcrick (tailnet `100.109.16.40`) | El monitor de salud interno de `openclaw-dispatcher` (loop async dentro del servicio systemd, no una entrada de `crontab` literal) sondea `http://100.109.16.40:8088/health` cada ~10s — **587 polls exitosos (200 OK) solo hoy**, sin fallos en la ventana de 3 días revisada. `supervisor.sh` (cron cada 5 min, confirmado en `crontab -l` de §2) reporta `Worker: OK` / `Dispatcher: OK` sin restarts ni menciones de pcrick/WinError en su log | `journalctl --user -u openclaw-dispatcher --since "3 days ago"` grep `100.109.16.40` (587 hoy) · `tail /tmp/supervisor.log` | No — el camino pcrick vía tailnet está sano ahora mismo |
| WinError 3 (ítem de banca histórica, path G: pcrick) | **No reproducido** en la ventana revisada del lado VPS (`journalctl` dispatcher 3 días + `supervisor.log`) — nota de alcance: WinError es un código de error de Windows; si el problema persiste, la evidencia primaria estaría del lado Windows (F1), no en logs VPS. Esta fila solo certifica "no visible desde VPS hoy", no "resuelto" | `grep -i "WinError" journalctl` + `supervisor.log` → sin resultados | Sí — F1/Windows debe re-probar del lado que realmente puede reproducir el error; VPS no lo ve actualmente |

**E7-VPS gate:** todas las filas con [E]. **PASS.**

## 6. Gate global F2

```
MEGADIAG_F2_RUNTIME_PASS=Y
```

- E2: PASS — [E] en las 8 filas.
- E4-VPS: PASS — [E] en 6 filas, `BLOCKED capa acceso-repo` nombrado en 1 fila
  (`umbral-skills-registry` inalcanzable).
- E5: PASS — [E] en 2 filas (Notion), `BLOCKED capa permiso-cliente/instancia
  incorrecta` nombrado en 2 filas (n8n).
- E7-VPS: PASS — [E] en las 6 filas.
- STOP conditions del plan: **ninguna se disparó** (cero secretos en stdout, cero
  servicio failed, cero drift de SHA — `origin/main` confirmado en
  `5b2cc8a117a2958c4c7792fb182b9e5f8b5530fc`, coincide con lo esperado `≥5b2cc8a1`).
- Cero mutación de runtime, cero restart, cero edición de `openclaw.json`, cero
  deletes, cero ship de skills. Único efecto en disco: este archivo + el PR draft
  que lo acompaña.

## 7. Decisiones pedidas a David (consolidado)

1. **Drift de skills 6/86 (y caída vs "42/86" de julio si esa cifra era correcta):**
   ¿re-sincronizar el runtime OpenClaw contra `openclaw/workspace-templates/skills/`,
   o es un estado aceptado/intencional que solo falta documentar?
2. **`openclaw-vps-operator` fuera de `main`:** ¿restaurar el archivo en `main` (desde
   la branch `poller-healthcheck-hardening`, actualizado), o formalizar que vive en
   otro lugar? De cualquier forma, `CLAUDE.md` y `.agents/PROTOCOL.md` quedan con una
   referencia rota que conviene corregir.
3. **`umbral-skills-registry` inalcanzable vía `gh` desde esta sesión:** ¿el repo
   vive bajo otro org/nombre, o el diagnóstico de "versión canónica" de skills debe
   anclarse directamente en `openclaw/workspace-templates/skills/` de este repo (que
   sí existe y sí es alcanzable) en vez de un registry externo?
4. **Conector MCP n8n de esta sesión no es el n8n VPS (dmbutic/umbralbim):** ¿se
   puede autorizar/reconectar el MCP correcto, o el probe B1/B3 se marca como fuera
   de alcance de Claude Code hasta nuevo aviso?
5. **Transcripts 9.2G en `agents/` (+ 5.1G de caché `npm` separado):** ¿autorizar
   poda/rotación de `agents/rick-ops` (el mayor) e identidades inactivas como
   `rick-linkedin-writer` (44 días sin uso)?
6. **Config warning `plugins.load.paths` redundante:** fix trivial vía
   `openclaw doctor --fix` — ¿autorizado para un paso posterior (no aplicado en esta
   pasada de solo lectura)?
