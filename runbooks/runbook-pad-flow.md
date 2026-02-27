# Runbook: Ejecutar flujos PAD desde Rick (VM)

## Contexto

Rick puede invocar flujos de Power Automate Desktop en la VM mediante la tarea `windows.pad.run_flow`. Solo los flujos en la allowlist (`config/tool_policy.yaml`) pueden ejecutarse.

## Requisitos

- VM Windows con Worker (NSSM) y Power Automate Desktop instalado.
- Flujo PAD creado y añadido a `config/tool_policy.yaml`.

## Crear flujo de prueba (EchoTest)

1. Abre Power Automate Desktop.
2. Nuevo flujo → nombre: **EchoTest**.
3. Añade acciones mínimas (ej. "Mostrar mensaje" con texto fijo).
4. Guarda el flujo.

## Registrar flujo en allowlist

Edita `config/tool_policy.yaml`:

```yaml
tools:
  pad:
    allowed_flows:
      - EchoTest
      - MiFlujoRPA   # Añadir aquí
    default_timeout_sec: 60
```

## Invocación desde Rick

La tarea se envía con `requires_vm: true` para que el Dispatcher la enrute a la VM:

```json
{
  "task": "windows.pad.run_flow",
  "input": { "flow_name": "EchoTest" }
}
```

## Ruta PAD

Por defecto: `C:\Program Files (x86)\Power Automate Desktop\PAD.Console.Host.exe`

Si PAD está en otra ruta, modificar `worker/tasks/windows.py`.

## Troubleshooting

- **"Flow not in allowlist"**: añadir el nombre exacto del flujo en `config/tool_policy.yaml`.
- **"PAD.Console.Host.exe not found"**: instalar PAD o verificar ruta.
- **Timeout**: aumentar `default_timeout_sec` en tool_policy.yaml.
