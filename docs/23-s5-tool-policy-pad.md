# 23 — S5 ToolPolicy y Conector PAD

## Resumen

- **ToolPolicy**: allowlist de herramientas Windows (`config/tool_policy.yaml`).
- **Conector PAD**: tarea `windows.pad.run_flow` para ejecutar flujos de Power Automate Desktop en la VM.
- Solo flujos/scripts listados en la allowlist pueden ejecutarse.

## Archivos

- `config/tool_policy.yaml` — Configuración allowlist.
- `worker/tool_policy.py` — Carga y validación de la política.
- `worker/tasks/windows.py` — Handler `windows.pad.run_flow`.
- `runbooks/runbook-pad-flow.md` — Procedimiento para crear y ejecutar flujos PAD.

## Uso

```json
{
  "task": "windows.pad.run_flow",
  "input": { "flow_name": "EchoTest" }
}
```

La tarea debe enviarse con `requires_vm: true` para que el Dispatcher la enrute al Worker en la VM.

## Pendiente

- MCP tools para Windows.
- Artifacts y auditoría de ejecución.
