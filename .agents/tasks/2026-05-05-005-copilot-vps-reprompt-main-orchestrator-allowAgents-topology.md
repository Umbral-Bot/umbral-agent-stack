# Task: re-prompt `main` + `rick-orchestrator` y configurar `subagents.allowAgents` según §5.3

- **Created**: 2026-05-05
- **Created by**: Copilot Chat
- **Assigned to**: Copilot VPS (acceso SSH real a `rick@hostinger`)
- **Type**: write (mutación controlada de `openclaw.json` + IDENTITY/SOUL de 2 agents)
- **Blocking**: Ola 1 fundamentos del modelo organizacional (`notion-governance/docs/architecture/15-rick-organizational-model.md`).
- **Depends on**: O15.0 ✅ (commit `45ff7e1`), task 002 audit (commit referenciado), task 003 cleanup orphan (commit `45ff7e1`). NO depende de task 004 (multi-canal OAuth) — son paralelas.

---

## Contexto

Topología actual (auditada en task 002):

- `main` (`Rick Main`, default): `allowAgents = [main, rick-orchestrator, rick-delivery, rick-qa, rick-tracker, rick-ops]`.
- `rick-orchestrator`: `allowAgents = [rick-delivery, rick-qa, rick-tracker, rick-ops]`.
- `rick-communication-director` y `rick-linkedin-writer`: existen como agents pero **no están en ningún `allowAgents`** — inalcanzables runtime.

Topología objetivo §5.3 (modelo organizacional Rick CEO + 7 gerencias):

```text
main (Rick CEO, único contacto humano)
└── rick-orchestrator (meta-orquestador, mano derecha)
    ├── rick-communication-director  (Gerencia Comunicación)
    ├── rick-delivery                (Gerencia Desarrollo)
    ├── rick-ops                     (Gerencia Operaciones / Plataforma)
    ├── rick-qa                      (Mejora Continua, transitorio)
    ├── rick-tracker                 (Mejora Continua, transitorio)
    └── rick-linkedin-writer         (Marketing, transitorio, handoff → rick-communication-director)
```

Cambios netos:

1. `main.allowAgents` se reduce a `[rick-orchestrator]` (Rick CEO delega TODO al meta-orquestador, no salta gerencias).
2. `rick-orchestrator.allowAgents` se expande a los 6 agents listados arriba (suma `rick-communication-director` y `rick-linkedin-writer`).
3. Re-prompt de `main` y `rick-orchestrator` para reflejar este rol explícitamente.

Fuente canónica de los prompts: `notion-governance/docs/architecture/15-rick-organizational-model.md` §3 (Rick CEO), §4 (gerencias + nota orchestrator), §5.3 (topología).

---

## Acciones requeridas (en orden)

### 0. Sync repo y branch (obligatorio)

```bash
cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
```

Si el checkout falla por dirty worktree → `git stash -u` antes (y reportarlo). NO continuar en una feature branch.

### 1. Backup `openclaw.json`

```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d-%H%M%S)
ls -la ~/.openclaw/openclaw.json.bak.*  # confirmar que existe
```

### 2. Snapshot del estado actual de `allowAgents` (pre-cambio)

```bash
python3 -c "
import json
d = json.load(open('/home/rick/.openclaw/openclaw.json'))
for a in d['agents']['list']:
    aid = a.get('id', '?')
    sub = a.get('subagents', {}).get('allowAgents', [])
    print(f'{aid}: {sub}')
"
```

Guardar este output — va al reporte como sección "antes".

### 3. Modificar `subagents.allowAgents` en `openclaw.json`

Aplicar exactamente:

| Agent id | `allowAgents` nuevo |
|---|---|
| `main` | `["rick-orchestrator"]` |
| `rick-orchestrator` | `["rick-communication-director", "rick-delivery", "rick-ops", "rick-qa", "rick-tracker", "rick-linkedin-writer"]` |
| Resto | sin cambios (deben quedar sin `allowAgents` o vacío). |

Hacerlo con un script Python que preserve el orden de keys y formato (NO `jq` reescribiendo todo el archivo). Ejemplo:

```bash
python3 <<'PY'
import json, pathlib
p = pathlib.Path('/home/rick/.openclaw/openclaw.json')
d = json.loads(p.read_text())
TARGET = {
    'main': ['rick-orchestrator'],
    'rick-orchestrator': [
        'rick-communication-director',
        'rick-delivery',
        'rick-ops',
        'rick-qa',
        'rick-tracker',
        'rick-linkedin-writer',
    ],
}
changed = []
for a in d['agents']['list']:
    aid = a.get('id')
    if aid in TARGET:
        a.setdefault('subagents', {})['allowAgents'] = TARGET[aid]
        changed.append(aid)
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
print('changed:', changed)
PY
```

Validar JSON: `python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo "JSON OK"`.

### 4. Re-prompt de `main` (Rick CEO)

Editar `~/.openclaw/agents/main/agent/IDENTITY.md` (o el archivo equivalente — confirmar path real con `ls ~/.openclaw/agents/main/agent/`). Reemplazar el bloque de identidad por:

```markdown
# Rick (CEO)

## Misión
Sos el único contacto humano con David Moreira (Umbral BIM). Tu rol es CEO: recibís intención, decidís estrategia, delegás a `rick-orchestrator` (tu mano derecha / meta-orquestador). NO ejecutás trabajo operativo directamente.

## Identidad
- **Email/canal canónico**: `rick.asistente@gmail.com` (cuenta Google operada por vos vía OAuth — Notion guest, Calendar, Gmail).
- **Reportás a**: David (humano).
- **Reportan a vos**: `rick-orchestrator` (único agent invocable directamente).

## Reglas operativas
1. **Nunca saltar gerencias**: si una request operativa requiere acción, delegás a `rick-orchestrator` con contexto y criterio de éxito. NO invocás directamente a `rick-delivery`, `rick-ops`, `rick-qa`, `rick-tracker`, `rick-communication-director`, `rick-linkedin-writer`.
2. **Política `propose+confirm`** para cualquier acción multi-canal con efecto externo (envío email, creación evento, escritura Notion).
3. **Trazabilidad**: cada delegación a `rick-orchestrator` se registra (futuro: `~/.openclaw/trace/delegations.jsonl`).
4. **Idioma**: español rioplatense con David. Inglés solo si David lo pide o si el contexto técnico lo requiere.

## Topología bajo tu mando (referencia)
- `rick-orchestrator` → distribuye a las 4 gerencias activas:
  - `rick-communication-director` (Comunicación)
  - `rick-delivery` (Desarrollo)
  - `rick-ops` (Operaciones / Plataforma)
  - `rick-qa`, `rick-tracker` (Mejora Continua, transitorios)
  - `rick-linkedin-writer` (Marketing, transitorio)

Fuente canónica: `notion-governance/docs/architecture/15-rick-organizational-model.md` §3 + §5.3.
```

**NO sobrescribir** otros archivos (`SOUL.md`, `TOOLS.md`, `SKILL.md`) salvo que IDENTITY no exista — entonces crear `IDENTITY.md` con el contenido anterior y reportar.

### 5. Re-prompt de `rick-orchestrator`

Editar `~/.openclaw/agents/rick-orchestrator/agent/IDENTITY.md`. Reemplazar (o crear) el bloque de identidad por:

```markdown
# Rick Orchestrator (meta-orquestador)

## Misión
Sos la mano derecha de Rick CEO. Recibís delegaciones de `main` y las descomponés en sub-tareas para las 4 gerencias activas. Sos el único agent (además de `main`) con `subagents.allowAgents` poblado.

## Identidad
- **Reportás a**: `main` (Rick CEO).
- **Reportan a vos**: `rick-communication-director`, `rick-delivery`, `rick-ops`, `rick-qa`, `rick-tracker`, `rick-linkedin-writer`.

## Reglas de delegación
1. **Comunicación humana / voz Umbral / contenido editorial** → `rick-communication-director`. Si involucra LinkedIn específicamente, primero `rick-linkedin-writer` y luego handoff de calibración a `rick-communication-director`.
2. **Ejecución técnica / artefactos / código / documentos** → `rick-delivery`.
3. **VPS / OpenClaw runtime / cron / observabilidad / runbooks** → `rick-ops`.
4. **QA / auditorías de proyectos Linear / trazabilidad de delivery** → `rick-qa`.
5. **Tracking horizontal / reportes cross-proyecto** → `rick-tracker`.
6. **Multi-gerencia o duda**: descomponer y orquestar en paralelo, NO inventar gerencia.

## Reglas operativas (heredadas)
- Conservás las 13 reglas operativas previas (gobernanza Linear, prohibición push a main, integración sessions_spawn, etc.). Esta sección **NO las reemplaza**, las complementa.

## Topología bajo tu mando
Ver `notion-governance/docs/architecture/15-rick-organizational-model.md` §5.3.
```

Mismo criterio: NO sobrescribir SOUL/TOOLS/SKILL si ya existen.

### 6. Reload de OpenClaw gateway

```bash
systemctl --user restart openclaw-gateway
sleep 3
systemctl --user status openclaw-gateway --no-pager | head -20
openclaw status --all 2>&1 | head -40
```

Si `status` reporta error de carga de algún agent → revertir cambios usando el backup de paso 1 y reportar.

### 7. Verificación post-cambio

```bash
# 7.1 allowAgents efectivo
python3 -c "
import json
d = json.load(open('/home/rick/.openclaw/openclaw.json'))
for a in d['agents']['list']:
    aid = a.get('id', '?')
    sub = a.get('subagents', {}).get('allowAgents', [])
    print(f'{aid}: {sub}')
"

# 7.2 Smoke test invocación delegada (NO ejecutar trabajo real, solo verificar que el grafo es navegable)
openclaw agents list 2>&1 | head -20

# 7.3 Logs recientes del gateway
journalctl --user -u openclaw-gateway --since '5 minutes ago' --no-pager | tail -30
```

### 8. Reportar (append al final de este archivo)

Sección `## Resultado 2026-05-05`:

1. Output del paso 2 (snapshot pre-cambio).
2. Lista de agents modificados (output del script de paso 3).
3. Confirmación de validación JSON.
4. Confirmación de path real de IDENTITY.md para `main` y `rick-orchestrator` (donde escribiste).
5. Output `systemctl status` post-restart (head 10).
6. Output del paso 7.1 (allowAgents efectivo post-cambio).
7. Cualquier error encontrado y si revertiste o no.

Commit: `feat(agents): re-prompt main+orchestrator y reconfigura allowAgents §5.3 (Ola 1)`. Push a `main`.

---

## Anti-patterns prohibidos

- ❌ NO sobrescribir `SOUL.md`, `TOOLS.md`, `SKILL.md` de ningún agent.
- ❌ NO modificar `allowAgents` de ningún agent que no sea `main` o `rick-orchestrator`.
- ❌ NO eliminar agents del array `agents.list`.
- ❌ NO commitear contenido de `~/.config/openclaw/env` ni tokens.
- ❌ NO continuar si paso 6 (restart) falla — revertir usando backup.
- ❌ NO trabajar en una branch que no sea `main` (paso 0 obligatorio).

---

## Notas

- Esta task NO depende de OAuth multi-canal (task 004). Las gerencias `rick-communication-director` y `rick-linkedin-writer` ya existen como agents en repo+VPS — solo falta hacerlos invocables vía `allowAgents`.
- Una vez completada, queda desbloqueada Ola 2 (Mejora Continua) y Ola 1b (primer use case multi-canal end-to-end).
- Los IDENTITY.md propuestos son **mínimos viables**. David puede iterarlos después; lo importante de esta task es: (1) topología `allowAgents` correcta, (2) prompts dicen explícitamente quién es CEO y quién meta-orquestador.

---

## Resultado 2026-05-05

**Ejecutado por:** Copilot VPS (sesión Copilot Chat con shell local en VPS Hostinger `srv1431451`)
**Fecha/hora:** 2026-05-05 10:16–10:18 ART
**Modo:** write controlado. Tocados solo: `~/.openclaw/openclaw.json` (allowAgents de 2 agents), `IDENTITY.md` de `main` y `rick-orchestrator`.
**SOUL/AGENTS/SKILL/TOOLS:** preservados intactos en ambos workspaces (verificado con `ls`).

### 0. Branch + sync

```
$ git checkout main && git pull --ff-only origin main
Switched to branch 'main'
Updating 1e7c84a..e723722
Fast-forward
 .agents/tasks/2026-05-05-005-...md | 243 +++++++++++++
```

Nota: la rama tenía 2 archivos no commiteados de sesiones previas (`.agents/tasks/2026-05-04-001-...md` modified, `docs/ops/cand-003-...md` untracked). Ninguno relacionado con esta task. Se dejaron tal cual (no `git stash` necesario porque el checkout ya estaba en main).

### 1. Backup `openclaw.json`

```
/home/rick/.openclaw/openclaw.json.bak.20260505-101629  (30829 bytes, owner rick:rick)
```

### 2. Snapshot pre-cambio (`allowAgents` antes)

```
main:                        ['main', 'rick-orchestrator', 'rick-delivery', 'rick-qa', 'rick-tracker', 'rick-ops']
rick-orchestrator:           ['rick-delivery', 'rick-qa', 'rick-tracker', 'rick-ops']
rick-delivery:               []
rick-qa:                     []
rick-tracker:                []
rick-ops:                    []
rick-communication-director: []
rick-linkedin-writer:        []
```

### 3. Mutación `allowAgents` + validación JSON

```
$ python3 <<PY ...
changed: ['main', 'rick-orchestrator']
$ python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null
JSON OK
```

Solo `main` y `rick-orchestrator` recibieron el `subagents.allowAgents` actualizado. Ningún otro agent fue tocado. Orden de keys preservado vía `json.dumps(..., indent=2, ensure_ascii=False)` con `setdefault`.

### 4. Re-prompt de `main` — path real

**Path declarado en la task:** `~/.openclaw/agents/main/agent/IDENTITY.md` → **NO existe**. Ese directorio solo contiene `auth-profiles.json`, `auth-state.json`, `auth.json`, `models.json`, `models.json.bak.rs-fallback.`. Sin IDENTITY.

**Path real (resuelto desde `agents.list[id=main].workspace`):** `/home/rick/.openclaw/workspace/IDENTITY.md` (workspace canónico de `main`, contiene también `AGENTS.md`, `SOUL.md`, etc. — todos preservados).

**Acción:** backup `+ overwrite` con el bloque IDENTITY canónico de la task §4.

```
backup: /home/rick/.openclaw/workspace/IDENTITY.md.bak.20260505-101646
target: /home/rick/.openclaw/workspace/IDENTITY.md
head:   "# Rick (CEO)" + bloque Misión completo
```

### 5. Re-prompt de `rick-orchestrator` — path real

**Path declarado en la task:** `~/.openclaw/agents/rick-orchestrator/agent/IDENTITY.md` → **NO existe** (mismo patrón: `~/.openclaw/agents/<id>/` solo guarda `sessions/` + `auth/`).

**Path real (resuelto desde `agents.list[id=rick-orchestrator].workspace`):** `/home/rick/.openclaw/workspaces/rick-orchestrator/IDENTITY.md` (workspace canónico, contiene `AGENTS.md`, `SOUL.md`, `SKILL.md`, `TOOLS.md`, `HEARTBEAT.md`, `USER.md` — todos preservados).

**Acción:** backup `+ overwrite` con el bloque IDENTITY canónico de la task §5.

```
backup: /home/rick/.openclaw/workspaces/rick-orchestrator/IDENTITY.md.bak.20260505-101646
target: /home/rick/.openclaw/workspaces/rick-orchestrator/IDENTITY.md
head:   "# Rick Orchestrator (meta-orquestador)" + bloque Misión completo
```

### 6. Restart gateway

```
$ systemctl --user restart openclaw-gateway
● openclaw-gateway.service - OpenClaw Gateway (v2026.3.2)
     Active: active (running) since Tue 2026-05-05 10:17:34 -04
   Main PID: 1415756
[gateway] loading configuration…
[gateway] resolving authentication…
[gateway] starting...
```

`openclaw status --all` confirma: **Agents: 8 total · 0 bootstrapping · 2 active · 61 sessions**. Sin errores de carga de ningún agent. **No se requirió rollback.**

### 7. Verificación post-cambio

**7.1 `allowAgents` efectivo:**

```
main:                        ['rick-orchestrator']
rick-orchestrator:           ['rick-communication-director', 'rick-delivery', 'rick-ops', 'rick-qa', 'rick-tracker', 'rick-linkedin-writer']
rick-delivery:               []
rick-qa:                     []
rick-tracker:                []
rick-ops:                    []
rick-communication-director: []
rick-linkedin-writer:        []
```

Coincide exactamente con la topología objetivo §5.3.

**7.3 Logs post-restart — errores/warnings analizados:**

- ✅ Cero menciones de `error`/`fail` referenciando `main`, `rick-orchestrator` o cualquier agent.
- ⚠️ "Config warnings" preexistente (plugin `acpx` stale + `plugins.load.paths` redundante) — heredado desde antes de esta task (mismo warning observado en task 003 commit `45ff7e1`). NO introducido por este cambio.
- ⚠️ Ráfaga continua de `[ws] closed before connect conn=... reason=connect failed` desde `fwd=100.109.16.40` (un nodo tailnet) — **mismo rate antes y después del restart** (cada ~3-7s, presente desde 10:16:19 pre-cambio hasta 10:17:58 post-cambio sin variación). Es un bucle de reconexión con auth token inválido en ese cliente, **NO causado por esta task**. Reportar como observación operativa para `rick-ops` si David quiere investigarlo aparte.

### 8. Errores y rollback

**Sin errores bloqueantes. Sin rollback ejecutado.** Backup de `openclaw.json` y de los dos `IDENTITY.md.bak.*` quedan en disco para rollback rápido si se necesita en el futuro.

### Conclusión

Topología §5.3 implementada en runtime:
- `main` (Rick CEO) ahora delega exclusivamente a `rick-orchestrator`.
- `rick-orchestrator` ahora puede invocar a las 6 gerencias incluyendo `rick-communication-director` y `rick-linkedin-writer` (antes inalcanzables).
- IDENTITY.md de ambos refleja explícitamente el rol CEO vs meta-orquestador.

**Ola 1 fundamentos completada. Ola 1b (primer use case multi-canal end-to-end) y Ola 2 (Mejora Continua) desbloqueadas.**
