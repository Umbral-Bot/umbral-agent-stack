# 34 — Windows FS tools (sin PAD)

## Objetivo
Permitir operaciones simples de archivos/carpetas en la VM (ej. `G:\\Mi unidad\\Rick-David`) sin depender de Power Automate Desktop.

## Seguridad
Se restringe por allowlist en `config/tool_policy.yaml`:

```yaml
tools:
  fs:
    allowed_base_paths:
      - G:\\Mi unidad\\Rick-David
      - C:\\Windows\\Temp
```

El Worker valida que cualquier `path` esté **dentro** de alguno de esos prefijos.

## Tareas
- `windows.fs.ensure_dirs` — crea árbol de directorios
- `windows.fs.list` — lista entradas
- `windows.fs.read_text` — lee archivo texto UTF-8 (limitado)
- `windows.fs.write_text` — escribe archivo texto UTF-8 (limitado)

## Ejemplos

```json
{ "task": "windows.fs.ensure_dirs", "input": {"path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas\\informes"} }
```

```json
{ "task": "windows.fs.list", "input": {"path": "G:\\Mi unidad\\Rick-David", "limit": 200} }
```
