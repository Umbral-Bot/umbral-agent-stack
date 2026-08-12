# Mega-diagnóstico general 2026-08 — PLAN (paso 3 del programa macro)

> **Status:** PLAN — este documento NO ejecuta nada. Es el paso 3 del programa macro de
> David 2026-08-11 (`docs/operations/macro-plan-2026-08-11.md`, hoja viva untracked en el
> clon de David; ledger `ledger-macro-hygiene-2026-08-11.jsonl`).
> **Emitido por:** PKG-MACRO-MEGADIAG-PLAN (Claude Fable, 2026-08-12).
> **Base:** `main` @ `bbe7248f` (#628, acta higiene VPS P5).
> **PR:** draft docs-only, label `do-not-merge`. La ejecución va en un PKG posterior
> (PKG-MACRO-MEGADIAG-EXEC) con el modelo recomendado en §5.

## 0. Contexto y relación con la semilla de mayo

Existe un mega-diagnóstico previo del 2026-05-20 (rama origin
`docs/workspace-megadiagnostico-2026-05-20` @ `3d95798`; working copy archivada en
`C:\GitHub\_archive\workspace-hygiene-2026-08-11\nga-megadiag\`). **Es histórico, no
estado actual**: describe un workspace pre-higiene (6 repos multi-root, conflicto UU en
`supervisor.sh`, clone copilot divergido 944/1289, arco O16 recién cerrado). Todo eso fue
barrido por los packs 1–4 Windows + P5 VPS del paso 1 (2026-08-11). De la semilla se
reutiliza **solo la forma**, que demostró funcionar:

- inventario por superficie con tabla path/branch/dirty/stashes/acción,
- delta "declarado vs observado" contra el roadmap,
- matriz de hilos vivos con bloqueos,
- prompt read-only autocontenido para la superficie VPS con STOP conditions,
- PR draft `do-not-merge` como acta que se mergea al final.

Ningún hallazgo de mayo se copia como hecho: todo se re-observa.

### Qué cambió desde mayo (por qué se replanifica)

- Paso 1 (higiene) CASI CERRADO: origin UAS = `main` + `rick/stage7_5-multiformat`
  (KEEP); clones Windows y VPS reducidos a canónicos; ~800 ramas locales clasificadas y
  eliminadas con evidencia; exports en `C:\GitHub\_archive\workspace-hygiene-2026-08-11\`.
- Paso 2 (capitalize) CERRADO: pkg-receiver 0.5.0, openclaw-vps-operator 0.1.1,
  skills-capitalize 0.1.10, cursor-orchestrator 0.9.0 (registry @ `d5dda4d`).
- El problema ya no es "dónde está el trabajo perdido" (eso lo respondió el paso 1);
  ahora es **"qué tenemos realmente funcionando, qué está degradado y qué es fósil"**,
  como insumo del paso 4 (reconteo intención vs logrado) y del paso 5 (decidir qué
  implementar).

## 1. Alcance

### IN

| Superficie | Detalle | Modo |
|---|---|---|
| Repo `umbral-agent-stack` (origin + clones Windows + VPS) | código, contratos, CI, docs (~150 archivos en `docs/`), scripts, skills embebidas | solo lectura |
| VPS Hostinger (usuario rick) | servicios systemd --user (gateway OpenClaw, worker, dispatcher, poller), crons/timers, config `~/.openclaw/`, disco, transcripts | solo lectura (vía Claude Remote-SSH) |
| Notion (superficies operativas) | Control Room, Publicaciones, gobernanza V2, surfaces del poller | solo lectura (MCP) |
| `umbral-skills-registry` | versiones canónicas vs lo cargado en runtimes (drift) | **solo lectura** — este diagnóstico jamás escribe el registry (un solo escritor) |
| n8n (instancias dmbutic + umbralbim) | workflows activos vs archivados, bot TEST vs prod, credenciales referenciadas | solo lectura (MCP) |
| Repos satélite: `notion-governance`, `dynamo-mcp`, `visor-ifc` | solo estado git/WIP + si su runtime declarado sigue vivo; sin diagnóstico interno profundo | solo lectura |
| Banca abierta del macro-plan | path G: WinError 3 pcrick, `VM_URL` vestigial, transcripts ~16 GB, CI Publicaciones 0.2.0 vs fixtures | re-verificar y costear, no cerrar |

### OUT

- **`umbral-bot-2` (producto):** OUT por defecto, pendiente decisión binaria de David
  (ver TU TURNO del REPORT). Si David dice SÍ, entra solo como eje adicional E7-bis con
  el mismo patrón (estado git ya lo cubrió pack 3; se agregaría runtime/deploy/CI del
  producto). La semilla de mayo también lo excluía.
- Ejecutar fixes, borrar, mergear, reautenticar, reiniciar servicios: **nada de eso**.
  Todo hallazgo se registra como fila con evidencia; la acción va a pasos 5–7.
- Stashes KEEP, WIP protegidos (umbral-bot-claude foro, umbral-bot-cursor beta-3,
  notion-governance-cursor, dynamo-mcp, visor-ifc, skills-registry dirty): se
  inventarían como filas de decisión, no se abren ni se tocan.
- `rick/stage7_5-multiformat` y worktree `poller-hardening`: no tocar (regla del programa).
- Azure/Foundry infra profunda, Linear, RRSS externas: fuera salvo mención incidental.

## 2. Ejes de diagnóstico (7)

Cada eje responde UNA pregunta y define su evidencia mínima [E]. Formato de salida
uniforme: tabla de filas `ítem | estado observado | evidencia | ¿pide decisión?`.

| # | Eje | Pregunta que responde | Evidencia mínima [E] |
|---|---|---|---|
| E1 | **Workspace y git post-higiene** | ¿Se cumple el criterio de cierre del paso 1 y qué residual queda (dirty WIP, forge 70 dirty, stashes KEEP, 58 huérfanas sin merge-base, heads de otros repos)? | `git status -sb` + `stash list` + `worktree list` por clon canónico; `ls C:\GitHub` vs lista esperada de 47; `git ls-remote --heads` por repo |
| E2 | **Runtime VPS** | ¿Qué servicios corren, con qué versión, sanos o degradados, y qué consume disco? | `systemctl --user status` (Active/PID, sin Environment), `/health` de worker/dispatcher, `openclaw status --all`, `crontab -l` redactado, `du -sh` de transcripts/ops_log |
| E3 | **Contratos, CI y tests** | ¿Qué gates automáticos existen, cuáles están rojos y por qué (empezando por Publicaciones 0.2.0 vs fixtures)? | `gh run list` últimas corridas por workflow + log del job rojo; inventario `.github/workflows/` + suites de test y su último resultado local |
| E4 | **Skills y drift repo↔runtime** | ¿Qué versiones canónicas del registry están realmente cargadas en cada runtime (VPS OpenClaw, Windows Claude/Cursor/Codex) y dónde hay drift? | tabla slug → versión canónica (`umbral-skills-registry` @ tip) vs versión desplegada (path + frontmatter en cada runtime); el drift 42/86 de julio se re-mide, no se hereda |
| E5 | **Superficies Notion + n8n** | ¿Qué superficies/workflows están vivos y gobernados (V2) vs muertos o en modo TEST olvidado? | lectura MCP: estado del poller Control Room, últimas ejecuciones de B1/B3 en n8n, bot TEST vs prod, páginas canónicas con timestamp de última escritura |
| E6 | **Intención vs realidad documental** | De los sistemas que `docs/` y el roadmap declaran (contratos supervisor 70–77, copilot-cli F1–F8, Granola 50–60, editorial, torneos…), ¿cuáles tienen runtime vivo hoy, cuáles quedaron en evidencia histórica y cuáles nunca se activaron? | matriz doc/sistema → {VIVO, DEGRADADO, FÓSIL, NUNCA_ACTIVADO} con al menos 1 probe por fila (servicio, cron, endpoint, o commit de evidencia + ausencia de runtime) |
| E7 | **Banca y riesgos abiertos** | Para cada ítem de banca: ¿sigue vigente, cuál es el costo de cerrarlo y qué decisión pide? | re-probe de cada uno: cron pcrick + WinError 3 en logs; `grep VM_URL` en código + env; `du` transcripts; run CI rojo citado en E3 |

Máximo 8 ejes respetado. E6 es el eje puente hacia el paso 4: su matriz ES el borrador
del reconteo de funciones (ver §7).

## 3. Método por superficie

### Windows (clones `C:\GitHub`)

- Agente: Claude en clon canónico `umbral-agent-stack-claude` (este mismo patrón PKG).
- Comandos: `git status/stash/worktree/ls-remote`, `gh run list`, `gh pr list`, Grep/Read
  sobre `docs/` y `scripts/`. Cero mutación: sin fetch destructivo, sin checkout de WIP
  ajeno, sin abrir stashes.
- E1, E3 (parte gh), E4 (parte Windows), E6, E7 (VM_URL/CI) se resuelven aquí.

### VPS (Claude Remote-SSH, usuario rick)

- Skill `openclaw-vps-operator` en modo **diagnose** (`references/reference-diagnose.md`)
  — nunca mutate ni auth en este diagnóstico.
- Prompt read-only autocontenido, heredero del Anexo A de mayo pero actualizado a la
  topología actual (3 locales KEEP, worktree poller, dispatcher con prefijos
  windows./browser./gui.). STOP conditions del anexo se mantienen (drift de SHA, secreto
  en stdout, servicio failed → parar y reportar).
- Prohibiciones literales: no restart, no pull/checkout/stash, no editar
  `~/.openclaw/openclaw.json`, no imprimir Environment/tokens.
- E2, E4 (parte VPS), E7 (transcripts, cron pcrick del lado VPS) se resuelven aquí.

### Notion / n8n (MCP, solo lectura)

- Notion vía MCP con gobernanza `notion-governance-runtime` presente: solo `fetch`/
  `search`/`query`, cero writes, cero archive.
- n8n vía MCP oficial: `search_workflows`, `get_workflow_details`, `search_executions` —
  nunca `update/publish/execute`.
- E5 se resuelve aquí; si un MCP no está autenticado en la sesión de ejecución, la fila
  queda `BLOCKED capa permiso-cliente` con la sonda que lo demuestra (no se adivina).

### Regla transversal de evidencia

Toda fila del diagnóstico lleva [E] = comando + salida literal recortada (o URL/SHA/run
ID) + timestamp. Sin [E] la fila es `PENDING`, nunca un estado afirmado. Secretos/PII
prohibidos en el reporte (regla dura del protocolo receptor).

## 4. Orden de ejecución y modelo por fase

La ejecución (PKG-MACRO-MEGADIAG-EXEC, futuro) se corta en 4 fases. Los ejes mecánicos
van con modelo barato; la síntesis y el eje puente van con modelo profundo.

| Fase | Ejes | Superficie | Modelo recomendado | Gate | Justificación |
|---|---|---|---|---|---|
| F1 — Inventario mecánico | E1 + E7 (probes) | Windows | **Sonnet** (barato; comandos + tablas, cero juicio) | `MEGADIAG_F1_INVENTORY_PASS` | trabajo enumerativo con criterio ya escrito (checklist §"criterio de cierre" del macro-plan) |
| F2 — Runtime vivo | E2 + E4-VPS + E5 | VPS (Remote-SSH) + MCP Notion/n8n | **Sonnet** para captura; escalar a **Opus/Fable** solo si aparece anomalía que exige diagnóstico causal | `MEGADIAG_F2_RUNTIME_PASS` | lecturas pautadas con STOP conditions; el prompt hace el trabajo, no el modelo |
| F3 — CI y drift | E3 + E4-Windows | Windows + gh | **Opus** (leer logs de CI rojo y clasificar deuda requiere juicio medio) | `MEGADIAG_F3_CONTRACTS_PASS` | distinguir "fixture desactualizado" de "contrato roto" es interpretación, no captura |
| F4 — Síntesis intención vs realidad | E6 + consolidado de F1–F3 | Windows (docs) + resultados previos | **Fable** (el corazón del diagnóstico: clasificar ~40 sistemas declarados en VIVO/DEGRADADO/FÓSIL/NUNCA_ACTIVADO y proponer la matriz del paso 4) | `MEGADIAG_F4_SYNTHESIS_PASS` | máxima densidad de juicio; errores aquí contaminan pasos 4–5 |

- F1 y F2 pueden correr en paralelo (superficies disjuntas). F3 espera F1 (usa su
  inventario de workflows). F4 espera todo.
- Cada fase cierra con su gate marcado en el acta de ejecución con [E]; el gate global
  `MEGADIAG_EXEC_PASS` = las 4 fases en PASS o en BLOCKED justificado con capa nombrada.
- Presupuesto orientativo: F1/F2 son 1 sesión cada una; F3 media sesión; F4 una sesión
  larga de Fable. Si una fase excede su ventana de contexto, cierre `PARTIAL` con punto
  de reanudación (regla de agotamiento del protocolo receptor).

## 5. Entregables de la ejecución (definidos ahora, producidos después)

1. `docs/operations/megadiag-2026-08-report.md` — acta única con las tablas de los 7
   ejes, los 4 gates y la matriz E6. Mismo patrón de PR draft docs-only.
2. Actualización de la hoja viva `macro-plan-2026-08-11.md` (la hace Cursor al trackear,
   no el ejecutor).
3. Cero mutación de runtime, cero deletes, cero ship de skills. Si la ejecución descubre
   un fix trivial, se anota como fila candidata para paso 5 — no se aplica.

## 6. Criterios de done de la ejecución

- Los 7 ejes tienen todas sus filas en estado con [E] o `BLOCKED` con capa nombrada.
- Ningún hallazgo de mayo citado como actual sin re-probe de agosto.
- La banca del macro-plan queda re-verificada con costo estimado por ítem (E7), sin
  cerrarse en silencio.
- La matriz E6 cubre como mínimo: contratos supervisor/OODA (docs 70–77), cadena
  copilot-cli F1–F8, pipeline Granola (50–60, 64–65, 78), pipeline editorial
  (67–68, editorial-pipeline/), torneos (69, 79), dispatcher/panel (#617–#627),
  poller Control Room, y los workflows n8n B1/B3.

## 7. Cómo alimenta el paso 4 (reconteo de funciones)

El paso 4 pide "intenciones declaradas vs cosas logradas". Este plan lo pre-cablea:

- **La matriz E6 es el barrido de intenciones**: cada doc/sistema declarado se convierte
  en una fila con estado observado. El paso 4 no arranca de cero: arranca de esa matriz
  y le agrega la dimensión "¿la intención sigue vigente para el sistema de trabajo
  actual de David?" — que es juicio humano + Fable, no probe.
- **E3 aporta la columna "logrado verificable"**: qué tiene test/CI verde es "logrado
  con red"; qué funciona sin gate es "logrado frágil".
- **E7 aporta el costo residual**: intenciones a medio cerrar con precio conocido.
- Salida esperada del paso 4: la misma matriz re-puntuada con David decidiendo por fila
  {mantener, acotar, cambiar, matar} — que es exactamente el insumo del paso 5.

## 8. Riesgos del plan

| Riesgo | Mitigación |
|---|---|
| MCP Notion/n8n sin auth en la sesión de ejecución | filas `BLOCKED capa permiso-cliente`; F2 no se declara FAIL por eso |
| E6 explota en tamaño (~150 docs) | E6 clasifica **sistemas** (≈40), no archivos; docs se agrupan por sistema; lo no mapeado queda en una fila "cola sin clasificar" explícita |
| Deriva a "arreglar mientras diagnostico" | prohibición dura §1-OUT + gates que solo aceptan lectura como evidencia |
| Doble escritor sobre skills-registry | E4 es solo lectura del registry; cualquier corrección de drift va a paso 5 |
| Semilla de mayo contamina como hecho | regla §0 + criterio de done "sin re-probe no se cita" |
