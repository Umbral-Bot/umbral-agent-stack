# PIT Broker Contract — Worker `copilot_cli.run`

> **Estado: HISTÓRICO.** Frente PIT archivado por gobernanza (inventario
> `docs/ops/uas-north-inventory-2026-08-06.md` §1 A.2). Este documento es registro de lo que se
> definió — **no es contrato runtime vigente**. La skill `product-innovation-tournament` en
> `main` sigue en su versión previa (v1.3); este contrato v1 nunca se cableó a ella.

- **Status:** v1 P0 — 2026-06-20.
- **Contrato canónico amplio:** [`pit-tournament-v2-contract.md`](pit-tournament-v2-contract.md).
- **Scope:** quién puede hacer qué y qué debe auditarse para declarar broker-real.

---

## Actores y permisos

| Actor | Puede | No puede |
|---|---|---|
| David | Autorizar gates, budget, secrets scope y re-run | Delegar aprobación implícita a una lane |
| Rick | Parsear, validar, confirmar, spawnear lanes y pedir batches al Worker | Ejecutar coding/repo directo fuera de `copilot_cli.run` |
| Lane OpenClaw | Orquestar estrategia, pedir batches broker, escribir evidencia de lane | Implementar directo, saltar broker, imprimir secretos |
| Worker | Ejecutar `copilot_cli.run` dentro del sandbox permitido | Aumentar permisos sin gate |
| Mission Control | Juzgar evidencia y comparar lanes | Convertir visual-only en broker-real |

## Payload mínimo `copilot_cli.run`

Todo batch debe incluir metadata obligatoria:

```yaml
task_type: copilot_cli.run
pit_id: pit-ejemplo-ruta-b
lane_id: lane-a
batch_id: batch-001
iteration: 1
repo:
  provider: github
  repo: TODO_OWNER/TODO_REPO
  ref: TODO_BRANCH_OR_SHA
  allowed_paths:
    - docs/
permissions:
  execute: false
  egress: false
  write_sandbox: false
  repo_product_push: false
secrets_scope:
  allow_env_refs: []
  allow_mcp: []
  deny:
    - raw_secret_values
  human_approval: required
request:
  intent: TODO
  instructions_ref: pit/<pit_id>/lanes/<lane_id>/requests/batch-001.md
```

Reglas:

- `pit_id`, `lane_id`, `batch_id` e `iteration` son obligatorios.
- `instructions_ref` apunta al vault; no incrustar secretos en payload.
- `execute=false` produce plan/dry-run, nunca ejecución real.
- `write_sandbox=true` solo aparece desde L4.
- `repo_product_push=true` solo aparece desde L5 con gate David.

## Auditoría mínima

Cada resultado debe producir un registro JSONL sanitizado con:

```yaml
timestamp: TODO
pit_id: pit-ejemplo-ruta-b
lane_id: lane-a
batch_id: batch-001
iteration: 1
broker: copilot_cli
execute: false
egress: false
write_sandbox: false
repo_product_push: false
model_ref: TODO_P3_VPS_VERIFY_MODEL_A
exit_status: blocked_or_pass
token_usage_ref: metrics/token_ledger.yaml
artifacts:
  - path: pit/<pit_id>/lanes/<lane_id>/broker/batch-001/
sanitized: true
```

Sin este registro, el batch no cuenta para `PIT_RUN_PASS_BROKER_REAL`.

## Subcomandos prohibidos

`banned_subcommands` debe bloquear, salvo gate L5 explícito y wrapper seguro:

```yaml
banned_subcommands:
  - git push
  - git push --force
  - git reset --hard
  - gh pr merge
  - gh release create
  - docker login
  - ssh
  - scp
  - curl --data-binary @
  - powershell Invoke-WebRequest with secret-bearing payloads
  - printenv
  - set
  - type .env
  - cat .env
```

Notas:

- `git diff`, `git status` y lectura de archivos permitidos pueden habilitarse en L2.
- Escrituras solo en sandbox de lane desde L4.
- Push a repo producto nunca es automático.

## Fallos

Si el Worker devuelve error:

- La lane registra `lane_status: blocked`.
- Rick reporta el motivo a David.
- No hay fallback silencioso a OpenClaw directo.
- No hay mock que simule éxito.
- No se degrada a `azure-openai-responses` para coding si el spec declara
  `coding_broker: copilot_cli`.

## Veredicto broker-real

Un torneo solo puede declarar `PIT_RUN_PASS_BROKER_REAL` cuando:

- Todos los batches de coding/repo pasaron por `copilot_cli.run`.
- La auditoría incluye metadata obligatoria.
- El token ledger existe.
- Los permisos observados no exceden el spec.
- Mission Control judge pudo leer evidencia.
- David gate final quedó registrado.
