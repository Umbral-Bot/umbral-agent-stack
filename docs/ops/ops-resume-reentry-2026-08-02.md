# Runbook: reingreso tras 1–2 días de pausa (Fase A, máquina)

Estado: Fase A del SPLIT faseado que David aprobó 2026-08-02 (`GO_SPLIT_FASEADO`,
ver `docs/operations/ledger-ops-resume.jsonl`). Fase A = SoT máquina en UAS
(este runbook + `scripts/ops_resume_board.py`). Fase B (vista humana en Notion)
está diferida — no forma parte de este documento ni de este PR.

## Por qué existe esto

El discovery de PKG-OPS-RESUME (2026-08-01, ver memoria de Claude
`pkg-ops-resume-discovery.md` y el ledger citado arriba) encontró que **todo
board estático se pudre**: `.agents/board.md` lleva ~3 semanas stale con tres
fechas internas contradictorias, y los dashboards Q2 de `notion-governance`
están congelados desde mayo/junio. La corrección no es "actualizar el board
más seguido" — es dejar de tener un archivo que alguien mantiene a mano y
generar el tablero **on-demand** desde datos que ya se escriben solos: los
ledgers JSONL append-only que define la skill `cursor-orchestrator`.

## Los 5 pasos (lunes después de 2 días)

1. **Traer PRs y ramas frescas.**
   ```bash
   git -C C:\GitHub\umbral-agent-stack fetch
   gh pr list --repo Umbral-Bot/umbral-agent-stack --state open
   ```
2. **Correr el generador** (este script) para ver el estado vigente de todos
   los frentes/paquetes que tienen ledger, con sus pelotas abiertas y stale:
   ```bash
   python scripts/ops_resume_board.py
   ```
3. **Leer la memoria persistente de Claude** (`C:\Users\david\.claude\projects\C--GitHub-umbral-agent-stack\memory\MEMORY.md`)
   — índice de frentes con estado DONE/OPEN/BLOQUEADO por sesión.
4. **Revisar qué se documentó al cerrar cada sesión reciente:**
   ```bash
   git -C C:\GitHub\umbral-agent-stack log --since="4 days ago" -- docs/ops docs/operations
   ```
5. **De 1–4, extraer la lista de "pelotas de David"** (paquetes en `REPORTADO`
   esperando veredicto, gates humanos pendientes, PRs abiertos sin merge) y
   decidir: mergear, emitir paquete nuevo, o marcar `BLOCKED`.

## Cómo correr el script

```bash
# Tablero humano, root = carpeta padre de este repo (normalmente C:\GitHub)
python scripts/ops_resume_board.py

# Salida JSON (para scripting/CI)
python scripts/ops_resume_board.py --json

# Otra carpeta contenedora de repos
python scripts/ops_resume_board.py --root D:\Code

# + PRs abiertos por repo con ledger (red, requiere gh autenticado; best-effort)
python scripts/ops_resume_board.py --with-prs

# Umbral de staleness distinto a 24h
python scripts/ops_resume_board.py --stale-hours 12
```

El script barre `<root>/*/docs/operations/ledger-*.jsonl` — no asume que todos
los repos vivan en un mismo monorepo; cada programa mantiene su propio ledger
en su propio repo (ver `docs/operations/README.md`). Repos ausentes o sin esa
carpeta se ignoran sin error.

### Lectura del output

- Cada bloque `=== frente ===` agrupa por `pkg`, y cada fila es la
  **última línea del ledger** para ese `(frente, pkg, dest)` — el estado
  vigente, no el historial completo.
- `[CERRADO]` = evento terminal (`PASS|FAIL|CERRADO`). `BLOCKED`/`NO_ACK` se
  muestran como **abiertos** a propósito — ver
  "Clasificación terminal/abierto" en `docs/operations/README.md` para la
  razón (desviación deliberada del enum literal de la misión original, para
  no esconder paquetes bloqueados).
- `[STALE>Nh]` = quedó en `EMITIDO`/`ACK` sin evento posterior por más de N
  horas — señal de "pelota perdida", no un hecho verificado (ver
  limitaciones abajo).
- `[DRIFT]` = el valor de `evento` no está en el enum de la spec
  (`docs/operations/README.md` documenta los valores drift ya vistos:
  `PENDING`, `DEPLOYED`, `DEPLOY_STARTED`, `MERGED`, `MERGED_DEPLOYED`). No
  se descarta la fila — se muestra igual, marcada.

## Cadencia de escritura del ledger (PREP-A2, 2026-08-04)

Este runbook lee `docs/operations/ledger-*.jsonl` para generar el tablero.
El tablero solo sirve si el ledger se escribe **cuando el evento ocurre**,
no reconstruido de memoria días después. Regla de cadencia:

1. **Al EMITIR un paquete, integrar un reporte, o cerrar un gate** (`PASS`,
   `FAIL`, `BLOCKED`, `NO_ACK`, `REEMISION`) — append 1 línea al ledger del
   programa correspondiente en ese momento, no al final de la sesión ni en
   una sesión posterior. Única excepción: backfill explícito de eventos que
   ya ocurrieron y quedaron fuera del ledger (como el de `PKG-OPS-RESUME-A1`
   hecho en PKG-OPS-RESUME-A2) — se permite, pero la `nota` debe decir
   `retroactivo` y el `ts` debe ser el del evento real, no el de la sesión
   que lo backfillea.
2. **Nunca marcar `PASS`/`FAIL`/`CERRADO` antes de que el hecho sea cierto**
   (ej. un PR mergeado, no solo abierto). `scripts/ops_resume_board.py`
   trata esos eventos como terminales y los oculta del tablero — un `PASS`
   prematuro esconde exactamente la "pelota de David" que este runbook
   existe para mostrar. Mientras el gate es solo `*_CODE_PASS` (código/docs
   listos, merge humano pendiente), el evento correcto es `REPORTADO`.
3. **Commitear el ledger en el mismo PR/ciclo cuando sea posible.** Un
   ledger editado solo en el filesystem local (sin commit) no es SoT — es el
   mismo riesgo que dejar cambios solo en `git stash`: se pierde sin aviso
   ante un `git clean`, una reinstalación de máquina, o un worktree nuevo.
   Si el paquete todavía no cierra, commitear igual el evento
   `EMITIDO`/`ACK`/`REPORTADO` apenas ocurre; el evento de cierre puede ir
   en un commit posterior dentro del mismo PR.
4. **Antes de retomar tras una pausa**, correr el generador (ver "Cómo
   correr el script" arriba) — no confiar en memoria ni en
   `.agents/board.md`.
5. **Notion (Fase B) será espejo, no fuente.** Cuando Fase B active la
   sincronización a Notion, ese dashboard **lee** de estos ledgers — nunca
   al revés. Ante cualquier discrepancia entre Notion y un `ledger-*.jsonl`,
   el ledger manda.

> **Actualización 2026-08-20 — el cierre no tiene dueño:** los dos únicos
> cierres del frente hasta ahora (A1 y A2) entraron al ledger como backfill
> retroactivo. Causa estructural: el evento `PASS` nace en el merge, que
> ejecuta Cursor/David *después* de que el PR del paquete quedó cerrado, y la
> regla 3 no le asigna dueño a ese append. Interinamente: el append del
> cierre es de quien mergea; si no ocurre, la primera sesión que detecte el
> merge lo backfillea (nota `retroactivo`, `ts` real del merge). Fix durable
> pendiente: un check post-merge en CI que cruce el tag `PKG-*` del commit
> contra el último evento del ledger y avise si falta el terminal.

## Delimitación (qué NO es esto)

| Superficie | Qué es | Por qué esto no la reemplaza |
|---|---|---|
| `.agents/board.md` | Tablero manual por sprint | Es exactamente el patrón que falló (stale, mantenido a mano). Este generador no lo actualiza ni lo lee; queda como está hasta que David decida qué hacer con él. |
| Mission Control (`mission_control/`, :8089) | Dashboard read-only sobre **runtime VPS** (OpenClaw, Redis, PIT vault) | Lee estado de ejecución de agentes en la VPS, no el ledger de paquetes/frentes de este repo. Es un link secundario runtime-only según el GO de David — no el home del tablero de reingreso. |
| OpenClaw / Control Room (Notion) | Runtime cockpit humano de Rick | Fase B diferida. Este generador no escribe en Notion ni sustituye esa superficie. |
| `docs/operations/ledger-*.jsonl` | **Fuente de verdad de este tablero** | Es lo único que este script lee. Append-only, nunca se edita a mano salvo para agregar líneas. |

## Limitaciones conocidas (honestas)

- **Staleness es aproximada, no un SLA.** Los timestamps de los ledgers reales
  mezclan formatos con y sin zona horaria (`2026-08-01T12:40` vs
  `2026-08-01T04:55:00Z`). El script normaliza lo que tiene zona a UTC y
  asume que lo que no tiene zona ya está en esa misma escala — puede haber
  unas horas de error. Es una señal de alerta para mirar, no un hecho
  verificado.
- **Solo entiende el schema `{ts, pkg, frente, dest, evento, ev, nota}`.**
  En el barrido real de 2026-08-02 sobre `C:\GitHub` apareció al menos un
  ledger (`umbral-bot-cursor/docs/operations/ledger-microsoft-marketplace-2026-08.jsonl`)
  con un schema distinto (`package`/`event`/`agent` en vez de
  `pkg`/`evento`/`dest`, sin campo `frente`). El script no lo interpreta —
  esas filas caen en `(sin-frente)/(sin-pkg)` marcadas `DRIFT`, visibles pero
  sin agrupar bien. No se intentó normalizar ese schema alterno en este PR
  (fuera de alcance); si se vuelve común, es candidato a una propuesta de
  schema como las de `docs/operations/README.md`.
- **`--with-prs` es best-effort y depende de `gh` autenticado localmente.**
  Si falla (sin red, sin `gh`, repo sin remoto), el tablero lo reporta como
  "gap honesto" por repo y sigue mostrando el resto — nunca aborta.
- **No hay reconciliación automática de duplicados/reemisiones.** Si un
  paquete se reemite (`REEMISION`), la fila anterior simplemente deja de
  aparecer como "vigente" — el historial completo sigue estando en el
  archivo `.jsonl`, el generador solo muestra el último estado.
