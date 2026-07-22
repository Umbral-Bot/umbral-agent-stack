# PIT / Torneos — ARCHIVED / HOLD (2026-07-22)

**Estado:** `PIT_TOURNAMENT_ARCHIVED`
**Decisión:** David no quiere torneos por ahora. Superficies de torneo/PIT quedan **desactivadas y archivadas** hasta un **GO explícito de David**.
**Alcance:** desactivación reversible a nivel runtime (gateway config). **No** se instaló, buildeó ni habilitó el plugin `umbral-tournament-github`. **No** se tocó editorial/Publicaciones, gates, `gpt-5.6-sol`, OAuth ni el plugin `umbral-worker` Notion.

## Qué estaba activo antes

Runtime `~/.openclaw/openclaw.json` (config viva del gateway, **no** versionada en repo):

| Superficie | Estado previo |
|---|---|
| `plugins.allow[]` | incluía `umbral-tournament-github` |
| `plugins.load.paths[]` | apuntaba a `openclaw/extensions/umbral-tournament-github` (sin `dist/` → packaging gap) |
| `plugins.entries.umbral-tournament-github` | `enabled: true` (+ config baseUrl/tokenFile/defaultRepoPath) |
| `agents.list[].tools.alsoAllow` (rick-delivery, rick-ops) | 5 tools phantom `umbral_tournament_{preflight,create_lane_branch,commit_and_push,open_pr,verify_pr}` |
| `skills.entries.tournament-github-cli` / `umbral-tournament-github` | ya `enabled: false` |

**Realidad de carga:** el plugin `umbral-tournament-github` **nunca cargaba** — mismo gap de packaging que tuvo `umbral-worker` (sin `dist/`, sin install record). Las tools `umbral_tournament_*` eran entradas **phantom** en allowlists: no estaban registradas como usables. No había cron, systemd unit ni timer de torneo/PIT.

## Cambios aplicados (reversibles)

Solo runtime (`~/.openclaw/openclaw.json`), con backup:

1. `plugins.allow[]` — removido `umbral-tournament-github`.
2. `plugins.load.paths[]` — removida la ruta del extension de torneo.
3. `plugins.entries.umbral-tournament-github.enabled` — `true → false` (bloque `config` conservado para reversibilidad).
4. `agents.list[].tools.alsoAllow` — removidas las 5 tools phantom `umbral_tournament_*` en `rick-delivery` y `rick-ops`.

Backup: `~/openclaw-backups/openclaw.json.pre-pit-archive.<TS>` (sin secretos en este doc).
Gateway reiniciado (`openclaw-gateway.service`) y verificado.

## Superficie latente NO tocada (intencional)

El binario **umbral-worker** (`:8088`, v0.4.0) aún registra handlers server-side de torneo/PIT:
`tournament.run`, `tournament_lane.*`, `pit.preflight`, `pit.lane_init`, `pit.iteration_close`, `pit.lane_announce`, `github.orchestrate_tournament`.

Estos viven **dentro** de `umbral-worker` (LIVE, PR #548) y solo son alcanzables por POST HTTP autenticado directo al worker — **no** hay tool de agente, cron ni trigger que los invoque tras este cambio. Se dejan intactos porque tocarlos implicaría **debilitar `umbral-worker`** (fuera de alcance / prohibido en este pase). Quedan dormidos, no cableados.

## Reversión (cuando David dé GO)

1. Restaurar backup o volver a poner en `~/.openclaw/openclaw.json`: `umbral-tournament-github` en `plugins.allow` + `load.paths`, `entries...enabled: true`, y las 5 tools en `alsoAllow`.
2. **Cerrar el packaging gap** del extension (`umbral-tournament-github`) igual que se hizo con `umbral-worker` en PR #548 (build `dist/` + package.json + install record + contracts.tools). Sin esto el plugin no carga aunque esté `enabled`.
3. Reiniciar gateway y verificar que `umbral_tournament_*` aparezcan registradas.

## Verificación post-cambio

- Gateway: `{"ok":true,"status":"live"}`, service active, 8 agents.
- `umbral-worker`: enabled, `dist/index.js` v0.1.0 — intacto.
- Notion vivo: worker `/health` lista `ping`, `notion.read_page`, `notion.add_comment`, `notion.poll_comments`, … ; agents conservan `umbral_notion_read_page`, `umbral_ping`.
- Torneo desactivado: `umbral-tournament-github` reportado como `plugin not found (stale config entry ignored)`; **0** tools `umbral_tournament_*`; **0** en `plugins.allow`; **0** en `alsoAllow`; **0** crons/timers.
