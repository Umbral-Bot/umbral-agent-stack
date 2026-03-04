---
name: windows
description: >-
  Execute Windows VM operations through Umbral Worker tasks:
  Power Automate Desktop flows, interactive worker bootstrap, firewall setup,
  and filesystem read/write helpers under policy-controlled paths.
  Use when "run pad flow", "open notepad", "write file on vm",
  "list files on windows", "start interactive worker", "allow vm port".
metadata:
  openclaw:
    emoji: "\U0001F5A5"
    requires:
      env:
        - WORKER_URL_VM
---

# Windows Skill

Rick puede ejecutar acciones en la VM Windows usando tasks `windows.*` y `windows.fs.*`.

## Requisitos

- `WORKER_URL_VM` accesible por Tailscale.
- Worker levantado en la VM Windows.
- Para PAD: Power Automate Desktop instalado.
- Para filesystem: rutas permitidas en `config/tool_policy.yaml`.

## Tasks disponibles

### 1. Ejecutar flujo PAD

Task: `windows.pad.run_flow`

```json
{
  "flow_name": "MiFlujoPAD"
}
```

Devuelve: `{"ok": bool, "flow_name":"...", "exit_code": int, "output":"...", "error":"...|null"}`

### 2. Abrir Bloc de notas

Task: `windows.open_notepad`

```json
{
  "text": "Prueba de sesion interactiva",
  "run_now": true
}
```

Devuelve: `{"ok": bool, "path":"...", "scheduled": bool, "error":"...|null"}`

### 3. Escribir token del Worker

Task: `windows.write_worker_token`

```json
{}
```

Devuelve: `{"ok": bool, "path":"C:\\openclaw-worker\\worker_token", "error":"...|null"}`

### 4. Permitir puerto en firewall

Task: `windows.firewall_allow_port`

```json
{
  "port": 8089,
  "name": "OpenClaw Worker 8089"
}
```

Devuelve: `{"ok": bool, "port": 8089, "name":"...", "error":"...|null"}`

### 5. Iniciar Worker interactivo

Task: `windows.start_interactive_worker`

```json
{}
```

Devuelve: `{"ok": bool, "bat":"...", "error":"...|null"}`

### 6. Agregar Worker interactivo al startup

Task: `windows.add_interactive_worker_to_startup`

```json
{
  "username": "Rick"
}
```

Devuelve: `{"ok": bool, "startup":"...", "link":"...", "error":"...|null"}`

### 7. Crear directorios

Task: `windows.fs.ensure_dirs`

```json
{
  "path": "G:\\Compartido\\Reportes"
}
```

Devuelve: `{"ok": bool, "path":"...", "error":"...|null"}`

### 8. Listar archivos

Task: `windows.fs.list`

```json
{
  "path": "G:\\Compartido",
  "limit": 200
}
```

Devuelve: `{"ok": bool, "path":"...", "entries":[...], "error":"...|null"}`

### 9. Leer texto

Task: `windows.fs.read_text`

```json
{
  "path": "G:\\Compartido\\notas.txt",
  "max_chars": 200000
}
```

Devuelve: `{"ok": bool, "path":"...", "text":"...", "truncated": bool, "error":"...|null"}`

### 10. Escribir texto

Task: `windows.fs.write_text`

```json
{
  "path": "G:\\Compartido\\salida.txt",
  "text": "contenido",
  "max_chars": 500000
}
```

Devuelve: `{"ok": bool, "path":"...", "chars": int, "error":"...|null"}`

### 11. Escribir binario base64

Task: `windows.fs.write_bytes_b64`

```json
{
  "path": "G:\\Compartido\\audio.mp3",
  "b64": "BASE64_PAYLOAD"
}
```

Devuelve: `{"ok": bool, "path":"...", "bytes": int, "error":"...|null"}`

## Triggers recomendados

- "run pad flow"
- "open notepad"
- "write file on vm"
- "list files on windows"
- "start interactive worker"

## Referencias

- `worker/tasks/windows.py`
- `worker/tasks/windows_fs.py`
- `worker/tasks/windows_fs_bin.py`

## Notas

- Estas tasks solo funcionan cuando el Worker corre en la VM Windows.
- `windows.fs.*` y `windows.fs.write_bytes_b64` respetan allowlist de rutas por policy.
