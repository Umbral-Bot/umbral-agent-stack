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
