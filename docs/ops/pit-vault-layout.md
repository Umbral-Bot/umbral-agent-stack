# PIT Vault — Layout (umbral-pit-vault)

- **Status:** v1 (PIT-1 spec) — 2026-06-09.
- **Decisión:** el trabajo PIT vive en un vault Obsidian **separado** (`umbral-pit-vault`) del vault personal de David, que sigue siendo **pull-only** en la VPS ([`obsidian-context-vault.md`](obsidian-context-vault.md)). El pit-vault sí admite escritura de agentes, **acotada a `pit/`**.
- **Herramientas:** [`scripts/pit/pit_vault_init.sh`](../../scripts/pit/pit_vault_init.sh) (bootstrap idempotente) + [`scripts/pit/pit_vault_check.py`](../../scripts/pit/pit_vault_check.py) (check read-only, basado en `obsidian_context_check.py`).

---

## 1. Topología

```text
Windows Obsidian app (David, lectura/curación)
  <- git repo privado umbral-pit-vault ->
VPS clone ~/umbral-pit-vault (agentes PIT)
  - lanes escriben SOLO bajo pit/<pit_id>/lanes/<lane_id>/
  - Rick escribe pit/<pit_id>/ (spec, outcome) y mueve a archive/ al cierre
```

A diferencia del vault personal (mirror pull-only), aquí los agentes commitean y pushean sus carpetas de torneo. David ve el tablero/notas desde su Obsidian con pull.

## 2. Estructura requerida

```text
umbral-pit-vault/
├── README.md
├── .gitignore                  # .obsidian/workspace*.json
├── pit/                        # ÚNICO árbol writable por agentes
│   └── <pit_id>/
│       ├── spec/pit_spec.yaml          # escrito por Rick post "ok, arranca"
│       ├── research/                   # notas compartidas del torneo
│       ├── lanes/
│       │   └── lane-<slug>/            # write scope de UNA lane
│       │       ├── kanban/board.md     # desde templates/kanban-lane.md
│       │       └── iterations/<n>/
│       │           ├── kpi_pack.json   # contra kpi-pack.schema.json
│       │           ├── prototype/      # fuentes html
│       │           └── notes.md
│       └── outcome/pit_outcome_report.yaml
├── templates/                  # read-only para lanes; sync desde el repo
│   ├── kanban-lane.md
│   ├── kpi-pack.schema.json
│   ├── pit_outcome_report.yaml
│   └── pit-<nombre>.yaml       # plantillas guardadas ("guarda como plantilla PIT <nombre>")
└── archive/                    # torneos cerrados; mueve Rick, no las lanes
    └── <pit_id>/ ...
```

Las fuentes canónicas de `templates/` viven en el repo: [`openclaw/workspace-templates/pit-vault/templates/`](../../openclaw/workspace-templates/pit-vault/templates/). El vault recibe copias vía `pit_vault_init.sh --with-templates <repo>`.

## 3. Reglas de escritura (write scope)

| Actor | Puede escribir | No puede |
|---|---|---|
| Lane agent (efímero) | `pit/<pit_id>/lanes/<su lane>/` | otras lanes, `spec/`, `outcome/`, `templates/`, `archive/`, raíz |
| Rick (broker/orquestador) | `pit/<pit_id>/` completo + `templates/pit-<nombre>.yaml` (plantillas) + mover a `archive/` | vault personal de David |
| David | todo (es su vault) | — |

- El runtime declara el scope con `PIT_VAULT_WRITE_SCOPE=pit`; `pit_vault_check.py --require-write-scope` falla si no está declarado.
- La raíz del vault es cerrada: solo `README.md`, `.gitignore`, `.gitattributes` (+ `.obsidian/`). Cualquier otro archivo suelto en raíz es error del check.
- El aislamiento por lane es el equivalente product del worktree por lane de D3 (docs/79 §4.3): cada lane solo toca su subárbol.

## 4. Seguridad (idéntica al vault personal)

- Prohibido en el vault: `.env`, llaves privadas (`id_*`, `*.pem`, `*.key`, …), `credentials.json`, `token.json`, sesiones de browser. El check los detecta y falla.
- Sin datos personales reales de usuarios; las señales de personas sintéticas van etiquetadas (ver [`pit-kanban-kpi-protocol.md`](pit-kanban-kpi-protocol.md) §5).
- `.obsidian/workspace*.json` no se versiona.

## 5. Bootstrap + check

```bash
# VPS (post-merge; NO ejecutar como parte del PR PIT-1)
bash scripts/pit/pit_vault_init.sh ~/umbral-pit-vault --with-templates ~/umbral-agent-stack

export PIT_VAULT_PATH=$HOME/umbral-pit-vault
export PIT_VAULT_WRITE_SCOPE=pit
python scripts/pit/pit_vault_check.py --vault-path "$PIT_VAULT_PATH" --require-write-scope
```

```powershell
# Windows (local, lectura)
$env:PIT_VAULT_PATH="C:\Users\david\Documents\umbral-pit-vault"
python scripts/pit/pit_vault_check.py --vault-path $env:PIT_VAULT_PATH
```

Veredictos esperados: `pass`/`fail` del check; el deploy del vault en VPS es ítem post-merge del plan ([`q2-core-first-unified-plan-2026-06-04.md`](q2-core-first-unified-plan-2026-06-04.md)).
